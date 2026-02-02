import firebase_admin
from firebase_admin import credentials, db
import re
import difflib
import json
import os
import time
import traceback
import sys

# .env 파일 로드 함수 (외부 라이브러리 없이 구현)
def load_env():
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

# 환경변수 로드 실행
load_env()

# 1. Firebase 초기화
if not firebase_admin._apps:
    try:
        key_path = os.environ.get("FIREBASE_KEY_PATH", "key.json")
        db_url = os.environ.get("FIREBASE_DB_URL", "https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app")
        
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': db_url
        })
    except Exception as e:
        print(f"[WARN] Firebase Init Warning (Ignore locally): {e}")

# 2. 카테고리 키워드 정의
CATEGORIES = {
    "연초": ["시가", "타바코", "말보로", "던힐", "카멜", "마일드", "세븐", "버지니아", "클래식", "토바코", "구수한", "누룽지", "트리베카"],
    "디저트": ["치즈", "케이크", "케익", "크림", "커피", "바닐라", "초코", "초콜릿", "우유", "밀크", "카라멜", "팝콘", 
              "쿠키", "버터", "빵", "도넛", "푸딩", "아이스크림", "빙수", "요거트", "타르트", "마카롱", "커스터드"]
}

# 3. 불용어 리스트
JUNK_WORDS = [
    '입호흡', '폐호흡', '액상', 'csv', '기성', '모드', '솔트', 'nic', 's-nic', 'rs-nic', '합성', '천연', '줄기', 
    '특가', '이벤트', '재입고', '신규', 'best', 'new', 'hot', '추천', '인기', '초특가', '할인',
    '품절', '임박', '한정', '증정', '사은품', '코일', '팟', '기기', '탱크',
    '[', ']', '(', ')', '{', '}', '★', '☆', '🚀', '🔥', '👍', '!', '?', '-', '/', '+', '=', '_', '@', '#', '$', '%', '^', '&', '*'
]

# 브랜드/단어 통일 맵
WORD_MAP = {
    'flex': '플렉스', 'flexx': '플렉스', '플렉스x': '플렉스',
    'nasty': '네스티', 'vgod': '브이갓', 'tokyo': '도쿄', 'super': '슈퍼',
    'aloe': '알로에', 'grape': '포도', 'apple': '사과', '레몬': '레몬',
    'peach': '복숭아', 'berry': '베리', 'mint': '민트', 'menthol': '멘솔',
    '슬로우블로우': '슬로우블로우', '블로우슬로우': '슬로우블로우',
    '더블슬로우블로우': '더블슬로우블로우', '더블블로우슬로우': '더블슬로우블로우'
}

# 사이트 내부 키 -> 실제 이름 매핑
SITE_NAME_MAP = {
    'modu': '모두의액상', 'juice24': '액상24', 'tjf': '더쥬스팩토리',
    'siasiu': '샤슈컴퍼니', 'vapemonster': '베이프몬스터', 'juice99': '99액상'
}

def classify_category(name):
    name_lower = name.lower()
    for k in CATEGORIES["연초"]:
        if k in name_lower: return "연초"
    for k in CATEGORIES["디저트"]:
        if k in name_lower: return "디저트"
    return "과일/멘솔"

def clean_junk_text(text):
    text = re.sub(r'리뷰\s*\d+', ' ', text)
    text = re.sub(r'평점\s*\d+(\.\d+)?', ' ', text)
    text = re.sub(r'\(\d+\)', ' ', text)
    text = re.sub(r'하이민트|high\s*mint', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\d+(\.\d+)?\s*mg', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\d+(\.\d+)?\s*%', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'(^|\s)\d+(\.\d+)?(\s|$)', ' ', text)
    return text.strip()

CUSTOM_ALIASES = {}
try:
    with open("custom_aliases.json", "r", encoding="utf-8") as f:
        CUSTOM_ALIASES = json.load(f)
        print(f"[INFO] Custom Aliases Loaded: {len(CUSTOM_ALIASES)}")
except FileNotFoundError:
    pass

