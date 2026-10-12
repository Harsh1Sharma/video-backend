FROM python:3.9-slim

# Install the FFmpeg machinery
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start the invisible cloud server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]