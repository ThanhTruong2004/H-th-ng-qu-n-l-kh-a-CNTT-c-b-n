# Hệ Thống Quản Lý & Lắp Ráp Đề Thi CNTT Cơ Bản (DLU)

> Ứng dụng web tự động lắp ráp bộ đề thi CNTT cơ bản của Trường Đại học Đà Lạt: cắt ảnh minh họa chính xác ngay trên trình duyệt, phân trang PDF động, và đóng gói bộ đề (đề thi + đáp án + bảng tiêu chí chấm điểm) thành một tệp ZIP duy nhất.
>
> 🎯 **Mục đích triển khai**: mạng nội bộ / localhost tại phòng máy hoặc phòng thi. Không yêu cầu bảo mật web-facing (Auth/CORS ngoài $192.168… đã bật sẵn).
>
> 🛡️ **Nginx lockdown**: `X-Frame-Options: SAMEORIGIN`, CSP đầy đủ (`frame-src`/`object-src`/`connect-src` cho phép `blob:`/`data:`) để vừa chặn clickjacking vừa không làm gãy PDF preview và `fetch(dataUrl)` của cropper.

---

## 📋 Yêu cầu phần cứng (RAM / CPU / Disk)

Bảng dưới được tính toán từ số liệu đo thực tế của hệ thống (xem Ghi chú kỹ thuật bên dưới) — gồm Docker image backend 2.41GB, cơ chế chuyển đổi LibreOffice tối đa 3 tiến trình song song (~800MB mỗi tiến trình theo thiết kế), trình duyệt Playwright Chromium singleton, và volume dữ liệu.

| Cấu hình | RAM | CPU (lõi vật lý) | Disk trống | Khi nào dùng |
|----------|-----|------------------|------------|--------------|
| **Tối thiểu** (chạy được) | 6 GB | 2 lõi | 15 GB | 1 người dùng, phòng thi nhỏ, tải không quá nặng |
| **Khuyến nghị** ✅ | 8 GB | 4 lõi | 25 GB | **Dùng mượt** — trường hợp phổ biến: 1–5 máy nội bộ truy cập đồng thời |
| **Doanh nghiệp / đồng thời cao** | 16 GB | 8 lõi | 50 GB | Nhiều giảng viên cùng nạp module / sinh đề trong giờ cao điểm |

### Phân tích chi tiết

**🧠 RAM (quan trọng nhất)**
- **Backend (Python + FastAPI + uvicorn)**: ~200–300 MB nền thường trực.
- **Playwright Chromium** (render HTML → PDF): ~300–500 MB khi render, giữ singleton toàn bộ vòng đời tiến trình.
- **LibreOffice**: mỗi lần chuyển đổi Word → PDF tiêu thụ tới **~800 MB**; hệ thống giới hạn **tối đa 3 tiến trình song song** (`asyncio.Semaphore(3)`), tức cao điểm ~2.4 GB chỉ riêng cho chuyển đổi.
- **Nginx (frontend)**: giới hạn container **1 GB** (đủ cho body buffer 50 MB + upstream buffer 128 MB + nội dung tĩnh), backend **4 GB**.
- → **8 GB là điểm cân bằng vàng**: đủ cho tải cao điểm mà không phải swap. Với 6 GB, một đợt 3 file Word chuyển đổi đồng thời sẽ đẩy hệ thống sát ngưỡng — nên **khuyến nghị 8 GB**.

**⚙️ CPU**
- Chuyển đổi LibreOffice và render Playwright đều **CPU-bound**. Tối đa 3 chuyển đổi LO song song + render HTML + nén ảnh JPEG (Pillow) cùng lúc ⇒ **4 lõi vật lý** là đủ mượt; 2 lõi chỉ phù hợp khi rảnh rỗi, thời gian sinh đề sẽ lâu hơn.
- > ⚠️ Lưu ý máy ảo: nên cấp **4 vCPU thật**, tránh oversubscribe quá mức.

