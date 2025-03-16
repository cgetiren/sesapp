import logging
from datetime import datetime
import json
from geopy.distance import geodesic

class NotificationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Demo mode için basit bildirim sistemi
        self.notifications = []

    def send_notification(self, message, notification_type='demo'):
        """Demo amaçlı bildirim gönderme"""
        self.notifications.append({
            'type': notification_type,
            'message': message,
            'timestamp': datetime.now()
        })
        return True

def send_alert(alert_data):
    """
    Silah sesi tespiti durumunda yetkililere bildirim gönderir.
    Bu demo versiyonunda sadece log dosyasına kayıt yapılır.
    
    Args:
        alert_data (dict): Olay bilgilerini içeren sözlük
            {
                'event_type': str,
                'location': tuple(float, float),
                'estimated_location': tuple(float, float),
                'timestamp': float
            }
    
    Returns:
        bool: Bildirim başarılı ise True, değilse False
    """
    try:
        # Bildirim verilerini hazırla
        notification = {
            'event_type': alert_data['event_type'],
            'actual_latitude': alert_data['location'][0],
            'actual_longitude': alert_data['location'][1],
            'estimated_latitude': alert_data['estimated_location'][0],
            'estimated_longitude': alert_data['estimated_location'][1],
            'timestamp': datetime.fromtimestamp(alert_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
            'severity': 'HIGH',
            'confidence': 0.95,
            'location_error': geodesic(
                alert_data['location'],
                alert_data['estimated_location']
            ).meters
        }
        
        # Log dosyasına kaydet
        with open('gunshot_alerts.log', 'a') as f:
            json.dump(notification, f)
            f.write('\n')
        
        return True
        
    except Exception as e:
        print(f"Bildirim gönderilirken hata oluştu: {str(e)}")
        return False 