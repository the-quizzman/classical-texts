# Handover — Classical Texts → Quizzman Wiki

**Người gửi:** Content / Classical Texts  
**Người nhận:** Wiki Dev (Quizzman)  
**Ưu tiên:** P0 — nội dung đã sẵn trên GitHub nhưng **chưa xuất hiện trên wiki**  
**Ngày:** 2026-08-04  
**Factory:** https://github.com/the-quizzman/classical-texts  
**Registry máy đọc được:** [`sources/wiki-registry.json`](../sources/wiki-registry.json)  
**Spec:** Classical Text Spec v1 (`docs` / template `CLASSICAL-TEXT-SPEC.md`)  
**Môi trường đích:** https://wiki.quizzman.com

---

## 0. TL;DR

1. Content đã tạo **38 book repos** + **3 collection indexes** dưới org `the-quizzman`, cùng contract với `daodejing`.
2. **1890** file `chapters/NNN.md` đã có Hán văn (`# Original Text`). Nhiều lớp dịch/chú vẫn `draft` / `_Chưa biên soạn._`.
3. Mỗi repo đã có `book.yaml`, workflow `.github/workflows/wiki-rebuild.yml`, `scripts/validate-books.sh`.
4. Wiki **chưa whitelist / chưa clone / chưa full-import** các repo này → trang sách chưa live.
5. Việc còn lại thuộc **Wiki Dev**: mở rộng pipeline đa-repo (trước đây ghi “ngoài phạm vi” trong handover `daodejing`), full rebuild lần đầu, bật webhook + secrets.

