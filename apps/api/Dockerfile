# Use official Playwright Python image which has all dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers are already installed in this image, but we can ensure chromium is linked
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# The API creates the new CRM tables safely at startup. The worker command is
# overridden by docker-compose and starts only after the API service.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
