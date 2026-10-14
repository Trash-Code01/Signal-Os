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

# Copy only runtime source. Local databases, environment files, provider
# diagnostics and credentials never enter the image build context/layers.
COPY alembic.ini ./
COPY alembic ./alembic
COPY core ./core
COPY engines ./engines
COPY providers ./providers
COPY auth.py main.py worker.py start.sh ./

# Expose port for FastAPI
EXPOSE 8000

# Start both API and supervised campaign worker even without a host override.
# A dedicated docker-compose worker can still override this command.
CMD ["bash", "start.sh"]
