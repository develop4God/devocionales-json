#!/usr/bin/env python3
"""
Translate temple_cleansing Bible study to Tagalog
"""
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../devocionales_scripts'))
from verse_resolver import VerseResolver

# Paths
DB_PATH = "/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3"
EN_FILE = "/home/runner/work/devocionales-json/devocionales-json/discovery/en/temple_cleansing_en_001.json"
TL_FILE = "/home/runner/work/devocionales-json/devocionales-json/discovery/tl/temple_cleansing_tl_001.json"

def translate_temple_cleansing():
    """Translate the temple_cleansing study to Tagalog"""

    # Load English source
    with open(EN_FILE, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Create Tagalog translation
    tl_data = {
        "id": en_data["id"],
        "type": en_data["type"],
        "date": en_data["date"],
        "title": "Ang Paglilinis ng Templo",
        "subtitle": "Nang ipahayag ni Jesus na Siya ang tunay na Templo",
        "language": "tl",
        "version": "Ang Dating Biblia",
        "estimated_reading_minutes": 7,  # EN is 6, adding 1 for Tagalog
        "key_verse": {},
        "cards": [],
        "tags": [
            "templo",
            "paglilinis",
            "banal_na_galit",
            "pagkabuhay_na_mag-uli",
            "katawan_ni_kristo",
            "propesiya"
        ],
        "metadata": {
            "total_word_count": en_data["metadata"]["total_word_count"],
            "greek_words_count": en_data["metadata"]["greek_words_count"],
            "scripture_references_count": en_data["metadata"]["scripture_references_count"],
            "difficulty_level": en_data["metadata"]["difficulty_level"],
            "themes": [
                "Si Jesus bilang tunay na templo",
                "Paglilinis at kabanalan",
                "Propesiya ng kamatayan at pagkabuhay na mag-uli",
                "Tipolohiya ng Lumang Tipan"
            ]
        }
    }

    # Initialize verse resolver
    with VerseResolver(DB_PATH) as resolver:

        # Translate key verse
        print("Translating key verse: John 2:19")
        cita, texto, error = resolver.resolve("John 2:19")
        if error:
            print(f"  ERROR: {error}")
            sys.exit(1)
        print(f"  → {cita}")
        tl_data["key_verse"] = {
            "reference": cita,
            "text": texto
        }

        # Card 1: Historical Context
        print("\nTranslating Card 1: Historical Context")
        tl_data["cards"].append({
            "order": 1,
            "type": "historical_context",
            "icon": "🕍",
            "title": "Ang Templo: Ang Bahay na Naging Negosyo",
            "subtitle": "Bakit galit na galit si Jesus",
            "content": """Upang maunawaan ang galit ni Jesus, kailangan mong maintindihan kung ano ang nangyayari sa Templo:

💰 ANG TIWALING SISTEMA:

• Ang mga Judio ay nagmula sa buong mundo para sa Paskuwa (2-3 milyong mga manalangin)
• Kailangan nilang palitan ang salaping Romano (na may larawan ni Cesar) ng mga templong siklo
• Ang mga mangangalakal ng salapi ay nangsingil ng MAPANG-ABUSONG komisyon (12-15% na kita)
• Ang mga pamilyang saserdote (Anas at Caifas) ay kumokontrol ng monopolyo

🐑 ANG NEGOSYO NG HANDOG:

• Ang mga manalangin ay nagdala ng mga hayop upang ihandog
• Ang mga tagasuri ng templo ay HALOS LAGING nakakakita ng 'mga depekto'
• Pagkatapos ay kailangan nilang bumili ng 'aprubadong' hayop sa mataas na presyo
• Ang kalapating nagkakahalaga ng 4 sentimos sa labas ay nagkakahalaga ng 75 sentimos sa loob
• Ang mga mahihirap ay sinusamantala sa ngalan ng Diyos

📍 ANG LOOBAN NG MGA HENTIL:

Ang lahat ng ito ay naganap sa TANGING lugar kung saan maaaring manalangin ang mga hindi Judio:
• Ang ingay ay nakabibingi (mga hayop, sigaw, mga negosasyon)
• Ang amoy ay hindi mapagtitiisan (dumi ng hayop)
• Ang mga Hentil na dumating upang hanapin ang Diyos ay nakatagpo ng isang pamilihan

🔥 BAKIT NAGALIT SI JESUS:

'Di ba nasusulat, Ang bahay ko ay tatawaging bahay ng panalangin ng lahat ng mga bansa? datapuwa't ginawa ninyong yungib ng mga tulisan.' (Marcos 11:17)

Hindi lamang ito katiwalian. Ito ay PAGBUBUKOD. Ang lugar na idinisenyo upang akitin ang mga bansa sa Diyos ay naging hadlang.""",
            "revelation_key": "Ang relihiyong sumusamantala sa mga mahihirap at nag-iiba sa mga nawala ay nagpapagalit sa Diyos, gaano man ito 'ortodokso' na tila."
        })

        # Card 2: Prophetic Action
        print("Translating Card 2: Prophetic Action")

        # Resolve scripture connections for card 2
        mal_cita, mal_texto, mal_error = resolver.resolve("Malachi 3:1-3")
        if mal_error:
            print(f"  ERROR resolving Malachi 3:1-3: {mal_error}")
            sys.exit(1)
        print(f"  → {mal_cita}")

        ps_cita, ps_texto, ps_error = resolver.resolve("Psalm 69:9")
        if ps_error:
            print(f"  ERROR resolving Psalm 69:9: {ps_error}")
            sys.exit(1)
        print(f"  → {ps_cita}")

        tl_data["cards"].append({
            "order": 2,
            "type": "prophetic_action",
            "icon": "🔥",
            "title": "Ang Panghampas ng mga Lubid: Banal na Galit sa Aksyon",
            "subtitle": "Bakit hindi ito emosyonal na pagsabog",
            "content": """Sinasabi ng Juan 2:15: 'At nang siya'y gumawa ng isang panghampas na lubid ay itinakwil niya ang lahat sa templo...'

⏱️ NAGLAAN NG ORAS SI JESUS:

• Ang 'gumawa' ay nasa aorist tense - sadyang aksyon
• Kailangan niyang maghanap ng mga lubid, saliwan, gawing latigo
• Ito ay HINDI hindi kontroladong impulso
• Ito ay MAKATARUNGANG galit, kontrolado, may layunin

🎯 ANO ANG GINAWA NIYA:

1. Itinakwil ang mga nagbibili ng baka at tupa
2. Ginupo ang mga hapag ng mga mangangalakal ng salapi (barya sa sahig)
3. Ikalat ang mga barya
4. Sa mga nagbibili ng kalapati ay INUTUSAN sila na umalis (walang ginamit na karahasan sa kanila, sila ang pinakamahirap)

💭 ANO ANG SINABI NIYA:

'Huwag ninyong gawin ang bahay ng aking Ama na bahay ng kalakal' (v.16)

Pansinin: 'Aking Ama' - inaangkin ni Jesus ang banal na awtoridad sa Templo.

📖 ANO ANG NAALAALA NG MGA ALAGAD:

'At naalaala ng kaniyang mga alagad na nasusulat, Ang sikap sa iyong bahay ay lumalamon sa akin' (Awit 69:9)

Ang Awit na ito ay MESYANIKO. Nauunawaan ng mga alagad: Tinutupad ni Jesus ang propesiya. Ang Mesiyas ay kailangang maglinis ng Templo.

✨ ANG ARAL:

Mayroong lugar para sa banal na galit. Si Jesus, ang siya ring nagsabi ng 'ibigin ang inyong mga kaaway', ay gumawa ng latigo at nilinis ang templo. May mga bagay na dapat harapin ng lakas, hindi ng diplomasya.""",
            "scripture_connections": [
                {
                    "reference": mal_cita,
                    "text": mal_texto
                },
                {
                    "reference": ps_cita,
                    "text": ps_texto
                }
            ],
            "revelation_key": "Ang pagpapakumbaba ay hindi kahinaan. Si Jesus ay mapagpakumbaba sa mga sira at mabangis sa mga mang-aapi. Tularan ang parehong."
        })

        # Card 3: Sign Demand
        print("Translating Card 3: Sign Demand")
        tl_data["cards"].append({
            "order": 3,
            "type": "sign_demand",
            "icon": "🏛️",
            "title": "Sirain ang Templong Ito: Ang Propesiyang Walang Nakaunawa",
            "subtitle": "Juan 2:19-22 - Ang pinaka-radikal na teolohikal na pagliko",
            "content": """Ang mga pinunong relihiyoso ay nanghingi: 'Anong tanda ang ipakikita mo sa amin, yamang ginagawa mo ang mga bagay na ito?'

Ang sagot ni Jesus ay nakakasira:

'Sirain ninyo ang templong ito, at sa loob ng tatlong araw ay aking itatayo.'

🤔 ANG KALITUHAN:

Sumagot sila: 'Apatnapu't anim na taon ang templong ito na itinatayo, at iyong itatayo sa loob ng tatlong araw?'

Nag-iisip sila tungkol sa pisikal na gusali:
• Si Herodes ang Dakila ay nagsimula ng muling pagtatayo ng templo noong 20-19 BC
• Sa panahon ni Jesus (26-27 AD) ay 46 taon na silang nagtayo
• Hindi ito matatapos hanggang 64 AD (6 taon lamang bago ito winasak ng mga Romano!)

💡 ANG PAGHAHAYAG:

Ipinaliwanag ni Juan: 'Datapuwa't sinasabi niya ang tungkol sa TEMPLO NG KANIYANG KATAWAN' (v.21)

Gumagawa si Jesus ng PAPUTOK na pahayag:

1️⃣ SIYA AY ANG TUNAY NA TEMPLO:
• Ang templo ay kung saan naninirahan ang Diyos
• Si Jesus AY Diyos na naninirahan sa atin (Juan 1:14 - 'tumayo ang tolda')
• Hindi na kailangan ng gusaling bato - ang Diyos ay nasa laman

2️⃣ HINUHULAAN NIYA ANG KANIYANG KAMATAYAN AT PAGKABUHAY NA MAG-ULI:
• 'Sirain' - aktibong tinig: papatayin nila Siya
• 'Aking itatayo' - aktibong tinig: SIYA ay muling mabubuhay (hindi pasibong muling binuhay)
• 'Tatlong araw' - eksaktong propesiya ng Kaniyang pagkabuhay na mag-uli

3️⃣ PINALITAN NIYA ANG BUONG SISTEMA:
• Wala nang mga handog na hayop - si Jesus ang huling Kordero
• Wala nang tagapamagitang saserdote - si Jesus ang ating Dakilang Saserdote
• Wala nang banal na lugar - tayo AY mga templo ng Banal na Espiritu (1 Cor 6:19)

⏰ KAILAN NILA NAINTINDIHAN:

'Nang siya nga'y magbangon na muli sa mga patay, ay naalaala ng kaniyang mga alagad na sinabi niya ito: at nagsipaniwala sila sa kasulatan, at sa salitang sinabi ni Jesus' (v.22)

Pagkatapos lamang ng pagkabuhay na mag-uli ay nag-ugnay sila ng mga tuldok.""",
            "identity_statement": "Ikaw ay ang templo kung saan naninirahan ang Diyos. Hindi mo kailangang pumunta sa banal na lugar upang matagpuan ang Diyos. Siya ay naninirahan sa iyo sa pamamagitan ng Kaniyang Espiritu.",
            "revelation_key": "Ang templo ng Jerusalem ay winasak noong 70 AD at hindi na muling itinayo. Bakit? Sapagkat ang tunay na Templo (si Kristo) ay dumating na. Ang lumang sistema ay natupad ang layunin nito."
        })

        # Card 4: Typology Thread
        print("Translating Card 4: Typology Thread")
        tl_data["cards"].append({
            "order": 4,
            "type": "typology_thread",
            "icon": "🧵",
            "title": "Ang Sinulid ng Templo: Mula sa Eden Hanggang sa Pahayag",
            "subtitle": "Paano si Jesus ang rurok ng lahat",
            "content": """Ang konsepto ng 'templo' ay tumatakbo sa buong Bibliya:

🌳 EDEN - ANG UNANG TEMPLO:
• Halamanan kung saan lumakad ang Diyos kasama ng tao (Genesis 3:8)
• Direktang pakikipag-ugnayan nang walang tagapamagitan
• Nawalang ang access sa pamamagitan ng kasalanan

⛺ TABERNAKULO - TEMPLONG MADADALANG:
• Naninirahan ang Diyos sa tolda sa gitna ng kampo (Exodo 40)
• Ang kaluwalhatian (Shekinah) ay bumaba sa ulap
• Sistema ng handog upang lumapit sa Diyos

🏛️ TEMPLO NI SOLOMON - PERMANENTENG TEMPLO:
• Bahay ng Diyos sa gitna ng Kaniyang bayan (1 Hari 8)
• Bahay ng panalangin para sa lahat ng bansa
• Winasak ng Babilonya noong 586 BC

🔨 TEMPLO NI ZOROBABEL/HERODES - MULING ITINAYONG TEMPLO:
• Hindi gaanong maluwalhati kaysa una (Esdras 3:12)
• Pag-asa: Hagai 2:9 - 'Ang kaluwalhatian ng huling bahay na ito ay magiging dakila kaysa dati'
• Pinalaki ito ni Herodes, ngunit nananatiling walang laman (hindi na bumalik ang Shekinah)

✨ SI JESUS - ANG NAGING KATAWANG TEMPLO:
• 'Ang Verbo ay nagkatawang tao, at NANAHAN (eskēnōsen = nagtayo ng kaniyang tolda) sa gitna natin' (Juan 1:14)
• 'Sirain ninyo ang templong ito, at sa loob ng tatlong araw ay aking itatayo' (Juan 2:19)
• Bumalik ang kaluwalhatian ng Diyos - sa katawang tao

⛪ ANG IGLESYA - BUHAY NA TEMPLO:
• 'Kayo ay... gusali ng Diyos' (1 Cor 3:9)
• 'Mga batong buhay... espirituwal na bahay' (1 Pedro 2:5)
• Naninirahan ang Diyos sa Kaniyang bayan na sama-sama

🌆 BAGONG JERUSALEM - WALANG TEMPLO:
• 'At hindi ko nakita ang templo doon: sapagka't ang Panginoong Dios na Makapangyarihan sa lahat at ang Cordero ay siyang templo niyaon' (Apocalipsis 21:22)
• Kumpletong pagbabalik sa Eden - muling naibalik ang direktang pakikipag-ugnayan""",
            "revelation_key": "Ang buong kasaysayan ng Bibliya ay ang Diyos na naghahangad na MANAHAN sa Kaniyang bayan. Si Jesus ang huling sagot: Emmanuel, Diyos na kasama natin."
        })

        # Card 5: Discovery Activation
        print("Translating Card 5: Discovery Activation")
        tl_data["cards"].append({
            "order": 5,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Pansariling Pagtuklas",
            "discovery_questions": [
                {
                    "category": "Pansariling Templo",
                    "question": "Sinasabi ni Pablo na ang iyong katawan ay templo ng Banal na Espiritu (1 Cor 6:19). Mayroon bang 'mga mangangalakal ng salapi at mga nagbibili' sa iyong templo - mga bagay na kailangang itakwil upang lubusang makapanahan ang Diyos?"
                },
                {
                    "category": "Banal na Galit",
                    "question": "Ipinakita ni Jesus ang banal na galit laban sa tiwaling relihiyon. May mga kawalang-katarungan ba sa iyong saklaw ng impluwensya na nangangailangan ng matinding pagharap, hindi lamang pasibong panalangin?"
                },
                {
                    "category": "Pagkabuhay na Mag-uli",
                    "question": "Sinabi ni Jesus 'sirain ang templong ito at sa loob ng tatlong araw ay AKING ITATAYO ITO'. Binuhay Niya ang Kaniyang sariling katawan. Anong bahagi ng iyong buhay ang nangangailangan ng kapangyarihan ng pagkabuhay na mag-uli ni Kristo upang buhayin mula sa kamatayan?"
                }
            ],
            "prayer": {
                "title": "Panalangin ng Paglilinis",
                "content": "Jesus, aking buhay na Templo. Salamat na hindi ko na kailangang maghanap ng gusali upang matagpuan Ka - naninirahan Ka sa akin. Ngayon ay hinihiling Ko sa Iyo na linisin ang templo ng aking buhay. Itakwil ang lahat ng hindi Ka pinaparangal. Gupuin ang mga hapag ng aking mga diyus-diyusan. Linisin ang mga looban ng aking puso upang maging bahay ng panalangin, hindi yungib ng mga tulisan. Ipaalala sa akin na ang parehong kapangyarihang bumuhay sa Iyo mula sa libingan sa loob ng tatlong araw ay nabubuhay sa akin. Buhayin ang mga patay na bahagi ng aking buhay. Nawa ay maging malinis na templo ako kung saan ang Iyong kaluwalhatian ay nananahan nang walang hadlang. Sa ngalan ni Jesus, Amen."
            }
        })

    # Save the translated file
    with open(TL_FILE, 'w', encoding='utf-8') as f:
        json.dump(tl_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Translation saved to: {TL_FILE}")
    return TL_FILE

if __name__ == "__main__":
    translate_temple_cleansing()
