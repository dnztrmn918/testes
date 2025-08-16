from telegram.ext import ContextTypes
from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
import json
import random
import string
import asyncio
from puan_sistemi import puan_sistemi
import unicodedata
import re

def _normalize_tr_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Türkçe'ye uygun temel normalize
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    text = text.replace("İ", "i").replace("I", "ı")
    text = text.casefold()
    # Harf ve rakam dışını temizle, boşlukları kaldır
    text = re.sub(r"[^a-zçğıöşü0-9]", "", text)
    return text

# Oyun durumu için bellek
turet_oyun_durumu = {}

async def turet_tahmin_kontrol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in turet_oyun_durumu or not turet_oyun_durumu[chat_id]['aktif']:
        return
    
    tahmin = _normalize_tr_text(update.message.text)
    dogru_kelime = _normalize_tr_text(turet_oyun_durumu[chat_id]['kelime'])
    
    if tahmin == dogru_kelime:
        kazanan = update.effective_user
        puan = turet_oyun_durumu[chat_id]['puan']
        
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
            "kelimeyi_turet", 
            puan, 
            chat_id,
            chat_name,
            chat_username
        )
        
        # Eski oyun mesajını sil
        if turet_oyun_durumu[chat_id]['current_message_id']:
            try:
                await context.bot.delete_message(chat_id, turet_oyun_durumu[chat_id]['current_message_id'])
            except Exception:
                pass
        
        # Bonus kelime kontrolü ve +1 hak verilme (sadece 1-2 soruda random)
        bonus_kelimeler = [
            "bilgisayar", "telefon", "araba", "hastane", "market", 
            "deniz", "orman", "güneş", "yıldız", "çiçek", "ağaç", 
            "kartal", "şahin", "baykuş", "penguen", "flamingo", "tavus"
        ]
        
        bonus_text = ""
        # Sadece %20 ihtimalle +1 hak ver (1-2 soruda random)
        if dogru_kelime.lower() in bonus_kelimeler and random.random() < 0.2:
            turet_oyun_durumu[chat_id]['max_kelime_degistirme'] += 1
            bonus_text = " 🎁 (Bonus Kelime! +1 ek hak)"
        
        # Kazanan mesajı
        puan_mesaji = f" (+{puan} puan)" if basarili else ""
        await context.bot.send_message(
            chat_id,
            f"🎊 <b>{dogru_kelime.upper()}</b> kelimesini doğru bilen: <a href='tg://user?id={kazanan.id}'>{kazanan.first_name}</a>!\n"
            f"🏆 Kazanılan puan: {puan}{puan_mesaji}{bonus_text}",
            parse_mode="HTML"
        )
        
        # Yeni raund başlat
        await yeni_turet_raund(chat_id, context)

async def turet_oyun_zamanlayici(chat_id, context):
    """15 dakika sonra oyunu otomatik sonlandırır"""
    try:
        # 15 dakika bekle (900 saniye)
        await asyncio.sleep(900)
        
        # Chat hala mevcut mu kontrol et
        if chat_id not in turet_oyun_durumu:
            return
        
        # Oyun hala aktif mi kontrol et
        if not turet_oyun_durumu[chat_id].get('aktif', False):
            return
        
        # Oyunu sonlandır
        try:
            await context.bot.send_message(
                chat_id,
                "😔 Üzgünüm, benimle kimse oynamadı.\n\n"
                "🧩 Kelimeyi Türet oyunu otomatik olarak sonlandırıldı."
            )
        except Exception as e:
            # Mesaj gönderilemezse sessizce devam et
            print(f"Zamanlayıcı mesaj hatası: {e}")
        finally:
            # Oyunu sonlandır ve task'ı temizle
            if chat_id in turet_oyun_durumu:
                turet_oyun_durumu[chat_id]['aktif'] = False
                turet_oyun_durumu[chat_id]['zamanlayici_task'] = None
            
    except asyncio.CancelledError:
        # Task iptal edildi, temizle
        if chat_id in turet_oyun_durumu:
            turet_oyun_durumu[chat_id]['zamanlayici_task'] = None
        print(f"✅ Türet zamanlayıcı task iptal edildi: {chat_id}")
        return
    except Exception as e:
        # Genel hata durumunda oyunu güvenli şekilde sonlandır
        print(f"Zamanlayıcı hatası: {e}")
        if chat_id in turet_oyun_durumu:
            turet_oyun_durumu[chat_id]['aktif'] = False
            turet_oyun_durumu[chat_id]['zamanlayici_task'] = None

