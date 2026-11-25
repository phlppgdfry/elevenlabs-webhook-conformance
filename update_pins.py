#!/usr/bin/env python3
"""Move every pin in sdks.json to the latest commit: the default branch for released SDKs, the
PR head for proposed changes. A merged or closed PR keeps its last pin.

Uses GITHUB_TOKEN when set (CI); anonymous requests work but are rate limited.
"""

import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def api(path: str) -> dict:
    request = urllib.request.Request(f"https://api.github.com/{path}",
                                     headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    path = ROOT / "sdks.json"
    sdks = json.loads(path.read_text())
    for s in sdks:
        old = s["ref"]
        if "proposed" in s:
            owner_repo, number = s["proposed"].split("github.com/")[1].split("/pull/")
            pr = api(f"repos/{owner_repo}/pulls/{number}")
            if pr["state"] == "open":
                s["ref"] = pr["head"]["sha"]
        else:
            s["ref"] = api(f"repos/{s['repo']}/commits/HEAD")["sha"]
        print(f"{s['name']:<24} {old[:7]} -> {s['ref'][:7]}")
    path.write_text(json.dumps(sdks, indent=2) + "\n")


if __name__ == "__main__":
    main()
