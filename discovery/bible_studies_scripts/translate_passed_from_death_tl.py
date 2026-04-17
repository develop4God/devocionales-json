#!/usr/bin/env python3
"""
Translate passed_from_death from English to Tagalog
"""
import json
import sys
import os

# Add parent directory to path for verse_resolver import
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

# Paths
DB_PATH = '/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3'
EN_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/en/passed_from_death_en_001.json'
TL_FILE = '/home/runner/work/devocionales-json/devocionales-json/discovery/tl/passed_from_death_tl_001.json'

# Load English source
with open(EN_FILE, 'r', encoding='utf-8') as f:
    en_data = json.load(f)

# Initialize resolver
resolver = VerseResolver(DB_PATH)

# Resolve key verse
print("Resolving key verse...")
key_ref = en_data['key_verse']['reference']
cita, texto, error = resolver.resolve(key_ref)
if error:
    print(f"ERROR resolving {key_ref}: {error}")
    sys.exit(1)
print(f"✓ {key_ref} → {cita}")

# Resolve scripture connections in card 3
print("\nResolving scripture connections...")
refs_to_resolve = [
    "John 10:28-29",
    "Romans 8:38-39",
    "Philippians 1:6",
    "2 Timothy 2:13"
]

resolved_scriptures = []
for ref in refs_to_resolve:
    c, t, e = resolver.resolve(ref)
    if e:
        print(f"ERROR resolving {ref}: {e}")
        sys.exit(1)
    print(f"✓ {ref} → {c}")
    resolved_scriptures.append({'reference': c, 'text': t})

resolver.close()

print("\n" + "="*60)
print("ALL VERSES RESOLVED SUCCESSFULLY")
print("="*60)
print(f"\nKey verse ({cita}):")
print(f"  {texto}")
print(f"\nScripture connections:")
for s in resolved_scriptures:
    print(f"  {s['reference']}: {s['text'][:60]}...")

