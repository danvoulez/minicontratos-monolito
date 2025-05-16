# Dockerfile for Monolito PromptOS on Railway

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway uses PORT env)
EXPOSE 5000

# Start the application
CMD ["python", "monolito.py"]
