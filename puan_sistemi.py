import pymongo
from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME
from datetime import datetime

class PuanSistemi:
    def __init__(self):
        try:
            self.client = pymongo.MongoClient(MONGODB_URI)
            self.db = self.client[DATABASE_NAME]
            self.collection = self.db[COLLECTION_NAME]
            print("MongoDB bağlantısı başarılı!")
        except Exception as e:
            print(f"MongoDB bağlantı hatası: {e}")
            self.client = None
            self.db = None
            self.collection = None
    
    def puan_ekle(self, user_id, user_name, oyun_tipi, puan, chat_id=None, chat_name=None, chat_username=None):
        """Kullanıcıya puan ekler"""
        if self.collection is None:
            return False, "MongoDB bağlantısı yok!"
        
        try:
            # Mevcut puanı kontrol et
            mevcut = self.collection.find_one({
                "user_id": user_id,
                "oyun_tipi": oyun_tipi,
                "chat_id": chat_id
            })
            
            if mevcut:
                # Mevcut puanı güncelle
                yeni_puan = mevcut["puan"] + puan
                self.collection.update_one(
                    {"user_id": user_id, "oyun_tipi": oyun_tipi, "chat_id": chat_id},
                    {
                        "$set": {
                            "puan": yeni_puan,
                            "son_guncelleme": datetime.now(),
                            "user_name": user_name,
                            "chat_name": chat_name,
                             "chat_username": chat_username
                        }
                    }
                )
            else:
                # Yeni puan kaydı oluştur
                self.collection.insert_one({
                    "user_id": user_id,
                    "user_name": user_name,
                    "oyun_tipi": oyun_tipi,
                    "puan": puan,
                    "chat_id": chat_id,
                    "chat_name": chat_name,
                    "chat_username": chat_username,
                    "ilk_kayit": datetime.now(),
                    "son_guncelleme": datetime.now()
                })
            
            return True, f"{puan} puan eklendi!"
        except Exception as e:
            print(f"Puan ekleme hatası: {e}")
            return False, f"Puan eklenirken hata oluştu: {e}"
    
    def puan_getir(self, user_id, oyun_tipi, chat_id=None):
        """Kullanıcının belirli oyun türündeki puanını getirir"""
        if self.collection is None:
            return 0
        
        try:
            query = {"user_id": user_id, "oyun_tipi": oyun_tipi}
            if chat_id:
                query["chat_id"] = chat_id
                
            kayit = self.collection.find_one(query)
            return kayit["puan"] if kayit else 0
        except Exception as e:
            print(f"Puan getirme hatası: {e}")
            return 0
    
    def top_puanlar(self, oyun_tipi, limit=10, chat_id=None):
        """Belirli oyun türünde en yüksek puanlı oyuncuları getirir"""
        if self.collection is None:
            return []
        
        try:
            query = {"oyun_tipi": oyun_tipi}
            if chat_id:
                query["chat_id"] = chat_id
                
            sonuclar = self.collection.find(query).sort("puan", -1).limit(limit)
            return list(sonuclar)
        except Exception as e:
            print(f"Top puanlar getirme hatası: {e}")
            return []
    
    def kullanici_istatistikleri(self, user_id, chat_id=None):
        """Kullanıcının tüm oyun türlerindeki puanlarını getirir"""
        if self.collection is None:
            return {}
        
        try:
            query = {"user_id": user_id}
            if chat_id:
                query["chat_id"] = chat_id
                
            sonuclar = self.collection.find(query)
            istatistikler = {}
            
            for kayit in sonuclar:
                istatistikler[kayit["oyun_tipi"]] = kayit["puan"]
            
            return istatistikler
        except Exception as e:
            print(f"Kullanıcı istatistikleri hatası: {e}")
            return {}
    
    def global_top_puanlar(self, oyun_tipi, limit=10):
        """Tüm gruplardan en yüksek puanlı oyuncuları getirir"""
        if self.collection is None:
            return []
        
        try:
            # MongoDB aggregation ile global top puanları hesapla
            pipeline = [
                {"$match": {"oyun_tipi": oyun_tipi}},
                {"$group": {
                    "_id": "$user_id",
                    "user_name": {"$first": "$user_name"},
                    "toplam_puan": {"$sum": "$puan"},
                    "chat_names": {"$addToSet": "$chat_name"},
                    "chat_usernames": {"$addToSet": "$chat_username"},
                    "son_guncelleme": {"$max": "$son_guncelleme"}
                }},
                {"$sort": {"toplam_puan": -1}},
                {"$limit": limit}
            ]
            
            sonuclar = self.collection.aggregate(pipeline)
            return list(sonuclar)
        except Exception as e:
            print(f"Global top puanlar getirme hatası: {e}")
            return []

# Global puan sistemi instance'ı
puan_sistemi = PuanSistemi()
