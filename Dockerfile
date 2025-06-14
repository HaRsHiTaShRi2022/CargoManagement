# Base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl python3 python3-pip npm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Tailwind CSS and fix PATH issue
RUN npm install -g tailwindcss && \
    ln -s /usr/local/lib/node_modules/tailwindcss/bin/tailwindcss /usr/local/bin/tailwindcss

# Set working directory
WORKDIR /app

# Copy application
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Build CSS using Tailwind
RUN tailwindcss -i ./static/css/input.css -o ./static/css/styles.css --minify

# Expose FastAPI default port
EXPOSE 8000

# Start FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
