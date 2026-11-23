FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    BOOKING_DB=/data/booking.db

WORKDIR /app
COPY app/ ./app/
COPY booking.py ./
COPY --from=frontend /build/dist ./frontend/dist

RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "app.web"]
