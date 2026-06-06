import sys, re
sys.path.insert(0, r'd:\Games\007 First Light\localization')

# Exec trực tiếp file để lấy should_skip vào namespace hiện tại
exec(open(r'd:\Games\007 First Light\localization\translate_ui_ai.py', encoding='utf-8').read())

# Test các string từ ảnh screenshot
test_cases = [
    # Tên riêng — phải skip
    ('Bond', True),
    ('Moneypenny', True),
    ('Greenway', True),
    ('Q-Watch', True),
    ('Hack', True),
    ('Android', True),
    ('Monroe', True),
    ('Basim', True),
    # Token — phải skip
    ("['UI_ControllerLayout_shoulderLalt']", True),
    ('{Hold}', True),
    ('{Press}', True),
    # String thực sự cần dịch — KHÔNG skip
    ('Game has been tampered with. Returning to main menu.', False),
    ('Overwrite save file', False),
    ('Load save file', False),
    ('Do you wish to proceed to the Microsoft Store?', False),
    ('Corrupted save file', False),
    ('Invalid save file', False),
    ('Exit to the title screen', False),
]

print("=== TEST should_skip ===")
all_pass = True
for text, expected_skip in test_cases:
    result = should_skip(text)
    status = "✓" if result == expected_skip else "✗ FAIL"
    if result != expected_skip:
        all_pass = False
    print(f"  {status} skip={result} (expect {expected_skip}): {repr(text[:50])}")

print()
if all_pass:
    print("ALL PASS ✓")
else:
    print("CÓ LỖI ✗")

# Đếm thực tế strings cần dịch lại trong ui.json
import json
src  = json.load(open(r'd:\Games\007 First Light\localization\extracted\ui.json', encoding='utf-8'))
out  = json.load(open(r'd:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\translations\ui.json', encoding='utf-8'))

truly_needed = []
for ok, ov in src.items():
    for ik, text in ov.items():
        if should_skip(text):
            continue
        vi = out.get(ok, {}).get(ik, text)
        if vi == text:  # chưa dịch
            truly_needed.append(text)

print(f"\nStrings thực sự còn cần dịch: {len(truly_needed)}")
for t in truly_needed[:20]:
    print(f"  {repr(t[:80])}")
