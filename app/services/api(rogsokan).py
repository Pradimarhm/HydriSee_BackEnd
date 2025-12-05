from flask import Flask, request, jsonify
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, db
import hashlib, secrets, time

app = Flask(__name__)

UPLOAD_FOLDER = 'storage/static'
os.makedirs(UPLOAD_FOLDER,  exist_ok=True)

cred = credentials.Certificate('hydrosee-projects-firebase-adminsdk-fbsvc-dc95d05e8e.json')

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://hydrosee-projects-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# REGISTER DEVICE
@app.route('/register_device', methods=['POST'])
def register_device():
    id_token = request.json.get('idToken')
    device_id = request.json.get('deviceId')
    device_type = request.json.get('deviceType')    
    if not id_token or not device_id:
        return jsonify({'error': 'missing'}), 200
    
    # vrifity token
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded['uid']
    except Exception as e:
        return jsonify({'error': 'invalid token', 'detail': str(e)}), 401
    
    device_ref = db.reference(f'devices/{device_id}')
    user_ref = db.reference(f'users/{uid}/devices')
    
    def txn_asign_device(curent):
        # device already or not
        if curent is not None and 'ownerId' in curent:
            # already owned
            return curent
        
        # make token and store only hased version
        pairing_token = secrets.token_urlsafe(8)
        now = int(time.time()*100)
        new = {
            'type': device_type,
            'ownerUid': uid,
            'pairedAt': now,
            'pairingTokenHash': hash_token(pairing_token),
            'lastSeen': now
        }
        return new
    
    result = device_ref.transaction(txn_asign_device)
    
    # result if is the final
    if result is None:
        return jsonify({'error':'transaction_failed'}), 500
    if result.get('ownerUid') != uid:
        return jsonify({'error':'already_owned', 'owner': result.get('ownerUid')}), 403
    
    pairing_token = secrets.token_urlsafe(8)
    device_ref.update({'pairingTokenHash': hash_token(pairing_token)})

    # Save pointer to user's devices (optional)
    user_ref.update({ device_type: device_id })

    return jsonify({'ok': True, 'pairingToken': pairing_token}), 200

# POST IMAGE TO SERVER
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return 'No Image Part', 400
    
    file = request.files['image']
    if file.filename == '' :
        return "No selected files", 400
    
    filename = datetime.now().strftime('%Y%m%d_%H%M%S') + ".jpg"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return "Image upload succesfully", 200

if __name__ == "__main__" :
    app.run(host='0.0.0.0', port=5000)