"""
Aggregator Service
Subscribes to 3 result topics, joins results by messageId, publishes to msg.score
Implements timeout handling for missing results
"""
import os
import json
import time
import uuid
import threading
from collections import defaultdict
from datetime import datetime
import paho.mqtt.client as mqtt
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BROKER_HOST = os.getenv('BROKER_HOST', 'localhost')
BROKER_PORT = int(os.getenv('BROKER_PORT', '1883'))
TOPIC_KEYWORD = os.getenv('TOPIC_KEYWORD', 'msg.keyword.result')
TOPIC_URL = os.getenv('TOPIC_URL', 'msg.url.result')
TOPIC_FORMAT = os.getenv('TOPIC_FORMAT', 'msg.format.result')
OUTPUT_TOPIC = os.getenv('OUTPUT_TOPIC', 'msg.score')
JOIN_TIMEOUT_SECONDS = int(os.getenv('JOIN_TIMEOUT_SECONDS', '3'))

# Storage for pending results
pending_results = defaultdict(dict)  # messageId -> {keyword: result, url: result, format: result, timestamp: ...}
pending_lock = threading.Lock()

# MQTT client for publishing (initialized in main)
client = None

# Metrics
messages_processed = 0
timeouts_count = 0
errors_count = 0

def calculate_score(keyword_result, url_result, format_result):
    """Calculate global score from all results"""
    scores = []
    
    if keyword_result:
        scores.append(keyword_result.get('score', 0.0))
    if url_result:
        scores.append(url_result.get('score', 0.0))
    if format_result:
        scores.append(format_result.get('score', 0.0))
    
    if not scores:
        return 1.0  # Worst case if no results
    
    # Average of all scores
    return sum(scores) / len(scores)

def check_timeouts():
    """Periodically check for timed-out messages"""
    global timeouts_count
    
    while True:
        time.sleep(1)  # Check every second
        current_time = time.time()
        
        with pending_lock:
            timed_out = []
            for message_id, results in list(pending_results.items()):
                timestamp = results.get('timestamp', 0)
                if current_time - timestamp > JOIN_TIMEOUT_SECONDS:
                    timed_out.append(message_id)
            
            for message_id in timed_out:
                results = pending_results.pop(message_id)
                keyword_result = results.get('keyword')
                url_result = results.get('url')
                format_result = results.get('format')
                
                # Calculate score with available results (degraded mode)
                score = calculate_score(keyword_result, url_result, format_result)
                
                # If missing results, increase score (more suspicious)
                missing_count = sum([
                    1 if not keyword_result else 0,
                    1 if not url_result else 0,
                    1 if not format_result else 0
                ])
                if missing_count > 0:
                    score = min(1.0, score + (missing_count * 0.2))
                    timeouts_count += 1
                    logger.warning(
                        f"messageId={message_id} "
                        f"serviceName=aggregator "
                        f"eventType=timeout "
                        f"missingResults={missing_count} "
                        f"degradedScore={score:.2f}"
                    )
                
                # Publish degraded result
                publish_score(message_id, score, results.get('trace', {}), degraded=True)

def publish_score(message_id, score, trace, degraded=False):
    """Publish score to output topic"""
    global messages_processed, client
    
    if client is None:
        logger.error("MQTT client not initialized")
        return
    
    span_id = str(uuid.uuid4())
    parent_span_id = trace.get('spanId')
    
    response = {
        "messageId": message_id,
        "timestamp": datetime.utcnow().isoformat(),
        "trace": {
            "traceId": trace.get('traceId'),
            "spanId": span_id,
            "parentSpanId": parent_span_id
        },
        "score": score,
        "degraded": degraded,
        "serviceName": "aggregator"
    }
    
    client.publish(OUTPUT_TOPIC, json.dumps(response), qos=1)
    messages_processed += 1
    
    logger.info(
        f"messageId={message_id} "
        f"traceId={trace.get('traceId')} "
        f"serviceName=aggregator "
        f"eventType=score_published "
        f"status=success "
        f"score={score:.2f} "
        f"degraded={degraded}"
    )

def process_result(message_id, result_type, payload):
    """Process a result and check if we can aggregate"""
    global errors_count
    
    try:
        trace = payload.get('trace', {})
        result = payload.get('result', {})
        
        with pending_lock:
            if message_id not in pending_results:
                pending_results[message_id] = {
                    'timestamp': time.time(),
                    'trace': trace
                }
            
            pending_results[message_id][result_type] = result
            
            # Check if we have all 3 results
            keyword_result = pending_results[message_id].get('keyword')
            url_result = pending_results[message_id].get('url')
            format_result = pending_results[message_id].get('format')
            
            if keyword_result and url_result and format_result:
                # Calculate score
                score = calculate_score(keyword_result, url_result, format_result)
                
                # Remove from pending and publish
                trace = pending_results[message_id].get('trace', {})
                del pending_results[message_id]
                
                publish_score(message_id, score, trace, degraded=False)
                
    except Exception as e:
        errors_count += 1
        logger.error(
            f"serviceName=aggregator "
            f"eventType=processing_error "
            f"status=error "
            f"error={str(e)}"
        )

def on_message_keyword(client, userdata, msg):
    """Handle keyword result"""
    payload = json.loads(msg.payload.decode())
    message_id = payload.get('messageId')
    process_result(message_id, 'keyword', payload)

def on_message_url(client, userdata, msg):
    """Handle URL result"""
    payload = json.loads(msg.payload.decode())
    message_id = payload.get('messageId')
    process_result(message_id, 'url', payload)

def on_message_format(client, userdata, msg):
    """Handle format result"""
    payload = json.loads(msg.payload.decode())
    message_id = payload.get('messageId')
    process_result(message_id, 'format', payload)

def main():
    global client
    
    logger.info(f"Aggregator starting - Broker: {BROKER_HOST}:{BROKER_PORT}")
    
    # Initialize publishing client first
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    logger.info(f"Input topics: {TOPIC_KEYWORD}, {TOPIC_URL}, {TOPIC_FORMAT}")
    logger.info(f"Output topic: {OUTPUT_TOPIC}, Timeout: {JOIN_TIMEOUT_SECONDS}s")
    
    # Start timeout checker thread
    timeout_thread = threading.Thread(target=check_timeouts, daemon=True)
    timeout_thread.start()
    
    # Create MQTT clients for each topic
    client_keyword = mqtt.Client()
    client_keyword.on_message = on_message_keyword
    client_keyword.connect(BROKER_HOST, BROKER_PORT, 60)
    client_keyword.subscribe(TOPIC_KEYWORD, qos=1)
    
    client_url = mqtt.Client()
    client_url.on_message = on_message_url
    client_url.connect(BROKER_HOST, BROKER_PORT, 60)
    client_url.subscribe(TOPIC_URL, qos=1)
    
    client_format = mqtt.Client()
    client_format.on_message = on_message_format
    client_format.connect(BROKER_HOST, BROKER_PORT, 60)
    client_format.subscribe(TOPIC_FORMAT, qos=1)
    
    try:
        # Start loops in separate threads
        threading.Thread(target=client_keyword.loop_forever, daemon=True).start()
        threading.Thread(target=client_url.loop_forever, daemon=True).start()
        threading.Thread(target=client_format.loop_forever, daemon=True).start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Aggregator stopping...")
        logger.info(f"Metrics - Processed: {messages_processed}, Timeouts: {timeouts_count}, Errors: {errors_count}")
        client_keyword.disconnect()
        client_url.disconnect()
        client_format.disconnect()
        client.disconnect()

if __name__ == '__main__':
    main()