def normalize_product(raw_name):
    if raw_name in CUSTOM_ALIASES:
        raw_name = CUSTOM_ALIASES[raw_name]
    temp_name = raw_name.lower()
    
    event_suffix = ""
    if "1+1" in temp_name: event_suffix = " (1+1)"
    elif "2+1" in temp_name: event_suffix = " (2+1)"
    elif "3+1" in temp_name: event_suffix = " (3+1)"
    temp_name = temp_name.replace("1+1", "").replace("2+1", "").replace("3+1", "")
    temp_name = clean_junk_text(temp_name)
    
    temp_name = re.sub(r'flex\s*x', 'flex', temp_name, flags=re.IGNORECASE)
    temp_name = re.sub(r'플렉스\s*x', '플렉스', temp_name, flags=re.IGNORECASE)
    temp_name = temp_name.replace("더블 슬로우 블로우", "더블슬로우블로우").replace("더블 블로우 슬로우", "더블슬로우블로우")
    temp_name = temp_name.replace("슬로우 블로우", "슬로우블로우").replace("블로우 슬로우", "슬로우블로우")

    volume = "30ml"
    vol_match = re.search(r'(\d+)\s*ml', temp_name, re.IGNORECASE)
    if vol_match:
        volume = vol_match.group(1) + "ml"
        temp_name = re.sub(r'\d+\s*ml', ' ', temp_name, flags=re.IGNORECASE)
    
    extracted_brand = ""
    bracket_match = re.search(r'[\[\(](.*?)[\]\)]', temp_name)
    if bracket_match:
        extracted_brand = bracket_match.group(1).strip()
        temp_name = re.sub(r'[\[\(].*?[\]\)]', ' ', temp_name)
        
    for junk in JUNK_WORDS:
        temp_name = temp_name.replace(junk, ' ')
    
    tokens = temp_name.split()
    if extracted_brand:
        for junk in JUNK_WORDS: extracted_brand = extracted_brand.replace(junk, '')
        tokens = extracted_brand.split() + tokens

    final_tokens = []
    seen = set()
    for t in tokens:
        t_clean = re.sub(r'[^a-z0-9가-힣]', '', t)
        if not t_clean: continue
        t_mapped = WORD_MAP.get(t_clean, t_clean)
        for sub_t in t_mapped.split():
            if sub_t in JUNK_WORDS or sub_t == '0': continue
            if sub_t not in seen:
                seen.add(sub_t)
                final_tokens.append(sub_t)

    final_tokens.sort()
    clean_name = " ".join(final_tokens)
    clean_name = clean_name.replace("더블슬로우블로우", "더블 슬로우 블로우").replace("슬로우블로우", "슬로우 블로우")
    category = classify_category(clean_name)
    match_key = "".join(final_tokens) + volume + event_suffix.strip()
    
    if len(clean_name) < 2: display_name = raw_name
    else: display_name = f"{clean_name} {volume}{event_suffix}"

    # 4. 주요 브랜드명 맨 앞으로 이동 (사용자 요청)
    # 추가하고 싶은 브랜드가 있으면 이 리스트에 넣으세요.
    priority_brands = [
        "펠릭스", "이그니스", "네스티", "세븐코리아", "타이타닉", "동경", "슈퍼쿨", "잽쥬스", "알케마스터",
        "테일러", "플렉스", "브이갓", "노보", "베라쥬스", "오르카", "오지구", "타노스", "와이키키"
    ]
    
    for brand in priority_brands:
        if brand in clean_name:
            # 브랜드가 이름 중간에 있으면 제거하고 맨 앞에 붙임
            # 단, 이미 맨 앞에 있으면 무시 (startswith 체크)
            if not clean_name.startswith(brand):
                # 기존 브랜드명 제거 (공백 정리 포함)
                temp_name = clean_name.replace(brand, "").strip()
                # 맨 앞에 브랜드명 부착
                clean_name = f"{brand} {temp_name}"
            # 한 번 브랜드를 찾아서 처리했으면 루프 종료 (중복 브랜드 처리 방지)
            break
            
    # 정규화된 이름 생성
    display_name = f"{clean_name} {volume}{event_suffix}"
    match_key = clean_name.replace(" ", "") + volume + event_suffix.strip() # 매칭 키는 공백 제거

    return {
        "original": raw_name, "category": category,
        "volume": volume, "match_key": match_key,
        "display_name": display_name
    }

