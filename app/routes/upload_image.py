from flask import Blueprint, request, jsonify
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, db
import hashlib, secrets, time

UPLOAD_FOLDER = 'storage/static'
os.makedirs(UPLOAD_FOLDER,  exist_ok=True)

bp = Blueprint('upload_image', __name__)

@bp.route('/', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return 'No Image Part', 400
    
    file = request.files['image']
    if file.filename == '' :
        return "No selected files", 400
    
    filename = datetime.now().strftime('%Y%m%d_%H%M%S') + ".jpg"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return "Image upload succesfully", 200