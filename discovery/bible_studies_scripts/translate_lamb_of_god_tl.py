#!/usr/bin/env python3
"""
Translate lamb_of_god_en_001.json to Tagalog
Uses VerseResolver with ADB_tl.SQLite3 for verse lookups
"""

import json
import sys
import os

# Add devocionales_scripts to path for verse_resolver
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'devocionales_scripts'))
from verse_resolver import VerseResolver

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'bible_database', 'ADB_tl.SQLite3')

# Read English source
EN_PATH = os.path.join(os.path.dirname(__file__), '..', 'en', 'lamb_of_god_en_001.json')
with open(EN_PATH, 'r', encoding='utf-8') as f:
    en_data = json.load(f)

# Initialize Tagalog translation
tl_data = en_data.copy()

# Update basic fields
tl_data['language'] = 'tl'
tl_data['version'] = 'Ang Dating Biblia'
tl_data['estimated_reading_minutes'] = 6  # 5-7 range, using 6 for TL

# Resolve verses using VerseResolver
with VerseResolver(DB_PATH) as resolver:
    # Key verse: John 1:29
    cita, texto, error = resolver.resolve("John 1:29")
    if error:
        print(f"ERROR resolving John 1:29: {error}")
        sys.exit(1)

    key_verse_ref = cita
    key_verse_text = texto

    # 2 Corinthians 5:21
    cita2, texto2, error2 = resolver.resolve("2 Corinthians 5:21")
    if error2:
        print(f"ERROR resolving 2 Corinthians 5:21: {error2}")
        sys.exit(1)

    scripture_anchor_ref = cita2
    scripture_anchor_text = texto2

print(f"Key verse reference (TL): {key_verse_ref}")
print(f"Key verse text (TL): {key_verse_text}")
print(f"\nScripture anchor reference (TL): {scripture_anchor_ref}")
print(f"Scripture anchor text (TL): {scripture_anchor_text}")

# Now translate the content
tl_data['title'] = 'Ang Kordero ng Diyos'
tl_data['subtitle'] = 'Ang katuparan ng 1,500 taon ng sistema ng handog sa isang pahayag'

# Update key verse
tl_data['key_verse']['reference'] = key_verse_ref
tl_data['key_verse']['text'] = key_verse_text

# Card 1: Historical Context
tl_data['cards'][0]['title'] = 'Ang Sistemang Alam ng Lahat'
tl_data['cards'][0]['subtitle'] = 'Nang magsalita si Juan, agad na naunawaan ng bawat Hudyo'
tl_data['cards'][0]['content'] = '''Isipin ang Ilog Jordan noong araw na iyon. Si Juan Bautista, ang pinakasikat na propeta ng Israel, ay itinuro ang isang di kilalang karpintero at sinabi: "Narito ang Kordero ng Diyos."

Para sa mga tagapakinig na Hudyo, ang pariralang ito ay nag-activate ng 1,500 taon ng kolektibong alaala:

• Bawat umaga at gabi, may mga korderong inihahain sa Templo sa Jerusalem (Exodo 29:38-39). Dalawang kordero bawat araw × 365 araw × 1,500 taon = mahigit 1 milyong kordero.

• Sa bawat Paskuwa, bawat pamilyang Hudyo ay naghahain ng sariling kordero. Ang dugo sa mga haligi ng pintuan ang nakapagligtas sa Israel mula sa kamatayan sa Ehipto.

• Sa Araw ng Pagtubos (Yom Kippur), ang punong saserdote ay pumapasok sa Banal ng mga Banal na may dalang dugo ng kordero upang tubusin ang mga kasalanan ng buong bansa.

Nang sabihin ni Juan na "ang Kordero ng Diyos," hindi ito magandang metapora lamang. Ipinahahayag niya: "Ito ang Huling Kordero. Ang siyang tinutukoy ng lahat ng ibang mga kordero."'''

tl_data['cards'][0]['revelation_key'] = 'Ang sistema ng handog ay hindi ang pinal na plano. Ito ay isang anino na nagtuturo kay Cristo.'

# Card 2: Greek Exegesis
tl_data['cards'][1]['title'] = 'Ang Salitang Nagbabago ng Lahat: AIRŌN'
tl_data['cards'][1]['subtitle'] = 'Hindi lamang takip sa kasalanan, kundi INAALIS ITO'