**💾 Disk**
- **Image Docker**: backend ~2.4 GB + frontend ~0.1 GB = **~2.5 GB**.
- **Build cache** (trong lúc `docker compose build`): có thể phình đến **~5 GB** (một phần giải phóng được bằng `docker builder prune`).
- **Volume dữ liệu** `exam-data`: mỗi module (ảnh crop PNG/JPEG, PDF gốc, file nguồn Excel/PPT) trung bình **50–150 MB**. Hiện trạng demo 3 module ≈ 1.3 GB.
- **Log Docker** (giới hạn): 10 MB × 3 file × 2 container ≈ 60 MB tối đa.
- Hệ điều hành + Docker Desktop: ~5–10 GB.
- → **25 GB trống** thoải mái cho hàng chục module; với phòng thi lớn, cấp thêm dung lượng cho volume.

---

## 🚀 Khởi chạy nhanh (Docker — khuyến nghị)

```bash
git clone https://github.com/ThanhTruong2004/H-th-ng-qu-n-l-kh-a-CNTT-c-b-n.git ITExamManager
cd ITExamManager

# Lần đầu (build image ~vài phút, cần ~6GB trống tạm thời cho build cache)
docker compose up -d --build

# Các lần sau (khởi động nhanh)
docker compose up -d
```

Ứng dụng khả dụng tại: **http://localhost:8000**

> 🔒 Backend chỉ `expose` cổng nội bộ 8000; mọi truy cập đi qua Nginx (frontend). Từ máy khác trong mạng nội bộ, truy cập `http://<IP-máy-chủ>:8000`.

### Lệnh hữu ích

```bash
docker compose ps                                  # trạng thái container
docker compose logs -f backend                     # theo dõi log backend
docker compose logs -f frontend                    # theo dõi log frontend
docker compose restart frontend                    # restart frontend (sau khi sửa nginx.conf)
docker builder prune -f                            # giải phóng build cache (~5GB)
docker volume ls                                   # xem volume dữ liệu
```

---

## 🪟 Chạy Windows bare-metal (không cần Docker)

Hệ thống đã được tối ưu đa nền tảng (path dùng `tempfile.gettempdir()`, pathlib, không hardcode `/tmp`).

**Bước 1 — Backend**

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
set DB_PATH=.\data\exams.db
set UPLOAD_DIR=.\data\uploads
set OUTPUT_DIR=.\data\outputs
uvicorn main:app --reload --port 8000
```

> Cần cài **[LibreOffice](https://www.libreoffice.org/download/)** cho tính năng chuyển đổi Word → PDF (.doc/.docx).

**Bước 2 — Frontend (dev mode)**

```bat
cd frontend
npm install
npm run dev
```

Frontend dev server (Vite port 5173) proxy `/api` về `http://localhost:8000`.

**Bước 3 — Frontend (production, tùy chọn)**

```bat
cd frontend
npm run build      # xuất ra frontend\dist\
```

---

## 📖 Hướng dẫn sử dụng

### Bước 1 — Nạp Module (tab *Upload*)

1. Nhập **Mã Module** (vd: `SET_1904C`).
2. Tải lên: **Đề thi gốc (PDF/.doc/.docx)**, **Đáp án gốc (PDF/.doc/.docx)**, **Excel gốc (.xlsx/.xls)**, **PowerPoint gốc (.pptx)**, và (tùy chọn) các **ảnh Word Assets**.
3. Bấm **Render Trang PDF** → mỗi ô trong lưới `Word Preview / Excel Preview / PPT Preview / Word Rubric / Excel Rubric / PPT Rubric` đều có thể mở cropper để kéo khung chọn 6 vùng ảnh minh họa (có thể cắt nhiều ảnh/vùng khi nội dung trải nhiều trang).
4. Bấm **Tải Lên Module**. Module xuất hiện trong Library và Generate.

### Bước 2 — Tạo bộ đề (tab *Generate*)

1. Nhập **Ngày Thi**, **Mã Đề**, **Cán Bộ Ra Đề**.
2. Chọn module theo cách **ngẫu nhiên** (mặc định) hoặc **thủ công** cho từng phần Word/Excel/PPT.
3. Bấm **Xem Trước** để kiểm tra đề & đáp án trong trình duyệt, hoặc **Tạo Đề & Tải ZIP**.

