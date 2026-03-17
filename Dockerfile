FROM python:3.11-slim

# Install system dependencies required by OpenCV (Debian 12 compatible)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code into the container
COPY . .

# Command to run your FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
