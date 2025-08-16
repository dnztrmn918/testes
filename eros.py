from __future__ import annotations

import html
import random
from collections import OrderedDict
from typing import Dict, List, Tuple

from telegram import Update
from telegram.ext import ContextTypes


# Her sohbet için son görülen kullanıcıları tutar (en fazla 200 kişi)
_recent_chat_users: Dict[int, OrderedDict[int, Tuple[str, int]]] = {}
_MAX_USERS_PER_CHAT = 200

# Bilinen grup üyeleri: chat_id -> user_id -> (display_name, is_bot)
_known_chat_users: Dict[int, Dict[int, Tuple[str, bool]]] = {}

# Her sohbet için son kullanılan kişileri takip eder (tekrar önleme)
_used_eros_pairs: Dict[int, List[Tuple[int, int]]] = {}
_MAX_PAIRS_MEMORY = 50  # Son 50 eşleşmeyi hatırla


def _remember_user(chat_id: int, user_id: int, display_name: str) -> None:
    store = _recent_chat_users.setdefault(chat_id, OrderedDict())
    if user_id in store:
        # Yeniden sona taşı
        store.move_to_end(user_id)
    store[user_id] = (display_name, user_id)
    # Limit aşılırsa baştan sil
    while len(store) > _MAX_USERS_PER_CHAT:
        store.popitem(last=False)


def _remember_known(chat_id: int, user_id: int, display_name: str, is_bot: bool) -> None:
    users = _known_chat_users.setdefault(chat_id, {})
    users[user_id] = (display_name, is_bot)


def _is_pair_used(chat_id: int, user1_id: int, user2_id: int) -> bool:
    """Bu eşleşme daha önce kullanıldı mı kontrol eder."""
    used_pairs = _used_eros_pairs.get(chat_id, [])
    pair = tuple(sorted([user1_id, user2_id]))  # Sıra önemli değil
    return pair in used_pairs


def _mark_pair_used(chat_id: int, user1_id: int, user2_id: int) -> None:
    """Bu eşleşmeyi kullanıldı olarak işaretler."""
    if chat_id not in _used_eros_pairs:
        _used_eros_pairs[chat_id] = []
    
    used_pairs = _used_eros_pairs[chat_id]
    pair = tuple(sorted([user1_id, user2_id]))  # Sıra önemli değil
    
    # Eşleşmeyi ekle
    used_pairs.append(pair)
    
    # Limit aşılırsa en eskiyi sil
    while len(used_pairs) > _MAX_PAIRS_MEMORY:
        used_pairs.pop(0)


async def eros_seen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Her mesajda kullanıcıyı hatırla (gruplarda eşleştirme için havuz)."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user or user.is_bot:
        return

    display_name = user.full_name or (user.username or str(user.id))
    _remember_user(chat.id, user.id, display_name)
    _remember_known(chat.id, user.id, display_name, user.is_bot or False)


