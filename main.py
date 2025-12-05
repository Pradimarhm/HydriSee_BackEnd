from app import create_app
# Hapus import firebase_admin dan credentials di sini, 
# karena sudah dihandle di FirebaseService
from app.services.firebase_service import FirebaseService
from app.services.mqtt_firebase import MqttFirebase
from app.services.mqtt_send_to_esp32 import MqttSendToEsp32
from app.config import Config

import sys # Import untuk exit

# Create Flask app
# Panggil create_app() di luar blok if __name__ hanya untuk deklarasi app
app = create_app()

if __name__ == '__main__':
    
    # =======================================================
    # 1. INISIALISASI KRITIS (HARUS PERTAMA)
    # =======================================================
    try:
        # Panggil inisialisasi yang ada di FirebaseService (yang memuat creds)
        FirebaseService.initialize() 
        
        # Cek apakah inisialisasi berhasil.
        if not FirebaseService._initialized:
            # Jika inisialisasi gagal di dalam metode initialize, kita keluar.
            print("❌ FATAL: FirebaseService gagal menginisialisasi Admin SDK.")
            sys.exit(1)
            
        print("✅ Firebase Admin SDK initialized.")

    except Exception as e:
        print(f"❌ FATAL: Kesalahan tak terduga saat inisialisasi Firebase: {e}")
        sys.exit(1)

    # =======================================================
    # 2. INISIALISASI LAYANAN (SEKARANG SUDAH AMAN)
    # =======================================================
    
    # Setup dan mulai MQTT Client (sekarang Firestore sudah siap)
    MqttFirebase.start_mqtt_client()
    MqttSendToEsp32.setup_client()
    print("✅ Semua layanan (MQTT) berhasil dimulai.")
    
    # =======================================================
    # 3. MULAI APLIKASI FLASK (LANGKAH TERAKHIR)
    # =======================================================
    print("\nStarting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
    
    # =======================================================
    # 4. KODE BERSIH-BERSIH (CLEANUP)
    # =======================================================
    print("\nServer dimatikan. Melakukan cleanup MQTT...")
    
    # Kode ini akan dieksekusi setelah app.run() berhenti
    try:
        MqttFirebase.client.loop_stop()
        MqttFirebase.client.disconnect()
        MqttSendToEsp32.client.loop_stop()
        MqttSendToEsp32.client.disconnect()
        print("Cleanup MQTT berhasil.")
    except Exception as e:
        print(f"Cleanup Error: {e}")