Tham chiếu handover cũ (1 sách): [`the-quizzman/daodejing` → `docs/YEU-CAU-KY-THUAT-WIKI.md`](https://github.com/the-quizzman/daodejing/blob/main/docs/YEU-CAU-KY-THUAT-WIKI.md).

---

## 1. Mục tiêu

Wiki **không** là source of truth. GitHub là source of truth. Wiki chỉ render + search.

Sau khi Wiki Dev hoàn tất:

| Hành động | Kết quả |
| --- | --- |
| Full import lần đầu mỗi book repo | Có trang sách + toàn bộ chương trên wiki |
| `git push` `main` | Incremental rebuild chỉ file `chapters/**` / `book.yaml` đổi |
| Đọc `book.yaml` | Metadata sách (title, path, chapter_count, licenses…) |

---

## 2. Content contract (quan trọng — khác bản nháp cũ)

Layout **hiện tại** (Classical Text Spec v1), áp dụng mọi book repo:

```text
book.yaml
chapters/
  001.md
  002.md
  …
docs/
scripts/validate-books.sh
.github/workflows/wiki-rebuild.yml
```

### 2.1. `book.yaml` (bắt buộc)

Ví dụ `lunyu`:

```yaml
spec: classical-text/v1
id: lunyu
title: Luận Ngữ
title_original: 論語
author: …
language: vi
category: nho-gia
chapter_count: 20
chapter_glob: chapters/*.md
status: draft
publish:
  base_url: https://wiki.quizzman.com
  book_path: /books/luan-ngu
rebuild:
  mode: incremental
  webhook_endpoint: /api/github/webhook
  rebuild_endpoint: /api/wiki/rebuild
  branch: main
```

**Mapping publish URL:**

```text
https://wiki.quizzman.com{book_path}
https://wiki.quizzman.com{book_path}/chapters/{n}   # đề xuất
```

(`book_path` đã khai báo per-repo trong `book.yaml` / registry.)

### 2.2. Chapter front matter (tối thiểu)

```yaml
---
chapter: 1
title: …
status: draft        # draft | review | stable
version: 1
---
```

Filename = zero-pad 3 chữ số khớp `chapter` → `001.md`.

### 2.3. Section H1 (đúng thứ tự, đúng tên)

1. `# Original Text`
2. `# Textual Variants`
3. `# Sino-Vietnamese`
4. `# Literal Translation`
5. `# Literary Translation` (có thể có `## Vietnamese`, `## English …`)
6. `# Commentary`
7. `# Textual Notes`
8. `# References`

Parser wiki nên:

- Render từng section thành tab / anchor / collapsible (tuỳ UX).
- **Không** fail build nếu section chỉ có `_Chưa biên soạn._`.
- Index search ưu tiên: Original Text + Literary Translation (VI/EN nếu có).

### 2.4. Collection repos (không phải sách đầy đủ)

| Repo | Vai trò |
| --- | --- |
| `sishu` / `wujing` / `shisanjing` | Index: `book.yaml` có `kind: collection` + `members: […]` — **không** có `chapters/` |

Wiki có thể: (A) bỏ qua, hoặc (B) render trang mục lục link sang book_path của members.

---

## 3. Danh sách repo cần whitelist + clone

**Machine-readable:** [`sources/wiki-registry.json`](../sources/wiki-registry.json)

### 3.1. Reference (đã có)

| id | GitHub | book_path | chapters |
| --- | --- | ---: | ---: |
| daodejing | https://github.com/the-quizzman/daodejing | /books/dao-duc-kinh | 81 |

### 3.2. Book repos (content-ready) — 38 repos / 1890 chapters

| id | GitHub | book_path | chapters |
| --- | --- | --- | ---: |
| daxue | https://github.com/the-quizzman/daxue | /books/dai-hoc | 1 |
| zhongyong | https://github.com/the-quizzman/zhongyong | /books/trung-dung | 1 |
| lunyu | https://github.com/the-quizzman/lunyu | /books/luan-ngu | 20 |
| mengzi | https://github.com/the-quizzman/mengzi | /books/manh-tu | 14 |
| yijing | https://github.com/the-quizzman/yijing | /books/chu-dich | 63 |
| shangshu | https://github.com/the-quizzman/shangshu | /books/thuong-thu | 55 |
| liji | https://github.com/the-quizzman/liji | /books/le-ky | 47 |
| chunqiu | https://github.com/the-quizzman/chunqiu | /books/xuan-thu | 12 |
| zhouli | https://github.com/the-quizzman/zhouli | /books/chu-le | 6 |
| yili | https://github.com/the-quizzman/yili | /books/nghi-le | 17 |
| gongyang | https://github.com/the-quizzman/gongyang | /books/cong-duong-truyen | 12 |
| guliang | https://github.com/the-quizzman/guliang | /books/coc-luong-truyen | 12 |
| xiaojing | https://github.com/the-quizzman/xiaojing | /books/hieu-kinh | 18 |
| erya | https://github.com/the-quizzman/erya | /books/nhi-nha | 19 |
| zhuangzi | https://github.com/the-quizzman/zhuangzi | /books/trang-tu | 33 |
| liezi | https://github.com/the-quizzman/liezi | /books/liet-tu | 8 |
| wenzi | https://github.com/the-quizzman/wenzi | /books/van-tu | 11 |
| yinfujing | https://github.com/the-quizzman/yinfujing | /books/am-phu-kinh | 3 |
| hanfeizi | https://github.com/the-quizzman/hanfeizi | /books/han-phi-tu | 55 |
| shangjunshu | https://github.com/the-quizzman/shangjunshu | /books/thuong-quan-thu | 24 |
| guanzi | https://github.com/the-quizzman/guanzi | /books/quan-tu | 76 |
| mozi | https://github.com/the-quizzman/mozi | /books/mac-tu | 53 |
| sunzi | https://github.com/the-quizzman/sunzi | /books/ton-tu-binh-phap | 13 |
| wuzi | https://github.com/the-quizzman/wuzi | /books/ngo-tu | 6 |
| liutao | https://github.com/the-quizzman/liutao | /books/luc-thao | 59 |
| sanlue | https://github.com/the-quizzman/sanlue | /books/tam-luoc | 3 |
| shiji | https://github.com/the-quizzman/shiji | /books/su-ky | 114 |
| hanshu | https://github.com/the-quizzman/hanshu | /books/han-thu | 118 |
| houhanshu | https://github.com/the-quizzman/houhanshu | /books/hau-han-thu | 120 |
| sanguozhi | https://github.com/the-quizzman/sanguozhi | /books/tam-quoc-chi | 3 |
| zizhitongjian | https://github.com/the-quizzman/zizhitongjian | /books/tu-tri-thong-giam | 294 |
| chuci | https://github.com/the-quizzman/chuci | /books/so-tu | 64 |
| shijing | https://github.com/the-quizzman/shijing | /books/thi-kinh | 306 |
| guwenguanzhi | https://github.com/the-quizzman/guwenguanzhi | /books/co-van-quan-chi | 24 |
| wenxindiaolong | https://github.com/the-quizzman/wenxindiaolong | /books/van-tam-dieu-long | 50 |
| huangdineijing | https://github.com/the-quizzman/huangdineijing | /books/hoang-de-noi-kinh | 110 |
| shanghanlun | https://github.com/the-quizzman/shanghanlun | /books/thuong-han-luan | 10 |
| jinguiyaolue | https://github.com/the-quizzman/jinguiyaolue | /books/kim-quy-yeu-luoc | 25 |

### 3.3. Collection indexes (tuỳ chọn)

| id | GitHub |
| --- | --- |
| sishu | https://github.com/the-quizzman/sishu |
| wujing | https://github.com/the-quizzman/wujing |
| shisanjing | https://github.com/the-quizzman/shisanjing |

---

## 4. Việc Wiki Dev cần làm

### P0 — bắt buộc để sách xuất hiện

| # | Việc | Chi tiết |
| --- | --- | --- |
| 1 | Mở rộng whitelist | Tất cả repo mục 3.2 (+ `daodejing`). Không hard-code 1 repo. |
| 2 | Clone trên server | Deploy key / machine user read-only; mỗi repo 1 thư mục; `git pull --ff-only`. |
| 3 | Full import lần đầu | `POST /api/wiki/rebuild` với `mode: "full"` cho từng book repo (hoặc job nội bộ). |
| 4 | Parse Spec v1 | `book.yaml` + `chapters/NNN.md` + 8 H1 sections như mục 2. |
| 5 | Route publish | Dùng `publish.book_path` từ `book.yaml`. |
| 6 | Webhook đa-repo | Cùng endpoint `/api/github/webhook`; phân nhánh theo `repository.full_name`. |
| 7 | Cấp secrets cho Content | `GITHUB_WEBHOOK_SECRET` + `WIKI_REBUILD_TOKEN` (staging + prod) — Content sẽ gắn webhook/Actions trên từng repo (hoặc org-level nếu Wiki prefer). |

### P1 — vận hành

| # | Việc |
| --- | --- |
| 8 | Queue serialize rebuild **theo repo** (tránh 2 pull song song cùng repo) |
| 9 | Log: `delivery_id`, `repository`, `sha`, `modified[]`, `duration_ms` |
| 10 | Search incremental theo chương |
| 11 | Catalog UI: nhóm theo `category` (nho-gia, dao-gia, …) — field có trong `book.yaml` / registry |

### Đề xuất thứ tự onboard (giảm rủi ro)

1. Smoke: `lunyu` (20 ch) + `sunzi` (13 ch)  
2. Medium: `zhuangzi`, `mengzi`, `yijing`  
3. Large: `shijing` (306), `zizhitongjian` (294), sử ký nhóm  
4. Collections indexes (nếu làm)

---

## 5. API (giữ nguyên contract daodejing)

### 5.1. `POST /api/github/webhook`

- Verify `X-Hub-Signature-256`
- Chỉ `push` + `refs/heads/main`
- Repo phải whitelist
- Gom path `chapters/**`, `book.yaml` từ commits
- `git pull --ff-only` → incremental rebuild

### 5.2. `POST /api/wiki/rebuild`

Auth: `Authorization: Bearer <WIKI_REBUILD_TOKEN>`

```json
{
  "repository": "the-quizzman/lunyu",
  "ref": "refs/heads/main",
  "sha": "<commit sha>",
  "mode": "full",
  "modified": []
}
```

| mode | Ý nghĩa |
| --- | --- |
| `incremental` | Rebuild `modified[]` |
| `full` | Rebuild mọi `chapters/*.md` + reload `book.yaml` |
| `manual` | Giống full / theo policy Wiki |

Actions ở mỗi repo đã có workflow gọi endpoint này khi push `chapters/**` hoặc `book.yaml` (cần secret `WIKI_REBUILD_TOKEN`).

---

## 6. Acceptance

1. `GET https://wiki.quizzman.com/books/luan-ngu` trả về sách Luận Ngữ (không 404).
2. Ít nhất 1 chương (vd. `/books/luan-ngu` → chương 1) hiển thị `# Original Text` có Hán văn.
3. Full rebuild `lunyu` + `sunzi` thành công; log có `sha` + số chương.
4. Sửa 1 file `chapters/003.md` trên `sunzi` + push → chỉ chương 3 cập nhật (≤ 15s p95).
5. Repo không whitelist → `403`.
6. Signature/token sai → `401`.
7. Search tìm được đoạn Hán văn vừa import (sau full index).

---

## 7. Known content quirks (Content sẽ refine sau)

Wiki **không** block import vì các điểm này — chỉ để Dev biết khi QA:

| Repo | Ghi chú |
| --- | --- |
| `sanguozhi` | Hiện 3 phần 魏/蜀/吴 (chưa tách 65 quyển) |
| `yijing` | 63/64 quẻ |
| `daxue` / `zhongyong` | 1 file全文 mỗi sách |
| `guwenguanzhi` | 24 quyển (chưa tách từng bài) |
| `shiji` | 114 (truyền thống 130) |
| Nhiều sách | Sino-Vietnamese / VI literary vẫn placeholder |

---

## 8. Deliverables cần Wiki trả lại Content

| # | Deliverable | Owner |
| --- | --- | --- |
| 1 | Confirm endpoint paths (nếu khác `/api/github/webhook`, `/api/wiki/rebuild`) | Wiki |
| 2 | `GITHUB_WEBHOOK_SECRET` + `WIKI_REBUILD_TOKEN` (staging + prod) | Wiki |
| 3 | Danh sách repo đã whitelist + đã full-import | Wiki |
| 4 | Staging URL để Content smoke-test | Wiki |
| 5 | Confirm URL schema chương (đề xuất: `{book_path}/chapters/{n}`) | Wiki |
| 6 | Policy xóa file chương (404 vs soft-delete) | Wiki |

**Sau khi nhận secrets**, Content sẽ:

1. Đăng ký webhook (per-repo hoặc org)
2. Set Actions secret `WIKI_REBUILD_TOKEN` trên các repo (hoặc org secrets)
3. Chạy acceptance mục 6

---

## 9. Liên hệ & file kèm

| File | Mục đích |
| --- | --- |
| [`sources/wiki-registry.json`](../sources/wiki-registry.json) | Whitelist + book_path + chapter_count |
| [`catalog.yaml`](../catalog.yaml) | Catalog biên tập |
| [`templates/CLASSICAL-TEXT-SPEC.md`](../templates/CLASSICAL-TEXT-SPEC.md) | Spec parser |
| [`templates/wiki-rebuild.yml`](../templates/wiki-rebuild.yml) | Actions mẫu |
| Ví dụ chương | https://github.com/the-quizzman/lunyu/blob/main/chapters/001.md |
| Ví dụ book.yaml | https://github.com/the-quizzman/lunyu/blob/main/book.yaml |

**Local clones (máy Content):** `/Users/gengyang/classical-texts/books/<id>/`
