"""
Heroku için optimizasyon ayarları
Bu dosya Heroku'da timeout ve connection sorunlarını önlemek için kullanılır
"""

import os
import signal
import sys
import time
import asyncio
from typing import Optional
from telegram.ext import ApplicationBuilder
from config import BOT_TOKEN

# Heroku timeout ayarları
HEROKU_TIMEOUT = 30
HEROKU_CONNECT_TIMEOUT = 30
HEROKU_READ_TIMEOUT = 30
HEROKU_WRITE_TIMEOUT = 30

def cleanup_old_instances():
    """Eski bot instance'larını temizler"""
    try:
        # Process ID'yi al
        current_pid = os.getpid()
        print(f"🔄 Mevcut process ID: {current_pid}")
        
        # Eski instance'ları temizle
        if os.path.exists('/tmp/bot.pid'):
            with open('/tmp/bot.pid', 'r') as f:
                old_pid = f.read().strip()
                try:
                    old_pid = int(old_pid)
                    if old_pid != current_pid:
                        print(f"🔄 Eski instance (PID: {old_pid}) temizleniyor...")
                        try:
                            os.kill(old_pid, signal.SIGTERM)
                            time.sleep(2)
                            os.kill(old_pid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
                except ValueError:
                    pass
        
        # Yeni PID'yi kaydet
        with open('/tmp/bot.pid', 'w') as f:
            f.write(str(current_pid))
        
        print("✅ Eski instance'lar temizlendi")
        
    except Exception as e:
        print(f"⚠️ Instance temizleme hatası: {e}")

def signal_handler(signum, frame):
    """Graceful shutdown için signal handler"""
    print(f"\n🛑 Signal {signum} alındı, bot kapatılıyor...")
    
    # PID dosyasını temizle
    try:
        if os.path.exists('/tmp/bot.pid'):
            os.remove('/tmp/bot.pid')
    except:
        pass
    
    sys.exit(0)

def setup_signal_handlers():
    """Signal handler'ları kurar"""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Windows için
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

def create_optimized_app():
    """Optimize edilmiş bot uygulaması oluşturur"""
    try:
        # Eski instance'ları temizle
        cleanup_old_instances()
        
        # Signal handler'ları kur
        setup_signal_handlers()
        
        # Bot'u oluştur
        app = (ApplicationBuilder()
               .token(BOT_TOKEN)
               .concurrent_updates(True)
               .build())
        
        print("✅ Optimize edilmiş bot uygulaması oluşturuldu")
        return app
        
    except Exception as e:
        print(f"❌ Bot uygulaması oluşturulamadı: {e}")
        return None

def create_heroku_app_builder():
    """Heroku için optimize edilmiş ApplicationBuilder döndürür"""
    
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

def main():
    """Ana fonksiyon"""
    print("🚀 Heroku Optimizasyon Modülü Başlatılıyor...")
    
    # Environment variables'ları ayarla
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    # Telegram timeout'ları
    os.environ.setdefault('TELEGRAM_READ_TIMEOUT', '30')
    os.environ.setdefault('TELEGRAM_WRITE_TIMEOUT', '30')
    os.environ.setdefault('TELEGRAM_CONNECT_TIMEOUT', '30')
    
    # HTTPX ayarları
    os.environ.setdefault('HTTPX_MAX_CONNECTIONS', '20')
    os.environ.setdefault('HTTPX_POOL_TIMEOUT', '5.0')
    
    print("✅ Environment variables ayarlandı")
    
    # Bot uygulamasını oluştur
    app = create_optimized_app()
    if not app:
        print("❌ Bot uygulaması oluşturulamadı")
        return
    
    try:
        print("🤖 Bot başlatılıyor...")
        app.run_polling(
            drop_pending_updates=True,  # Eski güncellemeleri at
            allowed_updates=None,  # Tüm güncellemeleri kabul et
            close_loop=False  # Loop'u kapatma
        )
    except KeyboardInterrupt:
        print("\n🛑 Bot kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"❌ Bot çalışırken hata oluştu: {e}")
    finally:
        # Temizlik
        try:
            if os.path.exists('/tmp/bot.pid'):
                os.remove('/tmp/bot.pid')
        except:
            pass
        print("✅ Bot kapatıldı")

if __name__ == "__main__":
    main()
