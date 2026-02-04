import firebase_admin
from firebase_admin import credentials, db
import os

def check_sites():
    if not os.path.exists("key.json"):
        return

    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })

    ref = db.reference('products')
    data = ref.get()
    if data:
        keys = list(data.keys())
        with open("firebase_keys.txt", "w", encoding="utf-8") as f:
            for k in keys:
                f.write(k + "\n")
        print(f"총 {len(keys)}개 사이트 키가 firebase_keys.txt에 저장되었습니다.")
    else:
        print("데이터 없음")

if __name__ == "__main__":
    check_sites()
