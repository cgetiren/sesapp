from flask import Flask, request, jsonify
import numpy as np
from triangulation import calculate_source_location
from notification import send_alert
from database import store_event, get_events
import time
from datetime import datetime, timedelta
import logging
from geopy.distance import geodesic
import threading
import queue

app = Flask(__name__)

class GunShotDetectionServer:
    def __init__(self):
        self.active_sensors = {}
        self.event_buffer = {}
        self.event_queue = queue.Queue()
        self.setup_logging()
        self.start_event_processor()
        
    def setup_logging(self):
        logging.basicConfig(
            filename='gunshot_detection.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def start_event_processor(self):
        self.processor_thread = threading.Thread(target=self.process_event_queue)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
    def process_event_queue(self):
        while True:
            try:
                event_key = self.event_queue.get(timeout=1.0)
                self.process_event_group(event_key)
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error processing event: {str(e)}")
                
    def validate_sensor_data(self, sensor_data):
        # Validate GPS coordinates
        for data in sensor_data:
            lat, lon = data['gps']
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False
                
        # Check time consistency
        timestamps = [data['timestamp'] for data in sensor_data]
        if max(timestamps) - min(timestamps) > 1.0:  # More than 1 second difference
            return False
            
        return True
        
    def calculate_time_differences(self, sensor_data):
        base_time = min(data['timestamp'] for data in sensor_data)
        return [data['timestamp'] - base_time for data in sensor_data]
        
    @app.route('/api/events', methods=['GET'])
    def get_recent_events(self):
        try:
            hours = int(request.args.get('hours', 24))
            since = datetime.now() - timedelta(hours=hours)
            events = get_events(since)
            return jsonify({'events': events})
        except Exception as e:
            logging.error(f"Error retrieving events: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
        
    @app.route('/api/event', methods=['POST'])
    def receive_event(self):
        event_data = request.json
        sensor_id = event_data['sensor_id']
        timestamp = event_data['timestamp']
        
        # Aynı olay için diğer sensörlerden gelen verileri grupla
        event_key = f"{timestamp:.1f}"
        if event_key not in self.event_buffer:
            self.event_buffer[event_key] = []
        self.event_buffer[event_key].append(event_data)
        
        # En az 3 sensörden veri geldiyse konumu hesapla
        if len(self.event_buffer[event_key]) >= 3:
            location = self.process_event(self.event_buffer[event_key])
            self.notify_authorities(location)
            
        return {'status': 'success'}
        
    def process_event(self, sensor_data):
        # Aykırı değer tespiti eklenebilir
        filtered_data = self.remove_outliers(sensor_data)
        sensor_locations = [data['gps'] for data in filtered_data]
        time_differences = self.calculate_time_differences(filtered_data)
        source_location = calculate_source_location(sensor_locations, time_differences)
        
        # Olayı veritabanına kaydet
        store_event({
            'timestamp': sensor_data[0]['timestamp'],
            'location': source_location,
            'sensor_data': sensor_data
        })
        
        return source_location
        
    def notify_authorities(self, location):
        alert_data = {
            'event_type': 'gunshot',
            'location': location,
            'timestamp': time.time()
        }
        send_alert(alert_data) 