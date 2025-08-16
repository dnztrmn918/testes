from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sessiz import tabu_baslat, tabu_oyunu_durdur, tabu_oyun_durumu
from türet import kelimeyi_turet_baslat, turet_oyunu_durdur, turet_oyun_durumu
from yalan import yalan_quiz_menu_from_game, yalan_quiz_durdur, yalan_quiz_oyunlari
from tahminle import tahminle_konus_baslat, tahminle_oyunu_durdur, tahminle_oyun_durumu

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎯 Tabu", callback_data='tabu'),
            InlineKeyboardButton("🧩 Kelime Türet", callback_data='kelimeyi_turet'),
        ],
        [
            InlineKeyboardButton("🧠 Soru Bankası", callback_data='yalanciyi_tahmin_et'),
            InlineKeyboardButton("🌍 Ülkeyi Tahmin Et", callback_data='tahminle_konus'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await update.message.reply_text("🎮 İstediğiniz herhangi bir oyunu seçip oyunun keyfini çıkarabilirsiniz! 🎯", reply_markup=reply_markup)
    except Exception as e:
        # Eğer reply_text başarısız olursa, normal send_message kullan
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🎮 İstediğiniz herhangi bir oyunu seçip oyunun keyfini çıkarabilirsiniz! 🎯",
            reply_markup=reply_markup
        )

async def game_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    oyun = query.data
    chat_id = query.message.chat.id

    # Aktif oyun kontrolü
    aktif_oyunlar = []
    if chat_id in yalan_quiz_oyunlari and getattr(yalan_quiz_oyunlari[chat_id], 'aktif', False):
        aktif_oyunlar.append("Soru Bankası")
    if chat_id in tabu_oyun_durumu and tabu_oyun_durumu[chat_id].get('aktif', False):
        aktif_oyunlar.append("Tabu")
    if chat_id in turet_oyun_durumu and turet_oyun_durumu[chat_id].get('aktif', False):
        aktif_oyunlar.append("Kelime Türet")
    if chat_id in tahminle_oyun_durumu and tahminle_oyun_durumu[chat_id].get('aktif', False):
        aktif_oyunlar.append("Ülkeyi Tahmin Et")

    if aktif_oyunlar:
        await query.edit_message_text(
            f"⚠️ Aktif oyunlar var! Önce mevcut oyunları bitirin.\n\n"
            f"Aktif oyunlar:\n" + "\n".join([f"• {oyun}" for oyun in aktif_oyunlar]) + "\n\n"
            f"Oyunları durdurmak için /stopgame komutunu kullanın."
        )
        return

    # Oyunu başlatmadan önce menü mesajını silmeye çalış
    try:
        await context.bot.delete_message(chat_id, query.message.message_id)
    except Exception:
        pass

    # Oyunu başlat
    if oyun == 'tabu':
        await tabu_baslat(query, context)
    elif oyun == 'kelimeyi_turet':
        await kelimeyi_turet_baslat(query, context)
    elif oyun == 'yalanciyi_tahmin_et':
        await yalan_quiz_menu_from_game(query, context)
    elif oyun == 'tahminle_konus':
        await tahminle_konus_baslat(query, context)

async def stopgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm aktif oyunları durdurur ve aktif oyun mesajlarını siler"""
    chat_id = update.effective_chat.id
    durdurulan_oyunlar = []
    
    # Yalan oyununu durdur
    if yalan_quiz_durdur(chat_id):
        durdurulan_oyunlar.append("Soru Bankası")
    
    # Tabu oyununu durdur
    if tabu_oyunu_durdur(chat_id):
        durdurulan_oyunlar.append("Tabu")
        try:
            from sessiz import tabu_oyun_durumu
            msg_id = tabu_oyun_durumu.get(chat_id, {}).get('current_message_id')
            if msg_id:
                try:
                    await context.bot.delete_message(chat_id, msg_id)
                except Exception:
                    try:
                        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="⏹️ Tabu durduruldu.")
                    except Exception:
                        pass
            
            # Sunucu seçim butonunu tekrar aktif hale getir
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("🎯 Tabu Oyunu Başlat", callback_data='tabu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="🎮 <b>Tabu oyunu durduruldu!</b> 🎮\n\nYeni oyun başlatmak için butona tıklayın:",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    # Türet oyununu durdur
    if turet_oyunu_durdur(chat_id):
        durdurulan_oyunlar.append("Kelimeyi Türet")
        try:
            from türet import turet_oyun_durumu
            msg_id = turet_oyun_durumu.get(chat_id, {}).get('current_message_id')
            if msg_id:
                try:
                    await context.bot.delete_message(chat_id, msg_id)
                except Exception:
                    try:
                        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="⏹️ Kelimeyi Türet durduruldu.")
                    except Exception:
                        pass
        except Exception:
            pass
    
    # Tahminle oyununu durdur
    if tahminle_oyunu_durdur(chat_id):
        durdurulan_oyunlar.append("Ülkeyi Tahmin Et")
        try:
            from tahminle import tahminle_oyun_durumu
            msg_id = tahminle_oyun_durumu.get(chat_id, {}).get('current_message_id')
            if msg_id:
                try:
                    await context.bot.delete_message(chat_id, msg_id)
                except Exception:
                    try:
                        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="⏹️ Ülkeyi Tahmin Et durduruldu.")
                    except Exception:
                        pass
        except Exception:
            pass
    
    if durdurulan_oyunlar:
        mesaj = (
            "🛑 <b>Oyunlar Durduruldu</b> 🛑\n\n" +
                "\n".join([f"• {oyun}" for oyun in durdurulan_oyunlar])
            )
        try:
            await update.message.reply_text(mesaj, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=mesaj, parse_mode="HTML")
    else:
        try:
            await update.message.reply_text("❌ Aktif oyun bulunamadı!")
        except Exception as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Aktif oyun bulunamadı!"
            )
