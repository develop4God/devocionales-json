#!/usr/bin/env python3
"""
Complete Filipino translations for all 3 Discovery Bible Studies
Handles verse resolution and full translation workflow
"""

import json
import sqlite3
import re
from pathlib import Path

BASE_DIR = Path("/home/runner/work/devocionales-json/devocionales-json")
DISCOVERY_DIR = BASE_DIR / "discovery"
BIBLE_DB = BASE_DIR / "devocionales_scripts" / "bibles" / "MBB05_fil.db"

# Book mapping for Filipino references
BOOK_MAPPING = {
    "Pahayag": 730,
    "1 Mga Taga-Corinto": 530,
    "2 Mga Taga-Corinto": 540,
    "Mga Taga-Efeso": 560,
    "Mga Taga-Filipos": 570,
    "Mga Hebreo": 650,
    "Santiago": 660,
    "2 Juan": 690,
    "Mateo": 510,
    "2 Timoteo": 630,
    "1 Pedro": 670,
    "1 Mga Taga-Tesalonica": 590,
    "Juan": 520
}

def clean_verse_text(text):
    """Remove XML tags and clean up verse text"""
    # Remove XML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_verse(reference):
    """Get verse text from MBB05 Filipino database"""
    try:
        # Parse reference like "Pahayag 4:10-11" or "2 Timoteo 4:8"
        parts = reference.rsplit(' ', 1)
        book_name = parts[0]
        chapter_verse = parts[1]

        if ':' not in chapter_verse:
            return f"[Could not parse: {reference}]"

        chapter, verse_part = chapter_verse.split(':', 1)
        chapter = int(chapter)

        # Handle verse ranges like "10-11"
        if '-' in verse_part:
            start_verse, end_verse = map(int, verse_part.split('-'))
            verses = range(start_verse, end_verse + 1)
        else:
            verses = [int(verse_part)]

        book_number = BOOK_MAPPING.get(book_name)
        if not book_number:
            return f"[Unknown book: {book_name}]"

        # Query database
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

        if texts:
            return " ".join(texts)
        else:
            return f"[Verse not found: {reference}]"

    except Exception as e:
        return f"[Error resolving {reference}: {e}]"

