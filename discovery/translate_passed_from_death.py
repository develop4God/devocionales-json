#!/usr/bin/env python3
"""
Translate passed_from_death_001 from English to Filipino
"""

import json
import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/discovery/bible_studies_scripts')

from verse_resolver import VerseResolver

# Paths
DB_PATH = '/home/runner/work/devocionales-json/devocionales-json/discovery/bible_database/MBB05_fil.SQLite3'
EN_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/en/passed_from_death_en_001.json'
FIL_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/fil/passed_from_death_fil_001.json'

# Load English source
with open(EN_FILE, 'r', encoding='utf-8') as f:
    en_data = json.load(f)

# Initialize VerseResolver
resolver = VerseResolver(DB_PATH)

def translate_verse_reference(ref):
    """Translate English book names to Filipino"""
    translations = {
        'John': 'Juan',
        'Colossians': 'Mga Taga-Colosas',
        'Ephesians': 'Mga Taga-Efeso',
        'Corinthians': 'Mga Taga-Corinto',
        'Galatians': 'Mga Taga-Galacia',
        'Romans': 'Mga Taga-Roma',
        'Philippians': 'Mga Taga-Filipos',
        'Timothy': 'Kay Timoteo',
        'Hebrews': 'Mga Hebreo',
        'Matthew': 'Mateo'
    }

    result = ref
    for eng, fil in translations.items():
        result = result.replace(eng, fil)
    return result

# Create Filipino translation
fil_data = {
    "id": en_data["id"],
    "type": en_data["type"],
    "date": en_data["date"],
    "title": "Lumipat mula sa Kamatayan patungo sa Buhay",
    "subtitle": "Ang huling paghahayag: hindi ka na maaaring maging 'hindi ipinanganak'",
    "language": "fil",
    "version": "Magandang Balita Biblia",
    "estimated_reading_minutes": 9,
    "key_verse": {},
    "cards": [],
    "tags": [
        "walang_hanggang_kaligtasan",
        "bagong_kapanganakan",
        "perpektong_panahunan",
        "natatakan_ng_espiritu",
        "juan_5_24",
        "disiplina_laban_sa_paghatol"
    ],
    "metadata": {
        "total_word_count": en_data["metadata"]["total_word_count"],
        "greek_words_count": en_data["metadata"]["greek_words_count"],
        "scripture_references_count": en_data["metadata"]["scripture_references_count"],
        "difficulty_level": en_data["metadata"]["difficulty_level"],
        "themes": [
            "Hindi na maibabalik ang bagong kapanganakan",
            "Kaligtasan batay sa katapatan ng Diyos",
            "Pagkakaiba ng disiplina at paghatol",
            "Perpektong panahunan ng kaligtasan"
        ]
    }
}

# Translate key verse
print("Resolving key verse: John 5:24")
citation, text, error = resolver.resolve("John 5:24")
if error:
    print(f"Error resolving John 5:24: {error}")
    text = en_data["key_verse"]["text"]
fil_data["key_verse"] = {
    "reference": "Juan 5:24",
    "text": text
}

# Card 1: The Moment of Revelation
card1 = {
    "order": 1,
    "type": "character_context",
    "icon": "🔄",
    "title": "Ang Sandali ng Paghahayag",
    "subtitle": "Pagsasama ng lahat ng nakaraang pag-aaral",
    "content": """Naglakbay tayo sa malalim na paglalakbay mula Gethsemane hanggang sa binuksang mga libingan:

1️⃣ GETHSEMANE: Pinagpawisan ng dugo ni Jesus sa ilalim ng presyon ng kopa
2️⃣ ANG HAPUNAN: Itinatag Niya ang Bagong Tipan bilang Tagapagmana
3️⃣ ANG KRUS: Ininom Niya ang kopa ng poot at pinabayaan
4️⃣ ANG TABING: Napunit ito mula itaas hanggang ibaba - nabuksan ang pagpasok
5️⃣ ANG MGA LIBINGAN: Nabuksan ang mga ito - nabuhay ang mga santo

🔑 ANG HULING TANONG:

Maaari bang MAWALA ang kanilang kaligtasan ang isang taong 'ipinanganak na muli'?

💡 ANG PAGHAHAYAG MULA SA NABUHAY NA MGA SANTO:

Nang makita natin na HINDI binuhay ng Diyos sina Abraham, David at Isaias para 'maligaw' pagkatapos, inihayag ng Banal na Espiritu ang isang bagay na malalim:

'Hindi sila binuhay ng Diyos para subukin silang muli. Binuhay sila dahil ang kanilang kaligtasan ay NATATAKAN na. Kung maaari silang maligaw, hindi sana ginugol ng Diyos ang Kanyang kapangyarihan ng muling pagkabuhay sa kanila.'

✨ ANG KONEKSYON:

Kung ang PISIKAL NA MULING PAGKABUHAY ay hindi na maibabalik...
Hindi ba rin ang ESPIRITUWAL NA MULING PAGKABUHAY?

📖 JUAN 5:24:

'Sinumang makinig sa aking salita... ay LUMIPAT NA mula sa kamatayan patungo sa buhay.'

Ang susing salita dito ay METABEBĒKEN (Strong G3327).""",
    "revelation_key": "Nang ipanganak ka na muli, naging 'nabuhay na mga santo' ka ngayon. Hindi ka na nasa libingan ng kasalanan. LUMIPAT ka na. Hindi na ito maibabalik."
}

