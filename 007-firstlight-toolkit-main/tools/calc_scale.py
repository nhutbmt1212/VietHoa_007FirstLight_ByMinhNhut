"""
Tinh scale_size chinh xac cho tung font de advance width khop voi font goc.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fontTools.ttLib import TTFont

FONTS_DIR = r'd:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\fonts'

# Advance width cua chu A trong font goc (do tu game)
# scale_em = 1024, do vay: advance_goc = hmtx_advance * (1024 * scale_size) / upm
ORIG = {
    1: {'A': 11407, 'avg_AZ': 11031, 'font': 'NotoSans-Bold.ttf',     'name': 'Rajdhani Bold'},
    2: {'A': 12738, 'avg_AZ': 12478, 'font': 'NotoSans-Regular.ttf',  'name': 'Noto Sans KNT'},
    3: {'A': 11059, 'avg_AZ': 10862, 'font': 'NotoSans-Regular.ttf',  'name': 'Arya Regular'},
    4: {'A': 10915, 'avg_AZ': 10780, 'font': 'NotoSans-Regular.ttf',  'name': 'Rajdhani Regular'},
    5: {'A': 11222, 'avg_AZ': 10939, 'font': 'NotoSans-SemiBold.ttf', 'name': 'Rajdhani SemiBold'},
    6: {'A': 11059, 'avg_AZ': 10853, 'font': 'NotoSans-Medium.ttf',   'name': 'Rajdhani Medium'},
}

print("=== Scale chinh xac cho tung font (match advance width voi font goc) ===")
print()
for fid, info in ORIG.items():
    path = os.path.join(FONTS_DIR, info['font'])
    tt = TTFont(path)
    hm = tt['hmtx'].metrics
    cmap = tt.getBestCmap()
    upm = tt['head'].unitsPerEm

    # advance_noto = hmtx[A] * (1024 * scale_size) / upm
    # can: advance_noto = target_A
    # => scale_size = target_A * upm / (hmtx[A] * 1024)
    hmtx_A = hm[cmap[65]][0]
    scale_size_exact = info['A'] * upm / (hmtx_A * 1024)
    
    # Verify voi avg_AZ
    scale_exact = 1024 * scale_size_exact / upm
    avg_check = sum(hm[cmap[c]][0]*scale_exact for c in range(65,91) if c in cmap) / 26
    
    print(f"Font {fid} ({info['name']:20s}) -> {info['font']:25s}: scale_size={scale_size_exact:.3f}  (verify avg_AZ: {avg_check:.0f} vs goc {info['avg_AZ']})")

print()
print("=== KET LUAN: dung scale_size rieng cho tung font group ===")
print()
# Gom theo font file
groups = {}
for fid, info in ORIG.items():
    path = os.path.join(FONTS_DIR, info['font'])
    tt = TTFont(path)
    hm = tt['hmtx'].metrics
    cmap = tt.getBestCmap()
    upm = tt['head'].unitsPerEm
    hmtx_A = hm[cmap[65]][0]
    ss = info['A'] * upm / (hmtx_A * 1024)
    key = info['font']
    if key not in groups:
        groups[key] = []
    groups[key].append((fid, ss, info['name']))

for fname, items in groups.items():
    avg_ss = sum(ss for _,ss,_ in items) / len(items)
    fids = [str(fid) for fid,_,_ in items]
    names = [n for _,_,n in items]
    print(f"  {fname}: scale_size={avg_ss:.2f}  (fonts {', '.join(fids)}: {', '.join(names)})")
