# Yêu cầu kỹ thuật — Đồng bộ GitHub → Quizzman Wiki (Đạo Đức Kinh)

**Người gửi:** Content / Platform (repo `daodejing`)  
**Người nhận:** Đội Wiki (Quizzman)  
**Ưu tiên:** P0 — chặn publish sách  
**Ngày:** 2026-08-03  
**Repo nguồn:** `the-quizzman/daodejing` (private/public — sẽ push sau khi webhook sẵn sàng)  
**Môi trường đích:** `https://wiki.quizzman.com`

---

## 1. Mục tiêu

Wiki **không** là nơi lưu nội dung cuối cùng. GitHub là **source of truth**. Wiki chỉ là bản render + search index từ Markdown trong repo.

Mỗi lần `git push` lên `main`, server wiki phải:

1. Nhận sự kiện (webhook hoặc API rebuild)
2. `git pull` repo content
3. **Incremental rebuild** các file thay đổi
4. Cập nhật DB + search index
5. Invalidate cache
6. Nội dung live trong vài giây

---

## 2. Phạm vi

### Trong phạm vi (MVP)

| # | Hạng mục |
| --- | --- |
| A | Endpoint GitHub Webhook |
| B | Endpoint rebuild thủ công / Actions |
| C | Incremental builder theo danh sách file |
| D | Clone/pull repo `daodejing` trên server |
| E | Parse Markdown + front matter → trang wiki |
| F | Cập nhật search index cho các trang rebuild |
| G | Invalidate cache theo slug/chương |

### Ngoài phạm vi (pha sau)

- Biên tập WYSIWYG trên wiki ghi ngược về GitHub
- Preview PR / deploy preview theo branch
- Đa repo sách (sau khi mẫu `daodejing` ổn định)

---

## 3. Kiến trúc mong muốn

```text
Editor (Cursor/VS Code)
        │
        ▼
Git repo local  ──git push──►  GitHub (source of truth)
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
         POST /api/github/webhook    GitHub Actions (dự phòng)
         (push event + signature)    POST /api/wiki/rebuild
                    │                       │
                    └───────────┬───────────┘
                                ▼
                     Quizzman Wiki Server
                                │
                    verify auth / signature
                                │
                           git pull
                                │
                    Incremental Builder
                     (chỉ file modified)
                                │
              ┌─────────┬───────┴────────┐
              ▼         ▼                ▼
           Parser    SQLite/PG      Search Index
              │         │                │
              └─────────┴───────┬────────┘
                                ▼
                         Cache invalidate
                                ▼
                            Wiki Live
```

---

## 4. API yêu cầu

### 4.1. `POST /api/github/webhook` (cách chính — bắt buộc)

Nhận webhook chuẩn GitHub `push`.

**Headers (GitHub gửi):**

| Header | Mô tả |
| --- | --- |
| `X-Hub-Signature-256` | HMAC SHA-256 body với `GITHUB_WEBHOOK_SECRET` |
| `X-GitHub-Event` | Chỉ xử lý `push` (các event khác → `202` ignore) |
| `X-GitHub-Delivery` | Idempotency key |

**Hành vi:**

1. Verify signature — sai → `401`
2. Chỉ nhận branch `refs/heads/main` — branch khác → `202` + no-op
3. Chỉ nhận repo đã whitelist (ban đầu: `the-quizzman/daodejing`)
4. Từ payload `commits[].added|modified|removed`, gom danh sách path dưới `chapters/` và `book.yaml`
5. `git fetch && git pull --ff-only` tại thư mục clone trên server
6. Incremental rebuild danh sách file
7. Trả về kết quả

**Response thành công (ví dụ):**

```json
{
  "ok": true,
  "mode": "incremental",
  "pulled": true,
  "sha": "abc123…",
  "rebuilt": ["chapters/023.md"],
  "removed": [],
  "duration_ms": 842
}
```

**SLA:** p95 < 10s cho ≤ 20 file thay đổi mỗi push.

---

### 4.2. `POST /api/wiki/rebuild` (dự phòng Actions + thủ công — bắt buộc)

Dùng khi webhook lỗi hoặc gọi từ GitHub Actions / script local.

**Auth:** `Authorization: Bearer <WIKI_REBUILD_TOKEN>`

**Request body:**

```json
{
  "repository": "the-quizzman/daodejing",
  "ref": "refs/heads/main",
  "sha": "<commit sha>",
  "mode": "incremental",
  "modified": [
    "chapters/023.md"
  ]
}
```

| Field | Type | Bắt buộc | Mô tả |
| --- | --- | --- | --- |
| `repository` | string | yes | Phải nằm trong whitelist |
| `ref` | string | yes | Chỉ `main` / `refs/heads/main` ở MVP |
| `sha` | string | yes | Commit cần sync tới |
| `mode` | `incremental` \| `full` \| `manual` | yes | `full` = rebuild mọi chương trong repo |
| `modified` | string[] | yes nếu incremental | Path relative từ root repo |

**Hành vi:**

1. Verify bearer token
2. `git pull` (hoặc `git checkout` đúng `sha` nếu pull chưa tới)
3. Nếu `mode=full` → rebuild toàn bộ sách trong repo
4. Nếu `mode=incremental` → chỉ rebuild `modified` (+ xử lý file bị xóa nếu có thêm field `removed` — khuyến nghị)
5. Cập nhật index + cache

**Response lỗi chuẩn:**

| HTTP | Khi nào |
| --- | --- |
| 401 | Token/signature sai |
| 403 | Repo không whitelist |
| 409 | Git conflict / không ff-only |
| 422 | Payload thiếu field / path ngoài `chapters/` |
| 500 | Build/parser lỗi |

---

