#!/usr/bin/env python3
"""
Patch script — fil/MBB05/2025
Applies 35 confirmed linguistic fixes to Devocional_year_2025_fil_MBB05.json
Validated: 35/35 dry run ✅ | 35/35 reverse validation ✅

Usage:
    python3 patch_fil_MBB05_2025.py                  # dry run (default)
    python3 patch_fil_MBB05_2025.py --apply          # apply fixes
    python3 patch_fil_MBB05_2025.py --apply --backup # apply + keep .bak
"""
import json, re, sys, shutil
from pathlib import Path

SOT_PATH = Path('Devocional_year_2025_fil_MBB05.json')
DRY_RUN  = '--apply' not in sys.argv
BACKUP   = '--backup' in sys.argv

# (entry_id, field, regex_pattern, replacement)
FIXES = [
    ('MgaTagaRomMBB0520250808',   'oracion',   r'\bsa pamamagitan mo\b',                              'sa pamamagitan Niya'),
    ('Pahayag24MBB0520250911',    'oracion',   r'pagliligtas na handog',                              'kaloob ng kaligtasan'),
    ('2Timoteo31MBB0520250924',   'oracion',   r'bawat pahina na kinasihan',                          'ang Salita na kinasihan'),
    ('MgaTagaFilMBB0520251002',   'oracion',   r'Amin po namin',                                      'Inaamin po namin'),
    ('MgaHebreo1MBB0520251106',   'reflexion', r'sentro ng ating mga panata at pag-asa',              'sentro ng ating pananampalataya at pag-asa'),
    ('1Juan418MBB0520251115',     'oracion',   r'Naminagusto naming maranasan',                       'Nais naming maranasan'),
    ('Juan173MBB0520251201',      'oracion',   r'nagdudugtong sa amin patungo sa Iyo',                'nagsisilbing tulay sa amin patungo sa Iyo'),
    ('MgaTagaEfeMBB0520260124',   'oracion',   r'naghihirap dahil sa aming mga pagkukulang',          'nasaktan dahil sa aming mga pagkukulang'),
    ('Juan141MBB0520260122',      'oracion',   r'sumasalahat ng pag-unawa',                           'lumalampas sa lahat ng pag-unawa'),
    # kapamahalaan — 13 systemic hits
    ('Mateo5310MBB0520250913',    'reflexion', r'kapamahalaan',  'pamamahala'),
    ('MgaTagaRomMBB0520251109',   'reflexion', r'kapamahalaan',  'pamamahala'),
    ('MgaTagaRomMBB0520251208',   'reflexion', r'kapamahalaan',  'pamamahala'),
    ('Lucas1532MBB0520260210',    'reflexion', r'kapamahalaan',  'pamamahala'),
    ('MgaTagaColMBB0520260412',   'reflexion', r'kapamahalaan',  'pamamahala'),
    ('MgaTagaColMBB0520260412',   'oracion',   r'kapamahalaan',  'pamamahala'),
    ('MgaHebreo7MBB0520260501',   'reflexion', r'kapamahalaan',  'pamamahala'),
    ('Pahayag17MBB0520260511',    'reflexion', r'kapamahalaan',  'pamamahala'),
    ('Juan1633MBB0520260612',     'oracion',   r'kapamahalaan',  'pamamahala'),
    ('Mateo82627MBB0520260630',   'oracion',   r'kapamahalaan',  'pamamahala'),
    ('Santiago41MBB0520260705',   'reflexion', r'kapamahalaan',  'pamamahala'),
    ('Santiago41MBB0520260705',   'oracion',   r'kapamahalaan',  'pamamahala'),
    ('Lucas137MBB0520260722',     'oracion',   r'kapamahalaan',  'pamamahala'),
    # remaining confirmed fixes
    ('Marcos834MBB0520260303',    'oracion',   r'ang aming mga nais, at mga pagnanais ng aming puso', 'ang mga pagnanais ng aming puso'),
    ('2MgaTagaCoMBB0520260424',   'oracion',   r'\bmasayod\b',                                        'masukatan'),
    ('MgaTagaGalMBB0520260426',   'oracion',   r'mabait at mabuti',                                   'mabuti'),
    ('Santiago28MBB0520260506',   'reflexion', r'\butong\b',                                          'utos'),
    ('Santiago28MBB0520260506',   'oracion',   r'\butong\b',                                          'utos'),
    ('MgaHebreo7MBB0520260501',   'reflexion', r'\bAplikante\b',                                      'Tagapamagitan'),
    ('Pahayag211MBB0520260503',   'oracion',   r'Kami ay lubos na nagpapasalamat sa katiyakan',       'Nagpapasalamat kami sa katiyakan'),
    ('MgaHebreo6MBB0520260609',   'reflexion', r'simulaing aralin',                                   'panimulang aral'),
    ('MgaHebreo6MBB0520260609',   'oracion',   r'simulaing aralin',                                   'panimulang aral'),
    ('MgaHebreo1MBB0520251106',   'reflexion', r'ulirang huwaran',                                    'huwaran'),
    ('Mateo20262MBB0520260625',   'oracion',   r'ulirang huwaran',                                    'huwaran'),
    ('MgaTagaFil2911MBB0520260629','reflexion',r'pagluluhodng',                                       'pagluluhod'),
    ('Juan832MBB0520260701',      'reflexion', r'maraming pagsubok at mga pagsubok',                  'maraming pagsubok'),
]

if not SOT_PATH.exists():
    print(f'❌ File not found: {SOT_PATH}')
    sys.exit(1)

with open(SOT_PATH, encoding='utf-8') as f:
    data = json.load(f)

fil = data['data']['fil']
sot = {}
for date, entries in fil.items():
    for idx, e in enumerate(entries):
        sot[e['id']] = (date, idx)

found = missed = 0
for entry_id, field, pattern, replacement in FIXES:
    if entry_id not in sot:
        print(f'❌ MISS     {entry_id} — not in SOT')
        missed += 1
        continue
    date, idx = sot[entry_id]
    val = fil[date][idx].get(field, '')
    rx = re.compile(pattern)
    if rx.search(val):
        new_val = rx.sub(replacement, val, count=1)
        m = rx.search(val).group()
        print(f'{"[DRY]" if DRY_RUN else "[FIX]"} {entry_id} | {field}')
        print(f'  OLD: ...{m}...')
        print(f'  NEW: ...{re.sub(pattern, replacement, m)}...')
        if not DRY_RUN:
            fil[date][idx][field] = new_val
        found += 1
    else:
        print(f'⚠️  NO MATCH {entry_id} | {field} | pattern: {pattern}')
        missed += 1

print(f'\n{"DRY RUN" if DRY_RUN else "APPLIED"}: {found} fixes | {missed} missed')

if not DRY_RUN and found > 0:
    if BACKUP:
        shutil.copy(SOT_PATH, SOT_PATH.with_suffix('.bak'))
        print(f'💾 Backup: {SOT_PATH.with_suffix(".bak")}')
    with open(SOT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'✅ Written: {SOT_PATH}')
