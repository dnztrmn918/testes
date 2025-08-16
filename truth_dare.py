import json
import random
from typing import Dict, List
from telegram import Update
from telegram.ext import ContextTypes


TRUTH_KEY = "dogruluk"
DARE_KEY = "cesaret"
TRUTH_DARE_PATH = "kelimeler/truth_dare.json"
TRUTH_MIN = 500
DARE_MIN = 100
RECENT_LIMIT = 50

_truth_dare_cache: Dict[str, List[str]] | None = None
_recent_truth: Dict[int, List[str]] = {}
_recent_dare: Dict[int, List[str]] = {}


def _load_truth_dare() -> Dict[str, List[str]]:
    global _truth_dare_cache
    if _truth_dare_cache is not None:
        return _truth_dare_cache
    try:
        with open(TRUTH_DARE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Güvenli tür dönüşümü
            truths = list(map(str, data.get(TRUTH_KEY, [])))
            dares = list(map(str, data.get(DARE_KEY, [])))
            _truth_dare_cache = {TRUTH_KEY: truths, DARE_KEY: dares}
            changed = _ensure_min_items(_truth_dare_cache)
            if changed:
                _persist_augmented_data(_truth_dare_cache)
            return _truth_dare_cache
    except Exception:
        # Dosya okunamazsa temel fallback
        _truth_dare_cache = {
            TRUTH_KEY: [
                "En büyük korkun nedir?",
                "Hiç birine yalan söyleyip yakalandın mı?",
            ],
            DARE_KEY: [
                "30 saniye boyunca komik bir dans yap.",
                "Telefon rehberinden birini ara ve şarkı söyle.",
            ],
        }
        _ensure_min_items(_truth_dare_cache)
        return _truth_dare_cache


def _ensure_min_items(store: Dict[str, List[str]]) -> bool:
    # Basit ve güvenli şablonlarla çeşit üret
    truth_templates = [
        "Son 24 saatte yaptığın en utanç verici şey neydi?",
        "Kimseye söylemediğin ama söylemek istediğin şey nedir?",
        "Bir sırrını şimdi paylaşmak zorunda olsan neyi seçerdin?",
        "Çocukken yaptığın en komik şey neydi?",
        "Asla söylemem dediğin ama şimdi söyleyebileceğin gerçek ne?",
        "Ailenin bilmediği ama arkadaşlarının bildiği bir şey söyle.",
        "Bugüne kadar yaptığın en çılgınca şey neydi?",
        "Bir ilişkide en çok sakladığın şey nedir?",
        "Birini kırdığını bildiğin ama özür dilemediğin bir an var mı?",
        "Seni en çok ne utandırır?",
    ]
    dare_templates = [
        "Gruba en komik sticker'ını yolla.",
        "Sesli sohbette 10 saniye boyunca şarkı söyle.",
        "Bir üyenin adını kullanarak şiir yaz ve gönder.",
        "Sırf bu tur için profil fotoğrafını 5 dakika değiştir.",
        "3 farklı aksanla 'Merhaba' de ve ses kaydı at.",
        "Gruba en son çektiğin fotoğrafı gönder.",
        "Rastgele bir emoji seç ve 20 saniye o emoji gibi davran.",
        "Bir reklam sunucusu gibi konuşup 15 saniyelik ses kaydı at.",
        "Bir film repliğini abartılı biçimde canlandır ve gönder.",
        "Kendini spiker gibi tanıtıp 10 saniyelik bir anons yap.",
    ]

    changed = False
    targets = ((TRUTH_KEY, truth_templates, TRUTH_MIN), (DARE_KEY, dare_templates, DARE_MIN))
    for key, templates, min_count in targets:
        pool = store.get(key, [])
        seen = set(pool)
        i = 0
        while len(pool) < min_count:
            base = random.choice(templates)
            # Küçük varyasyonlar ekle (tekrarı azaltmak için)
            suffix = random.choice([
                "",
                " (dürüst ol!)",
                " (tek kelimeyle cevapla)",
                " (detay ver)",
                " (kısaca anlat)",
            ])
            cand = f"{base}{suffix}"
            if cand not in seen:
                pool.append(cand)
                seen.add(cand)
                changed = True
            i += 1
            if i > min_count * 10:
                break
        store[key] = pool
        # Zorunlu tamamlayıcı: hâlâ eksikse sayılı varyantlarla doldur
        n = 1
        while len(store[key]) < min_count:
            base = random.choice(templates)
            cand = f"{base} #{n}"
            if cand not in seen:
                store[key].append(cand)
                seen.add(cand)
                changed = True
            n += 1
    return changed


def _persist_augmented_data(store: Dict[str, List[str]]) -> None:
    try:
        with open(TRUTH_DARE_PATH, "w", encoding="utf-8") as f:
            json.dump({TRUTH_KEY: store.get(TRUTH_KEY, []), DARE_KEY: store.get(DARE_KEY, [])}, f, ensure_ascii=False, indent=2)
    except Exception:
        # Sessizce geç; dosya yazılamazsa çalışma zamanı yine de devam eder
        pass


def _choose_non_repeating(items: List[str], recent: List[str]) -> str:
    if not items:
        return ""
    recent_set = set(recent[-RECENT_LIMIT:]) if recent else set()
    candidates = [x for x in items if x not in recent_set]
    if not candidates:
        candidates = items[:]  # hepsi tüketildiyse sıfırla
    return random.choice(candidates)


async def dogruluk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _load_truth_dare()
    chat_id = update.effective_chat.id if update.effective_chat else 0
    hist = _recent_truth.setdefault(chat_id, [])
    soru = _choose_non_repeating(data[TRUTH_KEY], hist) if data[TRUTH_KEY] else "Bir doğruluk sorusu bulunamadı."
    mesaj = (
        "🟦 <b>Doğruluk</b>\n\n"
        f"❓ {soru}"
    )
    await update.message.reply_text(mesaj, parse_mode="HTML")
    if soru:
        hist.append(soru)
        if len(hist) > RECENT_LIMIT:
            del hist[: len(hist) - RECENT_LIMIT]


async def cesaret_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _load_truth_dare()
    chat_id = update.effective_chat.id if update.effective_chat else 0
    hist = _recent_dare.setdefault(chat_id, [])
    gorev = _choose_non_repeating(data[DARE_KEY], hist) if data[DARE_KEY] else "Bir cesaret görevi bulunamadı."
    mesaj = (
        "🟥 <b>Cesaret</b>\n\n"
        f"🎯 {gorev}"
    )
    await update.message.reply_text(mesaj, parse_mode="HTML")
    if gorev:
        hist.append(gorev)
        if len(hist) > RECENT_LIMIT:
            del hist[: len(hist) - RECENT_LIMIT]



