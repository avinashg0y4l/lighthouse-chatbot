# Dockerfile (Corrected for Refactored Structure)

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

# Copy the entire src package AND the run.py script
COPY ./src /app/src
COPY run.py .

# Make port 5000 available to network outside this container
EXPOSE 5000

#Dockerfile creates a directory for uploads
# This is where the uploaded files will be stored
RUN mkdir -p /app/uploads

# Use the run.py script to start the app via the factory
CMD ["python", "run.py"]