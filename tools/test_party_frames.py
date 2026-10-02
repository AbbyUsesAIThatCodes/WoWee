"""Run the real FrameXML regression with fresh config, without a server login."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path,
                        help="Reject a stale runner that does not contain this build identity")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    runner, data = args.runner.resolve(), args.data.resolve()
    if args.manifest:
        identity = json.loads(args.manifest.read_text())["identity"]
        if identity.encode() not in runner.read_bytes():
            parser.error("Runner does not match the requested build manifest; wait for linking")
        print("Testing build: " + identity)
    if not (data / "interface" / "FrameXML" / "PartyMemberFrame.lua").is_file():
        parser.error("--data must contain extracted WotLK interface/FrameXML/PartyMemberFrame.lua")
    results = []
    for fallback in ("1", "0"):
        with tempfile.TemporaryDirectory(prefix="party-frames-", dir=args.output) as temp:
            env = dict(os.environ, WOWEE_CONFIG_ROOT=str(Path(temp) / "config"),
                       WOWEE_LOG_FILE=str(Path(temp) / "wowee.log"),
                       WOWEE_LUA_API_FALLBACK=fallback, WOWEE_LOG_LEVEL="warn")
            result = subprocess.run([str(runner), str(data), "--player", "--party-regression"],
                                    cwd=temp, env=env, text=True, encoding="utf-8",
                                    errors="replace", stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=180)
            (args.output / f"party-frames-fallback-{fallback}.log").write_text(
                result.stdout, encoding="utf-8")
            summary = {"fallback": fallback, "returncode": result.returncode,
                       "passed": result.returncode == 0 and
                       "party regression: disband clears all slots: PASS" in result.stdout}
            results.append(summary)
            for line in result.stdout.splitlines():
                if "party regression:" in line or "error(s)" in line:
                    print(line)
    (args.output / "party-frames-results.json").write_text(json.dumps(results, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
