"""
Keyword Filter Service
Subscribes to msg.raw, filters based on keyword blacklist, publishes to msg.keyword.result
"""
import os
import json
import time
import uuid
import paho.mqtt.client as mqtt
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BROKER_HOST = os.getenv('BROKER_HOST', 'localhost')
BROKER_PORT = int(os.getenv('BROKER_PORT', '1883'))
INPUT_TOPIC = os.getenv('INPUT_TOPIC', 'msg.raw')
OUTPUT_TOPIC = os.getenv('OUTPUT_TOPIC', 'msg.keyword.result')

# Keyword blacklist (configurable via env)
BLACKLIST = os.getenv('KEYWORD_BLACKLIST', 'URGENT,WIN,CLICK,OFFER').split(',')

# Metrics
messages_processed = 0
errors_count = 0

def check_keywords(content):
    """Check if content contains blacklisted keywords"""
    content_upper = content.upper()
    found_keywords = []
    
    for keyword in BLACKLIST:
        if keyword.strip().upper() in content_upper:
            found_keywords.append(keyword.strip())
    
    return {
        "passed": len(found_keywords) == 0,
        "foundKeywords": found_keywords,
        "score": 0.0 if len(found_keywords) == 0 else min(1.0, len(found_keywords) * 0.3)
    }

def on_message(client, userdata, msg):
    """Handle incoming message"""
    global messages_processed, errors_count
    start_time = time.time()
    
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        trace = payload.get('trace', {})
        content = payload.get('content', '')
        
        # Create child span
        span_id = str(uuid.uuid4())
        parent_span_id = trace.get('spanId')
        
        # Process
        result = check_keywords(content)
        
        # Build response
        response = {
            "messageId": message_id,
            "timestamp": payload.get('timestamp'),
            "trace": {
                "traceId": trace.get('traceId'),
                "spanId": span_id,
                "parentSpanId": parent_span_id
            },
            "result": result,
            "serviceName": "keyword-filter"
        }
        
        # Publish result
        client.publish(OUTPUT_TOPIC, json.dumps(response), qos=1)
        
        latency_ms = (time.time() - start_time) * 1000
        messages_processed += 1
        
        logger.info(
            f"messageId={message_id} "
            f"traceId={trace.get('traceId')} "
            f"serviceName=keyword-filter "
            f"latencyMs={latency_ms:.2f} "
            f"eventType=message_processed "
            f"status=success "
            f"result={result['passed']}"
        )
        
    except Exception as e:
        errors_count += 1
        logger.error(
            f"serviceName=keyword-filter "
            f"eventType=processing_error "
            f"status=error "
            f"error={str(e)}"
        )

def main():
    logger.info(f"Keyword Filter starting - Broker: {BROKER_HOST}:{BROKER_PORT}, Input: {INPUT_TOPIC}, Output: {OUTPUT_TOPIC}")
    logger.info(f"Blacklist: {BLACKLIST}")
    
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe(INPUT_TOPIC, qos=1)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Keyword Filter stopping...")
        logger.info(f"Metrics - Processed: {messages_processed}, Errors: {errors_count}")
        client.disconnect()

if __name__ == '__main__':
    main()

