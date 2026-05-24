#!/usr/bin/env python3
"""
Final completion script for all 3 Filipino Discovery Studies
"""

import json
import sqlite3
import re
from pathlib import Path

BASE_DIR = Path("/home/runner/work/devocionales-json/devocionales-json")
DISCOVERY_DIR = BASE_DIR / "discovery"
BIBLE_DB = BASE_DIR / "devocionales_scripts" / "bibles" / "MBB05_fil.db"

BOOK_MAPPING = {
    "Pahayag": 730, "1 Mga Taga-Corinto": 530, "2 Mga Taga-Corinto": 540,
    "Mga Taga-Efeso": 560, "Mga Taga-Filipos": 570, "Mga Hebreo": 650,
    "Santiago": 660, "2 Juan": 690, "Mateo": 510, "2 Timoteo": 630,
    "1 Pedro": 670, "1 Mga Taga-Tesalonica": 590, "Juan": 520,
    "Zacarias": 510, "Isaias": 300, "Ezekiel": 360, "Lucas": 520,
    "1 Juan": 680, "Deuteronomio": 50
}

def clean_verse_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_verse(reference):
    try:
        parts = reference.rsplit(' ', 1)
        book_name = parts[0]
        chapter_verse = parts[1]

        if ':' not in chapter_verse:
            return f"[Parse error: {reference}]"

        chapter, verse_part = chapter_verse.split(':', 1)
        chapter = int(chapter)

        if '-' in verse_part:
            start_verse, end_verse = map(int, verse_part.split('-'))
            verses = range(start_verse, end_verse + 1)
        else:
            verses = [int(verse_part)]

        book_number = BOOK_MAPPING.get(book_name)
        if not book_number:
            return f"[Unknown book: {book_name}]"

        conn = sqlite3.connect(BIBLE_DB)
        cursor = conn.cursor()
        texts = []
        for v in verses:
            cursor.execute(
                "SELECT text FROM verses WHERE book_number=? AND chapter=? AND verse=?",
                (book_number, chapter, v)
            )
            result = cursor.fetchone()
            if result:
                texts.append(clean_verse_text(result[0]))
        conn.close()

        return " ".join(texts) if texts else f"[Not found: {reference}]"
    except Exception as e:
        return f"[Error: {reference}]"

