import os

from aiokafka import AIOKafkaProducer
import asyncio

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")


async def send_log_message():
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP_SERVERS)
    try:
        await producer.start()
        log_message = b"Error: High CPU detected in Service A"
        await producer.send_and_wait("logs", log_message)
        print("Log message sent successfully.")
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(send_log_message())
    