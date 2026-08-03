#!/usr/bin/env python3
"""Import PD classical Chinese text into Classical Text Spec chapter files.

Sources (public-domain classical Chinese):
- incrediblesound/classical-chinese (JS chapter dumps)
- nk2028/lzh-collection (白文)
- garychowcmu/daizhigev20 (殆知阁 txt)

Preserves existing Bronze Mirror English blocks when present.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
RAW = ROOT / "sources" / "raw"
PLACEHOLDER = "_Chưa biên soạn._"

CN_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15, "十六": 16,
    "十七": 17, "十八": 18, "十九": 19, "二十": 20, "廿": 20, "三十": 30, "卅": 30,
}


def clean_fullwidth_space(s: str) -> str:
    s = s.replace("\u3000", "").replace("\xa0", " ")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def normalize_punct(s: str) -> str:
    # Keep Chinese punctuation; ensure paragraphs separated by blank lines for long texts
    return clean_fullwidth_space(s)


def parse_js(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    payload = text.split("=", 1)[1].strip().rstrip(";")
    data = json.loads(payload)
    out = []
    for item in data["data"]:
        title = item["title"]
        body = "\n".join(item["body"]).strip()
        # JS sources often omit punctuation; keep as-is (白文-ish)
        out.append((title, normalize_punct(body)))
    return out


def split_by_headers(text: str, patterns: list[str]) -> list[tuple[str, str]]:
    """Split text into (title, body) using first matching regex list of header patterns."""
    text = text.replace("\r\n", "\n")
    # Build combined pattern
    joined = "|".join(f"(?:{p})" for p in patterns)
    rx = re.compile(rf"(?m)^[　\s]*(?:○)?(?:{joined})\s*$")
    matches = list(rx.finditer(text))
    if not matches:
        return []
    chapters = []
    for i, m in enumerate(matches):
        title = re.sub(r"^[　\s○]+", "", m.group(0)).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = normalize_punct(text[start:end])
        if body:
            chapters.append((title, body))
    return chapters


def parse_lunyu_style(text: str) -> list[tuple[str, str]]:
    # 学而第一 / 为政第二
    return split_by_headers(
        text,
        [
            r".{1,12}第[一二三四五六七八九十百零〇\d]+",
            r"卷[一二三四五六七八九十百\d]+[^\n]{0,20}",
        ],
    )


def parse_xiaojing(text: str) -> list[tuple[str, str]]:
    # ○开宗明义章第一  (sometimes inline)
    text = re.sub(r"○", "\n○", text)
    return split_by_headers(
        text,
        [r".{1,20}章第[一二三四五六七八九十]+"],
    )


def parse_yinfu(text: str) -> list[tuple[str, str]]:
    return split_by_headers(
        text,
        [
            r"神仙抱一演道章上",
            r"富国安民演法章中",
            r"强兵战胜演术章下",
            r".{0,20}章[上中下]",
        ],
    )


def parse_hanfeizi_baiwen(text: str) -> list[tuple[str, str]]:
    # 初見秦第一 / 存韓第二
    return split_by_headers(
        text,
        [r".{1,20}第[一二三四五六七八九十百零〇两兩\d]+"],
    )


def parse_liezi_baiwen(text: str) -> list[tuple[str, str]]:
    return split_by_headers(
        text,
        [r".{1,12}第[一二三四五六七八九十]+"],
    )


def parse_zhuangzi_daizhi(text: str) -> list[tuple[str, str]]:
    # 卷一上第一逍遥游 or 第X
    chs = split_by_headers(
        text,
        [
            r"卷.{0,6}第[一二三四五六七八九十]+.{0,20}",
            r"第[一二三四五六七八九十]+[^\n]{0,20}",
        ],
    )
    return chs


def parse_numbered_juan(text: str, expected: int | None = None) -> list[tuple[str, str]]:
    chs = split_by_headers(
        text,
        [
            r"卷[一二三四五六七八九十百千零〇\d]+[^\n]{0,40}",
            r"第[一二三四五六七八九十百千零〇\d]+[卷篇首章节部][^\n]{0,40}",
            r".{1,20}第[一二三四五六七八九十百\d]+",
        ],
    )
    if expected and len(chs) != expected:
        # dedupe TOC: if first half duplicates second, keep latter half
        if len(chs) == expected * 2:
            chs = chs[expected:]
        elif len(chs) > expected:
            # keep last expected unique by scanning from end of TOC-like repeats
            # Prefer chapters that have substantial body
            substantial = [c for c in chs if len(c[1]) > 80]
            if len(substantial) >= expected:
                chs = substantial[:expected] if len(substantial) == expected else substantial[-expected:]
    return chs


def parse_whole_as_chapters_by_blank(text: str, max_chapters: int) -> list[tuple[str, str]]:
    """Fallback: split long text into N roughly equal chapter chunks by paragraphs."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", normalize_punct(text)) if p.strip()]
    if not paras:
        body = normalize_punct(text)
        return [("全文", body)] if body else []
    # If few paragraphs, one chapter each up to max
    if len(paras) <= max_chapters:
        return [(f"第{i}段", p) for i, p in enumerate(paras, 1)]
    # bucket
    size = max(1, len(paras) // max_chapters)
    out = []
    for i in range(max_chapters):
        start = i * size
        end = (i + 1) * size if i < max_chapters - 1 else len(paras)
        chunk = "\n\n".join(paras[start:end]).strip()
        if chunk:
            out.append((f"第{i+1}部分", chunk))
    return out


def extract_existing_bm_english(chapter_text: str) -> str | None:
    m = re.search(
        r"(## English — The Bronze Mirror\n.*?)(?=\n# |\Z)",
        chapter_text,
        re.S,
    )
    return m.group(1).rstrip() if m else None


def extract_front_matter(chapter_text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", chapter_text, re.S)
    if not m:
        raise ValueError("missing front matter")
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields, m.group(2)


def write_chapter(
    path: Path,
    n: int,
    title: str,
    original: str,
    bm_english: str | None,
    source_note: str,
) -> None:
    literary = f"## Vietnamese\n\n{PLACEHOLDER}\n"
    if bm_english:
        literary += f"\n{bm_english}\n"
    else:
        literary += f"\n## English\n\n{PLACEHOLDER}\n"

    refs = f"""| Layer | Source | License |
| --- | --- | --- |
| Original Text (Hán văn) | {source_note} | PD-old |
| English excerpts (nếu có) | [The Bronze Mirror](https://thebronzemirror.com/) | CC BY-SA 4.0 |

Chi tiết: [`sources/ATTRIBUTION.md`](../sources/ATTRIBUTION.md).
"""
    content = f"""---
chapter: {n}
title: {title}
status: draft
version: 1
---

# Original Text

{original}

# Textual Variants

{PLACEHOLDER}

# Sino-Vietnamese

{PLACEHOLDER}

# Literal Translation

{PLACEHOLDER}

# Literary Translation

{literary.strip()}

# Commentary

{PLACEHOLDER}

# Textual Notes

{PLACEHOLDER}

# References

{refs.strip()}
"""
    lines = [ln.rstrip() for ln in content.replace("\r\n", "\n").split("\n")]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def resize_chapters(book_dir: Path, count: int) -> None:
    chapters = book_dir / "chapters"
    existing = sorted(chapters.glob("[0-9][0-9][0-9].md"))
    # remove extras
    for p in existing:
        n = int(p.stem)
        if n > count:
            p.unlink()
    # ensure stubs for missing
    for n in range(1, count + 1):
        p = chapters / f"{n:03d}.md"
        if not p.exists():
            write_chapter(p, n, f"Chương {n}", PLACEHOLDER, None, "TBD")


def update_book_yaml_count(book_dir: Path, count: int, source_url: str) -> None:
    path = book_dir / "book.yaml"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^chapter_count:\s*\d+\s*$", f"chapter_count: {count}", text, flags=re.M)
    if re.search(r"^sources:", text, re.M):
        text = re.sub(
            r"^sources:\n(?:  .*\n)*",
            f"sources:\n  primary: {source_url}\n  bronzemirror: https://thebronzemirror.com/\n",
            text,
            count=1,
            flags=re.M,
        )
    path.write_text(text, encoding="utf-8")


def update_attribution(book_dir: Path, note: str) -> None:
    (book_dir / "sources" / "ATTRIBUTION.md").write_text(
        f"""# Attribution & licenses

## Original Chinese text

{note}

Classical Chinese source text is public domain (PD-old).

## The Bronze Mirror

- Site: https://thebronzemirror.com/
- English curated excerpts retained under **CC BY-SA 4.0** when present in chapters.

## Refresh

Imported by `classical-texts/scripts/import_pd_text.py`.
""",
        encoding="utf-8",
    )


BOOK_SOURCES: dict[str, dict] = {
    # structured JS
    "lunyu": {
        "file": "lunyu.js",
        "parser": "js",
        "url": "https://github.com/incrediblesound/classical-chinese",
        "note": "incrediblesound/classical-chinese texts/lunyu.js (PD classical Chinese)",
    },
    "sunzi": {
        "file": "sunzi.js",
        "parser": "js",
        "url": "https://github.com/incrediblesound/classical-chinese",
        "note": "incrediblesound/classical-chinese texts/sunzi.js",
        "title_map": {
            "始计": "Thủy Kế",
            "作战": "Tác Chiến",
            "谋攻": "Mưu Công",
            "军形": "Quân Hình",
            "兵势": "Binh Thế",
            "虚实": "Hư Thực",
            "军争": "Quân Tranh",
            "九变": "Cửu Biến",
            "行军": "Hành Quân",
            "地形": "Địa Hình",
            "九地": "Cửu Địa",
            "火攻": "Hỏa Công",
            "用间": "Dụng Gian",
        },
    },
    "zhuangzi": {
        "file": "zhuangzi.js",
        "parser": "js",
        "url": "https://github.com/incrediblesound/classical-chinese",
        "note": "incrediblesound/classical-chinese texts/zhuangzi.js",
    },
    # 白文
    "liezi": {
        "file": "liezi-baiwen.txt",
        "parser": "liezi_baiwen",
        "url": "https://github.com/nk2028/lzh-collection",
        "note": "nk2028/lzh-collection 列子白文.txt",
    },
    "hanfeizi": {
        "file": "hanfeizi-baiwen.txt",
        "parser": "hanfeizi_baiwen",
        "url": "https://github.com/nk2028/lzh-collection",
        "note": "nk2028/lzh-collection 韓非子白文.txt",
    },
    "mozi": {
        "file": "mozi-baiwen.txt",
        "parser": "hanfeizi_baiwen",
        "url": "https://github.com/nk2028/lzh-collection",
        "note": "nk2028/lzh-collection 墨子白文.txt",
    },
    "guanzi": {
        "file": "guanzi-daizhi.txt",
        "parser": "guanzi",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 子藏/法家/管子.txt",
    },
    # daizhige
    "xiaojing": {
        "file": "孝经.txt",
        "parser": "xiaojing",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/孝经/孝经.txt",
    },
    "erya": {
        "file": "尔雅.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/小学/尔雅.txt",
    },
    "daxue": {
        "file": "大学.txt",
        "parser": "single_or_paras",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/四书/大学.txt",
        "force_count": 1,
    },
    "zhongyong": {
        "file": "中庸.txt",
        "parser": "single_or_paras",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/四书/中庸.txt",
        "force_count": 1,
    },
    "mengzi": {
        "file": "mengzi.js",
        "parser": "mengzi_js",
        "url": "https://github.com/incrediblesound/classical-chinese",
        "note": "incrediblesound mengzi.js + daizhige 尽心下",
        "expected": 14,
    },
    "yinfujing": {
        "file": "yinfu-daizhi.txt",
        "parser": "yinfu",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 黄帝阴符经.txt",
    },
    "wenzi": {
        "file": "wenzi-daizhi.txt",
        "parser": "wenzi",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 道藏/藏外/文子.txt",
    },
    "wuzi": {
        "file": "wuzi-daizhi.txt",
        "parser": "wuzi",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 子藏/兵家/吴子.txt",
    },
    "liutao": {
        "file": "liutao-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 子藏/兵家/六韬.txt",
    },
    "sanlue": {
        "file": "sanlue-daizhi.txt",
        "parser": "sanlue",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 子藏/兵家/黄石公三略.txt",
    },
    "shangjunshu": {
        "file": "shangjunshu-daizhi.txt",
        "parser": "shangjun",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 子藏/法家/商子.txt",
    },
    "gongyang": {
        "file": "gongyang-daizhi.txt",
        "parser": "chunqiu",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/春秋/春秋公羊传.txt",
    },
    "guliang": {
        "file": "guliang-daizhi.txt",
        "parser": "chunqiu",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/春秋/春秋谷梁传.txt",
    },
    "jinguiyaolue": {
        "file": "jinguiyaolue-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 医藏/金匮要略方论.txt",
    },
    "yijing": {
        "file": "yijing-daizhi.txt",
        "parser": "yijing",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 易藏/易经/周易.txt",
        "expected": 64,
    },
    "shangshu": {
        "file": "shangshu-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/尚书/尚书.txt",
    },
    "shijing": {
        "file": "shijing-daizhi.txt",
        "parser": "shijing",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/诗经/诗经.txt",
    },
    "liji": {
        "file": "liji-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/礼经/礼记.txt",
    },
    "zhouli": {
        "file": "zhouli-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/礼经/周礼.txt",
    },
    "yili": {
        "file": "yili-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/礼经/仪礼.txt",
    },
    "chuci": {
        "file": "chuci-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 诗藏/楚辞/楚辞.txt",
    },
    "wenxindiaolong": {
        "file": "wenxindiaolong-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 集藏/文评/文心雕龙.txt",
    },
    "guwenguanzhi": {
        "file": "guwenguanzhi-daizhi.txt",
        "parser": "guwen",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 集藏/文总集/古文观止.txt",
    },
    "shanghanlun": {
        "file": "shanghanlun-daizhi.txt",
        "parser": "lunyu_style",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 医藏/伤寒论.txt",
    },
    "shiji": {
        "file": "shiji-daizhi.txt",
        "parser": "shiji",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 史藏/正史/史记.txt",
        "expected": 130,
    },
    "hanshu": {
        "file": "hanshu-daizhi.txt",
        "parser": "shiji",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 史藏/正史/汉书.txt",
    },
    "houhanshu": {
        "file": "houhanshu-daizhi.txt",
        "parser": "shiji",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 史藏/正史/后汉书.txt",
    },
    "sanguozhi": {
        "file": "sanguozhi-daizhi.txt",
        "parser": "shiji",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 史藏/正史/三国志.txt",
    },
    "zizhitongjian": {
        "file": "zizhitongjian-daizhi.txt",
        "parser": "tongjian",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 史藏/编年/资治通鉴.txt",
    },
    "huangdineijing": {
        "file": "neijing-combined",
        "parser": "neijing",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 黄帝内经素问 + 灵枢",
    },
    "chunqiu": {
        "file": "chunqiu-zuozhuan.txt",
        "parser": "chunqiu",
        "url": "https://github.com/garychowcmu/daizhigev20",
        "note": "daizhigev20 儒藏/春秋/春秋左传.txt (12 Công công)",
    },
}


def parse_source(cfg: dict) -> list[tuple[str, str]]:
    parser = cfg["parser"]
    if parser == "neijing":
        su = (RAW / "neijing-suwen.txt").read_text(encoding="utf-8", errors="replace")
        ling = (RAW / "neijing-lingshu.txt").read_text(encoding="utf-8", errors="replace")
        a = parse_numbered_juan(su)
        b = parse_numbered_juan(ling)
        # label
        a = [(f"素问·{t}", body) for t, body in a]
        b = [(f"灵枢·{t}", body) for t, body in b]
        return a + b

    path = RAW / cfg["file"]
    text = path.read_text(encoding="utf-8", errors="replace")

    if parser == "js":
        return parse_js(path)
    if parser == "mengzi_js":
        chs = parse_js(path)
        dz = (RAW / "孟子.txt").read_text(encoding="utf-8", errors="replace")
        m = re.search(r"(?m)^[　\s]*卷十四 尽心下\s*$([\s\S]*)$", dz)
        if m and len(chs) == 13:
            chs.append(("尽心章句下", normalize_punct(m.group(1))))
        return chs
    if parser == "wenzi":
        titles = [
            "道原", "精诚", "九守", "符言", "道德", "上德",
            "微明", "自然", "下德", "上仁", "上义", "上礼",
        ]
        positions = []
        for title in titles:
            idx = text.find(title, 600)
            if idx >= 0:
                positions.append((idx, title))
        positions.sort()
        out = []
        for i, (pos, title) in enumerate(positions):
            end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            body = normalize_punct(text[pos:end])
            body = re.sub(rf"^{re.escape(title)}\s*", "", body)
            if len(body) > 40:
                out.append((title, body))
        return out
    if parser == "xiaojing":
        return parse_xiaojing(text)
    if parser == "yinfu":
        return parse_yinfu(text)
    if parser == "liezi_baiwen":
        return parse_liezi_baiwen(text)
    if parser == "hanfeizi_baiwen":
        return parse_hanfeizi_baiwen(text)
    if parser == "lunyu_style":
        chs = parse_lunyu_style(text)
        chs = [(t, b) for t, b in chs if len(b) > 40]
        return chs
    if parser == "mengzi":
        chs = split_by_headers(text, [r"卷[一二三四五六七八九十]+[^\n]{0,30}"])
        chs = [(t, b) for t, b in chs if len(b) > 80]
        if len(chs) >= 28:
            chs = chs[-14:]
        return chs[:14]
    if parser == "single_or_paras":
        body = normalize_punct(re.sub(r"^中庸\s*", "", text))
        body = normalize_punct(re.sub(r"^大学\s*", "", body))
        lines = [ln for ln in body.splitlines() if ln.strip()]
        body = "\n".join(lines)
        return [("全文", body)]
    if parser == "wuzi":
        text2 = re.sub(r"^.*?(?=图国|呉起初见|吴起初见)", "", text, count=1, flags=re.S)
        chs = split_by_headers(
            text2 or text,
            [r"图国", r"料敌", r"治兵", r"论将", r"应变", r"励士", r".{1,10}第[一二三四五六]+"],
        )
        return [(t, b) for t, b in chs if len(b) > 40][:6] or parse_whole_as_chapters_by_blank(text, 6)
    if parser == "sanlue":
        chs = split_by_headers(
            text,
            [
                r"黄石公三畧卷上",
                r"黄石公三畧卷中",
                r"黄石公三畧卷下",
            ],
        )
        chs = [(t, b) for t, b in chs if len(b) > 80]
        if len(chs) >= 6:
            chs = chs[0::2]
        if len(chs) >= 3:
            return [("上略", chs[0][1]), ("中略", chs[1][1]), ("下略", chs[2][1])]
        return chs[:3] or parse_whole_as_chapters_by_blank(text, 3)
    if parser == "shangjun":
        chs = split_by_headers(text, [r".{1,12}第[一二三四五六七八九十百]+(?:亡佚)?"])
        return [(t, b) for t, b in chs if len(b) > 20 and "提要" not in t]
    if parser == "guanzi":
        chs = split_by_headers(text, [r".{1,16}第[一二三四五六七八九十百]+"])
        out = []
        for t, b in chs:
            if re.fullmatch(r"卷[一二三四五六七八九十百\d]+", t.strip()):
                continue
            if len(b) < 40:
                continue
            out.append((t, b))
        if len(out) > 100:
            out = out[len(out) // 2 :]
        return out
    if parser == "yijing":
        # 64 hexagrams often titled 乾 / 坤 or 第一
        chs = split_by_headers(
            text,
            [
                r"第[一二三四五六七八九十百零〇\d]+卦[^\n]{0,20}",
                r"[乾坤屯蒙需讼师比小畜履泰否同人大有谦豫随蛊临观噬嗑贲剥复无妄大畜颐大过坎离咸恒遁大壮晋明夷家人睽蹇解损益夬姤萃升困井革鼎震艮渐归妹丰旅巽兑涣节中孚小过既济未济][^\n]{0,10}",
            ],
        )
        chs = [(t, b) for t, b in chs if len(b) > 20]
        if len(chs) >= 64:
            return chs[:64]
        return chs or parse_whole_as_chapters_by_blank(text, 64)
    if parser == "shijing":
        # poems often 国风/小雅 headers + poem titles; split by 《 or numbered
        chs = split_by_headers(
            text,
            [
                r".{1,20}第[一二三四五六七八九十百\d]+",
                r"「[^」]{1,20}」",
                r"《[^》]{1,20}》",
            ],
        )
        chs = [(t, b) for t, b in chs if len(b) > 10]
        return chs
    if parser == "guwen":
        chs = split_by_headers(
            text,
            [
                r"卷[一二三四五六七八九十百\d]+[^\n]{0,30}",
                r".{1,30}",
            ],
        )
        # too greedy — use volume splits primarily
        chs = split_by_headers(text, [r"卷[一二三四五六七八九十百\d]+[^\n]{0,40}"])
        chs = [(t, b) for t, b in chs if len(b) > 80]
        return chs
    if parser == "shiji":
        chs = split_by_headers(
            text,
            [
                r".{0,20}第[一二三四五六七八九十百千零〇两兩\d]+[^\n]{0,30}",
                r"卷[一二三四五六七八九十百千\d]+[^\n]{0,40}",
            ],
        )
        chs = [(t, b) for t, b in chs if len(b) > 100]
        return chs
    if parser == "tongjian":
        chs = split_by_headers(
            text,
            [r"卷[一二三四五六七八九十百千零〇\d]+[^\n]{0,40}"],
        )
        chs = [(t, b) for t, b in chs if len(b) > 100]
        return chs
    if parser == "chunqiu":
        # 隐公/桓公 ... 12 dukes as chapters
        dukes = ["隐公", "桓公", "庄公", "闵公", "僖公", "文公", "宣公", "成公", "襄公", "昭公", "定公", "哀公"]
        parts = []
        for i, d in enumerate(dukes):
            # find occurrences
            pass
        # split on duke headers
        rx = re.compile(r"(?m)^[　\s]*((?:隐|桓|庄|閔|闵|僖|文|宣|成|襄|昭|定|哀)公)[^\n]{0,20}$")
        matches = list(rx.finditer(text))
        if not matches:
            # try without line anchors
            rx = re.compile(r"(隐公|桓公|庄公|闵公|僖公|文公|宣公|成公|襄公|昭公|定公|哀公)")
            matches = list(rx.finditer(text))
            # take first of each
            seen = set()
            filtered = []
            for m in matches:
                if m.group(1) not in seen:
                    seen.add(m.group(1))
                    filtered.append(m)
            matches = filtered
        for i, m in enumerate(matches):
            title = m.group(1)
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = normalize_punct(text[start:end])
            parts.append((title, body))
        return parts[:12]

    raise ValueError(f"unknown parser {parser}")


def import_book(book_id: str) -> dict:
    cfg = BOOK_SOURCES[book_id]
    book_dir = BOOKS / book_id
    if not book_dir.exists():
        raise FileNotFoundError(book_dir)

    chapters = parse_source(cfg)
    if not chapters:
        raise RuntimeError(f"{book_id}: parsed 0 chapters")

    force = cfg.get("force_count")
    if force:
        chapters = chapters[:force]

    expected = cfg.get("expected")
    if expected and len(chapters) > expected:
        chapters = chapters[:expected]

    title_map = cfg.get("title_map") or {}

    # preserve BM english from existing files by chapter number
    bm_by_n: dict[int, str] = {}
    for p in (book_dir / "chapters").glob("[0-9][0-9][0-9].md"):
        raw = p.read_text(encoding="utf-8")
        bm = extract_existing_bm_english(raw)
        if bm:
            bm_by_n[int(p.stem)] = bm

    count = len(chapters)
    resize_chapters(book_dir, count)

    for i, (title_zh, body) in enumerate(chapters, start=1):
        title = title_map.get(title_zh) or title_zh
        # Prefer Vietnamese titles already in catalog for known books via existing fm
        existing = book_dir / "chapters" / f"{i:03d}.md"
        if existing.exists():
            try:
                fm, _ = extract_front_matter(existing.read_text(encoding="utf-8"))
                old_title = fm.get("title", "")
                if old_title and old_title not in ("Chương " + str(i),) and not re.search(r"[\u4e00-\u9fff]", old_title):
                    # keep Vietnamese title if present
                    title = old_title
            except Exception:
                pass
        write_chapter(
            existing,
            i,
            title,
            body,
            bm_by_n.get(i),
            cfg["note"],
        )

    update_book_yaml_count(book_dir, count, cfg["url"])
    update_attribution(book_dir, f"- {cfg['note']}\n- URL: {cfg['url']}")

    # copy raw snapshot into book sources
    if cfg["file"] != "neijing-combined":
        src = RAW / cfg["file"]
        if src.exists():
            dest = book_dir / "sources" / src.name
            dest.write_bytes(src.read_bytes())
    else:
        for name in ("neijing-suwen.txt", "neijing-lingshu.txt"):
            src = RAW / name
            if src.exists():
                (book_dir / "sources" / name).write_bytes(src.read_bytes())

    return {"id": book_id, "chapters": count, "sample_title": chapters[0][0]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("books", nargs="*", help="Book ids (default: all mapped)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        print("\n".join(BOOK_SOURCES))
        return
    ids = args.books or list(BOOK_SOURCES)
    results = []
    for bid in ids:
        if bid not in BOOK_SOURCES:
            print(f"SKIP unknown {bid}")
            continue
        try:
            info = import_book(bid)
            print(f"OK {bid}: {info['chapters']} chapters ({info['sample_title']})")
            results.append({**info, "ok": True})
        except Exception as e:
            print(f"FAIL {bid}: {e}")
            results.append({"id": bid, "ok": False, "error": str(e)})
    out = ROOT / "sources" / "import-results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"Done {ok}/{len(results)} -> {out}")


if __name__ == "__main__":
    main()
