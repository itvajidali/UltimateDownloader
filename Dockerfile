# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies (FFmpeg is crucial)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create downloads folder
RUN mkdir -p downloads

# Expose port (Render uses 10000 usually, but we can configure)
ENV PORT=5000
EXPOSE 5000

# Start command
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--timeout", "120"]
