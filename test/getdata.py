from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate('hydrosee-projects-firebase-adminsdk-fbsvc-dc95d05e8e.json')

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://hydrosee-projects-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

ref = db.reference('devices/esp32')
print(ref.get())  