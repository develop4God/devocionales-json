#!/usr/bin/env python3
"""
Translate jesus_troubled_himself from English to Tagalog
Uses VerseResolver for all scripture lookups
"""

import json
import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'devocionales_scripts'))
from verse_resolver import VerseResolver

def translate_jesus_troubled_himself():
    # Load English source
    with open('discovery/en/jesus_troubled_himself_en_001.json', 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Create Tagalog version
    tl_data = {
        "id": en_data["id"],
        "type": en_data["type"],
        "date": en_data["date"],
        "title": "Kinabag Niya ang Kanyang Sarili",
        "subtitle": "Nang piliin ni Jesus na pumasok sa ating sakit",
        "language": "tl",
        "version": "ADB",
        "estimated_reading_minutes": 8,
        "key_verse": {},
        "scripture_passage": {},
        "cards": [],
        "tags": [
            "banal_na_pakikiramay",
            "pagkatao_ni_jesus",
            "kaaliwan",
            "lazaro",
            "tarasso",
            "juan_11",
            "sakit_at_pag_asa"
        ],
        "metadata": {
            "total_word_count": en_data["metadata"]["total_word_count"],
            "greek_words_count": en_data["metadata"]["greek_words_count"],
            "scripture_references_count": en_data["metadata"]["scripture_references_count"],
            "difficulty_level": en_data["metadata"]["difficulty_level"],
            "themes": [
                "Ang kusang pakikiramay ni Jesus",
                "Pumapasok ang Diyos sa ating sakit",
                "Banal na galit laban sa kamatayan",
                "Kaaliwan na ipinanganak mula sa karanasan"
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

        # Translate scripture_passage verses
        passage_verses = []
        for verse in en_data['scripture_passage']['verses']:
            verse_num = verse['number']
            verse_ref = f"John 11:{verse_num}"
            v_cita, v_texto, v_error = resolver.resolve(verse_ref)
            if v_error:
                print(f"Error resolving {verse_ref}: {v_error}")
                sys.exit(1)
            passage_verses.append({
                "number": verse_num,
                "text": v_texto
            })

        # Get passage reference
        passage_ref = en_data['scripture_passage']['reference']
        p_cita, _, p_error = resolver.resolve(passage_ref)
        if not p_error:
            tl_data['scripture_passage'] = {
                'reference': p_cita,
                'verses': passage_verses
            }

        # Card 1: Opening Mystery
        card1 = {
            "order": 1,
            "type": "opening_mystery",
            "icon": "😢",
            "title": "Ang Tanong na Walang Nagtatanung",
            "subtitle": "Bakit umiyak si Jesus kung alam Niya ang wakas?",
            "content": """Ito ay isa sa pinakasikat na tagpo sa Bibliya: 'Umiyak si Jesus' (Juan 11:35), ang pinakamaikling talata sa Kasulatan.

Ngunit may kakaiba dito na hindi napapansin ng karamihan:

❓ ANG PARADOX:

ALAM ni Jesus na sa loob lamang ng mas mababa sa 10 minuto, mabubuhay si Lazaro. Sinabi pa Niya kanina: 'Ang sakit na ito ay hindi sa kamatayan, kundi sa ikaluluwalhati ng Dios' (t.4).

Kaya bakit umiyak?

🤔 ANG MAAARI SANANG GINAWA NI JESUS:

Maaari sana lamang dumating si Jesus at sabihin:
• 'Huwag kayong umiyak, bubuhaying Ko siya'
• 'Panoorin ninyo na Ako ang Mesias'
• 'Sa loob ng 5 minuto magiging ayos ang lahat'

Ngunit hindi Niya ginawa.

💔 ANG TALAGANG NANGYARI:

Sa halip na tumalon agad sa himala, si Jesus ay:
1. NAKITA ang sakit ni Maria at ng mga Hudyong umiiyak
2. LUBHANG NAANTIG (dalawang beses - t.33 at t.38)
3. UMIYAK kasama nila
4. SAKA LAMANG gumawa ng himala

✨ ANG PAHAYAG:

Ipinakita ng Banal na Espiritu ang katotohanang ito sa isang tao: 'Sa natural na larangan, kung saan nakita ni Jesus ang mga taong umiiyak, maaari Niya lamang sabihin na huwag umiyak, bubuhaying Ko siya, huwag mag-alala, at hindi na umiyak. Ngunit naantig Siya at ngayon nauunawaan ko nang higit pa kaysa sa aking pinaniniwalaan.'

May KAPANGYARIHAN si Jesus na lutasin ang problema, ngunit PINILI Niya na MARAMDAMAN muna ang sakit.

Ito ang banal na pagkatao ni Jesus.""",
            "revelation_key": "Hindi lamang inaayos ni Jesus ang iyong mga problema sa isang pagpindot ng Kanyang mga daliri. Umuupo Siya sa iyo sa putik ng iyong pighati BAGO Niya isagawa ang himala."
        }

        tl_data['cards'].append(card1)

        # Card 2: Greek Exegesis - Tarassō
        card2 = {
            "order": 2,
            "type": "greek_exegesis",
            "icon": "🌊",
            "title": "Tarassō: Parang Pagkalog ng Tubig",
            "subtitle": "Ang salitang nagbabago ng lahat",
            "content": """Sa Juan 11:33, marahil nagsasabi ang iyong Bibliya na 'ay nabagabag' o 'lubhang naantig.' Ngunit sa orihinal na Griego, ang salita ay mas malakas pa:

📖 TARASSŌ (Strong G5015: ταράσσω)

Literal na kahulugan:
• Pag-UGOY nang mapusok
• Pag-KALOG sa kalmadong tubig hanggang maging malabo
• Pag-YANIG tulad ng bagyo na umugoy sa dagat

🌊 ANG LARAWAN:

Isipin mo ang isang lawa ng malinis na tubig, sa perpektong kalma. Biglang may nag-lagay ng patpat at pinagalaw nang mapusok. Ang tubig ay naging maugoy, malabo, nawala ang kapayapaan.

IYAN ang tarassō.

⚡ ANG NAKAKAGULAT NA BAHAGI:

Ang tekstong Griego ay nagsasabi: ἐτάραξεν ἑαυτόν (etaraxen heauton)

Literal na salin: 'KINABAG NIYA ANG KANYANG SARILI'

• Etaraxen = ACTIVE na pandiwa (Ginawa Niya ang aksyon)
• Heauton = REFLEXIVE na panghalip (sa Kanyang Sarili)

🎯 ANG MAHALAGANG PAGKAKAIBA:

Sa atin, ang pagkabagabag ay PASSIVE:
• Ang mga pangyayari ang kumabag SA ATIN
• Ang sakit ang umuugoy SA ATIN
• Ang balita ang gumugulong SA ATIN

Wala tayong kontrol dito.

Ngunit kay Jesus, ang pagkabagabag ay ACTIVE:
• PINILI Niyang kabagan ang Kanyang Sarili
• NAGPASYA Siyang ugayin ang Kanyang sariling kaluluwa
• KUSANG binuksan Niya ang mga kompwerta ng Kanyang puso

💡 BAKIT MAHALAGA ITO:

Si Jesus ay ang Prinsipe ng Kapayapaan. Ang Kanyang kaluluwa ay nasa perpektong kalma. ALAM Niya na mabubuhay si Lazaro.

Ngunit nang makita Niya si Maria at ang mga Hudyong umiiyak, NAGPASYA Siyang hayaang maging 'maugoy' ang Kanyang loob tulad ng dagat sa bagyo.

Bakit? Upang PUMASOK sa kanilang sakit. Hindi upang manatiling malayong tagamasid, kundi upang ilubog ang Sarili sa pagdurusa ng tao.""",
            "greek_words": [
                {
                    "word": "Tarassō",
                    "transliteration": "ταράσσω",
                    "strong": "G5015",
                    "meaning": "Pag-ugoy, pagkabag, paggambala nang mapusok",
                    "revelation": "Hindi 'biktima' si Jesus ng emosyon na lumampas sa Kanya. PINILI Niya na ugayin ang Kanyang sariling kaluluwa upang malapit sa iyong pakiramdam."
                },
                {
                    "word": "Heauton",
                    "transliteration": "ἑαυτόν",
                    "strong": "G1438",
                    "meaning": "Ang Kanyang Sarili (reflexive)",
                    "revelation": "Hindi ito nangyari KAY Jesus. Ginawa itong mangyari ni Jesus sa Kanya. Ito ay isang saserdoteng kilos ng kusang pakikiramay."
                }
            ],
            "revelation_key": "Nagpasya si Jesus na maging emosyonalng mahina. Ang Makapangyarihang Diyos ay pumili na 'mawalan ng Kanyang kalma' upang malapit sa iyo sa iyong kaguluhan."
        }

        tl_data['cards'].append(card2)

        # Card 3: Theological Depth - Embrimaomai
        john12_cita, john12_texto, john12_error = resolver.resolve("John 12:27")
        john13_cita, john13_texto, john13_error = resolver.resolve("John 13:21")

        if john12_error or john13_error:
            print(f"Error resolving scripture connections")
            sys.exit(1)

        card3 = {
            "order": 3,
            "type": "theological_depth",
            "icon": "💪",
            "title": "Embrimaomai: Ang Banal na Galit",
            "subtitle": "Hindi lamang malungkot si Jesus, Siya ay GALIT",
            "content": """May IBA PANG salita sa Juan 11:33 na marahil isinalin ng iyong Bibliya nang mahinahon. Sinasabi nito na si Jesus ay 'naghingal sa espiritu.'

Ngunit sa Griego ito ay mas matalas pa:

🔥 EMBRIMAOMAI (Strong G1690: ἐμβριμάομαι)

Orihinal na kahulugan:
• Ang PAG-UNGAL ng kabayong pandigma bago ang labanan
• Ang PAG-ANGIL na may pagkagalit
• Ang pakiramdam ng PIGILIN na galit

⚔️ ANG LARAWAN:

Isipin mo ang isang mandirigma sa larangan ng digmaan, humihingal nang mabigat, mga kalamnan ay nakatense, nag-uungal ng galit bago sumalakay sa kaaway.

IYAN ang naramdaman ni Jesus.

❓ NGUNIT LABAN KANINO?

Hindi Siya galit kay Maria, o kay Marta, o sa mga Hudyo.

GALIT Siya laban sa:
• KAMATAYAN na sumira sa Kanyang mga kaibigan
• KASALANAN na nagdala ng sumpang ito sa mundo
• ANG KAAWAY na dumating upang magnakaw, pumatay, at sumira

💔 ANG KONEKSYON SA TARASSŌ:

Nakaranas si Jesus ng DALAWANG sabay na emosyon:

1️⃣ TARASSŌ (pagkabagabag) = Pakikiramay sa sakit ng tao
2️⃣ EMBRIMAOMAI (galit) = Pagkagalit laban sa kamatayan

🎯 ANG KAHULUGAN NITO:

Kapag ikaw ay nasa iyong pinakamadilim na sandali:
• UMIYAK si Jesus kasama mo (pakikiramay)
• GALIT si Jesus para sa iyo (katarungan)

Hindi Niya tinitingnan ang iyong sakit na may klinikong kawalan ng malasakit. NAANTIG Siya sa Kanyang kaibuturan at NAG-UUNGAL ng galit laban sa sumusira sa iyo.

⚡ ANG HIMALA PAGKATAPOS NG GALIT:

Pagkatapos kabagan ang Sarili at magalit, si Jesus ay:
• Lumalakad sa libingan (t.38)
• Nag-utos na alisin ang bato (t.39)
• SUMIGAW may awtoridad: 'LAZARO, LUMABAS KA!' (t.43)

Hindi ito isang magalang na bulong. Ito ay ang UNGAL ng Mandirigma na sumasalakay sa teritoryo ng kamatayan upang agawin ang isang biktima.""",
            "scripture_connections": [
                {
                    "reference": john12_cita,
                    "text": john12_texto
                },
                {
                    "reference": john13_cita,
                    "text": john13_texto
                }
            ],
            "revelation_key": "Hindi malayong Diyos si Jesus na tumitingin sa iyong sakit na may pilosopikong kalma. Siya ay NAG-UUNGAL ng galit laban sa sumasakit sa iyo at UMAATAKE para sa iyo."
        }

        tl_data['cards'].append(card3)

        # Card 4: Comfort Promise
        card4 = {
            "order": 4,
            "type": "comfort_promise",
            "icon": "🕊️",
            "title": "Juan 14:1 - Ang Pangako Pagkatapos ng Sakit",
            "subtitle": "Bakit maaaring sabihin sa iyo ni Jesus na 'Huwag magulang puso ninyo'",
            "content": """Narito ang pinakamagandang koneksyon:

Pagkatapos KABAGAN ni Jesus ang SARILI sa Juan 11, 12, at 13 para sa atin, mayroon Siyang AWTORIDAD na sabihin sa atin sa Juan 14:

💎 JUAN 14:1:
'Huwag magulang (tarassesthō) ang inyong puso: kayo'y nagsisisampalataya sa Dios, magsampalataya naman kayo sa akin.'

Napansin mo ba? Ito ay ang PAREHONG SALITA: tarassō.

🔑 ANG BANAL NA LOHIKA:

1️⃣ KINABAG ni Jesus ang SARILI (Juan 11:33) = Inubos Niya ang pagkabagabag para sa iyo
2️⃣ Ininom ni Jesus ang buong kopa ng sakit (Gethsemane, Krus)
3️⃣ Ngayon maaari Niyang UTUSan ka na huwag magulang

☕ ANG ANALOHIYA:

Para bang may kopang mapait na dapat inumin ng isang tao. Sinabi ni Jesus:
'Iinumin Ko ang BUONG kopa. Bawat patak ng pighati, bawat alon ng kaguluhan, bawat sandali ng paghihirap. At kapag natapos Ko, HINDI mo na kailangang inumin ito.'

✨ KAYA NASASABI NIYA:
'Huwag magulang puso ninyo' - dahil KINABAG na Niya ang Sarili sa iyong lugar.

🎁 ANG BINIBIGAY NITO SA IYO NGAYON:

Kapag ang iyong kaluluwa ay maugoy tulad ng tubig sa bagyo:
• Hindi ito dahil hindi nauunawaan ng Diyos (KINABAG Niya ang SARILI)
• Hindi ito dahil nag-iisa ka (PUMASOK Siya sa iyong kaguluhan)
• Hindi ito dahil walang daan palabas (ININOM Niya ang buong kopa)

💪 ANG AWTORIDAD NG KANYANG KAALIWAN:

Maaaring aliwin ka ni Jesus dahil mayroon Siyang mga 'peklat' ng parehong pagkabagabag sa Kanyang sariling espiritu. Hindi Siya nagsasalita sa iyo bilang estranghero na hindi kailanman naghirap. Nagsasalita Siya bilang Isang:
• Pumili na kabagan ang Sarili
• Nakakaalam kung ano ang pakiramdam
• Nag-pinalampas ng pagkabagabag
• At ngayon nag-aalok sa iyo ng Kanyang kapayapaan

🕊️ HEBREO 4:15:
'Sapagka't mayroon tayong dakilang saserdote na hindi hindi masasalang sa pakikiramay sa ating mga kahinaan; kundi napagsubok sa lahat ng mga bagay na gaya natin.'

Hindi 'nakalimutan' ni Jesus kung ano ang pakiramdam ng pagkabagabag. Pinigil Niya ang Kanyang pagkatao upang kapag nakikipag-usap ka sa Kanya tungkol sa iyong sakit, hindi ka nakikipag-usap sa isang estranghero.""",
            "identity_statement": "Ang iyong pagkabagabag ay hindi nakakagulat kay Jesus, dahil pumili Siyang kabagan ang Sarili BAGO ka. Ang iyong kaguluhan ay hindi nagtutulak sa Kanya palayo, dahil KINABAG Niya ang SARILI upang malapit sa iyo.",
            "revelation_key": "Maaaring hilingin sa iyo ni Jesus na huwag magulang puso dahil inubos na Niya ang lahat ng pagkabagabag para sa iyo. Ininom Niya ang kopa upang makainom ka ng Kanyang kapayapaan."
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
                    "category": "Katapatan",
                    "question": "Naisip mo ba na hindi nauunawaan ni Jesus ang iyong sakit dahil Siya ay Diyos at 'laging alam kung paano magtatapos ang kuwento'? Paano nagbabago ang mga bagay na malaman na PUMILI Siya na ugayin ang Kanyang kaluluwa upang pumasok sa iyong kaguluhan?"
                },
                {
                    "category": "Pananaw sa Sakit",
                    "question": "Kapag ikaw ay nasa iyong pinakamadilim na sandali, nakikita mo ba si Jesus bilang isang taong gustong 'ayusin ang problema nang mabilis,' o bilang isang taong umuupo muna sa iyo sa putik bago gawin ang himala?"
                },
                {
                    "category": "Galit ng Diyos",
                    "question": "Alam mo ba na GALIT si Jesus (embrimaomai) laban sa sumusira sa iyo? Paano nagbabago ang iyong pananaw na malaman na hindi Niya tinitingnan ang iyong sakit na may kawalan ng malasakit, kundi NAG-UUNGAL ng galit para sa iyo?"
                },
                {
                    "category": "Pagsuko",
                    "question": "Sinasabi ni Jesus na 'Huwag magulang puso ninyo' PAGKATAPOS kabagan ang Sarili para sa iyo. Handa ka bang ibigay sa Kanya ang iyong kaguluhan, na alam na dinala na Niya ito para sa iyo?"
                }
            ],
            "prayer": {
                "title": "Panalangin ng Pagsuko",
                "content": "Jesus, ngayong araw ay natutuklasan ko ang bagong bagay tungkol sa Iyo: na Hindi Ka malayong Diyos na tumitingin sa aking sakit mula sa malayo. PUMILI Kang kabagan ang Sarili, NAGPASYA Kang ugayin ang Iyong sariling kaluluwa, naging GALIT laban sa kamatayan na nag-babanta sa akin.\n\nSalamat na hindi Mo ako hihingin na maging mapayapa mula sa lugar ng langit na kaaliwan, kundi mula sa lugar ng Isang ININOM ang kopa ng pagkabagabag para sa akin.\n\nNgayong araw ay ibinibigay ko sa Iyo ang aking maugoy na tubig, ang aking kaluluwa sa bagyo, ang aking magulong puso. Alam Mo kung ano ang pakiramdam. Pumasok Ka rito nang kusang-loob.\n\nKung paanong sumigaw Ka kay Lazaro na 'LUMABAS KA!', sumigaw sa ibabaw ng aking sitwasyon. Mag-ungal ng galit laban sa sumusira sa akin. At bigyan Mo ako ng Iyong kapayapaan, ang kapayapaang tanging Ikaw lamang ang makakabigay dahil inubos Mo na ang pagkabagabag para sa akin.\n\nSa pangalan ng Umuiyak para sa akin, na naantig para sa akin, na umungal para sa akin: Jesus. Amen."
            }
        }

        tl_data['cards'].append(card5)

    # Save Tagalog translation
    output_path = 'discovery/tl/jesus_troubled_himself_tl_001.json'
    os.makedirs('discovery/tl', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tl_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Translation saved to {output_path}")
    return output_path

if __name__ == '__main__':
    translate_jesus_troubled_himself()
