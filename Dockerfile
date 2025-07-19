# --- Builder Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application source files
COPY . .

# Generate the OpenAPI specification files
RUN python generate_openapi.py

# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files (excluding the generation script)
COPY main.py .
COPY instance_endpoints.py .
COPY sonarr.py .
COPY radarr.py .
COPY prune_openapi.py .

# Copy only the generated OpenAPI specs from the builder stage
COPY --from=builder /app/openapi.json .
COPY --from=builder /app/openapi-chatgpt.json .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-u", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
