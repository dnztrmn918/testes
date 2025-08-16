import json
import random
import asyncio
from datetime import datetime, timedelta
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram.error import TimedOut, NetworkError, TelegramError
import threading
import time
from puan_sistemi import puan_sistemi

# Oyun durumlarını saklamak için global değişkenler
yalan_quiz_oyunlari = {}
# Eski modülle uyumluluk için boş sözlük (artık kullanılmıyor ama import ediliyor)
yalan_oyunlari = {}

class QuizOyun:
    def __init__(self, chat_id: int, baslatan_id: int):
        self.chat_id = chat_id
        self.baslatan_id = baslatan_id
        self.aktif = False
        self.kategori = None
        self.raund = 0
        self.max_raund = 20
        self.puan = 3
        self.current_message_id = None
        self.soru_havuzu = []
        self.aktif_soru = None  # {soru, cevap}
        self.aktif_secenekler = None  # [seçenekler]
        self.kullanici_dogru_sayilari = {}  # {user_id: {"isim": str, "sayi": int}}
        self.kisi_cooldown = {}  # {user_id: datetime}
        self.kullanilan_indeksler = set()  # Tekrarı önlemek için
        self.cevap_verenler = {}  # {user_id: {"isim": str, "secim": str, "dogru": bool}}
        self.cevap_suresi = 15  # 15 saniye anket süresi
        self.cevap_timer = None
        self.anket_mesaj_id = None  # Anket mesaj ID'si

def _normalize_guess(text: str) -> str:
    import unicodedata, re
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    text = text.replace("İ", "i").replace("I", "ı").casefold()
    # Harf/digit dışını sil ve boşlukları da kaldır (boşluksuz karşılaştırma için)
    text = re.sub(r"[^a-zçğıöşü0-9]", "", text)
    return text


async def _process_poll_results(chat_id: int, context: ContextTypes.DEFAULT_TYPE, oyun: QuizOyun):
    """Anket sonuçlarını işler ve puanları hesaplar"""
    try:
        # Doğru cevabı bul
        dogru_cevap = oyun.aktif_soru["cevap"]
        
        # Cevap verenleri işle
        for user_id, bilgi in oyun.cevap_verenler.items():
            if bilgi["dogru"]:
                # Doğru cevap veren kullanıcıya puan ver
                try:
                    # Timeout koruması ile chat bilgisini al
                    chat = await asyncio.wait_for(
                        context.bot.get_chat(chat_id), 
                        timeout=10.0
                    )
                    chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Bilinmeyen Grup"
                except asyncio.TimeoutError:
                    print(f"⏰ Chat bilgisi timeout: {chat_id}")
                    chat_name = "Bilinmeyen Grup"
                except Exception as e:
                    print(f"❌ Chat bilgisi hatası: {e}")
                    chat_name = "Bilinmeyen Grup"
                
                # Puanı "Soru Bankası" oyunu için yaz
                try:
                    basarili, mesaj = puan_sistemi.puan_ekle(user_id, bilgi["isim"], "soru_bankasi", 3, chat_id, chat_name)
                    if basarili:
                        print(f"✅ Puan eklendi: {bilgi['isim']} ({user_id}) +3 puan")
                    else:
                        print(f"❌ Puan eklenemedi: {bilgi['isim']} ({user_id}) - {mesaj}")
                except Exception as e:
                    print(f"❌ Puan ekleme hatası: {e}")
                
                # Kişisel doğru sayısını artır
                kayit = oyun.kullanici_dogru_sayilari.get(user_id, {"isim": bilgi["isim"], "sayi": 0})
                kayit["sayi"] += 1
                oyun.kullanici_dogru_sayilari[user_id] = kayit
        
        # Anket sonuç mesajı oluştur ve gönder
        try:
            await asyncio.wait_for(
                _send_poll_results_message(chat_id, context, oyun),
                timeout=20.0
            )
        except asyncio.TimeoutError:
            print(f"⏰ Sonuç mesajı timeout: {chat_id}")
        except Exception as e:
            print(f"❌ Sonuç mesajı hatası: {e}")
                
    except asyncio.TimeoutError:
        print(f"⏰ Poll results timeout: {chat_id}")
    except Exception as e:
        print(f"❌ Anket sonuçları işlenirken hata: {e}")
        pass

async def _send_poll_results_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE, oyun: QuizOyun):
    """Anket sonuç mesajını gönderir"""
    try:
        # Doğru cevabı bul
        dogru_cevap = oyun.aktif_soru["cevap"]
        dogru_index = None
        secenek_harfleri = ["A", "B", "C", "D", "E"]
        
        for i, secenek in enumerate(oyun.aktif_secenekler):
            if secenek == dogru_cevap:
                dogru_index = i
                break
        
        # Sonuç mesajı oluştur
        sonuc_mesaji = f"⏰ <b>Süre doldu!</b>\n\n"
        sonuc_mesaji += f"✅ <b>Doğru cevap:</b> <code>{dogru_cevap}</code>\n\n"
        
        # Tüm seçenekleri doğru/yanlış işaretleriyle göster
        sonuc_mesaji += "📊 <b>Seçenekler:</b>\n"
        for i, secenek in enumerate(oyun.aktif_secenekler):
            if secenek == dogru_cevap:
                sonuc_mesaji += f"✅ <b>{secenek_harfleri[i]})</b> {secenek} <b>(DOĞRU)</b>\n"
            else:
                sonuc_mesaji += f"❌ <b>{secenek_harfleri[i]})</b> {secenek} <b>(YANLIŞ)</b>\n"
        
        sonuc_mesaji += "\n"
        
        # Cevap verenleri göster
        if oyun.cevap_verenler:
            sonuc_mesaji += "👥 <b>Cevap verenler:</b>\n"
            
            dogru_verenler = []
            yanlis_verenler = []
            
            for user_id, bilgi in oyun.cevap_verenler.items():
                if bilgi["dogru"]:
                    dogru_verenler.append(f"✅ <a href='tg://user?id={user_id}'>{bilgi['isim']}</a> +3 puan")
                else:
                    # Seçenek indeksini seçenek metnine çevir
                    secenek_index = bilgi["secim"]
                    if secenek_index is not None and secenek_index < len(oyun.aktif_secenekler):
                        secilen_secenek = oyun.aktif_secenekler[secenek_index]
                        yanlis_verenler.append(f"❌ <a href='tg://user?id={user_id}'>{bilgi['isim']}</a> ({secilen_secenek})")
                    else:
                        yanlis_verenler.append(f"❌ <a href='tg://user?id={user_id}'>{bilgi['isim']}</a> (Geçersiz seçim)")
            
            if dogru_verenler:
                sonuc_mesaji += "\n🎯 <b>Doğru cevap verenler:</b>\n" + "\n".join(dogru_verenler)
            
            if yanlis_verenler:
                sonuc_mesaji += "\n\n❌ <b>Yanlış cevap verenler:</b>\n" + "\n".join(yanlis_verenler)
        else:
            sonuc_mesaji += "👥 <b>Kimse cevap vermedi</b>\n"
        
        # Mevcut anket mesajını güncelle (yeni mesaj göndermek yerine)
        try:
            if oyun.anket_mesaj_id:
                await asyncio.wait_for(
                    context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=oyun.anket_mesaj_id,
                        text=sonuc_mesaji,
                        parse_mode="HTML"
                    ),
                    timeout=20.0  # Timeout süresini artırdım
                )
                print(f"✅ Anket mesajı güncellendi: {chat_id}")
            else:
                # Eğer anket mesaj ID yoksa yeni mesaj gönder
                await asyncio.wait_for(
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=sonuc_mesaji,
                        parse_mode="HTML"
                    ),
                    timeout=20.0  # Timeout süresini artırdım
                )
                print(f"✅ Anket sonuç mesajı gönderildi: {chat_id}")
        except asyncio.TimeoutError:
            print(f"⏰ Mesaj güncelleme timeout: {chat_id}")
            # Timeout olursa yeni mesaj göndermeyi dene
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=sonuc_mesaji,
                    parse_mode="HTML"
                )
                print(f"✅ Timeout sonrası yeni mesaj gönderildi: {chat_id}")
            except Exception as e2:
                print(f"❌ Timeout sonrası mesaj gönderme de başarısız: {e2}")
        except (TimedOut, NetworkError) as e:
            print(f"⏰ Telegram API timeout/network hatası: {e}")
            # Network hatası olursa yeni mesaj göndermeyi dene
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=sonuc_mesaji,
                    parse_mode="HTML"
                )
                print(f"✅ Network hatası sonrası yeni mesaj gönderildi: {chat_id}")
            except Exception as e2:
                print(f"❌ Network hatası sonrası mesaj gönderme de başarısız: {e2}")
        except Exception as e:
            print(f"❌ Mesaj güncelleme hatası: {e}")
            # Genel hata olursa yeni mesaj göndermeyi dene
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=sonuc_mesaji,
                    parse_mode="HTML"
                )
                print(f"✅ Hata sonrası yeni mesaj gönderildi: {chat_id}")
            except Exception as e2:
                print(f"❌ Hata sonrası mesaj gönderme de başarısız: {e2}")
        
        # 3 saniye sonra yeni soruya geç
        try:
            await asyncio.sleep(3)
            await asyncio.wait_for(
                quiz_yeni_soru(chat_id, context),
                timeout=20.0
            )
        except asyncio.TimeoutError:
            print(f"⏰ Yeni soru gönderme timeout: {chat_id}")
            # Timeout olursa oyunu durdur
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⏰ Yeni soru gönderilemedi. Oyun durduruluyor."
                )
                yalan_quiz_durdur(chat_id)
            except Exception:
                pass
        except Exception as e:
            print(f"❌ Yeni soru hatası: {e}")
            # Hata olursa oyunu durdur
            try:
                yalan_quiz_durdur(chat_id)
            except Exception:
                pass
        
    except asyncio.TimeoutError:
        print(f"⏰ Mesaj güncelleme timeout: {chat_id}")
    except Exception as e:
        print(f"❌ Mesaj güncelleme hatası: {e}")

