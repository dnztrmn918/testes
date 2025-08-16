from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from puan_sistemi import puan_sistemi

async def siralama_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sıralama menüsünü gösterir"""
    keyboard = [
        [InlineKeyboardButton("🎯 Tabu", callback_data="siralama_tabu")],
        [InlineKeyboardButton("🔤 Kelimeyi Türet", callback_data="siralama_kelimeyi_turet")],
        [InlineKeyboardButton("🧠 Soru Bankası", callback_data="siralama_soru_bankasi")],
        [InlineKeyboardButton("🌍 Ülkeyi Tahmin Et", callback_data="siralama_sehir_ulke")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏆 <b>SIRALAMA SİSTEMİ</b> 🏆\n\n"
        "Hangi oyunun sıralamasını görmek istiyorsun?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def siralama_oyun_secimi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyun seçimi callback'i"""
    query = update.callback_query
    await query.answer()
    
    oyun_tipi = query.data.split("_")[1] + "_" + query.data.split("_")[2]
    chat_id = query.message.chat.id
    
    oyun_adi = {
        "tabu": "🎯 Tabu",
        "kelimeyi_turet": "🧩 Kelimeyi Türet",
        "soru_bankasi": "🧠 Soru Bankası",
        "sehir_ulke": "🌍 Ülkeyi Tahmin Et",
    }.get(oyun_tipi, oyun_tipi)
    
    keyboard = [
        [InlineKeyboardButton("🌍 Global Sıralama", callback_data=f"global_siralama_{oyun_tipi}")],
        [InlineKeyboardButton("🏠 Yerel Sıralama", callback_data=f"yerel_siralama_{oyun_tipi}_{chat_id}")],
        [InlineKeyboardButton("🔙 Geri", callback_data="siralama_geri")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🏆 <b>{oyun_adi} Sıralaması</b> 🏆\n\n"
        f"Hangi sıralamayı görmek istiyorsun?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def global_siralama_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global sıralama callback'i"""
    query = update.callback_query
    await query.answer()
    
    oyun_tipi = query.data.split("_")[2] + "_" + query.data.split("_")[3]
    
    oyun_adi = {
        "tabu": "🎯 Tabu",
        "kelimeyi_turet": "🧩 Kelimeyi Türet",
        "soru_bankasi": "🧠 Soru Bankası",
        "sehir_ulke": "🏙️ Şehir-Ülke",
    }.get(oyun_tipi, oyun_tipi)
    
    top_oyuncular = puan_sistemi.global_top_puanlar(oyun_tipi, 10)
    
    if not top_oyuncular:
        await query.edit_message_text(
            f"🏆 <b>{oyun_adi} - Global Sıralama</b> 🏆\n\n"
            f"Henüz hiç puan kaydedilmemiş!",
            parse_mode="HTML"
        )
        return
    
    mesaj = f"🌍 <b>{oyun_adi}</b> — <i>Global Sıralama</i>\n\n"
    
    for i, oyuncu in enumerate(top_oyuncular, 1):
        # Madalya emojileri
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."
        
        # Grup isimleri ve varsa kullanıcı adı ile link
        chat_names = oyuncu.get("chat_names", [])
        chat_usernames = oyuncu.get("chat_usernames", [])
        chat_info = ""
        if chat_names:
            parts = []
            for idx, name in enumerate(chat_names):
                uname = chat_usernames[idx] if idx < len(chat_usernames) else None
                if uname:
                    parts.append(f"<a href='https://t.me/{uname}'>{name}</a>")
                else:
                    parts.append(name)
            chat_info = " (" + ", ".join(parts) + ")"
        user_id = oyuncu.get("_id")
        user_name = oyuncu.get("user_name", "Kullanıcı")
        if user_id:
            user_html = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
        else:
            user_html = f"<b>{user_name}</b>"
        mesaj += f"{medal} {user_html}{chat_info} — <b>{oyuncu['toplam_puan']}</b> puan\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Geri", callback_data="siralama_geri")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def yerel_siralama_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yerel sıralama callback'i"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split("_")
    oyun_tipi = data_parts[2] + "_" + data_parts[3]
    chat_id = int(data_parts[4])
    
    # Özel chat kontrolü
    if query.message.chat.type == "private":
        await query.edit_message_text(
            "❌ <b>Yerel Sıralama</b> ❌\n\n"
            "Bu özellik sadece gruplarda çalışır!\n\n"
            "🌍 Global sıralamayı görmek için Global Sıralama butonunu kullanın.",
            parse_mode="HTML"
        )
        return
    
    oyun_adi = {
        "tabu": "🎯 Tabu",
        "kelimeyi_turet": "🧩 Kelimeyi Türet",
        "soru_bankasi": "🧠 Soru Bankası",
        "sehir_ulke": "🌍 Ülkeyi Tahmin Et",
    }.get(oyun_tipi, oyun_tipi)
    
    top_oyuncular = puan_sistemi.top_puanlar(oyun_tipi, 10, chat_id)
    
    if not top_oyuncular:
        await query.edit_message_text(
            f"🏆 <b>{oyun_adi} - Yerel Sıralama</b> 🏆\n\n"
            f"Bu grupta henüz hiç puan kaydedilmemiş!",
            parse_mode="HTML"
        )
        return
    
    mesaj = f"🏠 <b>{oyun_adi}</b> — <i>Yerel Sıralama</i>\n\n"
    
    for i, oyuncu in enumerate(top_oyuncular, 1):
        # Madalya emojileri
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."
        
        uid = oyuncu.get("user_id") or oyuncu.get("_id")
        uname = oyuncu.get("user_name", "Kullanıcı")
        if uid:
            user_html = f"<a href='tg://user?id={uid}'>{uname}</a>"
        else:
            user_html = f"<b>{uname}</b>"
        mesaj += f"{medal} {user_html} — <b>{oyuncu['puan']}</b> puan\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Geri", callback_data="siralama_geri")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def siralama_geri_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sıralama geri callback'i"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎯 Tabu", callback_data="siralama_tabu")],
        [InlineKeyboardButton("🔤 Kelimeyi Türet", callback_data="siralama_kelimeyi_turet")],
        [InlineKeyboardButton("🧠 Soru Bankası", callback_data="siralama_soru_bankasi")],
        [InlineKeyboardButton("🌍 Ülkeyi Tahmin Et", callback_data="siralama_sehir_ulke")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏆 <b>SIRALAMA SİSTEMİ</b> 🏆\n\n"
        "Hangi oyunun sıralamasını görmek istiyorsun?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
