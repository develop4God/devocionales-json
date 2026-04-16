#!/usr/bin/env python3
"""
Translate woman_at_well Bible study from English to Tagalog
Uses ADB (Ang Dating Biblia) for all scripture lookups
"""

import json
import sys
import os

# Add parent directory to path for verse_resolver
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

# Paths
ADB_DB = '/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3'
EN_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/en/woman_at_well_en_001.json'
TL_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/tl/woman_at_well_tl_001.json'

def main():
    # Load English source
    with open(EN_FILE, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Initialize VerseResolver
    with VerseResolver(ADB_DB) as resolver:
        # Test connection
        print(f"Database has {resolver.verse_count()} verses")

        # Resolve key_verse
        print("\n=== Resolving Key Verse ===")
        key_ref = en_data["key_verse"]["reference"]
        cita, texto, error = resolver.resolve(key_ref)
        if error:
            print(f"ERROR: {error}")
            return 1
        print(f"EN: {key_ref}")
        print(f"TL: {cita}")
        print(f"Text: {texto[:100]}...")

        # Resolve scripture_connections
        print("\n=== Resolving Scripture Connections ===")
        card_3 = en_data["cards"][2]  # creation_connection card
        for sc in card_3.get("scripture_connections", []):
            ref = sc["reference"]
            cita, texto, error = resolver.resolve(ref)
            if error:
                print(f"ERROR in {ref}: {error}")
            else:
                print(f"EN: {ref} -> TL: {cita}")
                print(f"Text: {texto[:80]}...")

        # Now create the translation
        print("\n=== Creating Translation ===")

        tl_data = {
            "id": en_data["id"],
            "type": en_data["type"],
            "date": en_data["date"],
            "title": "Ang Babae sa Balon",
            "subtitle": "Nang wasakin ni Jesus ang lahat ng hadlang para sa isang pag-uusap na magbabago sa isang lungsod",
            "language": "tl",
            "version": "Ang Dating Biblia",
            "estimated_reading_minutes": 6,  # EN baseline is 5, add 1 min for Tagalog
            "key_verse": {
                "reference": "",
                "text": ""
            },
            "cards": [],
            "tags": [
                "buhay_na_tubig",
                "pagsamba",
                "ebanhelismo",
                "biyaya",
                "mga_samaritano",
                "babae_sa_balon"
            ],
            "metadata": {
                "total_word_count": en_data["metadata"]["total_word_count"],
                "greek_words_count": en_data["metadata"]["greek_words_count"],
                "scripture_references_count": en_data["metadata"]["scripture_references_count"],
                "difficulty_level": en_data["metadata"]["difficulty_level"],
                "themes": [
                    "Biyaya nang walang hadlang",
                    "Tunay na pagsamba",
                    "Pansariling ebanhelismo",
                    "Espirituwal na uhaw"
                ]
            }
        }

        # Resolve and set key verse
        cita, texto, error = resolver.resolve(en_data["key_verse"]["reference"])
        if not error:
            tl_data["key_verse"]["reference"] = cita
            tl_data["key_verse"]["text"] = texto

        # Card 1: Greek Exegesis - Living Water
        tl_data["cards"].append({
            "order": 1,
            "type": "greek_exegesis",
            "icon": "💧",
            "title": "Buhay na Tubig: Ang Kaloob na Nagbibigay-Kasiyahan sa Walang Hanggan",
            "subtitle": "Bakit ginagamit ni Jesus ang metapora ng tubig",
            "content": """Si Jesus ay nasa balon ni Jacob nang tanghali - ang pinakamainit na oras, kung kailan walang umiigib ng tubig. Isang babaeng Samaritana ang dumating na nag-iisa, umiiwas sa karamihan. At winasak ni Jesus ang TATLONG kultura ng hadlang:

🚫 MGA HADLANG NA WINASAK NI JESUS:

• Hadlang ng KASARIAN: Ang mga rabi ay hindi nakikipag-usap sa mga babae sa publiko
• Hadlang ng LAHI: Ang mga Judio ay walang pakikitungo sa mga Samaritano (Juan 4:9)
• Hadlang ng MORALIDAD: Mayroon siyang nakaraan ng limang asawa

Ngunit si Jesus ang nagsimula ng pag-uusap: 'Bigyan mo ako ng maiinom' (Juan 4:7).

💦 ANG METAPORA NG TUBIG:

Kinuha ni Jesus ang isang karaniwang bagay - tubig sa balon - at ginawa itong walang hanggang aral:

• Tubig sa balon = pansamantalang kasiyahan (v.13: 'mauuhaw muli')
• Buhay na tubig = walang hanggang kasiyahan (v.14: 'hindi na mauuhaw kailanman')

Ang buhay na tubig ay hindi isang bagay na TUMATANGGAP ka minsan. Nagiging 'balon ng tubig na bumubukal tungo sa buhay na walang hanggan' - isang bagay na panloob, permanente, umaapaw.

🔥 ANG TUNAY NA PANGANGAILANGAN:

Ang babae ay dumating na naghahanap ng pisikal na tubig, ngunit nakita ni Jesus ang kanyang espirituwal na uhaw. Naghanap siya ng kasiyahan sa limang pag-aasawa at ngayon ay namumuhay kasama ang isang tao na hindi niya asawa (v.18). Walang relasyon sa tao ang makapupuno ng kawalang-laman.

Inaalok ni Jesus ang tunay niyang kailangan: isang relasyon sa Kanya na nagbibigay-kasiyahan sa walang hanggan.""",
            "greek_words": [
                {
                    "word": "Hydōr Zōn",
                    "transliteration": "ὕδωρ ζῶν",
                    "meaning": "Buhay na tubig, dumadaloy na tubig, bukal ng tubig",
                    "revelation": "Sa Griyego, ang 'buhay na tubig' ay tumutukoy sa umaagos na tubig mula sa bukal, kaiba sa nakatigil na tubig sa aljibe. Nangako si Jesus ng isang bagay na dinamiko, sariwa, patuloy na dumadaloy - ang Banal na Espiritu."
                }
            ],
            "revelation_key": "Ang bawat pagsisikap ng tao na makamtan ang kasiyahan ay parang pag-inom ng tubig sa aljibe - nauubos ito. Si Jesus lamang ang nag-aalok ng isang panloob na bukal na hindi kailanman natutuyo."
        })

        # Card 2: Structural Analysis - Progression
        tl_data["cards"].append({
            "order": 2,
            "type": "structural_analysis",
            "icon": "🔍",
            "title": "Ang Pagsulong ng Pahayag",
            "subtitle": "Paano unti-unting ipinahayag ni Jesus ang Kanyang sarili sa kanya",
            "content": """Ang Juan 4 ay nagpapakita ng kahusayang PAGSULONG sa kung paano nakikita ng babae si Jesus:

1️⃣ TALATA 9: 'ISANG JUDIO'

• Nakikita niya lamang Siya sa pamamagitan ng Kanyang lahi
• Nagulat siya na nakikipag-usap Siya sa kanya
• Ang kanyang pananaw: 'Paanong ikaw, na isang Judio...'

2️⃣ TALATA 11: 'GINOO' (Kyrios)

• Isang pangunahing pamagat ng paggalang
• Hindi pa rin naiintindihan kung sino Siya
• Ang kanyang tanong: 'Ginoo, wala kang igib...'

3️⃣ TALATA 19: 'ISANG PROPETA'

• Nang ihayag ni Jesus ang kanyang nakaraan (limang asawa)
• Nakikilala niya ang supernatural na kapangyarihan
• 'Ginoo, nakikita ko na ikaw ay propeta'

4️⃣ TALATA 25-26: 'ANG MESIAS (ANG CRISTO)'

• Sinabi niya: 'Alam kong darating ang Mesias...'
• Direktang ipinahayag ni Jesus: 'Ako nga, na nakikipag-usap sa iyo'
• Isa sa pinaka-malinaw na pahayag ng Kanyang pagkakakilanlan sa mga ebanghelyo!

5️⃣ TALATA 29: 'ANG CRISTO' (patotoo sa lungsod)

• Tumakbo siya sa lungsod
• Sinabi sa kanila: 'Hindi baga ito ang Cristo?'
• Ang kanyang patotoo: 'Sinabi niya sa akin ang lahat ng aking ginawa'

✨ ANG PARAAN NI JESUS:

Hindi nililito ni Jesus ng pahayag. Unti-unti, sa pamamagitan ng pag-uusap, inilalakad niya ang babae mula sa pagkakita sa isang kakaibang Judio tungo sa pagkilala sa ipinangakong Mesias.""",
            "revelation_key": "Unti-unting inihahayag ni Jesus ang Kanyang sarili sa mga nagsisikap. Ang pahayag ay hindi dumating nang sabay-sabay, kundi sa pagsulong habang lumalaki ang ating pananampalataya."
        })

        # Card 3: Creation Connection - Worship
        # Resolve scripture connections
        sc_list = []
        for sc in en_data["cards"][2].get("scripture_connections", []):
            cita, texto, error = resolver.resolve(sc["reference"])
            if not error:
                sc_list.append({"reference": cita, "text": texto})

        tl_data["cards"].append({
            "order": 3,
            "type": "creation_connection",
            "icon": "⛰️",
            "title": "Pagsamba sa Espiritu at sa Katotohanan",
            "subtitle": "Juan 4:19-24 - Ang kasaysayan ng debate at ang rebolusyon ni Jesus",
            "content": """Tinanong ng babaeng Samaritana si Jesus ng isang tanong na naghiwalay sa mga Judio at mga Samaritano sa loob ng maraming siglo: 'Saan natin dapat sambahin ang Diyos? Sa bundok na ito (Gerizim) o sa Jerusalem?' (Juan 4:20).

🔎 BAKIT ANG DEBATE NA ITO?

• Ang mga Samaritano ay sumasamba sa Bundok Gerizim, dahil doon binago ni Josue ang tipan (Deuteronomio 11:29; Josue 8:33).
• Ang mga Judio ay nag-aangkin na ang Jerusalem lamang ang lehitimong lugar, dahil doon itinayo ni Solomon ang templo (2 Cronica 6:6; Salmo 122:1).

Ito ay humantong sa mga siglo ng tunggalian at paghihiwalay (tingnan ang Ezra 4:1-3).

📖 MGA BIBLIKAL NA SANGGUNIAN (ADB):

• Deuteronomio 11:29: 'At mangyayari, pagka dinala ka ng Panginoon mong Dios sa lupain... ay ilalagay mo ang pagpapala sa bundok ng Gerizim.'
• 2 Cronica 6:6: 'Nguni't aking pinili ang Jerusalem, upang naroroon ang aking pangalan.'
• Salmo 122:1: 'Ako'y nagalak nang kanilang sabihin sa akin, Tayo'y magsiparoon sa bahay ng Panginoon.'

⚡ ANG REBOLUSYONARYONG SAGOT NI JESUS:

Hindi kumakampi si Jesus sa alinmang pisikal na lugar. Ipinahayag niya: 'Ang oras ay dumarating, at ngayon nga, kung saan ang mga tunay na mananamba ay magsisisamba sa Ama sa espiritu at sa katotohanan' (Juan 4:23).

• Ang bundok o ang templo ay hindi na mahalaga
• Ang Diyos ay humahanap ng mga taos-pusong mananamba, na ginagabayan ng Espiritu at ng katotohanan ng Kanyang Salita
• Ang pagsamba ay isang buhay na relasyon, hindi isang heograpikal na ritwal

🙌 ANO ANG IBIG SABIHIN NG SUMAMBA SA ESPIRITU AT SA KATOTOHANAN?

• Espiritu: Pagsamba mula sa pinakamalalim na bahagi, na ginagabayan ng Banal na Espiritu (Filipos 3:3)
• Katotohanan: Pagsamba batay sa biblikal na pahayag ng kung sino ang Diyos (Juan 17:17)

⚡ ANG KATANGIAN NG DIYOS:

'Ang Diyos ay Espiritu' (Juan 4:24). Hindi Siya limitado ng mga lugar o mga gusali. Maaari Siyang sambahin kahit saan ng mga dumarating na may taos-pusong puso.

Kaya, winasak ni Jesus ang hadlang ng relihiyon at binuksan ang access sa lahat ng mga tao, kahit saan.""",
            "scripture_connections": sc_list,
            "revelation_key": "Ang pagsamba ay hindi na umaasa sa isang heograpikal na lokasyon. Nasaan ka man, maaaring naroon ang presensya ng Diyos kung darating ka sa espiritu at katotohanan."
        })

        # Card 4: Light and Darkness - Harvest
        tl_data["cards"].append({
            "order": 4,
            "type": "light_darkness",
            "icon": "🌾",
            "title": "Ang mga Bukiring Puti Para sa Pag-aani",
            "subtitle": "Juan 4:35-38 - Ang hindi inaasahang ebanhelismo",
            "content": """Habang nakikipag-usap si Jesus sa babae, ang mga alagad ay nasa lungsod na bumibili ng pagkain. Nang bumalik sila, NAGULAT sila na makita Siyang nakikipag-usap sa isang babae (v.27).

Ngunit may nangyaring pambihira:

👥 ANG HINDI INAASAHANG PAG-AANI:

Iniwan ng babae ang kanyang banga - simbolo ng kanyang dating buhay - at tumakbo sa lungsod. Ang kanyang patotoo ay simple ngunit makapangyarihan: 'Halikayo, tingnan ninyo ang isang lalaking nagsabi sa akin ng lahat ng mga bagay na aking ginawa: hindi baga ito ang Cristo?' (v.29).

Resulta: 'Nang magkagayo'y nagsilabas sila sa bayan, at nagsiparoon sa kaniya' (v.30).

🌾 ANG MGA PUTING BUKID:

Sinabi ni Jesus sa mga alagad: 'Itingin ninyo ang inyong mga mata, at masdan ninyo ang mga bukid, na mga puti na sa pag-aani' (v.35).

Ang larawang ito ay may visual at kultural na kasaysayan: maraming mga Samaritano ang nagsusuot ng puting damit upang protektahan ang kanilang sarili mula sa araw. Kaya, habang papalapit ang karamihan kay Jesus, ang kanilang puting kasuutan ay nagbigay ng impresyon ng isang bukid na handa na sa pag-aani.

Kaya, ang metapora ng 'puting bukid' ay hindi lamang nagsasalita ng espirituwal na pagkakataon, kundi inilalarawan din ang tunay na eksena na nakita ng mga alagad: isang karamihan na nakasuot ng puti, handa nang tanggapin ang mensahe.

• Iniisip ng mga alagad: 'Apat na buwan hanggang sa pag-aani'
• Ipinakita sa kanila ni Jesus: 'Ang pag-aani ay NGAYON, sa harap ninyo!'

💡 ANG PARAAN NG MISYON:

• Pumili si Jesus ng PINAKA-hindi malamang na tao (babae, Samaritana, imoral na nakaraan)
• Naging ebanghelista siya para sa buong lungsod
• Talata 39: 'Marami sa mga Samaritano... ay nangagsisampalataya sa kaniya dahil sa salita ng babae'
• Talata 41: 'Marami pang higit ang nangagsisampalataya dahil sa kaniyang sariling salita'

📊 ANG RESULTA:

Ang nagsimula sa isang pag-uusap sa balon ay nagtapos sa:
• Isang binagong lungsod
• Dalawang araw ng pagtuturo (v.40)
• Deklarasyon: 'Ito nga ang Cristo, ang Tagapagligtas ng sanglibutan' (v.42)""",
            "identity_statement": "Ikaw ay isang puting bukid para sa pag-aani. Ang iyong nakaraan ay hindi mahalaga; magagamit ni Jesus ang iyong patotoo upang maabot ang mga kilala mo.",
            "revelation_key": "Ang mga taong tinatanggihan ng relihiyon ay ang mga pinipili mismo ni Jesus upang magdala ng pagbabagong-buhay. Ang tunay na patotoo ay mas mahalaga kaysa sa isang libong sermon."
        })

        # Card 5: Discovery Activation
        tl_data["cards"].append({
            "order": 5,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Pansariling Pagtuklas",
            "discovery_questions": [
                {
                    "category": "Espirituwal na Uhaw",
                    "question": "Sa aling mga 'sirang aljibe' ka naghahanap ng kasiyahan na si Cristo lamang ang makapagbibigay? (mga relasyon, tagumpay, pagsang-ayon, atbp.)"
                },
                {
                    "category": "Mga Hadlang",
                    "question": "Winasak ni Jesus ang mga hadlang ng kultura upang maabot ang babaeng Samaritana. Anong mga hadlang (panlipunan, lahi, relihiyon) ang pumipigil sa iyo na ibahagi ang ebanghelyo sa iba?"
                },
                {
                    "category": "Ebanhelismo",
                    "question": "Iniwan ng babae ang kanyang banga at tumakbo upang ibahagi ang ginawa ni Jesus para sa kanya. Anong mga 'banga' (mga pasanin, mga kahihiyan sa nakaraan) ang kailangan mong iwan upang maging malaya sa pagpatotoo?"
                }
            ],
            "prayer": {
                "title": "Panalangin ng Buhay na Tubig",
                "content": "Jesus, salamat sa iyo sa pagwasak ng bawat hadlang upang maabot ako. Kinikilala ko na naghanap ako ng kasiyahan sa mga sirang aljibe na hindi kailanman makapupuno ng kawalang-laman sa aking kaluluwa. Ngayong araw ay umiinom ako ng buhay na tubig na iyong inaalok - isang panloob na bukal na hindi kailanman natutuyo. Tulungan mo akong sumamba sa iyo sa espiritu at sa katotohanan, hindi lamang sa mga lugar o mga ritwal, kundi sa tunay na relasyon sa iyo. Nawa'y ang aking patotoo, tulad ng babaeng Samaritana, ay maging daan upang ang iba ay matuklasan na ikaw ay tunay na Tagapagligtas ng sanglibutan. Sa pangalan ni Jesus, Amen."
            }
        })

        # Write the output file
        with open(TL_FILE, 'w', encoding='utf-8') as f:
            json.dump(tl_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Translation written to: {TL_FILE}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
