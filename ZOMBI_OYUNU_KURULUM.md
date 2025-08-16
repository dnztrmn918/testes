# 🧟‍♂️ Zombi Kıyameti Oyunu Kurulum Kılavuzu

## 📋 Özellikler

✅ **Tamamlanan Özellikler:**
- Gündüz/Gece döngüsü
- Butonlu oylama sistemi
- Rol dağıtımı (Zombi, Doktor, Polis, Sivil)
- Oyun yönetimi ve durum kontrolü
- Ana menü entegrasyonu
- Gece hamleleri (rollerin özel yetenekleri)
- Oylama sonuçlarının gruba yansıtılması

## 🎮 Oyun Kuralları

### 🎯 Oyun Amacı
- **İyi Takım:** Tüm zombileri bulup linç etmek
- **Kötü Takım (Zombiler):** İyi oyuncuları eşit sayıya getirmek

### 🎭 Roller ve Yetenekler
- **🧟‍♂️ Zombi:** Her gece bir kişiyi öldürebilir
- **👨‍⚕️ Doktor:** Her gece bir kişiyi iyileştirebilir
- **👮‍♂️ Polis:** Her gece bir kişinin rolünü öğrenebilir
- **👤 Sivil:** Gündüz tartışarak zombileri bulmaya çalışır

### ⏰ Oyun Süreleri
- **🌅 Gündüz:** 5 dakika (tartışma)
- **🗳️ Oylama:** 1 dakika (linç)
- **🌙 Gece:** 2 dakika (roller hamle yapar)

## 🚀 Kurulum

### 1. Gerekli Dosyalar
Zombi oyunu için aşağıdaki dosyalar gerekli:

```
zombi/
├── constants.py      # Oyun sabitleri ve süreler
├── game.py          # Ana oyun sınıfı
├── game_logic.py    # Oyun mantığı ve gece hamleleri
├── manager.py       # Oyun yönetimi
├── messages.py      # Mesaj yönetimi
└── voting.py        # Oylama sistemi

zombi_kiyameti.py    # Ana oyun dosyası
```

### 2. Ana Bot Entegrasyonu
`main.py` dosyasına aşağıdaki import'ları ekleyin:

```python
from zombi_kiyameti import (
    zombi_kiyameti_start, zombi_kiyameti_callback_handler, zombi_kiyameti_stop,
    is_game_active
)
```

### 3. Handler'ları Ekleyin
```python
# Zombi Kıyameti
app.add_handler(CommandHandler("zombi", zombi_kiyameti_start))
app.add_handler(CommandHandler("zombi_stop", zombi_kiyameti_stop))

# Zombi oyunu callback'leri
app.add_handler(CallbackQueryHandler(zombi_kiyameti_callback_handler, pattern="^zombi_(join|leave|cancel)$"))
app.add_handler(CallbackQueryHandler(zombi_kiyameti_callback_handler, pattern="^vote_"))
```

## 🎯 Kullanım

### Komutlar
- `/zombi` - Zombi Kıyameti oyununu başlat
- `/zombi_stop` - Oyunu durdur (admin)
- `/oyun` - Oyun menüsünden Zombi Kıyameti'ni seç

### Oyun Akışı
1. **Oyun Başlatma:** `/zombi` komutu ile
2. **Katılım:** Oyuncular butonlarla katılır (60 saniye)
3. **Rol Dağıtımı:** Roller özelden dağıtılır
4. **Gündüz:** Tartışma ve oylama
5. **Gece:** Roller hamle yapar
6. **Tekrar:** Gündüz/Gece döngüsü devam eder
7. **Oyun Sonu:** Kazanan takım belirlenir

## 🔧 Özelleştirme

### Süreleri Değiştirme
`zombi/constants.py` dosyasında:

```python
JOIN_TIMEOUT = 60      # Katılım süresi
DAY_TIMEOUT = 300      # Gündüz süresi (5 dakika)
VOTING_TIMEOUT = 60    # Oylama süresi (1 dakika)
NIGHT_TIMEOUT = 120    # Gece süresi (2 dakika)
```

### Oyuncu Limitleri
```python
MIN_PLAYERS = 4        # Minimum oyuncu
MAX_PLAYERS = 30       # Maksimum oyuncu
```

### Rolleri Değiştirme
```python
ROLES = {
    "zombi": {
        "name": "🧟‍♂️ Zombi",
        "team": "bad",
        "description": "Her gece bir kişiyi öldürebilir"
    },
    # Diğer roller...
}
```

## 🐛 Sorun Giderme

### Yaygın Sorunlar
1. **Import Hatası:** `zombi` klasörünün `__init__.py` dosyası olduğundan emin olun
2. **Callback Hatası:** Handler pattern'lerinin doğru olduğunu kontrol edin
3. **Süre Hatası:** Constants dosyasındaki sürelerin doğru olduğunu kontrol edin

### Test Etme
1. Bot'u başlatın
2. `/zombi` komutunu test edin
3. Oyuncu ekleme/çıkarma işlemlerini test edin
4. Oyun akışını test edin

## 📝 Notlar

- Oyun tamamen asenkron çalışır
- Tüm oyuncular için özel mesajlar gönderilir
- Oyun durumu sürekli güncellenir
- Hata durumlarında oyun otomatik olarak temizlenir

## 🎉 Tamamlanan Özellikler

✅ Gündüz/Gece döngüsü
✅ Butonlu oylama sistemi
✅ Rol dağıtımı
✅ Gece hamleleri
✅ Oylama sonuçları
✅ Oyun yönetimi
✅ Ana menü entegrasyonu
✅ Hata yönetimi

Zombi Kıyameti oyunu artık tamamen çalışır durumda! 🎮
