import os

# Bot Token
BOT_TOKEN = "8378360666:AAGCir9j47cgDU9NDFpcCToqC4SW2GLYhcM"

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://dtoraman89:44malatya22@cluster0.hcgwgdc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
DATABASE_NAME = 'oyunbot'
COLLECTION_NAME = 'puanlar'

# Telegram API Timeout Configuration - Daha hızlı yanıt için azaltıldı
TELEGRAM_READ_TIMEOUT = int(os.getenv('TELEGRAM_READ_TIMEOUT', 30))  # 120'den 30'a düşürüldü
TELEGRAM_WRITE_TIMEOUT = int(os.getenv('TELEGRAM_WRITE_TIMEOUT', 30))  # 120'den 30'a düşürüldü
TELEGRAM_CONNECT_TIMEOUT = int(os.getenv('TELEGRAM_CONNECT_TIMEOUT', 30))  # 120'den 30'a düşürüldü

# HTTPX Connection Pool - Daha hızlı bağlantı için optimize edildi
HTTPX_MAX_CONNECTIONS = int(os.getenv('HTTPX_MAX_CONNECTIONS', 20))  # 10'dan 20'ye çıkarıldı
HTTPX_POOL_TIMEOUT = float(os.getenv('HTTPX_POOL_TIMEOUT', 5.0))   # 10.0'dan 5.0'a düşürüldü

# Bot Startup Configuration
BOT_STARTUP_TIMEOUT = int(os.getenv('BOT_STARTUP_TIMEOUT', 180))  # 3 dakika
MAX_GET_UPDATES_RETRIES = int(os.getenv('MAX_GET_UPDATES_RETRIES', 5))
GET_UPDATES_RETRY_DELAY = int(os.getenv('GET_UPDATES_RETRY_DELAY', 10))  # 10 saniye

