FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY contextflow/ ./contextflow/
COPY setup.py .
COPY pyproject.toml .
COPY README.md .

# Install ContextFlow
RUN pip install .

# Create volume for data
VOLUME /data

# Set entrypoint
ENTRYPOINT ["contextflow"]
CMD ["--help"]