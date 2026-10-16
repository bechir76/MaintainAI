import itertools

import pytest

from ingestion.chunking import chunk_pages, chunk_text, has_content
from ingestion.pdf import Page


def make_text(n: int) -> str:
    return "\n".join(f"Line {i} describes a maintenance step for the pump." for i in range(n))


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("A single line.") == ["A single line."]


def test_empty_text_gives_no_chunks() -> None:
    assert chunk_text("") == []


def test_chunks_respect_size() -> None:
    chunks = chunk_text(make_text(60), size=300, overlap=60)
    assert len(chunks) > 5
    assert all(len(c) <= 300 for c in chunks)


def test_consecutive_chunks_overlap() -> None:
    chunks = chunk_text(make_text(40), size=300, overlap=80)
    for prev, nxt in itertools.pairwise(chunks):
        last_line = prev.splitlines()[-1]
        assert last_line in nxt.splitlines()[:3]


def test_no_overlap_when_zero() -> None:
    chunks = chunk_text(make_text(40), size=300, overlap=0)
    joined = "\n".join(chunks).splitlines()
    assert len(joined) == 40


def test_every_line_is_kept() -> None:
    text = make_text(50)
    chunks = chunk_text(text, size=250, overlap=50)
    covered = {line for c in chunks for line in c.splitlines()}
    assert covered == set(text.splitlines())


def test_long_line_split_on_sentences() -> None:
    line = " ".join(f"Sentence number {i} is here." for i in range(50))
    chunks = chunk_text(line, size=200, overlap=0)
    assert all(len(c) <= 200 for c in chunks)
    assert all(c.endswith(".") for c in chunks)


def test_long_word_without_spaces_is_cut() -> None:
    chunks = chunk_text("x" * 500, size=200, overlap=0)
    assert [len(c) for c in chunks] == [200, 200, 100]


def test_new_section_starts_new_chunk() -> None:
    body = "\n".join(["Intro text that fills the first part of the page."] * 4)
    text = f"{body}\n4. Troubleshooting high vibration\nStep one."
    chunks = chunk_text(text, size=300, overlap=100)
    assert chunks[-1].startswith("4. Troubleshooting high vibration")


def test_overlap_must_be_smaller_than_size() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", size=100, overlap=100)


def test_chunks_never_cross_pages() -> None:
    page_two = "Only page two. " * 8
    pages = [Page(1, make_text(20)), Page(2, page_two), Page(3, "")]
    chunks = chunk_pages(pages, size=300, overlap=50)
    assert {c.page for c in chunks} == {1, 2}
    assert next(c for c in chunks if c.page == 2).text == page_two
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_numbered_steps_are_not_treated_as_headings() -> None:
    body = "\n".join(["Context sentence that fills up the chunk nicely."] * 4)
    text = f"{body}\n1. Confirm the reading. Take a manual reading.\n2. Check the trend."
    chunks = chunk_text(text, size=400, overlap=100)
    assert len(chunks) == 1


def test_pages_with_only_a_header_are_dropped() -> None:
    pages = [Page(1, "Eaton Compressor Rotary Screw Compressor"), Page(2, make_text(5))]
    assert {c.page for c in chunk_pages(pages)} == {2}
    assert not has_content("2-12 Installation & Operation")
