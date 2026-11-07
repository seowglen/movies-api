FROM python:3.15-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

CMD ["sh", "-c", "python -m uvicorn serve:app --host 0.0.0.0 --port ${PORT}"]
