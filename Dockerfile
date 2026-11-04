FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project code
COPY . .

# Create output directory
RUN mkdir -p /app/output

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
