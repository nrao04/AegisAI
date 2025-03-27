from aiokafka import AIOKafkaProducer
import asyncio

# async funct to simulate log ingestion using
async def send_log_message():
    producer = AIOKafkaProducer(bootstrap_servers = 'localhost:9092')
    
    # start the kafka producer
    await producer.start()
    try:
        # simulated log message as bytes
        log_message = b"Error: High CPU detected in Service A"
        
        # send log message to 'logs' topic and wait for confirmation
        await producer.send_and_wait("logs", log_message)
        print("Log message sent successfully.")
    finally:
        # always ensure the producer is stopped to clean up resources
        await producer.stop()

# main event loop to execute send_log_message
if __name__ == "__main__":
    asyncio.run(send_log_message())
    