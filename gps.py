import serial
import pynmea2
import time
import logging

class GPS:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.logger = logging.getLogger(__name__)
        self.serial_port = None
        self.connect()
        
    def connect(self):
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
        except Exception as e:
            self.logger.error(f"GPS bağlantısı başarısız: {str(e)}")
            raise
            
    def get_coordinates(self):
        """GPS koordinatlarını al"""
        try:
            while True:
                line = self.serial_port.readline().decode('ascii', errors='replace')
                if line.startswith('$GPGGA'):
                    msg = pynmea2.parse(line)
                    latitude = msg.latitude
                    longitude = msg.longitude
                    return (latitude, longitude)
                    
        except Exception as e:
            self.logger.error(f"GPS koordinatları alınamadı: {str(e)}")
            # Hata durumunda varsayılan konum (örnek)
            return (41.015137, 28.979530) 