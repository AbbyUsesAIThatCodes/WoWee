"""Package an isolated Windows review from an existing identified build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--build", type=Path, required=True)
parser.add_argument("--metadata", type=Path, required=True)
parser.add_argument("--output-root", type=Path, required=True)
parser.add_argument("--dll-dir", type=Path, action="append", required=True)
parser.add_argument("--licenses", type=Path, action="append", default=[])
args = parser.parse_args()
manifest = json.loads((args.metadata / "build-manifest.json").read_text())
destination = args.output_root / manifest["identity"]
destination.mkdir(parents=True, exist_ok=False)
for name in ("wowee.exe", "framexml_run.exe"):
    shutil.copy2(args.build / "bin" / name, destination / name)
for name in ("build-manifest.json", "BUILD_REPORT.txt"):
    shutil.copy2(args.metadata / name, destination / name)
for name in ("LICENSE", "NOTICE", "ATTRIBUTION.md"):
    shutil.copy2(ROOT / name, destination / name)
shutil.copytree(args.build / "bin" / "addons", destination / "addons")
shutil.copytree(args.build / "bin" / "assets", destination / "assets",
                ignore=shutil.ignore_patterns("Original Music"))
tracked = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "Data/"], text=True)
for name in tracked.splitlines():
    target = destination / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / name, target)

# Resolve PE imports without executing the DLLs. Fail rather than silently
# deliver a package that depends on the developer's PATH.
pending = list(destination.glob("*.exe"))
seen = set()
system = Path(os.environ["SystemRoot"]) / "System32"
while pending:
    binary = pending.pop()
    imports = subprocess.check_output(["objdump", "-p", str(binary)], text=True)
    for name in re.findall(r"DLL Name:\s*(\S+)", imports):
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        dependency = next((directory / name for directory in args.dll_dir
                           if (directory / name).is_file()), None)
        if dependency:
            shutil.copy2(dependency, destination / name)
            pending.append(destination / name)
        elif (system / name).is_file() or key.startswith(("api-ms-", "ext-ms-")):
            continue
        else:
            raise RuntimeError("Unresolved runtime dependency: " + name)
for index, licenses in enumerate(args.licenses):
    shutil.copytree(licenses, destination / "third-party-licenses" / str(index))
(destination / "SOURCE.txt").write_text(
    "Fork Review; No Game Assets Included\n"
    f'https://github.com/{manifest["repository"]}/commit/{manifest["source_revision"]}\n'
    "See LICENSE, NOTICE, ATTRIBUTION.md and third-party-licenses.\n")
hashes = {str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
          for path in destination.rglob("*") if path.is_file()}
(destination / "SHA256SUMS.json").write_text(json.dumps(hashes, indent=2))
print(destination.resolve())
