"""
Final Router Service
Subscribes to msg.score, applies thresholds, publishes decision to msg.decision
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
INPUT_TOPIC = os.getenv('INPUT_TOPIC', 'msg.score')
OUTPUT_TOPIC = os.getenv('OUTPUT_TOPIC', 'msg.decision')
THRESHOLD_A = float(os.getenv('THRESHOLD_A', '0.3'))
THRESHOLD_B = float(os.getenv('THRESHOLD_B', '0.7'))

# Metrics
decisions_allow = 0
decisions_quarantine = 0
decisions_block = 0
errors_count = 0

def make_decision(score):
    """Apply thresholds to determine decision"""
    if score < THRESHOLD_A:
        return "ALLOW"
    elif score < THRESHOLD_B:
        return "QUARANTINE"
    else:
        return "BLOCK"

def on_message(client, userdata, msg):
    """Handle incoming score message"""
    global decisions_allow, decisions_quarantine, decisions_block, errors_count
    start_time = time.time()
    
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        trace = payload.get('trace', {})
        score = payload.get('score', 1.0)
        
        # Create child span
        span_id = str(uuid.uuid4())
        parent_span_id = trace.get('spanId')
        
        # Make decision
        decision = make_decision(score)
        
        # Update metrics
        if decision == "ALLOW":
            decisions_allow += 1
        elif decision == "QUARANTINE":
            decisions_quarantine += 1
        else:
            decisions_block += 1
        
        # Build response
        response = {
            "messageId": message_id,
            "timestamp": payload.get('timestamp'),
            "trace": {
                "traceId": trace.get('traceId'),
                "spanId": span_id,
                "parentSpanId": parent_span_id
            },
            "score": score,
            "decision": decision,
            "serviceName": "final-router"
        }
        
        # Publish decision
        client.publish(OUTPUT_TOPIC, json.dumps(response), qos=1)
        
        latency_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"messageId={message_id} "
            f"traceId={trace.get('traceId')} "
            f"serviceName=final-router "
            f"latencyMs={latency_ms:.2f} "
            f"eventType=decision_published "
            f"status=success "
            f"score={score:.2f} "
            f"decision={decision}"
        )
        
    except Exception as e:
        errors_count += 1
        logger.error(
            f"serviceName=final-router "
            f"eventType=processing_error "
            f"status=error "
            f"error={str(e)}"
        )

def main():
    logger.info(f"Final Router starting - Broker: {BROKER_HOST}:{BROKER_PORT}, Input: {INPUT_TOPIC}, Output: {OUTPUT_TOPIC}")
    logger.info(f"Thresholds - A: {THRESHOLD_A}, B: {THRESHOLD_B}")
    logger.info(f"Decision rules: score < {THRESHOLD_A} = ALLOW, {THRESHOLD_A} <= score < {THRESHOLD_B} = QUARANTINE, score >= {THRESHOLD_B} = BLOCK")
    
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe(INPUT_TOPIC, qos=1)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Final Router stopping...")
        logger.info(f"Metrics - ALLOW: {decisions_allow}, QUARANTINE: {decisions_quarantine}, BLOCK: {decisions_block}, Errors: {errors_count}")
        client.disconnect()

if __name__ == '__main__':
    main()

