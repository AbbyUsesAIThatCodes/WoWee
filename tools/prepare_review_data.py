"""Create private metadata/FrameXML for review; reference existing assets read-only.

The client synchronizes its expansion tables into WOW_DATA_PATH at startup.
Never point a review client directly at an existing installation's Data root.
"""
import argparse
import json
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--destination", type=Path, required=True)
args = parser.parse_args()
source, destination = args.source.resolve(), args.destination.resolve()
if destination.exists():
    parser.error("Destination must be new")
if not (source / "expansions" / "wotlk" / "manifest.json").is_file():
    parser.error("Source must be a Data root with an extracted WotLK manifest")
destination.mkdir(parents=True)
for expansion in (source / "expansions").iterdir():
    if not (expansion / "manifest.json").is_file():
        continue
    target = destination / "expansions" / expansion.name
    target.mkdir(parents=True)
    for table in expansion.glob("*.json"):
        if table.name != "manifest.json":
            shutil.copy2(table, target / table.name)
    manifest = json.loads((expansion / "manifest.json").read_text(encoding="utf-8"))
    original_base = (expansion / manifest.get("basePath", ".")).resolve()
    # The upstream manifest reader resolves relative paths against its directory.
    manifest["basePath"] = os.path.relpath(original_base, target).replace("\\", "/")
    (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    # FrameXML is loaded directly from this path; texture/model reads go through
    # the manifest above. Copy interface files rather than sharing writable dirs.
    for relative in ("interface/FrameXML", "interface/AddOns", "fonts", "misc/fonts"):
        asset = expansion / relative
        if asset.is_dir():
            shutil.copytree(asset, target / relative)
print(f"Private review data: {destination}")
print("Existing extracted assets are referenced for reads; config/tables are private.")
