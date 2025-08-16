from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto
from siralama_komutlari import siralama_komutu, siralama_oyun_secimi_callback, global_siralama_callback, yerel_siralama_callback, siralama_geri_callback

# Bilgi mesajı
BILGI_MESAJI = (
    "🎉 <b>Oyun ve Eğlence Botu'na Hoşgeldin!</b> 🎉\n\n"
    "Bu bot ile arkadaşlarınla <b>gruplarda</b> eğlenceli oyunlar oynayabilir, müzik ve şiir kanalımıza katılabilirsin!\n\n"
    "🎮 <b>Mevcut Oyunlar:</b>\n"
            "• 🎯 <b>Tabu:</b> Kelimeyi anlat, arkadaşların tahmin etsin\n"
    "• 🔤 <b>Kelimeyi Türet:</b> Karışık harflerden orijinal kelimeyi bul\n"
    "• 🧠 <b>Soru Bankası:</b> Kategori seç, soruları cevapla, puan topla\n"
    "• 🌍 <b>Ülkeyi Tahmin Et:</b> Şehirden ülkeyi bul\n"
    "• 💕 <b>Eros:</b> Rastgele eşleşmeler yap\n\n"
    "Aşağıdaki butonları kullanarak hemen başlayabilirsin! 👇"
)

# Start menüsü butonları
START_KEYBOARD = [
    [InlineKeyboardButton("🎮 Beni Gruba Ekle", url="https://t.me/tubidyoyunbot?startgroup=true")],
    [
        InlineKeyboardButton("👨‍💻 Yapımcı", url="https://t.me/dnztrmnn"),
        InlineKeyboardButton("🛡️ Moderatör", url="https://t.me/cevatbey")
    ],
    [
        InlineKeyboardButton("🕹️ Oyun Grubu", url="https://t.me/sohbetgo_tr"),
        InlineKeyboardButton("🎵 Şiir Müzik Kanalı", url="https://t.me/tubidymusic")
    ],
    [
        InlineKeyboardButton("ℹ️ Yardım", callback_data="help"),
        InlineKeyboardButton("🏆 Sıralama", callback_data="siralama")
    ]
]

# Yardım mesajı
HELP_MESAJI = """🎮 <b>OYUN BOTU YARDIM MENÜSÜ</b> 🎮

Bu bot ile eğlenceli oyunlar oynayabilir, puan kazanabilir ve arkadaşlarınla yarışabilirsin!

🎮 <b>Oyun Menüsü:</b>
/oyun - Tüm oyunları gör ve başlat

📊 <b>Puan Sistemi:</b>
/puan - Kendi puanını gör
/siralama - Sıralama tablosunu gör

❓ <b>Detaylı Yardım:</b>
Aşağıdaki butonlardan oyunlar hakkında detaylı bilgi alabilirsin!

🔧 <b>Diğer Komutlar:</b>
/start - Ana menü
/help - Bu yardım menüsü"""

