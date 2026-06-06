"""
inspect_rpkg.py
---------------
Tự parse cấu trúc header của file RPKG (format 2KPR / RPKGv2)
để liệt kê tất cả file type (4-char resource type) có bên trong.

Cách dùng:
    python inspect_rpkg.py

Tham khảo format từ:
  https://github.com/glacier-modding/RPKG-Tool/blob/main/rpkg_src/rpkg.cpp
"""

import struct
import os
import sys
from collections import Counter

RPKG_PATH = r"d:\Games\007 First Light\Runtime\chunk0.rpkg"

def read_u32(f):
    return struct.unpack("<I", f.read(4))[0]

def read_u64(f):
    return struct.unpack("<Q", f.read(8))[0]

def parse_rpkg(path):
    print(f"Parsing: {path}")
    print(f"Size: {os.path.getsize(path):,} bytes\n")

    with open(path, "rb") as f:
        # --- Magic ---
        magic = f.read(4)
        magic_str = magic.decode("ascii", errors="replace")
        print(f"Magic: {magic_str!r}  ({' '.join(f'{b:02X}' for b in magic)})")

        if magic == b"2KPR":
            version = 2
        elif magic == b"GKPR":
            version = 1
        else:
            print(f"[!] Unknown magic, aborting")
            return

        print(f"Version: RPKGv{version}\n")

        # --- RPKGv2 Header ---
        # struct: uint32 version, uint64 hash_offset, uint64 hash_count,
        #         uint64 data_offset (varies slightly by version)
        # Source: rpkg.cpp  read_rpkg()

        # Byte 4: version field (uint32)
        ver_field = read_u32(f)
        print(f"Version field: 0x{ver_field:08X}")

        # Bytes 8..15: hash table offset (uint64)
        hash_table_offset = read_u64(f)
        print(f"Hash table offset: 0x{hash_table_offset:016X}  ({hash_table_offset:,})")

        # Bytes 16..23: hash count (uint64)
        hash_count = read_u64(f)
        print(f"Hash count: {hash_count:,}")

        if hash_count == 0:
            print("[!] hash_count = 0 — file có thể rỗng hoặc header bị encrypt")
            return

        if hash_count > 5_000_000:
            print(f"[!] hash_count quá lớn ({hash_count}), có thể đọc sai offset")
            return

        # --- Đọc hash table ---
        # Mỗi entry trong hash table: uint64 hash + uint64 data_offset = 16 bytes
        # (RPKGv2 layout theo rpkg.cpp)
        print(f"\nĐang đọc hash table tại offset 0x{hash_table_offset:X}...")
        f.seek(hash_table_offset)

        # Đọc tất cả hash (8 bytes mỗi entry)
        hashes = []
        for _ in range(min(hash_count, 2_000_000)):
            raw = f.read(8)
            if len(raw) < 8:
                break
            h = struct.unpack("<Q", raw)[0]
            hashes.append(h)

        print(f"Đọc được {len(hashes):,} hash entries")

        # --- Phân tích resource type ---
        # Trong Glacier hash, 4 byte cao (byte 4-7 của uint64) = resource type (ASCII)
        # Hash layout: [4 bytes data hash][4 bytes resource type]
        # Ví dụ: 0x52434F4C_XXXXXXXX => type = "LOCR" (0x4C4F4352 little-endian)

        type_counter = Counter()
        sample_hashes = {}  # type -> [hash examples]

        for h in hashes:
            # Resource type là 4 byte cao (bits 32-63)
            type_bytes = struct.pack(">I", (h >> 32) & 0xFFFFFFFF)
            try:
                type_str = type_bytes.decode("ascii")
                if type_str.isprintable() and type_str.strip():
                    type_counter[type_str] += 1
                    if type_str not in sample_hashes:
                        sample_hashes[type_str] = []
                    if len(sample_hashes[type_str]) < 3:
                        sample_hashes[type_str].append(f"0x{h:016X}")
                else:
                    type_counter["[binary]"] += 1
            except Exception:
                type_counter["[binary]"] += 1

        print(f"\n{'='*55}")
        print(f"{'Resource Type':<15} {'Count':>10}  Sample hashes")
        print(f"{'='*55}")
        for t, cnt in type_counter.most_common(40):
            samples = "  " + ", ".join(sample_hashes.get(t, []))
            print(f"{t:<15} {cnt:>10}{samples}")

        # Tìm LOCR riêng
        locr_count = type_counter.get("LOCR", 0)
        print(f"\n{'='*55}")
        if locr_count > 0:
            print(f"[OK] Tìm thấy {locr_count} file LOCR!")
            print(f"     Sample: {sample_hashes.get('LOCR', [])}")
        else:
            print("[!] Không có LOCR trong file này.")
            # Tìm các type liên quan đến text/localization
            text_types = [t for t in type_counter if any(k in t.upper() for k in ["LOC","TEXT","LANG","STR","DLGE","CLNG","LINE"])]
            if text_types:
                print(f"[i] Các type có thể liên quan đến text: {text_types}")
            else:
                print("[i] Không thấy type nào liên quan đến localization.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else RPKG_PATH
    parse_rpkg(target)
    print()
    input("Nhấn Enter để thoát...")