# Card 2: Greek Exegesis
card2 = {
    "order": 2,
    "type": "greek_exegesis",
    "icon": "📖",
    "title": "Metabebēken: Ang Perpektong Panahunan ng Kaligtasan",
    "subtitle": "Bakit ito ay permanenteng legal na paglipat",
    "content": """Juan 5:24 - 'LUMIPAT NA (metabebēken) mula sa kamatayan patungo sa buhay.'

🔍 PAGSUSURI NG METABEBĒKEN (Strong G3327):

• META = Pagbabago ng lugar, paglipat
• BEBĒKEN = Pandiwa 'baino' (lumakad, maglakad)
• Panahunan: PERPEKTO

📚 ANG PERPEKTONG PANAHUNAN SA GRIEGO:

Ito ang PINAKAMALAKAS na panahunan ng pandiwa sa Griego:
• Aksyon na nangyari sa NAKARAAN
• Ang mga epekto ay NANANATILI sa kasalukuyan
• At nagpapatuloy tungo sa HINAHARAP

Hindi ito 'lumalipat' (kasalukuyang patuloy).
Hindi ito 'lilipat' (hinaharap).
Ito ay 'LUMIPAT NA at ang mga epekto ay permanente.'

🚚 ANG ILUSTRASYON NG PAGLIPAT:

Isipin na nakatira ka sa 'Kaharian ng Kamatayan':
• Pagkamamamayan: makasalanan
• Hari: Satanas
• Kapalaran: walang hanggang paghihiwalay

Nang ipanganak ka na muli, hindi mo pinabuti ang iyong kalagayan sa kaharian na iyon.
INILIPAT ka sa ibang kaharian:

Mga Taga-Colosas 1:13 - 'Sapagkat iniligtas niya tayo sa kapangyarihan ng kadiliman at dinala sa kaharian ng kanyang minamahal na Anak.'

• Bagong pagkamamamayan: santo
• Bagong Hari: Cristo
• Bagong kapalaran: buhay na walang hanggan

⚖️ ITO AY LEGAL NA PAGLIPAT:

Hindi ito nakadepende sa:
✗ Iyong pang-araw-araw na emosyon
✗ Iyong espirituwal na pagganap
✗ Iyong mga taas at baba

Nakadepende ito sa:
✓ Kamatayan ng Tagapagmana (pinatunayan ang testamento)
✓ Iyong pananampalataya kay Cristo (ginawa kang tagapagmana)
✓ Tatak ng Banal na Espiritu (garantiya)

🔒 MGA TAGA-EFESO 1:13-14:

'Kayo ay tinatakan sa kanya ng isang TATAK, ang ipinangakong Banal na Espiritu, na siyang paunang bayad na NAGSISIGURO ng ating pamana.'

PAUNANG BAYAD (arrabon - G728):
• Down payment na NAGSISIGURO ng buong bayad
• Tulad ng deposito sa bahay
• Legally binding

Kung ibinigay ng Diyos ang Espiritu bilang 'paunang bayad,' sa palagay mo ba ay hindi Niya kukumpletuhin ang transaksyon?""",
    "greek_words": [
        {
            "word": "Metabebēken",
            "transliteration": "μεταβέβηκεν",
            "meaning": "Lumipat na, inilipat na (perpektong panahunan)",
            "revelation": "Hindi ito patuloy na proseso. Ito ay natapos na katotohanan. LUMIPAT ka na. Ang iyong legal na posisyon ay permanenteng nagbago sa sandali ng paniniwala."
        },
        {
            "word": "Arrabon",
            "transliteration": "ἀρραβών",
            "meaning": "Garantiya, paunang bayad, pangako",
            "revelation": "Ang Banal na Espiritu sa iyo ay 'lagda' ng Diyos na kukumpletuhin Niya ang nasimulan Niya. Hindi ito utang; ito ay legal na pangako."
        },
        {
            "word": "Sphragizō",
            "transliteration": "σφραγίζω",
            "meaning": "Tatakin, markahan ng opisyal na tatak",
            "revelation": "Sa sinaunang mundo, ang tatak ng hari ay hindi masisira. Tinatakan ka ng Espiritu. Walang makakapagbasag ng tatak na iyon maliban sa Diyos, at hindi Niya gagawin iyon."
        }
    ],
    "revelation_key": "Ang Metabebēken ay perpektong panahunan: Lumipat ka na. Hindi ka 'sumusubok lumipat.' Hindi ka 'lilipat kung magtitiis ka.' LUMIPAT ka na. Permanente."
}

