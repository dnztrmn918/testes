from telegram.ext import ContextTypes
from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TimedOut, NetworkError
import json
import random
import asyncio
from puan_sistemi import puan_sistemi

# Oyun durumu için bellek
tabu_oyun_durumu = {}

# Kelimeleri bir kez yükle ve cache'le
try:
    with open('kelimeler/kelimeler.json', 'r', encoding='utf-8') as f:
        KELIMELER_CACHE = json.load(f)
except Exception as e:
    print(f"❌ Kelimeler yüklenemedi: {e}")
    KELIMELER_CACHE = ["kelime", "oyun", "bot", "telegram"]

async def safe_telegram_request(func, *args, max_retries=1, **kwargs):
    """Telegram API isteklerini hızlı şekilde yapar, sadece 1 retry yapar"""
    # Timeout parametresini kwargs'dan çıkar (ExtBot fonksiyonları kabul etmiyor)
    timeout_value = kwargs.pop('timeout', 10.0)  # 60 saniye yerine 10 saniye
    
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_value)
        except (TimedOut, NetworkError) as e:
            if attempt == max_retries:
                print(f"❌ Telegram API hatası: {e}")
                raise e
            print(f"⚠️ Telegram API hatası (deneme {attempt + 1}/{max_retries + 1}): {e}")
            # Çok kısa bekleme
            await asyncio.sleep(0.5)  # 1 saniye yerine 0.5 saniye
        except asyncio.TimeoutError:
            if attempt == max_retries:
                print(f"❌ Timeout hatası: {func.__name__}")
                raise TimedOut("Request timed out after retries")
            print(f"⚠️ Timeout hatası (deneme {attempt + 1}/{max_retries + 1}): {func.__name__}")
            # Çok kısa bekleme
            await asyncio.sleep(0.5)  # 1 saniye yerine 0.5 saniye
        except Exception as e:
            # Connection pool hatalarını özel olarak yakala
            if "Pool timeout" in str(e) or "connection pool" in str(e).lower():
                if attempt == max_retries:
                    print(f"❌ Connection pool hatası: {e}")
                    raise e
                print(f"⚠️ Connection pool hatası (deneme {attempt + 1}/{max_retries + 1}): {e}")
                # Connection pool hatası için kısa bekleme
                await asyncio.sleep(1)  # 3 saniye yerine 1 saniye
            else:
                # Diğer hatalar için basit yönetim
                if attempt == max_retries:
                    print(f"❌ Beklenmeyen hata: {e}")
                    raise e
                print(f"⚠️ Beklenmeyen hata (deneme {attempt + 1}/{max_retries + 1}): {e}")
                # Çok kısa bekleme
                await asyncio.sleep(0.5)  # 1 saniye yerine 0.5 saniye

