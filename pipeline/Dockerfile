FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-fra \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the pipeline scripts
# Note: we will mount the data directory as a volume in docker-compose
COPY . .

# Default command
CMD ["python", "scraper.py", "--from-year", "2020", "--to-year", "2024"]