# Card 3: You Cannot Be Un-Born
print("Resolving verses for Card 3...")
jn_10_28_29_citation, jn_10_28_29_text, err = resolver.resolve("John 10:28-29")
rom_8_38_39_citation, rom_8_38_39_text, err2 = resolver.resolve("Romans 8:38-39")
phil_1_6_citation, phil_1_6_text, err3 = resolver.resolve("Philippians 1:6")
tim_2_13_citation, tim_2_13_text, err4 = resolver.resolve("2 Timothy 2:13")

card3 = {
    "order": 3,
    "type": "theological_depth",
    "icon": "👶",
    "title": "Hindi Ka Maaaring Maging Hindi Ipinanganak",
    "subtitle": "Bakit hindi na maibabalik ang bagong kapanganakan",
    "content": """Juan 3:3 - 'Katotohanang sinasabi ko sa inyo, walang makakakita ng kaharian ng Diyos maliban kung siya ay IPINANGANAK NA MULI.'

👶 ANG LOHIKA NG KAPANGANAKAN:

Maaari bang maging 'hindi ipinanganak' ang isang sanggol?

Maaari silang:
✓ Magkasakit
✓ Sumuway
✓ Lumayo sa kanilang mga magulang
✓ Maghimagsik laban sa kanilang pamilya

Ngunit HINDI sila maaari:
✗ Mawala ang kanilang DNA
✗ Tumigil sa pagiging anak
✗ Maging 'hindi ipinanganak' mula sa kanilang pamilya

🧬 ANG NAGBAGONG KALIKASAN:

2 Mga Taga-Corinto 5:17 - 'Kaya kung ang sinuman ay kay Cristo, siya ay BAGONG NILIKHA: Ang luma ay lumipas na, ang bago ay narito na!'

KAINĒ KTISIS (Bagong Nilikha):
• Hindi 'pinabuti'
• Hindi 'binago'
• BAGO - isang bagay na hindi umiiral noon

📊 ANG PAGKAKAIBA:

RELIHIYON:
• Sinusubukang PAGBUTIHIN ang lumang kalikasan
• Tulad ng pagpipinta ng kabaong ng mga kulay
• Nananatili ang kamatayan sa loob

EBANGHELYO:
• PINAPATAY ng Diyos ang lumang kalikasan
• Binibigyan ka ng BAGONG kalikasan
• 'Ako ay ipinako kay Cristo' (Gal 2:20)

🔑 MGA TAGA-ROMA 8:9-10:

'Kayo, gayunpaman, ay hindi sa kaharian ng laman kundi sa kaharian ng Espiritu, kung tunay na NANINIRAHAN sa inyo ang Espiritu ng Diyos. At kung ang sinuman ay walang Espiritu ni Cristo, hindi siya kay Cristo.'

Ang patunay ng kaligtasan:
• HINDI ang iyong moral na pagkaperpekto
• HINDI ang iyong kaalaman sa Bibliya
• ANG presensya ng Banal na Espiritu sa iyo

Kung ang Espiritu ay NANINIRAHAN (oikeō - permanenteng nananahan) sa iyo, ikaw ay kay Cristo.

⚠️ ANG BABALA:

1 Juan 2:19 - 'Sila ay umalis mula sa atin, ngunit hindi talaga sila KABILANG sa atin. Sapagkat kung sila ay kabilang sa atin, sila ay nananatili sana sa atin.'

Ang taong 'nawalan' ng kanyang kaligtasan ay hindi kailanman nagkaroon nito.
Ang taong 'ipinanganak na muli' ay hindi maaaring maging hindi ipinanganak.""",
    "scripture_connections": [
        {
            "reference": "Juan 10:28-29",
            "text": jn_10_28_29_text if not err else en_data["cards"][2]["scripture_connections"][0]["text"]
        },
        {
            "reference": "Mga Taga-Roma 8:38-39",
            "text": rom_8_38_39_text if not err2 else en_data["cards"][2]["scripture_connections"][1]["text"]
        },
        {
            "reference": "Mga Taga-Filipos 1:6",
            "text": phil_1_6_text if not err3 else en_data["cards"][2]["scripture_connections"][2]["text"]
        },
        {
            "reference": "2 Kay Timoteo 2:13",
            "text": tim_2_13_text if not err4 else en_data["cards"][2]["scripture_connections"][3]["text"]
        }
    ],
    "revelation_key": "Ang kaligtasan ay hindi nakadepende sa iyong kakayahang kumapit sa Diyos. Nakadepende ito sa kakayahan ng Diyos na kumapit sa iyo. At hindi Siya bumitaw."
}

