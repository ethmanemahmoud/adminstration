"""
UI Dashboard Service
Subscribes to MQTT topics and displays real-time data via WebSocket
"""
import os
import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BROKER_HOST = os.getenv('BROKER_HOST', 'localhost')
BROKER_PORT = int(os.getenv('BROKER_PORT', '1883'))
TOPIC_RAW = os.getenv('TOPIC_RAW', 'msg.raw')
TOPIC_KEYWORD_RESULT = os.getenv('TOPIC_KEYWORD_RESULT', 'msg.keyword.result')
TOPIC_URL_RESULT = os.getenv('TOPIC_URL_RESULT', 'msg.url.result')
TOPIC_FORMAT_RESULT = os.getenv('TOPIC_FORMAT_RESULT', 'msg.format.result')
TOPIC_SCORE = os.getenv('TOPIC_SCORE', 'msg.score')
TOPIC_DECISION = os.getenv('TOPIC_DECISION', 'msg.decision')

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ui-dashboard-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Storage for tracking messages
message_tracking = {}  # messageId -> {raw, keyword, url, format, score, decision, timestamps}

# MQTT clients
mqtt_clients = []

def calculate_latency(message_id):
    """Calculate latency from raw message to decision"""
    if message_id not in message_tracking:
        return None
    
    data = message_tracking[message_id]
    if 'raw_timestamp' in data and 'decision_timestamp' in data:
        try:
            raw_time = datetime.fromisoformat(data['raw_timestamp'].replace('Z', '+00:00'))
            decision_time = datetime.fromisoformat(data['decision_timestamp'].replace('Z', '+00:00'))
            delta = decision_time - raw_time
            return delta.total_seconds() * 1000  # Convert to milliseconds
        except:
            return None
    return None

def on_mqtt_connect(client, userdata, flags, rc):
    """Callback when MQTT client connects"""
    if rc == 0:
        logger.info(f"MQTT client connected: {client._client_id}")
    else:
        logger.error(f"MQTT connection failed with code {rc}")

def on_mqtt_message_raw(client, userdata, msg):
    """Handle raw messages"""
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        timestamp = payload.get('timestamp')
        
        if message_id not in message_tracking:
            message_tracking[message_id] = {}
        
        message_tracking[message_id]['raw'] = payload
        message_tracking[message_id]['raw_timestamp'] = timestamp
        
        # Emit to WebSocket clients
        socketio.emit('raw_message', {
            'messageId': message_id,
            'content': payload.get('content', ''),
            'timestamp': timestamp,
            'traceId': payload.get('trace', {}).get('traceId')
        })
        
        logger.debug(f"Raw message received: {message_id}")
    except Exception as e:
        logger.error(f"Error processing raw message: {e}")

def on_mqtt_message_keyword(client, userdata, msg):
    """Handle keyword filter results"""
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        result = payload.get('result', {})
        
        if message_id not in message_tracking:
            message_tracking[message_id] = {}
        
        message_tracking[message_id]['keyword'] = result
        
        socketio.emit('keyword_result', {
            'messageId': message_id,
            'passed': result.get('passed', False),
            'score': result.get('score', 0.0),
            'foundKeywords': result.get('foundKeywords', [])
        })
    except Exception as e:
        logger.error(f"Error processing keyword result: {e}")

def on_mqtt_message_url(client, userdata, msg):
    """Handle URL inspector results"""
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        result = payload.get('result', {})
        
        if message_id not in message_tracking:
            message_tracking[message_id] = {}
        
        message_tracking[message_id]['url'] = result
        
        socketio.emit('url_result', {
            'messageId': message_id,
            'passed': result.get('passed', False),
            'score': result.get('score', 0.0),
            'foundUrls': result.get('foundUrls', [])
        })
    except Exception as e:
        logger.error(f"Error processing URL result: {e}")

def on_mqtt_message_format(client, userdata, msg):
    """Handle format checker results"""
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        result = payload.get('result', {})
        
        if message_id not in message_tracking:
            message_tracking[message_id] = {}
        
        message_tracking[message_id]['format'] = result
        
        socketio.emit('format_result', {
            'messageId': message_id,
            'passed': result.get('passed', False),
            'score': result.get('score', 0.0),
            'violations': result.get('violations', [])
        })
    except Exception as e:
        logger.error(f"Error processing format result: {e}")

