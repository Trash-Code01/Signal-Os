# Use standard python image since we removed Playwright
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies if any are needed for other packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# The API creates the new CRM tables safely at startup. The worker command is
# overridden by docker-compose and starts only after the API service.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
