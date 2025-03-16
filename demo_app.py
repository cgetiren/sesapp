import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QFrame
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
import time
import random
from datetime import datetime
import json
from notification import send_alert
import folium
from folium import plugins
import os
from geopy.distance import geodesic
import numpy as np
import threading
import geopy.point
from folium.plugins import Draw, MousePosition
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

class Bridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent
        
    @pyqtSlot(str, str, float, float)
    def markerDragged(self, event_type, sensor_name, lat, lon):
        """JavaScript'ten gelen marker sürükleme olayını işle"""
        if event_type == "dragend":
            self.app.update_sensor_position(sensor_name, lat, lon)

class GunShotDetectionDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Silah Sesi Tespit Sistemi - Demo")
        self.setGeometry(100, 100, 1200, 800)
        
        # İstanbul'da örnek bir bölge (Kadıköy)
        self.center_location = (40.990743, 29.029734)
        self.radius = 200  # metre cinsinden yarıçap
        
        # Son silah sesi konumu
        self.last_gunshot = None
        
        # Sensör konumları (GPS koordinatları)
        self.sensors = {
            "Mikrofon 1": (40.991743, 29.028734),  # ~100m kuzey
            "Mikrofon 2": (40.989743, 29.028734),  # ~100m güney
            "Mikrofon 3": (40.990743, 29.030734),  # ~100m doğu
            "Mikrofon 4": (40.990743, 29.027734),  # ~100m batı
            "Mikrofon 5": (40.991243, 29.029234),  # ~50m kuzeydoğu
            "Mikrofon 6": (40.990243, 29.029234),  # ~50m güneydoğu
            "Mikrofon 7": (40.990243, 29.028234),  # ~50m güneybatı
            "Mikrofon 8": (40.991243, 29.028234),  # ~50m kuzeybatı
            "Mikrofon 9": self.center_location      # merkez
        }
        
        # HTTP sunucusu için port
        self.port = self.find_free_port()
        
        # Web kanalı kurulumu
        self.channel = QWebChannel()
        self.bridge = Bridge(self)
        self.channel.registerObject("bridge", self.bridge)
        
        self.setup_ui()
        self.create_initial_map()
        self.start_http_server()
        
    def find_free_port(self):
        """Boş bir port bul"""
        with socketserver.TCPServer(("localhost", 0), None) as s:
            return s.server_address[1]
        
    def start_http_server(self):
        """HTTP sunucusunu başlat"""
        handler = SimpleHTTPRequestHandler
        self.httpd = HTTPServer(("localhost", self.port), handler)
        
        # Sunucuyu ayrı bir thread'de başlat
        server_thread = threading.Thread(target=self.httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
    def setup_ui(self):
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Ana layout
        layout = QHBoxLayout(central_widget)
        
        # Sol panel (harita)
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        
        # Web görüntüleyici
        self.web_view = QWebEngineView()
        left_layout.addWidget(self.web_view)
        
        # Sağ panel
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.StyledPanel)
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)
        
        # Sensör durumları
        sensor_frame = QFrame()
        sensor_frame.setFrameStyle(QFrame.StyledPanel)
        sensor_layout = QVBoxLayout(sensor_frame)
        sensor_layout.addWidget(QLabel("Sensör Durumları"))
        
        for sensor_name in self.sensors:
            sensor_layout.addWidget(QLabel(f"{sensor_name}: Aktif"))
        
        right_layout.addWidget(sensor_frame)
        
        # Kontrol butonları
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_layout = QVBoxLayout(control_frame)
        control_layout.addWidget(QLabel("Demo Kontrolleri"))
        
        simulate_btn = QPushButton("Silah Sesi Simüle Et")
        simulate_btn.clicked.connect(self.simulate_gunshot)
        control_layout.addWidget(simulate_btn)
        
        randomize_btn = QPushButton("Mikrofonları Rastgele Yerleştir")
        randomize_btn.clicked.connect(self.randomize_sensors)
        control_layout.addWidget(randomize_btn)
        
        refresh_btn = QPushButton("Haritayı Yenile")
        refresh_btn.clicked.connect(self.refresh_map)
        control_layout.addWidget(refresh_btn)
        
        right_layout.addWidget(control_frame)
        
        # Log alanı
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.StyledPanel)
        log_layout = QVBoxLayout(log_frame)
        log_layout.addWidget(QLabel("Sistem Logları"))
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        right_layout.addWidget(log_frame)
        
        # Panelleri ana layout'a ekle
        layout.addWidget(left_panel, stretch=1)
        layout.addWidget(right_panel)
        
    def create_initial_map(self):
        # Haritayı oluştur
        m = folium.Map(
            location=self.center_location,
            zoom_start=17,
            tiles='OpenStreetMap'
        )
        
        # Mouse pozisyonu gösterici ekle
        MousePosition().add_to(m)
        
        # Sensör alanını göster
        folium.Circle(
            location=self.center_location,
            radius=self.radius,
            color='gray',
            fill=True,
            opacity=0.2
        ).add_to(m)
        
        # JavaScript fonksiyonlarını ekle
        js_code = """
        // Global değişkenler
        var map = null;
        var markers = {};
        
        function markerDragHandler(e) {
            var marker = e.target;
            var position = marker.getLatLng();
            var sensorName = marker.options.title;
            
            // Python'a bildir
            if (window.channel && window.channel.objects.bridge) {
                window.channel.objects.bridge.markerDragged(
                    'dragend',
                    sensorName,
                    position.lat,
                    position.lng
                );
            }
        }
        
        function initializeMarkers() {
            // Tüm Leaflet marker'larını bul
            map.eachLayer(function(layer) {
                if (layer instanceof L.Marker) {
                    var sensorName = layer.options.title;
                    if (sensorName) {
                        // Marker'ı kaydet
                        markers[sensorName] = layer;
                        
                        // Sürükleme olaylarını ekle
                        layer.off('dragend');  // Önceki dinleyicileri temizle
                        layer.on('dragend', markerDragHandler);
                    }
                }
            });
        }
        
        // Harita yüklendiğinde çalışacak kod
        document.addEventListener('DOMContentLoaded', function() {
            // Harita referansını al
            map = document.querySelector('#map')._leaflet_map;
            if (map) {
                // Marker'ları initialize et
                initializeMarkers();
                
                // Harita güncellendiğinde marker'ları yeniden initialize et
                map.on('layeradd', function(e) {
                    if (e.layer instanceof L.Marker) {
                        setTimeout(initializeMarkers, 100);
                    }
                });
            }
        });
        """
        
        # JavaScript kodunu element olarak ekle
        m.get_root().script.add_child(folium.Element(js_code))
        
        # Sensörleri haritaya ekle
        for sensor_name, pos in self.sensors.items():
            marker = folium.Marker(
                location=pos,
                popup=sensor_name,
                title=sensor_name,
                icon=folium.Icon(color='blue', icon='info-sign'),
                draggable=True
            )
            marker.add_to(m)
        
        # Haritaya çizim kontrollerini ekle
        draw = Draw(
            draw_options={
                'polyline': False,
                'rectangle': False,
                'polygon': False,
                'circle': False,
                'marker': True,
                'circlemarker': False
            },
            edit_options={'edit': True}
        )
        m.add_child(draw)
        
        # Web kanalı için JavaScript kodunu ekle
        channel_js = """
        new QWebChannel(qt.webChannelTransport, function(channel) {
            window.channel = channel;
        });
        """
        m.get_root().html.add_child(folium.Element(
            f'<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'
            f'<script>{channel_js}</script>'
        ))
        
        # Haritayı HTML olarak kaydet
        self.map_file = "temp_map.html"
        m.save(self.map_file)
        
        # Web görüntüleyicide göster
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.setUrl(QUrl(f"http://localhost:{self.port}/{self.map_file}"))
        
    def refresh_map(self):
        """Haritayı yeniden oluştur ve göster"""
        self.create_initial_map()
        
    def randomize_sensors(self):
        """Mikrofonları belirlenen alan içinde rastgele yerleştir"""
        center_lat, center_lon = self.center_location
        
        for sensor_name in self.sensors:
            # Rastgele açı ve mesafe
            angle = random.uniform(0, 360)
            distance = random.uniform(0, self.radius)
            
            # Yeni koordinatları hesapla
            origin = geopy.Point(center_lat, center_lon)
            destination = geodesic(meters=distance).destination(origin, angle)
            
            self.sensors[sensor_name] = (destination.latitude, destination.longitude)
            self.log(f"{sensor_name} yeni konuma taşındı: {destination.latitude:.6f}, {destination.longitude:.6f}")
        
        self.create_initial_map()
        
    def estimate_gunshot_location(self, actual_location):
        """Sensör verilerine göre silah sesinin tahmini konumunu hesapla"""
        # Sensörlerden gelen ses gecikmelerine göre konum tahmini yap
        # Bu demo için basitleştirilmiş bir trilaterasyon yaklaşımı kullanıyoruz
        
        # Her sensörün mesafesini hesapla
        sensor_distances = {}
        for sensor_name, sensor_pos in self.sensors.items():
            # Gerçek mesafeye biraz gürültü ekle
            real_distance = geodesic(actual_location, sensor_pos).meters
            noise = random.uniform(-5, 5)  # ±5 metre hata payı
            sensor_distances[sensor_name] = real_distance + noise
        
        # En yakın 3 sensörü bul
        closest_sensors = sorted(sensor_distances.items(), key=lambda x: x[1])[:3]
        
        # En yakın 3 sensörün konumlarını ve mesafelerini kullan
        weights = []
        weighted_positions = []
        
        for sensor_name, distance in closest_sensors:
            sensor_pos = self.sensors[sensor_name]
            # Mesafeye dayalı ağırlık hesapla (daha yakın sensörler daha etkili)
            weight = 1.0 / (distance + 1)  # +1 sıfıra bölünmeyi önler
            weights.append(weight)
            weighted_positions.append((sensor_pos[0] * weight, sensor_pos[1] * weight))
        
        # Ağırlıklı ortalama ile tahmini konumu hesapla
        total_weight = sum(weights)
        estimated_lat = sum(pos[0] for pos in weighted_positions) / total_weight
        estimated_lon = sum(pos[1] for pos in weighted_positions) / total_weight
        
        # Gerçekçi bir hata ekle
        error_radius = min(sensor_distances.values()) * 0.1  # En yakın mesafenin %10'u kadar hata
        error_angle = random.uniform(0, 360)
        error_distance = random.uniform(0, error_radius)
        
        # Hatayı koordinatlara ekle
        error_point = geodesic(meters=error_distance).destination(
            geopy.Point(estimated_lat, estimated_lon),
            error_angle
        )
        
        return (error_point.latitude, error_point.longitude)
        
    def update_sensor_position(self, sensor_name, lat, lon):
        """Sensör konumunu güncelle ve haritayı yeniden hesapla"""
        self.sensors[sensor_name] = (lat, lon)
        self.log(f"{sensor_name} konumu güncellendi: {lat:.6f}, {lon:.6f}")
        
        # Eğer aktif bir silah sesi varsa, mesafeleri ve konumları yeniden hesapla
        if self.last_gunshot:
            actual_lat, actual_lon = self.last_gunshot
            
            # Yeni mesafeyi hesapla
            distance = geodesic((actual_lat, actual_lon), (lat, lon)).meters
            delay = (distance / 343.0) * 1000  # milisaniye cinsinden
            self.log(f"{sensor_name} için yeni mesafe: {distance:.2f}m, Gecikme: {delay:.2f}ms")
            
            # Tahmini konumu güncelle
            estimated_location = self.estimate_gunshot_location(self.last_gunshot)
            self.log(f"Yeni tahmini konum: {estimated_location[0]:.6f}, {estimated_location[1]:.6f}")
            
            # Haritayı güncelle
            self.update_map(self.last_gunshot)
            
            # Hata mesafesini hesapla ve göster
            error_distance = geodesic(self.last_gunshot, estimated_location).meters
            self.log(f"Konum tahmin hatası: {error_distance:.2f}m")

    def update_map(self, actual_location):
        self.last_gunshot = actual_location  # Son silah sesini kaydet
        
        m = folium.Map(
            location=self.center_location,
            zoom_start=17,
            tiles='OpenStreetMap'
        )
        
        # Mouse pozisyonu gösterici ekle
        MousePosition().add_to(m)
        
        # Sensör alanını göster
        folium.Circle(
            location=self.center_location,
            radius=self.radius,
            color='gray',
            fill=True,
            opacity=0.2
        ).add_to(m)
        
        # JavaScript fonksiyonlarını ekle
        js_code = """
        // Global değişkenler
        var map = null;
        var markers = {};
        
        function markerDragHandler(e) {
            var marker = e.target;
            var position = marker.getLatLng();
            var sensorName = marker.options.title;
            
            // Python'a bildir
            if (window.channel && window.channel.objects.bridge) {
                window.channel.objects.bridge.markerDragged(
                    'dragend',
                    sensorName,
                    position.lat,
                    position.lng
                );
            }
        }
        
        function initializeMarkers() {
            // Tüm Leaflet marker'larını bul
            map.eachLayer(function(layer) {
                if (layer instanceof L.Marker) {
                    var sensorName = layer.options.title;
                    if (sensorName) {
                        // Marker'ı kaydet
                        markers[sensorName] = layer;
                        
                        // Sürükleme olaylarını ekle
                        layer.off('dragend');  // Önceki dinleyicileri temizle
                        layer.on('dragend', markerDragHandler);
                    }
                }
            });
        }
        
        // Harita yüklendiğinde çalışacak kod
        document.addEventListener('DOMContentLoaded', function() {
            // Harita referansını al
            map = document.querySelector('#map')._leaflet_map;
            if (map) {
                // Marker'ları initialize et
                initializeMarkers();
                
                // Harita güncellendiğinde marker'ları yeniden initialize et
                map.on('layeradd', function(e) {
                    if (e.layer instanceof L.Marker) {
                        setTimeout(initializeMarkers, 100);
                    }
                });
            }
        });
        """
        
        # JavaScript kodunu element olarak ekle
        m.get_root().script.add_child(folium.Element(js_code))
        
        # Sensörleri haritaya ekle
        for sensor_name, pos in self.sensors.items():
            marker = folium.Marker(
                location=pos,
                popup=sensor_name,
                title=sensor_name,
                icon=folium.Icon(color='blue', icon='info-sign'),
                draggable=True
            )
            marker.add_to(m)
        
        if actual_location:
            # Gerçek silah sesi konumu (kırmızı)
            folium.CircleMarker(
                location=actual_location,
                radius=10,
                popup='Gerçek Konum',
                color='red',
                fill=True
            ).add_to(m)
            
            # Tahmini konum (sarı)
            estimated_location = self.estimate_gunshot_location(actual_location)
            
            # Tahmini konum için hata dairesi (sarı, yarı saydam)
            error_radius = geodesic(actual_location, estimated_location).meters
            folium.Circle(
                location=estimated_location,
                radius=error_radius,
                color='yellow',
                fill=True,
                opacity=0.2
            ).add_to(m)
            
            # Tahmini konum noktası
            folium.CircleMarker(
                location=estimated_location,
                radius=10,
                popup=f'Tahmini Konum (Hata: {error_radius:.1f}m)',
                color='yellow',
                fill=True
            ).add_to(m)
            
            # Sensörlerden gerçek konuma çizgiler
            for sensor_name, pos in self.sensors.items():
                # Mesafeyi hesapla
                distance = geodesic(actual_location, pos).meters
                # Ses gecikmesini hesapla
                delay = (distance / 343.0) * 1000  # milisaniye cinsinden
                
                # Çizgiyi ekle
                points = [pos, actual_location]
                folium.PolyLine(
                    points,
                    weight=2,
                    color='green',
                    opacity=0.5,
                    popup=f'Mesafe: {distance:.1f}m, Gecikme: {delay:.1f}ms'
                ).add_to(m)
        
        # Web kanalı için JavaScript kodunu ekle
        channel_js = """
        new QWebChannel(qt.webChannelTransport, function(channel) {
            window.channel = channel;
        });
        """
        m.get_root().html.add_child(folium.Element(
            f'<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'
            f'<script>{channel_js}</script>'
        ))
        
        # Haritayı kaydet ve güncelle
        m.save(self.map_file)
        self.web_view.reload()
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def simulate_gunshot(self):
        # Merkez noktadan rastgele bir konumda silah sesi oluştur
        center_lat, center_lon = self.center_location
        
        # Rastgele açı ve mesafe
        angle = random.uniform(0, 360)
        distance = random.uniform(0, self.radius)  # metre cinsinden
        
        # Yeni koordinatları hesapla
        origin = geopy.Point(center_lat, center_lon)
        destination = geodesic(meters=distance).destination(origin, angle)
        
        actual_lat, actual_lon = destination.latitude, destination.longitude
        
        self.log(f"Silah sesi tespit edildi!")
        self.log(f"Gerçek Konum: {actual_lat:.6f}, {actual_lon:.6f}")
        
        # Tahmini konum
        estimated_location = self.estimate_gunshot_location((actual_lat, actual_lon))
        self.log(f"Tahmini Konum: {estimated_location[0]:.6f}, {estimated_location[1]:.6f}")
        
        # Her sensör için ses algılama simülasyonu
        for sensor_name, sensor_pos in self.sensors.items():
            # Mesafeyi metre cinsinden hesapla
            distance = geodesic(
                (actual_lat, actual_lon),
                sensor_pos
            ).meters
            
            # Ses hızı: 343 m/s
            delay = (distance / 343.0) * 1000  # milisaniye cinsinden
            self.log(f"{sensor_name} sesi algıladı - Mesafe: {distance:.2f}m, Gecikme: {delay:.2f}ms")
        
        # Haritayı güncelle
        self.update_map((actual_lat, actual_lon))
        
        # Bildirim gönder
        alert_data = {
            'event_type': 'gunshot',
            'location': (actual_lat, actual_lon),
            'estimated_location': estimated_location,
            'timestamp': time.time()
        }
        
        if send_alert(alert_data):
            self.log("Bildirim başarıyla gönderildi!")
        else:
            self.log("Bildirim gönderilemedi!")
    
    def closeEvent(self, event):
        # HTTP sunucusunu durdur
        if hasattr(self, 'httpd'):
            self.httpd.shutdown()
            self.httpd.server_close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GunShotDetectionDemo()
    window.show()
    sys.exit(app.exec_()) 