FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    BOOKING_DB=/data/booking.db

WORKDIR /app
COPY app/ ./app/
COPY booking.py ./

RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001

ENTRYPOINT ["python", "booking.py"]
