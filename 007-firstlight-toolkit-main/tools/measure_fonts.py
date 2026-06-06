"""
measure_fonts.py - Do advance width cua font goc va Noto Sans
de tim scale chinh xac cho tung font group
"""
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import gfxf
from fontTools.ttLib import TTFont

ORIG = r'd:\Games\007 First Light\Runtime\_font_backup\original_font.GFXF'
FONTS_DIR = r'd:\Games\007 First Light\007-firstlight-toolkit-main\examples\vietnamese\fonts'

orig = open(ORIG, 'rb').read()
gfxsz = struct.unpack_from('<I', orig, 0x18)[0]
gfx = orig[84:84+gfxsz]

print("=== FONT GOC (game) - advance width cua chu A (scaleform units) ===")
orig_advs = {}
p = 21
while p < len(gfx):
    code, ln, q = gfxf.read_tag(gfx, p)
    if code == 75:
        body = gfx[q:q+ln]
        fid = struct.unpack_from('<H', body, 0)[0]
        nlen = body[4]
        name = body[5:5+nlen].decode('utf-8', 'replace')
        ng = struct.unpack_from('<H', body, 5+nlen)[0]
        ot = 5+nlen+2
        offs = [struct.unpack_from('<I', body, ot+i*4)[0] for i in range(ng+1)]
        cs = ot+offs[ng]
        codes = [struct.unpack_from('<H', body, cs+i*2)[0] for i in range(ng)]
        ads_off = cs + ng*2 + 6
        advs = [struct.unpack_from('<h', body, ads_off+i*2)[0] for i in range(ng)]
        
        adv_A = next((advs[i] for i in range(ng) if codes[i] == 65), None)
        adv_a = next((advs[i] for i in range(ng) if codes[i] == 97), None)
        adv_O = next((advs[i] for i in range(ng) if codes[i] == 79), None)
        avg_AZ = sum(advs[i] for i in range(ng) if 65 <= codes[i] <= 90) / max(1, sum(1 for c in codes if 65 <= c <= 90))
        avg_az = sum(advs[i] for i in range(ng) if 97 <= codes[i] <= 122) / max(1, sum(1 for c in codes if 97 <= c <= 122))
        
        orig_advs[fid] = {'A': adv_A, 'a': adv_a, 'O': adv_O, 'avgAZ': avg_AZ, 'avgaz': avg_az}
        print(f"  Font {fid:2d} ({name:30s}): A={adv_A}  a={adv_a}  avg_AZ={avg_AZ:.0f}  avg_az={avg_az:.0f}")
    if code == 0 and ln == 0:
        break
    p = q + ln

print()
print("=== NOTO SANS - advance width tai cac scale khac nhau ===")
for weight, fname in [
    ('Regular',  'NotoSans-Regular.ttf'),
    ('Bold',     'NotoSans-Bold.ttf'),
    ('Medium',   'NotoSans-Medium.ttf'),
    ('SemiBold', 'NotoSans-SemiBold.ttf'),
]:
    path = os.path.join(FONTS_DIR, fname)
    tt = TTFont(path)
    hm = tt['hmtx'].metrics
    cmap = tt.getBestCmap()
    upm = tt['head'].unitsPerEm
    
    for scale_size in [15, 16, 17, 18, 19, 20]:
        scale = (1024 * scale_size) / upm
        adv_A = hm[cmap[65]][0] * scale
        adv_a = hm[cmap[97]][0] * scale
        avg_AZ = sum(hm[cmap[c]][0]*scale for c in range(65,91) if c in cmap) / 26
        if scale_size == 20:  # in day du cho scale 20
            print(f"  {weight:10s} scale_size={scale_size}: A={adv_A:.0f}  a={adv_a:.0f}  avg_AZ={avg_AZ:.0f}")

print()
print("=== SO SANH: can tim scale_size nao cho adv_A gan voi font goc ===")
# Font 1 (Rajdhani Bold) -> dung NotoSans-Bold
# Font 3 (Arya Regular)  -> dung NotoSans-Regular
tt_bold = TTFont(os.path.join(FONTS_DIR, 'NotoSans-Bold.ttf'))
tt_reg  = TTFont(os.path.join(FONTS_DIR, 'NotoSans-Regular.ttf'))
hm_bold = tt_bold['hmtx'].metrics; cmap_bold = tt_bold.getBestCmap(); upm_bold = tt_bold['head'].unitsPerEm
hm_reg  = tt_reg['hmtx'].metrics;  cmap_reg  = tt_reg.getBestCmap();  upm_reg  = tt_reg['head'].unitsPerEm

for fid, target_font, tt, hm, cmap, upm in [
    (1, 'NotoSans-Bold',    tt_bold, hm_bold, cmap_bold, upm_bold),
    (3, 'NotoSans-Regular', tt_reg,  hm_reg,  cmap_reg,  upm_reg),
    (4, 'NotoSans-Regular', tt_reg,  hm_reg,  cmap_reg,  upm_reg),
]:
    if fid not in orig_advs: continue
    target_A = orig_advs[fid]['A']
    target_avg = orig_advs[fid]['avgAZ']
    if target_A is None: continue
    # Tim scale_size to match adv_A
    noto_adv_A_at1 = hm[cmap[65]][0] / upm * 1024  # advance at scale_size=1
    best_ss = target_A / noto_adv_A_at1
    noto_avg_at_best = sum(hm[cmap[c]][0]*best_ss for c in range(65,91) if c in cmap) / 26
    print(f"  Font {fid} ({target_font}): goc A={target_A}, best scale_size={best_ss:.2f}, avg_AZ={noto_avg_at_best:.0f} (goc={target_avg:.0f})")
