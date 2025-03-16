import requests
import json
import logging
from datetime import datetime

def send_data_to_server(event_data):
    """
    Sensör verilerini merkezi sunucuya gönder
    
    Args:
        event_data: {
            'timestamp': float,
            'gps': (float, float),
            'audio_data': list,
            'sensor_id': str
        }
    """
    try:
        # Sunucu adresi (örnek)
        server_url = 'http://localhost:5000/api/event'
        
        # Veriyi JSON formatına dönüştür
        json_data = json.dumps(event_data)
        
        # Sunucuya POST isteği gönder
        response = requests.post(
            server_url,
            data=json_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Sunucu hatası: {response.status_code}")
            return False
            
    except Exception as e:
        logging.error(f"Veri gönderilemedi: {str(e)}")
        return False 