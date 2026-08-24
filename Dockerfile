FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy rest of app
COPY . .

EXPOSE 8000

CMD sh -c "uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT"