# Card 4: What About Deliberate Sin?
card4 = {
    "order": 4,
    "type": "necessity_emphasis",
    "icon": "🛡️",
    "title": "Paano ang Sinasadyang Kasalanan?",
    "subtitle": "Pagkilala sa pagkakaiba ng disiplina at paghatol",
    "content": """🤔 ANG KARANIWANG PAGTUTOL:

'Ngunit sinasabi ng Mga Hebreo 10:26: Kung patuloy tayong nagkakasala nang sadya matapos nating matanggap ang kaalaman ng katotohanan, walang natitirang handog para sa mga kasalanan.'

Sumasalungat ba ito sa walang hanggang kaligtasan?

📖 ANG KONTEKSTO NG MGA HEBREO 10:

Ang may-akda ay nagsasalita tungkol sa mga taong:
• Nakakaalam ng ebanghelyo sa kaisipan
• Ngunit sadyang TINANGGIHAN si Cristo
• Bumalik sa sistemang pag-aalay ng Lumang Tipan
• Hindi kailanman nakaranas ng bagong kapanganakan

Hindi ito tungkol sa isang mananampalataya na nahulog sa kasalanan.
Ito ay tungkol sa isang taong hindi tunay na naniwala.

🔑 ANG PAGKAKAIBA:

ANAK NA NAGKAKASALA:
✓ Nakakaranas ng paninindigan mula sa Banal na Espiritu
✓ Nakakaranas ng disiplina ng ama (Heb 12:6)
✓ Sa huli ay naipanumbalik
✓ Hindi nawawala ang kanilang posisyon bilang anak

ESTRANGHERO NA NAGPAPANGGAP:
✗ Walang panloob na paninindigan
✗ Patuloy na nagpapatigas ng kanilang puso
✗ Sa huli ay tinalikdan ang profesyon ng pananampalataya
✗ Napatunayan na hindi sila kailanman anak (1 Juan 2:19)

⚖️ DISIPLINA laban sa PAGHATOL:

Mga Taga-Roma 8:1 - 'Samakatuwid, wala nang PAGHATOL para sa mga kay Cristo Jesus.'

Mga Hebreo 12:6 - 'Ang Panginoon ay NAGDIDISIPLINA sa taong kanyang minamahal.'

• PAGHATOL = Huling legal na parusa (impiyerno)
• DISIPLINA = Pansamantalang mapagmahal na pagwawasto (pagpapanumbalik)

Kung ikaw ay isang anak, hindi ka kailanman makakaranas ng paghatol.
Ngunit MAKAKARANAS ka ng disiplina kapag nagkasala ka.

🎯 1 JUAN 3:9:

'Walang ipinanganak ng Diyos ang PATULOY na magkakasala, dahil ang binhi ng Diyos ay nananatili sa kanila; hindi sila maaaring MAGPATULOY sa pagkakasala, dahil sila ay ipinanganak ng Diyos.'

• 'PATULOY' (poieō) = gawin nang tuluy-tuloy bilang pamumuhay
• Hindi sinasabi na hindi ka kailanman mahuhulog
• Sinasabi na hindi ka maaaring MAMUHAY nang komportable sa kasalanan

Ang tunay na anak ay maaaring mahulog, ngunit HINDI maaaring manatiling nakabagsak nang walang paninindigan.""",
    "identity_statement": "Ang walang hanggang kaligtasan ay hindi lisensya para magkasala. Ito ang pundasyon para sa tunay na pagpapakabanal. Hindi ka sumusunod dahil sa takot na mawala ang kaligtasan, kundi dahil sa pasasalamat sa pagtanggap nito.",
    "revelation_key": "Kung maaari kang magkasala nang sadya nang walang anumang paninindigan o kawalang-ginhawa, ang tanong ay hindi 'maaari ko bang mawala ang aking kaligtasan?' kundi 'ipinanganak ba ako na muli?'"
}

