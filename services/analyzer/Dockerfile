FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY tests ./tests

EXPOSE 8090

CMD ["python", "-m", "src.main"]