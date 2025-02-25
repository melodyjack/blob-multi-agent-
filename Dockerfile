# Dockerfile

FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy dependency file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Command to run your bot
CMD ["python", "-m", "src.main"]