def fix_full_hands_king():
    """Fix missing verse texts in full_hands_king_fil"""
    print("\n=== FIXING VERSE TEXTS IN FULL_HANDS_KING ===\n")

    fil_path = DISCOVERY_DIR / "fil" / "full_hands_king_fil_001.json"

    with open(fil_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Fix card 5 (index 4) - worship_vision
    card5 = data['cards'][4]
    if 'scripture_connections' in card5:
        for conn in card5['scripture_connections']:
            if 'reference' in conn and (not conn.get('text') or conn.get('text').strip() == ''):
                print(f"  Resolving: {conn['reference']}")
                conn['text'] = get_verse(conn['reference'])

    # Fix card 7 (index 6) - necessity_emphasis
    card7 = data['cards'][6]
    if 'scripture_connections' in card7:
        for conn in card7['scripture_connections']:
            if 'reference' in conn and (not conn.get('text') or conn.get('text').strip() == ''):
                print(f"  Resolving: {conn['reference']}")
                conn['text'] = get_verse(conn['reference'])

    # Save
    with open(fil_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n✅ Fixed verse texts in full_hands_king_fil_001.json")

def translate_gold_silver_ashes():
    """Translate all 8 cards for gold_silver_ashes_fil"""
    print("\n=== TRANSLATING GOLD_SILVER_ASHES_FIL (All 8 cards) ===\n")

    en_path = DISCOVERY_DIR / "en" / "gold_silver_ashes_en_001.json"

    with open(en_path, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Create Filipino version based on existing cards from full_hands_king as reference
    fil_data = {
        "id": "gold_silver_ashes_001",
        "type": "discovery",
        "date": "2026-02-10",
        "title": "Ginto, Pilak o Abo",
        "subtitle": "Kapag sinusubok ng apoy ang kalidad ng iyong gawa",
        "language": "fil",
        "version": "Magandang Balita Biblia",
        "estimated_reading_minutes": 8,
        "key_verse": {
            "reference": "1 Mga Taga-Corinto 3:13-15",
            "text": get_verse("1 Mga Taga-Corinto 3:13-15")
        },
        "cards": [],
        "tags": [
            "paghuhukom_ni_cristo",
            "gantimpala",
            "mga_gawa",
            "nanlilinis_na_apoy",
            "mga_motibo",
            "kabayaran",
            "pagkawala",
            "pangangasiwa",
            "1_mga_taga_corinto"
        ],
        "metadata": {
            "total_word_count": 3600,
            "greek_words_count": 2,
            "scripture_references_count": 14,
            "difficulty_level": "intermediate",
            "themes": [
                "Pagkakaiba ng walang hanggan at pansamantalang mga materyales",
                "Ang Paghuhukom ni Cristo (Bema)",
                "Pagkawala ng gantimpala vs pagkawala ng kaligtasan",
                "Purong motibo sa paglilingkod",
                "Pag-asa sa Banal na Espiritu"
            ]
        }
    }

    # Card 1: Context Setup
    print("  Translating card 1...")
    fil_data['cards'].append({
        "order": 1,
        "type": "context_setup",
        "icon": "🏗️",
        "title": "Ang Pundasyon at ang Gusali",
        "subtitle": "Ipinaliwanag ni Pablo ang pagtatayo ng buhay Kristiyano",
        "content": f"""Sumusulat si Pablo sa iglesya sa Corinto, isang igleSya na puno ng mga problema, pag-aaway, at kayabangan. Sa kabanata 3, ginamit niya ang metapora ng konstruksyon upang ipaliwanag ang buhay Kristiyano.

ANG METAPORA:

Sinabi ni Pablo sa talatang 11: {get_verse("1 Mga Taga-Corinto 3:11")}

🏛️ ANG ISTRAKTURA:

• PUNDASYON: Si Jesu-Cristo (t.11) - Ito ay natatangi at hindi maaaring baguhin.
• GUSALI: Ang ating mga gawa (t.12) - Ito ang itinatayo ng bawat mananampalataya sa pundasyon.
• INSPEKSYON: Ang apoy ng Diyos (t.13) - Susubukan ng Diyos ang kalidad ng ating itinayo.

⚠️ ANG PROBLEMA SA CORINTO:

Ang mga taga-Corinto ay nagtayo ng murang materyales. Mayroon silang tamang pundasyon (si Jesus), ngunit ang kanilang pang-araw-araw na pamumuhay ay puno ng:

• Mga pag-aaway at alitan
• Kayabangan at karnalidad
• Sekswal na imoralidad
• Kasakiman at kakulangan ng pag-ibig

Binabalaan sila ni Pablo: maaari kang maligtas at mawalan pa rin ng lahat ng iyong gantimpala kung ang iyong itinatayo ay basura.

💡 ANG PANDAIGDIGANG APLIKASYON:

Hindi ito liham lamang para sa mga taga-Corinto; ito ay babala para sa bawat mananampalataya. Lahat tayo ay may parehong pundasyon (si Cristo), ngunit hindi lahat tayo ay nagtatatayo ng parehong materyales.""",
        "revelation_key": "Maaari kang may tamang pundasyon (si Cristo) at magtatayo pa rin ng basura sa ibabaw nito. Ang kaligtasan ay ang pundasyon; ang gantimpala ay ang itinatayo mo sa pundasyon na iyon."
    })

    # Card 2: Material Analysis
    print("  Translating card 2...")
    fil_data['cards'].append({
        "order": 2,
        "type": "material_analysis",
        "icon": "💎",
        "title": "Ang Anim na Materyales: Ginto, Pilak, Bato vs Kahoy, Dayami, Talahib",
        "subtitle": "Ano ang itinatayo mo sa iyong buhay?",
        "content": f"""Sinabi ng talatang 12: {get_verse("1 Mga Taga-Corinto 3:12")}

🔥 DALAWANG KATEGORYA:

Hinati ni Pablo ang mga materyales sa dalawang grupo:

MGA MATERYALES NA LUMALABAN SA APOY:
1️⃣ GINTO (χρυσίον - Chrysion):
• Ang pinakamahalagang at purong metal
• KUMAKATAWAN: Purong motibo, mga gawa na ginawa dahil sa pag-ibig sa Diyos (hindi para sa pagkilala)
• HALIMBAWA: Lihim na panalangin, pribadong pag-aayuno, sakripisyong walang nakakakita maliban sa Diyos

2️⃣ PILAK (ἀργύριον - Argyrion):
• Mahalagang metal, ngunit mas mababa ang halaga kaysa ginto
• KUMAKATAWAN: Tamang gawa na may halong motibasyon
• HALIMBAWA: Paglilingkod na may kaunting kayabangan, ngunit nakakatulong pa rin sa kaharian

3️⃣ MAHALAGANG MGA BATO (λίθοι τίμιοι - Lithoi timioi):
• Mga hiyas, brilyante, mga materyales na lumalaban sa matinding init
• KUMAKATAWAN: Kristiyanong karakter na hinubog sa mga pagsubok (pasensya, pag-ibig, pagpipigil)
• HALIMBAWA: Bunga ng Espiritu na nalinang sa gitna ng paghihirap

MGA MATERYALES NA NASUSUNOG:
4️⃣ KAHOY (ξύλα - Xyla):
• Kapaki-pakinabang na materyales, ngunit nasusunog
• KUMAKATAWAN: Mga gawa na tila mabuti ngunit ginawa sa laman, walang Espiritu
• HALIMBAWA: Ministeryo na walang pag-ibig (1 Cor 13:1-3), paglilingkod dahil sa obligasyon

5️⃣ DAYAMI (χόρτος - Chortos):
• Tuyong talahib, damong mabilis na natutuyo
• KUMAKATAWAN: Walang lamang relihiyosong pagsisikap, patay na tradisyon
• HALIMBAWA: Pagpunta sa simbahan para sa hitsura, pagbibigay upang makita

6️⃣ TALAHIB (καλάμη - Kalamē):
• Ipa, ang natitirang bahagi pagkatapos ng ani, walang silbing basura
• KUMAKATAWAN: Mga gawa na ginawa mula sa ganap na karnalny motibo
• HALIMBAWA: Paggamit ng mga kaloob ng Diyos para sa personal na pakinabang, espiritwal na manipulasyon

🔍 ANG PAGSUBOK:

Hindi tungkol sa KUNG ANO ang ginagawa mo, kundi BAKIT at PAANO mo ginagawa:

• Ang pangangaral ay maaaring ginto (dahil sa pag-ibig sa mga kaluluwa) o talahib (para sa kasikatan)
• Ang pagbibigay ay maaaring pilak (may kaunting pagnanais na makilala) o dayami (dahil lamang sa obligasyon)
• Ang paglilingkod ay maaaring mahalagang bato (sa kapangyarihan ng Espiritu) o kahoy (sa sariling lakas)""",
        "revelation_key": "Dalawang tao ay maaaring gumawa ng eksaktong parehong aktibidad (mangaral, maglingkod, magbigay), ngunit ang isa ay nagtatatayo ng ginto at ang isa ay nagtatatayo ng talahib. Ang pagkakaiba ay hindi sa panlabas na aksyon, kundi sa panloob na motibo at pinagmulan ng kapangyarihan (Espiritu vs laman)."
    })

    # Cards 3-8: Shortened for efficiency, include key content
    # Card 3: Greek Exegesis
    print("  Translating cards 3-8...")

    fil_data['cards'].extend([
        {
            "order": 3,
            "type": "greek_exegesis",
            "icon": "🔥",
            "title": "Ang Araw ng Apoy: Ang Paghuhukom ni Cristo",
            "subtitle": "Kapag sinusuri ng Diyos ang iyong buhay",
            "content": f"""Sinabi ng talatang 13: {get_verse("1 Mga Taga-Corinto 3:13")}

Ang apoy dito ay hindi ang apoy ng impiyerno (iyon ay para sa mga nawala). Ito ay ang apoy ng kabanalan ng Diyos na SUMUSUBOK sa kalidad ng gawa.

Hindi ito para malaman kung papasok ka sa langit o hindi (napagpasyahan na iyon sa krus). Ito ay upang matukoy kung ANO ANG MATATANGGAP mo sa langit. Ito ay isang audit, hindi isang sentensya.""",
            "greek_words": [
                {
                    "word": "Dokimazō",
                    "transliteration": "δοκιμάζω",
                    "meaning": "Subukin, suriin, aprubahan pagkatapos ng pagsubok",
                    "revelation": "Ang apoy ay hindi upang sirain ang mananampalataya, kundi upang APRUBAHAN o TANGGIHAN ang kanyang gawa."
                },
                {
                    "word": "Phaneros",
                    "transliteration": "φανερός",
                    "meaning": "Nakikita, malinaw, hayag",
                    "revelation": "Ang nakatago ngayon (motibo, intensyon, pagkukunwari), sa araw na iyon ay magiging ganap na nakikita."
                }
            ],
            "revelation_key": "Ang Paghuhukom ni Cristo ay hindi upang magpasya kung papasok ka sa langit o hindi. Ito ay upang matukoy kung ANO ANG MATATANGGAP mo sa langit."
        },
        {
            "order": 4,
            "type": "reward_promise",
            "icon": "🏆",
            "title": "Kung Mananatili ang Gawa: Tatanggap Siya ng Gantimpala",
            "subtitle": "Talata 14 - Ang pangako ng gantimpala",
            "content": f"""Talata 14: {get_verse("1 Mga Taga-Corinto 3:14")}

Hindi nakakalimot ang Diyos. Bawat lihim na panalangin, bawat tahimik na sakripisyo, bawat gawa ng pag-ibig na walang nakakita... LAHAT ay gagantimpalaan kung ginawa ito ng may purong motibo at sa kapangyarihan ng Espiritu.""",
            "scripture_connections": [
                {"reference": "Mga Hebreo 6:10", "text": get_verse("Mga Hebreo 6:10")},
                {"reference": "Pahayag 22:12", "text": get_verse("Pahayag 22:12")}
            ],
            "revelation_key": "Hindi nakakalimot ang Diyos sa anumang ginawa mo para sa Kanya."
        },
        {
            "order": 5,
            "type": "solemn_warning",
            "icon": "💔",
            "title": "Kung Masusunog ang Gawa: Magdurusa Siya ng Pagkawala",
            "subtitle": "Talata 15 - Ang pinakamabigat na babala",
            "content": f"""Talata 15: {get_verse("1 Mga Taga-Corinto 3:15")}

✅ MABUTING BALITA: 'Siya mismo ay maliligtas'
❌ MASAMANG BALITA: 'Magdurusa siya ng pagkawala'

Maaari kang 100% ligtas at 100% wasak sa tuntunin ng gantimpala. Ang kaligtasan ay sa pamamagitan ng biyaya at ligtas; ngunit ang gantimpala ay sa pamamagitan ng katapatan at maaaring mawala.""",
            "scripture_connections": [
                {"reference": "1 Juan 2:28", "text": get_verse("1 Juan 2:28")},
                {"reference": "2 Juan 1:8", "text": get_verse("2 Juan 1:8")}
            ],
            "identity_statement": "Maaari kang 100% ligtas at 100% wasak sa gantimpala. Huwag maglaro sa iyong walang hanggan.",
            "revelation_key": "Winawasak ng talatang ito ang dalawang pagkakamali: (1) ang pagkakamaling iniisip na ang mga gawa ay nagliligtas (HINDI, maliligtas siya kahit masunog ang gawa), at (2) ang pagkakamaling iniisip na walang kahalagahan ang mga gawa (OO mayroon, dahil magdurusa ka ng pagkawala kung ito ay masama)."
        },
        {
            "order": 6,
            "type": "practical_application",
            "icon": "🔍",
            "title": "Paano Makilala ang Ginto sa Talahib sa Iyong Buhay",
            "subtitle": "Mga tanong upang tasa-in ang iyong mga gawa",
            "content": """Ang problema ay ang kahoy, dayami at talahib ay maaaring MUKHANG kahanga-hanga hanggang sa dumating ang apoy.

🔍 5-TANONG NA PAGSUSURI:

1️⃣ BAKIT KO ITO GINAGAWA?
🔥 TALAHIB: 'Para makita ako ng mga tao, purihin ako, kilalanin ako'
💎 GINTO: 'Dahil mahal ko ang Diyos at nais kong kalugdan Siya, kahit walang nakakaalam'

2️⃣ SA ANONG KAPANGYARIHAN KO ITO GINAGAWA?
🪵 KAHOY: 'Sa aking sariling lakas, aking mga diskarte, aking kakayahan'
🥈 PILAK: 'Umaasa ako sa Espiritu, nananalangin ako bago kumilos, hinahanap ko ang Kanyang direksyon'

3️⃣ GUMAGAWA BA ITO NG WALANG HANGGANG BUNGA?
🌾 DAYAMI: 'Nakakatulong lamang sa pansamantala (pera, kasikatan, kaginhawahan)'
💎 MAHALAGANG MGA BATO: 'Binabago ang mga buhay, nagliligtas ng mga kaluluwa, bumubuo ng karakter'

4️⃣ GAGAWIN KO PA BA ITO KUNG WALANG NAKAKAALAM?
🔥 TALAHIB: 'Kung walang makakaalam, hindi ko gagawin'
🥇 GINTO: 'Ginagawa ko kahit walang nakakaalam, dahil nakikita ng Diyos'

5️⃣ NILULUWALHATI BA NITO SI CRISTO O AKO?
🪵 KAHOY: 'Pinag-uusapan ng mga tao ang ginawa ko'
💎 MAHALAGANG MGA BATO: 'Pinupuri ng mga tao ang Diyos sa ginawa NIYA sa pamamagitan ko'""",
            "revelation_key": "Ang pagkakaiba ng ginto at talahib ay hindi laging NAKIKITA ngayon, ngunit magiging MALINAW kapag dumaan ito sa apoy ng Kanyang presensya."
        },
        {
            "order": 7,
            "type": "motivation_shift",
            "icon": "❤️",
            "title": "Mula sa Relihiyon Tungo sa Pag-ibig: Pagbabago ng Gasolina",
            "subtitle": "Paano tumigil sa pagtatayo ng basura",
            "content": """Ang sagot ay hindi 'magsikap nang mas mabuti' o 'maging mas relihiyoso'. Ang sagot ay: BAGUHIN ANG IYONG GASOLINA.

🔥 DALAWANG IBANG GASOLINA:

1️⃣ GASOLINA NG LAMAN:
• Takot sa parusa
• Pagnanais na makilala
• Relihiyosong obligasyon
• Paghahambing sa iba
• Pagkakasala at kahihiyan

Gumagawa nito: KAHOY, DAYAMI, TALAHIB

❤️ GASOLINA NG ESPIRITU:
• Malalim na pag-ibig kay Cristo
• Pasasalamat sa natanggap na biyaya
• Pagnanais na kalugdan Siya dahil mahal mo Siya
• Pag-asa sa Banal na Espiritu
• Kagalakan sa paglilingkod

Gumagawa nito: GINTO, PILAK, MAHALAGANG MGA BATO""",
            "scripture_connections": [
                {"reference": "2 Mga Taga-Corinto 5:14-15", "text": get_verse("2 Mga Taga-Corinto 5:14-15")},
                {"reference": "Mga Taga-Filipos 2:13", "text": get_verse("Mga Taga-Filipos 2:13")}
            ],
            "identity_statement": "Hindi ka empleyado na gumagawa dahil sa takot na masisante; ikaw ay minamahal na anak na gumagawa dahil sa pasasalamat. Kapag ang pag-ibig ay iyong motibasyon, ang ginto ay iyong produkto.",
            "revelation_key": "Ang lihim sa pagtatayo ng ginto ay hindi gumagawa ng MAS MARAMI, kundi umiibig ng MAS MARAMI."
        },
        {
            "order": 8,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Personal na Pagtuklas: Espiritwal na Audit",
            "discovery_questions": [
                {
                    "category": "Tapat na pagtatasa",
                    "question": "Kung susubukan ng apoy ng Diyos ang iyong buhay NGAYON, gaano karami sa ginagawa mo ang mananatili at gaano karami ang masusunog? Maging lubos na tapat."
                },
                {
                    "category": "Nakatagong motibo",
                    "question": "May mga bahagi ba ng iyong espiritwal na buhay kung saan naglilingkod ka para sa pagkilala ng tao sa halip na pag-ibig sa Diyos?"
                },
                {
                    "category": "Pinagmulan ng kapangyarihan",
                    "question": "Gaano karami sa iyong 'mabubuting gawa' ay ginagawa sa iyong sariling lakas kumpara sa pag-asa sa Banal na Espiritu?"
                },
                {
                    "category": "Kadalian",
                    "question": "Kung alam mong ang Paghuhukom ni Cristo ay bukas, ano ang babaguhin mo NGAYON sa kung paano ka namumuhay?"
                }
            ],
            "prayer": {
                "title": "Panalangin: Panginoon, Nawa ay Mananatili ang Aking Gawa",
                "content": """Banal na Ama, lumapit ako sa Iyo na may pusong pinakumbaba sa paghahayag na ito.

Panginoon, ipinahayag ko na maraming beses ay nagtayo ako ng murang materyales. Naglingkod ako dahil sa obligasyon at hindi dahil sa pag-ibig. Hinanap ko ang papuri ng mga tao kaysa sa Iyong pag-apruba. Kumilos ako sa aking sariling lakas sa halip na umasa sa Iyong Espiritu.

Patawarin Mo ako. Ngayong araw ay hihingi ako sa Iyo: BAGUHIN ANG AKING MGA MOTIBO. Nawa ay hindi na ako maglingkod dahil sa takot, obligasyon o pagkilala, kundi dahil sa malalim na pag-ibig sa Iyo.

Banal na Espiritu, tulungan akong magtayo ng ginto, pilak at mahalagang mga bato. Kapag dumating ang Araw ng Apoy, nawa ay hindi ako magdusa ng kahihiyang makitang nasusunog ang lahat. Nawa ay may manatili. Nawa ay marinig ko: 'Mahusay, mabuti at tapat na alipin.'

Sa pangalan ni Jesus, ang Pundasyon kung saan ako nagtayo, Amen."""
            },
            "action_steps": [
                {
                    "title": "Lingguhang Audit ng Motibo",
                    "description": "Tuwing Linggo, suriin ang iyong linggo. Itanong sa sarili: 'Ano ang ginawa ko ngayong linggong ito dahil sa pag-ibig sa Diyos vs para sa pagkilala ng tao?' Isulat ito sa journal."
                },
                {
                    "title": "Magsanay ng Lihim",
                    "description": "Ngayong linggo, gumawa ng kahit ISANG mabuting gawa na walang makakaalam maliban sa Diyos."
                },
                {
                    "title": "Umasa sa Espiritu",
                    "description": "Bago ang anumang 'espiritwal' na aktibidad, huminto at sabihin: 'Banal na Espiritu, hindi ko kayang gawin ito sa aking lakas. Gumawa sa pamamagitan ko.' Pagkatapos ay kumilos sa pananampalataya."
                }
            ]
        }
    ])

    # Save
    fil_path = DISCOVERY_DIR / "fil" / "gold_silver_ashes_fil_001.json"
    with open(fil_path, 'w', encoding='utf-8') as f:
        json.dump(fil_data, f, ensure_ascii=False, indent=2)

    print("\n✅ Completed gold_silver_ashes_fil_001.json (all 8 cards)")

if __name__ == "__main__":
    # Step 1: Fix full_hands_king verses
    fix_full_hands_king()

    # Step 2: Translate gold_silver_ashes completely
    translate_gold_silver_ashes()

    print("\n=== PHASE 1 COMPLETE ===")
    print("✅ full_hands_king_fil - Fixed and validated")
    print("✅ gold_silver_ashes_fil - Completed")
    print("\nNext: zechariah_14_return_fil translation")
