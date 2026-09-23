FROM python:3.12-slim

# Tesseract: OCR de fotos y PDFs escaneados (el resto de los PDF se leen con pypdf).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY src ./src
COPY alembic.ini .
COPY alembic ./alembic

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn vrf.main:app --host 0.0.0.0 --port ${PORT:-8000}"]