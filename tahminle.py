from telegram.ext import ContextTypes
from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
import json
import random
import re
import unicodedata

# Metin normalizasyonu: Türkçe karakterleri esneterek eşleştirir
def _normalize_country_text(text: str) -> str:
    s = unicodedata.normalize('NFKC', text or '')
    s = s.replace('İ', 'i').replace('I', 'ı').lower()
    tr_map = str.maketrans({
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u'
    })
    s = s.translate(tr_map)
    # Latin karakterleri sadeleştir (örn. ü -> u zaten çevrildi)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    s = ''.join(ch for ch in s if ch.isalnum())
    return s

# Ülke takma adları (alias) - normalize edilmiş halleriyle kontrol edilecek
_RAW_COUNTRY_ALIASES = {
    # Türkçe sade biçimler
    'Türkiye': {'Türkiye'},
    'Amerika Birleşik Devletleri': {'Amerika'},
    'Birleşik Krallık': {'Birleşik Krallık', 'İngiltere'},
    'Birleşik Arap Emirlikleri': {'Birleşik Arap Emirlikleri'},
    'Güney Kore': {'Güney Kore', 'Kore'},
    'Çin': {'Çin'},
    'Hollanda': {'Hollanda'},
    'Çekya': {'Çekya', 'Çek Cumhuriyeti'},
    'Mısır': {'Mısır'},
    'Fas': {'Fas'},
    'Yeni Zelanda': {'Yeni Zelanda'},
    'Almanya': {'Almanya'},
    'Fransa': {'Fransa'},
    'İspanya': {'İspanya'},
    'İtalya': {'İtalya'},
    'Yunanistan': {'Yunanistan'},
    'Avusturya': {'Avusturya'},
    'Portekiz': {'Portekiz'},
    'İsviçre': {'İsviçre'},
    'İsveç': {'İsveç'},
    'Norveç': {'Norveç'},
    'Finlandiya': {'Finlandiya'},
    'Polonya': {'Polonya'},
    'Romanya': {'Romanya'},
    'Bulgaristan': {'Bulgaristan'},
    'Ukrayna': {'Ukrayna'},
    'Kanada': {'Kanada'},
    'Meksika': {'Meksika'},
    'Arjantin': {'Arjantin'},
    'Brezilya': {'Brezilya'},
    'Japonya': {'Japonya'},
    'Hindistan': {'Hindistan'},
    'İran': {'İran'},
    'Irak': {'Irak'},
    'Suudi Arabistan': {'Suudi Arabistan'},
    'Endonezya': {'Endonezya'},
    'Malezya': {'Malezya'},
    'Singapur': {'Singapur'},
    'Tayland': {'Tayland'},
    'Filipinler': {'Filipinler'},
    'Vietnam': {'Vietnam'},
    'Pakistan': {'Pakistan'},
    'Bangladeş': {'Bangladeş'},
    'İsrail': {'İsrail'},
    'Lübnan': {'Lübnan'},
    'Ürdün': {'Ürdün'},
    'Nijerya': {'Nijerya'},
    'Güney Afrika': {'Güney Afrika'},
}

# Normalize alias map
_COUNTRY_ALIASES = {}
for k, vals in _RAW_COUNTRY_ALIASES.items():
    nk = _normalize_country_text(k)
    _COUNTRY_ALIASES[nk] = {_normalize_country_text(v) for v in vals}

def _is_country_guess_correct(guess: str, correct_country: str) -> bool:
    g = _normalize_country_text(guess)
    c = _normalize_country_text(correct_country)
    if not g:
        return False
    if g == c:
        return True
    # Alias kontrolü
    alias_set = _COUNTRY_ALIASES.get(c, set())
    if g in alias_set:
        return True
    # İçerme esnekliği (ör. "turkiye cumhuriyeti" → turkiye)
    if len(g) >= 2 and (g in c or c in g):
        return True
    for alias in alias_set:
        if len(g) >= 2 and (g in alias or alias in g):
            return True
    return False

# Oyun durumu için bellek
tahminle_oyun_durumu = {}

