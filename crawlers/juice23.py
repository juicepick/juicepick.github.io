"""
이삼액상 (23juice.kr) 크롤러
입호흡 액상 카테고리에서 상품 정보를 수집합니다.
"""

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
        print("❌ key.json 파일을 찾을 수 없습니다!")
        return False
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })
    return True

def start_juice23():
    print("🚀 이삼액상 (23juice.kr) 크롤링 시작...")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/juice23')

    seen_names = set()
    total_saved = 0

    try:
        # 페이지 순회 (최대 20페이지까지 시도)
        for page in range(1, 21):
            url = f"https://23juice.kr/product/list.html?cate_no=23&page={page}"
            print(f"📖 {page}페이지 로딩 중...")
            
            try:
                driver.get(url)
                time.sleep(4)  # 콘텐츠 로딩 대기

                # 상품 목록 찾기 - xans-product-listitem 내부의 li 요소들
                items = driver.find_elements(By.CSS_SELECTOR, "ul.xans-product-listnormal li")
                
                if not items:
                    # 다른 선택자 시도
                    items = driver.find_elements(By.CSS_SELECTOR, ".prdList li")
                    
                if not items:
                    print(f"⚠️ {page}페이지에서 상품을 찾을 수 없습니다. 크롤링 종료.")
                    break

                save_count = 0
                for item in items:
                    try:
                        # 1. 상품명 추출
                        name = ""
                        try:
                            # 상품명 링크에서 텍스트 추출
                            name_el = item.find_element(By.CSS_SELECTOR, ".name a")
                            name = name_el.text.strip()
                            # "상품명 : " 접두사 제거
                            if name.startswith("상품명 :"):
                                name = name.replace("상품명 :", "").strip()
                        except: pass
                        
                        if not name:
                            try:
                                # Fallback: 이미지 alt값
                                img_el = item.find_element(By.CSS_SELECTOR, "img")
                                name = img_el.get_attribute("alt").strip()
                            except: pass

                        if not name or name in seen_names: continue
                        
                        # 묶음상품이나 특수 상품은 제외
                        if "묶음" in name or "SET" in name or "문의" in name:
                            continue

                        # 2. 이미지 URL 추출 (개선)
                        image_url = ""
                        try:
                            # 썸네일 전용 컨테이너 내의 이미지만 타겟팅
                            img_els = item.find_elements(By.CSS_SELECTOR, ".thumbnail img, .prdImg img, .thumb img")
                            for img_el in img_els:
                                src = img_el.get_attribute("src")
                                if src and "icon" not in src.lower() and "btn" not in src.lower() and "common" not in src.lower():
                                    image_url = src
                                    break
                            
                            if image_url:
                                if image_url.startswith("//"):
                                    image_url = "https:" + image_url
                                elif image_url.startswith("/"):
                                    image_url = "https://23juice.kr" + image_url
                                elif not image_url.startswith("http"):
                                    image_url = "https://23juice.kr/" + image_url
                        except: pass

                        # 3. 가격 추출 (대수술: 할인가 우선)
                        price = 0
                        try:
                            full_text = item.text.replace(',', '').replace(' ', '')
                            # 패턴 1: 판매가라는 텍스트가 포함된 금액 (최우선)
                            # 예: "판매가:9900원" 또는 "9900원판매가"
                            sale_match1 = re.search(r'판매가:?(\d+)원', full_text)
                            sale_match2 = re.search(r'(\d+)원판매가', full_text)
                            
                            if sale_match1:
                                price = int(sale_match1.group(1))
                            elif sale_match2:
                                price = int(sale_match2.group(1))
                            else:
                                # 패턴 2: 소비자가를 제외한 금액 찾기
                                # 텍스트에서 소비자가 부분을 제거하고 남은 금액 중 가장 큰 금액 (또는 마지막 금액)
                                clean_text = re.sub(r'소비자가:?\d+원', '', full_text)
                                all_prices = re.findall(r'(\d+)원', clean_text)
                                if all_prices:
                                    # 보통 리스트에서 마지막에 나오는게 판매가인 경우가 많음 (할인가)
                                    price = int(all_prices[-1])
                        except Exception as e:
                            print(f"Price error: {e}")
                            pass

                        if price <= 0: continue

                        # 4. 상품 URL 추출
                        product_url = ""
                        try:
                            link_el = item.find_element(By.CSS_SELECTOR, "a[href*='product_no']")
                            product_url = link_el.get_attribute("href")
                        except: pass

                        # Firebase에 저장
                        seen_names.add(name)
                        key = re.sub(r'[^a-zA-Z0-9가-힣]', '', name)[:50]
                        
                        ref.child(key).set({
                            'name': name,
                            'price': price,
                            'image': image_url,
                            'url': product_url,
                            'site': 'juice23'
                        })
                        save_count += 1

                    except Exception as e:
                        continue

                total_saved += save_count
                print(f"✅ {page}페이지: {save_count}개 상품 저장 완료")
                
                # 상품이 없거나 너무 적으면 마지막 페이지로 판단
                if save_count == 0 and page > 1:
                    print("📝 더 이상 새 상품이 없습니다. 크롤링 종료.")
                    break

            except Exception as e:
                print(f"❌ {page}페이지 처리 중 오류: {e}")
                continue

    finally:
        driver.quit()
        print(f"\n🎉 이삼액상 크롤링 완료! 총 {total_saved}개 상품 저장됨")

if __name__ == "__main__":
    if init_firebase():
        start_juice23()
