from __future__ import annotations

import json
import os
import sys

try:
    import pika
except ImportError:  # pragma: no cover - pika optional outside docker
    pika = None

QUEUE = os.environ.get("RABBITMQ_QUEUE", "booking_events")
HOST = os.environ.get("RABBITMQ_HOST", "localhost")


def publish(event: dict) -> None:
    if pika is None:
        return
    try:
        params = pika.ConnectionParameters(
            host=HOST, connection_attempts=1, socket_timeout=1
        )
        conn = pika.BlockingConnection(params)
        channel = conn.channel()
        channel.queue_declare(queue=QUEUE, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        conn.close()
    except Exception:
        print(
            f"warning: could not publish event {event.get('event')}",
            file=sys.stderr,
        )
