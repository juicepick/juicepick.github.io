
with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

targets = ["12,900", "8,000"]

with open('debug_output_3.txt', 'w', encoding='utf-8') as out:
    for target in targets:
        out.write(f"\n=== Searching for {target} ===\n")
        count = 0
        for i, line in enumerate(lines):
            if target in line:
                for j in range(i, max(0, i - 40), -1):
                    if '<div class="product-card"' in lines[j]:
                        out.write(f"FOUND CARD at line {j+1}:\n")
                        out.write(lines[j].strip() + "\n")
                        for k in range(j, i+5):
                            if 'product-title' in lines[k]:
                                out.write(f"  Title: {lines[k].strip()}\n")
                        out.write("-" * 30 + "\n")
                        count += 1
                        break
                if count >= 3: break
