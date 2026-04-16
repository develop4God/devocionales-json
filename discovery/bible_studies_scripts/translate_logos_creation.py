#!/usr/bin/env python3
"""
Translate logos_creation from English to Tagalog
Uses VerseResolver with ADB_tl.SQLite3 for all scripture lookups
"""

import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../devocionales_scripts'))
from verse_resolver import VerseResolver

# Paths
BASE_DIR = '/home/runner/work/devocionales-json/devocionales-json'
EN_FILE = f'{BASE_DIR}/discovery/en/logos_creation_en_001.json'
TL_FILE = f'{BASE_DIR}/discovery/tl/logos_creation_tl_001.json'
DB_PATH = f'{BASE_DIR}/bible_database/ADB_tl.SQLite3'

def translate_to_tagalog():
    """Main translation function"""

    # Load English source
    with open(EN_FILE, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Create Tagalog translation (deep copy structure)
    tl_data = {
        "id": en_data["id"],
        "type": en_data["type"],
        "date": en_data["date"],
        "title": "Noong Pasimula ay ang Salita",
        "subtitle": "Nang ipahayag ni Juan na si Jesus ay ang walang hanggang Logos na lumikha ng lahat ng mga bagay",
        "language": "tl",
        "version": "Ang Dating Biblia",
        "estimated_reading_minutes": 5,
        "key_verse": {},
        "cards": [],
        "tags": [],
        "metadata": {}
    }

    # Initialize VerseResolver for Tagalog lookups
    with VerseResolver(DB_PATH) as resolver:

        # Translate key verse
        print("Translating key verse...")
        cita, texto, error = resolver.resolve("John 1:1")
        if error:
            print(f"ERROR resolving John 1:1: {error}")
            sys.exit(1)
        tl_data["key_verse"] = {
            "reference": cita,
            "text": texto
        }
        print(f"✓ Key verse: {cita}")

        # Translate Card 1: Greek Exegesis - Logos
        print("\nTranslating Card 1...")
        tl_data["cards"].append({
            "order": 1,
            "type": "greek_exegesis",
            "icon": "📖",
            "title": "Logos: Ang Salitang Kilala ng mga Pilosopo",
            "subtitle": "Bakit pinili ni Juan ang partikular na salitang ito",
            "content": "Nang isulat ni Juan ang 'Noong pasimula ay ang LOGOS', ginagamit niya ang isang salitang puno ng kahulugan para sa mga Judio at mga Griego.\n\n🏛️ PARA SA MGA PILOSOPONG GRIEGO:\n\n• Ginamit ng mga Estoiko ang 'Logos' upang ilarawan ang prinsipyo ng katwiran na namamahala sa sansinukob\n• Itinuro ni Heraclitus (~500 BC) na ang Logos ay ang puwersa ng pagkakaayos ng kosmos\n• Nakita ito ni Plato bilang tulay sa pagitan ng perpektong mundo at materyal na mundo\n• Para sa kanila, ang Logos ay isang IDEYA, isang KONSEPTO, isang HINDI-PERSONAL NA PWERSA\n\n📜 PARA SA MGA JUDIO:\n\n• Ang 'Logos' ay nagsasalin ng Hebreong 'Dabar' - ang Salita ng Diyos na lumilikha\n• Sa Genesis 1, ang Diyos ay NAGSASALITA at sumusunod ang paglikha: 'At sinabi ng Dios, Magkaroon ng liwanag: at nagkaroon ng liwanag'\n• Ipinahahayag ng Awit 33:6: 'Sa pamamagitan ng salita ng Panginoon ay nayari ang mga langit'\n• Ang Salita ng Diyos ay HINDI umuuwi nang walang kabuluhan (Isaias 55:11)\n\n💥 ANG GINAWA NI JUAN:\n\nKinuha ni Juan ang pamilyar na salitang ito at IPINAGKATAWANG-TAO ito. Ipinahahayag niya ang isang bagay na nakakagambala: 'Ang Logos na inyong pinagdedebatehan sa pilosopiya, ang Dabar na lumikha ng sansinukob - SIYA AY NAGKATAWANG-TAO! May pangalan Siya! Siya ay si Jesus ng Nazaret!'",
            "greek_words": [{
                "word": "Logos",
                "transliteration": "Λόγος",
                "meaning": "Salita, katwiran, diskurso, pagpapahayag ng kaisipan",
                "revelation": "Hindi lamang ito 'salitang binibigkas' (rhema). Ito ang kumpletong pagpapahayag ng kaisipan, katangian at kalooban ng Diyos. Si Jesus AY ang kaisipan ng Diyos na ipinahayag sa anyong tao."
            }],
            "revelation_key": "Ang Logos ay hindi pilosopiya. Ito ay isang Persona. Hindi konsepto na pinag-aaralan mo; ito ay Isang kilala mo."
        })
        print("✓ Card 1 complete")

        # Translate Card 2: Structural Analysis
        print("\nTranslating Card 2...")
        tl_data["cards"].append({
            "order": 2,
            "type": "structural_analysis",
            "icon": "🔍",
            "title": "Ang Tatlong Hampas ng Martilyo ng Juan 1:1",
            "subtitle": "Bawat pahayag ay sumasalungat sa ibang kaherehiya",
            "content": "Ang Juan 1:1 ay naglalaman ng TATLONG pahayag na sama-sama ay bumubuo ng kumpletong depensa ng pagka-Diyos ni Cristo:\n\n1️⃣ 'NOONG PASIMULA AY ANG SALITA' (Ēn archē ēn ho Logos)\n\n• Ang 'ay' (ēn) = imperfect tense sa Griego = patuloy na pag-iral na walang simula\n• HINDI nagsasabi ng 'dumating' o 'nilikha'\n• Sinasampal ang kaherehiya: 'Si Cristo ay ang unang nilalang'\n• KATOTOHANAN: Umiiral si Cristo BAGO ang pasimula. Siya ay walang hanggan.\n\n2️⃣ 'AT ANG SALITA AY SUMASA DIOS' (kai ho Logos ēn pros ton Theon)\n\n• Ang 'pros' = harapan sa harapan, sa patuloy na matalik na relasyon\n• Hindi lamang 'katabi' - ito ay aktibong pakikipag-ugnayan\n• Sinasampal ang kaherehiya: 'Si Jesus ay isa lamang ibang pangalan para sa Diyos Ama (modalismo)'\n• KATOTOHANAN: Ang Logos ay NATATANGING Persona sa relasyon sa Ama.\n\n3️⃣ 'AT ANG SALITA AY DIOS' (kai Theos ēn ho Logos)\n\n• HINDI nagsasabi ng 'isang dios' (Arianong kaherehiya)\n• Ang Theos na walang artikulo ay binibigyang-diin ang banal na KALIKASAN\n• Sinasampal ang kaherehiya: 'Si Jesus ay propeta o anghel lamang'\n• KATOTOHANAN: Ang Logos ay may PAREHONG banal na kalikasan gaya ng Ama.\n\n✨ BUOD:\nSi Jesus ay walang hanggang Diyos (talata 1a), natatangi bilang persona mula sa Ama (talata 1b), ngunit magkapareho sa banal na kalikasan (talata 1c).",
            "revelation_key": "Hindi nagsusulat ng tula si Juan. Siya ay bumubuo ng teolohikong kuta na tumagal sa 2,000 taon ng mga pag-atake."
        })
        print("✓ Card 2 complete")

        # Translate Card 3: Creation Connection
        print("\nTranslating Card 3...")

        # Resolve scripture connections
        col_cita, col_texto, col_error = resolver.resolve("Colossians 1:16")
        heb_cita, heb_texto, heb_error = resolver.resolve("Hebrews 1:2")

        if col_error or heb_error:
            print(f"ERROR: Colossians 1:16: {col_error}, Hebrews 1:2: {heb_error}")
            sys.exit(1)

        tl_data["cards"].append({
            "order": 3,
            "type": "creation_connection",
            "icon": "🌌",
            "title": "Ang Tunog ng Genesis: Lahat ng mga Bagay ay Ginawa sa Pamamagitan Niya",
            "subtitle": "Juan 1:3 - Ang banal na pagiging may-akda ni Cristo",
            "content": "Ipinahahayag ng Juan 1:3: 'Ang lahat ng mga bagay ay ginawa sa pamamagitan niya; at kung wala siya ay walang anomang bagay na ginawa, na ginawa.'\n\n🔗 ANG KONEKSYON SA GENESIS:\n\nBinuksan ni Juan ang kanyang ebanghelyo gamit ang PAREHONG mga salitang ginamit ni Moises upang buksan ang Bibliya: 'Noong pasimula'. Hindi ito pagkakataon. Sinasabi ni Juan: 'Ang nagsalita sa Genesis 1 at lumikha ng sansinukob ay siya ring lumalakad ngayon sa Galilea'.\n\nGenesis 1:\n• 'At sinabi ng Dios, Magkaroon ng liwanag' → Ang Salita (Logos) ay NAGSASALITA\n• 'At nagkaroon ng liwanag' → Ang paglikha ay SUMUSUNOD\n• 10 beses na sinasabi 'At sinabi ng Dios' → 10 kilos ng paglikha ng Salita\n\nJuan 1:\n• 'Ang lahat ng mga bagay ay ginawa sa pamamagitan niya' → Si Jesus ang Ahente ng Paglikha\n• 'Kung wala siya ay walang ANUMANG bagay na ginawa' → Ganap na diin\n\n📊 ANG TATLONG ISTRUKTURA:\n\nGumamit si Juan ng tatlong parirala upang alisin ang lahat ng pagdududa:\n1. 'Lahat ng mga bagay' (panta) = LAHAT nang walang pagbubukod\n2. 'Ginawa sa pamamagitan niya' (di autou egeneto) = Siya ang Ahente\n3. 'Kung wala siya ay WALA... ang ginawa' = Negatibong pahayag para sa pagpapalakas\n\n💡 NAKAKASIRA NA IMPLIKASYON:\n\nKung nilikha ni Cristo ang LAHAT ng mga bagay, kung gayon:\n• Nilikha Niya ang mga anghel (kasama si Satanas)\n• Nilikha Niya ang panahon (Siya ay lumalampas sa panahon)\n• Nilikha Niya ang materya (Hindi Siya nililimitahan ng pisikal na mga batas)\n• Nilikha ka NIYA (Nilikha ka Niya na may layunin)",
            "scripture_connections": [
                {
                    "reference": col_cita,
                    "text": col_texto
                },
                {
                    "reference": heb_cita,
                    "text": heb_texto
                }
            ],
            "revelation_key": "Ang karpintero mula sa Nazaret na lumalakad sa madungis na Galilea ay siya ring nag-ibitin ng mga galaksiya sa kalawakan. Nilikha ka Niya, at tanging Siya lamang ang makakapaglikha muli sa iyo."
        })
        print(f"✓ Card 3 complete ({col_cita}, {heb_cita})")

        # Translate Card 4: Light and Darkness
        print("\nTranslating Card 4...")
        tl_data["cards"].append({
            "order": 4,
            "type": "light_darkness",
            "icon": "💡",
            "title": "Ang Buhay ay ang Liwanag ng mga Tao",
            "subtitle": "Juan 1:4-5 - Ang walang hanggang tunggalian",
            "content": "Ipinagpapatuloy ni Juan: 'Sa kaniya'y may buhay; at ang buhay ay siyang ilaw ng mga tao. At ang ilaw ay lumiliwanag sa kadiliman; at hindi tinangkilik ng kadiliman.'\n\n🔦 BUHAY = LIWANAG:\n\nIkinonekta ni Juan ang dalawang konsepto:\n• Buhay (zoē) = hindi biyolohikal na buhay (bios), kundi WALANG HANGGANG buhay, buhay ng Diyos\n• Liwanag (phōs) = kapahayagan, katotohanan, presensya ng Diyos\n\nKung nasaan si Cristo, may BUHAY. At kung saan may buhay, may LIWANAG na naglalantad ng kadiliman.\n\n⚔️ ANG TUNGGALIAN:\n\nAng 'hindi tinangkilik ng kadiliman' - ang pandiwang Griego (katelaben) ay may dobleng kahulugan:\n1. 'Unawain' - ang kadiliman ay HINDI UMUNAWA sa liwanag\n2. 'Malupig' - ang kadiliman ay HINDI MAKAPAPATAY sa liwanag\n\nParehong kahulugan ay sinadya. Ang kadiliman:\n• Hindi makakaunawa sa liwanag (hindi sila maaring magsama)\n• Hindi makakapatay sa liwanag (walang kapangyarihan ito)\n\n🌍 HISTORIKAL NA APLIKASYON:\n\n• Sinubukan ni Herodes na patayin si Jesus na sanggol → NABIGO\n• Sinubukan ng mga Fariseo na bitag Siya sa Kanyang mga salita → NABIGO\n• Sinubukan ng mga Romano na patayin Siya → Bumangon Siya sa ikatlong araw\n• Sinubukan ni Satanas na sirain ang iglesya sa loob ng 2,000 taon → NANDITO PA RIN\n\nAng liwanag ay LAGING nananaig sa kadiliman. Walang tunay na labanan; tanging paglalantad lamang.",
            "identity_statement": "Ikaw ay tagadala ng Liwanag na hindi maunawaan o malupigan ng kadiliman. Sa iyong pinakamadilim na mga sandali, ang Liwanag sa iyo ay mas malakas kaysa kadiliman sa paligid mo.",
            "revelation_key": "Ang kadiliman ay hindi kapantay na kabaligtaran ng liwanag. Ito ay simpleng KAKULANGAN ng liwanag. Kapag pumasok si Cristo, kusang tumakas ang kadiliman."
        })
        print("✓ Card 4 complete")

        # Translate Card 5: Discovery Activation
        print("\nTranslating Card 5...")
        tl_data["cards"].append({
            "order": 5,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Pansariling Pagtuklas",
            "discovery_questions": [
                {
                    "category": "Paglikha",
                    "question": "Ang Logos na lumikha ng mga galaksiya ay personal na dinisenyo ka. Anong bahagi ng iyong buhay ang nangangailangan na LIKHAIN MULI ng Lumikha mula sa wala (ex nihilo)?"
                },
                {
                    "category": "Pagkakakilanlan",
                    "question": "Kung si Cristo ay ang Logos - ang kumpletong pagpapahayag ng kaisipan ng Diyos - ano ang sinasabi nito tungkol sa puso ng Ama sa iyo na si Jesus ay dumating bilang sanggol na mahina?"
                },
                {
                    "category": "Liwanag laban sa Kadiliman",
                    "question": "Sa aling bahagi ng iyong buhay mo nararamdaman na ang 'kadiliman' ay nananalo? Paano nababago ang iyong pananaw na malaman na ang liwanag ay LAGING nananaig, hindi sa pamamagitan ng pakikipaglaban, kundi sa pamamagitan lamang ng pag-iral?"
                }
            ],
            "prayer": {
                "title": "Panalangin ng Logos",
                "content": "Jesus, aking walang hanggang Logos. Ikaw ay umiiral bago ang 'pasimula', lumikha ng lahat ng mga bagay, at ngayon ay nabubuhay sa akin. Salamat na hindi Ka pilosopiya na dapat kong unawain, kundi Persona na makikilala ko. Ngayong araw ay hinihiling ko sa Iyo na magsalita ng kaayusan sa kaguluhan ng aking buhay, gaya ng ginawa Mo sa Genesis 1. Nawa ang Iyong liwanag sa akin ay maglantad at malupig ang bawat kadiliman. Ipaalala sa akin na ang parehong kapangyarihang nag-ibitin ng mga bituin ay nabubuhay sa loob ko, at walang kadiliman ang makapananaig laban sa Iyong liwanag. Sa pangalan ni Jesus, Amen."
            }
        })
        print("✓ Card 5 complete")

        # Translate tags
        tl_data["tags"] = [
            "logos",
            "paglikha",
            "walang_hanggan",
            "liwanag",
            "pagka_diyos_ni_cristo",
            "genesis"
        ]

        # Translate metadata
        tl_data["metadata"] = {
            "total_word_count": en_data["metadata"]["total_word_count"],
            "greek_words_count": 1,
            "scripture_references_count": 9,
            "difficulty_level": "intermediate-advanced",
            "themes": [
                "Pagka-Diyos ni Cristo",
                "Si Cristo bilang Lumikha",
                "Nagkatawang-taong Logos",
                "Liwanag laban sa kadiliman"
            ]
        }

    # Write translated file
    with open(TL_FILE, 'w', encoding='utf-8') as f:
        json.dump(tl_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Translation complete: {TL_FILE}")
    return TL_FILE

if __name__ == '__main__':
    translate_to_tagalog()