## 5. Quy ước nội dung (content contract)

Repo layout:

```text
book.yaml
books/
  dao-duc-kinh/
    _meta.yml
    01.md … 81.md
```

### 5.1. Front matter chương

```yaml
---
chapter: 23
title: Hi ngôn tự nhiên
slug: "23"
book: dao-duc-kinh
han_title: "希言自然"
---
```

### 5.2. URL publish mong muốn

```text
https://wiki.quizzman.com/books/dao-duc-kinh
https://wiki.quizzman.com/chapters/23
```

### 5.3. Mapping path → trang

| Path | Hành động |
| --- | --- |
| `books/<book>/<nn>.md` | Upsert trang chương |
| `books/<book>/_meta.yml` | Upsert metadata sách |
| `book.yaml` | Reload cấu hình nguồn |
| Path bị xóa trong push | Unpublish / soft-delete trang tương ứng |

### 5.4. Incremental — bắt buộc

Ví dụ chỉ sửa `chapters/023.md` → **chỉ rebuild Chương 23**.  
Không được full rebuild 81 chương (và tương lai hàng nghìn trang) cho mỗi push nhỏ.

---

## 6. Bảo mật & vận hành

| Hạng mục | Yêu cầu |
| --- | --- |
| Webhook secret | HMAC `sha256=` bắt buộc; secret rotate được |
| Rebuild token | Bearer riêng, không dùng webhook secret |
| Whitelist repo | Config server-side, không tin `repository` trong body một mình |
| Git trên server | Deploy key read-only hoặc machine user; chỉ `ff-only` |
| Log | Mỗi delivery: `delivery_id`, `sha`, `modified[]`, `duration_ms`, `ok/error` |
| Idempotency | Cùng `X-GitHub-Delivery` hoặc cùng `(sha, modified)` không double-apply gây lỗi |
| Rate | Hàng đợi serialize rebuild theo repo (tránh 2 pull song song) |

---

## 7. Cấu hình phía Content (đã chuẩn bị)

Repo local đã có:

- 81 file chương + `_meta.yml`
- `book.yaml`
- GitHub Action: `.github/workflows/wiki-rebuild.yml` → gọi `/api/wiki/rebuild`
- Script local: `scripts/trigger-rebuild.sh`

**Secrets Content sẽ set trên GitHub sau khi Wiki cấp:**

| Secret / Var | Ai cấp |
| --- | --- |
| `GITHUB_WEBHOOK_SECRET` | Wiki cấp → Content dán vào GitHub Webhook |
| `WIKI_REBUILD_TOKEN` | Wiki cấp → Content dán vào Actions secrets |
| Deploy key / clone URL | Wiki giữ trên server; Content invite machine user nếu cần |

---

## 8. Tiêu chí nghiệm thu (Acceptance)

1. Push sửa `chapters/023.md` → trang `/chapters/23` đổi nội dung trong **≤ 15s** (p95 ≤ 10s).
2. Các chương khác **không** đổi `updated_at` / không rebuild lại.
3. Webhook signature sai → 401, không pull.
4. Token rebuild sai → 401.
5. `mode=full` (Actions `workflow_dispatch`) rebuild cả 81 chương thành công.
6. Xóa một file chương + push → trang tương ứng unpublish hoặc 404 theo policy đội Wiki (cần confirm).
7. Search tìm được đoạn text mới sau rebuild chương đó.
8. Có log/metrics đủ để debug 1 delivery bất kỳ.

---

## 9. Việc cần đội Wiki trả lời / giao

| # | Deliverable | Owner | Deadline đề xuất |
| --- | --- | --- | --- |
| 1 | Implement `POST /api/github/webhook` | Wiki | T+3 |
| 2 | Implement `POST /api/wiki/rebuild` | Wiki | T+3 |
| 3 | Clone repo trên server + whitelist | Wiki | T+3 |
| 4 | Cấp `GITHUB_WEBHOOK_SECRET` + `WIKI_REBUILD_TOKEN` (staging + prod) | Wiki | T+3 |
| 5 | Confirm URL schema `/chapters/:slug` | Wiki | T+1 |
| 6 | Confirm policy xóa file (404 vs soft-delete) | Wiki | T+1 |
| 7 | Staging URL để Content test trước prod | Wiki | T+3 |
| 8 | Runbook: rotate secret, xem log rebuild | Wiki | T+5 |

**Phía Content (sau khi nhận secret):**

1. Push repo `the-quizzman/daodejing`
2. Đăng ký webhook GitHub
3. Set Actions secret
4. Chạy acceptance test mục 8

---

## 10. Open questions

1. Wiki dùng SQLite hay Postgres cho trang sách?
2. Search engine hiện tại là gì (Meilisearch / Postgres FTS / khác)? Incremental update API ra sao?
3. Có cần verify `sha` khớp remote trước khi build không?
4. Staging domain? (`staging.wiki.quizzman.com`?)
5. Có hỗ trợ `removed[]` trong body rebuild ngay MVP không?

---

## 11. Liên hệ & tài liệu kèm

- Kiến trúc ngắn: `docs/CICD.md`
- Config nguồn: `book.yaml`
- Mẫu chương: `chapters/023.md`
- Workflow dự phòng: `.github/workflows/wiki-rebuild.yml`

**Payload mẫu Actions sẽ gửi:**

```json
{
  "repository": "the-quizzman/daodejing",
  "ref": "refs/heads/main",
  "sha": "<commit>",
  "mode": "incremental",
  "modified": ["chapters/023.md"]
}
```

Vui lòng confirm endpoint path cuối cùng nếu khác `/api/github/webhook` và `/api/wiki/rebuild` để Content chỉnh workflow trước lần push đầu.
