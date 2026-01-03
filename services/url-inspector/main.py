"""
URL Inspector Service
Subscribes to msg.raw, inspects URLs and domains, publishes to msg.url.result
"""
import os
import json
import time
import uuid
import re
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
OUTPUT_TOPIC = os.getenv('OUTPUT_TOPIC', 'msg.url.result')

# Suspicious domains (configurable via env)
SUSPICIOUS_DOMAINS = os.getenv('SUSPICIOUS_DOMAINS', 'suspicious-site.com,spam-domain.net').split(',')

# Metrics
messages_processed = 0
errors_count = 0

def extract_urls(content):
    """Extract URLs from content"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, content, re.IGNORECASE)
    return urls

def check_urls(content):
    """Check URLs and domains for suspicious patterns"""
    urls = extract_urls(content)
    suspicious_urls = []
    suspicious_domains = []
    
    for url in urls:
        # Check for suspicious domains
        for domain in SUSPICIOUS_DOMAINS:
            if domain.strip().lower() in url.lower():
                suspicious_domains.append(domain.strip())
                suspicious_urls.append(url)
                break
    
    # Score based on findings
    score = 0.0
    if suspicious_urls:
        score = min(1.0, len(suspicious_urls) * 0.4)
    
    return {
        "passed": len(suspicious_urls) == 0,
        "urlsFound": len(urls),
        "suspiciousUrls": suspicious_urls,
        "suspiciousDomains": list(set(suspicious_domains)),
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
        result = check_urls(content)
        
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
            "serviceName": "url-inspector"
        }
        
        # Publish result
        client.publish(OUTPUT_TOPIC, json.dumps(response), qos=1)
        
        latency_ms = (time.time() - start_time) * 1000
        messages_processed += 1
        
        logger.info(
            f"messageId={message_id} "
            f"traceId={trace.get('traceId')} "
            f"serviceName=url-inspector "
            f"latencyMs={latency_ms:.2f} "
            f"eventType=message_processed "
            f"status=success "
            f"result={result['passed']}"
        )
        
    except Exception as e:
        errors_count += 1
        logger.error(
            f"serviceName=url-inspector "
            f"eventType=processing_error "
            f"status=error "
            f"error={str(e)}"
        )

def main():
    logger.info(f"URL Inspector starting - Broker: {BROKER_HOST}:{BROKER_PORT}, Input: {INPUT_TOPIC}, Output: {OUTPUT_TOPIC}")
    logger.info(f"Suspicious domains: {SUSPICIOUS_DOMAINS}")
    
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe(INPUT_TOPIC, qos=1)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("URL Inspector stopping...")
        logger.info(f"Metrics - Processed: {messages_processed}, Errors: {errors_count}")
        client.disconnect()

if __name__ == '__main__':
    main()