def process_data():
    print("[INFO] Fetching Firebase Data...")
    try:
        ref = db.reference('products')
        all_data = ref.get()
    except Exception as e:
        return {}, []
    
    if not all_data: return {}, []

    sites = ['modu', 'juice24', 'tjf', 'siasiu', 'vapemonster', 'juice99']
    merged_data = {}
    merged_data = {}
    print("[INFO] Normalizing & Merging Data...")
    
    for site in sites:
        site_data = all_data.get(site, {})
        for item_key, item_val in site_data.items():
            raw_name = item_val.get('name', '')
            price = item_val.get('price', 0)
            img = item_val.get('img') or item_val.get('image') or item_val.get('thumb') or ""
            link = item_val.get('link', '')

            if not raw_name or price <= 0: continue
            if img.startswith("//"): img = "https:" + img

            norm = normalize_product(raw_name)
            m_key = norm['match_key']

            if m_key not in merged_data:
                # [수정] Firebase의 제품별 views 노드에서 조회수를 가져옴
                global_item = all_data.get(m_key, {})
                views = global_item.get('views', 0) if isinstance(global_item, dict) else 0
                
                merged_data[m_key] = {
                    "display_name": norm['display_name'], "category": norm['category'],
                    "volume": norm['volume'], "image": img, "prices": {}, "views": views 
                }
            
            current_site_price = merged_data[m_key]["prices"].get(site, {}).get("price", 999999)
            if price < current_site_price:
                merged_data[m_key]["prices"][site] = { "price": price, "link": link }
            
            if not merged_data[m_key]["image"] and img:
                merged_data[m_key]["image"] = img
    
    try:
        with open("additional_images.json", "r", encoding="utf-8") as f:
            additional_images = json.load(f)
            for m_key, img_url in additional_images.items():
                if m_key in merged_data:
                     merged_data[m_key]['image'] = img_url
    except FileNotFoundError: pass

    return merged_data, sites

SEARCH_URLS = {
    'modu': "https://xn--hu1b83j3sfk9e3xc.kr/product/search.html?keyword=",
    'juice24': "https://juice24.kr/product/search.html?keyword=",
    'tjf': "https://www.tjf.kr/product/search.html?keyword=",
    'juice99': "https://99juice.co.kr/product/search.html?keyword=",
    'siasiu': "https://siasiu.com/product/search.html?keyword=", 
    'vapemonster': "https://vapemonster.co.kr/goods/goods_search.php?keyword="
}

