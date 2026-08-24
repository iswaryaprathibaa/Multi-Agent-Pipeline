FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY src/ src/
COPY server/ server/
COPY data/ data/

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
