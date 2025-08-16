from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from config import BOT_TOKEN, TELEGRAM_READ_TIMEOUT, TELEGRAM_WRITE_TIMEOUT, TELEGRAM_CONNECT_TIMEOUT, HTTPX_MAX_CONNECTIONS, HTTPX_POOL_TIMEOUT
from start import (start_command, help_command, help_callback, game_menu_callback, back_to_start_callback, 
                   help_tabu_callback, help_kelimeyi_turet_callback, help_soru_bankasi_callback, 
                   help_ulkeyi_tahmin_callback, help_truth_dare_callback, help_eros_callback, yapimci_callback, 
                   moderator_callback, siralama_callback, ozel_grup_komutu_handler, 
                   new_chat_members_handler, birlesik_tahmin_kontrol)
from game import game_command, game_button_handler, stopgame_command
from tahminle import tahminle_tahmin_kontrol, tahminle_gec_callback
from truth_dare import dogruluk_command, cesaret_command
from eros import eros_command, eros_seen_handler, eros_member_update_handler
from türet import turet_yeni_kelime_callback, turet_oyun_bitir_callback
from yalan import yalan_handlers, yalan_quiz_kategori_sec_callback, yalan_quiz_cevap_callback, yalan_quiz_pass_callback, yalan_quiz_change_callback
from puan_komutlari import puan_komutu, top_puanlar_komutu, puan_yardim_komutu
from siralama_komutlari import siralama_komutu, siralama_oyun_secimi_callback, global_siralama_callback, yerel_siralama_callback, siralama_geri_callback
from sessiz import sunucu_ol_sessiz_callback, kelime_gec_sessiz_callback, sunucu_istemiyorum_sessiz_callback, kelime_gor_sessiz_callback
import os

# Heroku için port ayarı
PORT = int(os.environ.get('PORT', 5000))

