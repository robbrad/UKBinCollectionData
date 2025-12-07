FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del gcc musl-dev libffi-dev openssl-dev

COPY . .

EXPOSE 8080

CMD ["uvicorn", "server:create_app", "--host", "0.0.0.0", "--port", "8080"]
