"""
Heroku için optimizasyon ayarları
Bu dosya Heroku'da timeout ve connection sorunlarını önlemek için kullanılır
"""

import os
import signal
import sys
import asyncio
from typing import Optional

# Heroku timeout ayarları
HEROKU_TIMEOUT = 30
HEROKU_CONNECT_TIMEOUT = 30
HEROKU_READ_TIMEOUT = 30
HEROKU_WRITE_TIMEOUT = 30

def setup_heroku_timeouts():
    """Heroku için timeout ayarlarını yapılandırır"""
    # Environment variables
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    # Timeout environment variables
    os.environ['TELEGRAM_TIMEOUT'] = str(HEROKU_TIMEOUT)
    os.environ['TELEGRAM_CONNECT_TIMEOUT'] = str(HEROKU_CONNECT_TIMEOUT)
    os.environ['TELEGRAM_READ_TIMEOUT'] = str(HEROKU_READ_TIMEOUT)
    os.environ['TELEGRAM_WRITE_TIMEOUT'] = str(HEROKU_WRITE_TIMEOUT)
    
    # MongoDB timeout environment variables
    os.environ['MONGODB_SERVER_SELECTION_TIMEOUT'] = '10000'
    os.environ['MONGODB_CONNECT_TIMEOUT'] = '10000'
    os.environ['MONGODB_SOCKET_TIMEOUT'] = '10000'

def setup_signal_handlers():
    """Signal handler'ları kurar (Heroku restart için)"""
    def signal_handler(signum, frame):
        print(f"Signal {signum} received, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def create_heroku_app_builder():
    """Heroku için optimize edilmiş ApplicationBuilder döndürür"""
    from telegram.ext import ApplicationBuilder
    
    return ApplicationBuilder()\
        .read_timeout(HEROKU_TIMEOUT)\
        .write_timeout(HEROKU_TIMEOUT)\
        .connect_timeout(HEROKU_CONNECT_TIMEOUT)\
        .pool_timeout(HEROKU_TIMEOUT)\
        .get_updates_read_timeout(HEROKU_READ_TIMEOUT)\
        .get_updates_write_timeout(HEROKU_WRITE_TIMEOUT)\
        .get_updates_connect_timeout(HEROKU_CONNECT_TIMEOUT)\
        .get_updates_pool_timeout(HEROKU_TIMEOUT)

def get_heroku_polling_config():
    """Heroku için optimize edilmiş polling konfigürasyonu döndürür"""
    return {
        'timeout': HEROKU_TIMEOUT,
        'drop_pending_updates': True,
        'allowed_updates': ["message", "callback_query", "chat_member"],
        'bootstrap_retries': 3
    }

# Heroku environment check
def is_heroku():
    """Heroku'da çalışıp çalışmadığını kontrol eder"""
    return os.environ.get('DYNO') is not None

def get_heroku_port():
    """Heroku port'unu alır"""
    return int(os.environ.get('PORT', 5000))

if __name__ == "__main__":
    print("Heroku optimizasyon ayarları yüklendi!")
    print(f"Heroku'da çalışıyor: {is_heroku()}")
    print(f"Port: {get_heroku_port()}")
    print(f"Timeout: {HEROKU_TIMEOUT}s")
