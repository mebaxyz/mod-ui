FROM python:3.10-slim

WORKDIR /app

COPY services/mod-ui-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/mod-ui-service/main.py .

EXPOSE 8080

CMD ["python", "main.py"]