# Oyun Bot

Telegram oyun botu - Kelimeyi Türet, Tabu ve Yalancıyı Tahmin Et oyunları ile MongoDB puan sistemi.

## 🎮 Oyunlar

### Kelimeyi Türet
- Karışık harflerden kelime tahmin etme
- 2 puan kazanma

### Tabu
- Film adı tahmin etme
- 3 puan kazanma

### Yalancıyı Tahmin Et
- Yalancıları bulma oyunu
- 5 puan kazanma

## 📊 Puan Sistemi

### Komutlar
- `/puan` - Kendi puanlarını gör
- `/top <oyun_tipi>` - Top puanları gör
- `/puan_yardim` - Puan sistemi yardımı

### Oyun Türleri
- `kelimeyi_turet` - Kelimeyi Türet
- `tabu` - Tabu
- `yalanciyi_tahmin` - Yalancıyı Tahmin Et

## 🚀 Heroku Deployment

### 1. Gerekli Dosyalar
- `requirements.txt` - Python bağımlılıkları
- `Procfile` - Heroku process tanımı
- `runtime.txt` - Python versiyonu
- `config.py` - Bot token ve MongoDB URI

### 2. Environment Variables
Heroku'da şu environment variable'ları ayarlayın:

```
BOT_TOKEN=your_telegram_bot_token
MONGODB_URI=your_mongodb_connection_string
```

### 3. MongoDB Atlas
1. MongoDB Atlas hesabı oluşturun
2. Cluster oluşturun
3. Database Access'te kullanıcı oluşturun
4. Network Access'te IP whitelist ekleyin (0.0.0.0/0)
5. Connection string'i alın

### 4. Heroku Deployment
```bash
# Heroku CLI ile
heroku create your-app-name
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set MONGODB_URI=your_mongodb_uri
git push heroku main

# Veya GitHub ile
# 1. GitHub'a push
# 2. Heroku Dashboard'dan GitHub repo'yu bağla
# 3. Environment variables'ları ayarla
# 4. Deploy et
```

## 📁 Dosya Yapısı

```
oyunbot/
├── main.py              # Ana bot dosyası
├── config.py            # Konfigürasyon
├── requirements.txt     # Python bağımlılıkları
├── Procfile            # Heroku process
├── runtime.txt         # Python versiyonu
├── puan_sistemi.py     # MongoDB puan sistemi
├── puan_komutlari.py   # Puan komutları
├── yalan.py            # Yalancıyı Tahmin Et oyunu
├── türet.py            # Kelimeyi Türet oyunu
├── sessiz.py           # Tabu oyunu
├── start.py            # Başlangıç komutları
└── kelimeler/          # Oyun kelimeleri
    ├── kelimeler.json
    └── yalan.json
```

## 🔧 Yerel Geliştirme

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# MongoDB'yi başlat (yerel)
# MongoDB URI'yi config.py'de ayarla

# Botu çalıştır
python main.py
```

## 📝 Notlar

- Bot MongoDB'ye bağlanamazsa puan sistemi çalışmaz ama oyunlar çalışmaya devam eder
- Heroku'da web dyno kullanılır (polling yerine webhook)
- Puanlar MongoDB'de kalıcı olarak saklanır
