FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY main.py .
COPY instance_endpoints.py .
COPY sonarr.py .
COPY radarr.py .
COPY prune_openapi.py .
COPY generate_openapi.py .

# Expose port
EXPOSE 8000

# Generate OpenAPI specs and run the application
CMD ["sh", "-c", "python generate_openapi.py && exec python -u -m uvicorn main:app --host 0.0.0.0 --port 8000"]
