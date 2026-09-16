# ============================================================================
# IT Exam Manager — backend image (AUDIT-22 storage & performance fix).
# Multi-stage diet: ~2.6 GB  ->  ~1.6-1.8 GB
#   Stage 1 (builder)         : build-essential + LibreOffice, pip deps into
#                              /install (disposable -> build tools never shipped)
#   Stage 2 (playwright-stage): chromium + OS deps, then DROP the downloaded
#                              archives under /root/.cache/ms-playwright/downloads
#                              (only the extracted browser is needed at runtime)
#   Stage 3 (final)           : copy /install + Playwright cache forward,
#                              apt-install runtime deps (incl. LibreOffice, whose
#                              private lib closure makes binary-copying brittle),
#                              all apt/pip caches purged
# ============================================================================

# ---- Stage 1: builder ------------------------------------------------------
FROM python:3.10-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget gnupg libfontconfig1 \
    libreoffice-writer libreoffice-core fonts-dejavu \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: playwright-stage ---------------------------------------------
FROM python:3.10-slim AS playwright-stage
RUN pip install --no-cache-dir playwright==1.62.0 \
    && playwright install chromium \
    && playwright install-deps chromium \
    && rm -rf /root/.cache/ms-playwright/downloads

# ---- Stage 3: final runtime image ------------------------------------------
FROM python:3.10-slim
WORKDIR /app

# Python packages (built in a disposable stage -> no compilers/headers shipped)
COPY --from=builder /install /usr/local

# Playwright chromium (extracted browser only — downloads cache already purged)
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
COPY --from=playwright-stage /root/.cache/ms-playwright /root/.cache/ms-playwright

# Runtime system deps.
# NOTE: LibreOffice is apt-installed here rather than COPY'ed from builder —
# copying the binaries is brittle (soffice.bin dlopens ~35 private shared libs
# — libicu76, libgpgmepp, libclucene, ... — whose versions must match the
# base distro). apt resolves the full dependency closure + the /usr/bin symlink
# chain in one shot at negligible size cost (~687MB either way).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-core fonts-dejavu fonts-liberation \
    libfontconfig1 \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]