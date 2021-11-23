FROM python:3.9.9-bullseye

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT [ "sanic", "main:app", "--host=0.0.0.0", "--port=8080" ]
