"""
Generator Service
Publishes raw messages to msg.raw topic every N seconds
"""
import os
import time
import json
import uuid
from datetime import datetime
import paho.mqtt.client as mqtt
import logging

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BROKER_HOST = os.getenv('BROKER_HOST', 'localhost')
BROKER_PORT = int(os.getenv('BROKER_PORT', '1883'))
RAW_TOPIC = os.getenv('RAW_TOPIC', 'msg.raw')
INTERVAL_SECONDS = int(os.getenv('INTERVAL_SECONDS', '5'))

# MQTT Client
client = mqtt.Client()
client.connect(BROKER_HOST, BROKER_PORT, 60)

def generate_message():
    """Generate a raw message with trace information"""
    message_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    
    # Sample content (can be varied)
    sample_contents = [
        "Check out this amazing offer! Click here: http://suspicious-site.com",
        "Hello world, this is a normal message",
        "URGENT!!! WIN $1000000 NOW!!!",
        "Visit https://example.com for more info",
        "Normal business communication"
    ]
    import random
    content = random.choice(sample_contents)
    
    message = {
        "messageId": message_id,
        "timestamp": datetime.utcnow().isoformat(),
        "content": content,
        "trace": {
            "traceId": trace_id,
            "spanId": span_id,
            "parentSpanId": None
        }
    }
    
    return message

def publish_message():
    """Publish a message to the raw topic"""
    message = generate_message()
    payload = json.dumps(message)
    
    start_time = time.time()
    result = client.publish(RAW_TOPIC, payload, qos=1)
    
    latency_ms = (time.time() - start_time) * 1000
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        logger.info(
            f"messageId={message['messageId']} "
            f"traceId={message['trace']['traceId']} "
            f"serviceName=generator "
            f"latencyMs={latency_ms:.2f} "
            f"eventType=message_published "
            f"status=success"
        )
    else:
        logger.error(
            f"messageId={message['messageId']} "
            f"serviceName=generator "
            f"eventType=message_publish_error "
            f"status=error"
        )

def main():
    logger.info(f"Generator starting - Broker: {BROKER_HOST}:{BROKER_PORT}, Topic: {RAW_TOPIC}, Interval: {INTERVAL_SECONDS}s")
    
    try:
        while True:
            publish_message()
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Generator stopping...")
        client.disconnect()

if __name__ == '__main__':
    main()

