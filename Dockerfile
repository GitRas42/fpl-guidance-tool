# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python production server
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY data_fetcher.py algorithm.py app.py ./

# Copy React build into /app/static (Flask serves this)
COPY --from=frontend-build /app/frontend/build ./static

# Create cache directory
RUN mkdir -p /app/cache

EXPOSE 5000

# Run with Gunicorn in production
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "30", "--access-logfile", "-"]
