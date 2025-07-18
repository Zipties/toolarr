FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py /app/main.py
COPY instance_endpoints.py /app/instance_endpoints.py
COPY sonarr.py /app/sonarr.py
COPY radarr.py /app/radarr.py

# Expose port
EXPOSE 8000

COPY prune_openapi.py /app/prune_openapi.py

# Generate OpenAPI specs and run the application
CMD ["sh", "-c", "python main.py && python prune_openapi.py && exec python -u -m uvicorn main:app --host 0.0.0.0 --port 8000"]
