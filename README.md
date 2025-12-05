ROUTE IOT DEVICE
POST    /api/device/register                    Daftarkan device baru
GET     /api/device/list                        Ambil daftar device user
GET     /api/device/sensor-data/<device_id>     Data sensor terbaru
GET     /api/device/sensor-history/<device_id>  Riwayat data sensor
DELETE  /api/device/delete/<device_id>          Hapus device
POST    /api/device/upload-image                Upload gambar ESP32-CAM
PUT     /api/device/update-name/<device_id>     Ubah nama device