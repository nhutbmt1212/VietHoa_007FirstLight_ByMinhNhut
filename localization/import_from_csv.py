"""
import_from_csv.py
------------------
Đọc file CSV đã dịch (cột 'vietnamese' đã được điền),
ghi bản dịch tiếng Việt vào ngôn ngữ đích trong các file JSON LOCR,
sau đó sẵn sàng để rebuild bằng rpkg-cli.

Cách dùng:
    python import_from_csv.py

Config bên dưới:
    TARGET_LANG  — ngôn ngữ bị ghi đè bằng tiếng Việt (mặc định: "schinese"
                   vì Chinese Simplified ít dùng nhất trong game Hitman/007)
    COPY_MISSING — nếu True, những chuỗi chưa dịch sẽ giữ nguyên bản gốc
"""

import json
import csv
import os
import glob
import shutil

LOCR_DIR   = os.path.join(os.path.dirname(__file__), "LOCR")
INPUT_CSV  = os.path.join(os.path.dirname(__file__), "translation_export.csv")

# Ngôn ngữ sẽ bị thay thế bằng tiếng Việt.
# Chọn ngôn ngữ ít dùng hoặc không cần thiết trong game.
# Sau đó vào Settings game chọn đúng ngôn ngữ đó.
TARGET_LANG = "schinese"   # Thay đổi nếu cần: "polish", "russian", "tchinese"...

COPY_MISSING = True  # Giữ nguyên bản gốc nếu chưa dịch

BACKUP_SUFFIX = ".bak"  # Tạo backup trước khi ghi


def load_translations(csv_path: str) -> dict:
    """
    Load CSV → dict: { (file_hash, string_hash) -> vietnamese_text }
    """
    translations = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["file_hash"], row["string_hash"])
            viet = row.get("vietnamese", "").strip()
            original = row.get("original", "").strip()
            if viet:
                translations[key] = viet
            elif COPY_MISSING:
                translations[key] = original
    return translations


def main():
    if not os.path.exists(INPUT_CSV):
        print(f"[!] Không tìm thấy file CSV: {INPUT_CSV}")
        print("    Hãy chạy export_to_csv.py trước và điền bản dịch.")
        return

    translations = load_translations(INPUT_CSV)
    print(f"[+] Đã load {len(translations)} chuỗi dịch từ CSV")

    json_files = glob.glob(os.path.join(LOCR_DIR, "**", "*.JSON"), recursive=True)
    json_files += glob.glob(os.path.join(LOCR_DIR, "**", "*.json"), recursive=True)
    json_files = list(set(json_files))

    if not json_files:
        print(f"[!] Không tìm thấy file JSON nào trong: {LOCR_DIR}")
        return

    modified = 0
    skipped = 0

    for json_path in sorted(json_files):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[!] Lỗi đọc {json_path}: {e}")
                continue

        file_hash = data.get("hash", os.path.basename(json_path))
        localization = data.get("localization", {})

        # Xác định ngôn ngữ nguồn để lấy cấu trúc hash
        source_entries = None
        for lang in ["english", "en"]:
            if lang in localization and localization[lang]:
                source_entries = localization[lang]
                break
        if source_entries is None:
            # Fallback: lấy ngôn ngữ đầu tiên
            for entries in localization.values():
                if entries:
                    source_entries = entries
                    break

        if not source_entries:
            skipped += 1
            continue

        # Xây dựng danh sách entry tiếng Việt
        viet_entries = []
        for entry in source_entries:
            string_hash = entry.get("hash", "")
            key = (file_hash, string_hash)
            translated = translations.get(key, entry.get("string", ""))
            viet_entries.append({
                "hash": string_hash,
                "string": translated
            })

        # Ghi vào ngôn ngữ đích
        if TARGET_LANG not in localization:
            # Nếu ngôn ngữ đích không tồn tại, tạo mới dựa trên English
            localization[TARGET_LANG] = viet_entries
        else:
            localization[TARGET_LANG] = viet_entries

        data["localization"] = localization

        # Backup file gốc
        backup_path = json_path + BACKUP_SUFFIX
        if not os.path.exists(backup_path):
            shutil.copy2(json_path, backup_path)

        # Ghi file đã chỉnh sửa
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        modified += 1

    print(f"[+] Đã cập nhật {modified} file JSON (ngôn ngữ đích: '{TARGET_LANG}')")
    print(f"[~] Bỏ qua {skipped} file (không có chuỗi)")
    print()
    print("Bước tiếp theo — Rebuild LOCR và tạo patch RPKG:")
    print(f'  cd "d:\\Games\\007 First Light\\tools\\rpkg"')
    print(f'  .\\rpkg-cli.exe -rebuild_locr_from_json_from "d:\\Games\\007 First Light\\localization\\LOCR"')
    print()
    print("Sau khi rebuild xong, copy file patch .rpkg vào thư mục Runtime\\")
    print("Đặt tên file: chunk0patch1.rpkg (hoặc chunk1patch1.rpkg)")
    print(f"Vào Settings game, chọn ngôn ngữ: {TARGET_LANG}")


if __name__ == "__main__":
    main()
