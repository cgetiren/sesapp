import numpy as np
from scipy.optimize import minimize
from geopy.distance import geodesic
import pyproj

class TriangulationCalculator:
    def __init__(self):
        self.geod = pyproj.Geod(ellps='WGS84')
        self.sound_speed = 343.2  # m/s at 20°C
        
    def calculate_source_location(self, sensor_positions, time_differences):
        """
        Gelişmiş ses kaynağı konumu hesaplama
        
        Args:
            sensor_positions: Sensörlerin GPS koordinatları [(lat1,lon1), ...]
            time_differences: Sensörler arasındaki varış zamanı farkları [t1, t2, ...]
        """
        def objective_function(x):
            lat, lon = x
            distances = []
            
            for sensor_pos in sensor_positions:
                # Haversine formülü ile mesafe hesapla
                _, _, distance = self.geod.inv(
                    lon, lat,
                    sensor_pos[1], sensor_pos[0]
                )
                distances.append(distance)
            
            # Mesafe farklarını hesapla
            distance_differences = []
            for i in range(len(distances) - 1):
                diff = distances[i] - distances[i + 1]
                distance_differences.append(diff)
            
            # Ses hızını kullanarak zaman farklarını hesapla
            calculated_time_diffs = np.array(distance_differences) / self.sound_speed
            measured_time_diffs = np.array(time_differences)
            
            return np.sum((calculated_time_diffs - measured_time_diffs) ** 2)
        
        # Başlangıç tahmini: sensörlerin ağırlık merkezi
        initial_lat = np.mean([pos[0] for pos in sensor_positions])
        initial_lon = np.mean([pos[1] for pos in sensor_positions])
        
        # Sınırları belirle
        bounds = (
            (initial_lat - 0.1, initial_lat + 0.1),  # lat bounds
            (initial_lon - 0.1, initial_lon + 0.1)   # lon bounds
        )
        
        # Optimize et
        result = minimize(
            objective_function,
            [initial_lat, initial_lon],
            method='L-BFGS-B',
            bounds=bounds
        )
        
        if not result.success:
            raise ValueError("Optimization failed to converge")
            
        return result.x 