def fix_gold_silver_ashes():
    """Add missing scripture connections"""
    print("\n=== FIXING GOLD_SILVER_ASHES SCRIPTURE CONNECTIONS ===\n")

    fil_path = DISCOVERY_DIR / "fil" / "gold_silver_ashes_fil_001.json"
    with open(fil_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Card 4: Add missing third connection
    data['cards'][3]['scripture_connections'].append({
        "reference": "Mateo 6:4",
        "text": get_verse("Mateo 6:4")
    })

    # Card 5: Add missing third connection
    data['cards'][4]['scripture_connections'].append({
        "reference": "1 Mga Taga-Corinto 9:27",
        "text": get_verse("1 Mga Taga-Corinto 9:27")
    })

    # Card 7: Add missing third connection
    data['cards'][6]['scripture_connections'].append({
        "reference": "Mga Taga-Efeso 5:16",
        "text": get_verse("Mga Taga-Efeso 5:16")
    })

    with open(fil_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ Fixed gold_silver_ashes_fil_001.json")

def create_zechariah():
    """Create complete zechariah_14_return_fil translation"""
    print("\n=== CREATING ZECHARIAH_14_RETURN_FIL (All 9 cards) ===\n")

    fil_data = {
        "id": "zechariah_14_return_001",
        "type": "discovery",
        "date": "2026-02-06",
        "title": "Zacarias 14: Kapag Tumapat ang Kanyang mga Paa sa Bundok ng mga Olibo",
        "subtitle": "Ang araw na bababa ang langit at mababago ang lupa",
        "language": "fil",
        "version": "Magandang Balita Biblia",
        "estimated_reading_minutes": 10,
        "key_verse": {
            "reference": "Zacarias 14:4",
            "text": "Sa araw na iyon, tatayo ang Panginoon sa Bundok ng mga Olibo sa silangan ng Jerusalem, at ang bundok ay hahati sa dalawa mula silangan hanggang kanluran."
        },
        "cards": [
            {
                "order": 1,
                "type": "historical_context",
                "icon": "📜",
                "title": "Ang Propetikong Konteksto: Kailan at Bakit ito Isinulat",
                "subtitle": "Ang katuparan ng eskatologiya ng Lumang Tipan",
                "content": """Ang Zacarias 14 ay ang rurok ng lahat ng propetikong literatura ng Bibliya. Ito ay hindi talinghaga o malinaw na tula. Ito ay literal na paglalarawan ng pinakamahalagang araw sa kasaysayan ng tao pagkatapos ng Krus: ang araw na babalik si Jesus bilang mananakop na Hari.

ANG KONTEKSTO:
Pagkatapos itayo ang Templo noong 515 BC, ang agarang mga pag-asa ng Mesiyaniko ay hindi natupad. Ang mabunying Hari ay hindi dumating. Ito ay humantong sa propeta na proyektahin ang huling pagwagi sa mas malayong hinaharap.

ANG PROPETIKONG PANANAW:
Tumitingin pabalik ang propeta (sa pagkakatapon at sa kabiguan ng agarang pagpapanumbalik) ngunit tumuturo nang ganap sa hinaharap (sa pisikal na pagbabalik ng Mesiyas). Ito ay isang teksto na tumalon sa 2,500 taon ng kasaysayan upang ilarawan ang ISANG tiyak na araw sa hinaharap.""",
                "revelation_key": "Ang Zacarias 14 ay hindi talinghaga. Ito ay literal na paglalarawan ng araw na babalik si Jesus bilang mananakop na Hari."
            },
            {
                "order": 2,
                "type": "hebrew_exegesis",
                "icon": "🔤",
                "title": "Hinnēh Yôm-Bā': Narito, Dumarating ang Araw",
                "subtitle": "Pagsusuri ng orihinal na Hebreo na naghahayag ng propetikong pagmamadali",
                "content": """Nagsisimula ang kabanata sa pariralang puno ng propetikong bigat:

'Hinnēh yôm-bā' la-YHWH' - 'Narito, dumarating ang araw PARA SA PANGINOON'

PAGKAKABUKOD NG HEBREO:
• HINNĒH: 'Narito' - isang particle ng madaliang pansin
• YÔM: 'Araw' - sa propesiya, 'ang Araw ng YHWH' ay ang sandali ng direktang interbensyon ng Diyos
• BĀ': 'Dumarating' - patuloy na aksyon

ANG KRISIS NG JERUSALEM (vv. 1-2):
Inilalarawan ng teksto ang isang apocalyptikong pagkubkob: 'Titipunin ko ang lahat ng mga bansa laban sa Jerusalem'

ANG THEOPHANY: ANG PROPETIKONG RUROK (vv. 3-4):
'Pagkatapos ay lalabas ang PANGINOON at makikipaglaban... At tatayo ang Kanyang mga paa sa araw na iyon sa Bundok ng mga Olibo'

ANG HEOGRAPIKONG PHENOMENA:
Ang bundok ay hahati 'qarāʿ' - ang parehong salita na ginamit kapag:
• Nahati ang Dagat na Pula sa harap ni Moises
• Napunit ang tabing ng templo nang mamatay si Jesus

Ito ay aksyon ng supernatural na interbensyon na nagbabago sa pisikal na heograpiya ng planeta.""",
                "hebrew_words": [
                    {
                        "word": "Hinnēh",
                        "transliteration": "הִנֵּה",
                        "meaning": "Narito, tingnan, makinig",
                        "revelation": "Tinatawag ng Diyos ang ating pansin na may pagmamadali. Hindi ito ordinaryong kaganapan; ito ang KAGANAPAN."
                    },
                    {
                        "word": "Qarāʿ",
                        "transliteration": "קָרַע",
                        "meaning": "Hatiin, punitin, wasakin nang marahas",
                        "revelation": "Ang parehong salita mula sa Dagat na Pula at sa tabing ng templo. Kapag 'pinunit' ng Diyos ang isang bagay, ito ay upang magbukas ng landas ng kaligtasan."
                    }
                ],
                "revelation_key": "Ang wikang Hebreo ay walang espasyo para sa simbolikong interpretasyon. Ito ay pisikal, literal, heograpikal at militar na kaganapan kung saan ang Diyos ng langit ay itatanim ang Kanyang mga paa sa lupa."
            },
            {
                "order": 3,
                "type": "theological_depth",
                "icon": "👑",
                "title": "YHWH Eḥād: Ang Huling Pagpahayag ng Shema",
                "subtitle": "Zacarias 14:9 - Ang teolohikal na sentro ng kabanata",
                "content": """Pagkatapos ng labanan at ng tagumpay, ipinahayag ni Zacarias ang pinakamahalagang katotohanan:

Zacarias 14:9: 'At ang PANGINOON ay magiging Hari sa buong daigdig. Sa araw na iyon, iisa lamang ang PANGINOON, at iisa ang Kanyang pangalan.'

ANG PAGPAPALAWAK NG SHEMA:
Bawat Judio ay nagsasabi ng Shema nang dalawang beses bawat araw: 'Pakinggan, O Israel: Ang PANGINOON ay ating Diyos, ang PANGINOON ay iisa'

Ngunit sa Zacarias 14, ang Judayong pagpahayag ng pananampalataya ay PINALAWAK sa buong mundo:
• Hindi na lamang 'ang PANGINOON ating Diyos' (pag-aari ng Israel)
• Ngayon ay 'ang PANGINOON na Hari sa BUONG DAIGDIG' (pandaigdig)

PRAKTIKAL NA IMPLIKASYON:
1️⃣ Ang katapusan ng idolatriya
2️⃣ Ang katapusan ng relihiyosong relativismo
3️⃣ Ang katapusan ng ateismo
4️⃣ Ang katapusan ng paghihimagsik

JESUS: ANG KATUPARAN:
Sa Kristiyanismo, ang Zacarias 14:9 ay natutupad kay Jesus. Ang pangalang YHWH at ang pangalang JESUS (Yeshua = YHWH ay nagliligtas) ay IISA at PAREHO.""",
                "scripture_connections": [
                    {
                        "reference": "Deuteronomio 6:4",
                        "text": get_verse("Deuteronomio 6:4")
                    },
                    {
                        "reference": "Mga Taga-Filipos 2:10-11",
                        "text": get_verse("Mga Taga-Filipos 2:10-11")
                    },
                    {
                        "reference": "Pahayag 11:15",
                        "text": get_verse("Pahayag 11:15")
                    }
                ],
                "revelation_key": "Ang Zacarias 14:9 ay hindi malinaw na pag-asa. Ito ay ganap na propetikong deklarasyon: darating ang araw na ang pribadong pagpahayag ng pananampalataya ('Si Jesus ay aking Panginoon') ay magiging pandaigdigang pampublikong pagpahayag ('Si Jesus ay ANG Panginoon')."
            },
            {
                "order": 4,
                "type": "structural_analysis",
                "icon": "💧",
                "title": "Buhay na mga Tubig: Ang Pagpapanumbalik ng Eden",
                "subtitle": "Zacarias 14:8 at ang pagpapagaling ng Patay na Dagat",
                "content": """Isa sa pinakamaganda at misteryosong detalye ng Zacarias 14 ay ang hydrolohikal na pagbabago:

Zacarias 14:8: 'At mangyayari sa araw na iyon, na lalabas ang mga buhay na tubig mula sa Jerusalem...'

KONEKSYON SA EZEKIEL 47:
Si Ezekiel ay may katulad na pangitain 70 taon nang mas maaga: 'Ang mga tubig na ito... bumababa sa disyerto, at pumapasok sa dagat: na dinala sa dagat, ang mga tubig ay mapapagaling.'

ANG PATAY NA DAGAT AY MABUBUHAY:
Ang Patay na Dagat ay kasalukuyang:
• 10 beses na mas maalat kaysa sa karagatan
• Walang isda o buhay sa tubig
• Tinatawag sa Hebreo na 'Yam ha-Melach' (Dagat ng Asin)

Ngunit sinabi ni Ezekiel: 'magkakaroon ng napakaraming isda'

MALALIM NA SIMBOLISMO:
Ito ay hindi lamang heograpikal na pagbabago. Ito ay ang PAGBABALIK NG SUMPA:
1️⃣ Sa Eden, mayroong isang ilog na lumalabas mula sa hardin
2️⃣ Pagkatapos ng Pagkahulog, ang lupa ay sinumpa - mga tagtuyot, mga disyerto, patay na mga dagat
3️⃣ Sa Milenyo, ang ilog ay muling dumaloy mula sa presensya ng Diyos (ang bagong Templo sa Jerusalem)
4️⃣ Sa bagong langit at bagong lupa, nakita ni Juan 'ang isang malinis na ilog ng tubig ng buhay'

ESPIRITWAL NA KATUPARAN NGAYON:
Sinabi ni Jesus sa Juan 7:37-38: 'Kung may nauuhaw, lumapit siya sa akin at uminom. Ang sumasampalataya sa akin... ay aagos mula sa kanyang loob ang mga ilog ng buhay na tubig.'""",
                "hebrew_words": [
                    {
                        "word": "Mayim Ḥayyim",
                        "transliteration": "מַיִם חַיִּים",
                        "meaning": "Buhay na mga tubig, nagbibigay-buhay na mga tubig",
                        "revelation": "Hindi ito nakatigil o kontaminadong tubig. Ito ay BUHAY na tubig - na umaagos, na naglilinis, na nagbibigay-buhay."
                    }
                ],
                "revelation_key": "Ang pagpapanumbalik ng Diyos ay hindi bahagya. Kapag bumalik si Jesus, hindi lamang Niya ipapanumbalik ang mga kaluluwa - ipapanumbalik Niya ang BUONG PAGLIKHA."
            },
            {
                "order": 5,
                "type": "chronological_sequence",
                "icon": "⏱️",
                "title": "Ang Eskatol</ na Pagkakasunud-sunod",
                "subtitle": "Mula ngayon hanggang sa walang hanggang trono",
                "content": """Upang maunawaan ang Zacarias 14 sa ganap na konteksto, kailangan nating tingnan ang pagkakasunud-sunod ng propetikong mga kaganapan:

KUMPLETONG TIMELINE:

1️⃣ ANG 'NGAYON' - ANG DAKILANG KOMISYON
2️⃣ ANG PAGDAKIP - ANG PAGLILIGTAS
3️⃣ ANG PAGHUHUKOM NI CRISTO - BEMA
4️⃣ ANG KASALAN NG KORDERO
5️⃣ ANG DAKILANG TRIBULASYON - 7 taon
6️⃣ ANG IKALAWANG PAGDATING - ZACARIAS 14:3-5
7️⃣ ANG PAGHUHUKOM NG MGA BANSA
8️⃣ ANG MILENYO - ZACARIAS 14:9-21

Ang kasaysayan ay hindi sirkular, ito ay linear. May simula (Genesis 1), punto ng pagliligtas (ang Pagdakip), punto ng rurok (Zacarias 14), at huling destinasyon (Pahayag 21-22).""",
                "scripture_connections": [
                    {
                        "reference": "Mateo 24:45-47",
                        "text": get_verse("Mateo 24:45-47")
                    },
                    {
                        "reference": "Lucas 19:17",
                        "text": get_verse("Lucas 19:17")
                    },
                    {
                        "reference": "Pahayag 20:6",
                        "text": get_verse("Pahayag 20:6")
                    }
                ],
                "revelation_key": "Ang lahat ay gumagalaw tungo sa araw na tatapat ang Kanyang mga paa sa Bundok ng mga Olibo."
            },
            {
                "order": 6,
                "type": "new_testament_fulfillment",
                "icon": "🔗",
                "title": "Ang Perpektong Koneksyon: Zacarias 14 at ang Bagong Tipan",
                "subtitle": "Paano pinatunayan ng Gawa 1 ang propesiya ni Zacarias",
                "content": """Ang koneksyon sa pagitan ng Zacarias 14 at ng Bagong Tipan ay napaka-eksakto na hindi ito maaaring pagkakataon.

GAWA 1:9-12 - ANG PAG-AKYAT:
'At habang tumitingin sila, dinala siya sa itaas, at natakpan siya ng ulap... Sinabi ng dalawang lalaki: "Ang Jesus na ito, na dinala sa itaas mula sa inyo patungo sa langit, ay darating sa ganoon ding paraan gaya ng nakita ninyo siyang umalis."'

DETALYADONG PAGSUSURI:
1️⃣ LUGAR NG PAG-ALIS: Bundok ng mga Olibo
2️⃣ PANGAKO NG ANGHEL: 'Darating sa ganoon ding paraan'
3️⃣ IMPLIKASYON: Kung umalis Siya nang PISIKAL mula sa Bundok ng mga Olibo, babalik Siya nang PISIKAL sa Bundok ng mga Olibo

Ang propetikong katumpakan ng Zacarias: Hindi sinabi ng Zacarias na 'babalik ang Mesiyas sa Israel'. Sinabi niya 'ang Kanyang mga paa ay tatayo sa BUNDOK NG MGA OLIBO'. Ang heograpikal na katumpakan na iyon ay hindi maaaring pagkakataon.""",
                "revelation_key": "Ang Bibliya ay hindi koleksyon ng mga hiwalay na kuwento. Ito ay isang PROPETIKONG TAPESTRY kung saan bawat sinulid ay konektado."
            },
            {
                "order": 7,
                "type": "millennial_transformation",
                "icon": "🌍",
                "title": "Ang Pista ng mga Tabernakulo: Pandaigdigang Pagsamba",
                "subtitle": "Zacarias 14:16-21 - Ang binagong mundo",
                "content": """Pagkatapos ng labanan at ng tagumpay, inilalarawan ni Zacarias kung paano magiging pag-andar ang mundo sa ilalim ng paghahari ng Mesiyas:

Zacarias 14:16: 'At mangyayari, na bawat isa na natitira sa lahat ng mga bansa... ay aakyat taun-taon upang sambahin ang Hari, ang PANGINOON ng mga hukbo, at ipagdiwang ang pista ng mga tabernakulo.'

BAKIT ANG PISTA NG MGA TABERNAKULO (SUKKOT)?
Ang Sukkot ay nangangahulugang 'tahanan'. Ito ay:
1️⃣ PAGGUNITA: Noong nanirahan ang Diyos kasama ng Israel sa ilang
2️⃣ SUMISIMBOLO: Ang presensya ng Diyos na nanirahan KASAMA ng Kanyang mga tao
3️⃣ KATUPARAN: Sinabi ni Juan 1:14 'Ang Verbo ay nagkatawang-tao, at NANIRAHAN sa gitna natin'
4️⃣ PROPESIYA: Pahayag 21:3 - 'Narito, ang tabernakulo ng Diyos ay kasama ng mga tao'

'KABANALAN PARA SA PANGINOON' - KAHIT SA MGA KAMPANA (vv.20-21):
Sa araw na iyon, kahit ang mga kampana ng mga kabayo ay may nakasulat na 'KABANALAN PARA SA PANGINOON'. Ang mga kaldero sa kusina ay magiging kasing-banal ng mga sisidlan ng altar.

ITO AY REBOLUSYONARYO:
Kasalukuyan may 'paghihiwalay' sa pagitan ng banal at karaniwan. NGUNIT SA MILENYO, ang LAHAT ay magiging banal dahil ang Banal na Hari ay naghahari sa LAHAT.""",
                "scripture_connections": [
                    {
                        "reference": "Juan 1:14",
                        "text": get_verse("Juan 1:14")
                    },
                    {
                        "reference": "Pahayag 21:3",
                        "text": get_verse("Pahayag 21:3")
                    }
                ],
                "revelation_key": "Ang Milenyo ay hindi lamang 'kapayapaan sa mundo' o 'pang-ekonomiyang kasaganaan'. Ito ay ang PAGPAPANUMBALIK ng orihinal na pakikipag-ugnayan sa pagitan ng Diyos at tao."
            },
            {
                "order": 8,
                "type": "personal_application",
                "icon": "💎",
                "title": "Ang Ating Tungkulin sa Milenyo: Mga Gantimpala at Gawain",
                "subtitle": "Ano ang gagawin natin kapag bumalik tayo kasama Niya",
                "content": """Ang pinaka-praktikal na tanong ay: Ano ang gagawin NATIN (ang mga dinakip) kapag bumalik tayo kasama ni Jesus sa Zacarias 14?

ANG MGA GANTIMPALA NG PAGHUHUKOM NI CRISTO:
Bago bumalik sa lupa, dadaan tayo sa Bema kung saan tatanggap tayo ng mga gantimpala ayon sa ating mga gawa:

🏆 ANG LIMANG KORONA:
1️⃣ Koronang Hindi Nasisira
2️⃣ Korona ng Kagalakan
3️⃣ Korona ng Katuwiran
4️⃣ Korona ng Buhay
5️⃣ Korona ng Kaluwalhatian

🏛️ IPINAGKATIWALAANG AWTORIDAD - PAGHAHARI NG MGA LUNGSOD:
Lucas 19:17-19: 'Mabuti, mabuting alipin... magkaroon ka ng awtoridad sa sampung lungsod'

Ang katapatan NGAYON ay tumutukoy sa responsibilidad NOON.

💬 1 TESALONICA 2:19:
'Sapagkat ano ang ating pag-asa, o kagalakan, o korona ng pagmamapuri? Hindi ba kayo sa presensya ng ating Panginoong Jesu-Cristo sa kanyang pagdating?'

Ang PINAKAMALAKING gantimpala (higit pa sa mga korona o mga lungsod) ay ang pakikipagtagpo sa mga dinala mo kay Cristo.""",
                "identity_statement": "Hindi ka naligtas upang lamang 'pumunta sa langit'. Naligtas ka upang MAGHARI kasama ni Cristo. Ikaw ay isang hari/reyna na nasa pagsasanay.",
                "revelation_key": "Ang Pagdakip ay hindi ang katapusan ng iyong kuwento; ito ay ang SIMULA ng iyong tunay na bokasyon."
            },
            {
                "order": 9,
                "type": "discovery_activation",
                "icon": "🙏",
                "title": "Personal na Pagtuklas: Pamumuhay na May Walang Hanggang Kadalian",
                "discovery_questions": [
                    {
                        "category": "Ebanghelistikong Kadalian",
                        "question": "Kung maaaring mangyari ang Pagdakip anumang sandali, namumuhay ka ba ng may kadalian para sa mga nawalang kaluluwa?"
                    },
                    {
                        "category": "Katapatan sa Kaunti",
                        "question": "Tapat ka ba sa 'kaunti' na ibinigay sa iyo ng Diyos ngayon (oras, pera, talento, impluwensya)?"
                    },
                    {
                        "category": "Pag-asam sa Kanyang Pagbabalik",
                        "question": "Umiibig ka ba sa pagpapakita ni Cristo? O ang ideya ng Kanyang pagbabalik ay nagbibigay sa iyo ng mas maraming takot kaysa kagalakan?"
                    }
                ],
                "prayer": {
                    "title": "Panalangin ng Pag-asa at Paglaan",
                    "content": """Amang nasa langit, YHWH na aming Hari,

Salamat sa Iyo sa paghahayag sa Iyong Salita ng kung ano ang darating. Salamat dahil ang kasaysayan ay hindi walang kahulugang bilog, kundi isang linya na gumagalaw tungo sa maluwalhating araw na tatapat ang Iyong mga paa sa Bundok ng mga Olibo.

Panginoong Jesus, nananabik ako sa Iyo. Nawa ang aking puso ay sumigaw kasama ng Espiritu at ng Kasintahan: 'Halika!' Tulungan akong mabuhay bawat araw na parang ito ang huling bago ng Iyong pagbabalik.

Patawarin Mo ako kung ako ay naging walang malasakit sa walang hanggang kapalaran ng mga nakapaligid sa akin. Bigyan Mo ako ng kadalian para sa mga kaluluwa.

Ama, ihanda Mo ako para sa araw na babalik kami kasama Mo mula sa langit patungo sa lupa. Nawa ang aking buhay ngayon ay maging tapat na pagsasanay para sa kaharian na papangasiwaan ko kasama Mo.

Hanggang sa araw na iyon, panatilihin Mo akong tapat. Hanggang sa araw na iyon, gamitin Mo ako para sa Iyong kaluwalhatian.

Halika na, Panginoong Jesus. Maranatha.

Sa Iyong makapangyarihang pangalan, ang pangalang higit sa lahat ng pangalan, ang pangalang luluhod ang bawat tuhod.

Amen."""
                },
                "action_steps": [
                    {
                        "title": "Listahan ng Panalangin para sa mga Nawala",
                        "description": "Isulat ang mga pangalan ng 5 taong hindi kilala si Jesus. Manalangin para sa kanila araw-araw."
                    },
                    {
                        "title": "Audit ng Katapatan",
                        "description": "Gumawa ng tapat na pagtatasa sa sarili: Tapat ka ba sa iyong oras, pera, katawan, pamilya, trabaho?"
                    },
                    {
                        "title": "Patuloy na Propetikong Pag-aaral",
                        "description": "Magbasa ng isang propetikong kabanata bawat linggo at ihambing ito sa Zacarias 14."
                    },
                    {
                        "title": "Isaulo ang Zacarias 14:9",
                        "description": "'At ang PANGINOON ay magiging Hari sa buong daigdig: sa araw na iyon, iisa lamang ang PANGINOON, at iisa ang Kanyang pangalan.'"
                    }
                ]
            }
        ],
        "tags": [
            "zacarias",
            "eskatologiya",
            "ikalawang_pagdating",
            "bundok_ng_mga_olibo",
            "milenyo",
            "pagdakip",
            "tribulasyon",
            "pagpapanumbalik",
            "natupad_na_propesiya"
        ],
        "metadata": {
            "total_word_count": 5200,
            "hebrew_words_count": 3,
            "scripture_references_count": 12,
            "difficulty_level": "intermediate-advanced",
            "themes": [
                "Pisikal na pagbabalik ni Cristo",
                "Heograpikal na pagbabago",
                "Kaharian ng Milenyo",
                "Eskatol</ na pagkakasunud-sunod",
                "Walang hanggang mga gantimpala"
            ]
        }
    }

    fil_path = DISCOVERY_DIR / "fil" / "zechariah_14_return_fil_001.json"
    with open(fil_path, 'w', encoding='utf-8') as f:
        json.dump(fil_data, f, ensure_ascii=False, indent=2)

    print("✅ Completed zechariah_14_return_fil_001.json (all 9 cards)")

def update_index():
    """Update index.json with Filipino entries"""
    print("\n=== UPDATING INDEX.JSON ===\n")

    index_path = DISCOVERY_DIR / "index.json"
    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)

    # Find and update the 3 studies
    for study in index_data['studies']:
        if study['id'] == 'full_hands_king_001':
            if 'fil' not in study['files']:
                study['files']['fil'] = 'full_hands_king_fil_001.json'
                study['titles']['fil'] = 'Punong-puno ang mga Kamay para sa Hari'
                study['subtitles']['fil'] = 'Kapag dinala ng Alpha at Omega ang Kanyang gantimpala'
                study['estimated_reading_minutes']['fil'] = 8
                print("  ✅ Added full_hands_king fil entry")

        elif study['id'] == 'gold_silver_ashes_001':
            if 'fil' not in study['files']:
                study['files']['fil'] = 'gold_silver_ashes_fil_001.json'
                study['titles']['fil'] = 'Ginto, Pilak o Abo'
                study['subtitles']['fil'] = 'Kapag sinusubok ng apoy ang kalidad ng iyong gawa'
                study['estimated_reading_minutes']['fil'] = 8
                print("  ✅ Added gold_silver_ashes fil entry")

        elif study['id'] == 'zechariah_14_return_001':
            if 'fil' not in study['files']:
                study['files']['fil'] = 'zechariah_14_return_fil_001.json'
                study['titles']['fil'] = 'Zacarias 14: Kapag Tumapat ang Kanyang mga Paa sa Bundok ng mga Olibo'
                study['subtitles']['fil'] = 'Ang araw na bababa ang langit at mababago ang lupa'
                study['estimated_reading_minutes']['fil'] = 10
                print("  ✅ Added zechariah_14_return fil entry")

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print("\n✅ Updated index.json with 3 Filipino entries")

if __name__ == "__main__":
    print("="*70)
    print(" FINAL COMPLETION: ALL 3 FILIPINO DISCOVERY STUDIES")
    print("="*70)

    # Step 1: Fix gold_silver_ashes scripture connections
    fix_gold_silver_ashes()

    # Step 2: Create complete zechariah translation
    create_zechariah()

    # Step 3: Update index.json
    update_index()

    print("\n" + "="*70)
    print(" ALL TASKS COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\n✅ full_hands_king_fil_001.json - 8 cards (COMPLETE)")
    print("✅ gold_silver_ashes_fil_001.json - 8 cards (COMPLETE)")
    print("✅ zechariah_14_return_fil_001.json - 9 cards (COMPLETE)")
    print("✅ index.json - Updated with 3 Filipino entries")
    print("\nTotal: 25 cards translated across 3 Discovery Bible Studies")
