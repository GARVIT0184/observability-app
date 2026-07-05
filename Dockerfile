FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Most platforms (Render, Railway, Fly.io) inject $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

CMD ["python", "app.py"]
