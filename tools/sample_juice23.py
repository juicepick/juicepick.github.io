
import firebase_admin
from firebase_admin import credentials, db
import json

cred = credentials.Certificate('key.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app'
    })

def sample_check():
    ref = db.reference('products/juice23')
    data = ref.get()
    if not data:
        print("No data")
        return
    
    count = 0
    for k, v in data.items():
        print(f"Name: {v.get('name')}")
        print(f"Price: {v.get('price')}")
        print(f"Image: {v.get('image')}")
        print("-" * 20)
        count += 1
        if count >= 10: break

if __name__ == "__main__":
    sample_check()
