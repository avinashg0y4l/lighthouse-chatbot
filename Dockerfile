# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install packages specified in requirements.txt
# --no-cache-dir reduces image size slightly
# --trusted-host pypi.python.org helps in some network environments
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application code (everything in src folder) into the container
COPY ./src /app/src

# Make port 5000 available to network outside this container
EXPOSE 5000

# Command to run when the container starts
# Uses Flask's built-in server for development
# For production, you'd typically use Gunicorn or uWSGI
CMD ["flask", "--app", "src/app:app", "run", "--host=0.0.0.0", "--port=5000"]