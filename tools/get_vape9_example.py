import firebase_admin
from firebase_admin import credentials, db
import os
import json

def get_example_product():
    if not os.path.exists("key.json"):
        return

    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })

    ref = db.reference('products/vape9')
    products = ref.order_by_key().limit_to_first(3).get()
    
    if products:
        with open("vape9_examples.json", "w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    get_example_product()
