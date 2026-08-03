# CI/CD — Đạo Đức Kinh → Quizzman Wiki

## Nguyên tắc

| Vai trò | Hệ thống |
| --- | --- |
| Source of truth | GitHub repo này |
| Bản render | Quizzman Wiki |
| Trigger chính | GitHub Webhook |
| Trigger dự phòng | GitHub Actions → `POST /api/wiki/rebuild` |

Không sửa nội dung trực tiếp trên wiki. Chỉ sửa Markdown → commit → push.

## Kiến trúc

```text
Repo (Markdown)
        ↓
Webhook / Actions
        ↓
Incremental Builder
        ↓
Parser
        ↓
Search Index
        ↓
Wiki Live
```

## Incremental rebuild

Payload ví dụ khi sửa chương 23:

```json
{
  "repository": "the-quizzman/daodejing",
  "ref": "refs/heads/main",
  "sha": "abc123…",
  "mode": "incremental",
  "modified": [
    "chapters/023.md"
  ]
}
```

Server chỉ rebuild **Chương 23**.

## Checklist sau khi GitHub auth

1. Tạo remote repo (ví dụ `the-quizzman/daodejing`)
2. `git remote add origin … && git push -u origin main`
3. Thêm **Webhook**
   - URL: `https://wiki.quizzman.com/api/github/webhook`
   - Secret: khớp server
   - Event: `push`
4. Thêm Action secret `WIKI_REBUILD_TOKEN`
5. (Tuỳ chọn) biến `WIKI_REBUILD_URL` nếu endpoint khác mặc định
6. Push thử một file → xác nhận wiki cập nhật trong vài giây

## Kiểm tra local (dry-run)

```bash
cp .env.example .env
# điền token khi có
chmod +x scripts/trigger-rebuild.sh
./scripts/trigger-rebuild.sh chapters/023.md
```

Không có token → script chỉ in payload, không gọi API.