# Card 5: Personal Discovery
card5 = {
    "order": 5,
    "type": "discovery_activation",
    "icon": "🙏",
    "title": "Pansariling Pagtuklas",
    "discovery_questions": [
        {
            "category": "Katiyakan ng kaligtasan",
            "question": "Nabubuhay ka ba na may katiyakan na ikaw ay 'LUMIPAT NA mula sa kamatayan patungo sa buhay' (perpektong panahunan), o may kawalan ng katiyakan na ikaw ay 'sumusubok lumipat' (kasalukuyang patuloy)?"
        },
        {
            "category": "Batayan ng pagsunod",
            "question": "Sumusunod ka ba sa Diyos dahil sa TAKOT na mawala ang iyong kaligtasan, o dahil sa PASASALAMAT dahil ang iyong kaligtasan ay ligtas na? Ano ang iyong tunay na motibasyon?"
        },
        {
            "category": "Ebidensya ng bagong kapanganakan",
            "question": "May ebidensya ba ng Banal na Espiritu na naninirahan sa iyo? Nakakaranas ka ba ng paninindigan kapag nagkakasala ka? O maaari kang mamuhay sa kasalanan nang walang kawalang-ginhawa?"
        },
        {
            "category": "Pagtitiwala sa Diyos",
            "question": "Kung ang iyong kaligtasan ay nakadepende sa iyong kakayahang 'kumapit' sa Diyos, gaano katagal ka mananatili? Ngunit kung nakadepende ito sa Diyos na kumapit sa iyo, paano babaguhin ang iyong kumpiyansa?"
        }
    ],
    "prayer": {
        "title": "Panalangin ng Katiyakan",
        "content": "Makalangit na Ama, ngayon ay nauunawaan ko nang malinaw na ang aking kaligtasan ay hindi mahinang proseso. Ito ay NATAPOS NA KATOTOHANAN. LUMIPAT ako na (metabebēken - perpektong panahunan) mula sa kamatayan patungo sa buhay. Hindi ako 'sumusubok lumipat.' Hindi ako 'lilipat kung ako ay kumikilos.' LUMIPAT ako na. Tulad ng mga santo na lumabas sa kanilang mga libingan sa Mateo 27, lumabas ako sa aking 'espirituwal na libingan' nang bigyan Mo ako ng buhay. At tulad ng hindi Mo sila binuhay para mawala sila, hindi Mo ako iniligtas para mawala ako. Patawarin Mo ang aking kawalan ng pananampalataya kapag ako ay nabubuhay na may takot na 'mawala' ang iyong tinatakan na ng Banal na Espiritu. Tulungan Mo akong sumunod hindi dahil sa takot ng paghatol, kundi dahil sa pasasalamat sa pag-ampon. Hindi ako empleyado na naka-probation. Ako ay isang ANAK na may garantisadong pamana. Hindi ako maaaring maging 'hindi ipinanganak.' Salamat sa Iyong hindi masisira na katapatan. Sa ngalan ni Jesus, Amen."
    }
}

# Add all cards
fil_data["cards"] = [card1, card2, card3, card4, card5]

# Save the translation
os.makedirs(os.path.dirname(FIL_FILE), exist_ok=True)
with open(FIL_FILE, 'w', encoding='utf-8') as f:
    json.dump(fil_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ Translation saved to: {FIL_FILE}")
print(f"📊 Estimated reading time: {fil_data['estimated_reading_minutes']} minutes")
print(f"📖 Bible version: {fil_data['version']}")

resolver.close()
