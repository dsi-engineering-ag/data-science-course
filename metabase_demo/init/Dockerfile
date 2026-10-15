FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache libpq

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.sql /app/schema.sql
COPY init_pipeline.py /app/init_pipeline.py

CMD ["python", "init_pipeline.py"]
