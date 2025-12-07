from flask import Blueprint, request, jsonify
from app.services.firebase_service import FirebaseService
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, firestore
import hashlib, secrets, time
from werkzeug.utils import secure_filename
import cv2
import numpy as np

# Konfigurasi Upload
UPLOAD_FOLDER = 'storage/static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)   

bp = Blueprint('iot_device', __name__)

# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def hash_token(token: str) -> str:
    """Hash token menggunakan SHA256"""
    return hashlib.sha256(token.encode()).hexdigest()

def allowed_file(filename):
    """Cek apakah file extension diizinkan"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================================================================
# ROUTE 1: REGISTER DEVICE (Pendaftaran Perangkat IoT)
# =========================================================================

@bp.route('/register', methods=['POST'])
def register_device():
    """
    Endpoint untuk mendaftarkan perangkat IoT baru
    Request Body (JSON):
    - idToken: Firebase Auth ID Token
    - deviceId: MAC Address perangkat (akan jadi document ID)
    - deviceName: Nama perangkat
    - deviceType: Tipe perangkat (misal: 'sensor', 'camera')
    """
    id_token = request.json.get('idToken')
    device_id = request.json.get('deviceId')
    device_name = request.json.get('deviceName', 'ESP32-HydroSee')
    device_type = request.json.get('deviceType', 'sensor')
    
    # Validasi input
    if not id_token or not device_id:
        return jsonify({'error': 'Missing required fields: idToken or deviceId'}), 400
    
    # Verify Firebase ID Token
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded['uid']
    except Exception as e:
        return jsonify({'error': 'Invalid token', 'detail': str(e)}), 401
    
    # Akses Firestore
    db = firestore.client()
    device_ref = db.collection('devices').document(device_id)
    
    try:
        # Cek apakah device sudah terdaftar
        device_doc = device_ref.get()
        
        if device_doc.exists:
            existing_data = device_doc.to_dict()
            # Jika sudah dimiliki user lain
            if existing_data.get('userId') != uid:
                return jsonify({
                    'error': 'Device already owned by another user',
                    'owner': existing_data.get('userId')
                }), 403
            
            # Jika sudah dimiliki user yang sama, return success
            return jsonify({
                'success': True,
                'message': 'Device already registered to this user',
                'deviceId': device_id
            }), 200
        
        # Generate pairing token
        pairing_token = secrets.token_urlsafe(16)
        now = firestore.SERVER_TIMESTAMP
        
        # Data device baru
        
        if device_type != "camera":
            new_device = {
                'name': device_name,
                'type': device_type,
                'userId': uid,
                'macAddress': device_id,
                'status': 'offline',
                'pairingTokenHash': hash_token(pairing_token),
                'createdAt': now,
                'lastSeen': now,
            }
        
        else:
            new_device = {
                'name': device_name,
                'type': device_type,
                'userId': uid,
                'macAddress': device_id,
                'status': 'offline',
                'pairingTokenHash': hash_token(pairing_token),
                'createdAt': now,
                'lastSeen': now,
                'lastTemp': 0.0,
                'lastHum': 0.0
            }
        
        # Simpan ke Firestore
        device_ref.set(new_device)
        
        return jsonify({
            'success': True,
            'message': 'Device registered successfully',
            'deviceId': device_id,
            'pairingToken': pairing_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Registration failed', 'detail': str(e)}), 500

# =========================================================================
# ROUTE 2: GET DEVICES (Ambil daftar perangkat user)
# =========================================================================

@bp.route('/list', methods=['GET'])
def get_devices():
    """
    Endpoint untuk mengambil daftar perangkat IoT milik user
    Headers:
    - Authorization: Bearer <idToken>
    """
    # Ambil token dari header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401
    
    id_token = auth_header.split('Bearer ')[1]
    
    # Verify token
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded['uid']
    except Exception as e:
        return jsonify({'error': 'Invalid token', 'detail': str(e)}), 401
    
    # Query Firestore
    db = firestore.client()
    devices_ref = db.collection('devices').where('userId', '==', uid)
    
    try:
        devices = []
        for doc in devices_ref.stream():
            device_data = doc.to_dict()
            device_data['deviceId'] = doc.id
            devices.append(device_data)
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch devices', 'detail': str(e)}), 500

# =========================================================================
# ROUTE 3: GET SENSOR DATA (Ambil data suhu & kelembapan terbaru)
# =========================================================================


@bp.route('/sensor-update-data', methods=['POST'])
def update_sensor_data():
    """
    Endpoint untuk menerima data sensor Suhu dan Kelembapan dari IoT Device
    dan mengupdatenya di dokumen 'devices' Firestore.

    Request Body (JSON):
    - deviceId: MAC Address perangkat (Document ID)
    - temp: Suhu saat ini
    - humid: Kelembapan saat ini
    - pairingToken: Token yang dihasilkan saat register
    """
    data = request.get_json()
    device_id = data.get('deviceId')
    temp = data.get('temp')
    humid = data.get('humid')
    pairing_token = data.get('pairingToken')

    # 1. Validasi Input
    if not device_id or temp is None or humid is None or not pairing_token:
        return jsonify({'error': 'Missing data in request body (deviceId, temp, humid, or pairingToken)'}), 400

    db = firestore.client()
    device_ref = db.collection('devices').document(device_id)

    try:
        device_doc = device_ref.get()
        if not device_doc.exists:
            return jsonify({'error': 'Device not found'}), 404
        
        device_data = device_doc.to_dict()

        # 2. Verifikasi Pairing Token (Otentikasi Perangkat)
        # Hash token yang diterima dan bandingkan dengan yang ada di Firestore
        hashed_input_token = hash_token(pairing_token)
        if device_data.get('pairingTokenHash') != hashed_input_token:
            return jsonify({'error': 'Unauthorized: Invalid pairing token'}), 401

        # 3. Update Data Sensor di Dokumen Device
        sensor_payload = {
            'lastTemp': float(temp),   # Menggunakan nama field yang sama dengan register dan model
            'lastHum': float(humid),   # Menggunakan nama field yang sama dengan register dan model
            'lastSeen': firestore.SERVER_TIMESTAMP,
            'status': 'online' # Update status menjadi online saat mengirim data
        }

        # Catatan Penting: Karena perangkat tidak mengirimkan token Firebase Auth,
        # kita tidak bisa menggunakan request.auth.uid == request.resource.data.userId
        # dalam Rules Firestore untuk Penulisan. Rules penulisan harus disesuaikan 
        # untuk mempercayai Backend Python yang sudah terautentikasi (Service Account).
        
        device_ref.update(sensor_payload)

        # (Opsional) 4. Simpan Riwayat Bacaan ke Sub-collection 'readings'
        readings_ref = device_ref.collection('readings')
        readings_ref.add({
            'temperature': float(temp),
            'humidity': float(humid),
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'success': True, 'message': 'Sensor data updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to update sensor data', 'detail': str(e)}), 500

# =========================================================================
# ROUTE 4: GET HISTORICAL DATA (Ambil riwayat data sensor)
# =========================================================================

@bp.route('/sensor-history/<device_id>', methods=['GET'])
def get_sensor_history(device_id):
    """
    Endpoint untuk mengambil riwayat data sensor
    Path Parameter:
    - device_id: MAC Address perangkat
    Query Parameters:
    - limit: Jumlah data yang diambil (default: 50)
    Headers:
    - Authorization: Bearer <idToken>
    """
    # Ambil token dari header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401
    
    id_token = auth_header.split('Bearer ')[1]
    limit = request.args.get('limit', 50, type=int)
    
    # Verify token
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded['uid']
    except Exception as e:
        return jsonify({'error': 'Invalid token', 'detail': str(e)}), 401
    
    # Query Firestore
    db = firestore.client()
    device_ref = db.collection('devices').document(device_id)
    
    try:
        # Cek device exists dan kepemilikan
        device_doc = device_ref.get()
        if not device_doc.exists:
            return jsonify({'error': 'Device not found'}), 404
        
        device_data = device_doc.to_dict()
        if device_data.get('userId') != uid:
            return jsonify({'error': 'Unauthorized access'}), 403
        
        # Ambil data historis dari sub-collection
        readings_ref = device_ref.collection('readings').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        
        history = []
        for doc in readings_ref.stream():
            reading = doc.to_dict()
            history.append({
                'temperature': reading.get('temperature'),
                'humidity': reading.get('humidity'),
                'timestamp': reading.get('timestamp')
            })
        
        return jsonify({
            'success': True,
            'deviceId': device_id,
            'history': history,
            'count': len(history)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch history', 'detail': str(e)}), 500

# =========================================================================
# ROUTE 5: DELETE DEVICE (Hapus perangkat)
# =========================================================================

@bp.route('/delete/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """
    Endpoint untuk menghapus perangkat IoT
    Path Parameter:
    - device_id: MAC Address perangkat
    Headers:
    - Authorization: Bearer <idToken>
    """
    # Ambil token dari header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401
    
    id_token = auth_header.split('Bearer ')[1]
    
    # Verify token
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded['uid']
    except Exception as e:
        return jsonify({'error': 'Invalid token', 'detail': str(e)}), 401
    
    # Query Firestore
    db = firestore.client()
    device_ref = db.collection('devices').document(device_id)
    
    try:
        device_doc = device_ref.get()
        
        if not device_doc.exists:
            return jsonify({'error': 'Device not found'}), 404
        
        device_data = device_doc.to_dict()
        
        # Cek kepemilikan
        if device_data.get('userId') != uid:
            return jsonify({'error': 'Unauthorized to delete this device'}), 403
        
        # Hapus sub-collection readings dulu (optional, tergantung kebutuhan)
        readings_ref = device_ref.collection('readings')
        batch = db.batch()
        for doc in readings_ref.stream():
            batch.delete(doc.reference)
        batch.commit()
        
        # Hapus device document
        device_ref.delete()
        
        return jsonify({
            'success': True,
            'message': f'Device {device_id} deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete device', 'detail': str(e)}), 500

# =========================================================================
# ROUTE 6: UPLOAD IMAGE (dari ESP32-CAM untuk deteksi serangga)
# =========================================================================

@bp.route('/upload-image', methods=['POST'])
def upload_image():
    # 1. Verifikasi Device ID dari Header (atau body)
    # ESP32 mengirim deviceId di body dan header X-Device-ID
    device_id = request.form.get('deviceId')
    
    # Fallback ke header jika body kosong (tergantung implementasi ESP)
    if not device_id:
        device_id = request.headers.get('X-Device-ID')

    if not device_id:
        return jsonify({'error': 'Missing Device ID'}), 400

    # 2. Cek File
    if 'image' not in request.files:
        return jsonify({'error': 'No image file part in request'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        # 3. Simpan File
        db = firestore.client()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Buat path: /storage/static/images/<device_id>/<timestamp>.jpg
        device_dir = os.path.join(UPLOAD_FOLDER, device_id)
        os.makedirs(device_dir, exist_ok=True)
        
        filename = secure_filename(f"{timestamp}.jpg")
        file_path = os.path.join(device_dir, filename)
        file.save(file_path)
        
        # URL publik yang akan disimpan di Firestore
        # Sesuaikan 'hydrosee.web.id' dengan base URL Anda
        public_url = f"http://hydrosee.web.id/{file_path.replace(os.path.sep, '/')}"

        # 4. Update Firestore
        device_ref = db.collection('devices').document(device_id)
        
        try:
            device_ref.update({
                'lastImage': public_url, # Simpan URL gambar terakhir
                'lastSeen': firestore.SERVER_TIMESTAMP,
                'imageCount': firestore.firestore.Increment(1)
            })
        except Exception as e:
            # Jika dokumen deviceId tidak ada
            return jsonify({'error': 'Failed to update Firestore', 'detail': str(e)}), 500

        return jsonify({
            'message': 'Image uploaded and Firestore updated successfully',
            'imageUrl': public_url
        }), 200
    
    return jsonify({'error': 'Invalid file format'}), 400


@bp.route('/status', methods=['POST'])
def update_status():
    """
    Endpoint untuk menerima heartbeat/status perangkat IoT.
    Request Body (JSON):
    - deviceId: ID perangkat
    - status: 'online'
    """
    
    # Ambil data JSON
    data = request.get_json()
    device_id = data.get('deviceId')
    status = data.get('status')
    
    # Fallback/Verifikasi Device ID dari Header (opsional, tapi disarankan)
    if not device_id:
        device_id = request.headers.get('X-Device-ID')

    if not device_id or not status:
        return jsonify({'error': 'Missing deviceId or status in request'}), 400

    db = firestore.client()
    device_ref = db.collection('devices').document(device_id)

    # Hanya update status dan waktu terakhir terlihat
    try:
        device_ref.update({
            'status': status,
            'lastSeen': firestore.SERVER_TIMESTAMP  # Firestore akan mengisi waktu server
        })
        
        return jsonify({'message': 'Status updated successfully'}), 200
        
    except Exception as e:
        # Ini akan terjadi jika dokumen dengan deviceId tersebut belum terdaftar
        return jsonify({'error': f'Failed to update status for {device_id}', 'detail': str(e)}), 404

# =========================================================================
# ROUTE 7: UPDATE DEVICE NAME (Ubah nama perangkat)
# =========================================================================

@bp.route('/update-name/<device_id>', methods=['PUT'])
def update_device_name(device_id):
    """
    Endpoint untuk mengubah nama perangkat
    Path Parameter:
    - device_id: MAC Address perangkat
    Request Body (JSON):
    - newName: Nama baru perangkat
    Headers:
    - Authorization: Bearer <idToken>
    """
    # Ambil token dari header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401
    
    id_token = auth_header.split('Bearer ')[1]
    new_name = request.json.get('newName')
    
    if not new_name:
        return jsonify({'error': 'Missing newName in request body'}), 400
    
    # Verify token
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded['uid']
    except Exception as e:
        return jsonify({'error': 'Invalid token', 'detail': str(e)}), 401
    
    # Query Firestore
    db = firestore.client()
    device_ref = db.collection('devices').document(device_id)
    
    try:
        device_doc = device_ref.get()
        
        if not device_doc.exists:
            return jsonify({'error': 'Device not found'}), 404
        
        device_data = device_doc.to_dict()
        
        # Cek kepemilikan
        if device_data.get('userId') != uid:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update nama
        device_ref.update({'name': new_name})
        
        return jsonify({
            'success': True,
            'message': 'Device name updated successfully',
            'newName': new_name
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update device name', 'detail': str(e)}), 500