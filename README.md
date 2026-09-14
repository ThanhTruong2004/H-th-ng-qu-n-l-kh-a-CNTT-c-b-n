# Hệ Thống Quản Lý & Lắp Ráp Đề Thi CNTT Cơ Bản (DLU)

> Ứng dụng web tự động lắp ráp bộ đề thi CNTT cơ bản của Trường Đại học Đà Lạt: cắt ảnh minh họa chính xác, phân trang PDF động, và đóng gói bộ đề (đề thi + đáp án + bảng tiêu chí chấm điểm) thành một tệp ZIP duy nhất.

---

## Mô tả

Hệ thống giải quyết bài toán lắp ráp đề thi vốn làm thủ công, gồm 3 công đoạn tự động hoàn toàn:

1. **Nạp Module theo định dạng chuẩn** — người dùng tải lên file PDF đề thi + đáp án, kèm file nguồn Excel/PowerPoint và ảnh Word, sau đó dùng **công cụ cắt ảnh (cropper)** ngay trên trình duyệt để đánh dấu chính xác 6 vùng ảnh minh họa (preview & rubric cho từng phần Word/Excel/PowerPoint).
2. **Lắp ráp động** — backend căn giữa và ép ảnh đúng khổ trang A4 theo thuật toán phân trang động (`stack_images`), giữ nguyên dải bbox chuẩn của mẫu đề mà không bao giờ lệch định dạng.
3. **Phát hành** — người dùng chọn module (ngẫu nhiên hoặc thủ công), nhập ngày thi/mã đề/cán bộ ra đề, **xem trước** trực tiếp trong trình duyệt rồi tải bộ đề về dưới dạng **ZIP** gồm file đề (`MaDe_*.pdf`), đáp án (`DapAn_*.pdf`) và bảng tiêu chí chấm điểm (Excel/PPT).

Hệ thống bám sát một mẫu định dạng đề thi cố định: header trường, khối hướng dẫn, phần trắc nghiệm, marker `HẾT`, footer phân trang, chữ ký — đảm bảo mọi bộ đề phát ra đều **chuẩn quy cách**.

## Tính năng chính

- **Cắt ảnh thông minh trên trình duyệt** (Cropper.js): render trang PDF thành ảnh, kéo khung chọn vùng, cắt nhiều ảnh cho một vùng khi nội dung trải nhiều trang.
- **Phân trang PDF động**: hình minh họa được scale + tự động xuống trang mới khi vượt khổ, sau đó footer phân trang được chèn chính xác (không render HTML hai lần).
- **Nén ảnh tối ưu**: tất cả ảnh crop được nén JPEG (quality 75) ngay trong bộ nhớ trước khi nhúng vào PDF, giảm tới ~90% kích thước tệp xuất ra.
- **Playwright singleton**: trình Chromium dùng chung cho toàn bộ vòng đời tiến trình, giảm độ trễ render HTML→PDF.
- **Xem trước & tải ZIP** chỉ với một nút bấm; backend chạy hoàn toàn trong Docker, dữ liệu lưu trữ bền vững qua named volume.

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Backend | Python **FastAPI**, PyMuPDF (**fitz**), **Playwright**, Jinja2, SQLite |
| Frontend | **Vue 3** (Composition API), **TailwindCSS**, Vite, Cropper.js |
| Vận hành | **Docker** + **Docker Compose**, Nginx reverse proxy |

## Yêu cầu

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Docker Engine + Compose)
- Git (nếu muốn clone và đóng góp)

## Khởi chạy nhanh

```bash
git clone <your-repo-url> ITExamManager
cd ITExamManager
docker-compose up --build
```

Ứng dụng khả dụng tại: **http://localhost:8000**

> Backend chỉ `expose` cổng nội bộ 8000; mọi truy cập đi qua Nginx (frontend) — an toàn, không lộ API ra ngoài.

## Hướng dẫn sử dụng

### Bước 1 — Nạp Module (tab *Upload*)

1. Nhập **Mã Module** (vd: `SET_1904C`).
2. Tải lên: **Đề thi gốc (PDF)**, **Đáp án gốc (PDF)**, **Excel gốc (.xlsx)**, **PowerPoint gốc (.pptx)**, và (tùy chọn) các **ảnh Word Assets**.
3. Bấm **Render Trang PDF** → mỗi ô trong lưới `Word Preview / Excel Preview / PPT Preview / Word Rubric / Excel Rubric / PPT Rubric` đều có thể mở cropper để kéo khung chọn 6 vùng ảnh minh họa.
4. Bấm **Tải Lên Module**. Module xuất hiện trong Library và Generate.