def on_mqtt_message_score(client, userdata, msg):
    """Handle aggregated scores"""
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        score = payload.get('score', 0.0)
        degraded = payload.get('degraded', False)
        
        if message_id not in message_tracking:
            message_tracking[message_id] = {}
        
        message_tracking[message_id]['score'] = score
        message_tracking[message_id]['degraded'] = degraded
        
        socketio.emit('score_message', {
            'messageId': message_id,
            'score': score,
            'degraded': degraded
        })
    except Exception as e:
        logger.error(f"Error processing score: {e}")

def on_mqtt_message_decision(client, userdata, msg):
    """Handle final decisions"""
    try:
        payload = json.loads(msg.payload.decode())
        message_id = payload.get('messageId')
        decision = payload.get('decision', 'UNKNOWN')
        score = payload.get('score', 0.0)
        timestamp = payload.get('timestamp')
        
        if message_id not in message_tracking:
            message_tracking[message_id] = {}
        
        message_tracking[message_id]['decision'] = decision
        message_tracking[message_id]['decision_timestamp'] = timestamp
        
        # Calculate latency
        latency = calculate_latency(message_id)
        
        # Get all data for this message
        data = message_tracking.get(message_id, {})
        
        socketio.emit('decision_message', {
            'messageId': message_id,
            'decision': decision,
            'score': score,
            'timestamp': timestamp,
            'latency': latency,
            'raw': data.get('raw', {}),
            'keyword': data.get('keyword', {}),
            'url': data.get('url', {}),
            'format': data.get('format', {}),
            'aggregatedScore': data.get('score', 0.0),
            'degraded': data.get('degraded', False)
        })
        
        logger.info(f"Decision received: {message_id} -> {decision} (latency: {latency}ms)")
    except Exception as e:
        logger.error(f"Error processing decision: {e}")

def setup_mqtt_client(topic, callback, client_id_suffix):
    """Setup and return an MQTT client"""
    client = mqtt.Client(client_id=f"ui-dashboard-{client_id_suffix}")
    client.on_connect = on_mqtt_connect
    client.on_message = callback
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe(topic, qos=1)
    return client

@app.route('/')
def index():
    """Serve the dashboard page"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info('WebSocket client connected')
    emit('status', {'message': 'Connected to dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info('WebSocket client disconnected')

def start_mqtt_clients():
    """Start all MQTT clients in separate threads"""
    global mqtt_clients
    
    # Create clients for each topic
    clients = [
        (TOPIC_RAW, on_mqtt_message_raw, 'raw'),
        (TOPIC_KEYWORD_RESULT, on_mqtt_message_keyword, 'keyword'),
        (TOPIC_URL_RESULT, on_mqtt_message_url, 'url'),
        (TOPIC_FORMAT_RESULT, on_mqtt_message_format, 'format'),
        (TOPIC_SCORE, on_mqtt_message_score, 'score'),
        (TOPIC_DECISION, on_mqtt_message_decision, 'decision'),
    ]
    
    for topic, callback, suffix in clients:
        client = setup_mqtt_client(topic, callback, suffix)
        mqtt_clients.append(client)
        
        # Start client loop in a separate thread
        thread = threading.Thread(target=client.loop_forever, daemon=True)
        thread.start()
        logger.info(f"Started MQTT client for {topic}")

def main():
    """Main function"""
    logger.info(f"UI Dashboard starting - MQTT Broker: {BROKER_HOST}:{BROKER_PORT}")
    logger.info(f"Subscribing to: {TOPIC_RAW}, {TOPIC_KEYWORD_RESULT}, {TOPIC_URL_RESULT}, {TOPIC_FORMAT_RESULT}, {TOPIC_SCORE}, {TOPIC_DECISION}")
    
    # Start MQTT clients
    start_mqtt_clients()
    
    # Wait a bit for MQTT connections
    time.sleep(2)
    
    # Start Flask app
    port = int(os.getenv('PORT', '5000'))
    logger.info(f"Starting Flask server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()