### Bước 3 — Quản lý (tab *Library*)

- Xem danh sách module, lần đầu mở **Chi Tiết Module** để xem các ảnh đã cắt.
- **Bấm vào ảnh thumbnail để phóng to** (Lightbox), nhấn `Esc` / click nền để đóng.
- Làm mới danh sách và xóa module.

---

## 🧩 Tính năng chính

- **Cắt ảnh thông minh trên trình duyệt** (Cropper.js): render trang PDF thành ảnh, kéo khung chọn vùng, lưu ảnh dưới dạng `URL.createObjectURL(blob)` (không base64 — tránh tràn bộ nhớ).
- **Phân trang PDF động**: hình minh họa được scale + tự động xuống trang mới khi vượt khổ, sau đó footer phân trang được chèn chính xác (không render HTML hai lần).
- **Nén ảnh tối ưu**: mọi ảnh crop được nén JPEG (quality 75) ngay trong bộ nhớ trước khi nhúng vào PDF, giảm tới ~90% kích thước tệp.
- **Playwright singleton + tự khởi động lại mỗi giờ**: giảm độ trễ render HTML→PDF, tránh Chromium rò rỉ bộ nhớ khi chạy lâu.
- **Chuyển đổi Word → PDF** qua LibreOffice (giới hạn 3 tiến trình song song, tự dọn temp).
- **Xem trước & tải ZIP** chỉ với một nút bấm; stream ZIP 64KB/chunk + ghi tệp nguyên tử (`.tmp` + `os.replace`) để không bao giờ phơi ra tệp ZIP chưa hoàn chỉnh.
- **Liệt kê ảnh phóng to (Lightbox)** trong thư viện, hỗ trợ bàn phím (Esc).
- 🛡️ **Chống đua nạp module (DI-1)**: khóa `threading.Lock` theo từng `module_id` — hai request nạp cùng một module đồng thời trả `409 Conflict`.
- 🔐 **Xóa an toàn (DI-2)**: xóa thư mục vật lý **trước**, xóa row DB **sau** — nếu xóa file thất bại, row vẫn còn để retry.
- ⏳ **Giới hạn render PDF (PERF-2)**: `asyncio.Semaphore(2)` — khi 2 tiến trình đang sinh đề, request tiếp theo trả `429 Too Many Requests` thay vì làm nghẽn Chromium.
- ⚡ **Cache đo chiều rộng chữ (PERF-1)**: `@lru_cache(maxsize=256)` cho `_text_width` thay cho dict vô hạn — chống rò rỉ bộ nhớ khi render nhiều footer/signature.
- 🖼️ **CSP thân thiện PDF**: `X-Frame-Options: SAMEORIGIN` + CSP cho phép `frame-src`/`object-src`/`connect-src` đến `blob:`/`data:` — PDF preview và `fetch(dataUrl)` của cropper hoạt động bình thường.

## 🛠 Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Backend | Python **FastAPI**, PyMuPDF (**fitz**), **Playwright** 1.62, Jinja2, SQLite (SQLitePool, không ORM) |
| Frontend | **Vue 3** (Composition API), **TailwindCSS**, Vite, Cropper.js |
| Vận hành | **Docker** + **Docker Compose**, Nginx reverse proxy, log rotation (`max-size 10m × 3`) |

## 📦 Cấu trúc dự án

