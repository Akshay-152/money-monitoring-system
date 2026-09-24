FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY frontend frontend
COPY data data
ENV PYTHONUNBUFFERED=1
EXPOSE 5000
CMD ["python", "-m", "backend.api.app"]
