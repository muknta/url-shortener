# The first instruction is what image we want to base our container on
# We Use an official Python runtime as a parent image
FROM python:3.9.6

# The enviroment variable ensures that the python output is set straight
# to the terminal with out buffering it first
ENV PYTHONUNBUFFERED 1

# create root directory for our project in the container
RUN mkdir -p /url_shortener

# Set the working directory to /url_shortener
WORKDIR /url_shortener

# Copy the current directory contents into the container at /url_shortener
ADD . /url_shortener/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt
