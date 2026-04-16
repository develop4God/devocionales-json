#!/usr/bin/env python3
"""
Translate good_shepherd from English to Tagalog
"""
import json
import sys
import os

# Add parent directory to path for verse_resolver import
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

# Paths
DB_PATH = '/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3'
EN_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/en/good_shepherd_en_001.json'
TL_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/tl/good_shepherd_tl_001.json'

# Load English source
with open(EN_FILE, 'r', encoding='utf-8') as f:
    en_data = json.load(f)

# Initialize resolver
resolver = VerseResolver(DB_PATH)

# Resolve key verse
print("Resolving key verse...")
key_ref = en_data['key_verse']['reference']
cita, texto, error = resolver.resolve(key_ref)
if error:
    print(f"ERROR resolving {key_ref}: {error}")
    sys.exit(1)
print(f"✓ {key_ref} → {cita}")

# Resolve scripture connections in card 3
print("\nResolving scripture connections...")
refs_to_resolve = [
    "Psalm 23:1-3",
    "Ezekiel 34:11",
    "John 10:3"
]

resolved_scriptures = []
for ref in refs_to_resolve:
    c, t, e = resolver.resolve(ref)
    if e:
        print(f"ERROR resolving {ref}: {e}")
        sys.exit(1)
    print(f"✓ {ref} → {c}")
    resolved_scriptures.append({'reference': c, 'text': t})

# Resolve scripture anchor in card 4
print("\nResolving scripture anchor...")
anchor_ref = "John 10:9"
c, t, e = resolver.resolve(anchor_ref)
if e:
    print(f"ERROR resolving {anchor_ref}: {e}")
    sys.exit(1)
print(f"✓ {anchor_ref} → {c}")

resolver.close()

print("\n" + "="*60)
print("ALL VERSES RESOLVED SUCCESSFULLY")
print("="*60)
print(f"\nKey verse ({cita}):")
print(f"  {texto}")
print(f"\nScripture connections:")
for s in resolved_scriptures:
    print(f"  {s['reference']}: {s['text'][:60]}...")
print(f"\nScripture anchor ({c}):")
print(f"  {t}")