# Now create the Tagalog translation
tl_data = {
    "id": "passed_from_death_001",
    "type": "discovery",
    "date": "2026-01-21",
    "title": "Lumipat Mula sa Kamatayan Tungo sa Buhay",
    "subtitle": "Ang huling pahayag: hindi ka na maaaring 'hindi ipinanganak'",
    "language": "tl",
    "version": "ADB",
    "estimated_reading_minutes": 10,
    "key_verse": {
        "reference": cita,
        "text": texto
    },
    "cards": [
        {
            "order": 1,
            "type": "character_context",
            "icon": "🔄",
            "title": "Ang Sandali ng Pahayag",
            "subtitle": "Pagsasama ng lahat ng nakaraang pag-aaral",
            "content": "Naglakbay tayo sa isang malalim na paglalakbay mula sa Gethsemane hanggang sa mga bukas na libingan:\n\n1️⃣ GETHSEMANE: Pinagpawisan ng dugo ni Jesus sa ilalim ng presyon ng kopa\n2️⃣ ANG HAPUNAN: Itinatag Niya ang Bagong Tipan bilang Tagapagmana\n3️⃣ ANG KRUS: Ininom Niya ang kopa ng poot at pinabayaan\n4️⃣ ANG TABING: Napunit ito mula itaas hanggang ibaba - bukas na ang access\n5️⃣ ANG MGA LIBINGAN: Nabuksan - ang mga banal ay binuhay\n\n🔑 ANG HULING TANONG:\n\nMaaari bang MAWALA ang kaligtasan ng isang taong 'ipinanganak na muli'?\n\n💡 ANG PAHAYAG MULA SA MGA MULING NABUHAY NA BANAL:\n\nNang makita natin na HINDI binuhay ng Diyos sina Abraham, David at Isaias para 'mawala' pagkatapos, ang Banal na Espiritu ay naghayag ng isang malalim na katotohanan:\n\n'Hindi sila binuhay ng Diyos upang subukan silang muli. Binuhay Niya sila dahil ang kanilang kaligtasan ay natatak na. Kung maaari silang mawala, hindi sana mamumuhunan ang Diyos ng Kanyang kapangyarihan ng pagkabuhay sa kanila.'\n\n✨ ANG KONEKSYON:\n\nKung ang PISIKAL na pagkabuhay ay hindi na maibabalik...\nHindi rin ba maaaring maibalik ang ESPIRITUWAL na pagkabuhay?\n\n📖 JUAN 5:24:\n\n'Ang nakikinig... ay LUMIPAT NA mula sa kamatayan tungo sa buhay.'\n\nAng susing salita dito ay METABEBĒKEN (Strong G3327).",
            "revelation_key": "Nang ipanganak ka na muli, naging 'muling nabuhay na banal' ka ngayon. Hindi ka na nasa libingan ng kasalanan. Ikaw ay LUMIPAT NA. Hindi na maibabalik."
        },
        {
            "order": 2,
            "type": "greek_exegesis",
            "icon": "📖",
            "title": "Metabebēken: Ang Perpektong Panahunan ng Kaligtasan",
            "subtitle": "Kung bakit ito ay permanenteng legal na paglipat",
            "content": "Juan 5:24 - 'LUMIPAT NA (metabebēken) mula sa kamatayan tungo sa buhay.'\n\n🔍 PAGSUSURI NG METABEBĒKEN (Strong G3327):\n\n• META = Pagbabago ng lugar, paglilipat\n• BEBĒKEN = Pandiwang 'baino' (lumakad, maglakad)\n• Panahunan: PERPEKTO\n\n📚 ANG PERPEKTONG PANAHUNAN SA GRIEGO:\n\nIto ay ang PINAKAMAKAPANGYARIHANG panahunan ng pandiwa sa Griego:\n• Aksyon na naganap sa NAKARAAN\n• Ang mga epekto ay NANANATILI sa kasalukuyan\n• At patuloy tungo sa HINAHARAP\n\nHindi ito 'lumalipat' (kasalukuyang tuluy-tuloy).\nHindi ito 'lilipat' (hinaharap).\nIto ay 'LUMIPAT NA at ang mga epekto ay permanente.'\n\n🚚 ANG LARAWAN NG PAGLIPAT:\n\nIsipin mo na nakatira ka sa 'Kaharian ng Kamatayan':\n• Pagkamamamayan: makasalanan\n• Hari: si Satanas\n• Tadhana: walang-hanggang paghihiwalay\n\nNang ipanganak ka na muli, hindi mo pinabuti ang iyong kalagayan sa kahariang iyon.\nNAGLIPAT ka sa ibang kaharian:\n\nColosas 1:13 - 'Sapagka't tayo'y iniligtas niya sa kapangyarihan ng kadiliman, at inilipat sa kaharian ng Anak ng kaniyang pag-ibig.'\n\n• Bagong pagkamamamayan: banal\n• Bagong Hari: si Cristo\n• Bagong tadhana: buhay na walang hanggan\n\n⚖️ ITO AY LEGAL NA PAGLIPAT:\n\nHindi ito nakadepende sa:\n✗ Iyong pang-araw-araw na emosyon\n✗ Iyong espirituwal na pagganap\n✗ Iyong mga pag-taas at pagbaba\n\nNakadepende ito sa:\n✓ Ang kamatayan ng Tagapagmana (pinagpahayag ang testamento)\n✓ Ang iyong pananampalataya kay Cristo (ginawa kang tagapagmana)\n✓ Ang tatak ng Banal na Espiritu (garantiya)\n\n🔒 EFESO 1:13-14:\n\n'At kayo'y tinakan sa kaniya ng TATAK, ang Espiritu Santong ipinangako, na siyang TIYAK ng ating mana.'\n\nTIYAK (arrabon - G728):\n• Paunang bayad na NAGSISIGURO ng buong bayad\n• Tulad ng deposito sa bahay\n• May bisa sa batas\n\nKung ibinigay ng Diyos ang Espiritu bilang 'paunang bayad,' sa tingin mo ba ay hindi Niya tatapusin ang transaksyon?",
            "greek_words": [
                {
                    "word": "Metabebēken",
                    "transliteration": "μεταβέβηκεν",
                    "meaning": "Lumipat na, naglipat na (perpektong panahunan)",
                    "revelation": "Hindi ito patuloy na proseso. Ito ay natupad na katotohanan. Ikaw ay LUMIPAT NA. Ang iyong legal na posisyon ay nagbago nang permanente sa sandali ng paniniwala."
                },
                {
                    "word": "Arrabon",
                    "transliteration": "ἀρραβών",
                    "meaning": "Garantiya, paunang bayad, pangako",
                    "revelation": "Ang Banal na Espiritu sa iyo ay 'lagda' ng Diyos na tatapusin Niya ang sinimulan Niya. Hindi ito pautang; ito ay legal na pangako."
                },
                {
                    "word": "Sphragizō",
                    "transliteration": "σφραγίζω",
                    "meaning": "Magtatak, markahan ng opisyal na tatak",
                    "revelation": "Sa sinaunang mundo, ang tatak ng hari ay hindi masisira. Tinakan ka ng Espiritu. Walang makakabasag ng takip na iyon maliban sa Diyos, at hindi Niya gagawin."
                }
            ],
            "revelation_key": "Ang Metabebēken ay perpektong panahunan: Ikaw ay LUMIPAT NA. Hindi ka 'sinusubukang lumipat.' Hindi ka 'lilipat kung magsusumikap ka.' Ikaw ay LUMIPAT NA. Permanente."
        },
        {
            "order": 3,
            "type": "theological_depth",
            "icon": "👶",
            "title": "Hindi Ka Maaaring Hindi Ipinanganak",
            "subtitle": "Kung bakit ang bagong pagsilang ay hindi na maibabalik",
            "content": "Juan 3:3 - 'Katotohanan, katotohanang sinasabi ko sa iyo, Maliban na ang tao'y ipanganak na maguli ay hindi niya makikita ang kaharian ng Dios.'\n\n👶 ANG LOHIKA NG PAGSILANG:\n\nMaaari bang 'hindi ipinanganak' ang isang sanggol?\n\nMaaari nilang:\n✓ Magkasakit\n✓ Sumuway\n✓ Lumayo sa kanilang mga magulang\n✓ Maghimagsik laban sa kanilang pamilya\n\nNgunit HINDI nila maaaring:\n✗ Mawala ang kanilang DNA\n✗ Ihinto ang pagiging anak\n✗ 'Hindi ipinanganak' mula sa kanilang pamilya\n\n🧬 ANG NABAGONG KALIKASAN:\n\n2 Corinto 5:17 - 'Kaya nga kung ang sinoman ay kay Cristo, siya'y BAGONG NILALANG: ang mga dating bagay ay nangagdaan na; narito, ang lahat ng mga bagay ay naging bago.'\n\nKAINĒ KTISIS (Bagong Nilikha):\n• Hindi 'pinabuti'\n• Hindi 'pinalitan'\n• BAGO - isang bagay na hindi umiiral noon\n\n📊 ANG PAGKAKAIBA:\n\nRELIHIYON:\n• Sinusubukang PAGBUTIHIN ang lumang kalikasan\n• Tulad ng pagpipinta ng kabaong na may kulay\n• Ang kamatayan ay nananatiling nasa loob\n\nEBANGHELYO:\n• PINATAY ng Diyos ang lumang kalikasan\n• Binibigyan ka ng BAGONG kalikasan\n• 'Ako'y ipinako na kay Cristo' (Gal 2:20)\n\n🔑 ROMA 8:9-10:\n\n'Nguni't kayo'y wala sa laman, kundi sa Espiritu, kung gayon ang Espiritu ng Dios ay TUMATAHAN sa inyo. Nguni't kung ang sinoman ay walang Espiritu ni Cristo, ang taong ito ay hindi sa kaniya.'\n\nAng patunay ng kaligtasan:\n• HINDI ang iyong moral na kasakdalan\n• HINDI ang iyong kaalaman sa Bibliya\n• ANG presensya ng Banal na Espiritu sa iyo\n\nKung ang Espiritu ay TUMATAHAN (oikeō - permanenteng naninirahan) sa iyo, pag-aari ka ni Cristo.\n\n⚠️ ANG BABALA:\n\n1 Juan 2:19 - 'Sila'y nagsilabas sa atin, datapuwa't hindi nangasa atin; sapagka't kung sila'y nangasa atin, ay nangakatitirang kasama natin: datapuwa't sila'y nagsilabas, upang mangahayag na sila'y hindi lahat nangasa atin.'\n\nAng taong 'nawalan' ng kanyang kaligtasan ay hindi kailanman nagkaroon nito.\nAng taong 'ipinanganak na muli' ay hindi maaaring hindi ipinanganak.",
            "scripture_connections": resolved_scriptures,
            "revelation_key": "Ang kaligtasan ay hindi nakadepende sa iyong kakayahang hawakan ang Diyos. Nakadepende ito sa kakayahan ng Diyos na hawakan ka. At hindi Siya bumitaw."
        },
        {
            "order": 4,
            "type": "necessity_emphasis",
            "icon": "🛡️",
            "title": "Paano ang Sinasadyang Kasalanan?",
            "subtitle": "Pagkilala sa pagitan ng disiplina at kondemnasyon",
            "content": "🤔 ANG KARANIWANG PAGTUTOL:\n\n'Ngunit sinasabi ng Hebreo 10:26: Sapagka't kung tayo'y magkasalang may kusang-loob pagkatapos na ating matanggap ang pagkakilala ng katotohanan, ay hindi na naiiwan ang anomang hain dahil sa mga kasalanan.'\n\nNagsasalungat ba ito sa walang-hanggang seguridad?\n\n📖 ANG KONTEKSTO NG HEBREO 10:\n\nAng may-akda ay nagsasalita tungkol sa mga taong:\n• Nakakilala sa ebanghelyo nang intelektuwal\n• Ngunit malay na TUMANGGING tanggapin si Cristo\n• Bumalik sa sistemang sakripisyo ng Lumang Tipan\n• Hindi kailanman nakaranas ng bagong pagsilang\n\nHindi ito tungkol sa isang mananampalataya na nagkasala.\nIto ay tungkol sa isang tao na hindi talaga naniwala.\n\n🔑 ANG PAGKAKAIBA:\n\nANAK NA NAGKAKASALA:\n✓ Nakakaranas ng pagsisisi mula sa Banal na Espiritu\n✓ Nagdurusa ng disiplinang parang ama (Heb 12:6)\n✓ Sa huli ay naipanumbalik\n✓ Hindi nawawala ang kanilang posisyon bilang anak\n\nESTRANGHERO NA NAGPAPANGGAP:\n✗ Walang panloob na pagsisisi\n✗ Unti-unting tumitibay ang kanilang puso\n✗ Sa huli ay iniiwanan ang propesyon ng pananampalataya\n✗ Pinatutunayan na hindi sila kailanman naging anak (1 Juan 2:19)\n\n⚖️ DISIPLINA vs. KONDEMNASYON:\n\nRoma 8:1 - 'Kaya nga ngayon ay walang ANOMANG KAHATULAN sa kanila na nasa kay Cristo Jesus.'\n\nHebreo 12:6 - 'Sapagka't ang sinomang iniibigin ng Panginoon ay kanyang SINASAWAY.'\n\n• KONDEMNASYON = Huling legal na parusa (impiyerno)\n• DISIPLINA = Pansamantalang mahabagin na pagwawasto (pagpapanumbalik)\n\nKung ikaw ay anak, hindi ka kailanman makakaranas ng kondemnasyon.\nNgunit MAKAKARANAS ka ng disiplina kapag nagkasala ka.\n\n🎯 1 JUAN 3:9:\n\n'Ang bawat ipinanganak sa Dios ay hindi NAGKAKASALA NG TULUY-TULOY, sapagka't ang kaniyang binhi ay nananatili sa kaniya; at hindi siya makagagawa ng kasalanan, sapagka't siya'y ipinanganak sa Dios.'\n\n• 'NAGKAKASALA NG TULUY-TULOY' (poieō) = gawin nang tuluy-tuloy bilang pamumuhay\n• Hindi sinasabing hindi ka kailanman mahuhulog\n• Sinasabing hindi ka maaaring MAMUHAY nang komportable sa kasalanan\n\nAng tunay na anak ay maaaring mahulog, ngunit HINDI maaaring manatiling nakabagsak nang walang pagsisisi.",
            "identity_statement": "Ang walang-hanggang seguridad ay hindi lisensya upang magkasala. Ito ang pundasyon para sa tunay na pagiging banal. Hindi ka sumusunod dahil sa takot na mawala ang kaligtasan, kundi dahil sa pasasalamat na natanggap mo ito.",
            "revelation_key": "Kung maaari kang magkasalang sadya nang walang anumang pagsisisi o pagkabalisa, ang tanong ay hindi 'maaari ko bang mawala ang aking kaligtasan?' kundi 'ipinanganak ba ako na muli kailanman?'"
        },
        {
            "order": 5,
            "type": "discovery_activation",
            "icon": "🙏",
            "title": "Pansariling Pagtuklas",
            "discovery_questions": [
                {
                    "category": "Katiyakan ng kaligtasan",
                    "question": "Namumuhay ka ba na may katiyakan na 'LUMIPAT ka NA mula sa kamatayan tungo sa buhay' (perpektong panahunan), o may kawalan ng katiyakan na 'sinusubukan mong lumipat' (kasalukuyang tuluy-tuloy)?"
                },
                {
                    "category": "Batayan ng pagsunod",
                    "question": "Sumusunod ka ba sa Diyos dahil sa TAKOT na mawala ang iyong kaligtasan, o dahil sa PASASALAMAT dahil ang iyong kaligtasan ay ligtas? Ano ang iyong tunay na motibrasyon?"
                },
                {
                    "category": "Ebidensya ng bagong pagsilang",
                    "question": "May ebidensya ba ng Banal na Espiritu na tumatahan sa iyo? Nakakaranas ka ba ng pagsisisi kapag nagkakasala ka? O maaari kang mamuhay sa kasalanan nang walang kabalisa?"
                },
                {
                    "category": "Pagtitiwala sa Diyos",
                    "question": "Kung ang iyong kaligtasan ay nakadepende sa iyong kakayahang 'hawakan' ang Diyos, gaano katagal ka makakatagal? Ngunit kung nakadepende ito sa Diyos na humahawak sa iyo, paano binabago nito ang iyong kumpiyansa?"
                }
            ],
            "prayer": {
                "title": "Panalangin ng Katiyakan",
                "content": "Ama sa Langit, ngayong araw ay nauunawaan ko nang malinaw na ang aking kaligtasan ay hindi mahinang proseso. Ito ay NATUPAD NA KATOTOHANAN. Ako ay LUMIPAT NA (metabebēken - perpektong panahunan) mula sa kamatayan tungo sa buhay. Hindi ako 'sinusubukang lumipat.' Hindi ako 'lilipat kung ako ay kikilos nang mabuti.' Ako ay LUMIPAT NA. Tulad ng mga banal na lumabas mula sa kanilang mga libingan sa Mateo 27, lumabas ako mula sa aking 'espirituwal na libingan' nang bigyan Mo ako ng buhay. At kung paanong hindi Mo sila binuhay upang mawala sila, hindi Mo ako iniligtas upang mawala ako. Patawarin Mo ang aking kawalan ng pananampalataya kapag namumuhay ako sa takot na 'mawala' ang tinakan Mo na ng Banal na Espiritu. Tulungan Mo akong sumunod hindi dahil sa takot ng kondemnasyon, kundi dahil sa pasasalamat ng pag-ampon. Hindi ako empleyado na nasa probisyon. Ako ay ANAK na may garantisadong mana. Hindi ako maaaring 'hindi ipinanganak.' Salamat sa Iyong hindi mababasag na katapatan. Sa pangalan ni Jesus, Amen."
            }
        }
    ],
    "tags": [
        "walang_hanggang_seguridad",
        "bagong_pagsilang",
        "perpektong_panahunan",
        "tinakan_ng_espiritu",
        "juan_5_24",
        "disiplina_vs_kondemnasyon"
    ],
    "metadata": {
        "total_word_count": 1650,
        "greek_words_count": 3,
        "scripture_references_count": 16,
        "difficulty_level": "intermediate-advanced",
        "themes": [
            "Hindi na maibabalik ang bagong pagsilang",
            "Seguridad na nakabatay sa katapatan ng Diyos",
            "Pagkakaiba sa pagitan ng disiplina at kondemnasyon",
            "Perpektong panahunan ng kaligtasan"
        ]
    }
}

# Save Tagalog file
os.makedirs(os.path.dirname(TL_FILE), exist_ok=True)
with open(TL_FILE, 'w', encoding='utf-8') as f:
    json.dump(tl_data, f, ensure_ascii=False, indent=2)

print(f"\n✓ Tagalog translation saved to: {TL_FILE}")
