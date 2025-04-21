# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p templates/admin static

# Make sure all Python files are executable
RUN find . -name "*.py" -exec chmod +x {} \;

# Set basic environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port for Cloud Run
EXPOSE 8080

# Start the application
CMD ["python", "app.py"]
