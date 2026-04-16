#!/usr/bin/env python3
"""
Translate born_again_en_001.json to Tagalog
Uses VerseResolver for all scripture lookups
"""

import json
import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'devocionales_scripts'))
from verse_resolver import VerseResolver

def translate_born_again():
    # Load English source
    with open('discovery/en/born_again_en_001.json', 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Create Tagalog version
    tl_data = en_data.copy()

    # Update metadata
    tl_data['language'] = 'tl'
    tl_data['version'] = 'Ang Dating Biblia'
    tl_data['estimated_reading_minutes'] = 5

    # Initialize verse resolver
    db_path = 'bible_database/ADB_tl.SQLite3'

    with VerseResolver(db_path) as resolver:
        # Translate title and subtitle
        tl_data['title'] = 'Dapat Kang Ipanganak na Muli'
        tl_data['subtitle'] = 'Nang ang guro ng Israel ay makatuklasan na ang kanyang relihiyon ay hindi sapat'

        # Translate key verse
        key_ref = en_data['key_verse']['reference']
        cita, texto, error = resolver.resolve(key_ref)
        if error:
            print(f"Error resolving {key_ref}: {error}")
            sys.exit(1)

        tl_data['key_verse']['reference'] = cita
        tl_data['key_verse']['text'] = texto

        # Translate cards
        tl_data['cards'] = []

        # Card 1: Character Context
        card1 = en_data['cards'][0].copy()
        card1['title'] = 'Si Nicodemo: Ang Taong May Lahat ng Bagay'
        card1['subtitle'] = 'Bakit napakahalaga ng kanyang pagbisita sa gabi'
        card1['content'] = """Si Juan ay nagbibigay sa atin ng tatlong mahalagang katotohanan tungkol kay Nicodemo sa isang talata lamang (Juan 3:1):

1️⃣ 'ISANG TAO SA MGA FARISEO':
• Ang mga Fariseo ay ang mga piniling relihiyoso - 6,000 lamang sa buong Israel
• Nagsaulo sila ng buong Torah
• Nag-aayuno sila ng dalawang beses sa isang linggo
• Nagbibigay sila ng ikasampung bahagi kahit ng mga pampalasa mula sa kanilang hardin
• Sila ang pinaka-respetado ng mga tao

2️⃣ 'NA ANG PANGALAN AY SI NICODEMO':
• Ang kanyang pangalan ay nangangahulugang 'Manlulupig ng mga tao'
• Ito ay isang prestihiyosong pangalan, mula sa isang aristokratikong pamilya

3️⃣ 'ISANG PINUNO NG MGA JUDIO':
• Miyembro ng Sanedrin - ang pinakamataas na konseho ng 70 katandaan
• Tanging ang pinaka-marunong lamang ang nakakarating sa Sanedrin
• Tinawag siya ni Jesus na 'ANG guro ng Israel' (Juan 3:10)

🌙 BAKIT SIYA DUMATING SA GABI:

Hindi lamang upang maiwasan ang pagpuna. Ito ay simboliko:
• Si Nicodemo ay nasa 'kadiliman ng espiritu' sa kabila ng kanyang kaalaman
• Siya ay natatakot na mawala ang kanyang posisyon
• Ang gabi ay kumakatawan sa kalagayan ng relihiyosong kaluluwa na walang si Cristo

💔 ANG IRONYA:

Ang taong may pinakamataas na kaalaman sa relihiyon sa Israel ay pumunta upang magtanong sa karpintero mula sa Nazaret. Ang kanyang perpektong relihiyon ay nag-iwan sa kanya ng kawalan."""

        card1['revelation_key'] = 'Maaari kang maging perpekto sa relihiyon at patay sa espiritu. Ang edukasyon sa teolohiya ay hindi pumapalit sa bagong kapanganakan.'

        tl_data['cards'].append(card1)

        # Card 2: Greek Exegesis
        card2 = en_data['cards'][1].copy()
        card2['title'] = 'Anōthen: Ang Salitang May Dobleng Kahulugan'
        card2['subtitle'] = 'Bakit nalito si Nicodemo'
        card2['content'] = """Sinabi sa kanya ni Jesus: 'Kailangan mong ipanganak na ANŌTHEN.'

Ang salitang Griego na ito ay may DALAWANG kahulugan nang sabay:

1️⃣ 'MULI' (minsan pa, pangalawang beses)
2️⃣ 'MULA SA ITAAS' (mula sa langit, mula sa Diyos)

🤔 ANG KALITUHAN NI NICODEMO:

Naiintindihan lamang ni Nicodemo ang unang kahulugan: 'Paanong ipanganganak ang tao, kung siya'y matanda na? Makakasok pa ba siya sa sinapupunan ng kaniyang ina, at ipanganganak?'

Nag-iisip siya ng paulit-ulit na PISIKAL na kapanganakan.

✨ ANG TUNAY NA IBIG SABIHIN NI JESUS:

Sinadya ni Jesus na gamitin ang parehong kahulugan:
• Kailangan mong ipanganak na MULI (hindi mo mapapabuti ang iyong unang kapanganakan)
• Kailangan mong ipanganak MULA SA ITAAS (tanging Diyos lamang ang makakagawa nito, hindi ikaw)

📊 ANG TUGON NI JESUS (v.5-6):

'Malibang ang tao'y ipanganak ng TUBIG at ng ESPIRITU, ay hindi siya makakasok sa kaharian ng Diyos.'

• Tubig = malamang na sanggunian sa Ezekiel 36:25-27 (espirituwal na paglilinis)
• Espiritu = ang Banal na Espiritu na gumagawa ng bagong kapanganakan

'Ang ipinanganak ng laman ay LAMAN; at ang ipinanganak ng Espiritu ay espiritu.'

Ang laman ay nanganganak lamang ng laman. Kahit gaano pa itong turuan, disiplinahin o pinuhin - nananatili itong laman. Tanging ang Espiritu lamang ang makalilikha ng espirituwal na buhay."""

        card2['greek_words'][0]['meaning'] = 'Muli / Mula sa itaas'
        card2['greek_words'][0]['revelation'] = 'Parehong kahulugan ay kinakailangan: ito ay kapanganakan na nangyayari na MULI (hindi ka pinabuti, ikaw ay PINALITAN), at nanggagaling MULA SA ITAAS (hindi ito sariling likha, ito ay kaloob ng Diyos).'

        card2['greek_words'][1]['meaning'] = 'Ipanganak, isinilang'
        card2['greek_words'][1]['revelation'] = 'Ito ay passive voice sa Griego - \'ipanganak\', hindi \'ipanganak ang iyong sarili\'. Ang bagong kapanganakan ay isang bagay na TINATANGGAP mo, hindi isang bagay na GINAGAWA mo.'

        card2['revelation_key'] = 'Hindi mo mapapanganak muli ang iyong sarili, tulad ng hindi mo napanganak ang iyong sarili noong una. Parehong kapanganakan ay tinatanggap, hindi nakakamit.'

        tl_data['cards'].append(card2)

        # Card 3: Theological Depth
        card3 = en_data['cards'][2].copy()
        card3['title'] = 'Ang Hangin ay Humihihip Kung Saan Nais Nito'
        card3['subtitle'] = 'Juan 3:8 - Ang hiwaga ng Espiritu'
        card3['content'] = """Gumamit si Jesus ng perpektong larawan upang ipaliwanag ang bagong kapanganakan:

'Ang hangin ay humihihip kung saan nais nito, at naririnig mo ang lagaslas niyaon, datapuwa't hindi mo maalaman kung saan nanggagaling, at kung saan naparoroon: gayon ang bawa't ipinanganak ng Espiritu.'

🌬️ ANG PALAISIPAN SA SALITA:

Sa Griego (at Hebreo), ang parehong salita ay nangangahulugang HANGIN at ESPIRITU:
• Griego: Pneuma (πνεῦμα)
• Hebreo: Ruach (רוּחַ)

Gumawa si Jesus ng tatlong magkakaparehong halimbawa:

1️⃣ ANG HANGIN AY HINDI NAKIKITA:
• Hindi mo MAKIKITA ang hangin
• Nakikita mo lamang ang mga EPEKTO nito (mga dahong gumagalaw, mga puno na yumuyuko)
• Ganoon din ang Espiritu - hindi mo Siya nakikita, ngunit nakikita mo ang Kanyang gawa sa mga buhay na binago

2️⃣ ANG HANGIN AY HINDI MAKONTROL:
• Ang hangin ay 'humihihip kung saan nais nito' - hindi mo ito pinapatakbo
• Ang Espiritu ay soberano - Siya ay pumipili kung kailan at saan Siya kikilos
• Hindi mo magagawa ang isang pagbabagong-buhay; maaari mo lamang maghanda para sa pagihip ng Hangin

3️⃣ ANG HANGIN AY HINDI MAIKAKAILA:
• 'Naririnig mo ang lagaslas niyaon' - kahit hindi mo ito nakikita, ALAM mo na nandoon ito
• Ang isang taong ipinanganak ng Espiritu ay gumagawa ng PATUNAY - bunga, pagbabago, pagbabagong-anyo

⚠️ ANG BABALA KAY NICODEMO:

Nais ni Nicodemo na MAINTINDIHAN bago maniwala. Sinabi sa kanya ni Jesus: 'Hindi mo lubusang maintindihan ang bagong kapanganakan, tulad ng hindi mo lubusang maintindihan ang hangin. Ngunit maaari mo itong MARANASAN'."""

        # Resolve scripture connections for card 3
        conn1_ref = en_data['cards'][2]['scripture_connections'][0]['reference']
        cita1, texto1, error1 = resolver.resolve(conn1_ref)
        if error1:
            print(f"Error resolving {conn1_ref}: {error1}")
            sys.exit(1)

        conn2_ref = en_data['cards'][2]['scripture_connections'][1]['reference']
        cita2, texto2, error2 = resolver.resolve(conn2_ref)
        if error2:
            print(f"Error resolving {conn2_ref}: {error2}")
            sys.exit(1)

        card3['scripture_connections'] = [
            {'reference': cita1, 'text': texto1},
            {'reference': cita2, 'text': texto2}
        ]

        card3['revelation_key'] = 'Ang gawa ng Espiritu ay misteryoso ngunit totoo, hindi nakikita ngunit hindi maikakaila, soberano ngunit maaaring maranasan.'

        tl_data['cards'].append(card3)

        # Card 4: Necessity Emphasis
        card4 = en_data['cards'][3].copy()
        card4['title'] = 'Huwag Magtaka: KINAKAILANGAN Ito'
        card4['subtitle'] = 'Bakit ang bagong kapanganakan ay hindi opsyonal'
        card4['content'] = """Sinabi ni Jesus sa Juan 3:7: 'Huwag kang magtaka na sinabi ko sa iyo, Kailangang kayo'y mangagpanganak na muli.'

Ang salitang 'kailangan' (dei sa Griego) ay nagpapahiwatig ng:
• Ganap na obligasyon
• Banal na pangangailangan
• Hindi-mapag-usapang kinakailangan

❌ BAKIT ANG RELIHIYON AY HINDI SAPAT:

Si Nicodemo ay may:
✓ Kaalaman sa Bibliya (guro ng Israel)
✓ Posisyon sa relihiyon (Fariseo)
✓ Awtoridad (miyembro ng Sanedrin)
✓ Walang-kapintasang moralidad (tumutupad ng 613 utos)
✓ Paggalang mula sa mga tao

Ngunit sinabi sa kanya ni Jesus: 'LAHAT ng iyan ay hindi sapat. Kailangan mong IPANGANAK NA MULI.'

🔑 ANG PANGUNAHING DAHILAN:

'Ang ipinanganak ng laman ay LAMAN' (v.6)

Ang problema ay hindi na ang laman ay MASAMA. Ang problema ay na ang laman ay LIMITADO:
• Hindi ito makalilikha ng espirituwal na buhay
• Hindi ito makakakita ng kaharian ng Diyos (v.3)
• Hindi ito makapapasok sa kaharian ng Diyos (v.5)

Kahit gaano mo pa itong turuan, pinuhin o disiplinahin ang laman - nananatili itong laman. Ito ay parang sinusubukang papalipasin ang isda sa pamamagitan ng mas mahirap na pagsasanay. Ang isda ay nangangailangan ng BAGONG KALIKASAN.

✨ ANG EBANGHELYO:

Hindi dumating ang Diyos upang pagbutihin ang iyong lumang sarili. Dumating Siya upang PATAYIN ito at bigyan ka ng bagong sarili. Hindi ito pagkukumpuni; ito ay PAGKABUHAY NA MAG-ULI."""

        card4['identity_statement'] = 'Kung ipinanganak ka na muli, hindi ka pinabuting bersyon ng iyong lumang sarili. Ikaw ay isang BAGONG NILIKHA. Ang lumang ikaw ay namatay kasama ni Cristo; ang bagong ikaw ay bumangon kasama Niya.'

        card4['revelation_key'] = 'Ang Kristiyanismo ay hindi espirituwal na pagpapabuti ng sarili. Ito ay kamatayan at pagkabuhay na mag-uli. Hindi \'maging mas mabuti\'; ito ay \'mamatay at tumanggap ng bagong buhay\'.'

        tl_data['cards'].append(card4)

        # Card 5: Discovery Activation
        card5 = en_data['cards'][4].copy()
        card5['title'] = 'Pansariling Pagtuklas'
        card5['discovery_questions'] = [
            {
                'category': 'Pagsusuri sa Sarili',
                'question': 'Nagtitiwala si Nicodemo sa kanyang relihiyon. Mayroon bang anumang bagay sa iyong buhay (moralidad, mabubuting gawa, kaalaman sa Bibliya) na pinagtitiwalaan mo ng HIGIT pa sa bagong kapanganakan?'
            },
            {
                'category': 'Patunay',
                'question': 'Sinabi ni Jesus na ang isang taong ipinanganak ng Espiritu ay parang hangin - hindi nakikita ngunit hindi maikakaila. Mayroon bang nakikitang patunay sa iyong buhay na ikaw ay binago ng Espiritu?'
            },
            {
                'category': 'Pagsuko',
                'question': 'Ang bagong kapanganakan ay PASSIVE voice - isang bagay na tinatanggap mo, hindi nakakamit. Sinusubukan mo bang \'ipanganak muli\' sa pamamagitan ng iyong pagsisikap, o sumusuko ka upang hayaang gawin ito ng Diyos sa iyo?'
            }
        ]

        card5['prayer']['title'] = 'Panalangin ng Bagong Kapanganakan'
        card5['prayer']['content'] = 'Ama sa Langit, kinikilala ko na ang aking relihiyon, moralidad at pagsisikap ay hindi sapat. Tulad ni Nicodemo, pumupunta ako sa Iyo sa aking kadiliman ng espiritu. Naniniwala ako na si Jesus ay namatay sa aking lugar at muling nabuhay. Ngayong araw ay tinatanggihan ko ang pagtitiwala sa aking laman - sa aking mga tagumpay, sa aking kabutihan, sa aking kaalaman. Banal na Espiritu, gawin Mo sa akin ang hindi ko magagawa para sa aking sarili: IPANGANAK MO AKONG MULI. Lumikha ng isang malinis na puso sa loob ko. Gawin Mo akong bagong nilikha. Nawa ang aking buhay ay maging hindi-maikakaila na patunay na ang Hangin ng Diyos ay humihip sa ibabaw ng aking patay na kaluluwa at nagbigay sa akin ng buhay na walang hanggan. Sa pangalan ni Jesus, Amen.'

        tl_data['cards'].append(card5)

        # Translate tags
        tl_data['tags'] = [
            'kaligtasan',
            'bagong_kapanganakan',
            'banal_na_espiritu',
            'pagbabagong_buhay',
            'nicodemo',
            'relihiyon_laban_sa_relasyon'
        ]

        # Translate metadata themes
        tl_data['metadata']['themes'] = [
            'Kakulangan ng relihiyon',
            'Bagong kapanganakan',
            'Soberanong gawa ng Espiritu',
            'Kamatayan at pagkabuhay na mag-uli'
        ]

    # Save Tagalog translation
    output_path = 'discovery/tl/born_again_tl_001.json'
    os.makedirs('discovery/tl', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tl_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Translation saved to {output_path}")
    return output_path

if __name__ == '__main__':
    translate_born_again()
