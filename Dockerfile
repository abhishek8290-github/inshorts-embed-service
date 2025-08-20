FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Install base requirements first (smaller, faster)
COPY requirements-base.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements-base.txt

# Install ML requirements separately (larger, more likely to timeout)
COPY requirements-ml.txt .
RUN pip install --no-cache-dir --timeout=600 --retries=10 -r requirements-ml.txt

COPY main.py .

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