# Now create the Tagalog translation
tl_data = {
    "id": "good_shepherd_001",
    "type": "discovery",
    "date": "2026-01-28",
    "title": "Ang Mabuting Pastol",
    "subtitle": "Nang ipahayag ni Jesus na kilala Niya ang bawat tupa sa pamamagitan ng pangalan",
    "language": "tl",
    "version": "Ang Dating Biblia",
    "estimated_reading_minutes": 7,
    "key_verse": {
        "reference": cita,
        "text": texto
    },
    "cards": [
        {
            "order": 1,
            "type": "historical_context",
            "icon": "🐑",
            "title": "Ang Pastol sa Israel",
            "subtitle": "Bakit napakalakas ng epekto ng larawang ito sa mga Hudyo",
            "content": "Nang sabihin ni Jesus na 'Ako ang mabuting pastol,' ginagamit Niya ang isa sa pinakamayamang larawan mula sa Lumang Tipan.\n\n🏜️ ANG KONTEKSTO NG KULTURA:\n\n• Ang pag-aalaga ng tupa ay ang pinakakaraniwang hanapbuhay sa Israel - nauunawaan ng lahat ang larawang ito\n• Ang mga pastol ay gumagugol ng mga araw at gabi kasama ang kanilang mga tupa sa ilang\n• Kilala nila ang bawat tupa sa pamamagitan ng pangalan at katangian\n• Kinikilala ng mga tupa ang partikular na tinig ng kanilang pastol\n• Ang pastol ay pumupunta SA UNAHAN ng kawan, hindi sa likuran - pinamumunuan niya sila, hindi tinutulak\n\n📖 ANG LARAWAN SA LUMANG TIPAN:\n\n• Nagsisimula ang Awit 23: 'Ang Panginoon ay aking pastol'\n• Tinatawag ng Diyos ang Sarili Niyang Pastol ng Israel (Awit 80:1, Ezekiel 34)\n• Sa Ezekiel 34, nangako ang Diyos: 'Ako mismo ang mag-aalaga sa aking mga tupa' (t.15)\n\n⚡ ANG NAKAKAGULAT NA KONEKSYON:\n\nNang sabihin ni Jesus na 'AKO ANG mabuting pastol,' ipinapahayag Niya: 'Ako ang PANGINOON, ang ipinangakong Pastol mula sa Ezekiel 34. Ako ang Diyos mismo na dumarating upang alagaan ang aking mga tupa.'\n\nPara sa mga Fariseo na nakikinig, hindi ito magandang tula. Ito ay deklarasyon ng pagka-Diyos na nagtulak sa kanila na mamumuhat ng mga bato (Juan 10:31).",
            "revelation_key": "Hindi dumating si Jesus upang maging isang mahusay na guro ng relihiyon. Dumating Siya upang maging ang Pastol na ipinangako ng Diyos para sa Kanyang bayan."
        },
        {
            "order": 2,
            "type": "greek_exegesis",
            "icon": "📖",
            "title": "Kalós: Hindi Lamang Mabuti, Kundi Maganda",
            "subtitle": "Ang salitang naglalarawan sa perpektong pastol",
            "greek_words": [
                {
                    "word": "Kalós",
                    "transliteration": "καλός",
                    "reference": "Juan 10:11",
                    "meaning": "Mabuti, maganda, marangal, kahusayan sa karakter at hitsura",
                    "revelation": "Hindi sinasabi ni Jesus na 'agathos' (moralitang mabuti). Sinasabi Niya ang KALÓS - isang pastol na:\n\n• Mabuti sa panloob na karakter\n• Maganda sa panlabas na hitsura\n• Marangal sa pag-uugali\n• Kahusayan sa bawat aspeto\n\nIto ang parehong salitang ginamit sa Genesis 1 (LXX) nang makita ng Diyos ang Kanyang nilikha at sinabi 'kaló' (napakabuti/maganda).\n\nHindi lamang isang pastol na gumagawa ng kanyang tungkulin. Ang PERPEKTO, KAHANGA-HANGANG, MAGANDANG pastol sa lahat ng kahulugan.",
                    "application": "Ang iyong Pastol ay hindi lamang moralitang mabuti. Siya ay lubos na maganda, ganap na mapagkakatiwalaan, perpektong kahusayan sa lahat ng paraan ng pag-aalaga sa iyo."
                },
                {
                    "word": "Tithēsin",
                    "transliteration": "τίθησιν",
                    "reference": "Juan 10:11",
                    "meaning": "Inilalagay, inilalapat, idinideposito nang kusang-loob",
                    "revelation": "Ang pandiwa ay nasa KASALUKUYANG panahon at AKTIBONG tinig: 'inilalagay' ang kanyang buhay.\n\nHindi sinasabing 'napilitang ibigay' o 'kinuha ang kanyang buhay.' Sinasabi na 'INILALAGAY' (tithēsin) - isang ganap na kusang kilos.\n\nUmuulit si Jesus dito sa t.18: 'Walang tao ang kumukuha nito sa akin, kundi ako ang naglalagay nito nang aking sarili.'\n\nHindi biktima. Isang KUSANG, SINADYA, PINILING sakripisyo.",
                    "application": "Hindi namatay si Cristo dahil natalo Siya sa labanan. Namatay Siya dahil PINILI Niya na mamatay para sa iyo. Ang Kanyang kamatayan ay ang pinaka-kusang kilos ng pagmamahal sa kasaysayan."
                }
            ],
            "revelation_key": "Ang mabuting pastol ay hindi lamang KAILANGAN na mag-alaga sa iyo. NAIS Niya na mag-alaga sa iyo. Ang Kanyang pagmamahal ay hindi obligasyon; ito ay kaligayahan."
        },
        {
            "order": 3,
            "type": "prophetic_thread",
            "icon": "🧵",
            "title": "Kilala Ko ang Aking mga Tupa",
            "subtitle": "Ang personal na intimidad ng Pastol sa bawat tupa",
            "content": "Sinasabi ng Juan 10:14-15: 'Ako ang mabuting pastol, at nakikilala ko ang aking mga tupa, at nakikilala nila ako. Kung paanong nakikilala ako ng Ama, gayon din nakikilala ko ang Ama.'\n\n🔑 TATLONG ANTAS NG PAGKILALA:\n\n1️⃣ 'KILALA KO ANG AKING MGA TUPA':\n\n• Ang salitang Griego ay 'ginōskō' - malalim, pinagkaranasan na kaalaman\n• Hindi mental na impormasyon; personal na relasyon\n• Kilala ni Jesus ang iyong pangalan, iyong kasaysayan, iyong mga sugat, iyong mga takot\n• Alam kung ano ang kailangan mo bago mo pa itanong\n\n2️⃣ 'AKO AY NAKIKILALA NG AKING MGA TUPA':\n\n• KINIKILALA ng mga tupa ang tinig ng pastol (t.4-5)\n• Hindi sumusunod sa mga estranghero dahil hindi kilala ang kanilang tinig\n• Ang kaalamang ito ay relasyonal, hindi lamang impormasyonal\n• Maaari mong malaman ang TUNGKOL kay Jesus nang hindi NAKIKILALA si Jesus\n\n3️⃣ ANG BANAL NA PAMANTAYAN:\n\n'Kung paanong nakikilala ako ng Ama, gayon din nakikilala ko ang Ama' (t.15)\n\nIkinukumpara ni Jesus ang IYONG relasyon sa Kanya sa KANYANG relasyon sa Ama:\n• Ang Ama at Anak ay may perpektong intimidad\n• Perpektong komunikasyon\n• Perpektong pagkakaisa\n• At sinasabi ni Jesus na GANYAN kung paano Niya kilala ka!\n\n⚠️ ANG BABALA:\n\nSa Mateo 7:23, sinasabi ni Jesus sa ilan: 'Hindi ko kayo kailanman nakilala.' Hindi 'Hindi ko kayo kailanman nalaman ang tungkol sa inyo.' Sinasabi 'Hindi ko kayo kailanman NAKILALA' (ginōskō).\n\nAng magkatuwang na pagkilala ay ang diwa ng ebanghelyo.",
            "scripture_connections": resolved_scriptures,
            "revelation_key": "Hindi ka numero sa isang malaking kawan. Kilala ka sa pamamagitan ng pangalan, minamahal nang personal, inaalagaan nang indibidwal ng Pastol ng sansinukob."
        },
        {
            "order": 4,
            "type": "theological_depth",
            "icon": "🚪",
            "title": "Ako ang Pintuan ng mga Tupa",
            "subtitle": "Ang eksklusibong access sa Ama",
            "content": "Sa Juan 10:7-9, gumawa si Jesus ng isa pang radikal na deklarasyon: 'Ako ang pintuan ng mga tupa.'\n\n🏕️ ANG KULUNGAN NG TUPA SA PANAHON NI JESUS:\n\n• Ang mga kulungan ng tupa ay nakapaligid ng mga pader na bato\n• May ISANG pasukan/labasan lamang\n• Ang pastol ay literal na HUMIHIGA sa pasukan sa gabi\n• Walang lobo ang makakapasok nang hindi dumaan sa pastol\n• Walang tupa ang makakaalis nang hindi nalalaman ng pastol\n\n🚪 'AKO ANG PINTUAN' (t.9):\n\nHINDI sinasabi ni Jesus na 'Ako ANG ISANG pintuan.' Sinasabi 'Ako ANG pintuan.'\n\nKahulugan:\n• TANGING access sa Ama ('Walang tao ang makaparoroon sa Ama, kundi sa pamamagitan ko' - Juan 14:6)\n• GANAP na seguridad (ang lobo ay kailangang dumaan muna sa Pastol)\n• BINABANTAYANG kalayaan ('papasok at lalabas, at makakasumpong ng pastulan' - t.9)\n\n🔒 ANG EKSKLUSIBIDAD:\n\nIto ay nakakasakit sa modernong kultura, ngunit malinaw si Jesus:\n• Walang maraming landas tungo sa Diyos\n• Hindi lahat ng relihiyon ay patungo sa parehong lugar\n• Si Jesus ang TANGING daan, ang TANGING pintuan\n\n'Ang lahat na nagsipariyan sa unahan ko ay mga magnanakaw at mga tulisan' (t.8)\n\nHindi niya iniinsulto ang mga propeta ng LT. Inilalantad Niya ang mga huwad na pastol na nangako ng kaligtasan sa anumang paraan maliban sa sakripisyo ni Cristo.\n\n✝️ ANG HALAGA NG PAGIGING PINTUAN:\n\nUpang maging pintuan, si Jesus ay kailangang:\n• Ilagay ang Kanyang katawan sa pagitan ng tupa at panganib\n• Tanggapin ang atake na nakalaan para sa tupa\n• Mamatay upang makapasok nang ligtas ang tupa\n\nSa krus, si Jesus ay literal na naging pintuan - ang Kanyang nabasag na katawan ay iyong pasukan tungo sa Ama.",
            "scripture_anchor": {
                "reference": c,
                "text": t
            },
            "revelation_key": "Hindi ka pumapasok sa kaharian ng Diyos sa pamamagitan ng pagiging mabuti, relihiyoso, o tapat. Pumapasok ka sa pamamagitan ng isang pintuan: si Jesu-Cristong ipinako at muling nabuhay."
        },
        {
            "order": 5,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Personal na Pagtuklas",
            "discovery_questions": [
                {
                    "category": "Kaalaman",
                    "question": "Sinasabi ni Jesus na 'Kilala ko ang aking mga tupa.' Namumuhay ka ba na may katiyakan na kilala ka ni Jesus nang PERSONAL, sa pamamagitan ng pangalan, kasama ang lahat ng iyong mga pakikibaka?"
                },
                {
                    "category": "Tinig",
                    "question": "Kinikilala ng mga tupa ang tinig ng pastol. Nakikilala mo ba ang tinig ni Jesus mula sa iba pang mga tinig (kultura, relihiyon, sarili mong isip) na nagsasalita sa iyong buhay?"
                },
                {
                    "category": "Pagtitiwala",
                    "question": "Ang pastol ay kusang naglalagay ng kanyang buhay para sa tupa. Naniniwala ka ba na NAIS ni Cristo na mag-alaga sa iyo, hindi lamang na KAILANGAN Niya?"
                }
            ],
            "prayer": {
                "title": "Panalangin sa Mabuting Pastol",
                "content": "Jesus, aking Mabuting Pastol, aking maganda at perpektong Pastol. Salamat na hindi ako numero sa isang walang-pangalang kawan. Kilala mo ako sa pamamagitan ng pangalan. Alam mo ang aking mga sugat, aking mga takot, aking mga pangangailangan. Ngayong araw ay pumipili akong makinig sa Iyong tinig higit sa lahat ng iba pang mga tinig. Salamat na kusang inilagay Mo ang Iyong buhay para sa akin. Hindi Ka biktima; Ikaw ay sakripisyo. Ikaw ang tanging pintuan tungo sa Ama, at pumapasok ako na may pasasalamat at kumpiyansa. Dalhin mo ako sa mga madamong pastulan at sa mga tahimik na tubig. Gabayan mo ako sa mga landas ng katuwiran alang-alang sa Iyong pangalan. Bagaman lumakad ako sa lambak ng lilim ng kamatayan, hindi ako matatakot sa kasamaan, sapagkat Ikaw ay kasama ko. Sa pangalan ng Mabuting Pastol, Amen."
            }
        }
    ],
    "tags": [
        "pastol",
        "pag-aalaga_ng_diyos",
        "kaligtasan",
        "personal_na_relasyon",
        "sakripisyo",
        "malalim_na_pagkilala"
    ],
    "metadata": {
        "total_word_count": 1020,
        "greek_words_count": 2,
        "scripture_references_count": 10,
        "difficulty_level": "intermediate",
        "themes": [
            "Pagkakakilanlan ni Cristo",
            "Pag-aalaga ng pastol",
            "Eksklusibidad ng ebanghelyo",
            "Personal na pagkilala"
        ]
    }
}

# Save Tagalog file
os.makedirs(os.path.dirname(TL_FILE), exist_ok=True)
with open(TL_FILE, 'w', encoding='utf-8') as f:
    json.dump(tl_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ Tagalog translation saved to: {TL_FILE}")
