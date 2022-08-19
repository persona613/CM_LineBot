# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /main
WORKDIR $APP_HOME

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/ultralytics/yolov5

COPY . ./

# Install production dependencies.
RUN pip install --upgrade pip && \
    pip install -r requirements_init.txt && \
    pip install -r https://raw.githubusercontent.com/ultralytics/yolov5/master/requirements.txt
    
# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app