def _yanlis_secenekler_olustur(dogru_cevap: str, kategori: str, aktif_soru: dict = None) -> list:
    """JSON dosyasından yanlış seçenekleri alır veya eski sistemi kullanır"""
    
    # Eğer JSON'da yanlış seçenekler varsa onları kullan
    if aktif_soru and "yanlis_secenekler" in aktif_soru:
        yanlis_secenekler = aktif_soru["yanlis_secenekler"]
        
        # Doğru cevabı listeden çıkar
        yanlis_secenekler = [s for s in yanlis_secenekler if s.lower() != dogru_cevap.lower()]
        
        # 4 tane yanlış seçenek seç
        secilen_yanlis = random.sample(yanlis_secenekler, min(4, len(yanlis_secenekler)))
        
        # Doğru cevabı ekle ve karıştır
        tum_secenekler = secilen_yanlis + [dogru_cevap]
        random.shuffle(tum_secenekler)
        
        return tum_secenekler
    
    # Eski sistem (fallback)
    # Önce doğru cevabın tipini belirle
    def cevap_tipi_belirle(cevap: str) -> str:
        cevap = str(cevap).strip()
        
        # Yıl kontrolü (4 haneli sayı veya MÖ/MS ile başlayan)
        if (len(cevap) == 4 and cevap.isdigit()) or cevap.startswith(("MÖ ", "MS ")):
            return "yil"
        
        # Sayı kontrolü (1-3 haneli)
        if cevap.isdigit() and 1 <= len(cevap) <= 3:
            return "sayi"
        
        # Okul kontrolü (Hogwarts, Oxford, Cambridge gibi)
        okul_kelimeleri = ["okul", "üniversite", "kolej", "akademi", "enstitü", "school", "university", "college", "academy"]
        if any(okul in cevap.lower() for okul in okul_kelimeleri) or cevap.lower() in ["hogwarts", "oxford", "cambridge", "harvard", "yale", "stanford", "mit", "princeton"]:
            return "okul"
        
        # İsim kontrolü (büyük harfle başlayan, boşluk içeren)
        if cevap and cevap[0].isupper() and " " in cevap:
            return "isim"
        
        # Tek kelime isim
        if cevap and cevap[0].isupper() and len(cevap) > 2:
            return "isim"
        
        # Olay kontrolü (uzun metin, "Devrimi", "Savaşı" gibi)
        if len(cevap) > 10 or any(kelime in cevap for kelime in ["Devrimi", "Savaşı", "Fethi", "Keşfi"]):
            return "olay"
        
        # Varsayılan olarak isim
        return "isim"
    
    cevap_tipi = cevap_tipi_belirle(dogru_cevap)
    
    # Kategori bazlı yanlış seçenekler
    if kategori == "cografya":
        if cevap_tipi == "yil":
            # Yıl sorusu için sadece yıllar
            yanlis_secenekler = [
                "1299", "1453", "1492", "1517", "1520", "1521", "1526", "1534", "1543", "1556",
                "1571", "1588", "1600", "1618", "1620", "1648", "1683", "1699", "1700", "1718",
                "1721", "1730", "1740", "1756", "1763", "1774", "1775", "1776", "1789", "1799",
                "1804", "1812", "1815", "1821", "1830", "1839", "1848", "1853", "1861", "1865"
            ]
        else:
            # İsim/yer sorusu için sadece yerler
            yanlis_secenekler = [
                # Dağlar
                "Everest", "K2", "Kangchenjunga", "Lhotse", "Makalu",
                "Cho Oyu", "Dhaulagiri", "Manaslu", "Nanga Parbat", "Annapurna",
                "Gasherbrum I", "Broad Peak", "Gasherbrum II", "Shishapangma",
                "Ağrı Dağı", "Kilimanjaro", "Mont Blanc", "Matterhorn", "Jungfrau",
                "Mount Whitney", "Denali", "Mount Rainier", "Mount Fuji", "Mount Elbrus",
                
                # Ülkeler
                "Türkiye", "Almanya", "Fransa", "İtalya", "İspanya", "Portekal",
                "Hollanda", "Belçika", "Avusturya", "İsviçre", "Polonya", "Çekya",
                "İngiltere", "İrlanda", "Norveç", "İsveç", "Finlandiya", "Danimarka",
                "Rusya", "Ukrayna", "Belarus", "Romanya", "Bulgaristan", "Yunanistan",
                "Japonya", "Çin", "Güney Kore", "Hindistan", "Pakistan", "Bangladeş",
                "Brezilya", "Arjantin", "Şili", "Peru", "Kolombiya", "Venezuela",
                "Mısır", "Güney Afrika", "Nijerya", "Kenya", "Etiyopya", "Sudan",
                "Kanada", "Meksika", "Avustralya", "Yeni Zelanda", "Fiji", "Papua Yeni Gine",
                
                # Şehirler
                "İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya",
                "Berlin", "Münih", "Hamburg", "Köln", "Frankfurt", "Düsseldorf",
                "Paris", "Lyon", "Marsilya", "Toulouse", "Nice", "Nantes",
                "Roma", "Milano", "Napoli", "Turin", "Palermo", "Bologna",
                "Madrid", "Barselona", "Valencia", "Sevilla", "Bilbao", "Málaga",
                "Londra", "Manchester", "Liverpool", "Birmingham", "Leeds", "Sheffield",
                "Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo", "Kobe",
                "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
                
                # Nehirler
                "Nil", "Amazon", "Yangtze", "Mississippi", "Yenisey", "Ob", "Paraná",
                "Kongo", "Amur", "Lena", "Mackenzie", "Niger", "Mekong", "Ganges",
                "İndus", "Brahmaputra", "Salween", "Irrawaddy", "Chao Phraya", "Red River",
                
                # Göller
                "Van Gölü", "Tuz Gölü", "Beyşehir Gölü", "İznik Gölü", "Manyas Gölü",
                "Baykal Gölü", "Tanganika Gölü", "Victoria Gölü", "Malawi Gölü", "Chad Gölü",
                "Superior Gölü", "Huron Gölü", "Michigan Gölü", "Erie Gölü", "Ontario Gölü",
                
                # Okyanuslar ve Denizler
                "Pasifik Okyanusu", "Atlas Okyanusu", "Hint Okyanusu", "Arktik Okyanusu",
                "Akdeniz", "Karadeniz", "Marmara Denizi", "Ege Denizi", "Kızıldeniz",
                "Baltık Denizi", "Kuzey Denizi", "İrlanda Denizi", "Celtic Denizi",
                
                # Çöller
                "Sahra Çölü", "Gobi Çölü", "Kalahari Çölü", "Namib Çölü", "Atacama Çölü",
                "Patagonya Çölü", "Sonora Çölü", "Mojave Çölü", "Chihuahuan Çölü",
                "Great Basin Çölü", "Thar Çölü", "Taklamakan Çölü", "Karakum Çölü"
            ]
    
    elif kategori == "tarih":
        if cevap_tipi == "yil":
            # Yıl sorusu için sadece yıllar
            yanlis_secenekler = [
                "1299", "1453", "1492", "1517", "1520", "1521", "1526", "1534", "1543", "1556",
                "1571", "1588", "1600", "1618", "1620", "1648", "1683", "1699", "1700", "1718",
                "1721", "1730", "1740", "1756", "1763", "1774", "1775", "1776", "1789", "1799",
                "1804", "1812", "1815", "1821", "1830", "1839", "1848", "1853", "1861", "1865",
                "1870", "1871", "1876", "1881", "1889", "1898", "1900", "1905", "1908", "1914",
                "1917", "1918", "1919", "1920", "1921", "1922", "1923", "1924", "1925", "1926",
                "1927", "1928", "1929", "1930", "1931", "1932", "1933", "1934", "1935", "1936",
                "1937", "1938", "1939", "1940", "1941", "1942", "1943", "1944", "1945", "1946",
                "1947", "1948", "1949", "1950", "1951", "1952", "1953", "1954", "1955", "1956",
                "1957", "1958", "1959", "1960", "1961", "1962", "1963", "1964", "1965", "1966",
                "1967", "1968", "1969", "1970", "1971", "1972", "1973", "1974", "1975", "1976",
                "1977", "1978", "1979", "1980", "1981", "1982", "1983", "1984", "1985", "1986",
                "1987", "1988", "1989", "1990", "1991", "1992", "1993", "1994", "1995", "1996",
                "1997", "1998", "1999", "2000", "2001", "2002", "2003", "2004", "2005", "2006",
                "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016",
                "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"
            ]
        elif cevap_tipi == "isim":
            # İsim sorusu için sadece isimler
            yanlis_secenekler = [
                "Fatih Sultan Mehmet", "Yavuz Sultan Selim", "Kanuni Sultan Süleyman",
                "Atatürk", "İnönü", "Demirel", "Özal", "Erdoğan",
                "Napolyon", "Hitler", "Stalin", "Churchill", "Roosevelt", "Kennedy",
                "Gandhi", "Mandela", "Castro", "Che Guevara", "Mao Zedong", "Deng Xiaoping",
                "Gorbachev", "Yeltsin", "Putin", "Trump", "Biden", "Macron", "Merkel"
            ]
        else:
            # Olay sorusu için sadece olaylar
            yanlis_secenekler = [
                "İstanbul'un Fethi", "Amerika'nın Keşfi", "Reform Hareketi", "Fransız Devrimi", 
                "Sanayi Devrimi", "I. Dünya Savaşı", "II. Dünya Savaşı", "Soğuk Savaş",
                "Berlin Duvarı'nın Yıkılması", "11 Eylül Saldırısı", "Covid-19 Pandemisi",
                "Rus Devrimi", "Çin Devrimi", "Vietnam Savaşı", "Kore Savaşı", "Küba Krizi",
                "Arap-İsrail Savaşı", "İran Devrimi", "Afganistan Savaşı", "Irak Savaşı"
            ]
    
    elif kategori == "spor":
        if cevap_tipi == "yil":
            # Yıl sorusu için sadece yıllar
            yanlis_secenekler = [
                "1958", "1962", "1966", "1970", "1974", "1978", "1982", "1986", "1990", "1994",
                "1998", "2002", "2006", "2010", "2014", "2018", "2022", "2026", "2030"
            ]
        else:
            # İsim sorusu için sadece sporcular, takımlar, ligler
            yanlis_secenekler = [
                # Futbolcular
                "Messi", "Ronaldo", "Neymar", "Mbappé", "Haaland", "Benzema",
                "Lewandowski", "Salah", "Mané", "De Bruyne", "Modrić", "Kroos",
                "Bellingham", "Vini Jr", "Kane", "Foden", "Saka", "Grealish",
                "Sterling", "Mahrez", "Silva", "Gündoğan", "Rodri", "Dias",
                "Van Dijk", "Alisson", "Ederson", "Courtois", "Oblak", "Neuer",
                "Ter Stegen", "Donnarumma", "Maignan", "Bounou", "Livakovic",
                
                # Takımlar
                "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", "Valencia",
                "Manchester City", "Manchester United", "Liverpool", "Chelsea", "Arsenal",
                "Tottenham", "Newcastle", "Aston Villa", "Brighton", "West Ham",
                "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen",
                "Paris Saint-Germain", "Monaco", "Lyon", "Marseille", "Nice",
                "Juventus", "Inter Milan", "AC Milan", "Napoli", "Roma", "Lazio",
                "Porto", "Benfica", "Sporting CP", "Ajax", "PSV", "Feyenoord",
                
                # Ligler
                "Premier Lig", "La Liga", "Bundesliga", "Serie A", "Ligue 1",
                "Primeira Liga", "Eredivisie", "Süper Lig", "Premier League",
                "Championship", "League One", "League Two", "Scottish Premiership",
                
                # Diğer Sporlar
                "LeBron James", "Stephen Curry", "Kevin Durant", "Giannis Antetokounmpo",
                "Nikola Jokic", "Joel Embiid", "Luka Doncic", "Ja Morant", "Zion Williamson",
                "Roger Federer", "Rafael Nadal", "Novak Djokovic", "Andy Murray",
                "Serena Williams", "Venus Williams", "Naomi Osaka", "Ashleigh Barty",
                "Lewis Hamilton", "Max Verstappen", "Charles Leclerc", "Lando Norris",
                "Fernando Alonso", "Sebastian Vettel", "Valtteri Bottas", "Carlos Sainz"
            ]
    
    elif kategori == "film":
        if cevap_tipi == "yil":
            # Yıl sorusu için sadece yıllar
            yanlis_secenekler = [
                "1977", "1980", "1983", "1984", "1985", "1989", "1991", "1993", "1994", "1997",
                "1999", "2001", "2003", "2008", "2009", "2010", "2012", "2015", "2019", "2022"
            ]
        else:
            # İsim sorusu için sadece filmler, yönetmenler, oyuncular
            yanlis_secenekler = [
                # Filmler
                "Titanic", "Avatar", "Avengers", "Star Wars", "Lord of the Rings",
                "Harry Potter", "Jurassic Park", "Forrest Gump", "The Godfather",
                "Inception", "Interstellar", "The Dark Knight", "Pulp Fiction", "Fight Club",
                "Parasite", "Joker", "The Matrix", "Gladiator", "Braveheart", "Titanic",
                "The Lion King", "Frozen", "Toy Story", "Finding Nemo", "Shrek",
                "The Shawshank Redemption", "Schindler's List", "The Green Mile", "Goodfellas",
                "Casino", "Scarface", "Heat", "The Departed", "Gangs of New York",
                
                # Yönetmenler
                "Christopher Nolan", "Peter Jackson", "James Cameron", "Quentin Tarantino",
                "David Fincher", "Francis Ford Coppola", "Martin Scorsese", "Steven Spielberg",
                "Ridley Scott", "Tim Burton", "Wes Anderson", "Coen Brothers", "Guy Ritchie",
                "Zack Snyder", "J.J. Abrams", "Patty Jenkins", "Ava DuVernay", "Greta Gerwig",
                
                # Oyuncular
                "Tom Hanks", "Robert Downey Jr.", "Joaquin Phoenix", "Hans Zimmer",
                "Leonardo DiCaprio", "Brad Pitt", "Johnny Depp", "Tom Cruise", "Will Smith",
                "Denzel Washington", "Morgan Freeman", "Al Pacino", "Robert De Niro",
                "Jack Nicholson", "Meryl Streep", "Sandra Bullock", "Julia Roberts",
                "Charlize Theron", "Nicole Kidman", "Cate Blanchett", "Emma Stone"
            ]
    
    elif kategori == "muzik":
        if cevap_tipi == "yil":
            # Yıl sorusu için sadece yıllar
            yanlis_secenekler = [
                "1960", "1962", "1965", "1967", "1969", "1971", "1973", "1975", "1977", "1979",
                "1981", "1983", "1985", "1987", "1989", "1991", "1993", "1995", "1997", "1999",
                "2001", "2003", "2005", "2007", "2009", "2011", "2013", "2015", "2017", "2019",
                "2021", "2023"
            ]
        else:
            # İsim sorusu için sadece sanatçılar, gruplar, şarkılar
            yanlis_secenekler = [
                # Sanatçılar
                "The Beatles", "Queen", "Michael Jackson", "Elvis Presley",
                "Madonna", "Beyoncé", "Adele", "Ed Sheeran", "Taylor Swift",
                "Drake", "Post Malone", "Billie Eilish", "Dua Lipa", "Olivia Rodrigo",
                "Prince", "Eminem", "Shakira", "Rihanna", "Lady Gaga", "Katy Perry",
                "Bruno Mars", "Justin Timberlake", "Justin Bieber", "Ariana Grande",
                "Selena Gomez", "Miley Cyrus", "Demi Lovato", "Nicki Minaj", "Cardi B",
                
                # Gruplar
                "Nirvana", "Guns N' Roses", "Metallica", "Imagine Dragons", "Coldplay",
                "U2", "Pink Floyd", "Led Zeppelin", "The Rolling Stones", "The Who",
                "AC/DC", "Black Sabbath", "Iron Maiden", "Judas Priest", "Megadeth",
                "Linkin Park", "Green Day", "Blink-182", "Sum 41", "Simple Plan",
                
                # Şarkılar
                "Thriller", "Bohemian Rhapsody", "Rolling in the Deep", "Shape of You",
                "Someone Like You", "bad guy", "Smells Like Teen Spirit", "Hey Jude",
                "November Rain", "Nothing Else Matters", "Purple Rain", "Single Ladies",
                "Lose Yourself", "Hips Don't Lie", "Believer", "Yellow", "Fix You",
                "Viva La Vida", "Paradise", "Sky Full of Stars"
            ]
    
    elif kategori == "unlu":
        if cevap_tipi == "yil":
            # Yıl sorusu için sadece yıllar
            yanlis_secenekler = [
                "1643", "1687", "1704", "1727", "1736", "1756", "1769", "1789", "1791", "1804",
                "1809", "1819", "1859", "1867", "1879", "1882", "1895", "1905", "1915", "1921",
                "1933", "1942", "1955", "1965", "1971", "1981", "1991", "2001", "2011", "2021"
            ]
        else:
            # İsim sorusu için sadece ünlüler
            yanlis_secenekler = [
                # Bilim İnsanları
                "Einstein", "Newton", "Tesla", "Edison", "Darwin", "Galileo",
                "Hawking", "Curie", "Planck", "Bohr", "Feynman", "Turing",
                "Archimedes", "Pythagoras", "Euclid", "Copernicus", "Kepler",
                "Lavoisier", "Mendel", "Pasteur", "Fleming", "Watson", "Crick",
                "Salk", "Sabin", "Jenner", "Koch", "Koch", "Koch", "Koch",
                
                # Sanatçılar
                "Da Vinci", "Mozart", "Beethoven", "Shakespeare", "Picasso",
                "Van Gogh", "Monet", "Rembrandt", "Michelangelo", "Raphael",
                "Donatello", "Botticelli", "Caravaggio", "Vermeer", "Goya",
                "Bach", "Handel", "Haydn", "Schubert", "Chopin", "Liszt",
                "Wagner", "Verdi", "Puccini", "Tchaikovsky", "Stravinsky",
                
                # Yazarlar
                "Dostoyevski", "Tolstoy", "Hugo", "Balzac", "Flaubert", "Zola",
                "Dickens", "Austen", "Brontë", "Hardy", "Wilde", "Shaw",
                "Joyce", "Woolf", "Orwell", "Huxley", "Hemingway", "Fitzgerald",
                "Steinbeck", "Faulkner", "Nabokov", "Borges", "Marquez", "Coelho",
                
                # Teknoloji Liderleri
                "Jobs", "Gates", "Zuckerberg", "Musk", "Bezos", "Page", "Brin",
                "Dorsey", "Koum", "Kalanick", "Thiel", "Andreessen", "Conway",
                "Khosla", "Doerr", "Horowitz", "Wilson", "Graham", "Altman",
                
                # Politikacılar
                "Churchill", "Roosevelt", "Kennedy", "Reagan", "Clinton", "Bush",
                "Obama", "Trump", "Biden", "Thatcher", "Blair", "Cameron",
                "May", "Johnson", "Truss", "Sunak", "Macron", "Merkel",
                "Putin", "Xi", "Modi", "Erdoğan", "Netanyahu", "Bin Salman"
            ]
    
    elif kategori == "edebiyat":
        if cevap_tipi == "yil":
            # Yıl sorusu için sadece yıllar
            yanlis_secenekler = [
                "1605", "1667", "1869", "1886", "1943", "1945", "1949", "1951", "1954", "1960",
                "1967", "1970", "1981", "1984", "1987", "1991", "1995", "1997", "2000", "2003"
            ]
        else:
            # İsim sorusu için sadece kitaplar, yazarlar, türler
            yanlis_secenekler = [
                # Türk Edebiyatı
                "Çalıkuşu", "Kürk Mantolu Madonna", "Tutunamayanlar", "Şah ve Uşak",
                "Simyacı", "Şeker Portakalı", "Küçük Prens", "Fareler ve İnsanlar",
                "Yabancı", "Dönüşüm", "Milena'ya Mektuplar", "Gurur ve Önyargı",
                "Jane Eyre", "Uğultulu Tepeler", "Küçük Kadınlar", "Tom Sawyer",
                "Huckleberry Finn", "Moby Dick", "Beyaz Diş", "Vahşetin Çağrısı",
                
                # Dünya Klasikleri
                "Don Kişot", "Suç ve Ceza", "Savaş ve Barış", "1984",
                "Hayvan Çiftliği", "Fareler ve İnsanlar", "Gazap Üzümleri",
                "Büyük Umutlar", "Oliver Twist", "David Copperfield",
                "Gurur ve Önyargı", "Emma", "Sense and Sensibility",
                "Uğultulu Tepeler", "Jane Eyre", "Küçük Kadınlar",
                "Tom Sawyer", "Huckleberry Finn", "Moby Dick",
                "Beyaz Diş", "Vahşetin Çağrısı", "Call of the Wild",
                
                # Modern Edebiyat
                "Yüzüklerin Efendisi", "Hobbit", "Harry Potter", "Narnia Günlükleri",
                "Game of Thrones", "Dune", "Neuromancer", "Snow Crash",
                "The Handmaid's Tale", "The Testaments", "The Power",
                "Normal People", "Conversations with Friends", "Beautiful World",
                "Klara and the Sun", "The Midnight Library", "The Seven Husbands",
                "Where the Crawdads Sing", "Educated", "Becoming",
                
                # Yazarlar
                "Cervantes", "Dostoyevski", "Tolstoy", "Orwell", "Steinbeck",
                "Dickens", "Austen", "Brontë", "Hardy", "Wilde", "Shaw",
                "Joyce", "Woolf", "Huxley", "Hemingway", "Fitzgerald",
                "Faulkner", "Nabokov", "Borges", "Marquez", "Coelho",
                "Pamuk", "Kemal", "Kemal", "Kemal", "Kemal", "Kemal",
                "Tolkien", "Rowling", "Lewis", "Martin", "Herbert",
                "Gibson", "Stephenson", "Atwood", "Rooney", "Ishiguro",
                "Haddon", "Haig", "Reid", "Owens", "Westover", "Obama"
            ]
    
    else:
        # Genel yanlış seçenekler
        yanlis_secenekler = [
            "Bilmiyorum", "Hiçbiri", "Diğer", "Yok", "Belirsiz",
            "Araştır", "Sorgula", "Düşün", "Tahmin", "Seç"
        ]
    
    # Dogru cevabı listeden çıkar
    yanlis_secenekler = [s for s in yanlis_secenekler if s.lower() != dogru_cevap.lower()]
    
    # 4 tane yanlış seçenek seç
    secilen_yanlis = random.sample(yanlis_secenekler, min(4, len(yanlis_secenekler)))
    
    # Dogru cevabı ekle ve karıştır
    tum_secenekler = secilen_yanlis + [dogru_cevap]
    random.shuffle(tum_secenekler)
    
    return tum_secenekler

