
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import json
import os

# Firebase 초기화 (기존 키 파일 사용)
cred = credentials.Certificate('key.json')
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app'
    })

def check_juice23_images():
    print("Fetching juice23 data from Firebase...")
    ref = db.reference('products/juice23')
    data = ref.get()
    
    if not data:
        print("No data found for juice23")
        return

    print(f"Total items in juice23: {len(data)}")
    
    suspicious_images = []
    normal_images = []
    
    for key, item in data.items():
        img_url = item.get('image', '')
        name = item.get('name', '')
        
        # 엄지손가락이나 아이콘으로 의심되는 패턴 확인
        # 보통 아이콘은 'icon', 'thumb', 'btn' 등의 단어가 포함되거나 사이즈가 작음
        # 여기서는 URL 패턴만 봅니다.
        
        print(f"[{name}] {img_url}")
        
        if "icon" in img_url.lower() or "btn" in img_url.lower():
            suspicious_images.append((name, img_url))
        else:
            normal_images.append((name, img_url))

    print("-" * 50)
    print(f"Suspicious Images found: {len(suspicious_images)}")
    for name, url in suspicious_images[:10]:
        print(f"WARN: {name} -> {url}")
        
    print("-" * 50)
    print(f"Normal Images sample: {len(normal_images)}")
    for name, url in normal_images[:5]:
        print(f"OK: {name} -> {url}")

if __name__ == "__main__":
    check_juice23_images()
