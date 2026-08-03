#!/usr/bin/env python3
"""Bootstrap Classical Text Spec v1 repos from catalog.yaml + Bronze Mirror corpus."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
BOOKS_DIR = ROOT / "books"

REQUIRED_SECTIONS = [
    "Original Text",
    "Textual Variants",
    "Sino-Vietnamese",
    "Literal Translation",
    "Literary Translation",
    "Commentary",
    "Textual Notes",
    "References",
]

PLACEHOLDER = "_Chưa biên soạn._"


def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        # Minimal subset parser for this catalog (no nested complexity beyond lists/dicts)
        return json.loads(subprocess.check_output(["python3", "-c", f"""
import sys
try:
    import yaml
except ImportError:
    sys.exit('PyYAML required: pip3 install pyyaml')
from pathlib import Path
import json
print(json.dumps(yaml.safe_load(Path({path!s}).read_text(encoding='utf-8')), ensure_ascii=False))
"""]).decode())
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def chapter_stub(
    n: int,
    title: str,
    book: dict,
    bm_blocks: list[dict],
) -> str:
    lit_en = ""
    original_bits = []
    for p in bm_blocks:
        original_bits.append(p.get("original_zh") or "")
        eng = (p.get("english") or "").strip()
        if eng:
            lit_en += f"\n\n### {p.get('section_zh') or p.get('section_en') or p['id']}\n\n{eng}\n"
            pers = (p.get("perspective_en") or "").strip()
            if pers:
                lit_en += f"\n_{pers}_\n"

    original = "\n\n".join(x for x in original_bits if x).strip() or PLACEHOLDER
    literary = ""
    literary += f"## Vietnamese\n\n{PLACEHOLDER}\n"
    if lit_en.strip():
        literary += f"\n## English — The Bronze Mirror\n{lit_en}\n"
    else:
        literary += f"\n## English\n\n{PLACEHOLDER}\n"

    refs = f"""| Layer | Source | License |
