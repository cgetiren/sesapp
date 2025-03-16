import sounddevice as sd
import numpy as np
import librosa
import tensorflow as tf
from scipy.io import wavfile
import time
import gps
from communication import send_data_to_server
import ntplib
from collections import deque

class AcousticSensor:
    def __init__(self, sample_rate=44100, chunk_size=1024, buffer_duration=1.0):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.buffer_size = int(buffer_duration * sample_rate)
        self.audio_buffer = deque(maxlen=self.buffer_size)
        self.ml_model = self.load_model()
        self.initialize_sensor()
        
    def initialize_sensor(self):
        self.initialize_gps()
        self.initialize_time_sync()
        self.load_calibration()
        
    def initialize_gps(self):
        # GPS modülünü başlat
        self.gps_module = gps.GPS()
        self.gps_coordinates = self.gps_module.get_coordinates()
        
    def initialize_time_sync(self):
        try:
            ntp_client = ntplib.NTPClient()
            self.time_offset = ntp_client.request('pool.ntp.org').offset
        except:
            self.time_offset = 0
            print("NTP sync failed, using system time")
    
    def load_model(self):
        # Load pre-trained model
        model = tf.keras.models.load_model('gunshot_detection_model.h5')
        return model
        
    def extract_features(self, audio_data):
        # Extract advanced audio features
        features = {}
        
        # Time domain features
        features['rms'] = np.sqrt(np.mean(audio_data**2))
        features['zero_crossing_rate'] = np.sum(np.diff(np.signbit(audio_data)))
        
        # Frequency domain features
        stft = librosa.stft(audio_data.flatten())
        mag_spec = np.abs(stft)
        
        features['spectral_centroid'] = librosa.feature.spectral_centroid(S=mag_spec)[0]
        features['spectral_bandwidth'] = librosa.feature.spectral_bandwidth(S=mag_spec)[0]
        features['spectral_rolloff'] = librosa.feature.spectral_rolloff(S=mag_spec)[0]
        
        # MFCC features
        mfccs = librosa.feature.mfcc(y=audio_data.flatten(), sr=self.sample_rate, n_mfcc=13)
        features['mfccs'] = mfccs.mean(axis=1)
        
        return features
        
    def detect_gunshot(self, audio_data):
        features = self.extract_features(audio_data)
        feature_vector = np.concatenate([
            [features['rms']],
            [features['zero_crossing_rate']],
            features['spectral_centroid'],
            features['spectral_bandwidth'],
            features['spectral_rolloff'],
            features['mfccs']
        ])
        
        # Normalize features
        feature_vector = (feature_vector - self.feature_means) / self.feature_stds
        
        # Make prediction
        prediction = self.ml_model.predict(feature_vector.reshape(1, -1))
        confidence = prediction[0][0]
        
        return confidence > 0.85  # High confidence threshold
        
    def start_monitoring(self):
        with sd.InputStream(callback=self.audio_callback,
                          channels=1,
                          samplerate=self.sample_rate,
                          blocksize=self.chunk_size):
            print("Ses izleme başladı...")
            while True:
                time.sleep(0.1) 