import firebase_admin
from firebase_admin import credentials, db
import os
import json
import sys
sys.path.insert(0, '.')
from build_site import normalize_product

def check_vape9_merge():
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
    
    print(f"vape9 상품 수: {len(vape9_data)}")
    
    # 정규화된 키 샘플 확인
    samples = list(vape9_data.items())[:5]
    for key, val in samples:
        name = val.get('name', '')
        norm = normalize_product(name)
        print(f"\n원본: {name}")
        print(f"  -> match_key: {norm['match_key']}")
        print(f"  -> display_name: {norm['display_name']}")
        print(f"  -> category: {norm['category']}")

if __name__ == "__main__":
    check_vape9_merge()
