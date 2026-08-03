#!/usr/bin/env python3
"""Create GitHub repos under the-quizzman and push local classical-text scaffolds."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
ORG = "the-quizzman"


def load_catalog() -> dict:
    import yaml

    return yaml.safe_load((ROOT / "catalog.yaml").read_text(encoding="utf-8"))


def repo_exists(name: str) -> bool:
    r = subprocess.run(
        ["gh", "repo", "view", f"{ORG}/{name}", "--json", "name"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def ensure_remote_and_push(path: Path, name: str, description: str) -> str:
    if not (path / ".git").exists():
        raise RuntimeError(f"no git repo at {path}")

    # remote
    remotes = subprocess.check_output(["git", "remote"], cwd=path, text=True).split()
    url = f"https://github.com/{ORG}/{name}.git"
    if "origin" not in remotes:
        if repo_exists(name):
            subprocess.run(["git", "remote", "add", "origin", url], cwd=path, check=True)
        else:
            subprocess.run(
                [
                    "gh",
                    "repo",
                    "create",
                    f"{ORG}/{name}",
                    "--public",
                    f"--description={description}",
                    "--source=.",
                    "--remote=origin",
                    "--push",
                ],
                cwd=path,
                check=True,
            )
            return f"https://github.com/{ORG}/{name}"
    # already has origin or remote added without push
    subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=path, check=True)
    return f"https://github.com/{ORG}/{name}"


def main() -> None:
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    catalog = load_catalog()
    results = []

    items = []
    for col in catalog.get("collections", []):
        items.append(
            (
                col["id"],
                f"{col['title_original']} — collection index (Classical Text Spec v1)",
            )
        )
    for book in catalog.get("books", []):
        items.append(
            (
                book["id"],
                f"{book['title_original']} — Quizzman Classical Text Spec v1",
            )
        )

    for name, desc in items:
        if only and name not in only:
            continue
        if name == "sunzi" and not only:
            # already created in prior step; still ensure push
            pass
        path = BOOKS / name
        if not path.exists():
            print(f"MISSING {path}")
            continue
        try:
            url = ensure_remote_and_push(path, name, desc)
            print(f"OK {name} -> {url}")
            results.append({"id": name, "url": url, "ok": True})
        except Exception as e:
            print(f"FAIL {name}: {e}")
            results.append({"id": name, "error": str(e), "ok": False})

    out = ROOT / "sources" / "github-repos.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"\nDone: {ok}/{len(results)} — wrote {out}")


if __name__ == "__main__":
    main()
