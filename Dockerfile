FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py /app/main.py
COPY sonarr.py /app/sonarr.py
COPY radarr.py /app/radarr.py

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-u", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
