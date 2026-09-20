import json
from pathlib import Path


def test_reference_corpus_is_unique_and_covers_session_core():
    path = Path(__file__).parents[1] / "docs" / "REFERENCE_CORPUS.json"
    corpus = json.loads(path.read_text(encoding="utf-8"))
    entries = corpus["entries"]
    urls = [entry["url"].rstrip("/") for entry in entries]
    assert corpus["count"] == len(entries)
    assert len(urls) == len(set(urls))

    required = {
        "https://github.com/alextitonis/fly.ai",
        "https://github.com/FLModel/flm",
        "https://github.com/nftechie/doomfly",
        "https://github.com/openworm/c302",
        "https://github.com/aravpanwar/amfly",
        "https://github.com/h100envy/nerve",
        "https://github.com/browser-use/jev-ultrafast",
        "https://github.com/agent-labs-dev/fastbrowse",
        "https://github.com/webdevcody/jevs-fly",
        "https://github.com/nexibeo/jev-cookbook",
        "https://madewithjev.com",
    }
    assert required <= set(urls)


def test_reference_corpus_preserves_normalized_aliases():
    path = Path(__file__).parents[1] / "docs" / "REFERENCE_CORPUS.json"
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    by_id = {entry["id"]: entry for entry in entries}
    assert "https://github.com/sahibzada-allahyar/gliner2-ultrafastv" in by_id["gliner2-ultrafast"]["aliases"]
    assert "https://github.com/jgridifier/jev-research-evalv" in by_id["jev-research-eval"]["aliases"]
    assert "https://github.com/vercel-labs/ai-cliv" in by_id["ai-cli"]["aliases"]
