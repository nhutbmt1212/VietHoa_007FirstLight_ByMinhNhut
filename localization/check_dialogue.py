import json
d = json.load(open(r'd:\Games\007 First Light\localization\extracted\dialogue.json', encoding='utf-8'))
total = sum(len(v['segments']) for v in d.values())
print(f'Entries: {len(d)}')
print(f'Total segments: {total}')
for k, v in list(d.items())[:3]:
    print(f'  {k}: {v["segments"]}')
