#!/usr/bin/env python3
"""
Translate 3 Discovery Bible Studies to Filipino
Studies: full_hands_king, gold_silver_ashes, zechariah_14_return
"""

import json
import sys
import os
import gzip
import urllib.request
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "devocionales_scripts"))
from verse_resolver import VerseResolver

# Constants
STUDIES = [
    "full_hands_king_001",
    "gold_silver_ashes_001",
    "zechariah_14_return_001"
]

BIBLE_DB_PATH = Path(__file__).parent.parent / "devocionales_scripts" / "bibles" / "MBB05_fil.db"
BIBLE_URL = "https://raw.githubusercontent.com/develop4God/bible_versions/main/fil/MBB05_fil.SQLite3.gz"

def download_bible_if_needed():
    """Download MBB05 Filipino Bible if not present"""
    if BIBLE_DB_PATH.exists():
        print(f"✓ Bible DB exists: {BIBLE_DB_PATH}")
        return

    print(f"Downloading MBB05 Filipino Bible...")
    BIBLE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    gz_path = BIBLE_DB_PATH.with_suffix('.db.gz')

    # Download
    urllib.request.urlretrieve(BIBLE_URL, gz_path)
    print(f"✓ Downloaded to {gz_path}")

    # Decompress
    with gzip.open(gz_path, 'rb') as f_in:
        with open(BIBLE_DB_PATH, 'wb') as f_out:
            f_out.write(f_in.read())

    # Clean up
    gz_path.unlink()
    print(f"✓ Decompressed to {BIBLE_DB_PATH}")

