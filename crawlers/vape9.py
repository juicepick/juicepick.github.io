import time
import os
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import re
import sys
import io

# Windows에서 출력 인코딩 강제 설정 (UTF-8)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Firebase 초기화 함수
def init_firebase():
    if not os.path.exists("key.json"):
        print("❌ key.json file not found!")
        return False
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })
    return True

def start_vape9():
    print("🚀 Vape9 (베이프나인) 테스트 수집 시작 (1~2페이지)...")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/vape9')

    seen_names = set()

    try:
        # 1페이지부터 24페이지까지 순회
        for page in range(1, 25):
            url = f"https://vape9.co.kr/product/list.html?cate_no=101&page={page}"
            print(f"📖 Page {page} loading...")
            
            try:
                driver.get(url)
                time.sleep(5) # 콘텐츠 로딩 대기

                items = driver.find_elements(By.CSS_SELECTOR, ".prdList > li")
                if not items:
                    print(f"⚠️ No items found on page {page}.")
                    break

                save_count = 0
                for item in items:
                    try:
                        # 1. Product Name
                        name = ""
                        try:
                            # 스크린샷 기반: .name a span (폰트 사이즈 20px 스타일이 있는 span)
                            name_el = item.find_element(By.CSS_SELECTOR, ".name a span:not(.title)")
                            name = name_el.text.strip()
                        except: pass
                        
                        if not name:
                            try:
                                # Fallback: 이미지 alt값
                                img_el = item.find_element(By.CSS_SELECTOR, ".thumbnail img")
                                name = img_el.get_attribute("alt").strip()
                            except: pass

                        if not name or name in seen_names: continue

                        # 2. Image URL
                        image_url = ""
                        try:
                            img_el = item.find_element(By.CSS_SELECTOR, ".thumbnail img")
                            image_url = img_el.get_attribute("src")
                            if image_url.startswith("//"):
                                image_url = "https:" + image_url
                        except: pass

                        # 3. Price Extraction
                        price = 0
                        
                        # 스크린샷 기반: .discount_rate의 data-prod-price 속성 또는 특정 스타일의 span
                        try:
                            discount_el = item.find_element(By.CSS_SELECTOR, ".discount_rate")
                            price_str = discount_el.get_attribute("data-prod-price")
                            if price_str:
                                price = int(price_str)
                        except: pass

                        if price == 0:
                            try:
                                # Fallback: 가격 텍스트 추출 (7,900원 형식)
                                price_el = item.find_element(By.CSS_SELECTOR, ".product_price span")
                                txt = price_el.text
                                price = int(''.join(filter(str.isdigit, txt)) or 0)
                            except: pass

                        # 4. Save to Firebase
                        if name and price > 1000:
                            # Normalize key: alphanumeric only
                            safe_key = "".join(c for c in name if c.isalnum())
                            
                            ref.child(safe_key).update({
                                "name": name,
                                "price": price,
                                "image": image_url,
                                "site": "vape9",
                                "url": f"https://vape9.co.kr/product/detail.html?product_no={item.get_attribute('id').replace('anchorBoxName_', '')}", # ID에서 추출 시도
                                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            
                            # 상세 페이지 URL을 정확히 가져오기 위해 링크 요소 확인
                            try:
                                link_el = item.find_element(By.CSS_SELECTOR, ".name a")
                                full_url = link_el.get_attribute("href")
                                ref.child(safe_key).update({"url": full_url})
                            except: pass

                            print(f"   ✅ [저장] {name[:15]} | {price}원")
                            seen_names.add(name)
                            save_count += 1

                    except Exception as e:
                        # print(f"Error processing item: {e}")
                        continue
                
                print(f"✅ Page {page} done: {save_count} items saved.")

            except Exception as e:
                print(f"❌ Error while crawling page {page}: {e}")
                continue

        print("📊 Vape9 Crawling Completed!")

    finally:
        driver.quit()

if __name__ == "__main__":
    if init_firebase():
        start_vape9()
