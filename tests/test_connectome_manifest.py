import json
from pathlib import Path
def test_manifest_has_hashes_for_installable_files():
    data=json.loads((Path(__file__).parents[1]/"config"/"connectomes.json").read_text())
    for pack in data["packs"]:
        if not pack["installable"]:continue
        assert pack["files"]
        for f in pack["files"]:assert f["url"].startswith("https://") and len(f["sha256"])==64
