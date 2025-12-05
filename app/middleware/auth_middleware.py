from functools import wraps
from flask import request, jsonify
from app.services.firebase_service import FirebaseService

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ambil token dari header Authorization
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split('Bearer ')[1]
        
        # Verifikasi token
        decoded_token = FirebaseService.verify_token(token)
        
        if not decoded_token:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Tambahkan user info ke request
        request.user = decoded_token
        
        return f(*args, **kwargs)
    
    return decorated_function   