def create_app():
    # Optimize edilmiş timeout ayarları ile request objesi oluştur
    request = HTTPXRequest(
        read_timeout=TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        connection_pool_size=HTTPX_MAX_CONNECTIONS,  # Connection pool boyutunu ayarla
        pool_timeout=HTTPX_POOL_TIMEOUT  # Pool timeout'u ayarla
    )
    
    # HTTPX connection pool ayarlarını environment variables ile yap
    os.environ['HTTPX_MAX_CONNECTIONS'] = str(HTTPX_MAX_CONNECTIONS)
    os.environ['HTTPX_POOL_TIMEOUT'] = str(HTTPX_POOL_TIMEOUT)
    
    # Bot konfigürasyonu - optimize edilmiş ve hızlı
    app = (ApplicationBuilder()
           .token(BOT_TOKEN)
           .request(request)
           .get_updates_request(request)  # get_updates için ayrı request objesi
           .concurrent_updates(True)  # Eşzamanlı güncellemeleri etkinleştir
           .build())
    
    # Bot başlatma ayarları - get_updates_request set edilemiyor, kaldırıldı
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    # /oyun komutu ekle ve /game yerine onu kullan
    async def oyun_wrapper(update, context):
        if await ozel_grup_komutu_handler(update, context):
            return
        await game_command(update, context)
    
    async def stopgame_wrapper(update, context):
        if await ozel_grup_komutu_handler(update, context):
            return
        await stopgame_command(update, context)
    
    async def dogruluk_wrapper(update, context):
        if await ozel_grup_komutu_handler(update, context):
            return
        await dogruluk_command(update, context)
    
    async def cesaret_wrapper(update, context):
        if await ozel_grup_komutu_handler(update, context):
            return
        await cesaret_command(update, context)
    
    async def sstop_wrapper(update, context):
        if await ozel_grup_komutu_handler(update, context):
            return
        await sstop_command(update, context)
    
    async def eros_wrapper(update, context):
        if await ozel_grup_komutu_handler(update, context):
            return
        await eros_command(update, context)
    
    app.add_handler(CommandHandler("oyun", oyun_wrapper))
    app.add_handler(CommandHandler("stopgame", stopgame_wrapper))
    # Doğruluk / Cesaret
    app.add_handler(CommandHandler("d", dogruluk_wrapper))
    app.add_handler(CommandHandler("c", cesaret_wrapper))
    app.add_handler(CommandHandler("sstop", sstop_wrapper))
    # Eros
    app.add_handler(CommandHandler("eros", eros_wrapper))
    
    # Puan sistemi komutları
    app.add_handler(CommandHandler("puan", puan_komutu))
    app.add_handler(CommandHandler("top", top_puanlar_komutu))
    app.add_handler(CommandHandler("puan_yardim", puan_yardim_komutu))
    
    # Sıralama komutları
    app.add_handler(CommandHandler("siralama", siralama_komutu))
    app.add_handler(CommandHandler("rating", siralama_komutu))
    
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(game_menu_callback, pattern="^game$"))
    app.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(help_tabu_callback, pattern="^help_tabu$"))
    app.add_handler(CallbackQueryHandler(help_kelimeyi_turet_callback, pattern="^help_kelimeyi_turet$"))
    app.add_handler(CallbackQueryHandler(help_soru_bankasi_callback, pattern="^help_soru_bankasi$"))
    app.add_handler(CallbackQueryHandler(help_ulkeyi_tahmin_callback, pattern="^help_ulkeyi_tahmin$"))
    app.add_handler(CallbackQueryHandler(help_truth_dare_callback, pattern="^help_truth_dare$"))
    app.add_handler(CallbackQueryHandler(help_eros_callback, pattern="^help_eros$"))
    # Genel kelime/sunucu callback'leri kaldırıldı; oyunlara özel callback'ler kullanılacak
    app.add_handler(CallbackQueryHandler(turet_yeni_kelime_callback, pattern="^turet_yeni_kelime$"))
    app.add_handler(CallbackQueryHandler(turet_oyun_bitir_callback, pattern="^turet_oyun_bitir$"))
    app.add_handler(CallbackQueryHandler(game_button_handler, pattern="^(tabu|kelimeyi_turet|yalanciyi_tahmin_et|tahminle_konus)$"))
    app.add_handler(CallbackQueryHandler(tahminle_gec_callback, pattern="^tahminle_gec$"))
    # Quiz/Soru Bankası callback'leri (ek güvence)
    app.add_handler(CallbackQueryHandler(yalan_quiz_kategori_sec_callback, pattern="^quiz_kat_"))
    app.add_handler(CallbackQueryHandler(yalan_quiz_cevap_callback, pattern="^quiz_cevap_"))
    app.add_handler(CallbackQueryHandler(yalan_quiz_pass_callback, pattern="^quiz_pass$"))
    app.add_handler(CallbackQueryHandler(yalan_quiz_change_callback, pattern="^quiz_change$"))
    
    # Tabu callback'leri - sadece doğru pattern'ler
    app.add_handler(CallbackQueryHandler(sunucu_ol_sessiz_callback, pattern="^sunucu_ol_sessiz$"))
    app.add_handler(CallbackQueryHandler(kelime_gec_sessiz_callback, pattern="^kelime_gec_sessiz$"))
    app.add_handler(CallbackQueryHandler(sunucu_istemiyorum_sessiz_callback, pattern="^sunucu_istemiyorum_sessiz$"))
    app.add_handler(CallbackQueryHandler(kelime_gor_sessiz_callback, pattern="^kelime_gor_sessiz$"))
    
    # Yeni callback'ler
    app.add_handler(CallbackQueryHandler(yapimci_callback, pattern="^yapimci$"))
    app.add_handler(CallbackQueryHandler(moderator_callback, pattern="^moderator$"))
    
    # Sıralama callback'leri
    app.add_handler(CallbackQueryHandler(siralama_callback, pattern="^siralama$"))
    app.add_handler(CallbackQueryHandler(siralama_oyun_secimi_callback, pattern="^siralama_(tabu|kelimeyi_turet|soru_bankasi|sehir_ulke)$"))
    app.add_handler(CallbackQueryHandler(global_siralama_callback, pattern="^global_siralama_"))
    app.add_handler(CallbackQueryHandler(yerel_siralama_callback, pattern="^yerel_siralama_"))
    app.add_handler(CallbackQueryHandler(siralama_geri_callback, pattern="^siralama_geri$"))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), birlesik_tahmin_kontrol))
    # Eros kullanıcı havuzu ve üyelik takibi
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, eros_member_update_handler))
    app.add_handler(MessageHandler(filters.ALL, eros_seen_handler))
    
    # Yalan oyunu handler'larını ekle
    yalan_handlers(app)
    
    return app

# Heroku için app instance'ı
app = create_app()

if __name__ == '__main__':
    app.run_polling()
