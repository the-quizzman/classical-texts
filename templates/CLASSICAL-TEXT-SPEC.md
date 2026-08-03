# Quizzman Classical Text Specification v1.0

## Objective

Design the Markdown specification for Quizzman Classical Text projects.

This specification will be used for:

* Dao De Jing
* Zhuangzi
* Liji
* Lunyu
* Liezi
* Future classical works

The specification must prioritize **human editing**, not machine optimization.

---

## Core Principles

1. Markdown is the source of truth.
2. Git is the version control system.
3. One chapter = One Markdown file.
4. Everything related to a chapter must exist in the same file.
5. Minimize file fragmentation.
6. Editing experience is more important than parser convenience.
7. Plain text first.

---

## Directory Structure

```text
repository/

README.md
LICENSE

book.yaml

chapters/
  001.md
  002.md
  003.md
  ...
  081.md

assets/

docs/
```

Optional (not part of the chapter editing surface):

```text
sources/          # raw crawl snapshots, attribution archives
scripts/          # import / validate helpers
.github/          # CI (rebuild wiki, lint)
```

**Do NOT** split translation, notes, commentary or references into different folders.

---

## File Layout

Every chapter must be self-contained.

Canonical section order (H1 headings, exact titles):

```markdown
---
chapter: 1
title: …
status: draft
version: 1
---

# Original Text

…

# Textual Variants

…

# Sino-Vietnamese

…

# Literal Translation

…

# Literary Translation

…

# Commentary

…

# Textual Notes

…

# References

…
```

Everything required to edit the chapter must be visible in one file.

No external lookup should be required during normal editing.

### Section semantics

| Section | Purpose |
| --- | --- |
| Original Text | Classical source text (e.g. Hán văn) |
| Textual Variants | Manuscript / edition differences (Mawangdui, Guodian, Wang Bi, …) |
| Sino-Vietnamese | Phiên âm Hán-Việt |
| Literal Translation | Word-near / gloss translation |
| Literary Translation | Fluent target-language rendering (may include `##` language subsections) |
| Commentary | Commentarial reading, teaching notes |
| Textual Notes | Philological notes tied to lemmas / lines |
| References | Sources, editions, licenses, citations |

Empty sections remain present as headings so editors always see the full scaffold.

---

## Metadata

Keep front matter minimal.

Allowed fields:

* `chapter` — integer chapter number (1-based)
* `title` — short human title for the chapter
* `status` — `draft` \| `review` \| `stable`
* `version` — integer editorial revision of this chapter file

Do not duplicate information (no `slug`, `book`, `han_title`, license maps in front matter — those belong in `book.yaml` or `# References`).

Filename rule: zero-padded to 3 digits → `001.md` … `081.md` matching `chapter`.

---

## Editing Philosophy

The editor should never need to open multiple files to edit one chapter.

The chapter file should contain:

* original text
* variants
* translation
* commentary
* references
* editorial notes

This is mandatory.

---

## Markdown Rules

* UTF-8
* LF line endings
* No tabs
* No trailing spaces
* Standard Markdown
* YAML front matter only

No JSON.

No XML.

No proprietary syntax.

Standard Markdown subsections (`##`, lists, tables, blockquotes) inside a section are allowed when they help humans — e.g. multiple literary languages under `# Literary Translation`.

---

## Book configuration (`book.yaml`)

Book-level metadata lives in one file at repo root. Example:

```yaml
spec: classical-text/v1
id: daodejing
title: Đạo Đức Kinh
title_original: 道德經
author: Lão Tử
language: vi
chapter_count: 81
chapter_glob: chapters/*.md
status: draft
licenses:
  original: PD-old
  vi_wikisource: CC-BY-SA-4.0
  en_legge: public-domain-usa
publish:
  base_url: https://wiki.quizzman.com
  book_path: /books/dao-duc-kinh
```

Renderers (Wiki, ebook, HTML, PDF, DOCX, API) read `book.yaml` + `chapters/*.md`. They must not require authors to change chapter Markdown when adding a new output format.

---

## Git Workflow

```text
Open chapter
    ↓
Edit
    ↓
Save
    ↓
git add .
    ↓
git commit
    ↓
git push
```

No manual build.

No manual export.

CI / webhook may rebuild derived views after push. Derived views are never the source of truth.

---

## Future Compatibility

The specification must support future rendering into:

* Wiki
* Ebook
* HTML
* PDF
* DOCX
* API

without changing the Markdown files.

Markdown remains the canonical source forever.

---

## Important Constraint

Optimize for:

* readability
* maintainability
* Git diff
* long-term preservation
* academic editing

Do **NOT** optimize for parser simplicity at the expense of editing experience.

The specification should remain practical for projects maintained over decades.

---

## Validation (normative for Quizzman repos)

A chapter file is valid when:

1. Front matter contains only allowed fields; `chapter`, `title`, `status`, `version` are present.
2. Filename is `{chapter:03d}.md`.
3. All eight canonical H1 sections exist, in order.
4. File is UTF-8, LF, no tab characters.
5. No trailing whitespace on any line.

Reference checker: `scripts/validate-books.sh`.

---

## Adoption map

| Work | Repo (planned) | Spec |
| --- | --- | --- |
| Dao De Jing | `daodejing` | v1.0 (this repo) |
| Zhuangzi | TBD | v1.0 |
| Liji | TBD | v1.0 |
| Lunyu | TBD | v1.0 |
| Liezi | TBD | v1.0 |
