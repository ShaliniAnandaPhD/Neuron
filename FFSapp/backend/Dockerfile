# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's source code to the container at /app
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0 # Listen on all available network interfaces
ENV FLASK_ENV=development # Set to development for auto-reloading during dev

# Expose the port that Flask will run on
EXPOSE 5000

# Command to run the Flask application
# Use a more robust server like Gunicorn for production, but flask run is fine for development
CMD ["flask", "run"]
