from pymongo import MongoClient
import logging
from datetime import datetime

class Database:
    def __init__(self):
        try:
            self.client = MongoClient('mongodb://localhost:27017/')
            self.db = self.client['gunshot_detection']
            self.events = self.db['events']
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            self.logger.error(f"Veritabanı bağlantısı başarısız: {str(e)}")
            raise

def store_event(event_data):
    """
    Olay verilerini veritabanına kaydet
    
    Args:
        event_data: {
            'timestamp': float,
            'location': (float, float),
            'sensor_data': list
        }
    """
    try:
        db = Database()
        event_data['created_at'] = datetime.now()
        db.events.insert_one(event_data)
        return True
    except Exception as e:
        logging.error(f"Olay kaydedilemedi: {str(e)}")
        return False

def get_events(since_datetime):
    """
    Belirli bir tarihten sonraki olayları getir
    
    Args:
        since_datetime: datetime object
    """
    try:
        db = Database()
        events = db.events.find({
            'timestamp': {'$gte': since_datetime.timestamp()}
        }).sort('timestamp', -1)
        
        return list(events)
    except Exception as e:
        logging.error(f"Olaylar getirilemedi: {str(e)}")
        return [] 