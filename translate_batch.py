#!/usr/bin/env python3
"""
Batch translation helper for Filipino Discovery Bible Studies
Completes cards 4-8 for full_hands_king and translates all cards for gold_silver_ashes and zechariah_14_return
"""

import json
import os
import sys
import subprocess
from pathlib import Path

# Setup paths
BASE_DIR = Path("/home/runner/work/devocionales-json/devocionales-json")
DISCOVERY_DIR = BASE_DIR / "discovery"
SCRIPTS_DIR = BASE_DIR / "devocionales_scripts"

def get_verse_text(reference, bible_version="MBB05"):
    """Get verse text using verse_resolver.py"""
    try:
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "verse_resolver.py"), reference, bible_version],
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Warning: Could not resolve {reference}: {result.stderr}")
            return f"[VERSE NOT FOUND: {reference}]"
    except Exception as e:
        print(f"Error resolving verse {reference}: {e}")
        return f"[ERROR: {reference}]"

def complete_full_hands_king():
    """Complete cards 4-8 for full_hands_king_fil"""
    print("\n=== COMPLETING FULL_HANDS_KING_FIL (Cards 4-8) ===\n")

    en_path = DISCOVERY_DIR / "en" / "full_hands_king_en_001.json"
    fil_path = DISCOVERY_DIR / "fil" / "full_hands_king_fil_001.json"

    with open(en_path, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    with open(fil_path, 'r', encoding='utf-8') as f:
        fil_data = json.load(f)

    # Cards 4-8 to translate
    cards_to_translate = [4, 5, 6, 7, 8]

    for card_num in cards_to_translate:
        print(f"\nTranslating card {card_num}...")
        en_card = en_data['cards'][card_num - 1]

        # Card 4: Crown Catalog
        if card_num == 4:
            fil_card = {
                "order": 4,
                "type": "crown_catalog",
                "icon": "👑",
                "title": "Ang Limang Korona ng Bagong Tipan",
                "subtitle": "Ang tiyak na gantimpala na ipinangako ng Diyos",
                "content": f"""Hindi nagsasalita ang Bibliya ng 'gantimpala' sa malinaw na paraan. Binabanggit nito ang tiyak na mga korona na ibibigay sa paghuhukom ni Cristo.

1️⃣ ANG KORONA NG KATUWIRAN (2 Timoteo 4:8):

{get_verse_text("2 Timoteo 4:8", "MBB05")}

• PARA KANINO: Sa mga umiibig at nananabik sa Kanyang pagdating
• PANGANGAILANGAN: Mabuhay na may pag-asa, tumitingin sa araw ng Kanyang pagbabalik
• SALOOBIN: 'Maranatha' (Halika, Panginoong Jesus) bilang isang pamumuhay

2️⃣ ANG KORONA NG BUHAY (Santiago 1:12 / Pahayag 2:10):

{get_verse_text("Santiago 1:12", "MBB05")}

• PARA KANINO: Sa mga lumalaban sa ilalim ng pagsubok at pag-uusig
• PANGANGAILANGAN: Katapatan sa gitna ng paghihirap
• PANGAKO: Para sa mga 'tapat hanggang sa kamatayan'

3️⃣ ANG KORONANG HINDI NASISIRA (1 Mga Taga-Corinto 9:25):

{get_verse_text("1 Mga Taga-Corinto 9:25", "MBB05")}

• PARA KANINO: Sa mga nagsasanay ng pagpipigil at disiplina
• PANGANGAILANGAN: Tumatakbo sa karera ng Kristiyano na may pagpipigil
• PAGKAKAIBA: Ang mga atleta ay nagsasanay para sa koronang nalalanta; tayo para sa walang hanggan

4️⃣ ANG KORONA NG KALUWALHATIAN (1 Pedro 5:4):

{get_verse_text("1 Pedro 5:4", "MBB05")}

• PARA KANINO: Mga pastor, anciano, pinuno na nag-aalaga sa kawan
• PANGANGAILANGAN: Pagpapastol hindi dahil sa pwersa o para sa yaman, kundi dahil sa pag-ibig
• BABALA: Hindi pag-hari sa pamana ng Diyos, kundi pagiging halimbawa

5️⃣ ANG KORONA NG KAGALAKAN (1 Mga Taga-Tesalonica 2:19):

{get_verse_text("1 Mga Taga-Tesalonica 2:19", "MBB05")}

• PARA KANINO: Sa mga nanalo ng mga kaluluwa at nagbahagi ng ebanghelyo
• PANGANGAILANGAN: Mamuhunan ang iyong buhay sa pagdadala ng iba kay Cristo
• WALANG HANGGAN: Ang mga tao lamang ang dadalhin natin sa langit

💎 ANG KAHALAGAHAN:

Ang mga koronang ito ay hindi para kolektahin tulad ng mga trophies. Ang mga ito ay upang magkaroon ng isang bagay na may halaga na ihagis sa paanan ng Hari kapag nakita natin Siya nang harapan (Pahayag 4:10).""",
                "revelation_key": "Napakabigay ng Diyos na hindi lamang Niya tayo sinasagip, kundi binibigyan din tayo ng maraming pagkakataon na makatanggap ng mga korona sa iba't ibang larangan ng buhay Kristiyano. Walang dahilan na dumating na may walang laman na mga kamay."
            }

        # Card 5: Worship Vision
        elif card_num == 5:
            fil_card = {
                "order": 5,
                "type": "worship_vision",
                "icon": "🙇",
                "title": "Paghahagis ng mga Korona: Ang Pinakamataas na Gawa ng Pagsamba",
                "subtitle": "Pahayag 4:10 - Kung bakit nais nating may punong-punong kamay",
                "content": f"""Ang pinakamagandang tanawin sa langit ay matatagpuan sa Pahayag 4:10-11. Ito ang sagot sa kung bakit mahalaga ang gantimpala:

{get_verse_text("Pahayag 4:10-11", "MBB05")}

👑 ANG KILOS:

Hindi PINAPANATILI ng mga anciano ang kanilang mga korona. INIHAHAGIS nila (bállō sa Griego: ihagis, itapon) ang mga ito sa paanan ng Kordero.

Bakit? Dahil sa sandaling iyon ng walang hanggang kalinawan, perpektong mauunawaan nila na:

• Ang korona ay napanalunan sa pamamagitan ng biyaya
• Ang katapatan ay naging posible sa pamamagitan ng Kanyang kapangyarihan
• Ang gawain ay sinimulan Niya at natapos Niya
• LAHAT ay mula sa Kanya, sa pamamagitan Niya, at para sa Kanya

💔 ANG TRAHEDYA NG WALANG LAMAN NA MGA KAMAY:

Ngayon nauunawaan natin kung bakit nakakalungkot na dumating na may walang laman na mga kamay. Hindi na hindi ka makakapasok sa langit (ligtas na ang kaligtasan sa pamamagitan ng biyaya), ngunit:

• Wala kang maaalok sa Kanya sa sandaling iyon
• Mawawalan ka ng pagkakataon na lumahok sa gawang pagsamba na iyon
• Malalaman mong nasayang mo ang mga pagkakataon para sa paglilingkod

Parang pagdating sa kasal na walang dalang regalo para sa bagong kasal. Imbitado ka, ngunit dumarating ka na may walang laman na mga kamay sa harap ng Pag-ibig ng iyong buhay.

🎁 ANG LAYUNIN NG GANTIMPALA:

Ang mga korona ay hindi upang palalakihin ang ating ego. Ang mga ito ay 'instrumento ng pagsamba.' Mas tapat tayo rito, mas malaki ang 'regalo' na mayroon tayo upang kilalanin ang Kanyang halaga roon.

Sabi ni Charles Spurgeon: 'Ang mga korona ay ibinibigay upang magkaroon tayo ng isang bagay na ihagis sa Kanyang mga paa, at sa gayon ay ipakita na minamahal natin Siya.'""",
                "scripture_connections": [
                    {
                        "reference": "Pahayag 4:10-11",
                        "text": get_verse_text("Pahayag 4:10-11", "MBB05")
                    },
                    {
                        "reference": "1 Mga Taga-Corinto 15:10",
                        "text": get_verse_text("1 Mga Taga-Corinto 15:10", "MBB05")
                    }
                ],
                "identity_statement": "Kung naligtas ka na sa pamamagitan ng biyaya, ang iyong tawag ngayon ay gumawa sa kapangyarihan ng Espiritu upang sa araw na iyon ay magkaroon ka ng mga korona na ihahagis sa Kanyang mga paa. Hindi tayo gumagawa upang MALIGTAS; gumagawa tayo dahil NALIGTAS na tayo at umiibig sa Hari.",
                "revelation_key": "Ang gantimpala ay hindi para sa atin; ito ay para sa Kanya. Ito ang huling pagkakataon na sabihing 'salamat' sa isang bagay na nahahawakan bago pumasok sa walang hanggan kung saan hindi na kailangan ng pananampalataya o gawa."
            }

        # Card 6: Contrast Analysis
        elif card_num == 6:
            fil_card = {
                "order": 6,
                "type": "contrast_analysis",
                "icon": "⚖️",
                "title": "Kaligtasan vs. Gantimpala: Ang Mahalagang Pagkakaiba",
                "subtitle": "Kung bakit ito ay biyaya AT gawa, hindi biyaya O gawa",
                "content": f"""Maraming Kristiyano ang nakalilito ng kaligtasan sa gantimpala. Ang pag-unawa sa pagkakaiba ay lubos na nagbabago ng kung paano tayo namumuhay.

📊 TALAHANAYAN NG PAGHAHAMBING:

═══════════════════════════════════════════════
KONSEPTO      │  KALIGTASAN     │  GANTIMPALA
═══════════════════════════════════════════════
PINAGMULAN    │  Gawa ni Cristo │  Gawa ng
              │  sa krus        │  mananampalataya
              │                 │  sa Espiritu
───────────────────────────────────────────────
PANGANGAILANGAN│ Pananampalataya│ Katapatan
              │  (Efeso 2:8-9)  │  (1 Cor 3:14)
───────────────────────────────────────────────
KALIKASAN     │  Ito ay REGALO  │  Ito ay PREMYO
              │  (handog)       │  (pagkilala)
───────────────────────────────────────────────
PAGKAKAIBA-IBA│ Pareho sa lahat │ Iba para sa
              │  (buhay na       │  bawat isa
              │  walang hanggan) │  (ayon sa gawa)
───────────────────────────────────────────────
BATAYAN       │  Ang ginawa ni  │  Ang ginawa MO
              │  Jesus (kamatayan)│ (paglilingkod)
───────────────────────────────────────────────
SALITANG      │  DORON          │  MISTHOS
GRIEGO        │  (regalo)       │  (sahod)
═══════════════════════════════════════════════

✅ KALIGTASAN:

• Tinatanggap sa isang sandali (kapag naniwala ka)
• Hindi maaaring mawala (Juan 10:28-29)
• Perpekto at agarang (hindi unti-unti)
• Walang 'mga antas' ng kaligtasan
• Ang lahat ng naligtas ay may buhay na walang hanggan

👑 GANTIMPALA:

• Binubuo araw-araw (sa iyong paglilingkod)
• Maaaring mawala (2 Juan 8)
• Progresibo (lumalaki sa bawat gawa)
• May 'mga antas' ng gantimpala
• Hindi lahat ng naligtas ay may parehong korona

⚠️ ANG PANGANIB:

Ang ilang Kristiyano ay nag-iisip: 'Dahil naligtas na ako, walang kahalagahan kung paano ako namumuhay.' MALI. Ang iyong kaligtasan ay hindi nasa panganib, ngunit ang iyong gantimpala ay nasa panganib.

Ang iba ay nag-iisip: 'Kung hindi nakakapagligtas ang mga gawa, bakit gagawin ko?' MALI. Ang mga gawa ay hindi nagdadala sa iyo SA langit, ngunit tinutukoy nila ang iyong karanasan SA langit.

🎯 ANG BALANSE NG BIBLIYA:

{get_verse_text("Mga Taga-Efeso 2:8-9", "MBB05")}

Ngunit sinasabi ng susunod na talata:

{get_verse_text("Mga Taga-Efeso 2:10", "MBB05")}

Ang kaligtasan ay sa pamamagitan ng pananampalataya nang walang gawa. Ngunit ang tunay na pananampalataya ay LAGING gumagawa ng mga gawa.""",
                "revelation_key": "Hindi tayo gumagawa upang kitain ang pagpasok sa langit; gumagawa tayo upang magkaroon ng isang bagay na ialay sa Hari kapag dumating tayo. Ang kaligtasan ay ang tiket; ang gantimpala ay kung ano ang tinutukoy mo na gagawin sa paglalakbay."
            }

        # Card 7: Necessity Emphasis
        elif card_num == 7:
            fil_card = {
                "order": 7,
                "type": "necessity_emphasis",
                "icon": "💎",
                "title": "Bakit Mahalaga na Magkaroon ng Punong-punong Kamay sa Araw na Iyon",
                "subtitle": "Ang tamang motibasyon para sa paglilingkod",
                "content": f"""Maaaring isipin ng iba: 'Hindi ba sapat na pumasok sa langit? Bakit mag-alala sa mga korona?'

May tatlong makapangyarihang dahilan:

1️⃣ DAHIL NAIS NIYA ITO:

Hindi sinasabi ni Jesus: 'Dumarating na ako.' Sinasabi Niya: 'Dumarating na ako, at ang aking GANTIMPALA ay kasama ko.'

NAIS Niyang gantimpalaan tayo. Nais Niyang parangalan tayo. Ito ang puso ng Ama na nananabik na magdiwang sa Kanyang tapat na mga anak.

Tulad sa talinghaga ng mga talento (Mateo 25:21): {get_verse_text("Mateo 25:21", "MBB05")}

Ang pagtanggi sa gantimpala dahil sa huwad na pagpapakumbaba ay pagtanggi sa Kanyang pagnanais na parangalan ka.

2️⃣ DAHIL ITO AY GAWA NG PAG-IBIG:

Isipin mo ito: Binigay Niya ang LAHAT para sa iyo sa krus. Ibinuhos Niya ang Kanyang dugo, tiniis ang impiyerno na karapat-dapat mo, namatay sa iyong lugar.

Ang pagdating na may punong-punong kamay ay paraan ng pagsasabi: 'Panginoon, nais ko ring bigyan Ka ng isang bagay. Hindi kita maililigtas, hindi kita matutubos, ngunit kinuha ko ang binigay Mo sa akin at pinarami ko ito para sa Iyo.'

Parang asawang nagsusumikap na magdala ng regalo sa kanyang asawa sa kanilang anibersaryo. Hindi dahil sa obligasyon; dahil sa pag-ibig.

3️⃣ DAHIL ITO AY NAKAKAAPEKTO SA IYONG WALANG HANGGAN:

Bagaman ang lahat ng naligtas ay magiging nasa langit, hindi lahat ay magkakaroon ng parehong kakayahan para sa kagalakan o parehong responsibilidad sa walang hanggang kaharian.

Nagsasalita si Jesus tungkol sa 'pagiging tagapangasiwa ng maraming bagay' (Mateo 25:21). Nagsasalita si Pablo tungkol sa ilan na 'magdurusa ng pagkawala' bagaman sila mismo ay naligtas (1 Mga Taga-Corinto 3:15).

Nagtuturo ang Bibliya na sa walang hanggan ay magkakaroon ng:

• Iba't ibang antas ng awtoridad (Lucas 19:17-19)
• Iba't ibang kakayahan para sa kagalakan (batay sa pagkakatulad kay Cristo na nilinang dito)
• Iba't ibang karangalan (ngunit walang inggit, dahil walang kasalanan sa langit)

💡 ANG TAMANG MOTIBASYON:

Hindi tayo naglilingkod dahil sa takot (ligtas na ang kaligtasan).
Hindi tayo naglilingkod dahil sa kasakiman (ang mga korona ay para sa Kanya).
Naglilingkod tayo dahil sa PAG-IBIG at PASASALAMAT.

Sabi ni Jim Elliot: 'Hindi siya mangmang na nagbibigay ng hindi niya mapapanatili upang makuha ang hindi niya mawawala.'""",
                "scripture_connections": [
                    {
                        "reference": "2 Juan 1:8",
                        "text": get_verse_text("2 Juan 1:8", "MBB05")
                    },
                    {
                        "reference": "1 Mga Taga-Corinto 3:14",
                        "text": get_verse_text("1 Mga Taga-Corinto 3:14", "MBB05")
                    },
                    {
                        "reference": "Mga Hebreo 11:6",
                        "text": get_verse_text("Mga Hebreo 11:6", "MBB05")
                    }
                ],
                "identity_statement": "Ikaw ay isang katiwala, hindi may-ari. Lahat ng mayroon ka (oras, kaloob, yaman, pagkakataon) ay ipinagkatiwala sa iyo upang paramihin. Sa araw na makita mo si Jesus, nais mong may ipakita sa Kanya: 'Panginoon, binigyan Mo ako ng 5 talento, at kumita ako ng 5 pa.'",
                "revelation_key": "Ang punong-punong kamay ay hindi opsyonal; ang mga ito ay natural na bunga ng pusong nagpapasalamat. Kung tunay mong nauunawaan ang ginawa Niya para sa iyo, hindi ka makapaghihiwalay sa paggawa para sa Kanya."
            }

        # Card 8: Discovery Activation
        elif card_num == 8:
            fil_card = {
                "order": 8,
                "type": "discovery_activation",
                "icon": "🙏",
                "title": "Personal na Pagtuklas: Paghahanda ng mga Kamay",
                "discovery_questions": [
                    {
                        "category": "Pagtatasa sa sarili",
                        "question": "Kung darating si Jesus ngayon, anong mga korona ang maaari mong ihagis sa Kanyang mga paa? O darating ka ba na may walang laman na mga kamay?"
                    },
                    {
                        "category": "Motibasyon",
                        "question": "Ano ang pinaka-nag-uudyok sa iyo sa iyong paglilingkod sa Diyos: takot na mawalan ng isang bagay, pagnanais na makakuha ng isang bagay, o malalim na pag-ibig sa Kanya? Maging tapat."
                    },
                    {
                        "category": "Pangangasiwa",
                        "question": "Sa mga 'talento' na ibinigay sa iyo ng Diyos (oras, kaloob, yaman, impluwensya), alin ang 'inilibing' mo at alin ang pinarami mo?"
                    },
                    {
                        "category": "Mga priyoridad",
                        "question": "Isipin ang sandali ng pagharap kay Jesus. Ano ang nais mong masabi sa Kanya tungkol sa kung paano ka namuhay? Namumuhay ka ba ngayon sa paraang hindi ka mahihiya sa araw na iyon, kundi magkakaroon ng kagalakan?"
                    }
                ],
                "prayer": {
                    "title": "Panalangin: Panginoon, Nais Kong May Punong-punong Kamay Para sa Iyo",
                    "content": f"""Amang nasa langit, Ikaw na siyang Alpha at Omega, ang Simula at ang Wakas, lumapit ako sa Iyo na may pusong nagpapasalamat ngunit may kamalayan din.

Salamat na ang aking kaligtasan ay hindi nakadepende sa aking mga gawa, kundi sa perpektong gawa ni Cristo sa krus. Ang siguradong iyon ay aking pundasyon.

Ngunit Panginoon, ngayong araw ay ginising ng Banal na Espiritu sa akin ang isang bagong pagnanais: ayaw kong tumayo sa harap Mo na may walang laman na mga kamay. Hindi dahil natatakot akong mawala ang aking kaligtasan, kundi dahil mahal kita at nais kong magkaroon ng isang bagay na ialay sa Iyo sa araw na iyon.

Binigyan Mo ako ng napakarami: oras, kaloob, pagkakataon, yaman, impluwensya. Ipinahayag ko na maraming beses ay inilibing ko ang mga talentong iyon dahil sa takot, katamaran, o kaabalahan sa mga bagay na walang halaga na walang hanggan.

Ngayong araw ay pumipili ako na maging tapat na katiwala. Tulungan mo ako na:

• Mabuhay na may pag-asa sa Iyong pagdating (upang manalo ng korona ng katuwiran)
• Lumaban sa mga pagsubok na may kagalakan (upang manalo ng korona ng buhay)
• Magsanay ng pagpipigil sa aking espiritwal na karera (upang manalo ng koronang hindi nasisira)
• Manguna sa iba na may pag-ibig kung nilagay Mo ako sa pamumuno (upang manalo ng korona ng kaluwalhatian)
• Ibahagi ang ebanghelyo at manalo ng mga kaluluwa (upang manalo ng korona ng kagalakan)

Nawa ang bawat araw ng aking buhay ay isang pamumuhunan sa walang hanggan. Na kapag dumating Ka na may Iyong gantimpala, marinig ko: 'Mahusay, mabuti at tapat na alipin.'

At sa araw na iyon, na may mga luhang pasasalamat, ihahagis ko ang aking mga korona sa Iyong mga paa at sasabihin: 'Panginoon, lahat ay dahil sa Iyong biyaya. Lahat ay Iyong kapangyarihang gumagawa sa akin. Lahat ay Iyo.'

Nawa ang aking buhay ay hindi maging walang kabuluhan. Nawa ang mga gawang ginagawa ko ay ginto, pilak, at mahalagang mga bato na nakakaligtas sa apoy ng Iyong presensya.

Sa pangalan ni Jesus, ang Alpha at Omega, Amen."""
                },
                "action_steps": [
                    {
                        "title": "Kilalanin ang Iyong Korona",
                        "description": "Sa 5 koronang nabanggit, pumili ng ISA na tutukan ngayong linggo. Halimbawa: kung pipiliin mo ang korona ng kagalakan, mangako na magbahagi ng ebanghelyo sa kahit isang tao."
                    },
                    {
                        "title": "Suriin ang Iyong mga Talento",
                        "description": "Gumawa ng listahan ng mga yaman na ibinigay sa iyo ng Diyos (oras, pera, kakayahan, relasyon). Itanong sa sarili: Pinaparami ko ba ito para sa Kanyang kaharian o mayroon itong 'inilibing'?"
                    },
                    {
                        "title": "Mabuhay na May Banal na Urgency",
                        "description": "Sinasabi ni Jesus na 'Dumarating na ako' ng tatlong beses. Tuwing umaga, kapag gumising ka, sabihin: 'Panginoon, kung ngayon ang araw na Ikaw ay darating, nais kong Ikaw ay makahanap sa akin na gumagawa para sa Iyo.' Hayaan ang pag-iisip na iyon na gabayan ang iyong mga desisyon."
                    }
                ]
            }

        fil_data['cards'].append(fil_card)

    # Save updated file
    with open(fil_path, 'w', encoding='utf-8') as f:
        json.dump(fil_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Completed full_hands_king_fil_001.json (cards 4-8 added)")

if __name__ == "__main__":
    complete_full_hands_king()
