#!/usr/bin/env python3
"""
Translate temple_cleansing_001 from English to Filipino
Following SKILL_discovery_translator.md guidelines
"""

import json
import sys
import os

# Add devocionales_scripts to path
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

# Constants
DB_PATH = '/home/runner/work/devocionales-json/devocionales-json/discovery/bible_database/MBB05_fil.SQLite3'
EN_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/en/temple_cleansing_en_001.json'
FIL_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/fil/temple_cleansing_fil_001.json'

def translate_to_filipino():
    """Main translation function"""

    # Load English source
    with open(EN_FILE, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Initialize verse resolver
    resolver = VerseResolver(DB_PATH)

    # Create Filipino translation
    fil_data = en_data.copy()

    # Update metadata fields
    fil_data['language'] = 'fil'
    fil_data['version'] = 'Magandang Balita Biblia'
    fil_data['estimated_reading_minutes'] = 7  # EN baseline 6 + 1 for Romance language patterns

    # Translate title and subtitle
    fil_data['title'] = 'Ang Paglilinis ng Templo'
    fil_data['subtitle'] = 'Nang ipahayag ni Jesus na Siya ang tunay na Templo'

    # Translate key verse
    citation, text, error = resolver.resolve('John 2:19')
    if error:
        print(f"Warning: Error resolving John 2:19 - {error}")
        fil_data['key_verse']['reference'] = 'Juan 2:19'
    else:
        fil_data['key_verse']['reference'] = citation
        fil_data['key_verse']['text'] = text

    # Translate each card
    cards = []

    # Card 1: Historical Context
    card1 = {
        'order': 1,
        'type': 'historical_context',
        'icon': '🕍',
        'title': 'Ang Templo: Ang Bahay na Naging Negosyo',
        'subtitle': 'Bakit nagalit si Jesus',
        'content': """Upang maunawaan ang galit ni Jesus, kailangan mong maunawaan kung ano ang nangyayari sa Templo:

💰 ANG TIWALING SISTEMA:

• Ang mga Judio ay dumating mula sa iba't ibang bahagi ng mundo para sa Paskuwa (2-3 milyong mga manlalakbay)
• Kailangan nilang magpalit ng salaping Romano (na may larawan ni Cesar) sa mga temple shekel
• Ang mga money changer ay nangsingil ng NAPAKALAKING komisyon (12-15% na kita)
• Ang mga pamilya ng mga pari (sina Anas at Caifas) ay nag-kontrol sa monopolyo

🐑 ANG NEGOSYO SA HANDOG:

• Ang mga manlalakbay ay nagdala ng mga hayop upang ihain
• Ang mga inspektors ng templo ay halos LAGING nakakakita ng 'mga depekto'
• Pagkatapos, kailangan nilang bumili ng mga 'aprubadong' hayop sa mataas na presyo
• Ang isang kalapati na nagkakahalaga ng 4 sentimo sa labas ay nagkakahalaga ng 75 sentimo sa loob
• Ang mga mahihirap ay pinagsamantalahan sa ngalan ng Dios

📍 ANG LOOBAN NG MGA GENTIL:

Lahat ng ito ay nangyari sa TANGING lugar kung saan ang mga hindi Judio ay maaaring manalangin:
• Ang ingay ay nakabibingi (mga hayop, sigawan, negosasyon)
• Ang amoy ay hindi maipaliwanag (dumi ng hayop)
• Ang mga Gentil na nakarating na naghahanap ng Dios ay nakakita ng isang pamilihan

🔥 BAKIT NAGALIT SI JESUS:

'Hindi ba't nakasulat: Ang aking bahay ay tatawaging bahay ng panalangin para sa lahat ng bansa? Ngunit ginawa ninyo itong yungib ng mga tulisan.' (Marcos 11:17)

Hindi lamang ito korupsyon. Ito ay PAGBUBUKOD. Ang lugar na idinisenyo upang akayin ang mga bansa sa Dios ay naging sagabal.""",
        'revelation_key': 'Ang relihiyong sumusamantala sa mga mahihirap at nag-eeksklusyon sa mga nawala ay nakakapukaw ng galit ng Dios, kahit gaano pa ka-"orthodox" ang hitsura nito.'
    }
    cards.append(card1)

    # Card 2: Prophetic Action
    # Resolve scripture connections
    mal_citation, mal_text, mal_error = resolver.resolve('Malachi 3:1-3')
    ps_citation, ps_text, ps_error = resolver.resolve('Psalm 69:9')

    card2 = {
        'order': 2,
        'type': 'prophetic_action',
        'icon': '🔥',
        'title': 'Ang Latigo ng mga Lubid: Banal na Galit sa Aksyon',
        'subtitle': 'Bakit hindi ito emosyonal na pagsabog',
        'content': """Sinabi sa Juan 2:15: 'At nang magawa niya ang latigo mula sa maliliit na lubid, itinakbo niya silang lahat mula sa templo...'

⏱️ SI JESUS AY GUMUGOL NG ORAS:

• Ang 'gumawa' ay nasa aorist tense - sadyang aksyon
• Kailangan niyang maghanap ng mga lubid, tupikin ang mga ito, gumawa ng latigo
• Ito ay HINDI walang kontrolng impulso
• Ito ay MAKATARUNGANG galit, kontrolado, may layunin

🎯 ANO ANG GINAWA NIYA:

1. Itinakbo ang mga nagbebenta ng mga baka at tupa
2. Ginulo ang mga mesa ng mga money changer (mga barya sa sahig)
3. Ikinasabog ang mga barya
4. Sa mga nagbebenta ng kalapati ay INIUTOS niya silang umalis (hindi gumamit ng karahasan sa kanila, sila ang pinaka-mahihirap)

💭 ANO ANG SINABI NIYA:

'Huwag ninyong gawing bahay ng kalakal ang bahay ng aking Ama' (v.16)

Pansinin: 'Aking Ama' - Inangkin ni Jesus ang banal na awtoridad sa Templo.

📖 ANO ANG NAALALA NG MGA ALAGAD:

'At naalala ng kanyang mga alagad na nakasulat: Ang pagkasibuk sa iyong bahay ay kumain sa akin' (Awit 69:9)

Ang Awit na ito ay MESIANIKO. Nauunawaan ng mga alagad: Si Jesus ay natutupad ang propesiya. Ang Mesiyas ay kinakailangang linisin ang Templo.

✨ ANG ARAL:

May lugar para sa banal na galit. Si Jesus, ang parehong nagsabing 'ibigin ang inyong mga kaaway', ay gumawa ng latigo at nilinis ang templo. Ang ilang mga bagay ay dapat harapin ng puwersa, hindi ng diplomasya.""",
        'scripture_connections': [
            {
                'reference': mal_citation if not mal_error else 'Malakias 3:1-3',
                'text': mal_text if not mal_error else "At ang Panginoon, na inyong hinahanap, ay biglang darating sa kanyang templo... Ngunit sino ang makatitiis sa araw ng kanyang pagdating?... Sapagkat siya ay tulad ng apoy ng tagapaglinis"
            },
            {
                'reference': ps_citation if not ps_error else 'Awit 69:9',
                'text': ps_text if not ps_error else "Sapagkat ang pagkasibuk sa iyong bahay ay kumain sa akin"
            }
        ],
        'revelation_key': 'Ang kaamuan ay hindi kahinaan. Si Jesus ay maamo sa mga sira at mabagsik sa mga mang-aapi. Tularan ang pareho.'
    }
    cards.append(card2)

    # Card 3: Sign Demand
    card3 = {
        'order': 3,
        'type': 'sign_demand',
        'icon': '🏛️',
        'title': 'Sirain ang Templong Ito: Ang Propesiyang Walang Nakaunawa',
        'subtitle': 'Juan 2:19-22 - Ang pinaka-radikal na teolohistikal na ikot',
        'content': """Ang mga lider ng relihiyon ay humihingi: 'Anong tanda ang maipakikita mo sa amin, dahil ginagawa mo ang mga bagay na ito?'

Ang sagot ni Jesus ay nakakasira:

'Sirain ninyo ang templong ito, at sa loob ng tatlong araw ay itatayo ko ito muli.'

🤔 ANG PAGKALITO:

Sumagot sila: 'Apatnapu't anim na taon ang ginugugol sa pagtatayo ng templong ito, at itatayo mo ito sa loob ng tatlong araw?'

Iniisip nila ang pisikal na gusali:
• Si Herodes ang Dakila ay nagsimula ng rekonstruksyon ng templo noong 20-19 BC
• Sa panahon ni Jesus (26-27 AD) sila ay nagtayo na ng 46 na taon
• Hindi ito matatapos hanggang 64 AD (6 taon lamang bago ito winasak ng mga Romano!)

💡 ANG PAHAYAG:

Ipinapaliwanag ni Juan: 'Ngunit siya ay nagsasalita tungkol sa TEMPLO NG KANYANG KATAWAN' (v.21)

Si Jesus ay gumagawa ng PUMUTOK na pahayag:

1️⃣ SIYA ANG TUNAY NA TEMPLO:
• Ang templo ay kung saan naninirahan ang Dios
• Si Jesus AY ang Dios na naninirahan sa gitna natin (Juan 1:14 - 'tumira')
• Hindi mo na kailangan ng gusali ng bato - ang Dios ay nasa laman

2️⃣ HINUHULAAN NIYA ANG KANYANG KAMATAYAN AT PAGKABUHAY:
• 'Sirain' - aktibong tinig: papatayin nila Siya
• 'Itatayo ko ito' - aktibong tinig: SIYA ay muling mabubuhay (hindi passive na mabubuhay)
• 'Tatlong araw' - eksaktong propesiya ng Kanyang pagkabuhay

3️⃣ PINALITAN NIYA ANG BUONG SISTEMA:
• Wala nang mga handog na hayop - si Jesus ang huling Kordero
• Wala nang tagapamagitan na pari - si Jesus ang ating Dakilang Pari
• Wala nang banal na lugar - TAYO ay mga templo ng Banal na Espiritu (1 Cor 6:19)

⏰ NOONG NAUNAWAAN NILA:

'Kaya nang siya ay muling nabuhay sa mga patay, naalala ng kanyang mga alagad na sinabi niya ito sa kanila; at sumampalataya sila sa Kasulatan, at sa salitang sinabi ni Jesus' (v.22)

Pagkatapos lamang ng pagkabuhay ay nag-ugnay sila ng mga tuldok.""",
        'identity_statement': 'Ikaw ay ang templo kung saan naninirahan ang Dios. Hindi mo kailangang pumunta sa banal na lugar upang mahanap ang Dios. Siya ay nabubuhay sa iyo sa pamamagitan ng Kanyang Espiritu.',
        'revelation_key': 'Ang templo ng Jerusalem ay winasak noong 70 AD at hindi na muling itinayo. Bakit? Dahil ang tunay na Templo (si Cristo) ay dumating na. Ang lumang sistema ay natupad ang layunin nito.'
    }
    cards.append(card3)

    # Card 4: Typology Thread
    card4 = {
        'order': 4,
        'type': 'typology_thread',
        'icon': '🧵',
        'title': 'Ang Sinulid ng Templo: Mula sa Eden Hanggang sa Pahayag',
        'subtitle': 'Paano si Jesus ang rurok ng lahat',
        'content': """Ang konsepto ng 'templo' ay tumatakbo sa buong Bibliya:

🌳 EDEN - ANG UNANG TEMPLO:
• Hardin kung saan naglalakad ang Dios kasama ng tao (Genesis 3:8)
• Direktang pakikisama nang walang tagapamagitan
• Akseso ay nawala sa pamamagitan ng kasalanan

⛺ TABERNAKULO - PORTABLE NA TEMPLO:
• Ang Dios ay naninirahan sa isang tolda sa gitna ng kampo (Exodo 40)
• Ang kaluwalhatian (Shekinah) ay bumababa sa ulap
• Sistema ng sakripisyo upang lumapit sa Dios

🏛️ TEMPLO NI SOLOMON - PERMANENTENG TEMPLO:
• Bahay ng Dios sa gitna ng Kanyang bayan (1 Hari 8)
• Bahay ng panalangin para sa lahat ng bansa
• Winasak ng Babilonia noong 586 BC

🔨 TEMPLO NI ZERUBBABEL/HERODES - MULING ITINAYONG TEMPLO:
• Mas kaunting kaluwalhatian kaysa sa una (Ezra 3:12)
• Pag-asa: Hageo 2:9 - 'Ang kaluwalhatian ng huling bahay na ito ay magiging mas dakila kaysa sa una'
• Pinalaki ni Herodes, ngunit ito ay nananatiling walang laman (ang Shekinah ay hindi na bumalik)

✨ SI JESUS - ANG NAKAKATAWANG TEMPLO:
• 'Ang Salita ay naging laman, at TUMIRA (eskēnōsen = nagtayo ng kanyang tabernakulo) sa gitna natin' (Juan 1:14)
• 'Sirain ang templong ito, at sa loob ng tatlong araw ay itatayo ko ito' (Juan 2:19)
• Ang kaluwalhatian ng Dios ay bumalik - sa lamang tao

⛪ ANG SIMBAHAN - BUHAY NA TEMPLO:
• 'Kayo ay... gusali ng Dios' (1 Cor 3:9)
• 'Mga buhay na bato... espirituwal na bahay' (1 Pedro 2:5)
• Ang Dios ay naninirahan sa Kanyang bayan nang sama-sama

🌆 BAGONG JERUSALEM - WALANG TEMPLO:
• 'At hindi ako nakakita ng templo doon: sapagkat ang Panginoong Dios Makapangyarihan at ang Kordero ay ang templo nito' (Pahayag 21:22)
• Kumpletong pagbabalik sa Eden - direktang pakikisama ay naibalik""",
        'revelation_key': 'Ang lahat ng kasaysayan ng Bibliya ay ang paghahanap ng Dios na MANIRAHAN sa Kanyang bayan. Si Jesus ang huling sagot: Emmanuel, ang Dios ay kasama natin.'
    }
    cards.append(card4)

    # Card 5: Discovery Activation
    card5 = {
        'order': 5,
        'type': 'discovery_activation',
        'icon': '🙏',
        'title': 'Pansariling Pagtuklas',
        'discovery_questions': [
            {
                'category': 'Pansariling Templo',
                'question': 'Sinabi ni Pablo na ang iyong katawan ay templo ng Banal na Espiritu (1 Cor 6:19). Mayroon bang mga "money changer at nagbebenta" sa iyong templo - mga bagay na kailangang itakbo upang ang Dios ay ganap na makapamahay?'
            },
            {
                'category': 'Banal na Galit',
                'question': 'Ipinakita ni Jesus ang banal na galit laban sa tiwaling relihiyon. Mayroon bang mga kawalang-katarungan sa iyong lugar ng impluwensya na nangangailangan ng malakas na pagharap, hindi lamang passive na panalangin?'
            },
            {
                'category': 'Pagkabuhay',
                'question': 'Sinabi ni Jesus na "sirain ang templong ito at sa loob ng tatlong araw ay ITATAYO KO ITO". Siya ay nagbangon ng kanyang sariling katawan. Anong bahagi ng iyong buhay ang kailangan ng kapangyarihan ng pagkabuhay ni Cristo upang mabuhay mula sa mga patay?'
            }
        ],
        'prayer': {
            'title': 'Panalangin ng Paglilinis',
            'content': 'Jesus, aking buhay na Templo. Salamat na hindi ko na kailangang maghanap ng gusali upang mahanap Ka - nabubuhay Ka sa akin. Ngayong araw ay hihingi ako sa Iyo na linisin ang templo ng aking buhay. Itakbo ang lahat na hindi ka pinararangal. Guluhin ang mga mesa ng aking mga diyus-diyusan. Linisin ang mga looban ng aking puso upang maging bahay ng panalangin, hindi yungib ng mga tulisan. Ipaalala mo sa akin na ang parehong kapangyarihan na nagbangon sa Iyo mula sa libingan sa loob ng tatlong araw ay nabubuhay sa akin. Ibangon ang mga patay na bahagi ng aking buhay. Nawa ako ay maging dalisay na templo kung saan ang Iyong kaluwalhatian ay nananatili nang walang hadlang. Sa ngalan ni Jesus, Amen.'
        }
    }
    cards.append(card5)

    fil_data['cards'] = cards

    # Translate tags
    fil_data['tags'] = [
        'templo',
        'paglilinis',
        'banal_na_galit',
        'pagkabuhay',
        'katawan_ni_cristo',
        'propesiya'
    ]

    # Translate metadata themes
    fil_data['metadata']['themes'] = [
        'Si Jesus bilang tunay na templo',
        'Paglilinis at kabanalan',
        'Propesiya ng kamatayan at pagkabuhay',
        'Tipohiya ng Lumang Tipan'
    ]

    # Calculate word count (approximate for Filipino)
    total_words = sum(len(card.get('content', '').split()) for card in fil_data['cards'])
    fil_data['metadata']['total_word_count'] = total_words

    # Close resolver
    resolver.close()

    # Save Filipino translation
    os.makedirs(os.path.dirname(FIL_FILE), exist_ok=True)
    with open(FIL_FILE, 'w', encoding='utf-8') as f:
        json.dump(fil_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Translation completed: {FIL_FILE}")
    print(f"📊 Word count: {total_words}")
    print(f"⏱️ Reading time: {fil_data['estimated_reading_minutes']} minutes")

    return FIL_FILE

if __name__ == '__main__':
    translate_to_filipino()