async def eros_member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yeni/ayrılan üyeleri takip eder ve bilinenler listesinde günceller."""
    chat = update.effective_chat
    msg = update.effective_message
    if not chat or not msg:
        return
    # Yeni katılanlar
    if msg.new_chat_members:
        for m in msg.new_chat_members:
            if m:
                dn = m.full_name or (m.username or str(m.id))
                _remember_known(chat.id, m.id, dn, m.is_bot or False)
                if not m.is_bot:
                    _remember_user(chat.id, m.id, dn)
    # Ayrılan üye
    if msg.left_chat_member:
        m = msg.left_chat_member
        try:
            if chat.id in _known_chat_users:
                _known_chat_users[chat.id].pop(m.id, None)
        except Exception:
            pass


async def eros_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if not chat:
        return

    # Sadece grup/supergroup
    if chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text("❌ Bu komut sadece gruplarda kullanılabilir.")
        return

    # Öncelikle bilinen grup üyeleri (bot olmayanlar)
    known = _known_chat_users.get(chat.id, {})
    candidates: OrderedDict[int, Tuple[str, int]] = OrderedDict()
    for uid, (dn, is_bot) in known.items():
        if not is_bot:
            candidates[uid] = (dn, uid)

    # Komutu yazan kişiyi de ekle (varsa)
    if user and not user.is_bot:
        display_name = user.full_name or (user.username or str(user.id))
        _remember_user(chat.id, user.id, display_name)
        # Bilinenlere de mevcudu ekle
        _remember_known(chat.id, user.id, display_name, False)
        if user.id not in candidates:
            candidates[user.id] = (display_name, user.id)

    # Hâlâ azsa: son görülenlerden doldur
    if len(candidates) < 2:
        recent = _recent_chat_users.get(chat.id, OrderedDict())
        for uid, (dn, _uid) in recent.items():
            if uid not in candidates:
                candidates[uid] = (dn, uid)

    # Hâlâ yetersizse yöneticilerden doldurmayı dene
    if len(candidates) < 2:
        try:
            admins = await context.bot.get_chat_administrators(chat.id)
            for adm in admins:
                adm_user = adm.user
                if adm_user and not adm_user.is_bot:
                    dn = adm_user.full_name or (adm_user.username or str(adm_user.id))
                    if adm_user.id not in candidates:
                        candidates[adm_user.id] = (dn, adm_user.id)
        except Exception:
            pass

    # Hala 2 kişi yoksa vazgeç
    if len(candidates) < 2:
        await update.effective_message.reply_text(
            "🙈 Yeterli kişi yok gibi görünüyor. Biraz sohbet olunca tekrar dene!"
        )
        return
    
    # Eğer çok az kişi varsa ve tüm eşleşmeler kullanılmışsa hafızayı temizle
    if len(candidates) <= 4 and chat.id in _used_eros_pairs:
        max_possible_pairs = len(candidates) * (len(candidates) - 1) // 2
        if len(_used_eros_pairs[chat.id]) >= max_possible_pairs:
            _used_eros_pairs[chat.id].clear()

    # Kullanılmamış eşleşme bulmaya çalış
    ids: List[int] = list(candidates.keys())
    max_attempts = 100  # Maksimum deneme sayısı
    
    for _ in range(max_attempts):
        pair = random.sample(ids, 2)
        user1_id, user2_id = pair[0], pair[1]
        
        # Bu eşleşme daha önce kullanıldı mı?
        if not _is_pair_used(chat.id, user1_id, user2_id):
            # Kullanılmamış eşleşme bulundu
            break
    else:
        # Tüm eşleşmeler kullanılmış, hafızayı temizle ve yeni eşleşme yap
        if chat.id in _used_eros_pairs:
            _used_eros_pairs[chat.id].clear()
        pair = random.sample(ids, 2)
        user1_id, user2_id = pair[0], pair[1]
    
    u1 = candidates[user1_id]
    u2 = candidates[user2_id]

    name1 = html.escape(u1[0])
    name2 = html.escape(u2[0])
    id1 = u1[1]
    id2 = u2[1]
    
    # Bu eşleşmeyi kullanıldı olarak işaretle
    _mark_pair_used(chat.id, id1, id2)

    # İsteğe bağlı: uyum yüzdesi
    uyum = random.randint(42, 99)

    # Kullanılan eşleşme sayısını hesapla
    used_count = len(_used_eros_pairs.get(chat.id, []))
    total_possible = len(candidates) * (len(candidates) - 1) // 2
    
    text = (
        "💘 <b>Eros</b> okunu fırlattı! 🎯\n\n"
        f"❤️ <a href='tg://user?id={id1}'>{name1}</a>  +  "
        f"<a href='tg://user?id={id2}'>{name2}</a> ❤️\n\n"
        f"💞 Uyum: <b>%{uyum}</b> • Mutluluklar! 💘\n"
        f"📊 Eşleşme: {used_count}/{total_possible}"
    )

    await update.effective_message.reply_text(text, parse_mode="HTML")


