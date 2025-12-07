import os
import cv2
import numpy as np
import pandas as pd
from pillow_heif import read_heif
from PIL import Image
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
from skimage.feature import local_binary_pattern

# ===================== PATH =======================
base_proj = os.path.dirname(os.path.abspath(__file__))

train_dir = os.path.join(base_proj, "pcoyserangga", "train")
test_dir  = os.path.join(base_proj, "pcoyserangga", "test")

csv_path   = os.path.join(base_proj, "pcoy_dataset_features.csv")
model_path = os.path.join(base_proj, "naivebayes_pakcoy.pkl")

# =================== Baca gambar HEIC ====================
def read_image_any_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".heic":
        heif_file = read_heif(path)
        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    else:
        return cv2.imread(path)

# ====================== AUGMENTASI ========================
def augment_image(img):
    aug = []
    aug.append(cv2.flip(img, 1))
    aug.append(cv2.flip(img, 0))
    aug.append(cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE))
    aug.append(cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE))
    aug.append(cv2.convertScaleAbs(img, alpha=1.2, beta=15))

    rows, cols = img.shape[:2]
    for angle in [15, -15]:
        M = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
        aug.append(cv2.warpAffine(img, M, (cols, rows)))

    return aug

# ===================== EKSTRAK FITUR ====================
def extract_features(img):
    img = cv2.resize(img, (128, 128))

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h_mean = np.mean(hsv[:, :, 0]) / 179.0
    s_mean = np.mean(hsv[:, :, 1]) / 255.0
    v_mean = np.mean(hsv[:, :, 2]) / 255.0
    h_std = np.std(hsv[:, :, 0]) / 179.0
    s_std = np.std(hsv[:, :, 1]) / 255.0
    v_std = np.std(hsv[:, :, 2]) / 255.0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_mean = np.mean(gray) / 255.0
    gray_std = np.std(gray) / 255.0

    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / edges.size

    lbp = local_binary_pattern(gray, P=8, R=1, method='uniform')
    lbp_hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, 10), density=True)

    feats = [
        round(h_mean,3), round(s_mean,3), round(v_mean,3),
        round(h_std,3), round(s_std,3), round(v_std,3),
        round(gray_mean,3), round(gray_std,3),
        round(edge_density,3)
    ]
    feats.extend(np.round(lbp_hist,3))

    return feats


# =================== TRAINING =====================
print("\n=== MEMBACA DATASET TRAIN ===\n")

data = []
labels = []

original_count = 0
augmented_count = 0

for root, dirs, files in os.walk(train_dir):
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
            img_path = os.path.join(root, file)
            img = read_image_any_format(img_path)
            if img is None:
                continue

            label = os.path.basename(root)

            # original
            feats = extract_features(img)
            data.append(feats)
            labels.append(label)
            original_count += 1

            # augment
            for aug in augment_image(img):
                data.append(extract_features(aug))
                labels.append(label)
                augmented_count += 1

# Simpan CSV
columns = [
    'H_mean','S_mean','V_mean',
    'H_std','S_std','V_std',
    'Gray_mean','Gray_std','Edge_density',
    'LBP_0','LBP_1','LBP_2','LBP_3','LBP_4',
    'LBP_5','LBP_6','LBP_7','LBP_8'
]

df = pd.DataFrame(data, columns=columns)
df['label'] = labels
df = df.sample(frac=1, random_state=None).reset_index(drop=True)
df.to_csv(csv_path, index=False)

print("=== INFORMASI DATASET ===")
print("Total gambar asli       :", original_count)
print("Total augmentasi        :", augmented_count)
print("Total baris CSV         :", len(df))
print(df['label'].value_counts())


# ===================== TRAIN TEST SPLIT ======================
X = df.drop('label', axis=1)
y = df['label']

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.25, shuffle=True, stratify=y, random_state=None
)


model = GaussianNB()
model.fit(X_train, y_train)

pred_val = model.predict(X_val)
acc_val = accuracy_score(y_val, pred_val)

print("\n=== HASIL TRAINING (VALIDASI) ===")
print("Akurasi:", acc_val)
print(classification_report(y_val, pred_val))

joblib.dump(model, model_path)
print("Model disimpan:", model_path)


# =========================== TESTING ===========================
print("\n=== MULAI TESTING ===\n")

test_data = []
true_labels = []

for root, dirs, files in os.walk(test_dir):
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
            img_path = os.path.join(root, file)
            img = read_image_any_format(img_path)
            if img is None:
                continue

            label = os.path.basename(root)
            feats = extract_features(img)

            test_data.append(feats)
            true_labels.append(label)

test_df = pd.DataFrame(test_data)

pred_test = model.predict(test_df)
acc_test = accuracy_score(true_labels, pred_test)

print("=== HASIL TEST ===")
print("Akurasi Test:", acc_test)
print(classification_report(true_labels, pred_test))

# ==================== GRAFIK EVALUASI ========================

# ============================================================
# ==================== GRAFIK EVALUASI ========================
# ============================================================

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

# ----------- Akurasi Train / Val / Test -----------
train_accuracy = accuracy_score(y_train, model.predict(X_train))
val_accuracy   = acc_val
test_accuracy  = acc_test

# ----------- Confusion Matrix -----------
cm = confusion_matrix(true_labels, pred_test, labels=model.classes_)

# ----------- F1 Score per Kelas -----------
prec, rec, f1, sup = precision_recall_fscore_support(
    true_labels, pred_test, labels=model.classes_
)

plt.figure(figsize=(14,10))

# ---- Subplot 1: Akurasi ----
plt.subplot(2,2,1)
plt.plot(["Train", "Validation", "Test"],
         [train_accuracy, val_accuracy, test_accuracy],
         marker='o')
plt.title("Akurasi Model Naive Bayes")
plt.ylabel("Akurasi")
plt.ylim(0, 1)
plt.grid(True)

# ---- Subplot 2: Confusion Matrix ----
plt.subplot(2,2,2)
sns.heatmap(cm, annot=True, fmt="d",
            xticklabels=model.classes_,
            yticklabels=model.classes_,
            cmap="Blues")
plt.title("Confusion Matrix - Data Test")
plt.xlabel("Predicted")
plt.ylabel("Actual")

# ---- Subplot 3: F1 Score per Kelas ----
plt.subplot(2,1,2)  # Lebar penuh bawah
plt.bar(model.classes_, f1)
plt.title("F1 Score per Kelas")
plt.ylabel("F1 Score")
plt.ylim(0,1)
plt.grid(True, axis="y")

plt.tight_layout()
plt.show()
