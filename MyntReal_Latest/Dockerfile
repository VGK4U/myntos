FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files
# and to keep stdout/stderr unbuffered.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies and Node.js (version 20)
RUN apt-get update && apt-get install -y curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the dependency files first to leverage Docker cache
COPY backend/requirements.txt backend/requirements.txt
COPY frontend/package.json frontend/package.json
COPY frontend/package-lock.json frontend/package-lock.json

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install Node.js dependencies
RUN cd frontend && npm install --production

# Copy the rest of the application code
COPY . .

# Make the start script executable
RUN chmod +x start.sh

# Elastic Beanstalk maps port 80 to the port exposed by the container
EXPOSE 5000

# Start both servers using the existing script
CMD ["./start.sh"]