def generate_report(data, sites):
    print("[INFO] Generating HTML Report...")
    import urllib.parse
    grid_items_html = ""
    
    # 기본 정렬: 판매처 많은 순 (내림차순)
    sorted_items = sorted(data.items(), key=lambda x: (len(x[1]['prices'])), reverse=True)
    
    for key, item in sorted_items:
        sorted_shops = sorted(item['prices'].items(), key=lambda x: x[1]['price'])
        min_price = 999999
        shops_html = ""
        
        for s_key, p_info in sorted_shops:
            p = p_info['price']
            l = p_info['link']
            if not l:
                query = urllib.parse.quote(item['display_name'])
                base = SEARCH_URLS.get(s_key, "")
                if base: l = f"{base}{query}"
            
            if p < min_price: min_price = p
            
            site_display_name = SITE_NAME_MAP.get(s_key, s_key.upper())
            shops_html += f"""
                <div class='shop-row'>
                    <span>{{site_display_name}}</span>
                    <a href='{{l}}' target='_blank' class='price-link' onclick="updateViews('{{key}}')">{{format(p, ',')}}원</a>
                </div>
            """
        
        # 판매처가 1개인 경우 바로 보낼 링크 준비
        single_link = ""
        if len(sorted_shops) == 1:
            # 1개일 때 그 링크 가져오기 (l 변수는 루프 마지막 값이라 위험, 명시적으로 접근)
            s_key_1, p_info_1 = sorted_shops[0]
            single_link = p_info_1['link']
            if not single_link: # 검색 링크 생성 로직 재사용 필요하나 복잡해지므로 여기선 단순 처리
                 import urllib.parse
                 q = urllib.parse.quote(item['display_name'])
                 b = SEARCH_URLS.get(s_key_1, "")
                 if b: single_link = f"{{b}}{{q}}"
        
        site_count = len(item['prices'])
        img_src = item['image'] if item['image'] else "assets/logo_placeholder.png"
        
        grid_items_html += f"""
        <div class="product-card" data-category="{item['category']}" data-price="{min_price}" data-views="{item.get('views', 0)}" data-sitecount="{site_count}" data-key="{key}">
            <div class="card-image">
                <img src="{img_src}" loading="lazy" alt="{item['display_name']}" 
                     onerror="this.onerror=null; this.src='https://raw.githubusercontent.com/juicepick/juicepick.github.io/master/assets/logo_placeholder.png';">
                <span class="category-tag {item['category']}">{item['category']}</span>
            </div>
            <div class="card-info">
                <h3 class="product-title">{item['display_name']}</h3>
                <div class="price-section">
                    <span class="label">최저가</span>
                    <span class="price-val">{format(min_price, ',')}원</span>
                </div>
                <button class="buy-btn" onclick="toggleShopList(this, '{key}', '{single_link}')">최저가 확인하기</button>
                <div class="shop-list">
                    {shops_html}
                </div>
                <div class="views-count">
                    <i class="fas fa-eye"></i> 조회 수: <span class="v-val">{item.get('views', 0)}</span>회
        </div>
        """

    # [NEW] 추천 시스템 로직 (사진 있고 조회수 높고 판매처 많은 순)
    # 1. 사진이 있는 상품 필터 (logo_placeholder 제외)
    has_img_items = [
        (k, i) for k, i in data.items() 
        if i.get('image') and 'logo_placeholder' not in i.get('image')
    ]
    # 2. 조회수 높고 판매처 많은 순으로 정렬
    recommended_items = sorted(has_img_items, key=lambda x: (x[1].get('views', 0), len(x[1]['prices'])), reverse=True)[:3]
    
    # 추천 HTML 생성
    featured_html = ""
    for idx, (r_key, r_item) in enumerate(recommended_items):
        rank_badge = f'<div style="padding: 5px 10px; background: var(--primary); color: white; font-weight: bold; position: absolute; top: 0; left: 0; z-index: 10;">👑 추천 {idx+1}위</div>' if idx == 0 else ""
        cat_class = r_item['category'].replace('/', '-')
        
        # 최저가 찾기
        r_min_price = min([p['price'] for p in r_item['prices'].values()])
        
        featured_html += f"""
                <div class="product-card" style="position: relative;">
                    {rank_badge}
                    <div class="card-image">
                        <img src="{r_item['image']}" alt="{r_item['display_name']}">
                        <span class="category-tag {cat_class}">{r_item['category']}</span>
                    </div>
                    <div class="card-info">
                        <h3 class="product-title">{r_item['display_name']}</h3>
                        <div class="price-section"><span class="price-val">{format(r_min_price, ',')}원~</span></div>
                        <button class="buy-btn" onclick="document.getElementById('searchInput').value='{r_item['display_name']}'; applyFilters();">가격 비교하기</button>
                    </div>
                </div>
        """

    # Firebase URL 가져오기 (환경변수 또는 기본값)
    db_url = os.environ.get("FIREBASE_DB_URL", "https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app")

    # 캐시 버스팅을 위한 버전키 생성 (현재 시간)
    version_key = str(int(time.time()))

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="국내외 인기 전자담배 액상 가격비교, 입호흡/폐호흡 액상 최저가 찾기 및 사용자 취향 기반 맞춤 추천 서비스.">
        <meta name="keywords" content="전자담배 액상 가격비교, 전담 액상 최저가, 액상 추천, 액상픽">
        <meta property="og:title" content="액상픽 - 전자담배 액상 가격비교 및 맞춤 추천 서비스">
        <meta property="og:type" content="website">

        <title>액상픽 - 전자담배 액상 가격비교 및 맞춤 추천 서비스</title>
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8789660340754359" crossorigin="anonymous"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js"></script>
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-database.js"></script>

        <link rel="manifest" href="manifest.json">
        <meta name="theme-color" content="#00a8ff">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="google-site-verification" content="oLmPfN2woDE_ChJzzVEV52goZJxhvC-theDmEock-vQ" />
        
        <!-- Favicon & OG Image -->
        <link rel="icon" type="image/png" href="assets/favicon.png?v={version_key}">
        <meta property="og:image" content="https://raw.githubusercontent.com/juicepick/juicepick.github.io/master/assets/og_image.png">
        
        <!-- Main CSS (Relative Path with Version) -->
        <link rel="stylesheet" href="assets/style.css?v={version_key}">
    </head>
    <body data-theme="light">
        <header>
            <nav class="nav-container">
                <a href="index.html" class="site-name">액상픽</a>
                <ul class="nav-menu">
                    <li><a href="blog/index.html">가이드</a></li>
                    <li><a href="board.html">자유게시판</a></li>
                    <li><a href="about.html">서비스소개</a></li>
                    <li><button onclick="toggleTheme()" class="theme-toggle" aria-label="테마 전환"><i class="fas fa-moon" id="theme-icon"></i></button></li>
                </ul>
            </nav>
        </header>

        <section class="hero">
            <div class="hero-content">
                <h1 class="hero-title">
                    <span class="highlight">전자담배 액상 가격비교</span>의 모든 것<br>
                    원하는 맛을 최저가로 찾아보세요
                </h1>
                <div class="search-container">
                    <input type="text" id="searchInput" class="search-input" placeholder="액상 이름 검색 (예: 알로에, 갱쥬스)..." onkeyup="if(event.key === 'Enter') applyFilters()">
                    <button class="search-btn" onclick="applyFilters()"><i class="fas fa-search"></i> 검색</button>
                </div>
            </div>
        </section>

        <!-- [DYNAMIC] 추천 인기 액상 -->
        <section class="featured-section" style="max-width: 1200px; margin: 40px auto 20px; padding: 0 20px;">
            <h2 style="font-size: 24px; margin-bottom: 20px; color: var(--text);">🔥 실시간 인기 급상승 액상 TOP 3</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
                {featured_html}
            </div>
        </section>
        <main>
            <div class="toolbar">
                <div class="cat-filters">
                    <button class="filter-btn active" onclick="filterCategory('all', this)">전체</button>
                    <button class="filter-btn" onclick="filterCategory('과일/멘솔', this)">과일/멘솔</button>
                    <button class="filter-btn" onclick="filterCategory('연초', this)">연초</button>
                    <button class="filter-btn" onclick="filterCategory('디저트', this)">디저트</button>
                </div>
                <div class="sort-options">
                    <select id="sortSelect" onchange="sortData()">
                        <option value="site-desc">일반순 (판매처 많은순)</option>
                        <option value="views">인기순 (조회수)</option>
                        <option value="price-asc">가격 낮은순</option>
                        <option value="name">이름순</option>
                    </select>
                </div>
            </div>

            <div class="product-grid" id="productGrid">
                {grid_items_html}
            </div>
            <div id="pagination" class="pagination"></div>

            <section class="seo-content">
                <div style="max-width: 1200px; margin: 0 auto;">
                    <h2>💡 스마트한 베이퍼들의 선택, 액상픽(Juice Pick)</h2>
                    <p style="margin-bottom: 15px; line-height: 1.6;">
                        <strong>액상픽(Juice Pick)</strong>은 대한민국 전자담배 사용자들이 더 합리적이고 편리하게 액상을 구매할 수 있도록 돕는 <strong>국내 최대 규모의 액상 가격비교 플랫폼</strong>입니다. 
                        수많은 온라인 쇼핑몰에 흩어져 있는 가격 정보를 일일이 찾아다니는 번거로움을 덜어드리기 위해, 우리는 실시간으로 데이터를 수집하고 분석하여 최신의 최저가 정보를 제공하고 있습니다.
                    </p>
                    <p style="margin-bottom: 15px; line-height: 1.6;">
                        '과일 멘솔', '연초', '디저트' 등 사용자의 다양한 취향을 고려한 정밀한 카테고리 분류와 강력한 검색 엔진을 통해, 입문자부터 숙련된 베이퍼까지 누구나 쉽고 빠르게 원하는 제품을 찾을 수 있습니다. 
                        단순히 가격만 비교하는 것을 넘어, 실제 판매처 수와 조회수를 기반으로 한 <strong>인기 트렌드 분석</strong>을 통해 실패 없는 액상 선택을 도와드립니다.
                    </p>
                    <p style="line-height: 1.6;">
                        액상픽은 투명한 정보 공개를 통해 건전한 베이핑 문화를 선도합니다. 불필요한 마케팅 거품을 걷어내고, 오직 품질과 가격 경쟁력으로 승부하는 우수한 판매처들을 발굴하여 여러분께 소개해 드립니다.
                        매일 업데이트되는 3,000개 이상의 액상 데이터베이스와 함께, 당신의 인생 액상을 가장 저렴한 가격에 만나보세요. 
                    </p>
                </div>
            </section>
        </main>
        
        <div id="loading-spinner"><div class="spinner"></div><p style="color:#fff;">로딩중...</p></div>
        <div id="ios-prompt">
            <span class="close-btn" onclick="document.getElementById('ios-prompt').style.display='none'">&times;</span>
            <div style="color:var(--sky-blue); font-weight:800; margin-bottom:5px;">앱으로 이용하기</div>
            아이폰 사파리 하단의 <b>공유 버튼</b>을 누르고 <b>'홈 화면에 추가'</b>를 선택하세요.
        </div>

        <footer>
            <div class="footer-content">
                <div class="footer-section">
                    <h4>액상픽 (JuicePick)</h4>
                    <p style="margin-bottom: 15px;">대한민국 No.1 전자담배 액상 최저가 검색 포털</p>
                    <div class="footer-links">
                        <a href="blog/index.html">블로그</a> | 
                        <a href="about.html">서비스소개</a> | 
                        <a href="terms.html">이용약관</a> | 
                        <a href="privacy.html" style="font-weight:bold;">개인정보처리방침</a> | 
                        <a href="mailto:contact@juicepick.github.io">제휴/광고 문의</a>
                    </div>
                </div>
                <div class="footer-section">
                    <h4>책임의 한계와 고지</h4>
                    <p style="font-size: 13px; color: #7f8c8d; line-height: 1.5;">
                        액상픽은 통신판매중개자로서 쇼핑몰의 상품 정보와 가격을 수집하여 제공할 뿐, 해당 상품의 주문, 배송, 환불에 대한 의무와 책임은 각 판매처에 있습니다. 
                        상품 정보에 대한 문의는 각 판매 사이트로 연락해 주시기 바랍니다.
                    </p>
                </div>
            </div>
            <p style="text-align:center; margin-top:40px; font-size:12px; color:#777; border-top: 1px solid #353b48; padding-top: 20px;">
                &copy; 2026 JuicePick. All rights reserved. Powered by JuiceHunter Engine.
                <br><span style="opacity: 0.5;">Build: {version_key}</span>
            </p>
        </footer>

        <script>
            // Firebase Config Injection
            const firebaseConfig = {{
                databaseURL: "{db_url}"
            }};
            // Initialize Firebase
            if (!firebase.apps.length) {{
                firebase.initializeApp(firebaseConfig);
            }}

            let allCards = [];
            let filteredCards = [];
            let currentPage = 1;
            const itemsPerPage = 52;
            let currentCategory = 'all';

            window.onload = function() {{
                const grid = document.getElementById('productGrid');
                allCards = Array.from(grid.children);
                filteredCards = [...allCards];
                
                // [NEW] 실시간 조회수 동기화 logic
                syncRealtimeViews();

                if ('serviceWorker' in navigator) {{
                    // GH Pages 캐시를 뚫기 위해 버전 쿼리 스트링 다시 도입
                    navigator.serviceWorker.register('sw.js?v={version_key}').then(reg => {{
                        reg.update(); // 매 로드 시 업데이트 확인

                        reg.onupdatefound = () => {{
                            const installingWorker = reg.installing;
                            installingWorker.onstatechange = () => {{
                                if (installingWorker.state === 'installed') {{
                                    if (navigator.serviceWorker.controller) {{
                                        showUpdateNotification();
                                    }}
                                }}
                            }};
                        }};
                    }});
                }}
                
                // [NEW] 버전 체크 logic (강제 새로고침 유도)
                checkVersionSync('{version_key}');

                initTheme();
                checkIOS();
                sortData();
            }};

            // [NEW] Firebase 실시간 조회수 동기화
            function syncRealtimeViews() {{
                if (!firebase || !firebase.database) return;
                const dbRef = firebase.database().ref('products');
                
                dbRef.on('value', (snapshot) => {{
                    const data = snapshot.val();
                    if (!data) return;
                    
                    document.querySelectorAll('.product-card[data-key]').forEach(card => {{
                        const key = card.dataset.key;
                        if (data[key] && data[key].views !== undefined) {{
                            const views = data[key].views;
                            card.dataset.views = views;
                            const vValNode = card.querySelector('.v-val');
                            if (vValNode) vValNode.innerText = views;
                        }}
                    }});
                }});
            }}

            // [NEW] 버전 체크 (LocalStorage 기반 강제 새로고침)
            function checkVersionSync(currentVersion) {{
                const savedVersion = localStorage.getItem('site_version');
                if (savedVersion && savedVersion !== currentVersion) {{
                    console.log('New version detected:', currentVersion);
                    localStorage.setItem('site_version', currentVersion);
                    // 1초 후 강제 새로고침 (캐시 무시)
                    setTimeout(() => {{
                        window.location.reload(true);
                    }}, 1000);
                }} else {{
                    localStorage.setItem('site_version', currentVersion);
                }}
            }}
            function showUpdateNotification() {{
                    const notify = document.createElement('div');
                    notify.style.cssText = `
                        position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
                        background: var(--primary); color: white; padding: 15px 25px;
                        border-radius: 50px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        z-index: 10000; display: flex; align-items: center; gap: 15px;
                        font-weight: 600; font-family: 'Pretendard', sans-serif;
                    `;
                    notify.innerHTML = `
                        <span>✨ 새로운 버전이 준비되었습니다!</span>
                        <button id="updateBtn" style="
                            background: white; color: var(--primary); border: none;
                            padding: 5px 15px; border-radius: 20px; cursor: pointer;
                            font-weight: 800;
                        ">업데이트</button>
                    `;
                    document.body.appendChild(notify);
                    
                    document.getElementById('updateBtn').onclick = () => {{
                        if (navigator.serviceWorker.controller) {{
                             navigator.serviceWorker.controller.postMessage({{ type: 'SKIP_WAITING' }});
                        }}
                        // 200ms 후 리로드
                        setTimeout(() => window.location.reload(), 200);
                    }};
                }}
                
                initTheme();
                checkIOS();
                sortData();
            }};

            // [수정] 기본 테마: 라이트모드 고정 (시스템 설정 무시)
            function initTheme() {{
                const savedTheme = localStorage.getItem('theme');
                // 저장된 값이 'dark'일 때만 다크모드. 그 외엔 무조건 라이트 (prefers-color-scheme 무시)
                if (savedTheme === 'dark') {{
                    document.documentElement.setAttribute('data-theme', 'dark');
                    document.getElementById('theme-icon').className = 'fas fa-sun';
                }} else {{
                    document.documentElement.removeAttribute('data-theme');
                    document.getElementById('theme-icon').className = 'fas fa-moon';
                }}
            }}

            function toggleTheme() {{
                const doc = document.documentElement;
                const icon = document.getElementById('theme-icon');
                if (doc.getAttribute('data-theme') === 'dark') {{
                    doc.removeAttribute('data-theme');
                    localStorage.setItem('theme', 'light');
                    icon.className = 'fas fa-moon';
                }} else {{
                    doc.setAttribute('data-theme', 'dark');
                    localStorage.setItem('theme', 'dark');
                    icon.className = 'fas fa-sun';
                }}
            }}

            function checkIOS() {{
                const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
                const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
                if (isIos && !isStandalone) {{
                    setTimeout(() => {{
                         document.getElementById('ios-prompt').style.display = 'block';
                    }}, 2000);
                }}
            }}

            // 통합 필터 함수 (검색어 + 카테고리)
            function applyFilters() {{
                const query = document.getElementById('mainSearch').value.toLowerCase().replace(/\\s+/g, '');
                const spinner = document.getElementById('loading-spinner');
                spinner.style.display = 'flex';

                setTimeout(() => {{
                    filteredCards = allCards.filter(card => {{
                        // 카테고리 매칭
                        const catMatch = (currentCategory === 'all') || (card.dataset.category === currentCategory);
                        
                        // 검색어 매칭
                        const title = card.querySelector('.product-title').innerText.toLowerCase().replace(/\\s+/g, '');
                        const searchMatch = title.includes(query);

                        return catMatch && searchMatch;
                    }});
                    
                    sortData(false); // sortData 내부 타임아웃 방지
                    spinner.style.display = 'none';
                }}, 100);
            }}

            function executeSearch() {{
                currentPage = 1;
                applyFilters();
            }}

            function sortData(useTimeout = true) {{
                const sortType = document.getElementById('sortSelect').value;
                
                const execSort = () => {{
                    filteredCards.sort((a, b) => {{
                        if (sortType === 'price-asc') {{
                            return parseInt(a.dataset.price) - parseInt(b.dataset.price);
                        }} else if (sortType === 'views') {{
                            return parseInt(b.dataset.views) - parseInt(a.dataset.views);
                        }} else if (sortType === 'name') {{
                             return a.querySelector('.product-title').innerText.localeCompare(b.querySelector('.product-title').innerText);
                        }} else {{
                            return parseInt(b.dataset.sitecount) - parseInt(a.dataset.sitecount);
                        }}
                    }});
                    
                    currentPage = 1;
                    renderCards();
                }};

                if (useTimeout) {{
                    const spinner = document.getElementById('loading-spinner');
                    spinner.style.display = 'flex';
                    setTimeout(() => {{
                        execSort();
                        spinner.style.display = 'none';
                    }}, 100);
                }} else {{
                    execSort();
                }}
            }}

            // [기능 추가] 조회수 증가 함수 (Firebase)
            function updateViews(key) {{
                if (!firebase || !firebase.database) return;
                const dbRef = firebase.database().ref('products/' + key + '/views');
                dbRef.transaction(currentViews => {{
                    return (currentViews || 0) + 1;
                }}).catch(err => console.error("Views update failed", err));
            }}

            // [기능 추가] 상점 목록 토글 또는 바로가기
            function toggleShopList(btn, key, linkIfOne) {{
                // 만약 linkIfOne이 존재하면 (판매처가 1곳인 경우), 목록 열지 않고 바로 이동
                if (linkIfOne && linkIfOne !== 'null' && linkIfOne !== '') {{
                    updateViews(key);
                    window.open(linkIfOne, '_blank');
                    return;
                }}

                // 판매처가 여러 곳이면 목록 토글
                const list = btn.nextElementSibling;
                list.classList.toggle('active');
                if (list.classList.contains('active')) {{
                    btn.textContent = '목록 닫기';
                }} else {{
                    btn.textContent = '최저가 확인하기';
                }}
            }}

            function filterCategory(cat, btn) {{
                currentCategory = cat;
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // 검색어 유지한 채로 카테고리 변경
                applyFilters();
            }}

            function renderCards() {{
                const grid = document.getElementById('productGrid');
                grid.innerHTML = ''; 

                const start = (currentPage - 1) * itemsPerPage;
                const end = start + itemsPerPage;
                const pageItems = filteredCards.slice(start, end);

                pageItems.forEach(card => {{
                    grid.appendChild(card);
                }});
                
                renderPagination();
                window.scrollTo(0, 0);
            }}

            function renderPagination() {{
                const pagination = document.getElementById('pagination');
                pagination.innerHTML = '';
                
                const totalPages = Math.ceil(filteredCards.length / itemsPerPage);
                if (totalPages <= 1) return;

                const currentGroup = Math.ceil(currentPage / 10);
                const startPage = (currentGroup - 1) * 10 + 1;
                const endPage = Math.min(startPage + 9, totalPages);

                if (startPage > 1) {{
                    const btn = createPageBtn('<', startPage - 1);
                    pagination.appendChild(btn);
                }}

                for (let i = startPage; i <= endPage; i++) {{
                    const btn = createPageBtn(i, i);
                    if (i === currentPage) btn.classList.add('active');
                    pagination.appendChild(btn);
                }}

                if (endPage < totalPages) {{
                    const btn = createPageBtn('>', endPage + 1);
                    pagination.appendChild(btn);
                }}
            }}

            function createPageBtn(text, pageNum) {{
                const btn = document.createElement('button');
                btn.className = 'page-btn';
                btn.innerText = text;
                btn.onclick = () => {{
                    currentPage = pageNum;
                    renderCards();
                }};
                return btn;
            }}


        </script>
    </body>
    </html>
    """

    filename = "index.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"[SUCCESS] Portal Style Report Generated: {filename}")

if __name__ == "__main__":
    try:
        merged_data, sites = process_data()
        if merged_data:
            generate_report(merged_data, sites)
        else:
            print("[ERROR] No data to generate.")
            # Create a simple fallback page so deployment doesn't completely fail
            with open("index.html", "w", encoding="utf-8") as f:
                f.write("<h1>Build Failed: No Data Found</h1>")
    except Exception:
        # Catch ALL errors and write to index.html so we can see them on the live site
        err_msg = traceback.format_exc()
        print(f"[CRITICAL ERROR] {err_msg}")
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(f"<h1>Build Site Critical Error</h1><pre>{err_msg}</pre>")
        # Exit 0 to allow deployment to proceed so we can read the error
        sys.exit(0)