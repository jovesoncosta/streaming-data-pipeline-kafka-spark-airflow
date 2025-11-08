#We start with a clean Python image.
FROM python:3.9-slim
#We define the working directory within the container
WORKDIR /app
#Copied the requirements file
COPY requirements.txt .
#Installed the libraries
RUN pip install --no-cache-dir -r requirements.txt
#Copied our script into the image
COPY producer.py .
#Will not be used by Airflow
CMD ["python", "producer.py"]