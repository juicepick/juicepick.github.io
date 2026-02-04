import firebase_admin
from firebase_admin import credentials, db
import os
import sys
sys.path.insert(0, '.')
from build_site import normalize_product

def get_vape9_keys():
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
    vape9_data = ref.get()
    
    if not vape9_data:
        print("vape9 데이터 없음")
        return
    
    # 처음 5개 상품의 match_key 출력
    samples = list(vape9_data.items())[:5]
    print("vape9 상품 match_key (처음 5개):")
    for key, val in samples:
        name = val.get('name', '')
        norm = normalize_product(name)
        print(norm['match_key'])

if __name__ == "__main__":
    get_vape9_keys()
