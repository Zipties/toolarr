# --- Builder Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Generate the OpenAPI specification files
RUN python generate_openapi.py

# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY instance_endpoints.py .
COPY sonarr.py .
COPY radarr.py .
COPY prune_openapi.py .
COPY generate_openapi.py .

# Include the generated specs
COPY --from=builder /app/openapi.json .
COPY --from=builder /app/openapi-chatgpt.json .

# Expose port
EXPOSE 8000

# Generate OpenAPI specs at runtime as well and start server
CMD ["sh", "-c", "python generate_openapi.py && exec python -u -m uvicorn main:app --host 0.0.0.0 --port 8000"]