tl_data['cards'][1]['greek_words'][0]['meaning'] = 'Itaas, pasanin sa mga balikat, dalhin papalayo nang lubos'
tl_data['cards'][1]['greek_words'][0]['revelation'] = '''Ang pandiwang ito ay napakahalaga. Hindi nagsasabi ng 'takpan' (kalyptō) o 'patawarin' (aphiēmi). Nagsasabi ng AIRŌN - itaas, pasanin, at DALHIN PAPALAYO.

Ito ang parehong salitang ginamit nang "kunin" ng mga alagad ang mga basket ng natirang tinapay, o nang "buhatin" ng mga sundalo ang krus upang dalhin ito.

Hindi tinakpan lamang ni Hesus ang iyong kasalanan upang hindi ito makita ng Diyos. Binuhat Niya ito mula sa iyong mga balikat, pinasan sa Kanyang sarili, nilakad Niya ito patungo sa Golgota, at inilibing sa Kanyang libingan. Nang Siya ay magbangon, ang iyong kasalanan ay hindi sumama sa Kanya. WALA NA ITO.'''

tl_data['cards'][1]['greek_words'][0]['application'] = 'Ang iyong pagkakasala, kahihiyan, nakaraan - hindi lamang pinatawad ni Cristo. INALIS Niya ito. Wala na ito sa iyo.'

tl_data['cards'][1]['greek_words'][1]['meaning'] = 'Batang kordero, malambot, walang depekto'
tl_data['cards'][1]['greek_words'][1]['revelation'] = '''Maaaring gumamit si Juan ng 'probaton' (matandang tupa) o 'arnion' (maliit na kordero). Ginamit niya ang AMNOS - ang perpektong isang taong gulang na kordero, walang dungis, na ginagamit sa pinakasagradong mga handog.

Direktang nauugnay ang salitang ito kay Isaias 53:7: "Siya ay dinadala bilang kordero sa katayan." Hindi pagkakataon. Ipinahahayag ni Juan: "Ito ang Nagdurusa na Lingkod na nakita ni Isaias 700 taon na ang nakalipas."'''

tl_data['cards'][1]['greek_words'][1]['application'] = 'Hindi sapat ang kahit anong handog. Tanging ang perpektong Kordero ng Diyos ang makakalis sa iyong kasalanan nang lubos.'

tl_data['cards'][1]['revelation_key'] = 'Ang pagkakaiba ng relihiyon at ebanghelyo: ang relihiyon ay tumakip ng kasalanan pansamantala; si Cristo ay NAG-ALIS nito nang permanente.'

# Card 3: Prophetic Thread
tl_data['cards'][2]['title'] = 'Ang Pulang Sinulid: Mula Genesis Hanggang Juan'
tl_data['cards'][2]['subtitle'] = 'Paano nagtuturo ang bawat kordero patungo sa sandaling ito'

tl_data['cards'][2]['timeline'][0]['description'] = 'Naghandog ang Diyos ng mga hayop upang takpan ang kahubaran nina Adan at Eba'
tl_data['cards'][2]['timeline'][0]['revelation'] = 'Ang unang pagbuhos ng dugo. Ipinapakita ng Diyos na kung walang dugo, walang takip para sa kasalanan.'

tl_data['cards'][2]['timeline'][1]['description'] = 'Sinabi ni Abraham kay Isaac: "Magbibigay ang Diyos ng kordero"'
tl_data['cards'][2]['timeline'][1]['revelation'] = 'Sa Bundok ng Moria (ang parehong lugar kung saan itatayo ang Templo), hinulaan ni Abraham na magbibigay ang Diyos ng Kanyang sariling kordero. Hindi hinahanap ni Abraham na magbigay; ang Diyos ang magbibigay ng Kanyang sarili.'

tl_data['cards'][2]['timeline'][2]['description'] = 'Ang Paskuwa: Isang kordero bawat pamilya, walang depekto, dugo sa mga haligi ng pintuan'
tl_data['cards'][2]['timeline'][2]['revelation'] = 'Ang dugo ng kordero ang dahilan kung bakit "lumampas" ang kamatayan. Naligtas ang Israel hindi dahil sa kanilang kabutihan, kundi dahil sa dugo.'

tl_data['cards'][2]['timeline'][3]['description'] = 'Ang Nagdurusa na Lingkod "ay dinadala bilang kordero sa katayan"'
tl_data['cards'][2]['timeline'][3]['revelation'] = '700 taon bago si Cristo, nakita ni Isaias ang Kordero na kusang pinasan ang ating mga kasalanan, na hindi bumuka ang bibig.'

tl_data['cards'][2]['timeline'][4]['description'] = 'Itinuro ni Juan: "Narito ANG Kordero ng Diyos"'
tl_data['cards'][2]['timeline'][4]['revelation'] = 'Hindi sinabi niya "isang kordero." Sinabi niya "ANG Kordero." Ang tiyak na isa. Ang siyang tinutukoy ng lahat ng mga anino.'

tl_data['cards'][2]['revelation_key'] = 'Ang bawat kordero sa Lumang Tipan ay isang kabanata sa kuwentong nagtatapos sa Juan 1:29. Si Cristo ang sagot na isinusulat ng Diyos sa loob ng 1,500 taon.'