def _secim_araligi_raunda_gore(raund: int):
    if raund <= 5:
        return (4, 6)
    if raund <= 10:
        return (6, 8)
    if raund <= 20:
        return (7, 9)
    return (8, 10)

def _raunda_gore_puan(raund: int, kelime: str = ""):
    base_puan = 0
    if raund <= 5:
        base_puan = 2
    elif raund <= 10:
        base_puan = 3
    elif raund <= 20:
        base_puan = 5
    else:
        base_puan = 7
    
    # Bonus kelimeler için ekstra puan
    bonus_kelimeler = {
        "bilgisayar": 3,
        "telefon": 2,
        "araba": 2,
        "hastane": 2,
        "market": 1,
        "deniz": 1,
        "orman": 1,
        "güneş": 1,
        "yıldız": 1,
        "çiçek": 1,
        "ağaç": 1,
        "kartal": 2,
        "şahin": 2,
        "baykuş": 2,
        "penguen": 3,
        "flamingo": 3,
        "tavus": 3
    }
    
    bonus = bonus_kelimeler.get(kelime.lower(), 0)
    return base_puan + bonus

def _raunda_gore_kelime_sec(kelimeler, raund: int, chat_id: int):
    min_len, max_len = _secim_araligi_raunda_gore(raund)
    uygun_kelimeler = [k for k in kelimeler if min_len <= len(k) <= max_len]
    if not uygun_kelimeler:
        uygun_kelimeler = kelimeler
    
    # Daha önce kullanılan kelimeleri takip et
    if chat_id not in turet_oyun_durumu:
        turet_oyun_durumu[chat_id] = {'kullanilan_kelimeler': []}
    elif 'kullanilan_kelimeler' not in turet_oyun_durumu[chat_id]:
        turet_oyun_durumu[chat_id]['kullanilan_kelimeler'] = []
    
    kullanilan = turet_oyun_durumu[chat_id]['kullanilan_kelimeler']
    
    # Kullanılmamış kelimeleri tercih et
    kullanilmamis = [k for k in uygun_kelimeler if k not in kullanilan]
    
    if kullanilmamis:
        secilen = random.choice(kullanilmamis)
    else:
        # Tüm kelimeler kullanıldıysa listeyi temizle ve yeniden başla
        kullanilan.clear()
        secilen = random.choice(uygun_kelimeler)
    
    # Seçilen kelimeyi kullanılan listesine ekle
    kullanilan.append(secilen)
    
    # Bonus puan veren kelimelerde +1 ek hakkı ekle
    bonus_kelimeler = [
        "bilgisayar", "telefon", "araba", "hastane", "market", 
        "deniz", "orman", "güneş", "yıldız", "çiçek", "ağaç", 
        "kartal", "şahin", "baykuş", "penguen", "flamingo", "tavus"
    ]
    
    # Bonus kelime kontrolü - oyun başladıktan sonra yapılacak
    return secilen

