import firebase_admin
from firebase_admin import credentials, auth, firestore # ✅ Ganti 'db' dengan 'firestore'
from app.config import Config
from datetime import datetime

class FirebaseService:
    _initialized = False
    _firestore_db = None  # Variabel untuk menyimpan referensi Firestore Client
    
    @classmethod
    def initialize(cls):
        """Inisialisasi Firebase Admin SDK dan Firestore Client."""
        if not cls._initialized:
            try:
                cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
                
                # Inisialisasi Firebase App. Kita tidak perlu databaseURL jika hanya menggunakan Firestore.
                # Namun, jika Anda memang masih butuh Realtime DB, sertakan 'databaseURL'.
                firebase_admin.initialize_app(cred)
                
                # Simpan referensi Firestore Client untuk penggunaan di fungsi lain
                cls._firestore_db = firestore.client() 
                cls._initialized = True
                print("Firebase Admin SDK & Firestore Client initialized.")
            except Exception as e:
                print(f"FATAL: Gagal inisialisasi FirebaseService: {e}")
                cls._initialized = False # Pastikan status tidak diubah jika gagal
    
    @staticmethod
    def verify_token(id_token, check_revoked=False, clock_skew_seconds=0):
        """Verifikasi Firebase ID token dari Flutter"""
        try:
            # Fungsi auth tetap sama, karena Admin SDK menangani otentikasi secara global
            decoded_token = auth.verify_id_token(
                id_token,
                check_revoked=check_revoked, 
                clock_skew_seconds=clock_skew_seconds
            )
            return decoded_token
        except Exception as e:
            return None
    
    @staticmethod
    def get_user(uid):
        """Ambil data user dari Firebase"""
        try:
            user = auth.get_user(uid)
            return {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'photo_url': user.photo_url
            }
        except Exception as e:
            return None
    
    # ====================================================================
    # ✅ FUNGSI BARU: Menggunakan FIRESTORE (Database berbasis Dokumen)
    # ====================================================================

    @classmethod
    def save_detection_result(cls, uid, data):
        """Simpan hasil deteksi ke Firestore (Koleksi users/{uid}/detections)"""
        if not cls._firestore_db:
            print("Firestore client not initialized.")
            return None
            
        # Tambahkan timestamp jika belum ada (menggunakan waktu server)
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
            
        try:
            # Path: users/{uid}/detections/{dokumen_otomatis}
            ref = cls._firestore_db.collection('users').document(uid).collection('detections')
            
            # Tambahkan data baru (Firestore akan otomatis menghasilkan ID)
            update_time, doc_ref = ref.add(data)
            
            return doc_ref.id # Kembalikan ID dokumen yang baru dibuat
        except Exception as e:
            print(f"Error saving detection to Firestore: {e}")
            return None
    
    @classmethod
    def get_user_detections(cls, uid, limit=20):
        """Ambil riwayat deteksi user dari Firestore"""
        if not cls._firestore_db:
            print("Firestore client not initialized.")
            return []
            
        try:
            ref = cls._firestore_db.collection('users').document(uid).collection('detections')
            
            # Query Firestore: Urutkan berdasarkan timestamp, ambil N terakhir
            query = ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            
            results = query.stream()
            
            # Format hasil menjadi list of dict
            detections = []
            for doc in results:
                data = doc.to_dict()
                data['id'] = doc.id
                detections.append(data)
                
            # Karena kita menggunakan DESCENDING, data sudah yang terbaru di depan
            return detections
            
        except Exception as e:
            print(f"Error getting detections from Firestore: {e}")
            return []