def yalan_handlers(app):
    # Eski handlers'ı kaldırıp quiz handlerlarını ekle
    app.add_handler(CommandHandler("yalan", yalan_quiz_baslat_komut))
    app.add_handler(CallbackQueryHandler(yalan_quiz_kategori_sec_callback, pattern="^quiz_kat_"))
    app.add_handler(CallbackQueryHandler(yalan_quiz_cevap_callback, pattern="^quiz_cevap_"))
    
    # Yeni anket handler'ları
    app.add_handler(MessageHandler(filters.POLL_ANSWER, poll_answer_handler))
    app.add_handler(MessageHandler(filters.POLL, poll_handler))
    
    # Soruyu geç butonları kaldırıldı - sadece anket var

async def yalan_quiz_baslat_komut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id in yalan_quiz_oyunlari and getattr(yalan_quiz_oyunlari[chat_id], 'aktif', False):
        await update.message.reply_text("❌ Zaten aktif bir quiz oyunu var!")
        return
    yalan_quiz_oyunlari[chat_id] = QuizOyun(chat_id, user_id)
    keyboard = [
        [InlineKeyboardButton("🎬 Film", callback_data="quiz_kat_film"), InlineKeyboardButton("🎵 Müzik", callback_data="quiz_kat_muzik")],
        [InlineKeyboardButton("🗺️ Coğrafya", callback_data="quiz_kat_cografya"), InlineKeyboardButton("🌟 Ünlü", callback_data="quiz_kat_unlu")],
        [InlineKeyboardButton("🏆 Spor", callback_data="quiz_kat_spor"), InlineKeyboardButton("📜 Tarih", callback_data="quiz_kat_tarih")],
        [InlineKeyboardButton("📖 Edebiyat", callback_data="quiz_kat_edebiyat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🧠 <b>QUİZ OYUNU</b>\n\n" 
        "Bir kategori seçerek 20 soruluk oyunu başlat!",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def yalan_quiz_menu_from_game(update: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    query = update
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    # Yeni oyun oluştur
    yalan_quiz_oyunlari[chat_id] = QuizOyun(chat_id, user_id)
    keyboard = [
        [InlineKeyboardButton("🎬 Film", callback_data="quiz_kat_film"), InlineKeyboardButton("🎵 Müzik", callback_data="quiz_kat_muzik")],
        [InlineKeyboardButton("🗺️ Coğrafya", callback_data="quiz_kat_cografya"), InlineKeyboardButton("🌟 Ünlü", callback_data="quiz_kat_unlu")],
        [InlineKeyboardButton("🏆 Spor", callback_data="quiz_kat_spor"), InlineKeyboardButton("📜 Tarih", callback_data="quiz_kat_tarih")],
        [InlineKeyboardButton("📖 Edebiyat", callback_data="quiz_kat_edebiyat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(
            text="🧠 <b>SORU BANKASI</b>\n\nBir kategori seçerek 20 soruluk oyunu başlat!",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception:
        # Eğer düzenleme başarısız olursa yeni mesaj gönder
        await context.bot.send_message(
            chat_id=chat_id,
            text="🧠 <b>SORU BANKASI</b>\n\nBir kategori seçerek 20 soruluk oyunu başlat!",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

async def yalan_quiz_kategori_sec_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Category selection triggers quickly; answer without alert to ensure responsiveness
    try:
        await query.answer()
    except Exception:
        pass
    chat_id = query.message.chat.id
    if chat_id not in yalan_quiz_oyunlari:
        await query.edit_message_text("❌ Aktif oyun yok!")
        return
    oyun = yalan_quiz_oyunlari[chat_id]
    kat = query.data.split("_")[-1]

    # yalan.json'u yükle ve kategoriye göre soru havuzunu hazırla
    with open("kelimeler/yalan.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    kategoriler = data.get("kategoriler", {})
    if kat not in kategoriler:
        await query.edit_message_text("❌ Geçersiz kategori!")
        return
    soru_havuzu = kategoriler.get(kat, [])
    # Havuzu 200 soruya tamamla (şık varyasyonlarla çoğaltma)
    soru_havuzu = _expand_soru_havuzu(soru_havuzu, hedef_sayi=200)

    if not soru_havuzu:
        await query.edit_message_text("❌ Soru bulunamadı!")
        return
    oyun.kategori = kat
    oyun.soru_havuzu = soru_havuzu
    oyun.aktif = True
    oyun.raund = 0

    # Kategori seçim mesajını düzenleyerek oyunu başlat (silinemezse düzenle)
    # Mesajı silmek yerine düzenlemeyi dene; başarısız olursa da yeni soruya geç
    try:
        await query.edit_message_text("⏳ Yükleniyor...", parse_mode="HTML")
        await quiz_yeni_soru(chat_id, context, prev_message_id=query.message.message_id)
    except Exception:
        await quiz_yeni_soru(chat_id, context)

async def soru_bankasi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    # Kullanıcının mevcut oyun puanlarını göster
    top = puan_sistemi.top_puanlar("yalanciyi_tahmin", 10, chat_id)
    if not top:
        await query.edit_message_text("📚 Soru Bankası için puan verisi yok.")
        return
    mesaj = "📚 <b>Soru Bankası Puanları</b>\n\n"
    for i, o in enumerate(top, 1):
        mesaj += f"{i}. <b>{o['user_name']}</b> - {o['puan']} puan\n"
    await query.edit_message_text(mesaj, parse_mode="HTML")

async def quiz_yeni_soru(chat_id: int, context: ContextTypes.DEFAULT_TYPE, prev_message_id: int | None = None):
    if chat_id not in yalan_quiz_oyunlari:
        return
    oyun = yalan_quiz_oyunlari[chat_id]
    if not oyun.aktif or oyun.raund >= oyun.max_raund:
        # Özet mesajı gönder
        if oyun.kullanici_dogru_sayilari:
            sirali = sorted(oyun.kullanici_dogru_sayilari.items(), key=lambda x: x[1]["sayi"], reverse=True)
            mesaj = "🏁 <b>QUIZ BİTTİ</b> 🏁\n\n" + "\n".join(
                [f"{i+1}. <a href='tg://user?id={uid}'>{bilgi['isim']}</a> — {bilgi['sayi']} doğru" for i, (uid, bilgi) in enumerate(sirali)]
            )
        else:
            mesaj = "🏁 <b>QUIZ BİTTİ</b> 🏁\n\nKatılım olmadı."
        await context.bot.send_message(chat_id, mesaj, parse_mode="HTML")
        oyun.aktif = False
        return
    # Önce önceki soru mesajını sil
    try:
        if oyun.current_message_id:
            await context.bot.delete_message(chat_id, oyun.current_message_id)
        # Eski anket mesajını da temizle
        if oyun.anket_mesaj_id:
            try:
                await context.bot.delete_message(chat_id, oyun.anket_mesaj_id)
            except Exception:
                pass
            oyun.anket_mesaj_id = None
    except Exception:
        pass
    if prev_message_id:
        try:
            await context.bot.delete_message(chat_id, prev_message_id)
        except Exception:
            pass
    oyun.raund += 1
    # Tekrarı önle – kullanılmamış bir indeks seç
    max_try = len(oyun.soru_havuzu)
    idx = None
    for _ in range(max_try):
        cand = random.randrange(0, len(oyun.soru_havuzu))
        if cand not in oyun.kullanilan_indeksler:
            idx = cand
            break
    if idx is None:
        # Hepsi kullanıldı, bitir
        oyun.raund = oyun.max_raund
        return await quiz_yeni_soru(chat_id, context)
    oyun.kullanilan_indeksler.add(idx)
    soru = oyun.soru_havuzu[idx]
    oyun.aktif_soru = soru
    
    # Çoktan seçmeli seçenekler oluştur
    cevap = str(soru.get("cevap", "")).strip()
    oyun.aktif_secenekler = _yanlis_secenekler_olustur(cevap, oyun.kategori, soru)
    
    # Cevap verenleri temizle
    oyun.cevap_verenler.clear()
    
    # Anket sistemi - Telegram Poll API kullanarak
    secenek_harfleri = ["A", "B", "C", "D", "E"]
    poll_options = []
    
    # Seçenekleri hazırla
    for i, secenek in enumerate(oyun.aktif_secenekler):
        poll_options.append(f"{secenek_harfleri[i]}) {secenek}")
    
    # Anket gönder (15 saniye süreli)
    try:
        poll_msg = await asyncio.wait_for(
            context.bot.send_poll(
                chat_id,
                f"❓ Soru {oyun.raund}/{oyun.max_raund}\n\n{soru['soru']}",
                poll_options,
                is_anonymous=False,  # Kullanıcı profilleri görünsün
                allows_multiple_answers=False,  # Tek cevap
                open_period=15,  # 15 saniye sonra otomatik kapanır
                explanation=f"⏰ Cevap süresi: {oyun.cevap_suresi} saniye\n🎯 Doğru cevabı seçin!"
            ),
            timeout=30.0  # Timeout süresini artırdım
        )
        oyun.anket_mesaj_id = poll_msg.message_id
        print(f"✅ Anket gönderildi: {chat_id}")
        
        # Anket gönderildikten sonra 15 saniye bekle ve sonuçları işle
        asyncio.create_task(anket_suresi_bekle(chat_id, context, oyun))
        
    except asyncio.TimeoutError:
        print(f"⏰ Anket gönderme timeout: {chat_id}")
        # Fallback: basit mesaj gönder
        try:
            fallback_msg = await context.bot.send_message(
                chat_id,
                f"❓ Soru {oyun.raund}/{oyun.max_raund}\n\n{soru['soru']}\n\n⏰ Anket gönderilemedi, lütfen tekrar deneyin.",
                parse_mode="HTML"
            )
            oyun.anket_mesaj_id = fallback_msg.message_id
        except Exception as e:
            print(f"❌ Fallback mesaj da başarısız: {e}")
            return
    except (TimedOut, NetworkError) as e:
        print(f"⏰ Telegram API timeout/network hatası: {e}")
        # Fallback: basit mesaj gönder
        try:
            fallback_msg = await context.bot.send_message(
                chat_id,
                f"❓ Soru {oyun.raund}/{oyun.max_raund}\n\n{soru['soru']}\n\n⏰ Anket gönderilemedi, lütfen tekrar deneyin.",
                parse_mode="HTML"
            )
            oyun.anket_mesaj_id = fallback_msg.message_id
        except Exception as e2:
            print(f"❌ Fallback mesaj da başarısız: {e2}")
            return
    except Exception as e:
        print(f"❌ Anket gönderme hatası: {e}")
        return
    
    # Soruyu geç butonu kaldırıldı - sadece anket var
    
    # Süreli anket kullanıldığı için timer'a gerek yok
    # Anket 15 saniye sonra otomatik kapanacak

async def quiz_cevap_timer(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """15 saniye sonra cevapları gösterir - artık kullanılmıyor çünkü anket sistemi var"""
    try:
        await asyncio.sleep(15)
    except asyncio.CancelledError:
        print(f"⏰ Timer iptal edildi: {chat_id}")
        return
    except Exception as e:
        print(f"⏰ Timer hatası: {e}")
        return
    
    if chat_id not in yalan_quiz_oyunlari:
        return
    
    oyun = yalan_quiz_oyunlari[chat_id]
    if not oyun.aktif or not oyun.aktif_soru:
        return
    
    # Timer'ı temizle
    oyun.cevap_timer = None
    
    # Anket sonuçlarını işle ve puanları hesapla
    try:
        await _process_poll_results(chat_id, context, oyun)
    except asyncio.TimeoutError:
        print(f"⏰ Poll results timeout: {chat_id}")
    except Exception as e:
        print(f"❌ Poll results hatası: {e}")
        pass

async def quiz_tahmin_kontrol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in yalan_quiz_oyunlari:
        return
    oyun = yalan_quiz_oyunlari[chat_id]
    if not oyun.aktif or not oyun.aktif_soru:
        return
    # Oyunu başlatan veya herkese açık: tahmini her kullanıcıdan kabul et
    # (Ek kısıtlama yok; ancak istersen spam/işbirliği engeli eklenebilir)
    import re
    raw_guess = update.message.text or ""
    raw_answer = str(oyun.aktif_soru.get('cevap',''))
    tahmin = _normalize_guess(raw_guess)
    dogru = _normalize_guess(raw_answer)
    # Kısmi/esnek eşleşme kuralları
    eslesme = False
    # 1) Tam eşleşme
    if tahmin == dogru and tahmin:
        eslesme = True
    # 2) Alt dize (en az 3 karakter) iki yönde
    elif (len(tahmin) >= 3 and (tahmin in dogru or dogru in tahmin)):
        eslesme = True
    else:
        # 3) Token tabanlı örtüşme (sıra bağımsız ad/soyad vb.)
        def tokens(s: str):
            # Orijinal metinden sadeleştirilmiş token çıkar
            import re
            s2 = re.sub(r"[^a-zçğıöşü0-9\s]", " ", (raw_guess if s is raw_guess else raw_answer).lower())
            return [t for t in s2.split() if len(t) >= 2]
        guess_tokens = tokens(raw_guess)
        ans_tokens = tokens(raw_answer)
        ortak = len(set(guess_tokens) & set(ans_tokens))
        if ans_tokens:
            oran = ortak / len(set(ans_tokens))
            if oran >= 0.6:
                eslesme = True
    if not eslesme:
        # Yakınlık bilgilendirmesi
        try:
            await context.bot.send_message(chat_id, "ℹ️ Çok yakındı ama değil. Biraz daha dene!")
        except Exception:
            pass
        return
    if tahmin:
        user = update.effective_user
        # Puan ver
        try:
            chat = await context.bot.get_chat(chat_id)
            chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Bilinmeyen Grup"
            chat_username = getattr(chat, 'username', None)
        except Exception:
            chat_name = "Bilinmeyen Grup"
            chat_username = None
        puan_sistemi.puan_ekle(user.id, user.first_name, "soru_bankasi", 3, chat_id, chat_name, chat_username)
        # Doğru bildirimi
        try:
            await context.bot.send_message(
                chat_id,
                f"✅ Doğru! <a href='tg://user?id={user.id}'>{user.first_name}</a> +3 puan aldı.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        # Sayaç
        kayit = oyun.kullanici_dogru_sayilari.get(user.id, {"isim": user.first_name, "sayi": 0})
        kayit["sayi"] += 1
        oyun.kullanici_dogru_sayilari[user.id] = kayit
        # Eski soruyu sil ve yeni soruya geç
        try:
            if oyun.current_message_id:
                await context.bot.delete_message(chat_id, oyun.current_message_id)
        except Exception:
            pass
        oyun.aktif_soru = None
        await quiz_yeni_soru(chat_id, context)

def _expand_soru_havuzu(sorular: list, hedef_sayi: int = 200) -> list:
    """Var olan soruları şık biçimde farklı kalıplarla çoğaltarak hedef sayıya tamamlar."""
    if not sorular:
        return []
    if len(sorular) >= hedef_sayi:
        return sorular
    templates = [
        "{soru}",
        "{soru} ✅",
        "{soru} 🤔",
        "{soru} (doğru cevabı seçiniz)",
        "{soru} — doğru olan hangisi?",
        "{soru} \n\nLütfen en doğru seçeneği işaretleyin.",
        "❓ {soru}",
        "📌 {soru}",
        "🧠 {soru}",
        "⭐ {soru}",
    ]
    genisletilmis = list(sorular)
    idx = 0
    while len(genisletilmis) < hedef_sayi:
        base = sorular[idx % len(sorular)]
        tpl = templates[idx % len(templates)]
        yeni_soru = {
            "soru": tpl.format(soru=base["soru"]),
            "cevap": base["cevap"]
        }
        genisletilmis.append(yeni_soru)
        idx += 1
    return genisletilmis

async def yalan_quiz_cevap_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anket sonuçlarını işler - artık kullanılmıyor çünkü anket sistemi var"""
    query = update.callback_query
    await query.answer("ℹ️ Bu buton artık kullanılmıyor. Anket üzerinden cevap verin!", show_alert=True)

async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anket cevaplarını takip eder"""
    if not update.poll_answer:
        return
    
    poll_answer = update.poll_answer
    chat_id = poll_answer.voter_chat.id if poll_answer.voter_chat else None
    user_id = poll_answer.user.id
    user_name = poll_answer.user.first_name or poll_answer.user.username or "Bilinmeyen"
    
    if not chat_id or chat_id not in yalan_quiz_oyunlari:
        return
    
    oyun = yalan_quiz_oyunlari[chat_id]
    if not oyun.aktif or not oyun.aktif_soru:
        return
    
    # Cevap verenleri kaydet
    if user_id not in oyun.cevap_verenler:
        oyun.cevap_verenler[user_id] = {
            "isim": user_name,
            "secim": poll_answer.option_ids[0] if poll_answer.option_ids else None,
            "dogru": False
        }
    else:
        # Kullanıcı zaten cevap vermişse güncelle
        oyun.cevap_verenler[user_id]["secim"] = poll_answer.option_ids[0] if poll_answer.option_ids else None
        oyun.cevap_verenler[user_id]["dogru"] = False
    
    # Doğru cevabı kontrol et
    dogru_cevap = oyun.aktif_soru["cevap"]
    secenek_index = poll_answer.option_ids[0] if poll_answer.option_ids else None
    
    if secenek_index is not None and secenek_index < len(oyun.aktif_secenekler):
        secilen_secenek = oyun.aktif_secenekler[secenek_index]
        if secilen_secenek == dogru_cevap:
            oyun.cevap_verenler[user_id]["dogru"] = True
            print(f"✅ Doğru cevap: {user_name} ({user_id}) - {dogru_cevap}")
        else:
            print(f"❌ Yanlış cevap: {user_name} ({user_id}) - {secilen_secenek} (Doğru: {dogru_cevap})")
    
    print(f"📊 Anket cevabı kaydedildi: {user_name} ({user_id}) - Seçenek: {secenek_index}, Doğru: {oyun.cevap_verenler[user_id]['dogru']}")

async def poll_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anket kapandığında çalışır"""
    if not update.poll:
        return
    
    poll = update.poll
    chat_id = None
    
    # Chat ID'yi bul
    for cid, oyun in yalan_quiz_oyunlari.items():
        if oyun.aktif and oyun.anket_mesaj_id:
            chat_id = cid
            break
    
    if not chat_id:
        return
    
    oyun = yalan_quiz_oyunlari[chat_id]
    if not oyun.aktif or not oyun.aktif_soru:
        return
    
    print(f"⏰ Anket kapandı: {chat_id}")
    
    # Anket sonuçlarını işle ve puanları hesapla
    try:
        await _process_poll_results(chat_id, context, oyun)
    except Exception as e:
        print(f"❌ Poll results hatası: {e}")
        # Hata olursa manuel olarak yeni soruya geç
        try:
            await asyncio.sleep(3)
            await asyncio.wait_for(
                quiz_yeni_soru(chat_id, context),
                timeout=25.0
            )
        except Exception as e2:
            print(f"❌ Manuel yeni soru hatası: {e2}")

async def yalan_quiz_pass_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    if chat_id not in yalan_quiz_oyunlari:
        return
    oyun = yalan_quiz_oyunlari[chat_id]
    user = query.from_user
    # Cooldown kontrolü (15 sn)
    simdi = datetime.now()
    son = oyun.kisi_cooldown.get(user.id)
    if son and (simdi - son).total_seconds() < 15:
        kalan = int(15 - (simdi - son).total_seconds())
        try:
            await query.answer(f"⏳ Lütfen {kalan} saniye sonra tekrar deneyin.", show_alert=True)
        except Exception:
            pass
        return
    oyun.kisi_cooldown[user.id] = simdi
        # Timer'ı durdur
    if oyun.cevap_timer:
        oyun.cevap_timer.cancel()
        oyun.cevap_timer = None
    
    # Herkese doğru cevabı duyur
    if oyun.aktif_soru:
        dogru = oyun.aktif_soru.get("cevap", "")
        try:
            await context.bot.send_message(
                chat_id,
                (
                    f"😔 <a href='tg://user?id={user.id}'>{user.first_name}</a> bilemedi.\n"
                    f"✅ Doğru cevap: <b>{dogru}</b>"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
    # Eski soruyu sil ve yeni soruya geç
    try:
        if oyun.current_message_id:
            await context.bot.delete_message(chat_id, oyun.current_message_id)
        # Eski anket mesajını da temizle
        if oyun.anket_mesaj_id:
            try:
                await context.bot.delete_message(chat_id, oyun.anket_mesaj_id)
            except Exception:
                pass
            oyun.anket_mesaj_id = None
    except Exception:
        pass
    oyun.aktif_soru = None
    oyun.aktif_secenekler = None
    await quiz_yeni_soru(chat_id, context)

async def yalan_quiz_change_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Alert göstermeye gerek yok; grup mesajı ile bilgilendir
    chat_id = query.message.chat.id
    if chat_id not in yalan_quiz_oyunlari:
        return
    oyun = yalan_quiz_oyunlari[chat_id]
    user = query.from_user
    # Cooldown kontrolü (15 sn)
    simdi = datetime.now()
    son = oyun.kisi_cooldown.get(user.id)
    if son and (simdi - son).total_seconds() < 15:
        kalan = int(15 - (simdi - son).total_seconds())
        try:
            await query.answer(f"⏳ Lütfen {kalan} saniye sonra tekrar deneyin.", show_alert=True)
        except Exception:
            pass
        return
    oyun.kisi_cooldown[user.id] = simdi
    
    # Timer'ı durdur
    if oyun.cevap_timer:
        oyun.cevap_timer.cancel()
        oyun.cevap_timer = None
    
    # Doğru cevabı etiketiyle birlikte gruba bildir (puan yok)
    if oyun.aktif_soru:
        dogru = oyun.aktif_soru.get("cevap", "")
        try:
            await context.bot.send_message(
                chat_id,
                (
                    f"🔄 <a href='tg://user?id={user.id}'>{user.first_name}</a> soruyu geçti.\n"
                    f"✅ Doğru cevap: <b>{dogru}</b>"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
    # Eski soruyu sil ve yeni soruya geç
    try:
        if oyun.current_message_id:
            await context.bot.delete_message(chat_id, oyun.current_message_id)
        # Eski anket mesajını da temizle
        if oyun.anket_mesaj_id:
            try:
                await context.bot.delete_message(chat_id, oyun.anket_mesaj_id)
            except Exception:
                pass
            oyun.anket_mesaj_id = None
    except Exception:
        pass
    oyun.aktif_soru = None
    oyun.aktif_secenekler = None
    await quiz_yeni_soru(chat_id, context)

def yalan_quiz_durdur(chat_id: int) -> bool:
    if chat_id in yalan_quiz_oyunlari and getattr(yalan_quiz_oyunlari[chat_id], 'aktif', False):
        yalan_quiz_oyunlari[chat_id].aktif = False
        return True
    return False


class YalanOyunu:
    def __init__(self, chat_id, baslatan_id):
        self.chat_id = chat_id
        self.baslatan_id = baslatan_id
        self.oyuncular = {}  # {user_id: {"isim": str, "rol": str, "kelime": str, "hazir": bool}}
        self.oyun_durumu = "bekleme"  # bekleme, hazirlik, oyun, oylama, bitti
        self.kelime_cifti = None
        self.yalancilar = []  # Yalancı ID'leri listesi
        self.oyuncu_oylamalari = {}  # {user_id: oy_verilen_id}
        self.oyun_baslama_zamani = None
        self.oyun_suresi = 120  # 2 dakika oyun süresi
        self.oyun_thread = None
        self.otomatik_baslatma_task = None
        self.hatirlatma_task = None
        self.mesaj_id = None  # Ana mesaj ID'si
        self.min_oyuncu = 4  # Minimum oyuncu sayısı
        self.max_oyuncu = 20  # Maksimum oyuncu sayısı
        self.baslatma_suresi = 300  # 5 dakika otomatik başlatma
        self.hatirlatma_suresi = 60  # 1 dakika hatırlatma aralığı
        self.oyun_baslatma_zamani = datetime.now()  # Oyun başlatma zamanı
        
    def oyuncu_ekle(self, user_id, isim):
        if user_id not in self.oyuncular:
            if len(self.oyuncular) >= self.max_oyuncu:
                return False, "Maksimum oyuncu sayısına ulaşıldı!"
            self.oyuncular[user_id] = {"isim": isim, "rol": "", "kelime": "", "hazir": True}  # Otomatik hazır
            return True, "Oyuna katıldınız!"
        return False, "Zaten oyuna katıldınız!"
    
    def oyuncu_hazir_yap(self, user_id):
        if user_id in self.oyuncular:
            self.oyuncular[user_id]["hazir"] = True
            return True
        return False
    
    def hazir_oyuncu_sayisi(self):
        return sum(1 for oyuncu in self.oyuncular.values() if oyuncu["hazir"])
    
    def oyunu_baslat(self):
        hazir_oyuncu_sayisi = self.hazir_oyuncu_sayisi()
        if hazir_oyuncu_sayisi < self.min_oyuncu:
            return False, f"En az {self.min_oyuncu} hazır oyuncu gerekli! (Hazır: {hazir_oyuncu_sayisi})"
        
        # Kelime çiftini seç
        with open("kelimeler/yalan.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.kelime_cifti = random.choice(data["kelime_ciftleri"])
        
        # Yalancı sayısını belirle (oyuncu sayısına göre)
        toplam_oyuncu = hazir_oyuncu_sayisi
        if toplam_oyuncu <= 6:
            yalancı_sayisi = 1
        elif toplam_oyuncu <= 10:
            yalancı_sayisi = 2
        else:
            yalancı_sayisi = 3
        
        # Hazır oyuncuları al
        hazir_oyuncular = [user_id for user_id, oyuncu in self.oyuncular.items() if oyuncu["hazir"]]
        
        # Yalancıları seç
        self.yalancilar = random.sample(hazir_oyuncular, yalancı_sayisi)
        
        # Rolleri ve kelimeleri dağıt
        for user_id in hazir_oyuncular:
            if user_id in self.yalancilar:
                self.oyuncular[user_id]["rol"] = "yalancı"
                self.oyuncular[user_id]["kelime"] = self.kelime_cifti["kelime2"]
            else:
                self.oyuncular[user_id]["rol"] = "dürüst"
                self.oyuncular[user_id]["kelime"] = self.kelime_cifti["kelime1"]
        
        self.oyun_durumu = "oyun"
        self.oyun_baslama_zamani = datetime.now()
        
        # Hatırlatma task'ını iptal et
        if self.hatirlatma_task and not self.hatirlatma_task.done():
            self.hatirlatma_task.cancel()
        
        # Oyun süresi thread'ini başlat
        self.oyun_thread = threading.Thread(target=self.oyun_suresi_takip)
        self.oyun_thread.daemon = True
        self.oyun_thread.start()
        
        return True, "Oyun başladı!"
    
    def oyun_suresi_takip(self):
        time.sleep(self.oyun_suresi)
        if self.oyun_durumu == "oyun":
            self.oyun_durumu = "oylama"
            # Burada oylama başlatılacak (async fonksiyon çağrılamaz)
    
    def oy_ver(self, oy_veren_id, oy_verilen_id):
        if self.oyun_durumu != "oylama":
            return False, "Şu anda oylama yapılmıyor!"
        
        hazir_oyuncular = [user_id for user_id, oyuncu in self.oyuncular.items() if oyuncu["hazir"]]
        if oy_veren_id not in hazir_oyuncular:
            return False, "Oyuncu değilsiniz!"
        
        if oy_verilen_id not in hazir_oyuncular:
            return False, "Geçersiz oy!"
        
        self.oyuncu_oylamalari[oy_veren_id] = oy_verilen_id
        return True, "Oyunuz kaydedildi!"
    
    def oylama_sonucu(self):
        hazir_oyuncular = [user_id for user_id, oyuncu in self.oyuncular.items() if oyuncu["hazir"]]
        if len(self.oyuncu_oylamalari) < len(hazir_oyuncular):
            return None, "Tüm oyuncular oy vermedi!"
        
        # En çok oy alan kişiyi bul
        oy_sayilari = {}
        for oy_verilen_id in self.oyuncu_oylamalari.values():
            oy_sayilari[oy_verilen_id] = oy_sayilari.get(oy_verilen_id, 0) + 1
        
        en_cok_oy_alan = max(oy_sayilari, key=oy_sayilari.get)
        
        # Kazananı belirle
        if en_cok_oy_alan in self.yalancilar:
            return "dürüstler", "Dürüstler kazandı! Yalancı yakalandı!"
        else:
            return "yalancı", "Yalancılar kazandı! Dürüstler yanıldı!"
    
    def oyunu_bitir(self):
        self.oyun_durumu = "bitti"
        if self.oyun_thread and self.oyun_thread.is_alive():
            self.oyun_thread.join(timeout=1)
        if self.otomatik_baslatma_task and not self.otomatik_baslatma_task.done():
            self.otomatik_baslatma_task.cancel()
        if self.hatirlatma_task and not self.hatirlatma_task.done():
            self.hatirlatma_task.cancel()

def yalan_oyunu_durdur(chat_id):
    """Belirtilen chat'teki yalan oyununu durdurur"""
    if chat_id in yalan_oyunlari:
        oyun = yalan_oyunlari[chat_id]
        oyun.oyunu_bitir()
        del yalan_oyunlari[chat_id]
        return True
    return False

async def yalan_uzat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yalan oyununun başlatma süresini uzatır"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in yalan_oyunlari:
        await update.message.reply_text("❌ Aktif yalan oyunu bulunamadı!")
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    if oyun.oyun_durumu != "bekleme":
        await update.message.reply_text("❌ Oyun zaten başladı!")
        return
    
    # Süreyi uzat (2 dakika daha bekle)
    await update.message.reply_text("⏰ Oyun başlatma süresi 2 dakika uzatıldı!")
    
    # Mevcut task'ı iptal et
    if oyun.otomatik_baslatma_task and not oyun.otomatik_baslatma_task.done():
        oyun.otomatik_baslatma_task.cancel()
    
    # Yeni task başlat (2 dakika daha)
    oyun.otomatik_baslatma_task = asyncio.create_task(otomatik_baslatma_kontrol(context, chat_id))

async def otomatik_baslatma_kontrol(context, chat_id):
    """5 dakika sonra otomatik oyun başlatma kontrolü"""
    try:
        await asyncio.sleep(300)  # 5 dakika bekle
        
        if chat_id not in yalan_oyunlari:
            return
        
        oyun = yalan_oyunlari[chat_id]
        if oyun.oyun_durumu != "bekleme":
            return
        
        # Yeterli oyuncu var mı kontrol et
        if len(oyun.oyuncular) >= oyun.min_oyuncu:
            # Eğer yeterli oyuncu varsa ama hazır değilse, onları hazır yap
            hazir_oyuncu_sayisi = oyun.hazir_oyuncu_sayisi()
            if hazir_oyuncu_sayisi < oyun.min_oyuncu:
                # Tüm oyuncuları hazır yap
                for user_id in oyun.oyuncular:
                    oyun.oyuncular[user_id]["hazir"] = True
                await context.bot.send_message(
                    chat_id, 
                    f"✅ Yeterli oyuncu var! ({len(oyun.oyuncular)} kişi)\n"
                    f"Oyun başlatılıyor..."
                )
            
            # Oyunu başlat
            basarili, mesaj = oyun.oyunu_baslat()
            if basarili:
                await oyun_baslatildi_mesaji_gonder(context, chat_id)
            else:
                await context.bot.send_message(chat_id, f"❌ {mesaj}")
        else:
            await context.bot.send_message(
                chat_id, 
                f"❌ Üzgünüm, yeterli oyuncu toplayamadık!\n"
                f"Gerekli: {oyun.min_oyuncu}, Katılan: {len(oyun.oyuncular)}\n"
                f"Oyun iptal edildi."
            )
            # Oyunu temizle
            oyun.oyunu_bitir()
            del yalan_oyunlari[chat_id]
    except asyncio.CancelledError:
        # Task iptal edildi, temizle
        if chat_id in yalan_oyunlari:
            yalan_oyunlari[chat_id].otomatik_baslatma_task = None
        print(f"✅ Yalan otomatik başlatma task iptal edildi: {chat_id}")
    except Exception as e:
        print(f"Otomatik başlatma hatası: {e}")
        # Hata durumunda da temizle
        if chat_id in yalan_oyunlari:
            yalan_oyunlari[chat_id].otomatik_baslatma_task = None

async def oyun_baslatildi_mesaji_gonder(context, chat_id):
    """Oyun başladığında tüm mesajları gönder"""
    oyun = yalan_oyunlari[chat_id]
    
    # Gruba bilgi mesajı
    hazir_oyuncular = [user_id for user_id, oyuncu in oyun.oyuncular.items() if oyuncu["hazir"]]
    toplam_oyuncu = len(hazir_oyuncular)
    yasayan_oyuncu = toplam_oyuncu  # Başlangıçta hepsi yaşıyor
    
    oyuncu_listesi = "\n".join([f"• <a href='tg://user?id={uid}'>{oyun.oyuncular[uid]['isim']}</a> ❤️ Yaşıyor" for uid in hazir_oyuncular])
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎭 <b>OYUN BAŞLADI!</b> 🎭\n\n"
             f"👥 <b>Oyuncular ({yasayan_oyuncu}/{toplam_oyuncu}):</b>\n{oyuncu_listesi}\n\n"
             f"💬 <b>Diğer kullanıcılar ile konuşun!</b>\n"
             f"⚠️ <b>Unutmayın:</b> Kelimeyi direkt söylemek yasak!\n"
             f"🎯 <b>Tanımlayarak farklı olan kişiyi tahmin edin!</b>\n\n"
             f"⏰ <b>2 dakika sonra oylama başlayacak!</b>",
        parse_mode="HTML"
    )
    
    # Her oyuncuya özelden rolünü gönder
    for user_id in hazir_oyuncular:
        oyuncu = oyun.oyuncular[user_id]
        try:
            if oyuncu["rol"] == "yalancı":
                # Diğer yalancıları da göster
                diger_yalancilar = [oyun.oyuncular[uid]["isim"] for uid in oyun.yalancilar if uid != user_id]
                diger_yalancilar_mesaji = ""
                if diger_yalancilar:
                    diger_yalancilar_mesaji = f"\n👥 Diğer yalancılar: {', '.join(diger_yalancilar)}"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎭 YALAN OYUNU BAŞLADI! 🎭\n\n"
                         f"🎭 Rolünüz: YALANCI\n"
                         f"📝 Kelimeniz: {oyuncu['kelime']}\n"
                         f"💡 Diğer oyuncularla konuşun ve dürüstleri kandırmaya çalışın!"
                         f"{diger_yalancilar_mesaji}"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎭 YALAN OYUNU BAŞLADI! 🎭\n\n"
                         f"✅ Rolünüz: DÜRÜST\n"
                         f"📝 Kelimeniz: {oyuncu['kelime']}\n"
                         f"💡 Diğer oyuncularla konuşun ve yalancıları bulmaya çalışın!"
                )
        except:
            pass  # Kullanıcı botu engellemiş olabilir
    
    # 2 dakika sonra oylama başlat
    await asyncio.sleep(120)
    await oylama_baslat(context, chat_id)

async def yalan_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if chat_id in yalan_oyunlari:
        await update.message.reply_text("Zaten aktif bir yalan oyunu var!")
        return
    
    yalan_oyunlari[chat_id] = YalanOyunu(chat_id, user_id)
    
    keyboard = [
        [InlineKeyboardButton("Oyuna Katıl", callback_data="yalan_katil_ozel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mesaj = await update.message.reply_text(
        f"🎭 <b>YALAN OYUNU BAŞLATILDI!</b>\n\n"
        f"👤 <b>Başlatan:</b> {user_name}\n"
        f"⏰ <b>Süre:</b> 5 dakika\n"
        f"👥 <b>Oyuncular:</b> 0 kişi\n\n"
        f"🎯 Oyuna katılmak için butona basın!",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    # Mesaj ID'sini kaydet
    yalan_oyunlari[chat_id].mesaj_id = mesaj.message_id
    
    # Otomatik başlatma task'ını başlat
    yalan_oyunlari[chat_id].otomatik_baslatma_task = asyncio.create_task(otomatik_baslatma_kontrol(context, chat_id))
    
    # Hatırlatma mesajı task'ını başlat
    yalan_oyunlari[chat_id].hatirlatma_task = asyncio.create_task(hatirlatma_mesaji_gonder_async(context, chat_id))

async def yalanciyi_tahmin_et_baslat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Game menüsünden çağrılan yalan oyunu başlatma fonksiyonu"""
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
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
    
    if chat_id in yalan_oyunlari:
        await query.edit_message_text("Zaten aktif bir yalan oyunu var!")
        return
    
    yalan_oyunlari[chat_id] = YalanOyunu(chat_id, user_id)
    
    # Oyun nesnesini al
    oyun = yalan_oyunlari[chat_id]
    
    keyboard = [
        [InlineKeyboardButton("Oyuna Katıl", callback_data="yalan_katil_ozel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Yeni mesaj olarak gönder
    mesaj = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"🎭 <b>YALAN OYUNU BAŞLATILDI!</b>\n\n"
             f"👤 <b>Başlatan:</b> <a href='tg://user?id={user_id}'>{user_name}</a>\n"
             f"⏰ <b>Süre:</b> 5 dakika\n"
             f"👥 <b>Oyuncular:</b> 0 kişi\n\n"
             f"🎯 Oyuna katılmak için butona basın!",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    # Mesaj ID'sini kaydet
    oyun.mesaj_id = mesaj.message_id
    
    # Otomatik güncelleme task'ını kaldır - gereksiz
    # oyun.guncelleme_task = asyncio.create_task(otomatik_guncelleme_async(context, chat_id))
    
    # Hatırlatma mesajı task'ını başlat
    oyun.hatirlatma_task = asyncio.create_task(hatirlatma_mesaji_gonder_async(context, chat_id))
    
    # Otomatik başlatma task'ını başlat
    oyun.otomatik_baslatma_task = asyncio.create_task(otomatik_baslatma_kontrol(context, chat_id))

async def yalan_katil_ozel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gruptan özele yönlendiren callback"""
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        print(f"Callback answer hatası: {e}")
        pass  # Query çok eski olabilir
    
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    # Aktif oyun kontrolü
    if chat_id not in yalan_oyunlari:
        try:
            await query.answer("❌ Aktif oyun bulunamadı!", show_alert=True)
        except:
            pass
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    # Oyun durumu kontrolü
    if oyun.oyun_durumu != "bekleme":
        try:
            await query.answer("🎮 Aktif oyun devam ediyor! Bir sonraki oyunu bekleyin.", show_alert=True)
        except:
            pass
        return
    
    # Zaten oyuna katılmış mı kontrol et
    if user_id in oyun.oyuncular:
        try:
            await query.answer("✅ Zaten oyuna katıldınız!", show_alert=True)
        except:
            pass
        return
    
    # Özele mesaj gönder
    keyboard = [
        [InlineKeyboardButton("✅ Evet, Katılıyorum", callback_data=f"yalan_katil_ozelden_{chat_id}")],
        [InlineKeyboardButton("❌ Hayır, Katılmıyorum", callback_data=f"yalan_kac_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Grup adını al
        grup_adi = query.message.chat.title or query.message.chat.first_name or "Bilinmeyen Grup"
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎭 <b>YALAN OYUNU</b>\n\n"
                 f"📱 <b>Grup:</b> {grup_adi}\n"
                 f"👥 <b>Oyuncular:</b> {len(oyun.oyuncular)} kişi\n\n"
                 f"❓ Bu gruptaki yalan oyununa katılmak istiyor musun?",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        try:
            await query.answer("✅ Özel mesaj gönderildi! Check your PM!", show_alert=True)
        except:
            pass
    except Exception as e:
        # Gruba uyarı mesajı gönder
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ <a href='tg://user?id={user_id}'>{user_name}</a>, özelden mesaj gönderemedim!\n\n"
                 f"🔧 Lütfen bot'u başlatın: @{context.bot.username}",
            parse_mode="HTML"
        )
        try:
            await query.answer("❌ Özel mesaj gönderilemedi!", show_alert=True)
        except:
            pass

async def yalan_katil_ozelden_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Özelden oyuna katılma callback'i"""
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    # Chat ID'yi callback data'dan al
    try:
        chat_id = int(query.data.split("_")[-1])
    except ValueError:
        await query.edit_message_text("❌ Geçersiz chat ID formatı!")
        return
    
    if chat_id not in yalan_oyunlari:
        await query.edit_message_text("❌ Aktif oyun bulunamadı!")
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    # Oyun durumu kontrolü
    if oyun.oyun_durumu != "bekleme":
        await query.edit_message_text("🎮 Aktif oyun devam ediyor! Bir sonraki oyunu bekleyin.")
        return
    
    basarili, mesaj = oyun.oyuncu_ekle(user_id, user_name)
    if basarili:
        # Gruba katıldı mesajı gönder
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ <a href='tg://user?id={user_id}'>{user_name}</a> oyuna katıldı!",
            parse_mode="HTML"
        )
        
        # Özelde kaçış butonu ekle
        keyboard = [
            [InlineKeyboardButton("🏃‍♂️ Oyundan Kaç", callback_data=f"yalan_kac_{chat_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Başlatan kişinin ismini al
        baslatan_isim = "Bilinmeyen"
        if oyun.baslatan_id in oyun.oyuncular:
            baslatan_isim = oyun.oyuncular[oyun.baslatan_id]['isim']
        
        await query.edit_message_text(
            f"✅ <b>OYUNA KATILDINIZ!</b>\n\n"
            f"🎭 <b>OYUN:</b> Yalancıyı Tahmin Et\n"
            f"👤 <b>Başlatan:</b> {baslatan_isim}\n"
            f"👥 <b>Oyuncular:</b> {len(oyun.oyuncular)} kişi\n\n"
            f"⏰ <b>OYUN BAŞLAMASI BEKLENİYOR...</b>\n\n"
            f"💡 OYUNDAN ÇIKMAK İSTERSEK AŞAĞIDAKI BUTONA BASIN!",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(f"❌ {mesaj}")

async def yalan_kac_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyundan kaçış callback'i"""
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass  # Query çok eski olabilir
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    # Chat ID'yi callback data'dan al
    try:
        chat_id = int(query.data.split("_")[-1])
    except ValueError:
        await query.edit_message_text("❌ Geçersiz chat ID formatı!")
        return
    
    if chat_id not in yalan_oyunlari:
        await query.edit_message_text("❌ Oyun bulunamadı!")
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    if user_id in oyun.oyuncular:
        # Oyuncuyu çıkar
        del oyun.oyuncular[user_id]
        
        # Gruba kaçış mesajı gönder
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ <a href='tg://user?id={user_id}'>{user_name}</a> oyundan çıktı!",
            parse_mode="HTML"
        )
        
        # Grup mesajını güncelle
        await guncelle_grup_mesaji(context, chat_id)
        
        await query.edit_message_text("❌ Oyuna katılmadınız!")
    else:
        await query.answer("Oyunda değilsiniz!", show_alert=True)

async def guncelle_grup_mesaji(context, chat_id):
    """Grup mesajını günceller"""
    if chat_id not in yalan_oyunlari:
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    # Oyuncu listesini oluştur
    if len(oyun.oyuncular) > 0:
        oyuncu_listesi = "\n".join([f"• <a href='tg://user?id={uid}'>{oyuncu['isim']}</a>" for uid, oyuncu in oyun.oyuncular.items()])
    else:
        oyuncu_listesi = "Henüz kimse katılmadı"
        
        keyboard = [
        [InlineKeyboardButton("Oyuna Katıl", callback_data="yalan_katil_ozel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
    # Başlatan kişinin ismini al (oyuncular listesinde olmayabilir)
    baslatan_isim = "Bilinmeyen"
    if oyun.baslatan_id in oyun.oyuncular:
        baslatan_isim = oyun.oyuncular[oyun.baslatan_id]['isim']
    else:
        # Başlatan kişi oyuncular listesinde yoksa, baslatan_id'den isim almaya çalış
        try:
            # Bu kısım daha sonra implement edilebilir
            baslatan_isim = f"ID: {oyun.baslatan_id}"
        except:
            baslatan_isim = "Bilinmeyen"
    
    # Mevcut mesajı güncelle
    if oyun.mesaj_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=oyun.mesaj_id,
                text=f"🎭 <b>YALAN OYUNU BAŞLATILDI!</b>\n\n"
                     f"👤 <b>Başlatan:</b> <a href='tg://user?id={oyun.baslatan_id}'>{baslatan_isim}</a>\n"
                     f"⏰ <b>Süre:</b> 5 dakika\n"
                     f"👥 <b>Oyuncular:</b> {len(oyun.oyuncular)} kişi\n\n"
                     f"<b>Katılanlar:</b>\n{oyuncu_listesi}\n\n"
                     f"🎯 Oyuna katılmak için butona basın!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Mesaj güncelleme hatası: {e}")
            # Eğer mesaj düzenlenemezse yeni mesaj gönder
            mesaj = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎭 <b>YALAN OYUNU BAŞLATILDI!</b>\n\n"
                     f"👤 <b>Başlatan:</b> <a href='tg://user?id={oyun.baslatan_id}'>{baslatan_isim}</a>\n"
                     f"⏰ <b>Süre:</b> 5 dakika\n"
                     f"👥 <b>Oyuncular:</b> {len(oyun.oyuncular)} kişi\n\n"
                     f"<b>Katılanlar:</b>\n{oyuncu_listesi}\n\n"
                     f"🎯 Oyuna katılmak için butona basın!",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            oyun.mesaj_id = mesaj.message_id

async def yalan_hazir_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyuna hazır olma callback'i"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    # Chat ID'yi callback data'dan al
    try:
        chat_id = int(query.data.split("_")[-1])
    except ValueError:
        await query.edit_message_text("❌ Geçersiz chat ID formatı!")
        return
    
    if chat_id not in yalan_oyunlari:
        await query.edit_message_text("❌ Oyun bulunamadı!")
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    if oyun.oyun_durumu != "bekleme":
        await query.edit_message_text("❌ Oyun zaten başladı!")
        return
    
    if user_id not in oyun.oyuncular:
        await query.edit_message_text("❌ Oyuna katılmamışsınız!")
        return
    
    if oyun.oyuncu_hazir_yap(user_id):
        # Gruba hazır oldu mesajı gönder
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ <a href='tg://user?id={user_id}'>{user_name}</a> hazır!",
            parse_mode="HTML"
        )
        
        await query.edit_message_text("✅ Oyuna hazır olduğunuzu bildirdiniz! 🎯")
        
        # Hazır oyuncu sayısını kontrol et
        hazir_oyuncu = oyun.hazir_oyuncu_sayisi()
        if hazir_oyuncu >= oyun.min_oyuncu:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎯 <b>Yeterli oyuncu toplandı!</b>\n"
                     f"Oyunu başlatabilirsiniz!",
                parse_mode="HTML"
            )
    else:
        await query.edit_message_text("❌ Zaten hazır olduğunuzu bildirmişsiniz!")

async def yalan_baslat_oyun_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    
    if chat_id not in yalan_oyunlari:
        await query.edit_message_text("Oyun bulunamadı!")
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    if user_id != oyun.baslatan_id:
        await query.answer("Sadece oyunu başlatan kişi başlatabilir!")
        return
    
    # Tüm oyunculara özelden hazır olma mesajı gönder
    for oyuncu_id, oyuncu in oyun.oyuncular.items():
        if not oyuncu["hazir"]:  # Sadece hazır olmayan oyunculara gönder
            try:
                keyboard = [
                    [InlineKeyboardButton("✅ Oyuna Hazırım", callback_data=f"yalan_hazir_{chat_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=oyuncu_id,
                    text=f"🎭 YALAN OYUNU HAZIRLIK 🎭\n\n"
                         f"Merhaba {oyuncu['isim']}!\n\n"
                         f"Yalan oyunu başlatılmak üzere.\n"
                         f"Oyuna hazır mısınız?\n\n"
                         f"⏰ 4 dakika içinde yeterli hazır oyuncu toplanmazsa oyun iptal edilecek.",
                    reply_markup=reply_markup
                )
            except:
                pass  # Kullanıcı botu engellemiş olabilir
    
    # Gruba bilgi mesajı
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎭 OYUN HAZIRLIK AŞAMASI 🎭\n\n"
             f"Tüm oyunculara özelden hazır olma mesajı gönderildi.\n"
             f"⏰ 4 dakika içinde en az {oyun.min_oyuncu} hazır oyuncu toplanması gerekiyor.\n\n"
             f"👥 Mevcut oyuncular: {len(oyun.oyuncular)}\n"
             f"✅ Hazır oyuncular: {oyun.hazir_oyuncu_sayisi()}"
    )
    
    # Otomatik başlatma thread'ini başlat
    oyun.otomatik_baslatma_thread = threading.Thread(target=lambda: asyncio.run(otomatik_baslatma_kontrol(context, chat_id)))
    oyun.otomatik_baslatma_thread.daemon = True
    oyun.otomatik_baslatma_thread.start()

async def oylama_baslat(context: ContextTypes.DEFAULT_TYPE, chat_id):
    if chat_id not in yalan_oyunlari:
        return
    
    oyun = yalan_oyunlari[chat_id]
    oyun.oyun_durumu = "oylama"
    
    # Gruba oylama başladı mesajı
    await context.bot.send_message(
        chat_id=chat_id,
        text="🗳️ OYLAMA BAŞLADI! 🗳️\n\nLinçlemek istediğiniz kişiyi seçin!"
    )
    
    # Hazır oyunculara özelden oylama butonları gönder
    hazir_oyuncular = [user_id for user_id, oyuncu in oyun.oyuncular.items() if oyuncu["hazir"]]
    
    for user_id in hazir_oyuncular:
        try:
            # Diğer oyuncular için butonlar oluştur (sadece yaşayan oyuncular)
            keyboard = []
            for oyuncu_id in hazir_oyuncular:
                if oyuncu_id != user_id:  # Kendine oy veremez
                    oyuncu = oyun.oyuncular[oyuncu_id]
                    # Sadece yaşayan oyuncuları göster (ölü oyuncular yok)
                    keyboard.append([InlineKeyboardButton(
                        f"Linçle: {oyuncu['isim']}", 
                        callback_data=f"yalan_oy_ver_{chat_id}_{oyuncu_id}"
                    )])
            
            if keyboard:  # Eğer linçlenebilir oyuncu varsa
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🗳️ OYLAMA BAŞLADI! 🗳️\n\nLinçlemek istediğiniz kişiyi seçin:",
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🗳️ OYLAMA BAŞLADI! 🗳️\n\nLinçlenebilir oyuncu kalmadı!"
                )
        except Exception as e:
            print(f"Oylama mesajı gönderme hatası (user_id: {user_id}): {e}")
            pass  # Kullanıcı botu engellemiş olabilir

async def yalan_oy_ver_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        print(f"Oylama callback answer hatası: {e}")
        pass
    
    user_id = query.from_user.id
    
    # Callback data'dan chat_id ve oy verilen kişinin ID'sini al
    try:
        data_parts = query.data.split("_")
        print(f"Callback data: {query.data}, Parts: {data_parts}")
        
        if len(data_parts) < 4:
            try:
                await query.edit_message_text("❌ Geçersiz callback data!")
            except:
                pass
            return
            
        # Format: yalan_oy_ver_{chat_id}_{oy_verilen_id}
        chat_id = int(data_parts[2])  # 3. eleman chat_id
        oy_verilen_id = int(data_parts[3])  # 4. eleman oy verilen kişi
        print(f"Chat ID: {chat_id}, Oy verilen ID: {oy_verilen_id}")
    except (ValueError, IndexError) as e:
        print(f"Callback data parse hatası: {e}")
        try:
            await query.edit_message_text("❌ Geçersiz callback data formatı!")
        except:
            pass
        return
    
    # Oyun kontrolü
    if chat_id not in yalan_oyunlari:
        try:
            await query.edit_message_text("❌ Oyun bulunamadı!")
        except:
            pass
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    # Oyun durumu kontrolü
    if oyun.oyun_durumu != "oylama":
        try:
            await query.edit_message_text("❌ Şu anda oylama yapılmıyor!")
        except:
            pass
        return
    
    # Oyuncu kontrolü
    if user_id not in oyun.oyuncular:
        try:
            await query.edit_message_text("❌ Oyunda değilsiniz!")
        except:
            pass
        return
    
    if oy_verilen_id not in oyun.oyuncular:
        try:
            await query.edit_message_text("❌ Geçersiz oy hedefi!")
        except:
            pass
        return
    
    basarili, mesaj = oyun.oy_ver(user_id, oy_verilen_id)
    
    if basarili:
        # Oy veren ve oy verilen kişinin isimlerini al
        oy_veren_isim = oyun.oyuncular[user_id]['isim']
        oy_verilen_isim = oyun.oyuncular[oy_verilen_id]['isim']
        
        # Gruba oy verme mesajı gönder
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🗳️ <b>{oy_veren_isim}</b> <b>{oy_verilen_isim}</b>'i linçlemek için oy kullandı!",
            parse_mode="HTML"
        )
        
        try:
            await query.answer("✅ Oyunuz kaydedildi!")
        except:
            pass
        
        # Tüm oyuncular oy verdi mi kontrol et
        hazir_oyuncular = [uid for uid, oyuncu in oyun.oyuncular.items() if oyuncu["hazir"]]
        if len(oyun.oyuncu_oylamalari) >= len(hazir_oyuncular):
            await oylama_sonucu_goster(context, chat_id)
    else:
        try:
            await query.answer(f"❌ {mesaj}")
        except:
            pass

async def oylama_sonucu_goster(context: ContextTypes.DEFAULT_TYPE, chat_id):
    if chat_id not in yalan_oyunlari:
        return
    
    oyun = yalan_oyunlari[chat_id]
    kazanan, mesaj = oyun.oylama_sonucu()
    
    if kazanan:
        # En çok oy alan kişiyi bul
        oy_sayilari = {}
        for oy_verilen_id in oyun.oyuncu_oylamalari.values():
            oy_sayilari[oy_verilen_id] = oy_sayilari.get(oy_verilen_id, 0) + 1
        
        en_cok_oy_alan = max(oy_sayilari, key=oy_sayilari.get)
        linclenen_isim = oyun.oyuncular[en_cok_oy_alan]['isim']
        
        # Yalancıları açıkla
        yalancı_isimler = [oyun.oyuncular[uid]['isim'] for uid in oyun.yalancilar]
        
        # Oy sonuçlarını göster
        oy_sonuclari = "🗳️ <b>OY SONUÇLARI</b> 🗳️\n\n"
        
        # Oyuncu listesi (canlı/ölü durumu ile)
        toplam_oyuncu = len(oyun.oyuncular)
        yasayan_oyuncu = toplam_oyuncu - 1  # Linçlenen kişi hariç
        
        oyuncu_listesi = f"👥 <b>OYUNCULAR ({yasayan_oyuncu}/{toplam_oyuncu}):</b>\n"
        for oyuncu_id, oyuncu in oyun.oyuncular.items():
            durum = "💀 ÖLÜ" if oyuncu_id == en_cok_oy_alan else "❤️ Yaşıyor"
            oyuncu_listesi += f"• {oyuncu['isim']} - {durum}\n"
        
        oy_sonuclari += oyuncu_listesi + "\n"
        oy_sonuclari += f"🎭 <b>YALANCILAR:</b> {', '.join(yalancı_isimler)}\n"
        oy_sonuclari += f"💀 <b>LİNÇLENEN:</b> {linclenen_isim}\n\n"
        oy_sonuclari += f"🏆 <b>SONUÇ:</b> {mesaj}"
        
        # Puan sistemi - kazananlara puan ver
        if kazanan == "dürüstler":
            # Dürüstler kazandı - yalancı olmayan herkese puan ver
            for oyuncu_id, oyuncu in oyun.oyuncular.items():
                if oyuncu_id not in oyun.yalancilar:
                    try:
                        chat = await context.bot.get_chat(chat_id)
                        chat_name = chat.title or chat.first_name or "Bilinmeyen Grup"
                        
                        basarili, _ = puan_sistemi.puan_ekle(
                            oyuncu_id,
                            oyuncu['isim'],
                            "yalanciyi_tahmin",
                            5,  # Kazanan puanı
                            chat_id,
                            chat_name
                        )
                    except Exception as e:
                        print(f"Puan ekleme hatası: {e}")
        else:
            # Yalancılar kazandı - yalancılara puan ver
            for yalancı_id in oyun.yalancilar:
                try:
                    chat = await context.bot.get_chat(chat_id)
                    chat_name = chat.title or chat.first_name or "Bilinmeyen Grup"
                    
                    basarili, _ = puan_sistemi.puan_ekle(
                        yalancı_id,
                        oyun.oyuncular[yalancı_id]['isim'],
                        "yalanciyi_tahmin",
                        5,  # Kazanan puanı
                        chat_id,
                        chat_name
                    )
                except Exception as e:
                    print(f"Puan ekleme hatası: {e}")
        
        await context.bot.send_message(chat_id=chat_id, text=oy_sonuclari, parse_mode="HTML")
        
        # Oyunu temizle
        oyun.oyunu_bitir()
        del yalan_oyunlari[chat_id]

# Otomatik güncelleme fonksiyonu kaldırıldı - gereksizdi

async def yalan_hizli_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yalan oyununu süre beklemeden direkt başlatır"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in yalan_oyunlari:
        await update.message.reply_text("❌ Aktif yalan oyunu bulunamadı!")
        return
    
    oyun = yalan_oyunlari[chat_id]
    
    if oyun.oyun_durumu != "bekleme":
        await update.message.reply_text("❌ Oyun zaten başladı!")
        return
    
    # Yeterli oyuncu var mı kontrol et
    if len(oyun.oyuncular) < oyun.min_oyuncu:
        await update.message.reply_text(
            f"❌ Yeterli oyuncu yok!\n"
            f"Gerekli: {oyun.min_oyuncu}, Mevcut: {len(oyun.oyuncular)}"
        )
        return
    
    # Tüm oyuncuları hazır yap
    for user_id in oyun.oyuncular:
        oyun.oyuncular[user_id]["hazir"] = True
    
    # Hatırlatma task'ını iptal et
    if oyun.hatirlatma_task and not oyun.hatirlatma_task.done():
        oyun.hatirlatma_task.cancel()
    
    # Oyunu başlat
    basarili, mesaj = oyun.oyunu_baslat()
    if basarili:
        await update.message.reply_text("✅ Oyun başlatılıyor...")
        await oyun_baslatildi_mesaji_gonder(context, chat_id)
    else:
        await update.message.reply_text(f"❌ {mesaj}")

async def hatirlatma_mesaji_gonder_async(context, chat_id):
    """60 saniyede bir hatırlatma mesajı gönderen async task"""
    
    try:
        while True:
            try:
                if chat_id not in yalan_oyunlari:
                    break
                
                oyun = yalan_oyunlari[chat_id]
                # Oyun bekleme durumunda değilse veya oyun başladıysa durdur
                if oyun.oyun_durumu != "bekleme":
                    print(f"Hatırlatma durduruldu - Oyun durumu: {oyun.oyun_durumu}")
                    break
                
                # 60 saniye bekle
                await asyncio.sleep(60)
                
                # Tekrar kontrol et (oyun başlamış olabilir)
                if chat_id not in yalan_oyunlari:
                    break
                
                oyun = yalan_oyunlari[chat_id]
                if oyun.oyun_durumu != "bekleme":
                    print(f"Hatırlatma durduruldu - Oyun durumu: {oyun.oyun_durumu}")
                    break
                
                # Kalan süreyi hesapla (oyun başlatma zamanından itibaren geçen süre)
                simdi = datetime.now()
                gecen_sure = (simdi - oyun.oyun_baslama_zamani).total_seconds()
                kalan_sure = max(0, oyun.baslatma_suresi - gecen_sure)
                
                # Eğer süre bittiyse döngüden çık
                if kalan_sure <= 0:
                    print("Hatırlatma durduruldu - Süre bitti")
                    break
                
                kalan_dakika = int(kalan_sure // 60)
                kalan_saniye = int(kalan_sure % 60)
                
                keyboard = [
                    [InlineKeyboardButton("Oyuna Katıl", callback_data="yalan_katil_ozel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Hatırlatma mesajı gönder
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ <b>Kalan Süre:</b> {kalan_dakika}:{kalan_saniye:02d}\n\n"
                             f"🎯 Oyuna katılmak için butona basın!",
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Hatırlatma mesajı gönderme hatası: {e}")
            
            except Exception as e:
                print(f"Hatırlatma task hatası: {e}")
                break
    except asyncio.CancelledError:
        # Task iptal edildi, normal
        print("Hatırlatma task iptal edildi")
        pass
    except Exception as e:
        print(f"Hatırlatma task genel hatası: {e}")
        pass

# Handler'ları kaydet
def yalan_handlers(app):
    app.add_handler(CommandHandler("yalan", yalan_baslat))
    app.add_handler(CommandHandler("uzat", yalan_uzat))
    app.add_handler(CommandHandler("ybaslat", yalan_hizli_baslat))
    app.add_handler(CallbackQueryHandler(yalan_katil_ozel_callback, pattern="^yalan_katil_ozel$"))
    app.add_handler(CallbackQueryHandler(yalan_katil_ozelden_callback, pattern="^yalan_katil_ozelden_"))
    app.add_handler(CallbackQueryHandler(yalan_kac_callback, pattern="^yalan_kac_"))
    app.add_handler(CallbackQueryHandler(yalan_hazir_callback, pattern="^yalan_hazir_"))
    app.add_handler(CallbackQueryHandler(yalan_baslat_oyun_callback, pattern="^yalan_baslat_oyun$"))
    app.add_handler(CallbackQueryHandler(yalan_quiz_cevap_callback, pattern="^quiz_cevap_"))
    # Soruyu geç butonları kaldırıldı - sadece anket var

async def anket_suresi_bekle(chat_id: int, context: ContextTypes.DEFAULT_TYPE, oyun: QuizOyun):
    """Anket süresini bekler ve sonuçları işler"""
    try:
        # 15 saniye bekle
        await asyncio.sleep(15)
        
        # Oyun hala aktif mi kontrol et
        if chat_id not in yalan_quiz_oyunlari or not oyun.aktif or not oyun.aktif_soru:
            print(f"⏰ Anket süresi bekleme iptal edildi - oyun aktif değil: {chat_id}")
            return
        
        print(f"⏰ Anket süresi doldu: {chat_id}")
        
        # Anket sonuçlarını işle ve puanları hesapla
        try:
            await asyncio.wait_for(
                _process_poll_results(chat_id, context, oyun),
                timeout=30.0  # Timeout süresini artırdım
            )
        except asyncio.TimeoutError:
            print(f"⏰ Anket sonuçları işleme timeout: {chat_id}")
            # Timeout olursa manuel olarak yeni soruya geç
            try:
                await asyncio.sleep(3)
                await asyncio.wait_for(
                    quiz_yeni_soru(chat_id, context),
                    timeout=30.0  # Timeout süresini artırdım
                )
            except Exception as e2:
                print(f"❌ Manuel yeni soru hatası: {e2}")
        except (TimedOut, NetworkError) as e:
            print(f"⏰ Telegram API timeout/network hatası: {e}")
            # Network hatası olursa manuel olarak yeni soruya geç
            try:
                await asyncio.sleep(3)
                await asyncio.wait_for(
                    quiz_yeni_soru(chat_id, context),
                    timeout=30.0  # Timeout süresini artırdım
                )
            except Exception as e2:
                print(f"❌ Manuel yeni soru hatası: {e2}")
        except Exception as e:
            print(f"❌ Anket sonuçları işleme hatası: {e}")
            # Hata olursa manuel olarak yeni soruya geç
            try:
                await asyncio.sleep(3)
                await asyncio.wait_for(
                    quiz_yeni_soru(chat_id, context),
                    timeout=30.0  # Timeout süresini artırdım
                )
            except Exception as e2:
                print(f"❌ Manuel yeni soru hatası: {e2}")
                
    except asyncio.CancelledError:
        print(f"⏰ Anket süresi bekleme iptal edildi: {chat_id}")
        pass
    except Exception as e:
        print(f"❌ Anket süresi bekleme hatası: {e}")
