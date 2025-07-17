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
COPY common_client.py /app/common_client.py

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-u", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
