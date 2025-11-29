# Use an official Python runtime as a parent image
FROM python:alpine

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file initially
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev \
    && pip install --upgrade --no-cache-dir -r requirements.txt \
    && apk del gcc musl-dev libffi-dev openssl-dev

# Copy the application code into the container
COPY . .

# Expose the port for the ukbc server to run on
EXPOSE 8080

# Command to run your application using Uvicorn
CMD ["uvicorn", "server:create_app", "--host", "0.0.0.0", "--port", "8080"]
