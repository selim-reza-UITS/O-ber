# 1. Base Image: Start with a lightweight Python version
FROM python:3.9-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install System Dependencies
# We need 'tesseract-ocr' for the ID reader and 'libgl1' for OpenCV to work
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy the dependency file first (Caching strategy)
COPY requirements.txt .

# 5. Install Python Libraries
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your code
COPY . .

# 7. Expose the port the app runs on
EXPOSE 8000

# 8. The command to start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]