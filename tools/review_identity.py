"""Reserve one review build in the fork's durable, CAS-updated ledger.

Run before EVERY artifact-producing build, including retries. Reusing an
artifact does not call this tool. The ledger branch must already exist.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args]).decode().strip()


def reserve(repository, pr):
    path = f"repos/{repository}/contents/build-ledger/pr-{pr}.json"
    for _ in range(20):
        read = subprocess.run(["gh", "api", path + "?ref=build-ledger"],
                              capture_output=True, text=True)
        sha = None
        if read.returncode == 0:
            previous = json.loads(read.stdout)
            sha = previous["sha"]
            entries = json.loads(base64.b64decode(previous["content"]))
        elif "404" in read.stderr:
            entries = []
        else:
            raise RuntimeError(read.stderr)
        ordinal = max((entry["ordinal"] for entry in entries), default=0) + 1
        entries.append({"ordinal": ordinal, "state": "reserved",
                        "source_revision": git("rev-parse", "HEAD")})
        body = {"message": f"build: reserve pr-{pr} build-{ordinal:03d}",
                "branch": "build-ledger",
                "content": base64.b64encode(json.dumps(entries, indent=2).encode()).decode()}
        if sha:
            body["sha"] = sha
        write = subprocess.run(["gh", "api", "--method", "PUT", path, "--input", "-"],
                               input=json.dumps(body), capture_output=True, text=True)
        if write.returncode == 0:
            return ordinal
        if "409" not in write.stderr and "422" not in write.stderr:
            raise RuntimeError(write.stderr)
    raise RuntimeError("Build ledger remained busy; no build identity allocated")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="AbbyUsesAIThatCodes/WoWee")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target", default="windows-x86-64-Release")
    args = parser.parse_args()
    if args.pr < 1 or not re.fullmatch(r"[A-Za-z0-9-]+", args.target):
        parser.error("Invalid PR or target")
    release = json.loads((ROOT / "release.json").read_text())
    revision = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=normal"))
    # All tracked inputs, plus submodule revisions; generated output is excluded.
    digest = hashlib.sha256()
    for name in git("ls-files", "--cached", "--others", "--exclude-standard").splitlines():
        path = ROOT / name
        digest.update(name.encode())
        if path.is_file():
            digest.update(path.read_bytes())
    digest.update(git("submodule", "status").encode())
    ordinal = reserve(args.repository, args.pr)
    now = datetime.now(timezone.utc)  # one clock capture for all identity surfaces
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    identity = (f'{release["version"]}_{release["codename_slug"]}_pr-{args.pr}_'
                f'build-{ordinal:03d}_{stamp}_g{revision[:12]}')
    if dirty:
        identity += "-dirty-" + digest.hexdigest()[:12]
    identity += "_" + args.target
    manifest = {**release, "repository": args.repository, "scope": f"pr-{args.pr}",
                "ordinal": ordinal, "built_at_utc": now.isoformat(),
                "source_revision": revision, "dirty": dirty,
                "source_fingerprint_sha256": digest.hexdigest(),
                "target": args.target, "identity": identity}
    args.out.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidentally relabeling an existing artifact.
    with (args.out / "build-manifest.json").open("x") as file:
        json.dump(manifest, file, indent=2)
    (args.out / "identity.cmake").write_text(
        f'set(WOWEE_GIT_VERSION "{release["version"]}-pr.{args.pr}.{ordinal}")\n'
        f'set(WOWEE_BUILD_DATE "{now.isoformat()}")\n'
        f'set(WOWEE_BUILD_ID "{identity}")\n')
    (args.out / "BUILD_REPORT.txt").write_text(
        f'WoWee Review Build\n{identity}\nState: Reserved\n'
        f'Source: {revision}\nIn-Game QA: Pending\n')
    print(identity)


if __name__ == "__main__":
    main()