async def kelimeyi_turet_baslat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
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
    
    # Kelime seç
    with open('kelimeler/tahmin.json', 'r', encoding='utf-8') as f:
        kelimeler = json.load(f)
    
    ilk_raund = 1
    kelime = _raunda_gore_kelime_sec(kelimeler, ilk_raund, chat_id)
    karisik_harfler = list(kelime)
    random.shuffle(karisik_harfler)
    karisik_kelime = ''.join(karisik_harfler)
    
    # İpucu oluştur (2 harf göster)
    ipucu_pozisyonlar = random.sample(range(len(kelime)), min(2, len(kelime)))
    ipucu_mesaji = ""
    for i, pos in enumerate(ipucu_pozisyonlar):
        ipucu_mesaji += f"{pos+1}.{kelime[pos]}"
        if i < len(ipucu_pozisyonlar) - 1:
            ipucu_mesaji += ", "
    
    # Oyun durumunu kaydet
    turet_oyun_durumu[chat_id] = {
        'kelime': kelime,
        'karisik_kelime': karisik_kelime,
        'raund': 1,
        'max_raund': 60,
        'puan': _raunda_gore_puan(1, kelime),
        'aktif': True,
        'baslatan_id': user_id,
        'kelime_degistirme_sayisi': 0,
        'max_kelime_degistirme': 5,  # Sabit 5 hak
        'current_message_id': None
    }
    
    # Bonus puan bilgisi
    base_puan = _raunda_gore_puan(turet_oyun_durumu[chat_id]['raund'])
    bonus_puan = turet_oyun_durumu[chat_id]['puan'] - base_puan
    bonus_text = f" (+{bonus_puan} bonus)" if bonus_puan > 0 else ""
    
    # Oyun mesajı
    vurgulu_karisik = ' '.join(list(karisik_kelime))
    oyun_mesaji = (
        f"🎲 Raund {turet_oyun_durumu[chat_id]['raund']}/{turet_oyun_durumu[chat_id]['max_raund']}\n"
        f"🔤 <b>Karışık Kelime:</b> <code>{vurgulu_karisik}</code>\n"
        f"🧮 <b>Harf Sayısı:</b> {len(kelime)}\n"
        f"💡 <b>İpucu:</b> {ipucu_mesaji}\n"
        f"🏆 <b>Puan:</b> {turet_oyun_durumu[chat_id]['puan']}{bonus_text}\n"
        f"🔄 <b>Kelime Değiştirme:</b> {turet_oyun_durumu[chat_id]['kelime_degistirme_sayisi']}/{turet_oyun_durumu[chat_id]['max_kelime_degistirme']}\n\n"
        f"🎯 Orijinal kelimeyi tahmin edin!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Kelimeyi Geç", callback_data="turet_yeni_kelime")],
        [InlineKeyboardButton("❌ Oyunu Bitir", callback_data="turet_oyun_bitir")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mesaj = await context.bot.send_message(
        chat_id,
        oyun_mesaji,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    turet_oyun_durumu[chat_id]['current_message_id'] = mesaj.message_id
    
    # Zamanlayıcı başlat (güvenli şekilde)
    try:
        zamanlayici_task = asyncio.create_task(turet_oyun_zamanlayici(chat_id, context))
        # Task referansını sakla
        turet_oyun_durumu[chat_id]['zamanlayici_task'] = zamanlayici_task
    except Exception as e:
        print(f"Zamanlayıcı başlatma hatası: {e}")
        # Zamanlayıcı başlatılamazsa oyunu devam ettir
        turet_oyun_durumu[chat_id]['zamanlayici_task'] = None

async def yeni_turet_raund(chat_id, context):
    if chat_id not in turet_oyun_durumu:
        return
    
    oyun = turet_oyun_durumu[chat_id]
    oyun['raund'] += 1
    
    # Kelime seç
    with open('kelimeler/tahmin.json', 'r', encoding='utf-8') as f:
        kelimeler = json.load(f)
    
    kelime = _raunda_gore_kelime_sec(kelimeler, oyun['raund'], chat_id)
    karisik_harfler = list(kelime)
    random.shuffle(karisik_harfler)
    karisik_kelime = ''.join(karisik_harfler)
    
    # İpucu oluştur (2 harf göster)
    ipucu_pozisyonlar = random.sample(range(len(kelime)), min(2, len(kelime)))
    ipucu_mesaji = ""
    for i, pos in enumerate(ipucu_pozisyonlar):
        ipucu_mesaji += f"{pos+1}.{kelime[pos]}"
        if i < len(ipucu_pozisyonlar) - 1:
            ipucu_mesaji += ", "
    
    # Oyun durumunu güncelle
    oyun['kelime'] = kelime
    oyun['karisik_kelime'] = karisik_kelime
    oyun['puan'] = _raunda_gore_puan(oyun['raund'], kelime)
    
    # Bonus puan bilgisi
    base_puan = _raunda_gore_puan(oyun['raund'])
    bonus_puan = oyun['puan'] - base_puan
    bonus_text = f" (+{bonus_puan} bonus)" if bonus_puan > 0 else ""
    
    # Oyun mesajı
    vurgulu_karisik = ' '.join(list(karisik_kelime))
    oyun_mesaji = (
        f"🎲 Raund {oyun['raund']}/{oyun['max_raund']}\n"
        f"🔤 <b>Karışık Kelime:</b> <code>{vurgulu_karisik}</code>\n"
        f"🧮 <b>Harf Sayısı:</b> {len(kelime)}\n"
        f"💡 <b>İpucu:</b> {ipucu_mesaji}\n"
        f"🏆 <b>Puan:</b> {oyun['puan']}{bonus_text}\n"
        f"🔄 <b>Kelime Değiştirme:</b> {oyun['kelime_degistirme_sayisi']}/{oyun['max_kelime_degistirme']}\n\n"
        f"🎯 Orijinal kelimeyi tahmin edin!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Kelimeyi Geç", callback_data="turet_yeni_kelime")],
        [InlineKeyboardButton("❌ Oyunu Bitir", callback_data="turet_oyun_bitir")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mesaj = await context.bot.send_message(
        chat_id,
        oyun_mesaji,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    oyun['current_message_id'] = mesaj.message_id

async def turet_yeni_kelime_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni kelime callback"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    if chat_id not in turet_oyun_durumu:
        await query.edit_message_text("❌ Aktif oyun bulunamadı!")
        return
    
    oyun = turet_oyun_durumu[chat_id]
    
    # Kelime değiştirme hakkı kontrolü
    if oyun['kelime_degistirme_sayisi'] >= oyun['max_kelime_degistirme']:
        await query.answer("❌ Kelime değiştirme hakkınız bitti!", show_alert=True)
        return
    
    # Önce eski kelimeyi al (yeni kelime seçilmeden önce)
    eski_kelime = oyun.get('kelime', 'Bilinmeyen')
    
    # Kelime değiştirme sayısını artır (sabit 5 hak)
    oyun['kelime_degistirme_sayisi'] += 1
    
    # Yeni kelime seç
    with open('kelimeler/tahmin.json', 'r', encoding='utf-8') as f:
        kelimeler = json.load(f)
    
    kelime = _raunda_gore_kelime_sec(kelimeler, oyun['raund'], chat_id)
    karisik_harfler = list(kelime)
    random.shuffle(karisik_harfler)
    karisik_kelime = ''.join(karisik_harfler)
    
    # İpucu oluştur
    ipucu_pozisyonlar = random.sample(range(len(kelime)), min(2, len(kelime)))
    ipucu_mesaji = ""
    for i, pos in enumerate(ipucu_pozisyonlar):
        ipucu_mesaji += f"{pos+1}.{kelime[pos]}"
        if i < len(ipucu_pozisyonlar) - 1:
            ipucu_mesaji += ", "
    
    # Oyun durumunu güncelle
    oyun['kelime'] = kelime
    oyun['karisik_kelime'] = karisik_kelime
    
    # Eski oyun mesajını sil ve yeni mesajı ayrı gönder
    try:
        if oyun.get('current_message_id'):
            await context.bot.delete_message(chat_id, oyun['current_message_id'])
    except Exception:
        pass
    
    # Kelimeyi geçen kullanıcı için bilgi mesajı
    kalan_hak = oyun['max_kelime_degistirme'] - oyun['kelime_degistirme_sayisi']
    
    gecme_mesaji = (
        f"🔄 <a href='tg://user?id={user_id}'>{user_name}</a> kelimeyi geçti!\n\n"
        f"🎯 <b>Geçilen Kelime:</b> <code>{eski_kelime.upper()}</code>\n"
        f"🎯 <b>Kalan Hak:</b> {kalan_hak}\n"
        f"💡 <b>Yeni Kelime:</b> {ipucu_mesaji}"
    )
    
    await context.bot.send_message(
        chat_id,
        gecme_mesaji,
        parse_mode="HTML"
    )

    # Bonus puan bilgisi
    base_puan = _raunda_gore_puan(oyun['raund'])
    bonus_puan = oyun['puan'] - base_puan
    bonus_text = f" (+{bonus_puan} bonus)" if bonus_puan > 0 else ""
    
    vurgulu_karisik = ' '.join(list(karisik_kelime))
    oyun_mesaji = (
        f"🎲 Raund {oyun['raund']}/{oyun['max_raund']}\n"
        f"🔤 <b>Karışık Kelime:</b> <code>{vurgulu_karisik}</code>\n"
        f"🧮 <b>Harf Sayısı:</b> {len(kelime)}\n"
        f"💡 <b>İpucu:</b> {ipucu_mesaji}\n"
        f"🏆 <b>Puan:</b> {oyun['puan']}{bonus_text}\n"
        f"🔄 <b>Kelime Değiştirme:</b> {oyun['kelime_degistirme_sayisi']}/{oyun['max_kelime_degistirme']}\n\n"
        f"🎯 Orijinal kelimeyi tahmin edin!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Kelimeyi Geç", callback_data="turet_yeni_kelime")],
        [InlineKeyboardButton("❌ Oyunu Bitir", callback_data="turet_oyun_bitir")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    yeni_mesaj = await context.bot.send_message(
        chat_id,
        oyun_mesaji,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    oyun['current_message_id'] = yeni_mesaj.message_id

async def turet_oyun_bitir_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()
    if chat_id in turet_oyun_durumu:
        # Zamanlayıcı görevini iptal et
        try:
            if 'zamanlayici_task' in turet_oyun_durumu[chat_id]:
                zamanlayici_task = turet_oyun_durumu[chat_id]['zamanlayici_task']
                if not zamanlayici_task.done():
                    zamanlayici_task.cancel()
        except Exception as e:
            print(f"Zamanlayıcı iptal hatası: {e}")
        
        turet_oyun_durumu[chat_id]['aktif'] = False
    try:
        await query.edit_message_text("⏹️ Kelimeyi Türet oyunu sonlandırıldı.")
    except Exception as e:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="⏹️ Kelimeyi Türet oyunu sonlandırıldı."
        )

def turet_oyunu_durdur(chat_id):
    """Belirtilen chat'teki türet oyununu durdurur"""
    if chat_id in turet_oyun_durumu and turet_oyun_durumu[chat_id]['aktif']:
        # Zamanlayıcı görevini iptal et
        try:
            if 'zamanlayici_task' in turet_oyun_durumu[chat_id]:
                zamanlayici_task = turet_oyun_durumu[chat_id]['zamanlayici_task']
                if not zamanlayici_task.done():
                    zamanlayici_task.cancel()
        except Exception as e:
            print(f"Zamanlayıcı iptal hatası: {e}")
        
        # Oyunu durdur
        turet_oyun_durumu[chat_id]['aktif'] = False
        return True
    return False