```
ITExamManager/
├── docker-compose.yml            # backend + frontend, named volume exam-data, log rotation
├── backend/
│   ├── Dockerfile                # 3-stage: docker diet ~2.4GB (builder → playwright → final)
│   ├── main.py                   # FastAPI: toàn bộ API endpoints + startup hygiene
│   ├── database.py               # SQLite schema, SQLitePool (pool_size=5, timeout 15)
│   ├── models.py                 # Pydantic models
│   ├── file_utils.py             # Đường dẫn dữ liệu, format_ngay_thi đa-định-dạng, hằng số ext
│   ├── conversion.py             # Chuyển Word→PDF qua LibreOffice (Semaphore(3))
│   ├── requirements.txt
│   ├── services/
│   │   └── pdf_generator.py      # stack_images, phân trang, footer, signature, Playwright singleton
│   └── templates/                # exam_p1.html, answer_key_p1.html, answer_key_p4.html
└── frontend/
    ├── Dockerfile                # build bằng Node rồi serve bằng Nginx
    ├── nginx.conf                # Proxy /api/ → backend:8000 (timeout 300s), buffer RAM (body 50M, upstream 128M), security headers (SAMEORIGIN + CSP)
    └── src/
        ├── App.vue               # Layout + điều hướng tab
        ├── api.js                # API client (fetchWithTimeout 180s, AbortController)
        ├── style.css
        └── components/
            ├── UploadPdfForm.vue # Nạp PDF + cropper 6 vùng ảnh + dataURLToFile async (fetch)
            ├── LibraryPanel.vue  # Thư viện module + Lightbox (Phase 25)
            └── GeneratePanel.vue # Tạo đề / xem trước / tải ZIP
```

## 🔌 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/health` | Kiểm tra sức khỏe |
| POST | `/api/modules/pages` | Render các trang PDF ra base64 để cắt ảnh |
| POST | `/api/modules/ingest` | Nạp module (PDF + crops + file nguồn) — `409` nếu module đang được nạp đồng thời |
| GET | `/api/modules` | Danh sách module |
| GET | `/api/modules/{module_id}` | Chi tiết module (crops + word assets) |
| GET | `/api/modules/{module_id}/files/{category}/{filename}` | Phục vụ file asset (chống path traversal) |
| DELETE | `/api/modules/{module_id}` | Xóa module |
| POST | `/api/generate/preview` | Sinh đề + đáp án (generation artifact) — trả `generation_id`; `429` khi đã có 2 tiến trình đang sinh |
| GET | `/api/generations/{generation_id}/exam.pdf` | PDF đề thi của artifact |
| GET | `/api/generations/{generation_id}/answer_key.pdf` | PDF đáp án của artifact |
| POST | `/api/generate/download` | Đóng gói ZIP từ artifact (không sinh lại PDF); `429` khi render queue đầy |

## 💾 Docker Volumes & Dữ liệu

Dữ liệu người dùng lưu trong **named volume** `exam-data` (mount vào `/data`) — **không mất khi container khởi động lại**:

| Đường dẫn trong container | Nội dung |
|---------------------------|----------|
| `/data/exams.db` | Cơ sở dữ liệu SQLite |
| `/data/uploads/` | PDF gốc + ảnh crop (PNG/JPEG) + file nguồn của các module |
| `/data/outputs/` | PDF đề/đáp án đã sinh + các tệp ZIP tải xuống (tự xóa sau streaming) |

> 🔁 **Backup**: `docker run --rm -v itexammanager_exam-data:/data -v %cd%:/backup ubuntu tar czf /backup/exam-data.tgz -C /data .`

## 🧹 Vận hành & Dọn dẹp tự động

Hệ thống tự làm sạch khi khởi động (và định kỳ):
- Generation artifact quá 1 giờ → xóa.
- ZIP tải xuống quá 1 giờ → xóa (có age-guard chống đua khi đang stream chậm).
- Temp thư mục mồ côi của LibreOffice/PDF-gen (`lo_conv_*`, `pdfgen_*`…) trong `tempfile.gettempdir()` (đa nền tảng).
- Checkpoint SQLite WAL mỗi 10 phút (chống phình `.db-wal`).
- Chromium chủ động khởi động lại sau 1 giờ.

## ⚙️ Biến môi trường

| Biến | Mặc định | Mô tả |
|------|---------|-------|
| `DB_PATH` | `/data/exams.db` | Đường dẫn SQLite |
| `UPLOAD_DIR` | `/data/uploads` | Thư mục upload module |
| `OUTPUT_DIR` | `/data/outputs` | Thư mục xuất PDF/ZIP |
| `EXAM_FONT_FILE` / `EXAM_FONT_BOLD_FILE` | Liberation Serif | Ghi đè font Times New Roman |

