FROM jupyter/scipy-notebook

# RUN apt-get update && apt-get install graphwiz
COPY requirements.txt .
RUN pip3 install -r requirements.txt