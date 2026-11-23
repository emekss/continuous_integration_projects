from __future__ import annotations

import json
import time

import pika

from app.notify import HOST, QUEUE


def main() -> None:  # pragma: no cover - long-running worker
    while True:
        try:
            conn = pika.BlockingConnection(pika.ConnectionParameters(host=HOST))
            break
        except pika.exceptions.AMQPConnectionError:
            print("waiting for rabbitmq...", flush=True)
            time.sleep(2)

    channel = conn.channel()
    channel.queue_declare(queue=QUEUE, durable=True)

    def on_message(ch, method, properties, body):
        event = json.loads(body)
        name = event.get("apartment", {}).get("name", "?")
        print(
            f"Notification to {event.get('user')}: "
            f"{event.get('event')} — {name}",
            flush=True,
        )
        ch.basic_ack(method.delivery_tag)

    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
    print(f"listening on queue {QUEUE}...", flush=True)
    channel.start_consuming()


if __name__ == "__main__":
    main()