# Card 4: Theological Depth
tl_data['cards'][3]['title'] = 'Ang Banal na Palitan'
tl_data['cards'][3]['subtitle'] = 'Ang kinuha ni Cristo at ang ibinigay Niya sa iyo kapalit'

tl_data['cards'][3]['content'] = '''Sa sistema ng Lumang Tipan, ang kordero ay namatay SA LUGAR ng tao. Ito ay kapalit. Ngunit ginawa ni Cristo ang mas malalim:

🔄 ANG DAKILANG PALITAN:

• Ang iyong kasalanan → sa Kanya (2 Corinto 5:21)
• Ang Kanyang katuwiran → sa iyo

• Ang iyong kamatayan → Siya ang namatay (Roma 6:23)
• Ang Kanyang buhay → ikaw ang namumuhay (Galacia 2:20)

• Ang iyong pagkakasala → dinala Niya ito (Isaias 53:6)
• Ang Kanyang kawalang-sala → tumatakip sa iyo

• Ang iyong paghihiwalay sa Diyos → naranasan Niya ito sa krus ("Diyos ko, bakit mo ako pinabayaan?")
• Ang Kanyang pakikipag-isa sa Ama → ngayon ay sa iyo ("Abba, Ama")

Ito ay hindi patas na palitan. Ito ang pinaka-hindi pantay na palitan sa kasaysayan: kinuha Niya ang iyong pinakamasama at ibinigay Niya sa iyo ang Kanyang pinakamabuti.'''

tl_data['cards'][3]['scripture_anchor']['reference'] = scripture_anchor_ref
tl_data['cards'][3]['scripture_anchor']['text'] = scripture_anchor_text

tl_data['cards'][3]['revelation_key'] = 'Hindi ka sumusubok na maabot ang Diyos. Natapos na ni Cristo ang paglalakbay at dinala ka Niya kasama Niya.'

# Card 5: Discovery Activation
tl_data['cards'][4]['title'] = 'Pansariling Pagtuklas'

tl_data['cards'][4]['discovery_questions'][0]['category'] = 'Kalayaan'
tl_data['cards'][4]['discovery_questions'][0]['question'] = 'Anong kasalanan, pagkakasala, o kahihiyan ang dinadala mo pa rin sa iyong buhay na INALIS NA (airōn) ni Cristo 2,000 taon na ang nakalipas?'

tl_data['cards'][4]['discovery_questions'][1]['category'] = 'Pagkakakilanlan'
tl_data['cards'][4]['discovery_questions'][1]['question'] = 'Sa banal na palitan, kinuha ni Cristo ang iyong kamatayan at ibinigay Niya sa iyo ang Kanyang buhay. Namumuhay ka ba bilang isang taong namatay, o bilang isang taong may buhay ni Cristo?'

tl_data['cards'][4]['discovery_questions'][2]['category'] = 'Pasasalamat'
tl_data['cards'][4]['discovery_questions'][2]['question'] = '1 milyong kordero ang inihain sa Templo sa buong panahon. Lahat ay nagturo kay Hesus. Paano binabago ng pagkaalam na Siya ang Huling Kordero ang iyong pagsamba ngayon?'

tl_data['cards'][4]['prayer']['title'] = 'Panalangin ng Pag-aktibo'
tl_data['cards'][4]['prayer']['content'] = '''Hesus, aking perpektong Kordero. Ngayong araw ay tinatanggap ko sa pamamagitan ng pananampalataya ang ipinahayag ni Juan: INALIS MO ang aking kasalanan. Hindi mo ito tinakpan, hindi mo ito binawasan - binuhat mo ito, pinasan mo ito, at dinala mo ito papalayo. Ngayong araw ay pipiliin kong tumigil sa pagdadala ng dati mo nang dinadala para sa akin. Salamat sa hindi pantay na palitan: kinuha Mo ang aking kamatayan at ibinigay Mo sa akin ang Iyong buhay. Nawa ang aking buhay ay maging tugon ng pasasalamat para sa Kordero na pinatay mula nang itatag ang mundo. Sa ngalan ni Hesus, Amen.'''

# Tags
tl_data['tags'] = [
    'handog',
    'pagtubos',
    'kordero',
    'pagbabayad-sala',
    'palitan',
    'kalayaan',
    'paskuwa'
]

# Metadata themes
tl_data['metadata']['themes'] = [
    'Sistema ng handog',
    'Kahalili sa pagbabayad ng sala',
    'Natupad na propesiya',
    'Banal na palitan'
]

# Write output
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'tl', 'lamb_of_god_tl_001.json')
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(tl_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ Translation complete: {OUTPUT_PATH}")
