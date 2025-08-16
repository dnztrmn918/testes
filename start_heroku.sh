#!/bin/bash

# Heroku startup script
echo "🚀 Tubidy Oyun Botu başlatılıyor..."

# Environment variables
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Telegram timeout environment variables - artırıldı
export TELEGRAM_TIMEOUT=120
export TELEGRAM_CONNECT_TIMEOUT=120
export TELEGRAM_READ_TIMEOUT=120
export TELEGRAM_WRITE_TIMEOUT=120

# HTTPX Connection Pool - Basit ayarlar
export HTTPX_MAX_CONNECTIONS=10
export HTTPX_POOL_TIMEOUT=10.0

# MongoDB timeout environment variables
export MONGODB_SERVER_SELECTION_TIMEOUT=30000
export MONGODB_CONNECT_TIMEOUT=30000
export MONGODB_SOCKET_TIMEOUT=30000

# Python path
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Check if optimization module exists
if [ -f "heroku_optimization.py" ]; then
    echo "✅ Heroku optimizasyon modülü bulundu"
else
    echo "⚠️ Heroku optimizasyon modülü bulunamadı, varsayılan ayarlar kullanılacak"
fi

# Start the bot with error handling and retry mechanism
echo "🤖 Bot başlatılıyor..."
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "🔄 Bot başlatma denemesi $((RETRY_COUNT + 1))/$MAX_RETRIES"
    
    # Bot'u başlat
    python main.py
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Bot başarıyla başlatıldı!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "❌ Bot çöktü (Exit code: $EXIT_CODE)"
        
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⏳ $((RETRY_COUNT * 30)) saniye sonra yeniden başlatılıyor..."
            sleep $((RETRY_COUNT * 30))
        else
            echo "❌ Maksimum deneme sayısına ulaşıldı. Bot başlatılamadı."
            exit 1
        fi
    fi
done
