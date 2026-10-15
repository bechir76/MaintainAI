import math

from core.llm.fake_embedder import FakeEmbedder
from core.llm.text import stem, tokenize


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


async def test_deterministic_and_normalised() -> None:
    [a] = await FakeEmbedder(dim=256).embed(["Pump vibration limits"])
    [b] = await FakeEmbedder(dim=256).embed(["Pump vibration limits"])
    assert a == b
    assert math.isclose(sum(v * v for v in a), 1.0, rel_tol=1e-9)
    assert len(a) == 256


async def test_related_text_scores_higher() -> None:
    q, rel, unrel = await FakeEmbedder().embed(
        [
            "pump bearing vibration",
            "High vibration of the pump bearings is caused by misalignment",
            "Compressed air receivers must be drained",
        ]
    )
    assert cosine(q, rel) > cosine(q, unrel)


async def test_empty_text_gives_unit_vector() -> None:
    [v] = await FakeEmbedder(dim=8).embed(["the and of"])
    assert v == [1.0] + [0.0] * 7


def test_tokenize_and_stem() -> None:
    tokens = tokenize("The pumps are vibrating at 7.1 mm/s on P-3")
    assert tokens == ["pump", "vibr", "7.1", "mm/s", "p-3"]
    assert stem("bearings") == stem("bearing")
    assert stem("vibrating") == stem("vibration") == stem("vibrate")
    assert stem("gas") == "gas"


def test_compound_words_and_e_endings() -> None:
    assert "lockout" in tokenize("Lockout/Tagout procedure")
    assert "lockout/tagout" in tokenize("Lockout/Tagout procedure")
    assert stem("regreased") == stem("regrease") == stem("regreasing")
    assert tokenize("P-100/250") == ["p-100/250"]