async def tahminle_konus_baslat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    chat_id = query.message.chat.id
    
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
    
    # Veriyi yükle ve yeni şemaya göre dönüştür (ülkeler -> sehir kayıtları)
    try:
        with open('kelimeler/sehir_ulkeler.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            ulkeler = data.get('ulkeler', [])
            veriler = []
            for kayit in ulkeler:
                ulke_adi = kayit.get('ulke')
                baskent = kayit.get('baskent')
                for sehir in kayit.get('sehirler', []):
                    veriler.append({
                        'sehir': sehir,
                        'ulke': ulke_adi,
                        'baskent': baskent,
                    })
    except Exception:
        veriler = []
    tahminle_oyun_durumu[chat_id] = {
        'aktif': True,
        'veriler': veriler,
        'kullanilan': set(),
        'current_message_id': None
    }
    await yeni_sehir_sor(chat_id, context)

async def yeni_sehir_sor(chat_id, context: ContextTypes.DEFAULT_TYPE):
    if chat_id not in tahminle_oyun_durumu:
        return
    oyun = tahminle_oyun_durumu[chat_id]
    if not oyun['veriler']:
        await context.bot.send_message(chat_id, "❌ Veri bulunamadı.")
        oyun['aktif'] = False
        return
    # Kullanılmayan rastgele şehir seç
    max_try = len(oyun['veriler'])
    idx = None
    for _ in range(max_try):
        cand = random.randrange(0, len(oyun['veriler']))
        if cand not in oyun['kullanilan']:
            idx = cand
            break
    if idx is None:
        oyun['kullanilan'] = set()
        idx = random.randrange(0, len(oyun['veriler']))
    oyun['kullanilan'].add(idx)
    kayit = oyun['veriler'][idx]
    sehir = kayit.get('sehir', '')
    oyun['aktif_kayit'] = kayit
    # Tek buton: Geç
    keyboard = [[InlineKeyboardButton("🔄 Geç", callback_data='tahminle_gec')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await context.bot.send_message(
        chat_id,
        f"🌍 <b>Ülkeyi Tahmin Et</b>\n\n🏙️ <b>Şehir:</b> <code>{sehir}</code>\n\nBu şehir hangi ülkeye bağlıdır?\n\nİpucu: Ülke adını yazınız (TR/USA gibi kısaltmalar da geçerli).",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    oyun['current_message_id'] = msg.message_id

async def tahminle_tahmin_kontrol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in tahminle_oyun_durumu:
        return
    oyun = tahminle_oyun_durumu[chat_id]
    if not oyun.get('aktif') or not oyun.get('aktif_kayit'):
        return
    raw_guess = (update.message.text or '').strip()
    raw_ans = (oyun['aktif_kayit'].get('ulke', '')).strip()
    eslesme = _is_country_guess_correct(raw_guess, raw_ans)
    if eslesme:
        user = update.effective_user
        try:
            chat = await context.bot.get_chat(chat_id)
            chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Bilinmeyen Grup"
            chat_username = getattr(chat, 'username', None)
        except Exception:
            chat_name = "Bilinmeyen Grup"
            chat_username = None
        # Puan ekle (Şehir-Ülke oyunu)
        try:
            from puan_sistemi import puan_sistemi
            puan_sistemi.puan_ekle(user.id, user.first_name, 'sehir_ulke', 2, chat_id, chat_name, chat_username)
        except Exception:
            pass
        await context.bot.send_message(chat_id, f"✅ Doğru! <a href='tg://user?id={user.id}'>{user.first_name}</a>", parse_mode='HTML')
        try:
            if oyun['current_message_id']:
                await context.bot.delete_message(chat_id, oyun['current_message_id'])
        except Exception:
            pass
        await yeni_sehir_sor(chat_id, context)
    else:
        # Yakın tahmin geri bildirimi (ör. ülke adının en az yarısı örtüşüyorsa)
        g = _normalize_country_text(raw_guess)
        c = _normalize_country_text(raw_ans)
        if g and c:
            overlap = 0
            # basit subseq skorlaması
            i = j = 0
            while i < len(g) and j < len(c):
                if g[i] == c[j]:
                    overlap += 1
                    i += 1
                    j += 1
                else:
                    j += 1
            if overlap >= max(2, len(c)//2):
                try:
                    await context.bot.send_message(chat_id, "🤏 Çok yakındı! Biraz daha dene ✨")
                except Exception:
                    pass

async def tahminle_gec_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    if chat_id not in tahminle_oyun_durumu:
        return
    oyun = tahminle_oyun_durumu[chat_id]
    if oyun.get('aktif_kayit'):
        sehir = oyun['aktif_kayit'].get('sehir', '')
        ulke = oyun['aktif_kayit'].get('ulke', '')
        baskent = oyun['aktif_kayit'].get('baskent', '')
        detay = f" — Başkent: <b>{baskent}</b>" if baskent else ""
        await context.bot.send_message(chat_id, f"🔄 Geçildi. Doğru cevap: <b>{ulke}</b> ({sehir}){detay}", parse_mode='HTML')
    try:
        if oyun['current_message_id']:
            await context.bot.delete_message(chat_id, oyun['current_message_id'])
    except Exception:
        pass
    await yeni_sehir_sor(chat_id, context)

def tahminle_oyunu_durdur(chat_id):
    """Belirtilen chat'teki tahminle oyununu durdurur"""
    if chat_id in tahminle_oyun_durumu and tahminle_oyun_durumu[chat_id].get('aktif', False):
        tahminle_oyun_durumu[chat_id]['aktif'] = False
        return True
    return False
