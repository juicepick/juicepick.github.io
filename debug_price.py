
import build_site
import firebase_admin
from firebase_admin import credentials, db
import os
import re

# Patch env load if needed, or assume build_site loaded it
if not os.environ.get("FIREBASE_KEY_PATH"):
    build_site.load_env()

def mock_process_and_check():
    merged_data, sites = build_site.process_data()
    
    print("\n--- CHECKING PRICE DATA TYPES ---")
    problematic_found = False
    
    # Check specific items from the screenshot if possible (search by name)
    target_keywords = ["네스티 아이스 파인애플", "노보 블루펀치"]
    
    for key, item in merged_data.items():
        display_name = item['display_name']
        
        # Check if targets from screenshot match
        is_target = any(k in display_name for k in target_keywords)
        
        # Check price types in min_price logic
        sorted_shops = sorted(item['prices'].items(), key=lambda x: x[1]['price'])
        if not sorted_shops: continue
        
        min_price = 999999
        min_p_val = 999999
        
        for s_key, p_info in sorted_shops:
            p = p_info['price']
            if not isinstance(p, int):
                print(f"[FAIL] Price is NOT int: {display_name} -> {p} ({type(p)})")
                problematic_found = True
            
            if p < min_price: min_price = p

        if is_target:
            print(f"[TARGET] {display_name}")
            print(f"   Category: {item['category']}")
            print(f"   Min Price: {min_price} (Type: {type(min_price)})")
            print(f"   Prices: {item['prices']}")

    print("--- PRICE CHECK COMPLETE ---")

if __name__ == "__main__":
    if not firebase_admin._apps:
         # Repo-init code from build_site - slightly modified to run here
         pass
    mock_process_and_check()