### Bước 2 — Tạo bộ đề (tab *Generate*)

1. Nhập **Ngày Thi**, **Mã Đề**, **Cán Bộ Ra Đề**.
2. Chọn module theo cách **ngẫu nhiên** (mặc định) hoặc **thủ công** cho từng phần.
3. Bấm **Xem Trước** để kiểm tra đề & đáp án trong trình duyệt, hoặc **Tạo Đề & Tải ZIP**.

### Bước 3 — Quản lý (tab *Library*)

Xem danh sách module đã nạp, làm mới và xóa module.

## Cấu trúc dự án

```
ITExamManager/
├── docker-compose.yml            # Orchestrate backend + frontend, named volume exam-data
├── .dockerignore                 # Nguồn build tối giản
├── backend/
│   ├── Dockerfile                # python:3.10-slim + Playwright Chromium
│   ├── main.py                   # FastAPI app: các route API chính
│   ├── database.py               # SQLite schema & kết nối
│   ├── models.py                 # Pydantic models
│   ├── file_utils.py            # Xử lý tệp, ZIP packaging, đường dẫn dữ liệu
│   ├── requirements.txt
│   ├── services/
│   │   └── pdf_generator.py     # Lắp ráp PDF: stack_images, phân trang, footer, Playwright singleton
│   └── templates/                # exam_p1.html, answer_key_p1.html, answer_key_p4.html
└── frontend/
    ├── Dockerfile
    ├── nginx.conf                # Proxy /api/ → backend:8000 (timeout 300s)
    └── src/
        ├── App.vue               # Layout + điều hướng tab
        ├── api.js                # API client
        ├── style.css
        └── components/
            ├── UploadPdfForm.vue # Nạp PDF + cropper 6 vùng ảnh
            ├── LibraryPanel.vue  # Danh sách module
            └── GeneratePanel.vue # Tạo đề / xem trước / tải ZIP
```

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/health` | Kiểm tra sức khỏe |
| POST | `/api/modules/pages` | Render các trang PDF ra base64 để cắt ảnh |
| POST | `/api/modules/ingest` | Nạp module (PDF + crops + file nguồn) |
| GET | `/api/modules` | Danh sách module |
| DELETE | `/api/modules/{module_id}` | Xóa module |
| POST | `/api/generate/preview` | Sinh đề + đáp án, trả URL xem trước |
| GET | `/api/preview/{token}/{kind}` | Tải file preview theo token |
| POST | `/api/generate/download` | Sinh và trả về bộ đề dạng ZIP |

## Docker Volumes

Dữ liệu người dùng được lưu trong **named volume** `exam-data` (mount vào `/data` trong container backend) — **không mất khi container khởi động lại**:

| Đường dẫn trong container | Nội dung |
|---------------------------|----------|
| `/data/exams.db` | Cơ sở dữ liệu SQLite |
| `/data/uploads/` | PDF gốc + ảnh crop (PNG/JPEG) của các module |
| `/data/outputs/` | PDF đề thi/đáp án đã sinh + các tệp ZIP |

## Ghi chú kỹ thuật

- **Chỉ render HTML một lần**: số trang cuối được xác định từ tài liệu ảnh trước, sau đó trang html đầu tiên được render duy nhất một lần với `tong_so_trang` đúng.
- **Ép ảnh chuẩn khung**: mọi ảnh crop nhúng vào PDF theo dải bbox cố định (`85.04` … `538.59`, khổ A4), ép đúng max-width `453.55`, giữ tỷ lệ, top-anchor.
- **Fonts**: mặc định dùng Liberation Serif trong container; có thể ghi đè bằng biến môi trường `EXAM_FONT_FILE` / `EXAM_FONT_BOLD_FILE`.

## Phát triển cục bộ (không cần Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m playwright install chromium
set DB_PATH=./data/exams.db
set UPLOAD_DIR=./data/uploads
set OUTPUT_DIR=./data/outputs
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Frontend dev server proxy `/api` về `http://localhost:8000`.