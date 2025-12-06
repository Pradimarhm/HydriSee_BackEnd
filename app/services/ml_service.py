import cv2, joblib, numpy as np, os, shutil
from skimage.feature import local_binary_pattern
from pillow_heif import read_heif
from app.services.mqtt_send_to_esp32 import MqttSendToEsp32
import time

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# folder tempat file ml_service.py berada
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============= PATH =============

# ambil gambar mentah dari storage/static
FOLDER_ESP = os.path.join(BASE_DIR, "..", "..", "storage", "static", "images")

# folder hasil prediksi
FOLDER_DONE_TRUE  = os.path.join(BASE_DIR, "..", "..", "storage", "imagedone", "predikada")
FOLDER_DONE_FALSE = os.path.join(BASE_DIR, "..", "..", "storage", "imagedone", "prediktidak")

# path model .pkl ada di folder ml_model
MODEL_PATH = os.path.join(BASE_DIR, "..", "..", "ml_model", "naivebayes_pakcoy.pkl")

# buat folder bila belum ada
for p in [FOLDER_ESP, FOLDER_DONE_TRUE, FOLDER_DONE_FALSE]:
    os.makedirs(p, exist_ok=True)

# ============= LOAD MODEL =============
model = joblib.load(MODEL_PATH)

# ============= BACA Gambar =============
def read_image_any_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".heic":
        heif = read_heif(path)
        img = np.array(heif)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        return cv2.imread(path)

# ============= EKSTRAKSI FITUR =============
def extract_features(img):
    img = cv2.resize(img, (128,128))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    feats = [
        np.mean(hsv[:,:,0])/179,
        np.mean(hsv[:,:,1])/255,
        np.mean(hsv[:,:,2])/255,
        np.std(hsv[:,:,0])/179,
        np.std(hsv[:,:,1])/255,
        np.std(hsv[:,:,2])/255,
    ]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    feats.append(np.mean(gray)/255)
    feats.append(np.std(gray)/255)

    edges = cv2.Canny(gray,100,200)
    feats.append(np.sum(edges > 0) / edges.size)

    lbp = local_binary_pattern(gray, P=8, R=1, method='uniform')
    lbp_hist,_ = np.histogram(lbp.ravel(), bins=np.arange(0,10), density=True)
    feats.extend(lbp_hist)

    return np.array(feats).reshape(1,-1)

# ============= PATCH GRID =============
def generate_patches(img, gs=4):
    patches = []
    h, w = img.shape[:2]
    ph, pw = h // gs, w // gs
    for i in range(gs):
        for j in range(gs):
            p = img[i*ph:(i+1)*ph, j*pw:(j+1)*pw]
            if p.size > 0:
                patches.append(p)
    return patches

# ============= ORB DETECTOR =============
orb = cv2.ORB_create(nfeatures=500)

def orb_keypoints(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kp = orb.detect(gray, None)
    return len(kp)

# ============= AMBIL GAMBAR TERTUA =============
def get_oldest(path):
    fs = [
        os.path.join(path, f)
        for f in os.listdir(path)
        if f.lower().endswith((".jpg",".jpeg",".png",".heic"))
    ]
    if not fs:
        return None
    fs.sort(key=os.path.getmtime)
    return fs[0]

# ============= LOOP =============
print("🔌 Menunggu MQTT terkoneksi...")
MqttSendToEsp32.setup_client()

if not MqttSendToEsp32.wait_until_connected(5):
    print("❌ MQTT gagal terkoneksi, tetap lanjut tanpa MQTT...")
else:
    print("✅ MQTT terkoneksi, siap mengirim data!")


while True:
    img_path = get_oldest(FOLDER_ESP)
    if img_path is None:
        print("⚠ Tidak ada gambar, menunggu gambar baru...")
        time.sleep(10)
        continue


    print(f"\n🔍 Memproses: {os.path.basename(img_path)}")
    img = read_image_any_format(img_path)
    if img is None:
        print("❌ Gambar gagal dibaca!")
        continue

    patches = generate_patches(img, 4)

    vote_nb = 0
    vote_orb = 0

    global_orb = orb_keypoints(img)

    # Deteksi over-exposure
    hsv_global = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    if np.mean(hsv_global[:,:,2]) > 190:
        final = "tidakadabelalang"
    else:
        for p in patches:
            feats = extract_features(p)
            pred = model.predict(feats)[0]
            if pred == "belalang":
                vote_nb += 1

            kp = orb_keypoints(p)
            if kp > 45:
                vote_orb += 1

        if vote_nb >= 6:
            final = "belalang"
        elif vote_orb >= 5:
            final = "belalang"
        elif global_orb > 190:
            final = "belalang"
        else:
            final = "tidakadabelalang"

    print(f"📌 Vote NB = {vote_nb}, Vote ORB = {vote_orb}, ORB global = {global_orb}")
    print(f"📌 HASIL FINAL: {final}")

    # ========== MQTT SEND ==========
    try:
        if final == "belalang":
            MqttSendToEsp32.send_insect_status("ada")
        else:
            MqttSendToEsp32.send_insect_status("tidak ada")
    except Exception as e:
        print(f"❌ MQTT ERROR: {e}")


    # pindah file
    dest = FOLDER_DONE_TRUE if final == "belalang" else FOLDER_DONE_FALSE
    shutil.move(img_path, os.path.join(dest, os.path.basename(img_path)))

    print(f"📦 File dipindah ke → {dest}")
    print("⏱ Tunggu sebelum proses berikutnya...")
    time.sleep(5)

print("\n=== SELESAI ===")
