# Use a base Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy only the requirements file first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port your app runs on
EXPOSE 5000

# Set non-sensitive environment variables
ENV FLASK_ENV=docker

# Command to run the Flask app
CMD ["python", "app.py"]
