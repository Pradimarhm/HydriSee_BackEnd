from flask import Blueprint, request, jsonify
from app.services.firebase_service import FirebaseService

bp = Blueprint('auth', __name__)

@bp.route('/verify', methods=['POST'])
def verify_token():
    """Verifikasi token dari Flutter"""
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    print(f"Received token: {token}")
    decoded = FirebaseService.verify_token(token, clock_skew_seconds=10)
    
    if not decoded:
        print("Token verification FAILED.")
        return jsonify({'error': 'Invalid token'}), 401
    
    print(f"Token verified for UID: {decoded['uid']}")
    user_data = FirebaseService.get_user(decoded['uid'])
    
    return jsonify({
        'status': 'success',
        'user': user_data
    }), 200