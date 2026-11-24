FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py tokenalphabet_slugs.json ./

ENV DB_PATH=/data/alerts.db
VOLUME /data

CMD ["python", "bot.py"]
