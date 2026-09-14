FROM python:3.10-slim
WORKDIR /app
# Install system deps required by Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# ONLY install chromium to save ~1GB
RUN playwright install chromium
RUN playwright install-deps chromium
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