## 🧠 Ghi chú kỹ thuật

- **Chỉ render HTML một lần**: số trang cuối được xác định từ tài liệu ảnh trước, sau đó trang HTML đầu được render duy nhất một lần với `tong_so_trang` đúng.
- **Con trỏ Y dùng chung (Phase 28)**: `build_exam_pdf` dùng một `current_page` + `current_y` quay vòng cho cả ba phần Word/Excel/PPT — `stack_images` tự xuống trang mới khi hết chỗ; thiếu preview một phần thì bỏ qua bằng `logger.warning` chứ không làm rơi PPT. Lưu ý "LƯU Ý" nhúng qua `insert_htmlbox(css=...)` (PyMuPDF 1.27 không nhận `fontname/fontsize/color` trong htmlbox) và sau đó `current_y = note_y + 90.0` để phần Excel/PPT không chồng lên.
- **Ép ảnh chuẩn khung**: mọi ảnh crop nhúng vào PDF theo dải bbox cố định (khổ A4), giữ tỷ lệ, top-anchor; signature đáp án có phương án tự động xuống trang mới khi thiếu chỗ.
- **Ngày thi đa định dạng**: chấp nhận ISO (có/không `T`-time), `DD/MM/YYYY`, `DD-MM-YYYY`; nếu để trống/placeholder (`dd/mm/yyyy`) sẽ xuất `…/…/…` (gạch chấm để viết tay).
- **Đo chiều rộng chữ có giới hạn**: `@lru_cache(maxsize=256)` cho `_text_width` (thay thế dict phình vô hạn từ Phase 32).
- **Streaming ZIP không nạp hết vào RAM**: đọc file theo từng khối 64KB và `/api/generate/download` ghi ZIP nguyên tử (`.tmp` → `os.replace`).
- **Buffer Nginx trong RAM**: `client_body_buffer_size 50M` (payload upload ≤50MB không chạm đĩa) + `proxy_buffers 8 16M`/`proxy_buffer_size 16M` (response API ~4.2MB buffered đầy đủ trong RAM).
- **Kích thước image**: backend ~**2.41 GB**, frontend ~**0.11 GB** (đo thực tế). Image cài kèm LibreOffice + Chromium; bản `python:3.10-slim` gốc.
- **Log rotation**: mỗi container giới hạn `10 MB × 3 file`.
- **CORS**: bật sẵn `allow_origins=["*"]` cho dễ triển khai nội bộ; nếu dùng công khai cần thu hẹp.

## ❓ Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân / Cách xử lý |
|-----------|--------------------------|
| `Cannot convert ... Word document to PDF` | Thiếu LibreOffice (bản bare-metal) hoặc file Word trống/corrupt |
| Tải ZIP bị lỗi/giữa chừng | Mạng chậm; hệ thống tự regenerate ZIP — thử tải lại |
| Render trang PDF chậm | Máy thiếu CPU/RAM — xem bảng cấu hình phần cứng |
| `Module 'X' already exists` | Mã module trùng — chọn mã khác hoặc xóa trong Library |
| `Module 'X' is currently being ingested. Please wait.` (409) | Ai đó đang nạp cùng module — chờ xong rồi thử lại |
| `Server is generating PDFs. Please retry in a moment.` (429) | Đã có 2 lần sinh đề đồng thời — chờ vài giây rồi thử lại |
| Nginx warning "request body buffered to temp file" | Đã loại bỏ bằng `client_body_buffer_size 50M` — nếu vẫn xuất hiện với payload >50MB, tăng thêm |
| Docker chiếm nhiều disk | `docker builder prune -f` để giải phóng build cache |
| Không truy cập được từ máy khác | Kiểm tra firewall mở cổng 8000; truy cập `http://<IP>:8000` |

## 📜 License

Dự án nội bộ của Trường Đại học Đà Lạt — phục vụ công tác đào tạo CNTT cơ bản.