| --- | --- | --- |
| Hán văn (dự kiến) | Public domain classical text | PD-old |
| English excerpts (nếu có) | [The Bronze Mirror](https://thebronzemirror.com/) | CC BY-SA 4.0 |

Chi tiết: [`sources/ATTRIBUTION.md`](../sources/ATTRIBUTION.md).
"""

    body_parts = {
        "Original Text": original,
        "Textual Variants": PLACEHOLDER,
        "Sino-Vietnamese": PLACEHOLDER,
        "Literal Translation": PLACEHOLDER,
        "Literary Translation": literary.strip(),
        "Commentary": PLACEHOLDER,
        "Textual Notes": PLACEHOLDER,
        "References": refs.strip(),
    }

    lines = [
        "---",
        f"chapter: {n}",
        f"title: {title}",
        "status: draft",
        "version: 1",
        "---",
        "",
    ]
    for h in REQUIRED_SECTIONS:
        lines.append(f"# {h}")
        lines.append("")
        lines.append(body_parts[h])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_book_yaml(book: dict) -> str:
    return f"""# Quizzman Classical Text — book-level config
# Spec: docs/CLASSICAL-TEXT-SPEC.md (classical-text/v1)

spec: classical-text/v1
id: {book['id']}
title: {book['title']}
title_original: {book['title_original']}
author: {book['author']}
language: vi
category: {book['category']}
chapter_count: {book['chapter_count']}
chapter_glob: chapters/*.md
status: draft

licenses:
  original: PD-old
  bronzemirror_en: CC-BY-SA-4.0

sources:
  bronzemirror: https://thebronzemirror.com/
  primary: TBD

publish:
  base_url: https://wiki.quizzman.com
  book_path: {book['book_path']}

rebuild:
  mode: incremental
  webhook_endpoint: /api/github/webhook
  rebuild_endpoint: /api/wiki/rebuild
  branch: main
"""


def write_readme(book: dict, is_collection: bool = False, members: list[str] | None = None) -> str:
    if is_collection:
        member_lines = "\n".join(f"- `{m}`" for m in (members or []))
        return f"""# {book['title']}

Repo mục lục (Classical Text Spec v1) cho bộ **{book['title']}**（{book['title_original']}）.

Thành viên:

{member_lines}

Nguồn tham khảo curated: [The Bronze Mirror](https://thebronzemirror.com/).

Spec: [`docs/CLASSICAL-TEXT-SPEC.md`](docs/CLASSICAL-TEXT-SPEC.md)
"""

    return f"""# {book['title']}

Classical Text repo (Quizzman Classical Text Spec v1) — Markdown là **source of truth** cho sách **{book['title']}**（{book['title_original']}） trên [Quizzman Wiki](https://wiki.quizzman.com).

Spec: [`docs/CLASSICAL-TEXT-SPEC.md`](docs/CLASSICAL-TEXT-SPEC.md)

## Cấu trúc

```text
README.md
LICENSE
book.yaml
chapters/
  001.md … {book['chapter_count']:03d}.md
assets/
docs/
sources/
scripts/
```

Một chương = một file. Mọi lớp (nguyên văn, dị bản, Hán-Việt, dịch, chú, tham chiếu) nằm **trong cùng file**.

## Nguồn nội dung & giấy phép

| Nguồn | Nội dung | Giấy phép |
| --- | --- | --- |
| Classical Chinese (PD-old) | Original Text | PD-old |
| [The Bronze Mirror](https://thebronzemirror.com/) | Đoạn English curated (nếu có) | **CC BY-SA 4.0** |

> **Lưu ý:** thebronzemirror.com hiện chỉ có đoạn chọn lọc, không phải full text. Các chương còn trống (`_Chưa biên soạn._`) chờ import từ nguồn PD/open (Wikisource, ctext, …).

Chi tiết: [`LICENSE`](LICENSE), [`sources/ATTRIBUTION.md`](sources/ATTRIBUTION.md).

```bash
./scripts/validate-books.sh
```

## CI/CD

Push `main` → GitHub Actions → Wiki incremental rebuild.

Xem [`docs/CICD.md`](docs/CICD.md).
"""


def write_attribution(book: dict) -> str:
    return f"""# Attribution & licenses

## 1. Original Chinese text

Public domain (PD-old). Work: **{book['title_original']}**.

Full-text import source is still TBD for most chapters (scaffold created {book['chapter_count']} files).

## 2. The Bronze Mirror

- Site: https://thebronzemirror.com/
- Content used: curated English translations / perspectives matched to this work (when available)
- License (stated on corpus): Original translations **CC BY-SA 4.0**; original Chinese texts public domain
- Local snapshot: parent factory `classical-texts/sources/bronzemirror-corpus.json`

When reusing Bronze Mirror English layers, retain attribution and share-alike under CC BY-SA 4.0.

## 3. Dao De Jing sibling

Pattern and Spec copied from https://github.com/the-quizzman/daodejing
"""


def write_license(book: dict) -> str:
    return f"""# Licenses

This repository aggregates public-domain and openly licensed texts for **{book['title']}**（{book['title_original']}）.

## Original Chinese text (Hán văn)

Public domain (PD-old). Classical work published millennia ago / author deceased > 100 years.

## The Bronze Mirror English excerpts (when present)

- Source: https://thebronzemirror.com/
- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
  https://creativecommons.org/licenses/by-sa/4.0/

You must retain attribution and share derivatives of the Bronze Mirror translation layer under CC BY-SA 4.0 (or compatible).

## Repo tooling / config

Scripts and CI workflows are for Quizzman Wiki integration.
"""


def map_bm_to_chapters(book: dict, corpus: dict) -> dict[int, list[dict]]:
    """Map Bronze Mirror passages onto chapter numbers when possible."""
    src = book.get("bronzemirror_source_zh")
    out: dict[int, list[dict]] = {}
    if not src:
        return out
    passages = [p for p in corpus.get("passages", []) if p.get("source_zh") == src]

    # Dao De Jing / numbered chapters: 第一章 → 1
    cn_num = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15, "十六": 16, "十七": 17,
        "十八": 18, "十九": 19, "二十": 20, "廿": 20,
        "廿二": 22, "廿二": 22, "三十": 30, "卅": 30,
        "三十三": 33, "四十四": 44, "四十六": 46, "六十三": 63, "六十七": 67, "七十六": 76,
        "九": 9, "八": 8, "一": 1,
    }

    for p in passages:
        placed = False
        sec = p.get("section_zh") or ""
        # Chapter N pattern
        m = re.search(r"第([一二三四五六七八九十百零〇两两\d]+)章", sec)
        if m:
            token = m.group(1)
            if token.isdigit():
                n = int(token)
            else:
                # simple map for common DDJ numbers present in corpus
                n = cn_num.get(token)
                if n is None:
                    # fallback parse
                    n = None
            if n:
                out.setdefault(n, []).append(p)
                placed = True

        # Lunyu book names / Sunzi pian → use chapter_titles reverse map
        titles = book.get("chapter_titles") or {}
        if not placed and titles:
            for num, title in titles.items():
                # rough: if section contains known title chars
                if title.replace(" ", "")[:2] in sec.replace(" ", "") or any(
                    ch in sec for ch in title if len(ch) > 0
                ):
                    # better: explicit known mappings
                    pass
            # explicit lunyu ids
            pid = p.get("id", "")
            if pid.startswith("lunyu-"):
                # lunyu-15-24 → chapter 15
                parts = pid.split("-")
                if len(parts) >= 2 and parts[1].isdigit():
                    out.setdefault(int(parts[1]), []).append(p)
                    placed = True
            if pid.startswith("sunzi") or "谋攻" in sec:
                # map mưu công → 3
                for num, title in titles.items():
                    if "Mưu" in title or "谋攻" in sec:
                        if title == "Mưu Công" or "谋攻" in sec:
                            out.setdefault(3, []).append(p)
                            placed = True
                            break

        # Yijing hexagrams → chapters 1 (乾), 2 (坤), etc.
        if not placed and book["id"] == "yijing":
            if "乾" in sec:
                out.setdefault(1, []).append(p); placed = True
            elif "坤" in sec:
                out.setdefault(2, []).append(p); placed = True
            elif "革" in sec:
                out.setdefault(49, []).append(p); placed = True
            elif "谦" in sec or "謙" in sec:
                out.setdefault(15, []).append(p); placed = True
            elif "系辞" in sec or "繫辭" in sec:
                # put Great Commentary excerpts in chapter 1 notes area via ch 1 append
                out.setdefault(1, []).append(p); placed = True

        if not placed and book["id"] == "zhuangzi":
            if "养生主" in sec or "庖丁" in sec:
                out.setdefault(3, []).append(p); placed = True  # 养生主 traditionally ch.3

        if not placed and book["id"] == "mengzi":
            if "公孙丑" in sec:
                out.setdefault(3, []).append(p); placed = True  # 公孙丑上 often book 3

        if not placed and book["id"] == "huangdineijing":
            out.setdefault(1, []).append(p); placed = True

        if not placed:
            out.setdefault(1, []).append(p)

    return out


def scaffold_book(book: dict, corpus: dict, force: bool = False) -> Path:
    dest = BOOKS_DIR / book["id"]
    if dest.exists() and not force:
        print(f"skip existing {dest}")
        return dest
    if dest.exists() and force:
        shutil.rmtree(dest)

    dest.mkdir(parents=True)
    (dest / "chapters").mkdir()
    (dest / "assets").mkdir()
    (dest / "docs").mkdir()
    (dest / "sources").mkdir()
    (dest / "scripts").mkdir()
    (dest / ".github" / "workflows").mkdir(parents=True)

    # docs / scripts from templates
    for name in [
        "CLASSICAL-TEXT-SPEC.md",
        "CHAPTER-TEMPLATE.md",
        "CICD.md",
        "YEU-CAU-KY-THUAC-WIKI.md",
    ]:
        src = TEMPLATES / name
        # fix typo in list
    shutil.copy2(TEMPLATES / "CLASSICAL-TEXT-SPEC.md", dest / "docs" / "CLASSICAL-TEXT-SPEC.md")
    shutil.copy2(TEMPLATES / "CHAPTER-TEMPLATE.md", dest / "docs" / "CHAPTER-TEMPLATE.md")
    shutil.copy2(TEMPLATES / "CICD.md", dest / "docs" / "CICD.md")
    shutil.copy2(TEMPLATES / "YEU-CAU-KY-THUAT-WIKI.md", dest / "docs" / "YEU-CAU-KY-THUAT-WIKI.md")
    shutil.copy2(TEMPLATES / "validate-books.sh", dest / "scripts" / "validate-books.sh")
    (dest / "scripts" / "validate-books.sh").chmod(0o755)
    shutil.copy2(TEMPLATES / "wiki-rebuild.yml", dest / ".github" / "workflows" / "wiki-rebuild.yml")
    shutil.copy2(TEMPLATES / ".gitignore", dest / ".gitignore")
    shutil.copy2(TEMPLATES / ".env.example", dest / ".env.example")

    (dest / "book.yaml").write_text(write_book_yaml(book), encoding="utf-8")
    (dest / "README.md").write_text(write_readme(book), encoding="utf-8")
    (dest / "LICENSE").write_text(write_license(book), encoding="utf-8")
    (dest / "sources" / "ATTRIBUTION.md").write_text(write_attribution(book), encoding="utf-8")

    bm_map = map_bm_to_chapters(book, corpus)
    titles = book.get("chapter_titles") or {}
    for n in range(1, int(book["chapter_count"]) + 1):
        title = titles.get(n) or titles.get(str(n)) or f"Chương {n}"
        text = chapter_stub(n, title, book, bm_map.get(n, []))
        (dest / "chapters" / f"{n:03d}.md").write_text(text, encoding="utf-8")

    # init git
    if not (dest / ".git").exists():
        run(["git", "init", "-b", "main"], cwd=dest)
        run(["git", "add", "."], cwd=dest)
        run(
            [
                "git",
                "commit",
                "-m",
                f"Initial {book['title_original']} Classical Text Spec v1 scaffold.",
            ],
            cwd=dest,
        )
    print(f"created {dest} ({book['chapter_count']} chapters)")
    return dest


def scaffold_collection(col: dict, force: bool = False) -> Path:
    dest = BOOKS_DIR / col["id"]
    if dest.exists() and not force:
        print(f"skip existing collection {dest}")
        return dest
    if dest.exists() and force:
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "docs").mkdir()
    shutil.copy2(TEMPLATES / "CLASSICAL-TEXT-SPEC.md", dest / "docs" / "CLASSICAL-TEXT-SPEC.md")
    book_like = {
        "id": col["id"],
        "title": col["title"],
        "title_original": col["title_original"],
        "author": "Bộ kinh điển",
        "category": col["category"],
        "chapter_count": 0,
        "book_path": f"/books/{col['id']}",
    }
    (dest / "README.md").write_text(
        write_readme(book_like, is_collection=True, members=col.get("members")),
        encoding="utf-8",
    )
    (dest / "book.yaml").write_text(
        f"""spec: classical-text/v1
id: {col['id']}
title: {col['title']}
title_original: {col['title_original']}
kind: collection
status: draft
members:
"""
        + "\n".join(f"  - {m}" for m in col.get("members", [])),
        encoding="utf-8",
    )
    (dest / ".gitignore").write_text((TEMPLATES / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    if not (dest / ".git").exists():
        run(["git", "init", "-b", "main"], cwd=dest)
        run(["git", "add", "."], cwd=dest)
        run(
            ["git", "commit", "-m", f"Initial {col['title_original']} collection index."],
            cwd=dest,
        )
    print(f"created collection {dest}")
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", help="Only these book/collection ids")
    ap.add_argument("--skip-git-commit", action="store_true")
    args = ap.parse_args()

    catalog = load_yaml(ROOT / "catalog.yaml")
    corpus = json.loads((ROOT / catalog["bronzemirror"]["corpus"]).read_text(encoding="utf-8"))

    only = set(args.only) if args.only else None

    for col in catalog.get("collections", []):
        if only and col["id"] not in only:
            continue
        scaffold_collection(col, force=args.force)

    for book in catalog.get("books", []):
        if only and book["id"] not in only:
            continue
        scaffold_book(book, corpus, force=args.force)

    # parent README
    lines = [
        "# Classical Texts (Quizzman)",
        "",
        "Factory + local clones theo [Classical Text Spec v1](templates/CLASSICAL-TEXT-SPEC.md).",
        "",
        "Nguồn curated: [The Bronze Mirror](https://thebronzemirror.com/) (CC BY-SA 4.0 EN excerpts).",
        "",
        "## Bộ sưu tập",
        "",
    ]
    for col in catalog.get("collections", []):
        lines.append(f"- [{col['title']} / {col['title_original']}](books/{col['id']}/) → " + ", ".join(f"`{m}`" for m in col["members"]))
    lines += ["", "## Sách", ""]
    by_cat: dict[str, list] = {}
    for b in catalog["books"]:
        by_cat.setdefault(b["category"], []).append(b)
    for cat, items in by_cat.items():
        lines.append(f"### {cat}")
        lines.append("")
        for b in items:
            lines.append(f"- [`{b['id']}`](books/{b['id']}/) — {b['title']}（{b['title_original']}） · {b['chapter_count']} ch")
        lines.append("")
    lines += [
        "## Đã có sẵn",
        "",
        "- [`daodejing`](../daodejing/) — 道德經 (repo riêng)",
        "",
        "## Bootstrap",
        "",
        "```bash",
        "pip3 install pyyaml",
        "python3 scripts/bootstrap.py",
        "python3 scripts/bootstrap.py --only sunzi lunyu",
        "```",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
