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

def start_juicebox():
    print("🚀 Juicebox (쥬스박스) Full Crawling Started (1 to 53 Pages)")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("--headless")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/juicebox')

    try:
        # 1페이지부터 53페이지까지 순회
        # 실시간 웹사이트 상황에 따라 페이지 수가 변할 수 있으므로 에러 처리 포함
        for page in range(1, 54):
            url = f"https://juicebox.co.kr/product/list.html?cate_no=52&page={page}"
            print(f"📖 Page {page}/53 loading...")
            
            try:
                driver.get(url)
                time.sleep(3) # Wait for content to load

                items = driver.find_elements(By.CSS_SELECTOR, ".prdList > li")
                if not items:
                    print(f"⚠️ No items found on page {page}. Finalizing.")
                    break

                save_count = 0
                for i, item in enumerate(items):
                    try:
                        # 1. Product Name (Strict use of Image Alt)
                        name = ""
                        try:
                            img_el = item.find_element(By.CSS_SELECTOR, ".thumbnail img, .prdImg img")
                            name = img_el.get_attribute("alt").strip()
                        except: pass
                        
                        if not name or "상품명" in name:
                             # Fallback to name span if alt is missing or is just a label
                             try:
                                 name_el = item.find_element(By.CSS_SELECTOR, ".name a span:not(.title), .description .name span:not(.title)")
                                 name = name_el.text.strip()
                             except: pass

                        # [FIX] '이미지' 문자 제거 (병합 문제 해결)
                        if name:
                            name = name.replace('이미지', '').strip()
                            name = re.sub(r'\s+', ' ', name)  # 중복 공백 제거

                        if not name: continue

                        # 2. Price Extraction (Strict 'Won' anchor)
                        price = 0
                        
                        def extract_p(txt):
                            match = re.search(r'([\d,]+)\s*원', txt)
                            if match:
                                return int(match.group(1).replace(',', ''))
                            return 0

                        # Check sale price column first
                        try:
                            spans = item.find_elements(By.CSS_SELECTOR, "li[column_name='product_price'] span")
                            for s in spans:
                                p = extract_p(s.get_attribute("innerText"))
                                if p > 0:
                                    price = p
                                    break
                        except: pass

                        # Fallback to general price spans
                        if price == 0:
                            try:
                                spans = item.find_elements(By.CSS_SELECTOR, "li[column_name='price_unit'] span, .price span")
                                for s in spans:
                                    p = extract_p(s.get_attribute("innerText"))
                                    if p > 0:
                                        price = p
                                        break
                            except: pass

                        # 3. Save to Firebase
                        if name and price > 1000:
                            # Normalize key: alphanumeric only
                            safe_key = "".join(c for c in name if c.isalnum())
                            
                            ref.child(safe_key).update({
                                "name": name,
                                "price": price,
                                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            save_count += 1

                    except Exception:
                        continue
                
                print(f"✅ Page {page} done: {save_count} items saved.")

            except Exception as e:
                print(f"❌ Error while crawling page {page}: {e}")
                continue

        print("📊 Juicebox Crawling Completed Successfully!")

    finally:
        driver.quit()

if __name__ == "__main__":
    if init_firebase():
        start_juicebox()
