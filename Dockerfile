# Use official slim python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential for compiling C dependencies if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Grant execution rights to the startup script
RUN chmod +x start.sh

# Expose port (Hugging Face Spaces uses 7860 by default)
EXPOSE 7860

# Run startup script
CMD ["./start.sh"]
