#!/usr/bin/env python3
"""
Translate i_am_before_abraham from English to Tagalog
Uses VerseResolver for all scripture lookups
"""

import json
import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'devocionales_scripts'))
from verse_resolver import VerseResolver

def translate_i_am_before_abraham():
    # Load English source
    with open('discovery/en/i_am_before_abraham_en_001.json', 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Create Tagalog version
    tl_data = {
        "id": en_data["id"],
        "type": en_data["type"],
        "date": en_data["date"],
        "title": "AKO AY: Bago si Abraham",
        "subtitle": "Nang iangkin ni Jesus ang walang-hanggan at kinuha ng mga tao ang mga bato",
        "language": "tl",
        "version": "Ang Dating Biblia",
        "estimated_reading_minutes": 7,
        "key_verse": {},
        "cards": [],
        "tags": [
            "pagka_diyos_ni_cristo",
            "mga_pahayag_na_ako_ay",
            "juan_8",
            "walang_hanggan",
            "pagsusuri_ng_griego",
            "pamumusong",
            "soberanya"
        ],
        "metadata": {
            "total_word_count": en_data["metadata"]["total_word_count"],
            "greek_words_count": en_data["metadata"]["greek_words_count"],
            "scripture_references_count": en_data["metadata"]["scripture_references_count"],
            "difficulty_level": en_data["metadata"]["difficulty_level"],
            "themes": [
                "Walang-hanggang pag-iral ni Cristo",
                "Ang banal na Pangalan",
                "Pag-unawa ng mga Hudyo sa pamumusong",
                "Supernatural na soberanya"
            ]
        }
    }

    # Initialize verse resolver
    db_path = 'bible_database/ADB_tl.SQLite3'

    with VerseResolver(db_path) as resolver:
        # Translate key verse
        key_ref = en_data['key_verse']['reference']
        cita, texto, error = resolver.resolve(key_ref)
        if error:
            print(f"Error resolving {key_ref}: {error}")
            sys.exit(1)

        tl_data['key_verse'] = {
            'reference': cita,
            'text': texto
        }

        # Card 1: Character Context
        card1 = {
            "order": 1,
            "type": "character_context",
            "icon": "🕎",
            "title": "Ang Pista ng mga Tabernakulo: Ang Pagtatakda ng Entablado",
            "subtitle": "Bakit nangyayari ang pag-uusap na ito kung saan at kailan ito nangyayari",
            "content": """Ang paghaharap na ito ay nangyayari sa panahon ng Pista ng mga Tabernakulo (Sukkot), isa sa tatlong mandatoryong pista ng mga peregrinasyon ng Israel. Napakahalaga ng pag-unawa sa konteksto:

🏛️ ANG LOKASYON:
• Si Jesus ay nasa ingatan ng Templo (Juan 8:20)
• Dito nakatayo ang apat na higanteng candelabra
• Sa panahon ng Sukkot, ang mga menorah na ito ay sinindihan upang gunitain ang haligi ng apoy sa ilang
• Ang liwanag ay napakalakas na nag-iilaw sa buong Jerusalem

🔥 ANG SIMBOLISMO:
• Ang haligi ng apoy ay kumakatawan sa presensya ng Diyos na gumagabay sa Israel
• Ito ay isang patuloy na paalala na ang YHWH ay naninirahan kasama nila
• Ang naiilaw na Templo ay nagpapahayag: 'Nandito ang Diyos'

💡 ANG PAGHAHABOL NI JESUS (8:12):
Sa kontekstong ITO, ipinahahayag ni Jesus: 'Ako ang ilaw ng sanglibutan.'

Hindi lamang Siya gumagamit ng isang magandang metapora. Inaangkin Niya na maging ang realidad na ang mga candelabra ay sumasagisag lamang. Siya ang tunay na haligi ng apoy. Siya ang hayag na presensya ng YHWH.

⚔️ ANG TUMATAAS NA TENSYON:
Sa Juan 8:58, ang debate na ito ay tumataas na sa loob ng ilang oras. Si Jesus ay:
• Tinawag sila na mga anak ng diyablo (8:44)
• Inaangkin na kilala Niya nang personal si Abraham (8:56)
• Sinabi na si Abraham ay 'nagalak na makita ang aking araw'

Ngayon ang rurok.""",
            "revelation_key": "Hindi pumili si Jesus ng mga random na sandali upang gumawa ng radikal na mga angkin. Bawat pahayag na 'AKO AY' ay inilagay sa isang konteksto na idinisenyo upang gawing hindi mapagkakamalang Kanyang pagkakakilanlan."
        }

        tl_data['cards'].append(card1)

        # Card 2: Greek Exegesis
        card2 = {
            "order": 2,
            "type": "greek_exegesis",
            "icon": "📖",
            "title": "Genesthai laban sa Egō Eimi: Ang Gramatika ng Walang-hanggan",
            "subtitle": "Dalawang pandiwa na naghahayag ng dalawang kalikasan",
            "content": """Ang Juan 8:58 ay naglalaman ng isa sa pinakateolohikong nakakargadong mga pangungusap sa Kasulatan:

'Ἀμὴν ἀμὴν λέγω ὑμῖν, πρὶν Ἀβραὰμ γενέσθαι ἐγὼ εἰμί.'
'Amēn amēn legō hymin, prin Abraam genesthai egō eimi.'

🔍 PANDIWA NI ABRAHAM: GENESTHAI (γενέσθαι)

• Strong's G1096: γίνομαι (ginomai)
• Anyo: Aorist infinitive
• Kahulugan: 'Dumating sa pag-iral,' 'ipinanganak,' 'maging'
• Implikasyon: Si Abraham ay may simula sa panahon
• Timeline: Mga 2000 BC

📊 ANG GRAMATIKA:
Ang aorist tense ay nagtatatak ng isang tiyak na historikal na kaganapan. Si Abraham ay hindi laging umiiral - DUMATING SIYA SA PAG-IRAL sa isang partikular na sandali nang tawagin siya ng Diyos.

⚡ PANDIWA NI JESUS: EGŌ EIMI (ἐγὼ εἰμί)

• Strong's G1510 (εἰμί) + G1473 (ἐγώ)
• Anyo: Present indicative, emphatic
• Kahulugan: 'AKO AY' (patuloy, walang-hanggang kasalukuyan)
• Implikasyon: Walang simula, walang katapusan - walang-hanggang pag-iral

🔥 ANG GULAT:
Hindi nagsasabi si Jesus ng:
• 'AKO AY NOON bago si Abraham' (nakaraang panahon)
• 'Umiiral ako bago si Abraham' (binibigyang-diin ang pagkakasunud-sunod)

Sinasabi Niya: 'AKO AY' - gamit ang walang-hanggang kasalukuyang panahon na lumalampas sa panahon mismo.

🌟 ANG KONEKSYON SA EXODO 3:14:
Nang tanungin ni Moises ang pangalan ng Diyos sa umuusok na palumpong, sinabi ng Diyos:
• Hebreo: אֶהְיֶה אֲשֶׁר אֶהְיֶה (Ehyeh Asher Ehyeh)
• Griegong LXX: Ἐγώ εἰμι ὁ ὤν (Egō eimi ho ōn)
• Salin: 'AKO AY AKO AY'

Inaangkin ni Jesus ang banal na Pangalan.""",
            "greek_words": [
                {
                    "word": "Genesthai",
                    "transliteration": "γενέσθαι",
                    "meaning": "Dumating sa pag-iral, ipinanganak",
                    "revelation": "Ang pandiwang ito ay nagtatatak ng mga nilikha. Lahat ng 'dumating sa pag-iral' ay may Lumikha - kasama si Abraham."
                },
                {
                    "word": "Egō Eimi",
                    "transliteration": "ἐγὼ εἰμί",
                    "meaning": "AKO AY (walang-hanggang kasalukuyan)",
                    "revelation": "Ito ang pangalan ng Diyos. Hindi 'ako ay noon' o 'ako ay magiging' - kundi ang walang-hanggan, sariling umiiral na ISA na AY lamang."
                }
            ],
            "revelation_key": "Ang gramatika mismo ay isang teolohikong pahayag. Si Abraham ay 'naging.' Si Jesus ay 'AY.' Ang isa ay may simula. Ang Isa ay ang Simula."
        }

        tl_data['cards'].append(card2)

        # Card 3: Theological Depth - The Stones
        exo_cita, exo_texto, exo_error = resolver.resolve("Exodus 3:14")
        lev_cita, lev_texto, lev_error = resolver.resolve("Leviticus 24:16")

        if exo_error or lev_error:
            print(f"Error resolving scripture connections")
            sys.exit(1)

        card3 = {
            "order": 3,
            "type": "theological_depth",
            "icon": "⚖️",
            "title": "Ang mga Bato: Bakit Naintindihan Nila nang Perpekto",
            "subtitle": "Juan 8:59 - Patunay na nakuha nila ang mensahe",
            "content": """Agad pagkatapos sabihin ni Jesus na 'AKO AY,' inirekord ng teksto:

'Nang magkagayo'y nangagdampot sila ng mga bato upang ib uhin siya...' (Juan 8:59a)

🪨 BAKIT MGA BATO?

Hindi ito isang spontaneous na kagulo ng karamihan. Ito ay isang kinalkula na legal na pagtatangkang pagpatay batay sa Batas ni Moises:

📜 LEVITICO 24:16:
'At ang lumapastangan sa pangalan ng Panginoon, ay walang pagsalang papatayin, at lahat ng kapisanan ay walang pagsalang babatuhin siya: maging taga ibang lupa, o maging ipinanganak sa lupain, ay papatayin niya, pagka kaniyang nilalait ang pangalan ng Panginoon.'

⚡ ANG SAKDAL: PAMUMUSONG

Sa ilalim ng batas ng mga Hudyo, ang pamumusong ay hindi lamang 'pagsasabi ng masasamang bagay tungkol sa Diyos.' Mayroon itong napaka-tiyak na kahulugan:
• Pagbigkas ng sagradong Pangalan (YHWH) upang iangkin ang pagka-diyos sa sarili
• Kinukuha ang eksklusibong pagkakakilanlan ng Diyos at inaangkin ito bilang sarili mo

Ito EKSAKTO ang ginawa ni Jesus. Sa pamamagitan ng pagsasabi ng 'Egō Eimi' sa kontekstong ito, inaangkin Niya ang:
1️⃣ Pag-iral bago lahat ng nilikha
2️⃣ Ang banal na Pangalan na inihayag sa umuusok na palumpong
3️⃣ Pagkakapantay sa Ama

❌ KUNG SI JESUS AY GURO LAMANG:

Itatapon lamang sana Siya ng mga Hudyo bilang:
• Isang baliw (delusyonal)
• Isang erehe (nalito sa teolohiya)
• Isang taong inaalihan ng demonyo (8:48 - iminungkahi na nila ito)

Ngunit hindi nila Siya itinakwil. Sinubukan nilang PATAYIN Siya.

✅ BAKIT? DAHIL NAINTINDIHAN NILA:

Walang Hudyong ika-1 siglo ang hindi makakaintindi ng 'Egō Eimi' sa kontekstong ito. Alam nila:
• Ang Shema: 'Pakinggan mo, Israel: Ang Panginoon nating Dios ay isang Panginoon' (Deut 6:4)
• Ang sagradong Pangalan mula sa Exodo 3:14
• Ang parusa para sa pamumusong

Ang kanilang karahasan ay ang kanilang eksamen sa teolohiya. Nakakuha sila ng A+ sa pag-unawa - at F sa pananampalataya.""",
            "scripture_connections": [
                {
                    "reference": exo_cita,
                    "text": exo_texto
                },
                {
                    "reference": lev_cita,
                    "text": lev_texto
                }
            ],
            "revelation_key": "Ang mga bato ay nagpapatunay ng angkin. Kung sinabi lamang ni Jesus na Siya ay umiiral bago si Abraham, maaaring makipagtalo sila sa teolohiya. Ngunit ang pag-angkin ng 'AKO AY' ay nangangahulugang pag-angkin na maging Diyos - at iyon ay nangangailangan ng pagsamba o pagbitay."
        }

        tl_data['cards'].append(card3)

        # Card 4: Theological Depth - Supernatural Exit
        card4 = {
            "order": 4,
            "type": "theological_depth",
            "icon": "✨",
            "title": "Ang Supernatural na Paglabas: Ekrybē",
            "subtitle": "Nang nagtago ang Liwanag mula sa mga pumili ng kadiliman",
            "content": """Pagkatapos nilang kunin ang mga bato, may kahanga-hangang bagay na nangyayari:

'...datapuwa't si Jesus ay nagkubli (ἐκρύβη), at lumabas sa templo, na nagdaan sa gitna nila, at gayon ay nagdaan.' (Juan 8:59b)

🔍 ANG SALITA: EKRYBĒ (ἐκρύβη)

• Strong's G2928: κρύπτω (kryptō)
• Anyo: Aorist passive indicative
• Ugat na kahulugan: 'Magtago, ikubli, mag-encrypt'
• Inggles na mga derivatives: 'Crypt,' 'cryptic,' 'encryption'

⚡ BAKIT MAHALAGA ANG 'PASSIVE':

Ang passive voice (ekrybē) ay nangangahulugang 'Siya ay ITINAGO' - hindi 'Nagtago Siya ng Kanyang Sarili.'

Iminumungkahi nito ang banal na interbensyon:
• Itinago Siya ng Diyos Ama
• Isang supernatural na tabing ay bumagsak sa kanilang mga mata
• Ang Liwanag ay ginawa ang Kanyang Sariling hindi nakikita sa mga tumangging sa Kanya

🚶 'NAGDAAN SA GITNA NILA':

Napakahalaga ng pariralang ito. Si Jesus ay HINDI:
• Sumilip sa isang side door
• Tumakas sa takot
• Nagtago sa likod ng haligi

Siya ay lumakad SA GITNA ng isang armadong karamihan na handang ipatupad Siya.

💭 ANG TEOLOHIKONG IRONYA:

1️⃣ Inaangkin lang ni Jesus na Siya ang 'ilaw ng sanglibutan' (8:12)
2️⃣ Tinanggihan nila ang Liwanag
3️⃣ Ngayon ang Liwanag ay 'nagtago' mula sa kanila - isang anyo ng paghatol

🔦 IBANG MGA GAMIT NG KRYPTŌ (G2928):

• Mateo 11:25 - Ang Diyos ay 'nagtago' ng katotohanan mula sa mga marunong at matalino
• Lucas 19:42 - Ang kapayapaan ay 'nakatago' mula sa mga mata ng Jerusalem bilang paghatol
• Mga Taga-Colosas 3:3 - Ang ating buhay ay 'nakatago' kay Cristo sa Diyos (proteksyon)

🎯 ANG PATTERN:

Hindi ito ang unang pagkakataon na ginagawa ito ni Jesus:
• Lucas 4:30 - Sa Nazaret, sinubukan nilang itapon Siya sa bangin, ngunit 'na pagdaan niya sa gitna nila ay yumaon ng kaniyang lakad'

Sa parehong pagkakataon, ipinakita ni Jesus na:
• Walang sinoman ang makakakuha ng Kanyang buhay - kusang ibinibigay Niya ito (Juan 10:18)
• Ang Kanyang 'oras' ay hindi pa dumarating (Juan 7:30)
• Siya ay soberano kahit sa tinangkang pagpatay""",
            "greek_words": [
                {
                    "word": "Ekrybē",
                    "transliteration": "ἐκρύβη",
                    "meaning": "Itinago, ikinubli (passive voice)",
                    "revelation": "Ang passive voice ay tumutukoy sa banal na passive - itinago Siya ng Diyos. Ang Liwanag ay umurong mula sa mga pumili ng kadiliman."
                }
            ],
            "revelation_key": "Hindi tumakas si Jesus tulad ng isang fugitive. Umalis Siya tulad ng isang Hari na nagpasya, 'Hindi ito ang aking panahon.' Ang Kanyang paglabas ay kasing-supernatural ng Kanyang angkin - parehong nagpapatunay ng Kanyang pagka-diyos."
        }

        tl_data['cards'].append(card4)

        # Card 5: Discovery Activation
        card5 = {
            "order": 5,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Pansariling Pagtuklas",
            "discovery_questions": [
                {
                    "category": "Pagkakakilanlan",
                    "question": "Ginamit ni Jesus ang gramatika mismo upang patunayan ang Kanyang walang-hanggan. Ano ang mga implikasyon para sa iyong buhay kung ang karpintero mula sa Nazaret ay talagang ang walang-hanggang 'AKO AY' na umiiral bago ang paglikha?"
                },
                {
                    "category": "Tugon",
                    "question": "Perpekto ang pag-unawa ng mga lider ng mga Hudyo sa angkin ni Jesus - at pumili ng mga bato sa halip na pagsuko. Nang harapin ang pagka-diyos ni Cristo ngayon, anong 'mga bato' ang kinukuha ng mga tao sa halip na sumamba (intelektwalismo, pag-uyam, pag-iwas)?"
                },
                {
                    "category": "Soberanya",
                    "question": "Si Jesus ay kumalma na lumakad sa isang mamamatay-taong karamihan dahil 'ang Kanyang oras ay hindi pa dumarating.' Paano binabago ang ganap na soberanya ni Cristo sa Kanyang sariling kamatayan ang paraan ng iyong pagtingin sa Kanyang soberanya sa iyong buhay?"
                }
            ],
            "prayer": {
                "title": "Panalangin ng Pagsamba sa Walang-hanggang AKO AY",
                "content": "Panginoong Jesus, Ikaw ang AKO AY - ang Isa na umiiral sa labas ng panahon, bago si Abraham, bago ang paglikha, bago may anumang dumating sa pag-iral. Hindi Ka isang nilikha. Ikaw ang Lumikha. Hindi Ka limitado ng panahon. Ikaw ang Matanda ng mga Araw at ang walang-hanggang Kasalukuyan. Ipinapahayag ko na Ikaw lamang ang Diyos. Tulad ng mga nasa Templo, mayroon akong pagpili: kumuha ng mga bato ng pagtanggi o lumuhod sa pagsamba. Ngayong araw ay pumipili ako ng pagsamba. Kinikilala ko na Ikaw ay PANGINOON - ang parehong Pangalan na inihayag kay Moises sa umuusok na palumpong. Ikaw ang Ilaw ng Sanglibutan, at hinihiling ko na huwag Kang magtago mula sa akin tulad ng ginawa Mo sa mga tumangging sa Iyo. Buksan ang aking mga mata upang makita ang Iyong kaluwalhatian. Bigyan mo ako ng pananampalataya upang maniwala sa nakaintindi kahit ng Iyong mga kaaway: na Ikaw ay Diyos sa katawang-tao. Sa Iyong walang-hanggang Pangalan, ang Pangalan sa itaas ng lahat ng mga pangalan, Amen."
            }
        }

        tl_data['cards'].append(card5)

    # Save Tagalog translation
    output_path = 'discovery/tl/i_am_before_abraham_tl_001.json'
    os.makedirs('discovery/tl', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tl_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Translation saved to {output_path}")
    return output_path

if __name__ == '__main__':
    translate_i_am_before_abraham()
