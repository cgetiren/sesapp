# Silah Sesi Tespit Sistemi - Demo Uygulaması

Bu proje, yüksek hassasiyetli mikrofonlar kullanarak silah sesi tespiti ve lokalizasyonu yapan bir sistemin demo uygulamasıdır. ShotSpotter benzeri bir sistemin simülasyonunu gerçekleştirir.

## Özellikler

- 🎯 Gerçek zamanlı silah sesi tespiti simülasyonu
- 📍 GPS tabanlı mikrofon konumlandırma
- 🗺️ İnteraktif harita arayüzü (OpenStreetMap)
- 📊 Ses gecikmesi ve mesafe hesaplamaları
- 🎯 Trilaterasyon ile konum tahmini
- 📱 Gerçek zamanlı bildirim sistemi
- 🔄 Dinamik mikrofon konumlandırma
- 📈 Hata payı hesaplama ve görselleştirme

## Gereksinimler

```bash
Python 3.8+
PyQt5
PyQtWebEngine
folium
geopy
pillow
selenium
webdriver-manager
```

## Kurulum

1. Gerekli Python paketlerini yükleyin:
```bash
pip install PyQt5 PyQtWebEngine folium geopy pillow selenium webdriver-manager
```

2. Projeyi klonlayın veya indirin:
```bash
git clone <repo-url>
cd gunshot-detection-demo
```

3. Uygulamayı çalıştırın:
```bash
python demo_app.py
```

## Kullanım

1. **Ana Pencere**
   - Sol tarafta interaktif harita
   - Sağ tarafta kontrol paneli ve log ekranı

2. **Mikrofon Konumları**
   - Mavi işaretçiler mikrofonları temsil eder
   - İşaretçileri sürükleyerek mikrofonların konumunu değiştirebilirsiniz
   - Her konum değişikliğinde mesafeler ve tahminler otomatik güncellenir

3. **Silah Sesi Simülasyonu**
   - "Silah Sesi Simüle Et" butonuna tıklayarak yeni bir olay oluşturun
   - Kırmızı işaretçi gerçek silah sesi konumunu gösterir
   - Sarı işaretçi ve daire tahmini konumu ve hata payını gösterir
   - Yeşil çizgiler mikrofonlara olan mesafeyi gösterir

4. **Kontroller**
   - Silah Sesi Simüle Et: Yeni bir silah sesi olayı oluşturur
   - Mikrofonları Rastgele Yerleştir: Mikrofonları alan içinde rastgele konumlandırır
   - Haritayı Yenile: Harita görünümünü yeniler

5. **Log Paneli**
   - Mikrofon konum güncellemeleri
   - Mesafe ve gecikme hesaplamaları
   - Konum tahmin sonuçları
   - Hata mesafesi bilgileri

## Teknik Detaylar

### Konum Tahmini
- En yakın 3 mikrofon kullanılarak trilaterasyon yapılır
- Mesafeye dayalı ağırlıklı ortalama ile konum hesaplanır
- Gerçekçi hata payı simülasyonu eklenir

### Ses Gecikmesi Hesaplama
- Ses hızı: 343 m/s
- Mesafe ve gecikme formülü: `gecikme = (mesafe / 343.0) * 1000` (milisaniye)

### Harita Sistemi
- OpenStreetMap altyapısı
- Folium kütüphanesi ile interaktif harita
- PyQt5 WebEngine ile harita görüntüleme
- QWebChannel ile JavaScript-Python iletişimi

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

## Katkıda Bulunma

1. Bu depoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Bir Pull Request oluşturun 