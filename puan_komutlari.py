from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from puan_sistemi import puan_sistemi

async def puan_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının puanlarını gösterir"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    istatistikler = puan_sistemi.kullanici_istatistikleri(user_id)
    
    if not istatistikler:
        await update.message.reply_text(
            (
                f"🏁 <b>PUANLAR</b>\n\n"
                f"👤 <b>{user_name}</b> henüz puan kazanmamış.\n\n"
                f"🎮 Oyunlar:\n"
                f"• 🧩 Kelimeyi Türet\n"
                f"• 🎯 Tabu\n"
                f"• 🧠 Soru Bankası"
            ),
            parse_mode="HTML"
        )
        return
    
    mesaj = f"🏆 <b>{user_name}</b> — <i>Puan İstatistikleri</i>\n\n"
    
    toplam_puan = 0
    for oyun_tipi, puan in istatistikler.items():
        oyun_adi = {
            "kelimeyi_turet": "🧩 Kelimeyi Türet",
            "tabu": "🎯 Tabu",
            "yalanciyi_tahmin": "🎭 Yalancıyı Tahmin Et",
            "soru_bankasi": "🧠 Soru Bankası",
        }.get(oyun_tipi, oyun_tipi)

        mesaj += f"• {oyun_adi}: <b>{puan}</b> puan\n"
        toplam_puan += puan
    
    mesaj += f"\n🔢 <b>Toplam Puan:</b> <b>{toplam_puan}</b>"
    
    await update.message.reply_text(mesaj, parse_mode="HTML")

async def top_puanlar_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """En yüksek puanlı oyuncuları gösterir"""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            (
                "🏅 <b>TOP PUANLAR</b>\n\n"
                "Kullanım: <code>/top &lt;oyun_tipi&gt;</code>\n\n"
                "Oyun türleri:\n"
                "• <code>kelimeyi_turet</code>\n"
                "• <code>tabu</code>\n"
                "• <code>soru_bankasi</code>"
            ),
            parse_mode="HTML"
        )
        return
    
    oyun_tipi = args[0].lower()
    
    oyun_adi = {
        "kelimeyi_turet": "🧩 Kelimeyi Türet",
        "tabu": "🎯 Tabu",
        "yalanciyi_tahmin": "🎭 Yalancıyı Tahmin Et",
        "soru_bankasi": "🧠 Soru Bankası",
    }.get(oyun_tipi, oyun_tipi)
    
    top_oyuncular = puan_sistemi.top_puanlar(oyun_tipi, 10)
    
    if not top_oyuncular:
        await update.message.reply_text(
            f"🏅 <b>{oyun_adi}</b> — <i>Top Puanlar</i>\n\nHenüz hiç puan yok.",
            parse_mode="HTML"
        )
        return
    
    mesaj = f"🏅 <b>{oyun_adi}</b> — <i>Top Puanlar</i>\n\n"
    
    for i, oyuncu in enumerate(top_oyuncular, 1):
        rozet = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        mesaj += f"{rozet} <b>{oyuncu['user_name']}</b> — <b>{oyuncu['puan']}</b> puan\n"
    
    await update.message.reply_text(mesaj, parse_mode="HTML")

async def puan_yardim_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Puan sistemi hakkında yardım mesajı"""
    await update.message.reply_text(
        "📊 <b>Puan Sistemi</b>\n\n"
        "🎮 <b>Oyunlar ve Puanlar:</b>\n"
        "• Kelimeyi Türet: 2 puan\n"
        "• Tabu: 3 puan\n"
        "• Yalancıyı Tahmin Et: 5 puan\n\n"
        "📋 <b>Komutlar:</b>\n"
        "/puan - Kendi puanlarını gör\n"
        "/top <oyun_tipi> - Top puanları gör\n"
        "/puan_yardim - Bu mesajı göster\n\n"
        "🏆 Puanlarınız MongoDB'de saklanır ve kalıcıdır!",
        parse_mode="HTML"
    )
