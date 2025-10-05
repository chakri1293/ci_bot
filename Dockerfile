# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY Backend ./Backend

# Ensure Python sees /app
ENV PYTHONPATH=/app/Backend

# Expose port 80 (Elastic Beanstalk expects this)
EXPOSE 80

# Run FastAPI with Uvicorn
CMD ["uvicorn", "Backend.app:app", "--host", "0.0.0.0", "--port", "80"]