# Yardım klavyesi
HELP_KEYBOARD = [
    [InlineKeyboardButton("🎯 Tabu", callback_data="help_tabu")],
    [InlineKeyboardButton("🔤 Kelimeyi Türet", callback_data="help_kelimeyi_turet")],
    [InlineKeyboardButton("🧠 Soru Bankası", callback_data="help_soru_bankasi")],
    [InlineKeyboardButton("🌍 Ülkeyi Tahmin Et", callback_data="help_ulkeyi_tahmin")],
    [InlineKeyboardButton("💕 Eros", callback_data="help_eros")],
    [InlineKeyboardButton("🏆 Sıralama", callback_data="siralama")],
    [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_to_start")]
]

# Bot gruba eklendiğinde gönderilecek mesaj
GRUP_MESAJI = (
    "🎉 <b>Bot Gruba Eklendi!</b> 🎉\n\n"
    "Eklediğiniz için teşekkür ederim! 🙏\n\n"
    "🎮 <b>Oyun Nasıl Başlatılır?</b>\n"
    "1️⃣ /oyun yazarak oyun menüsünü açın\n"
    "2️⃣ Oynamak istediğiniz oyunu seçin\n"
    "3️⃣ Eğlenceli oyunlara başlayın!\n\n"
    "🎵 <b>Müzik ve Şiir Kanalımız:</b>\n"
    "Aşağıdaki butona tıklayarak kanalımıza katılabilirsiniz!"
)

GRUP_KEYBOARD = [
    [InlineKeyboardButton("🎵 Şiir Müzik Kanalı", url="https://t.me/tubidymusic")]
]

# Özel mesajlarda grup komutları için mesaj
OZEL_GRUP_KOMUTU_MESAJI = (
    "😔 <b>Üzgünüm!</b> 😔\n\n"
    "Bu komut sadece <b>gruplarda</b> çalışır.\n"
    "Beni grubuna ekleyerek oyunları oynayabilirsin!\n\n"
    "🎮 <b>Grup Oyunları:</b>\n"
    "• 🎯 Tabu\n"
    "• 🔤 Kelimeyi Türet\n"
    "• 🧠 Soru Bankası\n"
    "• 🌍 Ülkeyi Tahmin Et\n"
    "• 💕 Eros\n"
    "• 🎭 Doğruluk/Cesaret\n\n"
    "👇 Aşağıdaki butonu kullanarak beni grubuna ekleyebilirsin!"
)

OZEL_GRUP_KOMUTU_KEYBOARD = [
    [InlineKeyboardButton("🎮 Beni Gruba Ekle", url="https://t.me/tubidyoyunbot?startgroup=true")],
    [InlineKeyboardButton("🏠 Ana Menü", callback_data="back_to_start")]
]

async def ozel_grup_komutu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Özel mesajlarda grup komutları için handler"""
    chat_type = update.effective_chat.type
    
    if chat_type == "private":
        # Özel chat'te grup komutu kullanıldı
        reply_markup = InlineKeyboardMarkup(OZEL_GRUP_KOMUTU_KEYBOARD)
        
        await update.message.reply_text(
            OZEL_GRUP_KOMUTU_MESAJI,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return True  # Komut işlendi
    return False  # Komut işlenmedi (grupta)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komutu - Sadece özel chat'te çalışır"""
    chat_type = update.effective_chat.type
    
    if chat_type == "private":
        # Özel chat - Resim ve butonlu menü göster
        reply_markup = InlineKeyboardMarkup(START_KEYBOARD)
        
        try:
            # Resim ile birlikte mesaj gönder
            await update.message.reply_photo(
                photo="resim/start.png",
                caption=BILGI_MESAJI,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception:
            # Resim bulunamazsa sadece metin gönder
            await update.message.reply_text(
                BILGI_MESAJI,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
    else:
        # Grup chat - Start komutu özelden kullanılmalı
        await update.message.reply_text(
            "❌ Bu komut sadece özel mesajda kullanılabilir.\n\n"
            "✅ Lütfen bana özelden yaz: /start",
            parse_mode="HTML"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help komutu"""
    chat_type = update.effective_chat.type
    
    if chat_type == "private":
        # Özel chat için yardım menüsü
        keyboard = [
            [InlineKeyboardButton("🎯 Tabu", callback_data="help_tabu")],
            [InlineKeyboardButton("🔤 Kelimeyi Türet", callback_data="help_kelimeyi_turet")],
            [InlineKeyboardButton("🧠 Soru Bankası", callback_data="help_soru_bankasi")],
            [InlineKeyboardButton("🌍 Ülkeyi Tahmin Et", callback_data="help_ulkeyi_tahmin")],
            [InlineKeyboardButton("🎲 Doğruluk / Cesaret", callback_data="help_truth_dare")],
            [InlineKeyboardButton("👨‍💻 Yapımcı", url="https://t.me/dnztrmnn")],
            [InlineKeyboardButton("🛡️ Moderatör", url="https://t.me/cevatbey")],
            [InlineKeyboardButton("🏆 Sıralama", callback_data="siralama")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 <b>OYUN YARDIM MENÜSÜ</b> 🎮\n\n"
            "Hangi oyun hakkında bilgi almak istiyorsun?",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        # Grup chat için oyun butonları
        keyboard = [
            [InlineKeyboardButton("🎯 Tabu", callback_data="help_tabu")],
            [InlineKeyboardButton("🔤 Kelimeyi Türet", callback_data="help_kelimeyi_turet")],
            [InlineKeyboardButton("🧠 Soru Bankası", callback_data="help_soru_bankasi")],
            [InlineKeyboardButton("🌍 Ülkeyi Tahmin Et", callback_data="help_ulkeyi_tahmin")],
            [InlineKeyboardButton("🎲 Doğruluk / Cesaret", callback_data="help_truth_dare")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 <b>OYUN YARDIM MENÜSÜ</b> 🎮\n\n"
            "Hangi oyun hakkında bilgi almak istiyorsun?",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

async def sstop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sstop komutu"""
    await update.message.reply_text(
        "🛑 <b>Oyun Durdurma</b> 🛑\n\n"
        "Bu komut henüz aktif değil.",
        parse_mode="HTML"
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help callback"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Mesaj düzenlemeyi dene
        await query.edit_message_text(
            HELP_MESAJI,
            reply_markup=get_help_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        # Mesaj düzenlenemezse yeni mesaj gönder
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=HELP_MESAJI,
                reply_markup=get_help_menu(),
                parse_mode="HTML"
            )
        except Exception as e2:
            print(f"Help callback hatası: {e2}")
            # Son çare: sadece metin gönder
            await query.answer("❌ Mesaj gönderilemedi!", show_alert=True)

async def siralama_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sıralama callback"""
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

async def yapimci_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yapımcı callback"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "👨‍💻 <b>YAPIMCI BİLGİLERİ</b> 👨‍💻\n\n"
        "🎮 <b>Bot Adı:</b> Oyun Botu\n"
        "👨‍💻 <b>Yapımcı:</b> @tubidy\n"
        "📧 <b>İletişim:</b> @tubidy\n"
        "🌐 <b>Website:</b> https://t.me/tubidymusic\n\n"
        "🎵 <b>Müzik Kanalı:</b> @tubidymusic\n"
        "🕹️ <b>Oyun Grubu:</b> @oyungrubu",
        parse_mode="HTML"
    )

async def moderator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Moderatör callback"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🛡️ <b>MODERATÖR</b> 🛡️\n\n"
        "Moderatör: @cevatbey",
        parse_mode="HTML"
    )

async def game_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım menüsündeki Oyun Menüsü butonu için oyun seçim klavyesini gösterir"""
    from game import game_command
    query = update.callback_query
    await query.answer()
    # Callback olduğu için direkt game_command'u tetikleyemiyoruz; menüyü yeniden gönderelim
    keyboard = [
        [
            InlineKeyboardButton("🎯 Tabu", callback_data='tabu'),
            InlineKeyboardButton("🧩 Kelime Türet", callback_data='kelimeyi_turet'),
        ],
        [
            InlineKeyboardButton("🎭 Yalancıyı Bul", callback_data='yalanciyi_tahmin_et'),
            InlineKeyboardButton("🌍 Ülkeyi Tahmin Et", callback_data='tahminle_konus'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎮 İstediğiniz herhangi bir oyunu seçip oyunun keyfini çıkarabilirsiniz! 🎯", reply_markup=reply_markup)

def get_start_menu():
    return InlineKeyboardMarkup(START_KEYBOARD)

def get_help_menu():
    return InlineKeyboardMarkup(HELP_KEYBOARD)

async def help_tabu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tabu yardım callback - detaylı, süslü"""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mesaj = (
        "🎯 <b>TABU</b> 🎯\n\n"
        "🎭 <b>Nasıl Oynanır:</b>\n"
        "• Sunucu kelimeyi görür ve sohbette anlatmaya çalışır\n"
        "• Diğer oyuncular kelimeyi tahmin etmeye çalışır\n"
        "• Kelimeyi doğru bilen kişi puan kazanır ve sonraki sunucu olur\n\n"
        "🛠️ <b>Oyun Başlatma:</b>\n"
        "1️⃣ /oyun yaz → Tabu'yu seç\n"
        "2️⃣ Sunucu atanır ve kelimeyi görür\n"
        "3️⃣ Kelimeyi Geç butonu ile yeni kelime isteyebilirsin\n\n"
        "🏆 <b>Puan Sistemi:</b>\n"
        "• Doğru tahmin: +3 puan (raund ilerledikçe artar)\n"
        "• Sunucu olma: Doğru bilen kişi 10 saniye öncelik kazanır\n\n"
        "⏳ <b>Oyun Süresi:</b>\n"
        "• 15 dakika pasiflikte oyun otomatik biter\n\n"
        "🛑 <b>Oyun Durdurma:</b>\n"
        "• /sstop komutu ile oyunu durdurabilirsin\n"
        "• Aktif mesaj silinir ve oyun kapanır"
    )
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def help_kelimeyi_turet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kelimeyi Türet yardım callback - detaylı, süslü"""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mesaj = (
        "🔤 <b>KELİMEYİ TÜRET</b> 🔤\n\n"
        "🧩 <b>Nasıl Oynanır:</b>\n"
        "• Karışık harflerden orijinal kelimeyi bulmaya çalış\n"
        "• İpucu ve harf sayısı verilir\n"
        "• Kelimeyi Geç butonu ile yeni kelime isteyebilirsin\n\n"
        "🛠️ <b>Oyun Başlatma:</b>\n"
        "1️⃣ /oyun yaz → Kelimeyi Türet'i seç\n"
        "2️⃣ Karışık kelimeyi gör ve sohbette tahmin yaz\n"
        "3️⃣ Kelimeyi Geç ile yeni kelime iste (eski mesaj silinir)\n\n"
        "🏆 <b>Puan Sistemi:</b>\n"
        "• Raund 1: +2 puan\n"
        "• Raund 2: +3 puan\n"
        "• Raund 3: +5 puan\n"
        "• Raund 4: +7 puan\n"
        "• Bonus kelimeler: Ekstra puan + 1 hak\n\n"
        "⏳ <b>Oyun Süresi:</b>\n"
        "• 15 dakika pasiflikte oyun otomatik biter\n\n"
        "🛑 <b>Oyun Durdurma:</b>\n"
        "• /sstop komutu ile oyunu durdurabilirsin\n"
        "• Aktif mesaj silinir ve oyun kapanır"
    )
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def help_soru_bankasi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Soru Bankası (Quiz) yardım callback"""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mesaj = (
        "🧠 <b>SORU BANKASI (QUIZ)</b> 🧠\n\n"
        "🎛️ <b>Nasıl Oynanır:</b>\n"
        "• Kategori seç (Film, Müzik, Coğrafya, Ünlü, Spor, Tarih, Edebiyat)\n"
        "• 5 seçenekli anket ile cevap ver\n"
        "• 30 saniye süren var\n"
        "• 20 raund sürer\n\n"
        "🛠️ <b>Oyun Başlatma:</b>\n"
        "1️⃣ /oyun yaz → Soru Bankası'nı seç\n"
        "2️⃣ Kategori seç → anket ile soru gelir\n"
        "3️⃣ A, B, C, D, E seçeneklerinden birini seç\n\n"
        "🏆 <b>Puan Sistemi:</b>\n"
        "• Doğru cevap: +3 puan\n"
        "• Yanlış cevap: 0 puan\n"
        "• Süre dolduğunda doğru cevap gösterilir\n\n"
        "⏳ <b>Oyun Süresi:</b>\n"
        "• Her soru için 30 saniye\n"
        "• 15 dakika pasiflikte oyun otomatik biter\n\n"
        "🛑 <b>Oyun Durdurma:</b>\n"
        "• /sstop komutu ile oyunu durdurabilirsin\n"
        "• Aktif mesaj silinir ve oyun kapanır"
    )
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def help_ulkeyi_tahmin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ülkeyi Tahmin Et yardım callback"""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mesaj = (
        "🌍 <b>ÜLKEYİ TAHMİN ET</b> 🌍\n\n"
        "🏙️ <b>Nasıl Oynanır:</b>\n"
        "• Verilen şehirden ülkeyi tahmin et\n"
        "• Örnek: Ankara → Türkiye\n"
        "• Türkçe isimler ve yaygın kısaltmalar kabul edilir\n"
        "• Örnek: ABD → Amerika, İngiltere → UK\n\n"
        "🛠️ <b>Oyun Başlatma:</b>\n"
        "1️⃣ /oyun yaz → Ülkeyi Tahmin Et'i seç\n"
        "2️⃣ Şehir mesajı gelir, ülke ismini yaz\n"
        "3️⃣ Geç butonu ile yeni soru iste (eski mesaj silinir)\n\n"
        "🏆 <b>Puan Sistemi:</b>\n"
        "• Doğru cevap: +2 puan\n"
        "• Yanlış cevap: 0 puan\n"
        "• Geçilen sorular puan vermez\n\n"
        "⏳ <b>Oyun Süresi:</b>\n"
        "• 15 dakika pasiflikte oyun otomatik biter\n\n"
        "🛑 <b>Oyun Durdurma:</b>\n"
        "• /sstop komutu ile oyunu durdurabilirsin\n"
        "• Aktif mesaj silinir ve oyun kapanır"
    )
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def help_eros_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eros yardım callback"""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mesaj = (
        "💕 <b>EROS</b> 💕\n\n"
        "💘 <b>Nasıl Oynanır:</b>\n"
        "• Rastgele iki kişi eşleştirilir\n"
        "• Eşleşen kişiler birbirlerine mesaj gönderebilir\n"
        "• Aynı kişiler tekrar eşleşmez (son 10 eşleşme hatırlanır)\n\n"
        "🛠️ <b>Oyun Başlatma:</b>\n"
        "1️⃣ /oyun yaz → Eros'u seç\n"
        "2️⃣ Rastgele eşleşme yapılır\n"
        "3️⃣ Eşleşen kişiler gösterilir\n\n"
        "🏆 <b>Özellikler:</b>\n"
        "• Tekrar eşleşme engellenir\n"
        "• Eşleşme sayısı gösterilir\n"
        "• Küçük gruplarda otomatik temizlik\n\n"
        "⏳ <b>Oyun Süresi:</b>\n"
        "• Anlık eşleşme, süre yok\n\n"
        "🛑 <b>Oyun Durdurma:</b>\n"
        "• /sstop komutu ile oyunu durdurabilirsin\n"
        "• Aktif mesaj silinir ve oyun kapanır"
    )
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def help_truth_dare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Doğruluk / Cesaret yardım callback"""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mesaj = (
        "🎲 <b>DOĞRULUK / CESARET</b>\n\n"
        "🟦 Doğruluk için: <b>/d</b> yaz\n"
        "🟥 Cesaret için: <b>/c</b> yaz\n\n"
        "📚 Sorular ve görevler ‘kelimeler/truth_dare.json’ dosyasından seçilir.\n"
        "🎨 Mesajlar emojilerle süslenir, buton yoktur."
    )
    await query.edit_message_text(mesaj, reply_markup=reply_markup, parse_mode="HTML")

async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # Resim ile birlikte mesaj gönder
        await query.edit_message_media(
            media=InputMediaPhoto(
                media="resim/start.png",
                caption=BILGI_MESAJI,
                parse_mode="HTML"
            ),
            reply_markup=get_start_menu()
        )
    except Exception:
        # Resim bulunamazsa sadece metin gönder
        await query.edit_message_text(BILGI_MESAJI, reply_markup=get_start_menu(), parse_mode="HTML")

async def new_chat_members_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni üye eklendiğinde çalışır"""
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            # Bot gruba eklendi
            keyboard = [
                [InlineKeyboardButton("🎵 Şiir Müzik Kanalı", url="https://t.me/tubidymusic")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                GRUP_MESAJI,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            break

# Oyun detay mesajları
TABU_MESAJI = (
    "<b>🎯 TABU OYUNU</b>\n\n"
    "<b>📋 Oyun Amacı:</b>\n"
    "Bir kelimeyi sadece hareketlerle anlatmak!\n\n"
    "<b>🎮 Nasıl Oynanır:</b>\n"
    "1️⃣ /oyun komutu ile menüyü açın ve Tabu'yu seçin\n"
    "2️⃣ Sunucu kelimeyi görür ve hareketlerle anlatır\n"
    "3️⃣ Diğer oyuncular tahmin etmeye çalışır\n"
    "4️⃣ Doğru bilen kişi sunucu olur\n\n"
    "<b>📝 Komutlar:</b>\n"
    "• <b>/oyun</b> - Oyun menüsü\n"
    "• <b>Kelimeyi Gör</b> - Kelimeyi gör (sadece sunucu)\n"
    "• <b>Kelimeyi Geç</b> - Yeni kelime iste (sadece sunucu)\n"
    "• <b>Sunucu İstemiyorum</b> - Sunuculuktan çık\n\n"
    "<b>⚠️ Kurallar:</b>\n"
    "• Konuşmak yasak!\n"
    "• Sadece hareket kullanın\n"
    "• Ses çıkarmayın\n"
    "• Yazı yazmayın\n\n"
    "<b>🏆 Puanlama:</b>\n"
    "• Doğru tahmin: +3 puan (başlangıç)\n"
    "• Her 5 raundta +1 puan artış\n"
    "• Maksimum 10 puan"
)

KELIMEYI_TURET_MESAJI = (
    "<b>📝 KELİMEYİ TÜRET OYUNU</b>\n\n"
    "<b>📋 Oyun Amacı:</b>\n"
    "Verilen kelimeden yeni kelimeler türetmek!\n\n"
    "<b>🎮 Nasıl Oynanır:</b>\n"
    "1️⃣ /turet komutu ile oyunu başlatın\n"
    "2️⃣ Bot bir ana kelime verir\n"
    "3️⃣ Oyuncular bu kelimeden türetilen kelimeler yazar\n"
    "4️⃣ En çok kelime bulan kazanır\n\n"
    "<b>📝 Komutlar:</b>\n"
    "• <b>/turet</b> - Oyunu başlat\n"
    "• <b>Yeni Kelime</b> - Farklı kelime iste\n"
    "• <b>Oyunu Bitir</b> - Oyunu sonlandır\n\n"
    "<b>⚠️ Kurallar:</b>\n"
    "• Ana kelimenin harflerini kullanın\n"
    "• Anlamlı kelimeler yazın\n"
    "• Türkçe kelimeler olmalı\n"
    "• Aynı kelimeyi tekrar yazmayın\n\n"
    "<b>🏆 Puanlama:</b>\n"
    "• Her kelime: +1 puan\n"
    "• Uzun kelimeler: Bonus puan"
)

YALANCIYI_TAHMİN_MESAJI = (
    "<b>🎭 YALANCIYI TAHMİN ET OYUNU</b>\n\n"
    "<b>📋 Oyun Amacı:</b>\n"
    "Yalancıları bulmak ve dürüstleri korumak!\n\n"
    "<b>🎮 Nasıl Oynanır:</b>\n"
    "1️⃣ /yalan komutu ile oyunu başlatın\n"
    "2️⃣ Oyuncular özelden katılır\n"
    "3️⃣ Herkese farklı kelimeler verilir\n"
    "4️⃣ Yalancılar farklı kelime alır\n"
    "5️⃣ Konuşarak yalancıları bulun\n"
    "6️⃣ Oylama ile yalancıyı seçin\n\n"
    "<b>📝 Komutlar:</b>\n"
    "• <b>/yalan</b> - Oyunu başlat\n"
    "• <b>/uzat</b> - Süreyi uzat\n"
    "• <b>/ybaslat</b> - Hızlı başlat\n\n"
    "<b>⚠️ Kurallar:</b>\n"
    "• Kelimeyi direkt söylemek yasak!\n"
    "• Tanımlayarak anlatın\n"
    "• Yalancıları kandırmaya çalışın\n"
    "• Dürüstleri koruyun\n\n"
    "<b>🏆 Kazanan:</b>\n"
    "• Dürüstler yalancıyı bulursa: Dürüstler kazanır\n"
    "• Yalancı yakalanmazsa: Yalancılar kazanır"
)

async def help_tabu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(TABU_MESAJI, reply_markup=reply_markup, parse_mode="HTML")

async def help_kelimeyi_turet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(KELIMEYI_TURET_MESAJI, reply_markup=reply_markup, parse_mode="HTML")

async def help_yalanciyi_tahmin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(YALANCIYI_TAHMİN_MESAJI, reply_markup=reply_markup, parse_mode="HTML")

async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(BILGI_MESAJI, reply_markup=get_start_menu(), parse_mode="HTML")

async def new_chat_members_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni üye eklendiğinde çalışır"""
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            # Bot gruba eklendi
            keyboard = [
                [InlineKeyboardButton("🎵 Şiir Müzik Kanalı", url="https://t.me/tubidymusic")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                GRUP_MESAJI,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            break

# Eksik callback fonksiyonları
async def kelime_gor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kelime gör callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bu özellik henüz aktif değil.")

async def kelime_gec_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kelime geç callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bu özellik henüz aktif değil.")

async def sunucu_istemiyorum_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sunucu istemiyorum callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bu özellik henüz aktif değil.")

async def sunucu_ol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sunucu ol callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bu özellik henüz aktif değil.")

async def sunucu_ol_serbest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sunucu ol serbest callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bu özellik henüz aktif değil.")

async def turet_yeni_kelime_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Türet yeni kelime callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bu özellik henüz aktif değil.")

async def turet_oyun_bitir_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Türet oyun bitir callback"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bu özellik henüz aktif değil.")

async def game_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Game button handler"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "tabu":
        await query.edit_message_text("🎯 Tabu oyunu başlatılıyor...")
    elif query.data == "kelimeyi_turet":
        await query.edit_message_text("🔤 Kelimeyi Türet oyunu başlatılıyor...")
    elif query.data == "yalanciyi_tahmin_et":
        await query.edit_message_text("🎭 Yalancıyı Tahmin Et oyunu başlatılıyor...")
    elif query.data == "tahminle_konus":
        await query.edit_message_text("Bu özellik henüz aktif değil.")

async def birlesik_tahmin_kontrol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Birleşik tahmin kontrol: ilgili tüm oyun tahmin kontrollerini sırasıyla çağırır."""
    handlers = []
    try:
        from sessiz import tabu_tahmin_kontrol  # type: ignore
        handlers.append(tabu_tahmin_kontrol)
    except Exception:
        pass
    try:
        from türet import turet_tahmin_kontrol  # type: ignore
        handlers.append(turet_tahmin_kontrol)
    except Exception:
        pass
    try:
        from yalan import quiz_tahmin_kontrol  # type: ignore
        handlers.append(quiz_tahmin_kontrol)
    except Exception:
        pass
    try:
        from tahminle import tahminle_tahmin_kontrol  # type: ignore
        handlers.append(tahminle_tahmin_kontrol)
    except Exception:
        pass

    for handler in handlers:
        try:
            await handler(update, context)
        except Exception:
            pass

