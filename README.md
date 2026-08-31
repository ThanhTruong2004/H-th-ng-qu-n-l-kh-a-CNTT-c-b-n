# ICT DLU - Exam Manager

Hệ thống web quản lý và sinh đề thi CNTT (Trường Đại học Đà Lạt). Ứng dụng quản lý đề thi ở cấp độ tệp (.docx, .xlsx, .pptx), tự động chọn ngẫu nhiên để tạo bộ đề mới, ghép bảng tiêu chí chấm điểm thành một tệp duy nhất, và đóng gói thành tệp ZIP để tải về.

## Tech Stack

- **Backend**: Python FastAPI + SQLite
- **Frontend**: Vue 3 + Tailwind CSS + Vite
- **Containerization**: Docker + Docker Compose
- **Design**: Editorial-Luxury & Soft-Structuralism (tham khảo taste-skill & superpowers)

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (required)
- [Git](https://git-scm.com/)

## Quick Start

```bash
git clone https://github.com/[your-username]/ITExamManager.git
cd ITExamManager
docker-compose up --build
```

The application will be available at **http://localhost:8000**

## Project Structure

```
ITExamManager/
├── docker-compose.yml          # Orchestrates backend + frontend containers
├── .dockerignore
├── backend/
│   ├── main.py                 # FastAPI application & API routes
│   ├── database.py             # SQLite schema & connection management
│   ├── models.py               # Pydantic request/response models
│   ├── file_utils.py           # File handling, Excel merging, ZIP packaging
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.vue             # Main layout with tab navigation
│   │   ├── api.js              # API client layer
│   │   ├── style.css           # Tailwind CSS + component classes
│   │   └── components/
│   │       ├── UploadPanel.vue      # Drag-and-drop file upload
│   │       ├── LibraryPanel.vue     # Browse, filter, delete exam sets
│   │       └── GeneratePanel.vue    # Generate & download exam sets
│   ├── tailwind.config.js      # Design tokens & theme configuration
│   ├── vite.config.js          # Vite build configuration
│   ├── nginx.conf              # Reverse proxy to backend API
│   ├── package.json
│   └── Dockerfile
```

## How It Works

### 1. Upload Exam Sets

- Upload an exam file (.docx, .xlsx, .pptx) along with its associated grading criteria (.xlsx)
- The system auto-detects the category (Word, Excel, PowerPoint)
- Files are stored persistently via Docker volumes

### 2. Browse Library

- View all uploaded exam sets
- Filter by category (Word / Excel / PowerPoint)
- Delete individual sets

### 3. Generate Exam Sets

- The system requires at least 1 file in each category (Word, Excel, PowerPoint)
- Choose how many unique sets to generate (1-50)
- Each generated set contains:
  - 1 randomly selected Word exam
  - 1 randomly selected Excel exam
  - 1 randomly selected PowerPoint exam
  - 1 merged Final_Grading_Sheet.xlsx (combining all 3 criteria files)
- Download as a single ZIP file

## Docker Volumes

Data persists across container restarts via named Docker volumes:

| Volume | Purpose |
|--------|---------|
| `exam-data` | Stores SQLite database + uploaded files + generated ZIPs |

## Development (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
set DB_PATH=./exams.db
set UPLOAD_DIR=./uploads
set OUTPUT_DIR=./outputs
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Get exam counts by category |
| GET | `/api/sets` | List all exam sets |
| POST | `/api/sets/upload` | Upload exam + criteria files |
| DELETE | `/api/sets/{id}` | Delete an exam set |
| POST | `/api/generate` | Generate random exam sets |
| GET | `/api/generated` | List generated sets |
| GET | `/api/download/{filename}` | Download generated ZIP |
| DELETE | `/api/generated/{id}` | Delete a generated set |
