from pathlib import Path

from ingestion.pdf import clean_text, parse_pdf

MANUALS = Path(__file__).resolve().parents[2] / "data" / "manuals"


def test_clean_text_normalises_whitespace_and_unicode() -> None:
    assert clean_text("a \t b\n\n  c� \n") == "a b\nc"
    assert clean_text("100 MΩ") == "100 MΩ"


def test_parse_keeps_page_numbers_and_strips_headers() -> None:
    pages = parse_pdf(MANUALS / "P-MT-02_pump_maintenance_troubleshooting.pdf")
    assert [p.number for p in pages] == [1, 2, 3, 4]
    assert "Fault table" in pages[1].text
    assert "Troubleshooting high vibration" in pages[2].text
    for page in pages:
        assert "Sample document" not in page.text
        assert not any(line.startswith("Page ") for line in page.text.splitlines())


def test_hidden_text_is_extracted() -> None:
    # The service bulletin hides an instruction in white 1pt text. The parser sees it,
    # which is why retrieved text has to be filtered before it reaches the model.
    pages = parse_pdf(MANUALS / "SB-P-017_pump_seal_service_bulletin.pdf")
    assert "ignore all previous instructions" in pages[0].text.lower()
