import firebase_admin
from firebase_admin import credentials, db
import os
import json

def debug_vape9():
    if not os.path.exists("key.json"):
        print("❌ key.json 파일이 없습니다!")
        return

    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })

    # Check products/vape9 path
    print("📡 Firebase에서 products/vape9 데이터 확인 중...")
    ref = db.reference('products/vape9')
    vape9_data = ref.get()
    
    if vape9_data:
        print(f"✅ vape9 데이터 발견: {len(vape9_data)}개 상품")
        # 첫 번째 상품 출력
        first_key = list(vape9_data.keys())[0]
        print(f"\n📦 첫 번째 상품 예시 (key: {first_key}):")
        print(json.dumps(vape9_data[first_key], indent=2, ensure_ascii=False))
    else:
        print("❌ products/vape9 경로에 데이터가 없습니다!")
    
    # Check if vape9 exists under 'products' root
    print("\n📡 products 루트 노드의 하위 키 목록 확인...")
    products_ref = db.reference('products')
    products_data = products_ref.get()
    if products_data:
        print(f"✅ products 하위 키: {list(products_data.keys())}")
    else:
        print("❌ products 노드에 데이터가 없습니다!")

if __name__ == "__main__":
    debug_vape9()
