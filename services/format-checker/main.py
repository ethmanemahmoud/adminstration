"""
Format Checker Service
Subscribes to msg.raw, checks format rules, publishes to msg.format.result
"""
import os
import json
import time
import uuid
import string
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
OUTPUT_TOPIC = os.getenv('OUTPUT_TOPIC', 'msg.format.result')

# Format rules (configurable via env)
MAX_LENGTH = int(os.getenv('MAX_LENGTH', '200'))
FORBIDDEN_CHARS = os.getenv('FORBIDDEN_CHARS', '|<>').split(',')
MAX_SYMBOL_RATIO = float(os.getenv('MAX_SYMBOL_RATIO', '0.3'))

# Metrics
messages_processed = 0
errors_count = 0

def check_format(content):
    """Check format rules"""
    violations = []
    score = 0.0
    
    # Check length
    if len(content) > MAX_LENGTH:
        violations.append(f"length_exceeded:{len(content)}")
        score += 0.3
    
    # Check forbidden characters
    found_forbidden = []
    for char in FORBIDDEN_CHARS:
        if char.strip() in content:
            found_forbidden.append(char.strip())
    if found_forbidden:
        violations.append(f"forbidden_chars:{','.join(found_forbidden)}")
        score += 0.3
    
    # Check symbol ratio
    symbol_count = sum(1 for c in content if c in string.punctuation)
    if len(content) > 0:
        symbol_ratio = symbol_count / len(content)
        if symbol_ratio > MAX_SYMBOL_RATIO:
            violations.append(f"high_symbol_ratio:{symbol_ratio:.2f}")
            score += 0.4
    
    score = min(1.0, score)
    
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "score": score
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
        result = check_format(content)
        
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
            "serviceName": "format-checker"
        }
        
        # Publish result
        client.publish(OUTPUT_TOPIC, json.dumps(response), qos=1)
        
        latency_ms = (time.time() - start_time) * 1000
        messages_processed += 1
        
        logger.info(
            f"messageId={message_id} "
            f"traceId={trace.get('traceId')} "
            f"serviceName=format-checker "
            f"latencyMs={latency_ms:.2f} "
            f"eventType=message_processed "
            f"status=success "
            f"result={result['passed']}"
        )
        
    except Exception as e:
        errors_count += 1
        logger.error(
            f"serviceName=format-checker "
            f"eventType=processing_error "
            f"status=error "
            f"error={str(e)}"
        )

def main():
    logger.info(f"Format Checker starting - Broker: {BROKER_HOST}:{BROKER_PORT}, Input: {INPUT_TOPIC}, Output: {OUTPUT_TOPIC}")
    logger.info(f"Rules - Max length: {MAX_LENGTH}, Forbidden chars: {FORBIDDEN_CHARS}, Max symbol ratio: {MAX_SYMBOL_RATIO}")
    
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe(INPUT_TOPIC, qos=1)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Format Checker stopping...")
        logger.info(f"Metrics - Processed: {messages_processed}, Errors: {errors_count}")
        client.disconnect()

if __name__ == '__main__':
    main()