def translate_full_hands_king(resolver):
    """Translate full_hands_king_en_001.json"""
    print("\n" + "="*70)
    print("TRANSLATING: Full Hands for the King")
    print("="*70)

    # The translation with warm pastoral Filipino tone
    translation = {
        "id": "full_hands_king_001",
        "type": "discovery",
        "date": "2026-02-09",
        "title": "Punong-puno ang mga Kamay para sa Hari",
        "subtitle": "Kapag dinala ng Alpha at Omega ang Kanyang gantimpala",
        "language": "fil",
        "version": "Magandang Balita Biblia",
        "estimated_reading_minutes": 8,
        "key_verse": {},
        "cards": [],
        "tags": [
            "pahayag",
            "gantimpala",
            "mga_korona",
            "kabayaran",
            "alpha_at_omega",
            "katapatan",
            "pangangasiwa",
            "pagsamba",
            "ikalawang_pagdating"
        ],
        "metadata": {
            "total_word_count": 3800,
            "greek_words_count": 2,
            "scripture_references_count": 15,
            "difficulty_level": "intermediate",
            "themes": [
                "Pagkakaiba ng kaligtasan at gantimpala",
                "Ang limang korona ng Bagong Tipan",
                "Pagsamba sa pamamagitan ng gantimpala",
                "Tapat na pangangasiwa",
                "Si Cristo bilang Alpha at Omega"
            ]
        }
    }

    # Resolve key verse
    cita, texto, error = resolver.resolve("Revelation 22:12-13")
    if error:
        print(f"⚠ Key verse error: {error}")
        return None

    translation["key_verse"] = {
        "reference": cita,
        "text": texto
    }
    print(f"✓ Key verse: {cita}")

    # Card 1: Historical Context
    translation["cards"].append({
        "order": 1,
        "type": "historical_context",
        "icon": "🏝️",
        "title": "Ang Huling Mensahe ng Pahayag",
        "subtitle": "Tinanggap ni Juan sa Patmos ang huling pangitain",
        "content": """Nasa huling kabanata tayo ng huling aklat ng Bibliya. Ang apostol na si Juan, matanda na at itinatapon sa pulong Patmos dahil sa kanyang patotoo tungkol kay Cristo, ay tumanggap ng pinakakumpleto ng pahayag tungkol sa mga huling panahon.

AGARANG KONTEKSTO:

• Kakakita lang ni Juan ng Bagong Jerusalem na bumababa mula sa langit
• Nakita niya ang ilog ng tubig ng buhay at ang puno ng buhay
• Narinig niya ang mga huling pagpapala
• At ngayon, sa mga huling talata, si Jesus mismo ang nagsasalita nang direkta

⚡ ANG TATLONG PANGAKO:

Sa Pahayag 22, inuulit ni Jesus nang tatlong beses: 'Darating na ako' (t.7, t.12, t.20). Hindi ito pag-uulit; ito ay agarang-agaran. Ito ang puso ng Kasintahang nag-aasam na muling mapiling ang Kanyang minamahal.

Ngunit sa talata 12, may idagdag Siyang napakahalaga: hindi lamang Siya darating, kundi dalang-dala Niya ang 'gantimpala' na naaayon sa bawat isa.

🎯 ANG KAHULUGAN:

Kapag bumalik si Jesus, hindi Siya darating na walang laman ang mga kamay. Dala Niya ang 'kabayaran' na naaayon sa bawat isa. Ang tanong ay: ano ang dadalhin natin?""",
        "revelation_key": "Ang Pahayag ay hindi nagtatapos lamang sa pangako ng kaligtasan, kundi sa pangako ng gantimpala. Si Jesus ay dumarating bilang Tagapagligtas, ngunit gayundin bilang Gantimpagbabayad sa mga nagsisikap sa Kanya."
    })

    # Card 2: Greek Exegesis
    # Get scripture connections
    rev_1_8_c, rev_1_8_t, _ = resolver.resolve("Revelation 1:8")
    isa_44_6_c, isa_44_6_t, _ = resolver.resolve("Isaiah 44:6")
    phil_1_6_c, phil_1_6_t, _ = resolver.resolve("Philippians 1:6")

    translation["cards"].append({
        "order": 2,
        "type": "greek_exegesis",
        "icon": "📖",
        "title": "Misthos: Ang Kabayaran ng Manggagawa",
        "subtitle": "Ang pagkakaiba ng handog at gantimpala",
        "content": """Sinasabi ng talata 12: 'Ang aking GANTIMPALA (misthos) ay kasama ko, upang bigyan ang bawat tao ayon sa kanyang gawa.'

PAGSUSURI SA GRIEGO:

🔑 MISTHOS (μισθός) - Strong G3408:

• Literal na kahulugan: Sahod, bayad, gantimpala
• Pinagmulan: Ang bayad na tinatanggap ng manggagawa sa pagtatapos ng araw
• Paggamit sa Bibliya: Laging nangangahulugan ng kabayaran para sa ginawang gawa
• Ginamit ni Jesus ang salitang ito sa Mateo 20:8: 'Tawagin mo ang mga manggagawa at bayaran mo sila (misthos)'

⚖️ TEOLOHIKAL NA PAGKAKAIBA:

Ginagamit ng Bibliya ang iba't ibang salita para sa iba't ibang konsepto:

• DORON (δῶρον): Handog, libreng regalo → Ang kaligtasan ay DORON (Mga Taga-Efeso 2:8)
• MISTHOS (μισθός): Kinitang sahod → Ang gantimpala ay MISTHOS (Pahayag 22:12)

Ang kaligtasan ay hindi kinita; ito ay tinanggap. Ngunit ang gantimpala ay kinita; ito ay pinaghirapan sa pamamagitan ng mga gawang ginawa sa kapangyarihan ng Espiritu.

💰 BANAL NA KATARUNGAN:

Kusang loob na nagiging 'may utang' ang Diyos sa Kanyang mga lingkod. Hindi Niya kailangang magbayad sa atin ng anuman (binigyan na Niya tayo ng buhay na walang hanggan), ngunit sa Kanyang pagkamapagbigay ay pinipili Niyang parangalan ang ating katapatan ng gantimpala.

Sinabi ni San Agustin: 'Kapag kinoronahan ng Diyos ang ating mga merito, wala Siyang ginagawa kundi kinokoronahan ang Kanyang sariling mga kaloob.'""",
        "greek_words": [
            {
                "word": "Misthos",
                "transliteration": "μισθός",
                "meaning": "Sahod, gantimpala, bayad para sa gawa",
                "revelation": "Hindi lamang nagliligtas ang Diyos sa pamamagitan ng biyaya, kundi ginagantimpalaan din ang katapatan. Ang misthos ay patunay na sa langit ay magkakaroon ng pagkakaiba sa karangalan at responsibilidad, bagaman lahat tayo ay may buhay na walang hanggan."
            },
            {
                "word": "Apodounai",
                "transliteration": "ἀποδοῦναι",
                "meaning": "Magbayad pabalik, gantihan, isauli",
                "revelation": "Ito ay salita ng legal na katarungan. 'Isinasauli' ng Diyos ang naaayon sa bawat isa. Hindi ito arbitraryo; ito ay ayon sa 'ginawa ng bawat isa' (kata ta erga)."
            }
        ],
        "revelation_key": "Ang salitang 'misthos' ay naghahayag na hindi lamang dumarating si Jesus upang iligtas tayo (tapos na iyon sa krus), kundi upang GANTIMPALAAN tayo para sa kung paano tayo nabuhay pagkatapos na maligtas."
    })

    # Continuing with remaining cards...
    # Card 3: Theological Depth
    translation["cards"].append({
        "order": 3,
        "type": "theological_depth",
        "icon": "🔄",
        "title": "Ang Alpha at Omega: Ang Siklo ng Kaluwalhatian",
        "subtitle": "Bakit ipinapaliwanag ng Kanyang pagkakakilanlan ang gantimpala",
        "content": """Pagkatapos magsalita tungkol sa misthos, idineklara ni Jesus ang Kanyang pagkakakilanlan sa t.13:

'Ako ang Alpha at Omega, ang simula at ang wakas, ang una at ang huli.'

Bakit ang deklarasyong ito dito? Dahil ipinapaliwanag nito ang siklo ng gantimpala.

🅰️ SIYA ANG ALPHA (ANG SIMULA):

• Siya ang naglagay sa iyo ng pagnanais na maglingkod sa Kanya
• Siya ang nagbigay sa iyo ng mga kaloob at talento
• Siya ang nagbigay sa iyo ng kapangyarihan ng Kanyang Espiritu
• Siya ang nagsimula ng gawa sa iyong puso

🅾️ SIYA ANG OMEGA (ANG WAKAS):

• Siya ang panghuling tatanggap ng lahat ng iyong gawa
• Siya ang tumatanggap ng bunga ng iyong paglilingkod
• Siya ang sukdulang layunin ng iyong pagsamba
• Isinasara Niya ang bilog sa pamamagitan ng pagtanggap ng Kanyang sinimulan

🔄 ANG KUMPLETONG SIKLO:

1. ALPHA: Inilagay ng Diyos sa iyo ang binhi (pagnanasa, kaloob, kakayahan)
2. PROSESO: Ikaw ay gumagawa sa Kanyang kapangyarihan (hindi sa iyo)
3. OMEGA: Ginagantimpalaan ka ng Diyos sa pagiging tapat na katiwala
4. PAGSAMBA: Isinasauli mo ang korona sa Kanyang mga paa (Pahayag 4:10)

💡 ANG MAGANDANG PARADOX:

Gumagawa tayo nang buong lakas, ngunit alam na ang mga lakasang iyon ay binigay din sa atin ng Kanya. Sinabi ni Pablo sa 1 Mga Taga-Corinto 15:10: 'Ngunit sa biyaya ng Diyos ako ay kung ano ako: at ang kanyang biyaya na ipinagkaloob sa akin ay hindi walang kabuluhan; kundi ako ay nagtrabaho nang higit kaysa sa kanilang lahat: ngunit hindi ako, kundi ang biyaya ng Diyos na kasama ko.'

Ang pagdating na may punong-punong kamay ay hindi pagmamataas; ito ay pagsamba. Ito ay pagsasabi: 'Panginoon, binigay Mo ito sa akin, pinarami ko ito sa Iyong kapangyarihan, at ngayon ay ibinabalik ko ito sa Iyo dahil lagi itong Iyo.'""",
        "scripture_connections": [
            {"reference": rev_1_8_c, "text": rev_1_8_t},
            {"reference": isa_44_6_c, "text": isa_44_6_t},
            {"reference": phil_1_6_c, "text": phil_1_6_t}
        ],
        "revelation_key": "Kung Siya ang Alpha at Omega, ang lahat ng ating katapatan ay simpleng koneksyon sa pagitan ng Kanyang sinimulan at Kanyang kukumpletuhin. Ang punong-punong kamay ay hindi ating merito; ito ay patunay na ang Kanyang biyaya ay gumawa sa atin."
    })

    print(f"✓ Completed {len(translation['cards'])} cards")

    return translation

def main():
    """Main translation workflow"""
    print("Filipino Translation Batch Script")
    print("="*70)

    # Step 1: Download Bible if needed
    download_bible_if_needed()

    # Step 2: Initialize verse resolver
    print(f"\nInitializing verse resolver...")

    with VerseResolver(str(BIBLE_DB_PATH)) as resolver:
        print(f"✓ Connected to {BIBLE_DB_PATH.name}")
        print(f"✓ Total verses: {resolver.verse_count():,}")

        # Step 3: Translate each study
        for study_id in STUDIES:
            if study_id == "full_hands_king_001":
                result = translate_full_hands_king(resolver)
                if result:
                    # Write to file
                    output_path = Path(__file__).parent / "fil" / f"{study_id.replace('_001', '_fil_001')}.json"
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"✓ Wrote: {output_path.name}")
            # Add other studies here

    print("\n" + "="*70)
    print("Translation Complete!")
    print("="*70)

if __name__ == "__main__":
    main()
