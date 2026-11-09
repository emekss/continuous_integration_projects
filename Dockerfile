FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    BOOKING_DB=/data/booking.db

WORKDIR /app
COPY app/ ./app/
COPY booking.py ./

RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "app.web"]
