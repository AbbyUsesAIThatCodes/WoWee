"""Check the delivered review directory, binary, metadata and build console agree."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("artifact", type=Path)
parser.add_argument("--header", type=Path, required=True)
parser.add_argument("--log", type=Path, required=True)
args = parser.parse_args()
manifest = json.loads((args.artifact / "build-manifest.json").read_text())
identity = manifest["identity"]
assert args.artifact.name == identity, "Artifact directory name mismatch"
assert identity in args.header.read_text(), "Compiled header mismatch"
assert identity in args.log.read_text(errors="replace"), "Console mismatch"
assert identity in (args.artifact / "BUILD_REPORT.txt").read_text(), "Report mismatch"
assert identity.encode() in (args.artifact / "wowee.exe").read_bytes(), "Binary mismatch"
print("PASS: directory, manifest, header, binary, console, and report: " + identity)