async def tabu_tahmin_kontrol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in tabu_oyun_durumu or not tabu_oyun_durumu[chat_id]['aktif']:
        return
    
    # Büyük/küçük harf duyarsız karşılaştırma için normalize et
    tahmin = update.message.text.strip()
    dogru_film = tabu_oyun_durumu[chat_id]['film']
    
    # Türkçe karakterleri normalize et ve büyük/küçük harf duyarsız yap
    import unicodedata
    import re
    
    def normalize_text(text):
        # Türkçe karakterleri normalize et
        text = unicodedata.normalize('NFKC', text)
        # Sadece harf ve rakamları al, boşlukları kaldır
        text = re.sub(r'[^a-zA-ZğüşıöçĞÜŞİÖÇ0-9]', '', text)
        # Küçük harfe çevir
        return text.lower()
    
    tahmin_normalized = normalize_text(tahmin)
    dogru_film_normalized = normalize_text(dogru_film)
    
    # Sunucu kendi kelimesini yazarsa sayma
    if update.effective_user.id == tabu_oyun_durumu[chat_id].get('sunucu_id'):
        return
    
    if tahmin_normalized == dogru_film_normalized:
        kazanan = update.effective_user
        puan = tabu_oyun_durumu[chat_id]['puan']
        
        # Doğru bilen kişiyi kaydet
        tabu_oyun_durumu[chat_id]['dogru_bilen_id'] = kazanan.id
        tabu_oyun_durumu[chat_id]['dogru_bilen_ismi'] = kazanan.first_name
        
        # Puan ekle
        try:
            chat = await context.bot.get_chat(chat_id)
            chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Bilinmeyen Grup"
            chat_username = getattr(chat, 'username', None)
        except Exception:
            chat_name = "Bilinmeyen Grup"
            chat_username = None
        basarili, mesaj = puan_sistemi.puan_ekle(
            kazanan.id, 
            kazanan.first_name, 
            "tabu", 
            puan, 
            chat_id,
            chat_name,
            chat_username
        )
        
        # Eski oyun mesajını sil
        if tabu_oyun_durumu[chat_id]['current_message_id']:
            try:
                await context.bot.delete_message(chat_id, tabu_oyun_durumu[chat_id]['current_message_id'])
            except:
                pass
        
        # Sadece doğru bilen için 10 saniye öncelik süresi tanımla
        from datetime import datetime, timedelta
        tabu_oyun_durumu[chat_id]['sunucu_oncelik_bitis'] = datetime.utcnow() + timedelta(seconds=10)

        # Raundu artır, yeni kelimeyi hazırla (gizlice)
        oyun = tabu_oyun_durumu[chat_id]
        oyun['raund'] += 1
        # Cache'den kelime seç (dosya okuma yok)
        yeni_kelime = random.choice(KELIMELER_CACHE)
        oyun['film'] = yeni_kelime
        oyun['puan'] = min(10, 3 + (oyun['raund'] // 5))
        
        # Yeni raund mesajını hazırla (sunucu seçiminden sonra gönderilecek)
        oyun['yeni_raund_hazir'] = True

        # Sunucu seçim mesajını GÖNDERME, sadece hazırla
        # Bu mesaj sunucu_ol_sessiz_callback'de gönderilecek
        oyun['sunucu_secim_hazir'] = True
        oyun['dogru_bilen_kelime'] = dogru_film
        oyun['dogru_bilen_puan'] = puan

async def sunucu_ol_sessiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sunucu olmak istiyorum callback"""
    query = update.callback_query
    
    # Query timeout kontrolü - çok eski query'leri reddet
    try:
        # Query'yi hemen answer et (timeout'u önle)
        await query.answer()
    except Exception as e:
        print(f"❌ Query answer hatası: {e}")
        return
    
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    if chat_id not in tabu_oyun_durumu:
        try:
            await query.edit_message_text("❌ Aktif oyun bulunamadı!")
        except:
            # Mesaj düzenlenemezse yeni mesaj gönder
            await context.bot.send_message(chat_id, "❌ Aktif oyun bulunamadı!")
        return
    
    oyun = tabu_oyun_durumu[chat_id]
    
    # Aktif sunucu kontrolü - eğer zaten aktif sunucu varsa engelle
    if oyun.get('sunucu_id') and oyun.get('sunucu_id') != user_id:
        try:
            await query.edit_message_text("❌ Zaten aktif bir sunucu var! Mevcut sunucu çıkana kadar bekleyin.")
        except:
            # Mesaj düzenlenemezse yeni mesaj gönder
            await context.bot.send_message(chat_id, "❌ Zaten aktif bir sunucu var! Mevcut sunucu çıkana kadar bekleyin.")
        return
    
    # 10 saniyelik öncelik denetimi
    if oyun.get('sunucu_oncelik_bitis'):
        from datetime import datetime
        if datetime.utcnow() < oyun['sunucu_oncelik_bitis']:
            # Öncelik süresi henüz bitmemiş
            if user_id != oyun.get('dogru_bilen_id'):
                try:
                    await query.edit_message_text("❌ Üzgünüm, kelimeyi sen doğru bilmedin! Sadece doğru bilen kişi sunucu olabilir.")
                except:
                    # Mesaj düzenlenemezse yeni mesaj gönder
                    await context.bot.send_message(chat_id, "❌ Üzgünüm, kelimeyi sen doğru bilmedin! Sadece doğru bilen kişi sunucu olabilir.")
                return
        else:
            # Öncelik süresi bitti, herkes sunucu olabilir
            oyun['sunucu_oncelik_bitis'] = None
    
    # Sunucuyu güncelle
    oyun['sunucu_id'] = user_id
    oyun['sunucu_ismi'] = user_name
    
    # Eski kontrol paneli mesajını sil (eğer varsa)
    if oyun.get('kontrol_panel_id') and oyun['kontrol_panel_id'] != query.message.message_id:
        try:
            await context.bot.delete_message(chat_id, oyun['kontrol_panel_id'])
        except:
            pass
    
    # Eski raund mesajını sil (eğer varsa)
    if oyun.get('raund_mesaj_id'):
        try:
            await context.bot.delete_message(chat_id, oyun['raund_mesaj_id'])
        except:
            pass
    
    # Query mesajını sil (eğer başarılı olursa)
    try:
        await query.delete()
    except:
        pass
    
    # Önce sunucu seçim mesajını gönder (eğer hazırsa)
    if oyun.get('sunucu_secim_hazir'):
        keyboard = [[InlineKeyboardButton("👑 Sunucu Olmak İstiyorum", callback_data="sunucu_ol_sessiz")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            sunucu_secim_mesaji = await safe_telegram_request(
                context.bot.send_message,
                chat_id,
                (
                    "🏁 <b>RAUND TAMAMLANDI</b> 🏁\n\n"
                    f"🎯 <b>Kelime:</b> <code>{oyun.get('dogru_bilen_kelime', 'Bilinmeyen')}</code>\n"
                    f"👤 <b>Doğru Bilen:</b> <a href='tg://user?id={oyun.get('dogru_bilen_id')}'>{oyun.get('dogru_bilen_ismi', 'Bilinmeyen')}</a>\n"
                    f"🏆 <b>Puan:</b> {oyun.get('dogru_bilen_puan', 0)}\n\n"
                    "👑 <b>SUNUCU SEÇİMİ</b> 👑\n"
                    "⏳ İlk 10 saniye sadece doğru bilen kişi sunucu olabilir.\n"
                    "👇 Sunucu olmak için butona tıklayın."
                ),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            # Sunucu seçim mesaj ID'sini sakla
            oyun['sunucu_secim_mesaj_id'] = sunucu_secim_mesaji.message_id
            
            # Sunucu seçim bilgilerini temizle
            oyun['sunucu_secim_hazir'] = False
            oyun['dogru_bilen_kelime'] = None
            oyun['dogru_bilen_puan'] = None
            
        except Exception as e:
            print(f"❌ Sunucu seçim mesajı gönderilemedi: {e}")
    
    # Kontrol paneli mesajını gönder
    keyboard = [
        [InlineKeyboardButton("👁️ Kelimeyi Gör", callback_data="kelime_gor_sessiz")],
        [InlineKeyboardButton("🔄 Kelimeyi Geç", callback_data="kelime_gec_sessiz")],
        [InlineKeyboardButton("❌ Sunucu İstemiyorum", callback_data="sunucu_istemiyorum_sessiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        kontrol_mesaji = await safe_telegram_request(
            context.bot.send_message,
            chat_id,
            f"🎯 <b>TABU</b> 🎯\n\n"
            f"👑 <b>Sunucu:</b> {user_name}\n"
            f"📊 <b>Raund:</b> {oyun['raund']}/{oyun['max_raund']}\n"
            f"🏆 <b>Puan:</b> {oyun['puan']}\n\n"
            f"🎯 Kelimeyi tahmin edin!\n"
            f"👑 <b>Sunucu:</b> {user_name}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        # Kontrol paneli mesaj ID'sini sakla
        oyun['kontrol_panel_id'] = kontrol_mesaji.message_id
        oyun['current_message_id'] = kontrol_mesaji.message_id
        # Raund mesaj ID'sini temizle
        oyun['raund_mesaj_id'] = None
        
        # Yeni raundu başlat (eğer hazırsa)
        if oyun.get('yeni_raund_hazir'):
            try:
                await yeni_tabu_raund(chat_id, context)
                oyun['yeni_raund_hazir'] = False
            except Exception as e:
                print(f"Yeni raund başlatma hatası: {e}")
                # Hata mesajını yeni mesaj olarak gönder
                await context.bot.send_message(chat_id, "❌ Yeni raund başlatılamadı!")
    except (TimedOut, NetworkError) as e:
        print(f"❌ Kontrol paneli mesajı gönderilemedi: {e}")
        # Hata durumunda basit mesaj gönder
        await context.bot.send_message(chat_id, "❌ Sunucu seçimi sırasında ağ hatası oluştu!")
    except Exception as e:
        print(f"Sunucu seçimi sonrası hata: {e}")
        # Hata durumunda basit mesaj gönder
        await context.bot.send_message(chat_id, "❌ Sunucu seçimi sırasında hata oluştu!")

async def kelime_gec_sessiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kelime geç callback - Sadece sunucu kullanabilir"""
    query = update.callback_query
    
    # Query timeout kontrolü - çok eski query'leri reddet
    try:
        # Query'yi hemen answer et (timeout'u önle)
        await query.answer()
    except Exception as e:
        print(f"❌ Query answer hatası: {e}")
        return
    
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    message_id = query.message.message_id
    
    if chat_id not in tabu_oyun_durumu:
        try:
            await query.edit_message_text("❌ Aktif oyun bulunamadı!")
        except:
            await context.bot.send_message(chat_id, "❌ Aktif oyun bulunamadı!")
        return
    
    oyun = tabu_oyun_durumu[chat_id]
    
    # Sunucu kontrolü - mesaj ID'sini kontrol et
    if user_id != oyun.get('sunucu_id'):
        try:
            await query.edit_message_text("Üzgünüm, sunucu sen değilsin.")
        except:
            await context.bot.send_message(chat_id, "Üzgünüm, sunucu sen değilsin.")
        return
    
    # Mesaj ID kontrolü - basitleştirildi, aktif mesajlarda çalışır
    if message_id != oyun.get('current_message_id') and message_id != oyun.get('kontrol_panel_id'):
        try:
            await query.edit_message_text("❌ Bu buton artık geçerli değil!")
        except:
            await context.bot.send_message(chat_id, "❌ Bu buton artık geçerli değil!")
        return
    
    # Yeni kelime seç ve sadece sunucuya göster (cache'den)
    yeni_kelime = random.choice(KELIMELER_CACHE)
    oyun['film'] = yeni_kelime

    # Sunucuya uyarı penceresinde göster
    try:
        await query.answer(f"Yeni kelimeniz: {yeni_kelime}", show_alert=True)
    except:
        # Uyarı penceresi gösterilemezse yeni mesaj gönder
        await context.bot.send_message(chat_id, f"👑 {query.from_user.first_name}, yeni kelimeniz: {yeni_kelime}")
    
    # Mesajı güncelle - yeni kelime seçildiğini belirt
    try:
        await safe_telegram_request(
            query.edit_message_text,
            f"🎯 <b>TABU</b> 🎯\n\n"
            f"👑 <b>Sunucu:</b> {oyun.get('sunucu_ismi', 'Bilinmeyen')}\n"
            f"📊 <b>Raund:</b> {oyun['raund']}/{oyun['max_raund']}\n"
            f"🏆 <b>Puan:</b> {oyun['puan']}\n\n"
            f"🎯 Yeni kelime seçildi! Kelimeyi tahmin edin!\n"
            f"👑 <b>Sunucu:</b> {oyun.get('sunucu_ismi', 'Bilinmeyen')}",
            reply_markup=query.message.reply_markup,
            parse_mode="HTML"
        )
        
        # Mesaj ID'yi güncelle (bu mesaj artık aktif)
        oyun['current_message_id'] = query.message.message_id
        oyun['kontrol_panel_id'] = query.message.message_id
        
    except (TimedOut, NetworkError) as e:
        print(f"❌ Kelime geç mesajı güncellenemedi: {e}")
        # Hata durumunda yeni mesaj gönder
        await context.bot.send_message(chat_id, "❌ Mesaj güncellenirken ağ hatası oluştu!")
    except Exception as e:
        print(f"❌ Kelime geç mesajı güncellenirken hata: {e}")
        # Hata durumunda yeni mesaj gönder
        await context.bot.send_message(chat_id, "❌ Mesaj güncellenirken hata oluştu!")

async def sunucu_istemiyorum_sessiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sunucu istemiyorum callback"""
    query = update.callback_query
    
    # Query timeout kontrolü - çok eski query'leri reddet
    try:
        # Query'yi hemen answer et (timeout'u önle)
        await query.answer()
    except Exception as e:
        print(f"❌ Query answer hatası: {e}")
        return
    
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    message_id = query.message.message_id
    
    if chat_id not in tabu_oyun_durumu:
        try:
            await query.edit_message_text("❌ Aktif oyun bulunamadı!")
        except:
            await context.bot.send_message(chat_id, "❌ Aktif oyun bulunamadı!")
        return
    
    oyun = tabu_oyun_durumu[chat_id]
    
    # Sunucu kontrolü
    if user_id != oyun.get('sunucu_id'):
        try:
            await query.edit_message_text("❌ Sadece sunucu bu butonu kullanabilir!")
        except:
            await context.bot.send_message(chat_id, "❌ Sadece sunucu bu butonu kullanabilir!")
        return
    
    # Mesaj ID kontrolü - basitleştirildi, aktif mesajlarda çalışır
    if message_id != oyun.get('current_message_id') and message_id != oyun.get('kontrol_panel_id'):
        try:
            await query.edit_message_text("❌ Bu buton artık geçerli değil!")
        except:
            await context.bot.send_message(chat_id, "❌ Bu buton artık geçerli değil!")
        return
    
    # Sunucuyu çıkar
    oyun['sunucu_id'] = None
    oyun['sunucu_ismi'] = None
    
    # Mesaj ID'leri temizle
    oyun['kontrol_panel_id'] = None
    oyun['raund_mesaj_id'] = None
    
    # Sunucu olmak istiyorum butonu
    keyboard = [
        [InlineKeyboardButton("👑 Sunucu Olmak İstiyorum", callback_data="sunucu_ol_sessiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await safe_telegram_request(
            query.edit_message_text,
            f"👑 <b>Sunucu Çıktı!</b> 👑\n\n"
            f"🎯 <a href='tg://user?id={user_id}'>{user_name}</a> sunuculuktan çıktı!\n"
            f"👑 <b>Yeni sunucu olmak isteyenler için buton:</b>\n"
            f"⏳ <i>Sunucu olmak için butona tıklayın</i>",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        # Yeni sunucu seçimi için mesaj ID'sini güncelle
        oyun['current_message_id'] = query.message.message_id
        
    except (TimedOut, NetworkError) as e:
        print(f"❌ Sunucu çıkış mesajı güncellenemedi: {e}")
        # Hata durumunda yeni mesaj gönder
        await context.bot.send_message(chat_id, "❌ Mesaj güncellenirken ağ hatası oluştu!")
    except Exception as e:
        print(f"❌ Sunucu çıkış mesajı güncellenirken hata: {e}")
        # Hata durumunda yeni mesaj gönder
        await context.bot.send_message(chat_id, "❌ Mesaj güncellenirken hata oluştu!")

async def tabu_oyun_zamanlayici(chat_id, context):
    try:
        await asyncio.sleep(900)  # 15 dakika (900 saniye)
        if chat_id in tabu_oyun_durumu and tabu_oyun_durumu[chat_id]['aktif']:
            try:
                await safe_telegram_request(
                    context.bot.send_message,
                    chat_id,
                    "😔 Üzgünüm, benimle kimse oynamadı.\n\n" 
                    "🎯 Tabu oyunu otomatik olarak sonlandırıldı."
                )
            except (TimedOut, NetworkError) as e:
                print(f"❌ Zamanlayıcı mesajı gönderilemedi: {e}")
            except Exception as e:
                print(f"Zamanlayıcı mesaj hatası: {e}")
            finally:
                # Task'ı temizle
                if chat_id in tabu_oyun_durumu:
                    tabu_oyun_durumu[chat_id]['aktif'] = False
                    tabu_oyun_durumu[chat_id]['zamanlayici_task'] = None
    except asyncio.CancelledError:
        # Task iptal edildi, normal - temizle
        if chat_id in tabu_oyun_durumu:
            tabu_oyun_durumu[chat_id]['zamanlayici_task'] = None
        print(f"✅ Zamanlayıcı task iptal edildi: {chat_id}")
    except Exception as e:
        print(f"Zamanlayıcı hatası: {e}")
        # Hata durumunda da temizle
        if chat_id in tabu_oyun_durumu:
            tabu_oyun_durumu[chat_id]['aktif'] = False
            tabu_oyun_durumu[chat_id]['zamanlayici_task'] = None

async def tabu_baslat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    
    # Yetki kontrolü
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_delete_messages:
            await query.edit_message_text(
                "❌ Üzgünüm, mesajları silme yetkim yok!\n\n"
                "🔧 Lütfen beni yönetici yapın ve şu yetkileri verin:\n"
                "• Mesajları silme\n"
                "• Mesaj gönderme\n\n"
                "Bu yetkiler olmadan oyun düzgün çalışamaz."
            )
            return
    except Exception as e:
        await query.edit_message_text(
            "❌ Yetki kontrolü yapılamadı!\n\n"
            "🔧 Lütfen beni yönetici yapın ve gerekli yetkileri verin."
        )
        return
    
    # Kelime seç (cache'den)
    kelime = random.choice(KELIMELER_CACHE)
    
    # Oyun durumunu kaydet
    tabu_oyun_durumu[chat_id] = {
        'film': kelime,
        'raund': 1,
        'max_raund': 60,
        'puan': 3,
        'aktif': True,
        'baslatan_id': user_id,
        'sunucu_id': user_id,
        'sunucu_ismi': query.from_user.first_name,
        'current_message_id': None,
        'oyun_mesaj_id': None,
        'kontrol_panel_id': None,
        'raund_mesaj_id': None,
        'dogru_bilen_id': None,
        'dogru_bilen_ismi': None,
        'sunucu_oncelik_bitis': None,
        'yeni_raund_hazir': False,
        'sunucu_secim_hazir': False,
        'dogru_bilen_kelime': None,
        'dogru_bilen_puan': None,
        'sunucu_secim_mesaj_id': None,
        'zamanlayici_task': None
    }
    
    # Oyun mesajını gönder
    keyboard = [
        [InlineKeyboardButton("👁️ Kelimeyi Gör", callback_data="kelime_gor_sessiz")],
        [InlineKeyboardButton("🔄 Kelimeyi Geç", callback_data="kelime_gec_sessiz")],
        [InlineKeyboardButton("❌ Sunucu İstemiyorum", callback_data="sunucu_istemiyorum_sessiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mesaj = await safe_telegram_request(
            context.bot.send_message,
            chat_id,
            f"🎯 <b>TABU</b> 🎯\n\n"
            f"👑 <b>Sunucu:</b> {query.from_user.first_name}\n"
            f"📊 <b>Raund:</b> 1/{tabu_oyun_durumu[chat_id]['max_raund']}\n"
            f"🏆 <b>Puan:</b> {tabu_oyun_durumu[chat_id]['puan']}\n\n"
            f"🎯 Kelimeyi tahmin edin!\n"
            f"👑 <b>Sunucu:</b> {query.from_user.first_name}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    
    # Ana oyun mesaj ID'sini sakla
    tabu_oyun_durumu[chat_id]['oyun_mesaj_id'] = mesaj.message_id
    tabu_oyun_durumu[chat_id]['current_message_id'] = mesaj.message_id
    
    # Zamanlayıcı başlat ve referansını sakla
    zamanlayici_task = asyncio.create_task(tabu_oyun_zamanlayici(chat_id, context))
    tabu_oyun_durumu[chat_id]['zamanlayici_task'] = zamanlayici_task

async def yeni_tabu_raund(chat_id, context):
    if chat_id not in tabu_oyun_durumu:
        print(f"Chat {chat_id} için oyun bulunamadı")
        return
    
    oyun = tabu_oyun_durumu[chat_id]
    if not oyun.get('aktif'):
        print(f"Chat {chat_id} için oyun aktif değil")
        return
    
    oyun['raund'] += 1
    
    # Kelime seç (cache'den)
    kelime = random.choice(KELIMELER_CACHE)
    oyun['film'] = kelime
    
    # Puanı artır (zorluk artışı)
    oyun['puan'] = min(10, 3 + (oyun['raund'] // 5))
    
    try:
        # Oyun mesajını gönder (kelimeyi herkese göstermeden)
        keyboard = [
            [InlineKeyboardButton("👁️ Kelimeyi Gör", callback_data="kelime_gor_sessiz")],
            [InlineKeyboardButton("🔄 Kelimeyi Geç", callback_data="kelime_gec_sessiz")],
            [InlineKeyboardButton("❌ Sunucu İstemiyorum", callback_data="sunucu_istemiyorum_sessiz")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        mesaj = await safe_telegram_request(
            context.bot.send_message,
            chat_id,
            f"🎯 <b>TABU</b> 🎯\n\n"
            f"👑 <b>Sunucu:</b> {oyun.get('sunucu_ismi', 'Bilinmeyen')}\n"
            f"📊 <b>Raund:</b> {oyun['raund']}/{oyun['max_raund']}\n"
            f"🏆 <b>Puan:</b> {oyun['puan']}\n\n"
            f"🎯 Kelimeyi tahmin edin!\n"
            f"👑 <b>Sunucu:</b> {oyun.get('sunucu_ismi', 'Bilinmeyen')}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        # Yeni raund mesaj ID'sini sakla
        oyun['raund_mesaj_id'] = mesaj.message_id
        # Ana oyun mesaj ID'sini de güncelle
        oyun['current_message_id'] = mesaj.message_id
        # Kontrol panel ID'sini temizle (artık bu mesaj aktif)
        oyun['kontrol_panel_id'] = None
    except (TimedOut, NetworkError) as e:
        print(f"❌ Yeni raund mesajı gönderilemedi: {e}")
        # Hata durumunda oyunu durdur
        oyun['aktif'] = False
    except Exception as e:
        print(f"Yeni raund başlatma hatası: {e}")
        # Hata durumunda oyunu durdur
        oyun['aktif'] = False

async def kelime_gor_sessiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kelimeyi sadece sunucuya uyarı penceresinde gösterir"""
    query = update.callback_query

    # Query timeout kontrolü - çok eski query'leri reddet
    try:
        # Query'yi hemen answer et (timeout'u önle)
        await query.answer()
    except Exception as e:
        print(f"❌ Query answer hatası: {e}")
        return

    chat_id = query.message.chat.id
    user_id = query.from_user.id
    message_id = query.message.message_id

    if chat_id not in tabu_oyun_durumu:
        try:
            await query.edit_message_text("❌ Aktif oyun bulunamadı!")
        except:
            await context.bot.send_message(chat_id, "❌ Aktif oyun bulunamadı!")
        return

    oyun = tabu_oyun_durumu[chat_id]

    # Sunucu kontrolü - sadece sunucu kullanabilir
    if user_id != oyun.get('sunucu_id'):
        try:
            await query.edit_message_text("❌ Üzgünüm, sunucu sen değilsin!")
        except:
            await context.bot.send_message(chat_id, "❌ Üzgünüm, sunucu sen değilsin!")
        return
    
    # Mesaj ID kontrolü - basitleştirildi, aktif mesajlarda çalışır
    if message_id != oyun.get('current_message_id') and message_id != oyun.get('kontrol_panel_id'):
        try:
            await query.edit_message_text("❌ Bu buton artık geçerli değil!")
        except:
            await context.bot.send_message(chat_id, "❌ Bu buton artık geçerli değil!")
        return
    
    kelime = oyun.get('film', '')
    
    # Sunucuya uyarı penceresinde göster
    try:
        await query.answer(f"Aktif kelimeniz: {kelime}", show_alert=True)
    except:
        # Uyarı penceresi gösterilemezse yeni mesaj gönder
        await context.bot.send_message(chat_id, f"👑 {query.from_user.first_name}, aktif kelimeniz: {kelime}")

def tabu_oyunu_durdur(chat_id):
    """Belirtilen chat'teki tabu oyununu durdurur"""
    if chat_id in tabu_oyun_durumu and tabu_oyun_durumu[chat_id]['aktif']:
        # Zamanlayıcı task'ını iptal et
        zamanlayici_task = tabu_oyun_durumu[chat_id].get('zamanlayici_task')
        if zamanlayici_task and not zamanlayici_task.done():
            try:
                zamanlayici_task.cancel()
            except Exception as e:
                print(f"Zamanlayıcı iptal hatası: {e}")
        
        # Oyun durumunu temizle
        tabu_oyun_durumu[chat_id]['aktif'] = False
        tabu_oyun_durumu[chat_id]['sunucu_id'] = None
        tabu_oyun_durumu[chat_id]['sunucu_ismi'] = None
        
        return True
    return False
