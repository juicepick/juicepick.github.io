
import sys
import os

# Ensure we can import build_site
sys.path.append(os.getcwd())

try:
    import build_site
except ImportError:
    print("Error: Could not import build_site.py")
    sys.exit(1)

def test_case(name, expected, description):
    result = build_site.classify_category(name)
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] {description}: '{name}' -> Got '{result}', Expected '{expected}'")

print("--- Verifying Fix in build_site.py ---")

# Test Cases
test_case("세븐코리아 포카리", "과일/멘솔", "Brand 'Seven Korea' should be ignored for 연초 trigger")
test_case("레드 세븐데이즈 애플", "과일/멘솔", "Brand 'Seven Days' should be ignored for 연초 trigger")
test_case("마일드 세븐", "연초", "Real Tobacco product 'Mild Seven' should stay 연초")
test_case("세븐 믹스", "연초", "Generic 'Seven' should trigger 연초 if not exception")
test_case("알로에 베라", "과일/멘솔", "Standard Fruit check")
test_case("치즈 케이크", "디저트", "Standard Dessert check")
test_case("세븐리퀴드 포도", "과일/멘솔", "Brand 'Seven Liquid' should be ignored for 연초 trigger")

print("--- Verification Complete ---")
