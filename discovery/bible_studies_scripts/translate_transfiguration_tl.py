#!/usr/bin/env python3
"""
Translate transfiguration from English to Tagalog
"""
import json
import sys
import os

# Add parent directory to path for verse_resolver import
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

# Paths
DB_PATH = '/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3'
EN_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/en/transfiguration_en_001.json'
TL_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/tl/transfiguration_tl_001.json'

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
    "Luke 24:27",
    "John 5:46"
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
anchor_ref = "2 Peter 1:17-18"
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
print(f"  {t[:60]}...")

# Now create the Tagalog translation
tl_data = {
    "id": "transfiguration_001",
    "type": "discovery",
    "date": "2026-01-29",
    "title": "Ang Pagbabagong-Anyo",
    "subtitle": "Nang magbukas ang tabing ng laman at sumilay ang kaluwalhatian",
    "language": "tl",
    "version": "ADB",
    "estimated_reading_minutes": 9,
    "key_verse": {
        "reference": cita,
        "text": texto
    },
    "cards": [
        {
            "order": 1,
            "type": "historical_context",
            "icon": "⛰️",
            "title": "Ang Bundok ng Kaluwalhatian",
            "subtitle": "Anim na araw pagkatapos: ang propetikong konteksto",
            "content": "Nagsisimula ang Mateo 17:1: 'At pagkatapos ng anim na araw...'\n\n🔍 ANIM NA ARAW PAGKATAPOS NG ANO?\n\nIsinusulat ng Mateo 16:21-28:\n• Hinulaan ni Jesus ang Kanyang kamatayan at pagkabuhay (t.21)\n• Sinaway ni Pedro si Jesus (t.22)\n• Sinaway ni Jesus si Pedro: 'Lumagay ka sa likuran ko, Satanas' (t.23)\n• Nagsalita si Jesus tungkol sa halaga ng pagiging alagad (t.24-26)\n• Nangako si Jesus: 'Katotohanang may ilan sa mga narito na hindi titikim ng kamatayan, hanggang sa kanilang makita ang Anak ng tao na paparito sa kaniyang kaharian' (t.28)\n\n⚡ ANG NATUPAD NA PANGAKO:\n\nANIM NA ARAW pagkatapos, tinupad ni Jesus ang pangakong iyon. Nakita nina Pedro, Santiago, at Juan ang Anak ng Tao sa Kanyang kaluwalhatian - isang unang sulyap ng Kanyang kaharian.\n\n⛰️ ANG BUNDOK (marahil Bundok Hermon):\n\n• Taas: 9,232 talampakan - ang pinakamataas na bundok sa Israel\n• Natatakpan ng niyebe sa tuktok nito ('maputi na gaya ng liwanag')\n• Malayo at pribadong lokasyon, malayo sa mga tao\n• Hangganan sa pagitan ng Israel at ng mundo ng mga Hentil\n\n📖 ANG BIBLIKONG PADRON:\n\nNaghahayag ang Diyos ng Kanyang Sarili sa mga bundok:\n• Tinanggap ni Moises ang Kautusan sa Sinai\n• Narinig ni Elias ang payapang maliit na tinig sa Horeb\n• Ibinigay ni Jesus ang Sermon sa Bundok\n• Nanalangin si Jesus sa Bundok ng mga Olibo\n• Namatay si Jesus sa Golgota (bundok)\n• Umakyat si Jesus mula sa Bundok ng mga Olibo\n\nAng mga bundok ay mga lugar ng banal na pagtatagpo, kung saan hinahawakan ng langit ang lupa.",
            "revelation_key": "Sa tamang oras nang marinig ng mga alagad ang tungkol sa krus (kamatayan), ipinakita sa kanila ni Jesus ang korona (kaluwalhatian). Ang pagbabagong-anyo ay ang banal na lunas sa pagkabalisa."
        },
        {
            "order": 2,
            "type": "greek_exegesis",
            "icon": "📖",
            "title": "Metamorphoō: Binago Mula sa Loob Patungo sa Labas",
            "subtitle": "Hindi pagtatakip, kundi paghahayag",
            "greek_words": [
                {
                    "word": "Metamorphoō",
                    "transliteration": "μεταμορφόω",
                    "reference": "Mateo 17:2",
                    "meaning": "Magbago-anyo, baguhin ang anyo na naghahayag ng panloob na diwa",
                    "revelation": "Ang pandiwang Griego na ito ay nagbibigay sa atin ng salitang Ingles na 'metamorphosis'. Ang kahulugan nito ay:\n\n• Pagbabago MULA SA LOOB patungo sa labas\n• Hindi pagsusuot ng costume; paghahayag ng nasa loob na\n• Tulad ng uod na nababago sa paru-paro - ang paru-paro ay nasa DNA na ng uod\n\nHindi 'nagbihis' si Jesus bilang maluwalhati. Hinayaan Niya ang Kanyang PANLOOB na kaluwalhatian na sumilay sa Kanyang pagkatao.\n\nSa loob ng 33 taon, TINAKPAN ni Jesus ang Kanyang kaluwalhatian. Sa pagbabagong-anyo, sa ilang sandali, nabuksan ang tabing at nakita ng mga alagad kung sino TALAGA Siya.\n\n🔥 ANG PAREHONG SALITA SA ROMA 12:2:\n\n'At kayo'y huwag magsiayon sa sanglibutan: kundi kayo'y mangagbago (metamorphoō) sa pagbabago ng inyong pagiisip.'\n\nAng parehong pagbabagong nangyari kay Jesus sa bundok ay dapat mangyari sa iyo! Hindi panlabas, kundi panloob. Hindi relihiyoso, kundi totoo.",
                    "application": "Ang iyong Cristiyanong pagbabago ay hindi pagsusuot ng relihiyosong maskara. Ito ay paghahayag ng kaluwalhatian ni Cristo sa iyo na sumisilakbo sa iyong buhay."
                },
                {
                    "word": "Elampsen",
                    "transliteration": "ἔλαμψεν",
                    "reference": "Mateo 17:2",
                    "meaning": "Nagniningning, naglalabas ng maliwanag na liwanag",
                    "revelation": "Ang pandiwa ay naglalarawan ng AKTIBO, MALIWANAG, HINDI-MAITATATAGO na ningning.\n\n'At ang kaniyang mukha ay nagningning NA GAYA NG ARAW' - hindi mahinang ningning, kundi ang pinakamatingkad na liwanag na kilala ng tao.\n\nTandaan:\n• Sa paglalang, sinabi ng Diyos 'Magkaroon ng liwanag' (Genesis 1:3)\n• Sinasabi ni Jesus 'Ako ang ilaw ng sanglibutan' (Juan 8:12)\n• Sa pagbabagong-anyo, ang LIWANAG na iyon ay nagiging pisikal na nakikita\n\nIto ang parehong kaluwalhatian (Shekinah) na:\n• Pinuno ang tabernakulo (Exodo 40:34)\n• Pinuno ang templo ni Solomon (I Mga Hari 8:11)\n• Ngayon ay tumatahan sa katawan ni Jesus ('at ang Verbo ay nagkatawang-tao, at tumahan sa gitna natin, at aming nakita ang kaniyang KALUWALHATIAN' - Juan 1:14)",
                    "application": "Ang kaluwalhatiang nakikita mo sa pagbabagong-anyo ay hindi bago. Ito ang walang-hanggang kaluwalhatian ng Anak na sa isang sandali ay naging nakikita. Ito ang kaluwalhatiang taglay Niya sa Ama bago itinatag ang sanglibutan."
                }
            ],
            "revelation_key": "Ang pagbabagong-anyo ay hindi pagtanggap ni Jesus ng kaluwalhatian. Ito ay paghahayag ni Jesus ng kaluwalhatiang lagi Niyang taglay ngunit tinakpan sa Kanyang pagkatao."
        },
        {
            "order": 3,
            "type": "prophetic_thread",
            "icon": "🧵",
            "title": "Sina Moises at Elias: Ang Kautusan at ang mga Propeta",
            "subtitle": "Dalawang saksi ng dalawang tipan",
            "content": "Sinasabi ng Mateo 17:3: 'At narito, napakita sa kanila si Moises at si Elias na nagsasalita sa kaniya.'\n\n🔍 BAKIT SINA MOISES AT ELIAS?\n\n📜 Si MOISES ay kumakatawan sa KAUTUSAN:\n• Tumanggap ng Sampung Utos sa Sinai\n• Nagbigay ng Torah sa Israel\n• Nanghula ng Mesias: 'Ang Panginoon mong Dios ay magbabangon sa iyo ng isang Propeta, na gaya ko' (Deuteronomio 18:15)\n• Namatay at inilibing mismo ng Diyos (Deuteronomio 34:5-6)\n\n🔥 Si ELIAS ay kumakatawan sa mga PROPETA:\n• Ang pinakamaringal na propeta sa LT\n• Hindi namatay - dinala sa langit sa karwahe ng apoy (II Mga Hari 2:11)\n• Hinirang na bumalik bago ang Mesias (Malakias 4:5)\n\n✨ MAGKASAMA ay kumakatawan sila sa:\n• 'Ang Kautusan at ang mga Propeta' - ang buong Lumang Tipan\n• Parehong nagkaroon ng pakikipag-usap sa Diyos sa mga bundok (Sinai/Horeb)\n• Parehong nag-ayuno ng 40 araw\n• Parehong kumakatawan sa lumang tipan\n\n💬 ANO ANG PINAG-UUSAPAN NILA?\n\nIhahayag ng Lucas 9:31: 'Na nangagsasalita tungkol sa kaniyang pagkamatay (EXODO sa Griego), na dapat niyang ganapin sa Jerusalem.'\n\nPinag-uusapan nila ang KRUS!\n\n• Pinamunuan ni Moises ang unang Exodo (pag-alis mula sa Egipto)\n• Gaganapin ni Jesus ang HULING Exodo (pag-alis mula sa kasalanan at kamatayan)\n• Ang Kautusan at ang mga Propeta ay TUMUTURO sa krus\n\n🎯 ANG MENSAHE:\n\nAng buong Lumang Tipan (Kautusan at mga Propeta) ay natutupad kay Jesus. HINDI sila nakikipagtunggali kay Jesus; NAGPAPATOTOO sila tungkol kay Jesus.",
            "scripture_connections": resolved_scriptures,
            "revelation_key": "Ang Lumang Tipan ay hindi ibang libro mula sa ebanghelyo. Ito ay ang ebanghelyo sa mga anino, na tumuturo kay Cristo."
        },
        {
            "order": 4,
            "type": "theological_depth",
            "icon": "☁️",
            "title": "Ang Tinig ng Ama: Ito ang Aking Minamahal na Anak",
            "subtitle": "Ang ikalawang pagkakataong nagsalita ang Ama mula sa langit",
            "content": "Mateo 17:5: 'At samantalang siya'y nagsasalita pa, narito, isang ulap na maliwanag ang nagbulubong sa kanila: at narito, isang tinig na nanggagaling sa ulap, na nagsasabi, Ito ang aking Anak na minamahal, na aking kinalulugdan; dinggin ninyo siya.'\n\n☁️ ANG ULAP:\n\n• Hindi ordinaryong ulap - 'ulap na maliwanag' (maliwanag na ulap)\n• Ang SHEKINAH - ang nakikitang kaluwalhatian ng Diyos\n• Ang parehong ulap na:\n  - Pinamunuan ang Israel sa ilang (Exodo 13:21)\n  - Pinuno ang tabernakulo (Exodo 40:34-35)\n  - Pinuno ang templo (I Mga Hari 8:10-11)\n  - Magdadala kay Jesus sa pag-akyat (Gawa 1:9)\n  - Dadalhin si Jesus sa Kanyang ikalawang pagparito (Mateo 24:30)\n\n🗣️ ANG TINIG NG AMA (ikalawang beses sa mga ebanghelyo):\n\n1️⃣ UNANG BESES - Sa binyag (Mateo 3:17):\n• 'Ito ang aking minamahal na Anak, na aking kinalulugdan'\n• Sa SIMULA ng ministeryo ni Jesus\n\n2️⃣ IKALAWANG BESES - Sa pagbabagong-anyo (Mateo 17:5):\n• 'Ito ang aking minamahal na Anak, na aking kinalulugdan; DINGGIN NINYO SIYA'\n• BAGO ang krus\n• May MAHALAGANG karagdagan: 'DINGGIN NINYO SIYA'\n\n📢 'DINGGIN NINYO SIYA!':\n\nKakamungkahing lamang ni Pedro na gumawa ng tatlong tabernakulo (t.4) - inilalagay si Jesus sa parehong antas nina Moises at Elias.\n\nWINAWASTO ito ng Ama:\n• Hindi tatlong tabernakulo - ISA lamang\n• Hindi tatlong tinig - ISANG tinig\n• Hindi 'makinig sa Kautusan AT sa mga Propeta AT kay Jesus'\n• Kundi: 'DINGGIN NINYO SIYA' - si Jesus ay HIGIT PA\n\n🔊 PINATUTUNAYAN ng Hebreo 1:1-2:\n\n'Ang Dios, pagkatapos na siya'y magsalita nang madaming panahon at nang madaming paraan nang unang panahon sa mga magulang sa pamamagitan ng mga propeta, Ay nagsalita sa atin sa mga huling araw na ito sa pamamagitan ng kaniyang Anak.'\n\nSina Moises at Elias ay mga tagapagsalita para sa Diyos. Si Jesus AY ang Salita ng Diyos.",
            "scripture_anchor": {
                "reference": c,
                "text": t
            },
            "revelation_key": "Ang Kautusan at ang mga Propeta ay mabuti, ngunit si Cristo ay PANGWAKAS. Huwag magdagdag ng anuman kay Jesus. Siya ay sapat, ganap, kataas-taasan."
        },
        {
            "order": 5,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Pansariling Pagtuklas",
            "discovery_questions": [
                {
                    "category": "Tinakpang Kaluwalhatian",
                    "question": "Tinakpan ni Jesus ang Kanyang kaluwalhatian sa laman ng tao dahil sa pag-ibig sa iyo. Pinahahalagahan mo ba na ang Hari ng sansinukob ay nagpakababa upang iligtas ka?"
                },
                {
                    "category": "Pagbabago",
                    "question": "Ang parehong salitang 'metamorphoō' ay naglalarawan ng pagbabagong-anyo ni Jesus at ng iyong pagbabago sa Roma 12:2. Hinihintulutan mo ba si Cristo na magningning MULA SA LOOB mo, o sinusubukan mo lamang na magmukhang relihiyoso sa panlabas?"
                },
                {
                    "category": "Pakikinig",
                    "question": "Sinasabi ng Ama na 'DINGGIN NINYO SIYA.' Nakikinig ka ba sa tinig ni Jesus higit sa lahat ng iba pang mga tinig, kahit relihiyosong mga tinig?"
                }
            ],
            "prayer": {
                "title": "Panalangin ng Pagsamba",
                "content": "Jesus na maluwalhati, Haring nabago ng anyo. Salamat na sa bundok ay ipinakita Mo kung sino Ka TALAGA - ang Anak ng Diyos sa maliwanag na kaluwalhatian. Sa loob ng 33 taon ay tinakpan Mo ang Iyong kaluwalhatian upang lumapit sa akin. Sa krus, ang Iyong kaluwalhatian ay mas natakpan pa upang pasanin ang aking kasalanan. Sa muling pagkabuhay, ang Iyong kaluwalhatian ay nagniningning muli. At isang araw, kapag nakita kita nang harapan, makikita ko ang kaluwalhatiang iyon na walang takip magpakailanman. Ama, salamat sa tinig mula sa langit: 'Ito ang aking minamahal na Anak.' Ngayong araw ay pumipili akong DINGGIN Siya lamang. Banal na Espiritu, baguhin mo ako mula sa loob. Hayaang magningning ang Iyong kaluwalhatian sa aking sirang buhay. Metamorphose mo ako hanggang sumasalamin ako sa larawan ni Cristo. Sa pangalan ng minamahal na Anak, Amen."
            }
        }
    ],
    "tags": [
        "kaluwalhatian",
        "pagbabagong_anyo",
        "paghahayag",
        "pagbabago",
        "tinig_ng_ama",
        "kahihigitan_ni_cristo"
    ],
    "metadata": {
        "total_word_count": 1200,
        "greek_words_count": 2,
        "scripture_references_count": 12,
        "difficulty_level": "intermediate",
        "themes": [
            "Nahayag na kaluwalhatian ni Cristo",
            "Kahihigitan ni Cristo sa Kautusan",
            "Panloob na pagbabago",
            "Patotoo ng Ama"
        ]
    }
}

# Save Tagalog file
os.makedirs(os.path.dirname(TL_FILE), exist_ok=True)
with open(TL_FILE, 'w', encoding='utf-8') as f:
    json.dump(tl_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ Tagalog translation saved to: {TL_FILE}")
