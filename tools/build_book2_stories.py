#!/usr/bin/env python3
"""Build RoLang's bilingual story collection from 4000 Essential English Words, Book 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from story_catalog import category_for, publish_collection


BOOK_TITLE = "4000 Essential English Words - Book 2"
COLLECTION_ID = "4000-essential-english-words-book-2"
XHTML_NS = "{http://www.w3.org/1999/xhtml}"
OPF_NS = "{http://www.idpf.org/2007/opf}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes())


def localized(indonesian: Any, filipino: Any) -> dict[str, Any]:
    return {"id": indonesian, "fil": filipino}


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def slugify(value: str) -> str:
    value = value.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def title_for(unit_title: str) -> str:
    return re.sub(r"^Unit\s+\d+\s*", "", unit_title, flags=re.IGNORECASE).strip()


def image_info(data: bytes) -> tuple[str, str, int, int]:
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("Expected a JPEG illustration")
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        length = int.from_bytes(data[offset : offset + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            return "image/jpeg", ".jpg", width, height
        offset += length
    raise ValueError("Could not read JPEG dimensions")


EXPECTED_TITLES = [
    "The twelve months", "The dragon", "The battle of Thermopylae", "The deer and his image",
    "May 29,1953", "The frog prince", "A beautiful bird", "Tricky turtle", "The tale of bartelby O’Boyle",
    "Blackbeard", "Dinosaur drawings", "The mean chef", "The cat and the fox", "The good student",
    "The lucky knife", "Prince Sam", "Henry ford’s famous car", "The priest", "Mrs. May and the green girl",
    "Albert Einstein", "From the earth to the stars", "The farm festival", "The clever thief",
    "The doctor’s cure", "The criminal", "The two captains", "The Duke and the Minister",
    "The fisherman", "Osiris and the Nile", "The taxi driver",
]


STORIES: list[dict[str, Any]] = [
    {
        "category": "Kebaikan dan keserakahan",
        "summary": ("Anna menemukan bunga untuk saudara tirinya dengan bantuan dua belas bulan; keserakahan ibu tiri dan saudara tirinya membuat mereka tersesat.", "Tinulungan ng labindalawang buwan si Anna na humanap ng bulaklak para sa kaniyang kapatid sa ama; naligaw naman ang sakim na madrasta at anak nito."),
        "characters": ["Anna", "her stepmother", "her stepsister", "the twelve months"],
        "setting": "A snowy landscape and Anna's home, during January and the changing months.",
        "theme": ("Kindness is rewarded, while greed can lead people astray.", "kabaitan at kasakiman", "kabaitan at kasakiman"),
        "events": ["Anna's stepmother sends her into the January snow to find flowers for the stepsister.", "Anna meets the twelve months, who move time forward from January through February to spring in March.", "Flowers bloom, and Anna returns with a full basket and tells what happened.", "The stepmother and stepsister seek the months for gifts, become lost, and Anna lives happily on her own."],
        "sentences": [
            ("Sa gitna ng taglamig, pinatira ng malupit na madrasta si Anna at ang kaniyang anak sa iisang bahay, ngunit si Anna lamang ang pinagtatrabaho.", "Pada musim dingin, seorang ibu tiri yang kejam tinggal serumah dengan Anna dan putrinya, tetapi hanya Anna yang disuruh bekerja."),
            ("Isang gabing napakalamig, inutusan niya si Anna na humanap ng mga bulaklak para sa anak niyang may gusto nito.", "Pada suatu malam yang sangat dingin, ia menyuruh Anna mencari bunga untuk putrinya yang menginginkannya."),
            ("Naglakad si Anna sa niyebe hanggang makatagpo niya ang labindalawang lalaki, na nagpaliwanag na sila ang labindalawang buwan.", "Anna berjalan menembus salju sampai bertemu dua belas lelaki yang menjelaskan bahwa mereka adalah dua belas bulan."),
            ("Sa tulong nila, mabilis na lumipas ang Enero at Pebrero, at pinainit ni Marso ang araw hanggang mamulaklak ang parang.", "Dengan bantuan mereka, Januari dan Februari berlalu cepat, lalu Maret menghangatkan matahari sampai bunga-bunga bermekaran di padang."),
            ("Pinuno ni Anna ng bulaklak ang kaniyang basket, nagpasalamat, at ikinuwento sa bahay ang kabutihan ng mga buwan.", "Anna memenuhi keranjangnya dengan bunga, berterima kasih, lalu menceritakan kebaikan para bulan di rumah."),
            ("Nang humingi rin ng regalo ang madrasta at anak nito, naligaw sila sa paghahanap; namuhay namang masaya si Anna nang mag-isa.", "Ketika ibu tiri dan putrinya juga mencari hadiah, mereka tersesat; Anna pun hidup bahagia seorang diri."),
        ],
        "vocabulary": [("madrasta", "ibu tiri", "pangngalan"), ("niyebe", "salju", "pangngalan"), ("labindalawang buwan", "dua belas bulan", "parirala"), ("lumipas", "berlalu", "pandiwa"), ("parang", "padang", "pangngalan"), ("naligaw", "tersesat", "pandiwa")],
        "expressions": [("Sa tulong nila", "Dengan bantuan mereka"), ("namuhay nang masaya", "hidup dengan bahagia")],
        "grammar": ("Ginagamit ang nang + pandiwa upang ilarawan kung paano ginawa ang isang kilos; ipinakikilala ng hanggang ang hangganan ng pagbabago.", "Nang + kata kerja menerangkan cara suatu tindakan dilakukan; hanggang menunjukkan batas perubahan."),
        "questions": [
            (("Sino ang inutusan ng madrasta na humanap ng bulaklak?", "Siapa yang disuruh ibu tiri mencari bunga?"), [("Ang sariling anak niya", "Putrinya sendiri"), ("Si Anna", "Anna"), ("Isa sa mga buwan", "Salah satu bulan")], 1, ("Si Anna ang pinapunta sa niyebe upang maghanap ng bulaklak.", "Anna yang disuruh pergi ke tengah salju untuk mencari bunga.")),
            (("Anong pagbabago ang ginawa ng mga buwan para kay Anna?", "Perubahan apa yang dilakukan para bulan untuk Anna?"), [("Pinabilis nila ang pagdating ng tagsibol", "Mereka mempercepat datangnya musim semi"), ("Ginawa nilang gabi ang umaga", "Mereka mengubah pagi menjadi malam"), ("Itinago nila ang mga bulaklak", "Mereka menyembunyikan bunga")], 0, ("Pinaikot nila ang mga buwan hanggang dumating ang Marso at mamulaklak ang parang.", "Mereka mempercepat pergantian bulan sampai Maret tiba dan bunga bermekaran.")),
            (("Ano ang nangyari sa madrasta at anak niya?", "Apa yang terjadi pada ibu tiri dan putrinya?"), [("Nakauwi sila agad", "Mereka segera pulang"), ("Nakakita sila ng mas maraming bulaklak", "Mereka menemukan lebih banyak bunga"), ("Naligaw sila habang naghahanap ng regalo", "Mereka tersesat saat mencari hadiah")], 2, ("Naghahanap sila ng mga buwan para humingi ng regalo ngunit hindi na nakauwi.", "Mereka mencari para bulan untuk meminta hadiah, tetapi tidak pernah menemukan jalan pulang.")),
        ],
    },
    {
        "category": "Pakikipagsapalaran at katapangan", "summary": ("Tinalo ng isang batang lalaki ang dragon na nananakot sa kaniyang bayan matapos gumawa ng tabak mula sa meteor sa tulong ng isang pantas.", "Seorang anak lelaki mengalahkan naga yang meneror kotanya setelah membuat pedang dari meteor dengan bantuan seorang tetua bijaksana."),
        "characters": ["the dragon", "the boy", "the wise old man", "the townspeople"], "setting": "A town beneath remote southern mountains, a temple, and the dragon's castle.",
        "theme": ("Courage joined with wise preparation can defeat a powerful threat.", "katapangan at paghahanda", "tapang at paghahanda"),
        "events": ["A dragon demands food from a town and turns a man to stone with its fiery breath.", "A boy asks a temple sage for help and follows directions to collect a meteor.", "The sage forges a sword and tells the boy to cover himself with foul-smelling weeds.", "The boy sneaks into the castle, kills the sleeping dragon, and brings its treasure home."],
        "sentences": [
            ("Sa isang kastilyo sa liblib na kabundukan sa timog, naninirahan ang masamang dragon na nanghihingi ng pagkain sa mga tao.", "Di sebuah kastel di pegunungan selatan yang terpencil, tinggal naga jahat yang menuntut makanan dari penduduk."),
            ("Nang tumanggi ang bayan, nagbuga ito ng mainit na singaw at naging batong rebulto ang isang lalaki.", "Ketika penduduk menolak, naga itu menyemburkan uap panas dan mengubah seorang lelaki menjadi patung batu."),
            ("Humingi ng payo ang isang batang lalaki sa matandang pantas sa templo, na nagsabing kunin niya ang meteor na babagsak sa hilaga.", "Seorang anak lelaki meminta nasihat tetua bijaksana di kuil; sang tetua menyuruhnya mengambil meteor yang akan jatuh di utara."),
            ("Gumawa ang pantas ng tabak mula sa meteor at pinayuhang magbalot ang bata ng mabahong damo upang hindi siya maamoy ng dragon.", "Sang tetua menempa pedang dari meteor dan menyuruh anak itu memakai gulma berbau busuk agar naga tak dapat menciumnya."),
            ("Pagkaraan ng mahabang paglalakbay, pumasok ang bata sa kastilyo at nakita ang dragon na natutulog sa loob.", "Setelah perjalanan panjang, anak itu memasuki kastel dan melihat naga sedang tidur di dalam."),
            ("Napatay niya ito gamit ang tabak, saka iniuwi sa bayan ang ginto at alahas; natuwa ang lahat dahil ligtas na sila.", "Ia membunuh naga dengan pedang, lalu membawa pulang emas dan perhiasan; semua orang gembira karena kini mereka aman."),
        ],
        "vocabulary": [("kastilyo", "kastel", "pangngalan"), ("kabundukan", "pegunungan", "pangngalan"), ("singaw", "uap", "pangngalan"), ("pantas", "orang bijaksana", "pangngalan"), ("meteor", "meteor", "pangngalan"), ("mabahong", "berbau busuk", "pang-uri")],
        "expressions": [("humingi ng payo", "meminta nasihat"), ("ligtas na sila", "mereka sudah aman")],
        "grammar": ("Ipinakikita ng nang ang pangyayaring nag-udyok sa kasunod na kilos. Ginagamit ang upang + pandiwa para ipahayag ang layunin.", "Nang memperkenalkan peristiwa pemicu tindakan berikutnya. Untuk + kata kerja menyatakan tujuan."),
        "questions": [
            (("Paano tinakot ng dragon ang bayan?", "Bagaimana naga meneror kota?"), [("Sinunog nito ang palengke", "Ia membakar pasar"), ("Ginawa nitong bato ang isang lalaki gamit ang mainit na hininga", "Ia mengubah seorang lelaki menjadi batu dengan napas panas"), ("Kinulong nito ang pantas", "Ia memenjarakan sang tetua")], 1, ("Mainit na singaw ang ibinuga ng dragon at naging rebulto ang lalaki.", "Naga menyemburkan uap panas yang mengubah lelaki itu menjadi patung.")),
            (("Saan nagmula ang metal ng tabak ng bata?", "Dari mana bahan pedang anak itu berasal?"), [("Sa meteor", "Dari meteor"), ("Sa kastilyo", "Dari kastel"), ("Sa templo", "Dari kuil")], 0, ("Meteor na nakuha sa hilagang langit ang ginamit ng pantas sa paggawa ng tabak.", "Sang tetua menggunakan meteor yang diambil dari langit utara untuk membuat pedang.")),
            (("Bakit nagbalot ng mabahong damo ang bata?", "Mengapa anak itu memakai gulma berbau busuk?"), [("Upang hindi siya maamoy ng dragon", "Agar naga tidak dapat menciumnya"), ("Upang magtago sa niyebe", "Agar bersembunyi di salju"), ("Upang painitin ang tabak", "Agar memanaskan pedang")], 0, ("Iyon ang paraan para hindi matunton ng pang-amoy ng dragon ang bata.", "Itu cara agar naga tidak dapat melacak anak itu dengan penciumannya.")),
        ],
    },
    {
        "category": "Kasaysayan at pagtatanggol", "summary": ("Ipinagtanggol ng tatlong daang Spartan ang makitid na lagusan sa Thermopylae laban sa napakalaking hukbo ng Persia, ngunit tuluyang natalo sila.", "Tiga ratus prajurit Sparta mempertahankan celah sempit di Thermopylae dari pasukan Persia yang jauh lebih besar, tetapi akhirnya kalah."),
        "characters": ["the Spartan chief", "the 300 Spartan soldiers", "the Persian army"], "setting": "The narrow mountain pass at Thermopylae in ancient Greece.",
        "theme": ("Steadfast courage can endure even when victory is unlikely.", "katatagan sa gitna ng pagkatalo", "keteguhan meski kalah"),
        "events": ["A Spartan leader prepares 300 men to hold a narrow entrance against a huge Persian force.", "Persian arrows are stopped by shields, and the Spartans roll logs onto attackers.", "The small force fights for three days with little sleep.", "The Persians find a way through and kill the Spartan chief and his men; the battle remains famous."],
        "sentences": [
            ("Sa sinaunang Greece, naghanda ang pinuno ng mga Spartan na ipagtanggol ang makitid na pasukan sa Thermopylae.", "Di Yunani kuno, pemimpin Sparta bersiap mempertahankan pintu masuk sempit di Thermopylae."),
            ("Tatlong daan lamang ang kaniyang matatapang na kawal, samantalang daan-daang libo ang nasa hukbong Persian.", "Pasukannya hanya terdiri dari tiga ratus prajurit pemberani, sedangkan tentara Persia berjumlah ratusan ribu."),
            ("Pinili nilang harangin ang kalaban sa makipot na lagusan upang hindi madaling makadaan ang napakaraming sundalo.", "Mereka memilih menghadang musuh di celah sempit agar begitu banyak prajurit tak mudah melintas."),
            ("Nasalag ng mga kalasag ang mga palaso, at gumulong naman ang mga troso pababa sa mga umaatake.", "Perisai menahan anak panah, sementara batang-batang kayu digelindingkan ke arah para penyerang."),
            ("Tatlong araw silang lumaban nang halos walang tulog, ngunit kalaunan ay nakahanap ng daan ang mga Persian.", "Mereka bertempur selama tiga hari dengan hampir tanpa tidur, tetapi akhirnya orang Persia menemukan jalan untuk menembus pertahanan."),
            ("Napatay ang pinuno at lahat ng kaniyang kawal; kahit natalo, naging tanyag sa kasaysayan ang kanilang pagtatanggol.", "Pemimpin dan seluruh prajuritnya tewas; meski kalah, pertahanan mereka menjadi terkenal dalam sejarah."),
        ],
        "vocabulary": [("ipagtanggol", "mempertahankan", "pandiwa"), ("makitid", "sempit", "pang-uri"), ("lagusan", "celah", "pangngalan"), ("hukbo", "pasukan", "pangngalan"), ("kalasag", "perisai", "pangngalan"), ("pagtatanggol", "pertahanan", "pangngalan")],
        "expressions": [("halos walang tulog", "hampir tanpa tidur"), ("kahit natalo", "meskipun kalah")],
        "grammar": ("Ang samantalang ay nagtatambis ng magkasalungat na dami o kalagayan. Ginagamit ang kahit + pandiwa upang kilalanin ang kinalabasan nang hindi binabago ang pangunahing punto.", "Samantalang membandingkan jumlah atau keadaan yang berlawanan. Bahkan jika + kata kerja mengakui hasil tanpa mengubah gagasan utama."),
        "questions": [
            (("Ilang Spartan ang humarap sa hukbong Persian?", "Berapa prajurit Sparta menghadapi pasukan Persia?"), [("Tatlong daan", "Tiga ratus"), ("Labindalawang libo", "Dua belas ribu"), ("Daan-daang libo", "Ratusan ribu")], 0, ("Tatlong daan lamang ang mga kawal ng pinuno laban sa mas malaking hukbo.", "Pasukan pemimpin itu hanya terdiri dari tiga ratus prajurit.")),
            (("Bakit nila pinili ang makitid na lagusan?", "Mengapa mereka memilih celah sempit?"), [("Doon naroon ang kanilang kampo", "Di sanalah perkemahan mereka"), ("Mahirap dumaan doon ang malaking hukbo", "Pasukan besar sulit melewati tempat itu"), ("Doon nagmula ang mga palaso", "Anak panah berasal dari sana")], 1, ("Makipot na lugar ang pumigil sa kalaban na gamitin ang buong dami nito.", "Tempat sempit itu mencegah musuh mengerahkan seluruh jumlah pasukannya.")),
            (("Ano ang wakas ng labanan?", "Bagaimana akhir pertempuran itu?"), [("Nagsitakas ang mga Persian", "Orang Persia melarikan diri"), ("Nabihag ang pinuno ngunit nakauwi ang iba", "Pemimpin ditangkap, tetapi yang lain pulang"), ("Napatay ang pinuno at lahat ng Spartan", "Pemimpin dan seluruh prajurit Sparta tewas")], 2, ("Nakahanap ng daan ang kalaban at napatay ang lahat ng kawal ng pinuno.", "Musuh menemukan jalan masuk dan membunuh seluruh prajurit pemimpin itu.")),
        ],
    },
    {
        "category": "Fabel at pagpapahalaga sa sarili", "summary": ("Nakatakas ang usa sa asong humahabol sa kaniya dahil sa matitibay na paa at kuko, hindi sa magandang sungay at dibdib na ipinagmamalaki niya.", "Rusa berhasil lolos dari anjing pengejar berkat kaki dan kuku yang kuat, bukan tanduk dan dada indah yang ia banggakan."),
        "characters": ["the deer", "the dog"], "setting": "A rocky forest with thick trees and shaded places.",
        "theme": ("Useful strengths matter more than attractive appearance.", "kakayahan laban sa anyo", "kemampuan lebih penting daripada penampilan"),
        "events": ["The deer admires his chest and horns but dislikes his thin legs and hooves.", "A dog wakes and chases him through the forest.", "The deer's legs and hard hooves carry him over rocks, while his horns catch in branches and his chest cannot pass between trees.", "He escapes and learns to value the features that truly helped him."],
        "sentences": [
            ("Araw-araw na hinahangaan ng usa ang malapad niyang dibdib at magagandang sungay, ngunit ayaw niya sa payat niyang mga paa at kuko.", "Setiap hari rusa mengagumi dada lebarnya dan tanduknya yang indah, tetapi ia tidak menyukai kaki dan kukunya yang kurus."),
            ("Isang araw, ginising ng ingay niya ang malaking aso na agad siyang hinabol papasok sa kagubatan.", "Suatu hari, suaranya membangunkan anjing besar yang segera mengejarnya ke dalam hutan."),
            ("Mabilis siyang tumakbo dahil sa matitibay na paa, at hindi nasaktan ang matitigas niyang kuko sa magagaspang na bato.", "Ia berlari cepat dengan kaki kuat, dan kuku kerasnya tidak terluka oleh batu-batu kasar."),
            ("Ngunit sumabit sa mga sanga ang kaniyang sungay at hindi makalusot sa pagitan ng makakapal na puno ang malapad niyang dibdib.", "Namun tanduknya tersangkut di dahan, dan dada lebarnya tak dapat melewati sela pepohonan yang rapat."),
            ("Nang makawala siya, nagpahinga siya sa lilim at napagtantong muntik siyang mahuli dahil sa mga ipinagmamalaki niyang anyo.", "Setelah lolos, ia beristirahat di tempat teduh dan menyadari bahwa ia hampir tertangkap karena penampilan yang ia banggakan."),
            ("Natutuhan niyang pahalagahan ang mga paa at kuko na talagang nagligtas sa kaniya.", "Ia belajar menghargai kaki dan kuku yang benar-benar menyelamatkannya."),
        ],
        "vocabulary": [("usa", "rusa", "pangngalan"), ("sungay", "tanduk", "pangngalan"), ("kuko", "kuku", "pangngalan"), ("magagaspang", "kasar", "pang-uri"), ("sumabit", "tersangkut", "pandiwa"), ("pahalagahan", "menghargai", "pandiwa")],
        "expressions": [("muntik siyang mahuli", "ia hampir tertangkap"), ("talagang nagligtas sa kaniya", "benar-benar menyelamatkannya")],
        "grammar": ("Ang dahil sa ay nagpapakilala ng sanhi. Ang nang makawala ay nag-uugnay ng dalawang kilos na magkasunod sa panahon.", "Karena memperkenalkan sebab. Setelah lolos menghubungkan dua tindakan yang berurutan."),
        "questions": [
            (("Aling bahagi ng katawan ang nakatulong sa usa na tumakbo?", "Bagian tubuh mana membantu rusa berlari?"), [("Ang mga sungay", "Tanduknya"), ("Ang mga paa", "Kakinya"), ("Ang dibdib", "Dadanya")], 1, ("Matitibay na paa ang nagbigay sa usa ng bilis habang tumatakas.", "Kaki kuat membuat rusa dapat berlari cepat saat melarikan diri.")),
            (("Ano ang naging hadlang sa usa sa pagitan ng mga puno?", "Apa yang menghambat rusa di antara pepohonan?"), [("Ang kaniyang sungay at dibdib", "Tanduk dan dadanya"), ("Ang kaniyang buntot", "Ekornya"), ("Ang kaniyang mga kuko", "Kukunya")], 0, ("Sumabit ang sungay at hindi magkasya ang dibdib sa makakapal na puno.", "Tanduknya tersangkut dan dadanya tidak muat di antara pepohonan rapat.")),
            (("Ano ang natutuhan ng usa?", "Apa yang dipelajari rusa?"), [("Mas mahalaga ang anyo kaysa kakayahan", "Penampilan lebih penting daripada kemampuan"), ("Dapat iwasan ang lilim", "Tempat teduh harus dihindari"), ("Pahalagahan ang talagang nakatutulong", "Hargai hal yang benar-benar berguna")], 2, ("Paa at kuko ang tumulong sa kaniya kaya iyon ang dapat niyang pahalagahan.", "Kaki dan kukunya yang menolongnya, sehingga itulah yang perlu ia hargai.")),
        ],
    },
    {
        "category": "Paggalugad at tagumpay", "summary": ("Naabot ng isang beteranong kasapi ng pangkat ang tuktok ng Everest, nag-iwan ng mga larawang patunay, at bumaba nang ligtas kasama ang kaniyang mga kasama.", "Seorang penjelajah senior mencapai puncak Everest, mengambil foto sebagai bukti, lalu turun dengan selamat bersama timnya."),
        "characters": ["the narrator", "John Hunt", "the climbing team", "the narrator's relatives"], "setting": "The summit of Mount Everest on May 29, 1953.",
        "theme": ("A difficult achievement is shared, remembered, and celebrated.", "pagsisikap at tagumpay", "usaha dan pencapaian"),
        "events": ["The expedition reaches the summit of Mount Everest on May 29, 1953.", "The narrator observes the snow-covered, silent landscape and photographs it as proof.", "The team turns back after a short time at the summit.", "John Hunt congratulates the climbers, and the narrator sends word to relatives that the team is safe."],
        "sentences": [
            ("Noong Mayo 29, 1953, narating ng tagapagsalaysay at ng kaniyang pangkat ang tuktok ng pinakamataas na bundok sa mundo.", "Pada 29 Mei 1953, narator dan timnya mencapai puncak gunung tertinggi di dunia."),
            ("Makapal ang niyebe sa ilalim ng kanilang bota, at tahimik ang malawak na tanawing napapaligiran ng mga ulap at bato.", "Salju tebal berada di bawah sepatu mereka, dan pemandangan luas yang dikelilingi awan serta batu terasa sunyi."),
            ("Bilang nakatatandang explorer sa grupo, kumuha siya ng maraming larawan upang patunayan na narating nila ang tuktok.", "Sebagai penjelajah senior dalam kelompok, ia mengambil banyak foto untuk membuktikan bahwa mereka telah mencapai puncak."),
            ("Makalipas ang labinlimang minuto, binalot niya ng amerikana ang sarili at naghanda ang pangkat na bumaba.", "Setelah lima belas menit, ia membungkus tubuhnya dengan mantel dan tim bersiap turun."),
            ("Binati sila ng buong pangkat at pinuri ni John Hunt ang kanilang nagawa.", "Seluruh tim memberi selamat dan John Hunt memuji pencapaian mereka."),
            ("Nagpadala siya ng mensahe sa kaniyang mga kamag-anak na ligtas sila, kahit gusto pa niyang pagmasdan ang tanawin.", "Ia mengirim kabar kepada kerabatnya bahwa mereka selamat, meskipun masih ingin menikmati pemandangan lebih lama."),
        ],
        "vocabulary": [("tuktok", "puncak", "pangngalan"), ("niyebe", "salju", "pangngalan"), ("tanawin", "pemandangan", "pangngalan"), ("patunayan", "membuktikan", "pandiwa"), ("bumaba", "turun", "pandiwa"), ("kamag-anak", "kerabat", "pangngalan")],
        "expressions": [("narating ang tuktok", "mencapai puncak"), ("ligtas sila", "mereka selamat")],
        "grammar": ("Ginagamit ang upang + pandiwa upang magpahayag ng layunin. Ipinakikita ng kahit ang pagsalungat sa naunang pangyayari.", "Untuk + kata kerja menyatakan tujuan. Meskipun menunjukkan pertentangan dengan peristiwa sebelumnya."),
        "questions": [
            (("Anong bundok ang narating ng pangkat?", "Gunung apa yang dicapai tim?"), [("Mount Everest", "Gunung Everest"), ("Mount Fuji", "Gunung Fuji"), ("Thermopylae", "Thermopylae")], 0, ("Tuktok ng Mount Everest ang narating nila noong petsang nasa pamagat.", "Mereka mencapai puncak Gunung Everest pada tanggal yang menjadi judul cerita.")),
            (("Bakit kumuha ng maraming larawan ang tagapagsalaysay?", "Mengapa narator mengambil banyak foto?"), [("Para magpadala ng regalo", "Untuk mengirim hadiah"), ("Para magkaroon ng patunay sa pag-akyat", "Untuk memiliki bukti pendakian"), ("Para ipakita ang bagyo", "Untuk menunjukkan badai")], 1, ("Kailangan ng pangkat ng patunay na narating nila ang tuktok.", "Tim membutuhkan bukti bahwa mereka telah mencapai puncak.")),
            (("Ano ang ginawa ng tagapagsalaysay bago umalis sa bundok?", "Apa yang dilakukan narator sebelum meninggalkan gunung?"), [("Nagpadala ng balita na ligtas sila", "Mengirim kabar bahwa mereka selamat"), ("Nagtayo ng bahay", "Membangun rumah"), ("Naghintay ng isang buwan", "Menunggu sebulan")], 0, ("Nagpadala siya ng mensahe sa mga kamag-anak bago bumaba kasama ng pangkat.", "Ia mengirim pesan kepada kerabat sebelum turun bersama tim.")),
        ],
    },
    {
        "category": "Pangako at pananagutan", "summary": ("Nakuha ng palaka ang iskultura ng prinsesa kapalit ng isang pangako; nang maging prinsipe siya, tumanggi siyang pakasalan ang prinsesang hindi tumupad dito.", "Katak memperoleh patung sang putri dengan imbalan sebuah janji; setelah menjadi pangeran, ia menolak menikahi putri yang mengingkari janji itu."),
        "characters": ["the princess", "the frog prince", "the king", "the witches"], "setting": "A pool and the royal palace in a kingdom abroad.",
        "theme": ("Promises carry responsibility, even when keeping them is inconvenient.", "pangako at pananagutan", "janji dan tanggung jawab"),
        "events": ["The princess drops her bear sculpture into a pool, and a frog offers to retrieve it for a promise.", "She promises that he may share her bed but runs away after he returns the sculpture.", "The king insists that she keep her word, and she kisses the frog in the morning.", "The frog becomes a prince who explains witches cursed him, but he refuses marriage because she broke her promise."],
        "sentences": [
            ("Habang naglalaro sa tabi ng lawa, nahulog sa tubig ang eskulturang oso ng isang prinsesa.", "Saat bermain di tepi kolam, patung beruang milik seorang putri jatuh ke air."),
            ("Inalok ng malaking palaka na kunin iyon kapalit ng pangakong patutulugin niya ito sa kaniyang kama at hahalikan kinabukasan.", "Seekor katak besar menawarkan diri mengambilnya dengan imbalan janji bahwa ia boleh tidur di ranjang sang putri dan diciumnya esok pagi."),
            ("Nang makuha ng palaka ang laruan, tumakbo ang prinsesa palayo dahil inakala niyang hindi kailangang tuparin ang pangako.", "Setelah katak mengambil mainan itu, sang putri lari karena mengira ia tidak perlu menepati janji."),
            ("Nang pumunta ang palaka sa palasyo, iniutos ng hari na tuparin niya ang sinabi, kaya pinatulog niya ito sa unan at hinalikan sa umaga.", "Ketika katak datang ke istana, raja memerintahkannya menepati kata-kata, sehingga ia membiarkannya tidur di bantal dan menciumnya pagi hari."),
            ("Biglang naging prinsipe ang palaka at ipinaliwanag na isinumpa siya ng masasamang mangkukulam noong kabataan niya.", "Katak itu tiba-tiba menjadi pangeran dan menjelaskan bahwa para penyihir jahat mengutuknya saat ia masih muda."),
            ("Nais siyang pakasalan ng prinsesa, ngunit tumanggi ang prinsipe dahil hindi niya tinupad ang unang pangako.", "Sang putri ingin menikah dengannya, tetapi pangeran menolak karena ia tidak menepati janji awal."),
        ],
        "vocabulary": [("eskultura", "patung", "pangngalan"), ("kapalit", "imbalan", "pangngalan"), ("pangako", "janji", "pangngalan"), ("tuparin", "menepati", "pandiwa"), ("palasyo", "istana", "pangngalan"), ("mangkukulam", "penyihir", "pangngalan")],
        "expressions": [("kapalit ng pangako", "dengan imbalan sebuah janji"), ("tumanggi dahil", "menolak karena")],
        "grammar": ("Ang dahil + pangungusap ay nagbibigay ng dahilan. Ang nang + pandiwa ay nag-uugnay ng pangyayaring nauna sa kasunod na kilos.", "Karena + klausa memberikan alasan. Setelah + kata kerja menghubungkan peristiwa terdahulu dengan tindakan berikutnya."),
        "questions": [
            (("Ano ang ipinangako ng prinsesa sa palaka?", "Apa yang dijanjikan sang putri kepada katak?"), [("Ginto", "Emas"), ("Pagtulog sa kama at halik sa umaga", "Tidur di ranjangnya dan ciuman pagi hari"), ("Isang kastilyo", "Sebuah kastel")], 1, ("Iyon ang hiniling ng palaka bilang kapalit sa pagkuha ng eskultura.", "Itulah yang diminta katak sebagai imbalan untuk mengambil patung.")),
            (("Sino ang nag-utos sa prinsesa na tuparin ang pangako?", "Siapa yang memerintahkan sang putri menepati janji?"), [("Ang hari", "Raja"), ("Ang kaniyang kapatid", "Saudaranya"), ("Ang mga mangkukulam", "Para penyihir")], 0, ("Ipinatupad ng hari ang pangako matapos dumating ang palaka sa palasyo.", "Raja menegakkan janji itu setelah katak datang ke istana.")),
            (("Bakit tumangging magpakasal ang prinsipe?", "Mengapa pangeran menolak menikah?"), [("Dahil nais niyang bumalik sa ibang kaharian", "Karena ingin kembali ke kerajaan lain"), ("Dahil ayaw niya sa palasyo", "Karena tidak menyukai istana"), ("Dahil hindi tinupad ng prinsesa ang pangako", "Karena sang putri tidak menepati janji")], 2, ("Nadismaya siya nang hindi tuparin ng prinsesa ang unang napagkasunduan.", "Ia kecewa ketika sang putri tidak menepati kesepakatan awal.")),
        ],
    },
    {
        "category": "Pagtuklas at pagtitiyaga", "summary": ("Pinatunayan ni Dr. Norton na may ibong nakapagsasalita matapos itong matagpuan kasama ni Jai malapit sa bulkan sa kolonya.", "Dr. Norton membuktikan bahwa ada burung yang dapat berbicara setelah menemukannya bersama Jai di dekat gunung berapi di koloni."),
        "characters": ["Dr. Norton", "the sailor", "Jai", "the talking bird", "Dr. Norton's colleagues"], "setting": "A researcher's home, an overseas colony, a volcano, and ancient ruins.",
        "theme": ("Persistence can turn an unproven idea into a discovery.", "pagtitiyaga at pagtuklas", "ketekunan dan penemuan"),
        "events": ["A sailor tells biologist Dr. Norton about a talking bird, but his colleagues doubt it.", "Dr. Norton travels to the colony and Jai guides him toward a volcano.", "After searching for weeks without success, Dr. Norton turns back.", "He hears a greeting at old ruins, discovers the bird, cages it, and returns home."],
        "sentences": [
            ("Araw-araw na nag-aaral ng mga hayop si Dr. Norton, isang iskolar ng biyolohiya.", "Dr. Norton, seorang sarjana biologi, mempelajari hewan setiap hari."),
            ("Ikinuwento sa kaniya ng isang mandaragat mula sa kolonya sa ibayong dagat ang tungkol sa ibong nakapagsasalita.", "Seorang pelaut dari koloni seberang laut bercerita kepadanya tentang burung yang dapat berbicara."),
            ("Hindi naniwala ang mga kasamahan niya, ngunit naglayag pa rin siya upang humanap ng makatotohanang patunay.", "Rekan-rekannya tidak percaya, tetapi ia tetap berlayar untuk mencari bukti yang nyata."),
            ("Tinulungan siya ni Jai na maghanap sa paligid ng bulkan, ngunit ilang linggo silang walang makita.", "Jai membantunya mencari di sekitar gunung berapi, tetapi selama berminggu-minggu mereka tidak menemukan apa pun."),
            ("Habang pauwi at dumaraan sa mga sinaunang guho, nakarinig si Dr. Norton ng bumati sa kaniya.", "Dalam perjalanan pulang melewati reruntuhan kuno, Dr. Norton mendengar seseorang menyapanya."),
            ("Nakita niya ang ibon, inilagay ito sa hawla, at umuwi dala ang mahalagang tuklas na pinagdudahan ng iba.", "Ia melihat burung itu, memasukkannya ke dalam sangkar, dan pulang membawa penemuan penting yang diragukan orang lain."),
        ],
        "vocabulary": [("iskolar", "sarjana", "pangngalan"), ("biyolohiya", "biologi", "pangngalan"), ("mandaragat", "pelaut", "pangngalan"), ("kasamahan", "rekan", "pangngalan"), ("bulkan", "gunung berapi", "pangngalan"), ("guho", "reruntuhan", "pangngalan")],
        "expressions": [("sa ibayong dagat", "di seberang laut"), ("dala ang mahalagang tuklas", "membawa penemuan penting")],
        "grammar": ("Ginagamit ang ngunit upang pag-ugnayin ang magkasalungat na ideya. Ang habang ay nagpapakita ng mga kilos na nagaganap kasabay ng isa't isa.", "Tetapi menghubungkan gagasan yang berlawanan. Sementara menunjukkan tindakan yang berlangsung bersamaan."),
        "questions": [
            (("Ano ang ibinalita ng mandaragat kay Dr. Norton?", "Apa yang diceritakan pelaut kepada Dr. Norton?"), [("May ibong nakapagsasalita", "Ada burung yang dapat berbicara"), ("May nawawalang barko", "Ada kapal hilang"), ("May bagong templo", "Ada kuil baru")], 0, ("Iyon ang kuwento ng mandaragat na hindi pinaniwalaan ng mga kasamahan ni Dr. Norton.", "Itulah cerita pelaut yang tidak dipercaya rekan-rekan Dr. Norton.")),
            (("Sino ang gumabay kay Dr. Norton sa kolonya?", "Siapa yang memandu Dr. Norton di koloni?"), [("Ang mandaragat", "Pelaut itu"), ("Si Jai", "Jai"), ("Isang kasamahan", "Seorang rekannya")], 1, ("Si Jai ang nangakong magdadala sa kaniya sa lugar kung saan nakatira ang ibon.", "Jai berjanji membawanya ke tempat burung itu tinggal.")),
            (("Saan niya sa wakas nakita ang ibon?", "Di mana ia akhirnya menemukan burung itu?"), [("Sa templo", "Di kuil"), ("Sa barko", "Di kapal"), ("Malapit sa mga sinaunang guho", "Di dekat reruntuhan kuno")], 2, ("Narinig niya ang ibon habang dumaraan pauwi sa mga lumang guho.", "Ia mendengar burung itu saat melewati reruntuhan tua dalam perjalanan pulang.")),
        ],
    },
    {
        "category": "Fabel at talino", "summary": ("Natalo ng pamilya ni Tera ang mayabang na kunehong si Ricky sa karera sa pamamagitan ng pagpapanggap na magkakapareho sila sa mga palatandaan sa daan.", "Keluarga Tera mengalahkan Ricky si kelinci yang sombong dalam lomba dengan menyamar serupa di sepanjang jalur."),
        "characters": ["Ricky the rabbit", "Tera the turtle", "Tera's family"], "setting": "A race path from a riverbank through a valley to a hill.",
        "theme": ("Careful teamwork can outwit speed and overconfidence.", "pagtutulungan at panlilinlang", "kerja sama dan siasat"),
        "events": ["Ricky boasts no one can beat him, and Tera challenges him to race to a hill.", "Tera admits to her family that she plans to cheat and gives them instructions.", "Her relatives wear matching white feathers and take positions along the route.", "Ricky sees a turtle ahead at each point, exhausts himself, and reaches the hill after Tera's sister."],
        "sentences": [
            ("Sa tabi ng ilog, nagyabang si Ricky na walang makakatalo sa kaniya sa karera, ngunit hinamon siya ni Tera na pagong.", "Di tepi sungai, Ricky membual bahwa tak seorang pun dapat mengalahkannya dalam lomba, tetapi Tera si kura-kura menantangnya."),
            ("Ang patutunguhan nila ay burol, at alam ni Tera na mas mabilis tumakbo si Ricky kaysa kaniya.", "Tujuan mereka adalah bukit, dan Tera tahu Ricky berlari lebih cepat darinya."),
            ("Inamin niya sa pamilya na mandadaya siya, saka nag-utos na magsuot silang lahat ng magkakatulad na puting balahibo.", "Ia mengaku kepada keluarganya bahwa ia akan berbuat curang, lalu menyuruh mereka mengenakan bulu putih yang serupa."),
            ("Nagtago sa mga anino ang mga kamag-anak niya sa daan, at isa-isang tumakbo sa unahan tuwing papalapit si Ricky.", "Keluarganya bersembunyi dalam bayang-bayang di sepanjang jalan dan berlari ke depan bergantian setiap Ricky mendekat."),
            ("Inakala ni Ricky na laging nauuna si Tera kaya ginamit niya ang napakaraming lakas sa paghabol.", "Ricky mengira Tera selalu berada di depan, sehingga ia menghabiskan banyak tenaga untuk mengejarnya."),
            ("Pagdating niya sa burol, naroon na ang kapatid ni Tera; nanalo ang mga pagong at hindi nahalata ni Ricky ang daya nila.", "Saat tiba di bukit, saudara Tera sudah berada di sana; keluarga kura-kura menang dan Ricky tidak menyadari siasat mereka."),
        ],
        "vocabulary": [("nagyabang", "membual", "pandiwa"), ("patutunguhan", "tujuan", "pangngalan"), ("mandadaya", "akan berbuat curang", "pandiwa"), ("balahibo", "bulu", "pangngalan"), ("anino", "bayang-bayang", "pangngalan"), ("nahalata", "menyadari", "pandiwa")],
        "expressions": [("walang makakatalo sa kaniya", "tak seorang pun dapat mengalahkannya"), ("hindi nahalata ang daya", "tidak menyadari siasatnya")],
        "grammar": ("Ang tuwing ay nagsasaad ng paulit-ulit na pagkakataon. Ang kaya ay nag-uugnay ng sanhi at bunga.", "Setiap kali menunjukkan kejadian berulang. Maka menghubungkan sebab dan akibat."),
        "questions": [
            (("Saan ang dulo ng karera?", "Di mana garis akhir lomba?"), [("Sa burol", "Di bukit"), ("Sa templo", "Di kuil"), ("Sa kabilang pampang", "Di tepi seberang")], 0, ("Burol ang itinakdang patutunguhan nina Ricky at Tera.", "Bukit adalah tujuan yang ditetapkan Ricky dan Tera.")),
            (("Paano nagtulungan ang pamilya ni Tera?", "Bagaimana keluarga Tera bekerja sama?"), [("Nagpalit-palit sila ng lugar at nagpanggap na si Tera", "Mereka bergantian di jalur dan menyamar sebagai Tera"), ("Pinahinto nila ang karera", "Mereka menghentikan lomba"), ("Nagtago sila ng pagkain ni Ricky", "Mereka menyembunyikan makanan Ricky")], 0, ("Nagkakawangis ang mga kamag-anak ni Tera sa puting balahibo at nag-abang sa landas.", "Kerabat Tera tampak serupa dengan bulu putih dan menunggu di sepanjang jalur.")),
            (("Bakit napagod si Ricky?", "Mengapa Ricky kelelahan?"), [("Masyado siyang naglakad bago magsimula", "Ia berjalan terlalu jauh sebelum lomba"), ("Patuloy niyang hinabol ang mga kamag-anak ni Tera", "Ia terus mengejar anggota keluarga Tera"), ("Nawala ang kaniyang sapatos", "Sepatunya hilang")], 1, ("Akala niya ay laging nasa unahan si Tera kaya nag-ubos siya ng lakas sa paghabol.", "Ia mengira Tera selalu di depan dan menghabiskan tenaga untuk mengejarnya.")),
        ],
    },
    {
        "category": "Katarungan at pagtulong sa kapwa", "summary": ("Naging tanyag si Bartelby dahil tinulungan niya si Gilliam at ang mahihirap sa pamamagitan ng pagkuha ng pagkain mula sa mayayaman.", "Bartelby dikenal karena menolong Gilliam dan kaum miskin dengan mengambil makanan dari orang kaya."),
        "characters": ["Bartelby O’Boyle", "Gilliam", "the royal family", "the poor", "the rich"], "setting": "A divided kingdom in disorder and its capital city.",
        "theme": ("Cooperation and generosity can bring aid to people in need.", "pagtutulungan at katarungan", "kerja sama dan keadilan"),
        "events": ["Bartelby is forced to work for the royal family and resents the unfair life.", "A struggle for authority divides the kingdom, and he escapes during the disorder.", "He decides to help hungry people and defends Gilliam from attackers in the capital.", "Bartelby and Gilliam take surplus food from the rich and give it to the poor, earning admiration."],
        "sentences": [
            ("Noong bata pa si Bartelby O’Boyle, ginawa siyang alipin ng maharlikang pamilya at hindi siya pinayagang makipaglaro sa ibang bata.", "Saat kecil, Bartelby O’Boyle dijadikan budak keluarga kerajaan dan tidak diizinkan bermain dengan anak-anak lain."),
            ("Nang mag-away ang mga pangkat para sa kapangyarihan, nagkaroon ng kaguluhan sa kaharian at nakatakas siya.", "Ketika kelompok-kelompok bertikai memperebutkan kekuasaan, kerajaan menjadi kacau dan ia melarikan diri."),
            ("Nakita niyang maraming tao ang nagugutom kaya nagpasiyang tulungan sila, ngunit kailangan muna niyang humanap ng paraan.", "Ia melihat banyak orang kelaparan dan memutuskan menolong mereka, tetapi ia perlu mencari cara terlebih dahulu."),
            ("Sa kabisera, ipinagtanggol niya si Gilliam mula sa mga lalaking umaatake at binigyan ito ng pagkain.", "Di ibu kota, ia membela Gilliam dari para lelaki yang menyerangnya dan memberinya makanan."),
            ("Naging magkaibigan sila at kumuha ng sobrang pagkain sa mayayaman upang ipamahagi sa mga walang makain.", "Mereka berteman dan mengambil makanan berlebih dari orang kaya untuk dibagikan kepada mereka yang tak punya makanan."),
            ("Nakipagtulungan ang iba sa kanila, at hinangaan sa buong kaharian si Bartelby dahil sa pagtulong niya sa mahihirap.", "Orang lain ikut bekerja sama, dan Bartelby dikagumi di seluruh kerajaan karena menolong kaum miskin."),
        ],
        "vocabulary": [("alipin", "budak", "pangngalan"), ("maharlika", "kerajaan", "pang-uri"), ("kaguluhan", "kekacauan", "pangngalan"), ("kabisera", "ibu kota", "pangngalan"), ("ipamahagi", "membagikan", "pandiwa"), ("mahihirap", "kaum miskin", "pangngalan")],
        "expressions": [("nagpasiyang tulungan sila", "memutuskan untuk menolong mereka"), ("walang makain", "tidak punya makanan")],
        "grammar": ("Ginagamit ang kaya upang ipakita ang bunga ng naunang dahilan. Ang mula sa ay nagpapakilala ng pinagmulan o pinanggalingan.", "Maka menunjukkan akibat dari alasan sebelumnya. Dari memperkenalkan asal atau sumber."),
        "questions": [
            (("Bakit tumakas si Bartelby sa maharlikang pamilya?", "Mengapa Bartelby melarikan diri dari keluarga kerajaan?"), [("Nais niyang hanapin si Gilliam", "Ia ingin mencari Gilliam"), ("Naging magulo ang kaharian dahil sa agawan sa kapangyarihan", "Kerajaan kacau karena perebutan kekuasaan"), ("Inutusan siya ng hari", "Raja menyuruhnya")], 1, ("Nagkaroon ng labanan ng mga pangkat para sa pamumuno kaya nagkagulo.", "Kelompok-kelompok berebut kekuasaan sehingga terjadi kekacauan.")),
            (("Sino ang ipinagtanggol ni Bartelby sa kabisera?", "Siapa yang dibela Bartelby di ibu kota?"), [("Si Gilliam", "Gilliam"), ("Ang hari", "Raja"), ("Ang kaniyang kapatid", "Saudaranya")], 0, ("Inatake si Gilliam ng ilang lalaki at ipinagtanggol siya ni Bartelby.", "Beberapa lelaki menyerang Gilliam, lalu Bartelby membelanya.")),
            (("Kanino ibinigay nina Bartelby at Gilliam ang pagkain?", "Kepada siapa Bartelby dan Gilliam memberikan makanan?"), [("Sa mga sundalo", "Kepada para prajurit"), ("Sa mga mayayaman", "Kepada orang kaya"), ("Sa mga nagugutom na mahihirap", "Kepada kaum miskin yang kelaparan")], 2, ("Ibinibigay nila sa mga walang pagkain ang sobrang kinuha nila mula sa mayayaman.", "Mereka memberikan kelebihan makanan yang diambil dari orang kaya kepada orang yang kelaparan.")),
        ],
    },
    {
        "category": "Pirata at bunga ng mga pasiya", "summary": ("Iniwan ni Blackbeard ang pamimirata matapos mang-hostage ng mga taga-bayan para sa gamot, ngunit natagpuan at napatay siya ng hukbong-dagat habang nangingisda.", "Blackbeard berhenti menjadi bajak laut setelah menyandera warga demi obat, tetapi angkatan laut menemukannya dan membunuhnya saat ia memancing."),
        "characters": ["Blackbeard", "the ship's narrator", "the townspeople", "the Royal Navy"], "setting": "A pirate ship in fog, a coastal town, and a fishing boat at sea.",
        "theme": ("Past actions can continue to shape a person's future.", "bunga ng nakaraan", "akibat perbuatan masa lalu"),
        "events": ["A narrator sees Blackbeard aboard a pirate ship in thick fog.", "Blackbeard attacks ships, takes townspeople, and demands medicine for sick pirates.", "A reward and the prospect of trial lead him to quit piracy and become a fisherman.", "The Royal Navy finds him at sea, kills him, and leaves his story to be retold."],
        "sentences": [
            ("Noong unang gabi ng trabaho ng tagapagsalaysay sa malaking barkong pirata, nakita niya si Blackbeard sa gitna ng makapal na hamog.", "Pada malam pertama narator bekerja di kapal bajak laut besar, ia melihat Blackbeard di tengah kabut tebal."),
            ("Minsan, sinalakay ni Blackbeard ang mga barkong malapit sa isang bayan at dinakip ang ilang mamamayan.", "Suatu hari, Blackbeard menyerang kapal-kapal dekat sebuah kota dan menawan beberapa warga."),
            ("Humingi siya ng gamot para sa mga maysakit na pirata, ngunit galit at takot ang mga taga-bayan.", "Ia menuntut obat bagi para bajak laut yang sakit, tetapi penduduk kota marah dan ketakutan."),
            ("Nagbigay rin sila ng gamot dahil wala silang magawa, at nag-alok ang bayan ng gantimpala para mahuli siya.", "Mereka tetap memberikan obat karena tak punya pilihan, dan kota menawarkan hadiah bagi siapa pun yang menangkapnya."),
            ("Ayaw niyang humarap sa paglilitis kaya iniwan niya ang pagiging pirata at naging mangingisda.", "Ia tidak ingin menghadapi pengadilan, sehingga berhenti menjadi bajak laut dan menjadi nelayan."),
            ("Natagpuan pa rin siya ng hukbong-dagat habang nasa bangka, at namatay siya sa labanan; patuloy namang ikinukuwento ang kaniyang buhay.", "Angkatan laut tetap menemukannya di atas perahu dan ia tewas dalam pertempuran; kisah hidupnya terus diceritakan."),
        ],
        "vocabulary": [("barkong pirata", "kapal bajak laut", "parirala"), ("hamog", "kabut", "pangngalan"), ("dinakip", "menawan", "pandiwa"), ("gamot", "obat", "pangngalan"), ("gantimpala", "hadiah", "pangngalan"), ("paglilitis", "pengadilan", "pangngalan")],
        "expressions": [("wala silang magawa", "mereka tidak punya pilihan"), ("iniwan ang pagiging pirata", "berhenti menjadi bajak laut")],
        "grammar": ("Ginagamit ang kaya upang ilahad ang bunga ng pasiya. Ang habang ay nagpapakita ng kilos na nagaganap kasabay ng iba.", "Sehingga menyatakan akibat dari keputusan. Saat menunjukkan tindakan yang berlangsung pada waktu yang sama."),
        "questions": [
            (("Bakit humingi ng gamot si Blackbeard sa bayan?", "Mengapa Blackbeard meminta obat dari kota?"), [("May sakit ang ilang pirata", "Beberapa bajak laut sakit"), ("Nasira ang kaniyang barko", "Kapalnya rusak"), ("Nais niyang magbukas ng tindahan", "Ia ingin membuka toko")], 0, ("Kailangan niya ng gamot para sa mga maysakit na tauhan sa barko.", "Ia membutuhkan obat untuk awak kapal yang sakit.")),
            (("Ano ang ginawa ni Blackbeard matapos magkaroon ng gantimpala sa pagdakip sa kaniya?", "Apa yang dilakukan Blackbeard setelah ada hadiah untuk menangkapnya?"), [("Nagpatuloy siya sa pamimirata", "Ia terus membajak kapal"), ("Iniwan niya ang pamimirata at nangisda", "Ia berhenti membajak kapal dan menjadi nelayan"), ("Naglingkod siya sa bayan", "Ia bekerja untuk kota")], 1, ("Iniwasan niya ang paglilitis sa pamamagitan ng pagtigil sa pagiging pirata.", "Ia berusaha menghindari pengadilan dengan berhenti menjadi bajak laut.")),
            (("Sino ang pumatay kay Blackbeard?", "Siapa yang membunuh Blackbeard?"), [("Mga mangingisda", "Para nelayan"), ("Mga taga-bayan", "Penduduk kota"), ("Hukbong-dagat ng hari", "Angkatan laut kerajaan")], 2, ("Inatake siya ng Royal Navy habang nangingisda sa kaniyang bangka.", "Royal Navy menyerangnya ketika ia sedang memancing di perahunya.")),
        ],
    },
    {
        "category": "Katatawanan at imahinasyon", "summary": ("Nangarap si Carl ng isang dinosaur na magpapasikat sa kaniya habang gumagawa ng pagsusulit, ngunit nakalimutan niyang tapusin ang mismong pagsusulit.", "Carl membayangkan dinosaurus yang akan membuatnya terkenal saat mengerjakan ujian, tetapi lupa menyelesaikan ujiannya sendiri."),
        "characters": ["Carl", "Carl's mother", "the teacher", "the principal", "Carl's imagined dinosaur"], "setting": "Carl's rainy morning, school, and an imagined dinosaur exhibition.",
        "theme": ("Imagination is exciting, but responsibilities still need attention.", "imahinasyon at pananagutan", "imajinasi dan tanggung jawab"),
        "events": ["Carl wakes late with unfinished homework and is sent to school in rain.", "His teacher sends him to the principal over his umbrella, and he struggles with a geography test.", "He draws a dinosaur and imagines it becoming famous and exhibited at school.", "The teacher calls time, and Carl realizes he has not finished the real test."],
        "sentences": [
            ("Pagkagising ni Carl, naalala niyang hindi niya nagawa ang takdang-aralin sa astronomiya at kimika.", "Saat bangun, Carl ingat bahwa ia belum mengerjakan pekerjaan rumah astronomi dan kimianya."),
            ("Umuulan at basang-basa siya sa pagpasok, saka pinagalitan ng guro dahil inilagay niya ang payong sa maling lugar.", "Hujan turun dan ia basah kuyup saat tiba di sekolah, lalu gurunya menegur karena ia meletakkan payung di tempat yang salah."),
            ("Dahil hindi niya alam ang mga sagot sa pagsusulit sa heograpiya, nagsimula siyang gumuhit ng malaking dinosaur sa papel.", "Karena tidak mengetahui jawaban ujian geografi, ia mulai menggambar dinosaurus besar di kertas."),
            ("Sa isip niya, naging buhay ang dinosaur at hinangaan siya ng klase bilang henyo.", "Dalam pikirannya, dinosaurus itu hidup dan teman-teman sekelas mengaguminya sebagai jenius."),
            ("Inisip niyang ipapakita niya ito sa paaralan at maniningil ng bayad sa mga gustong makakita.", "Ia membayangkan akan memamerkannya di sekolah dan meminta bayaran dari orang-orang yang ingin melihatnya."),
            ("Nang sabihin ng guro na ipasa na ang papel, nakita ni Carl na hindi pala niya natapos ang tunay na pagsusulit.", "Ketika guru menyuruh mengumpulkan kertas, Carl menyadari bahwa ia ternyata belum menyelesaikan ujian yang sebenarnya."),
        ],
        "vocabulary": [("takdang-aralin", "pekerjaan rumah", "pangngalan"), ("payong", "payung", "pangngalan"), ("pagsusulit", "ujian", "pangngalan"), ("gumuhit", "menggambar", "pandiwa"), ("hinangaan", "mengagumi", "pandiwa"), ("ipasa", "mengumpulkan", "pandiwa")],
        "expressions": [("sa isip niya", "dalam pikirannya"), ("hindi pala niya natapos", "ternyata ia belum menyelesaikan")],
        "grammar": ("Ang dahil ay nagpapakilala ng dahilan. Ginagamit ang pala upang magpahiwatig ng bagong pagkaunawa o pagkakatuklas.", "Karena memperkenalkan alasan. Ternyata menandai pemahaman atau penemuan yang baru disadari."),
        "questions": [
            (("Anong dalawang takdang-aralin ang nakalimutan ni Carl?", "Dua pekerjaan rumah apa yang dilupakan Carl?"), [("Astronomiya at kimika", "Astronomi dan kimia"), ("Matematika at musika", "Matematika dan musik"), ("Heograpiya at kasaysayan", "Geografi dan sejarah")], 0, ("Hindi nagawa ni Carl ang gawain niya sa astronomiya at kimika.", "Carl belum mengerjakan tugas astronomi dan kimianya.")),
            (("Ano ang iginuhit niya habang nagsusulit?", "Apa yang ia gambar saat ujian?"), [("Isang bangka", "Sebuah perahu"), ("Isang dinosaur", "Seekor dinosaurus"), ("Isang kastilyo", "Sebuah kastel")], 1, ("Dahil hindi niya alam ang mga sagot, gumuhit siya ng malaking dinosaur.", "Karena tidak tahu jawabannya, ia menggambar dinosaurus besar.")),
            (("Bakit hindi natapos ni Carl ang pagsusulit?", "Mengapa Carl tidak menyelesaikan ujian?"), [("Nawala ang kaniyang papel", "Kertasnya hilang"), ("Nagpunta siya sa principal", "Ia pergi ke kepala sekolah"), ("Nangarap siya habang gumuguhit", "Ia melamun saat menggambar")], 2, ("Nadala siya sa imahinasyon niya at hindi na nasagutan ang natitirang bahagi.", "Ia terbawa lamunannya dan tidak mengerjakan sisa ujian.")),
        ],
    },
    {
        "category": "Pagbabago at pananagutan", "summary": ("Binago ng mga kusinero ang mapang-abusong restawran matapos itali ang chef; nang mapagtanto niyang siya ang may sala, nagsimula siyang maging mapagbigay.", "Para juru masak mengubah restoran yang penuh kekerasan setelah mengikat kepala koki; saat menyadari kesalahannya, ia mulai bersikap murah hati."),
        "characters": ["the mean chef", "the cooks", "the waiters", "the customers"], "setting": "A poorly managed restaurant.",
        "theme": ("Leaders must accept responsibility for the way they treat others.", "pananagutan ng pinuno", "tanggung jawab seorang pemimpin"),
        "events": ["The chef overcharges customers, fails to repair the oven, and mistreats workers.", "Cooks oppose him and tie him up so they can run the restaurant.", "They lower prices, cook with good ingredients, and make the restaurant welcoming.", "The chef recognizes that he caused the problems and offers customers a free meal."],
        "sentences": [
            ("Mahal maningil ang masungit na chef, at hindi kayang bumili ng pagkain ng maraming customer.", "Kepala koki yang galak memasang harga mahal, dan banyak pelanggan tidak mampu membeli makanan."),
            ("Nang masira ang metal na hurno at hindi niya ipaayos, nasunog ang niluluto at kandila na lamang ang ilaw.", "Ketika oven logam rusak dan tidak ia perbaiki, masakan terbakar dan hanya lilin yang menerangi ruangan."),
            ("Binabantayan niya ang mga kusinero, sinisigawan sila, at hindi binabayaran ang mga waiter kaya nabaon ang mga ito sa utang.", "Ia mengawasi para juru masak, membentak mereka, dan tidak membayar pelayan sehingga mereka terlilit utang."),
            ("Sa wakas, tumutol ang lahat ng manggagawa at itinali ang chef upang sila muna ang mamahala sa restawran.", "Akhirnya semua pekerja melawan dan mengikat kepala koki agar mereka dapat mengelola restoran."),
            ("Binabaan nila ang presyo, gumamit ng masasarap na sangkap, at nagsindi ng mga ilaw kaya dumagsa ang mga customer.", "Mereka menurunkan harga, memakai bahan-bahan terbaik, dan menyalakan lampu sehingga pelanggan berdatangan."),
            ("Napagtanto ng chef na siya ang may sala sa mga problema at iginiit niyang magbigay ng libreng pagkain sa mga customer.", "Kepala koki menyadari bahwa ia penyebab masalah dan bersikeras memberikan makanan gratis kepada pelanggan."),
        ],
        "vocabulary": [("masungit", "galak", "pang-uri"), ("hurno", "oven", "pangngalan"), ("sinisigawan", "membentak", "pandiwa"), ("nabaon", "terlilit utang", "pandiwa"), ("sangkap", "bahan", "pangngalan"), ("libreng pagkain", "makanan gratis", "parirala")],
        "expressions": [("Sa wakas", "Akhirnya"), ("siya ang may sala", "ia yang bersalah")],
        "grammar": ("Ang kaya ay nagpapakita ng bunga. Ginagamit ang upang + pandiwa upang ipaliwanag ang layunin ng isang kilos.", "Sehingga menunjukkan akibat. Untuk + kata kerja menjelaskan tujuan suatu tindakan."),
        "questions": [
            (("Bakit nasunog ang pagkain sa restawran?", "Mengapa makanan di restoran terbakar?"), [("Nasira ang hurno at hindi ito pinaayos", "Oven rusak dan tidak diperbaiki"), ("Walang nagluto", "Tak ada yang memasak"), ("Namatay ang lahat ng kandila", "Semua lilin padam")], 0, ("Hindi pinaayos ng chef ang sirang metal na hurno kaya nasunog ang pagkain.", "Kepala koki tidak memperbaiki oven logam yang rusak sehingga makanan terbakar.")),
            (("Ano ang ginawa ng mga kusinero upang mapatakbo ang restawran?", "Apa yang dilakukan para juru masak untuk menjalankan restoran?"), [("Umalis sila sa bayan", "Mereka meninggalkan kota"), ("Itinali nila ang chef at sila ang namahala", "Mereka mengikat kepala koki dan mengambil alih"), ("Isinara nila ang kusina", "Mereka menutup dapur")], 1, ("Itinali nila ang chef upang makontrol nila ang restawran.", "Mereka mengikat kepala koki agar dapat mengendalikan restoran.")),
            (("Ano ang napagtanto ng chef sa huli?", "Apa yang disadari kepala koki pada akhirnya?"), [("Ang mga customer ang may sala", "Pelanggan yang bersalah"), ("Walang silbi ang ilaw", "Lampu tidak berguna"), ("Siya ang sanhi ng mga problema", "Ia penyebab masalah")], 2, ("Kinilala niyang sariling asal ang dahilan ng paghina ng restawran.", "Ia mengakui bahwa perilakunya sendiri menyebabkan masalah restoran.")),
        ],
    },
    {
        "category": "Fabel at talino", "summary": ("Nakatakas ang pusa sa mga lobo sa pamamagitan ng pag-akyat sa puno, samantalang nahuli ang soro dahil hindi makapili sa napakarami nitong plano.", "Kucing lolos dari serigala dengan memanjat pohon, sedangkan rubah tertangkap karena tak dapat memilih di antara terlalu banyak rencananya."),
        "characters": ["the cat", "the fox", "the wolves"], "setting": "A mountain peak and nearby forest where wolves approach.",
        "theme": ("One reliable plan is better than many confused ideas.", "isang maaasahang plano", "satu rencana yang dapat diandalkan"),
        "events": ["The fox boasts that he has countless escape plans, while the cat has only one.", "The fox offers to teach the cat, who says her plan always works.", "Wolves appear, and the cat immediately climbs a tree.", "The fox hesitates over which plan to use and is caught by the wolves."],
        "sentences": [
            ("Sa tuktok ng bundok, pinag-usapan ng pusa at soro kung paano sila makatatakas sa mga kaaway.", "Di puncak gunung, kucing dan rubah membicarakan cara melarikan diri dari musuh."),
            ("Ipinagyabang ng soro na bilyon-bilyon ang mga plano niya, mula sa pag-ukit ng butas hanggang pagtawag sa mga kaibigan.", "Rubah membanggakan bahwa ia punya miliaran rencana, dari membuat lubang sampai memanggil teman-temannya."),
            ("Iisa lamang ang plano ng pusa, at tiniyak niyang gumagana iyon sa bawat pagkakataon.", "Kucing hanya memiliki satu rencana dan meyakinkan rubah bahwa rencana itu selalu berhasil."),
            ("Nang makakita sila ng pangkat ng mga lobo, mabilis na umakyat sa puno ang pusa.", "Ketika melihat sekawanan serigala, kucing segera memanjat pohon."),
            ("Hindi makapagpasya ang soro kung tatawag sa mga kaibigan o susubok ng ibang paraan, kaya paikot-ikot lamang siya.", "Rubah tidak dapat memutuskan apakah harus memanggil teman atau mencoba cara lain, sehingga ia hanya berputar-putar."),
            ("Nahuli ng mga lobo ang soro, samantalang ligtas sa puno ang pusa; mas mabuti pala ang isang mahusay na plano kaysa maraming magulo.", "Serigala menangkap rubah, sementara kucing aman di pohon; ternyata satu rencana baik lebih berguna daripada banyak rencana yang membingungkan."),
        ],
        "vocabulary": [("soro", "rubah", "pangngalan"), ("kaaway", "musuh", "pangngalan"), ("ipinagyabang", "membanggakan", "pandiwa"), ("tiniyak", "meyakinkan", "pandiwa"), ("makapagpasya", "memutuskan", "pandiwa"), ("nahuli", "tertangkap", "pandiwa")],
        "expressions": [("sa bawat pagkakataon", "setiap kali"), ("hindi makapagpasya", "tidak dapat memutuskan")],
        "grammar": ("Ang kaysa ay ginagamit sa paghahambing. Ang nang ay maaaring magpakilala ng oras kung kailan nagsimula ang kasunod na kilos.", "Daripada digunakan untuk membandingkan. Ketika memperkenalkan waktu dimulainya tindakan berikutnya."),
        "questions": [
            (("Ilang plano ang sinabi ng pusa na mayroon siya?", "Berapa banyak rencana yang dikatakan kucing ia miliki?"), [("Isa", "Satu"), ("Dose", "Dua belas"), ("Bilyon-bilyon", "Miliaran")], 0, ("Sinabi ng pusa na iisa ang plano niya at gumagana ito.", "Kucing mengatakan ia hanya punya satu rencana yang selalu berhasil.")),
            (("Paano nakatakas ang pusa sa mga lobo?", "Bagaimana kucing lolos dari serigala?"), [("Tumakbo sa ilog", "Berlari ke sungai"), ("Umakyat sa puno", "Memanjat pohon"), ("Tumawag ng hukbo", "Memanggil pasukan")], 1, ("Agad na umakyat sa puno ang pusa nang makita ang mga lobo.", "Kucing segera memanjat pohon ketika melihat serigala.")),
            (("Bakit nahuli ang soro?", "Mengapa rubah tertangkap?"), [("Hindi siya makapili ng plano", "Ia tidak dapat memilih rencana"), ("Nakatulog siya", "Ia tertidur"), ("Nawala ang mga kaibigan niya", "Teman-temannya hilang")], 0, ("Nag-alinlangan siya at nag-isip kung aling plano ang uunahin.", "Ia ragu dan memikirkan rencana mana yang harus digunakan lebih dulu.")),
        ],
    },
    {
        "category": "Pag-aaral at kalusugan", "summary": ("Nanghina si Sue dahil sa sobrang pag-aaral at tinuruan siya ng nars na magpahinga upang mapangalagaan ang kaniyang kalusugan.", "Sue jatuh sakit karena belajar berlebihan dan perawat mengajarinya beristirahat demi kesehatannya."),
        "characters": ["Sue", "the teacher", "the nurse", "Sue's parents"], "setting": "Sue's dormitory, a physics test, and the school nurse's office.",
        "theme": ("Rest is part of learning and caring for oneself.", "pahinga at pangangalaga sa sarili", "istirahat dan menjaga diri"),
        "events": ["Sue prepares carefully for school but has slept very little while completing work and studying.", "During a physics test, her vision blurs and she briefly cannot see clearly.", "She insists on finishing a portion of the test before going to the nurse.", "The nurse warns that overwork can have severe effects, and Sue begins getting enough rest."],
        "sentences": [
            ("Maagang umalis si Sue sa dormitoryo na malinis ang uniporme at may papel tungkol sa greenhouse na natapos niya.", "Sue meninggalkan asrama pagi-pagi dengan seragam bersih dan makalah tentang rumah kaca yang sudah ia selesaikan."),
            ("Halos hindi siya natulog dahil gumawa rin siya ng takdang-aralin at nag-aral para sa pagsusulit sa pisika.", "Ia hampir tidak tidur karena juga mengerjakan tugas dan belajar untuk ujian fisika."),
            ("Habang nagsusulit, uminit ang mukha niya at lumabo ang paningin hanggang hindi siya makakita nang ilang sandali.", "Saat ujian, wajahnya terasa panas dan penglihatannya kabur sampai ia tidak dapat melihat selama beberapa saat."),
            ("Nais siyang dalhin ng guro sa nars, ngunit ipinilit ni Sue na tapusin muna ang natitirang bahagi ng pagsusulit.", "Guru ingin membawanya ke perawat, tetapi Sue bersikeras menyelesaikan sisa ujiannya terlebih dahulu."),
            ("Binigyan siya ng nars ng katas at ipinaliwanag na maaaring magdulot ng malubhang epekto ang palaging pagkapagod.", "Perawat memberinya jus dan menjelaskan bahwa kelelahan terus-menerus dapat menimbulkan akibat serius."),
            ("Naalala ni Sue ang payo ng kaniyang mga magulang at nagpasyang matulog nang sapat mula noon.", "Sue mengingat nasihat orang tuanya dan memutuskan untuk cukup tidur sejak saat itu."),
        ],
        "vocabulary": [("dormitoryo", "asrama", "pangngalan"), ("uniporme", "seragam", "pangngalan"), ("paningin", "penglihatan", "pangngalan"), ("lumabo", "kabur", "pandiwa"), ("malubha", "serius", "pang-uri"), ("pagkapagod", "kelelahan", "pangngalan")],
        "expressions": [("halos hindi siya natulog", "ia hampir tidak tidur"), ("matulog nang sapat", "tidur dengan cukup")],
        "grammar": ("Ginagamit ang habang para sa kilos na nangyayari kasabay ng iba. Ang mula noon ay nagsasaad ng pagpapatuloy mula sa isang pangyayari.", "Saat menghubungkan tindakan yang berlangsung bersamaan. Sejak saat itu menandai kelanjutan setelah suatu peristiwa."),
        "questions": [
            (("Bakit halos hindi natulog si Sue?", "Mengapa Sue hampir tidak tidur?"), [("Naglakbay siya buong gabi", "Ia bepergian semalaman"), ("Gumawa siya ng papel at nag-aral para sa pagsusulit", "Ia menulis makalah dan belajar untuk ujian"), ("Nagtrabaho siya sa kusina", "Ia bekerja di dapur")], 1, ("Naghanda siya ng papel at nag-aral para sa pagsusulit sa pisika.", "Ia menyiapkan makalah dan belajar untuk ujian fisika.")),
            (("Ano ang nangyari sa paningin ni Sue habang nagsusulit?", "Apa yang terjadi pada penglihatan Sue saat ujian?"), [("Lumabo ito", "Penglihatannya kabur"), ("Lalong luminaw ito", "Penglihatannya semakin jelas"), ("Nakita niya ang greenhouse", "Ia melihat rumah kaca")], 0, ("Lumabo ang paningin niya at hindi siya makakita nang ilang sandali.", "Penglihatannya kabur dan ia tidak dapat melihat selama beberapa saat.")),
            (("Ano ang ipinayo ng nars kay Sue?", "Apa nasihat perawat kepada Sue?"), [("Huwag nang pumasok sa paaralan", "Jangan pergi ke sekolah lagi"), ("Magpatuloy kahit pagod", "Teruskan meski lelah"), ("Magpahinga at matulog nang sapat", "Beristirahat dan tidur cukup")], 2, ("Nagbabala ang nars na may malubhang epekto ang sobrang pagtatrabaho at kailangan ni Sue ng pahinga.", "Perawat memperingatkan bahwa kerja berlebihan berdampak serius dan Sue perlu beristirahat.")),
        ],
    },
]


STORIES.extend([
    {
        "category": "Kasaysayan at pagtuklas", "summary": ("Nakakita ang tagapagsalaysay ng sinaunang kutsilyong may sulat na pampasuwerte habang naghuhukay kasama ang kaniyang tiyuhin, at nakatuklas pa ang pangkat ng iba pang bagay.", "Nakakita ang tagapagsalaysay ng sinaunang kutsilyong may sulat na pampasuwerte habang naghuhukay kasama ang kaniyang tiyuhin, at nakatuklas pa ang pangkat ng iba pang bagay."),
        "characters": ["the narrator", "the narrator's uncle", "the student crew"], "setting": "A muddy archaeological dig site and the crew's tent.",
        "theme": ("A discovery may inspire further success, and shared finds can benefit the public.", "pagtuklas at pagbabahagi", "pagtuklas at pagbabahagi"),
        "events": ["A narrator joins an uncle and a contracted student crew searching for historical objects for a school foundation.", "After weeks without a find, the narrator digs through wet soil and mud.", "The narrator uncovers an old knife whose inscription promises good luck and keeps it in a tent.", "The next day the crew finds pots, jewelry, and weapons, which the uncle donates to a committee."],
        "sentences": [
            ("Inialay ng tagapagsalaysay ang kaniyang buhay sa pag-aaral ng mga nakaraang henerasyon at sumama siya sa tiyuhing naghahanap ng sinaunang bagay.", "Narator mendedikasikan hidupnya untuk mempelajari generasi masa lalu dan bergabung dengan pamannya mencari benda kuno."),
            ("Kumuha rin ang tiyuhin ng pangkat ng mga estudyanteng pumirma ng kontrata para magtrabaho sa proyektong pangkasaysayan ng paaralan.", "Pamannya juga merekrut sekelompok siswa yang menandatangani kontrak untuk bekerja pada proyek sejarah sekolah."),
            ("Lumipas ang halos isang buwan nang walang makita, kaya naghukay ang tagapagsalaysay sa patong-patong na basang lupa.", "Hampir sebulan berlalu tanpa temuan, sehingga narator menggali lapisan-lapisan tanah yang basah."),
            ("Sa putik, nakita niya ang lumang kutsilyong may makinis na hawakan at nakasulat na magdadala ito ng suwerte.", "Di lumpur, ia menemukan pisau tua dengan gagang halus dan tulisan bahwa pisau itu akan membawa keberuntungan."),
            ("Itinaas niya ito upang mabasa ang sulat at itinago sa tolda matapos sabihing maaari niya itong itago ng kaniyang tiyuhin.", "Ia mengangkatnya agar dapat membaca tulisan, lalu menyimpannya di tenda setelah pamannya mempersilakannya memilikinya."),
            ("Kinabukasan, marami pa silang natagpuang palayok, alahas at sandata; ipinagkaloob ng tiyuhin sa komite ang lahat ng ito.", "Keesokan harinya, mereka menemukan lebih banyak periuk, perhiasan, dan senjata; pamannya menyumbangkan semuanya kepada sebuah komite."),
        ],
        "vocabulary": [("henerasyon", "generasi", "pangngalan"), ("kontrata", "kontrak", "pangngalan"), ("patong-patong", "berlapis-lapis", "pang-uri"), ("putik", "lumpur", "pangngalan"), ("hawakan", "gagang", "pangngalan"), ("ipinagkaloob", "menyumbangkan", "pandiwa")],
        "expressions": [("walang makita", "tidak menemukan apa pun"), ("magdadala ito ng suwerte", "benda ini akan membawa keberuntungan")],
        "grammar": ("Ang nang + pandiwa ay nagtatakda ng oras ng pangyayari. Ipinakikita ng matapos + pandiwa na naganap muna ang isang kilos bago ang kasunod.", "Ketika + kata kerja menetapkan waktu peristiwa. Setelah + kata kerja menunjukkan bahwa satu tindakan terjadi sebelum tindakan berikutnya."),
        "questions": [
            (("Bakit nagtatrabaho ang pangkat ng estudyante?", "Mengapa kelompok siswa itu bekerja?"), [("Para maghanap ng lumang bagay para sa pundasyon ng paaralan", "Untuk mencari benda kuno bagi yayasan sejarah sekolah"), ("Para magtayo ng bahay", "Untuk membangun rumah"), ("Para mag-alaga ng kabayo", "Untuk merawat kuda")], 0, ("Naghahanap sila ng mga kayamanang pangkasaysayan para sa foundation ng paaralan.", "Mereka mencari benda bersejarah untuk yayasan sekolah.")),
            (("Ano ang unang natagpuan ng tagapagsalaysay sa putik?", "Apa yang pertama ditemukan narator di lumpur?"), [("Isang kutsilyo", "Sebuah pisau"), ("Mga palayok", "Beberapa periuk"), ("Isang kuwintas", "Sebuah kalung")], 0, ("Isang lumang kutsilyo ang nakita niya habang naghuhukay sa basang lupa.", "Ia menemukan pisau tua saat menggali tanah basah.")),
            (("Ano ang ginawa ng tiyuhin sa mga bagay na natagpuan kinabukasan?", "Apa yang dilakukan paman terhadap benda yang ditemukan esok hari?"), [("Ipinagbili niya ang mga ito", "Ia menjualnya"), ("Ipinagkaloob niya sa komite", "Ia menyumbangkannya kepada komite"), ("Itinago niya sa tolda", "Ia menyimpannya di tenda")], 1, ("Ipinagkaloob ng tiyuhin sa isang espesyal na komite ang mga palayok, alahas at sandata.", "Pamannya menyumbangkan periuk, perhiasan, dan senjata kepada sebuah komite khusus.")),
        ],
    },
    {
        "category": "Pagkakakilanlan at pagbabago", "summary": ("Nagpalit ng papel sina Sam at Prinsipe Bertram sa loob ng isang linggo at kapwa natuklasang mas pinahahalagahan nila ang dati nilang buhay.", "Sam dan Pangeran Bertram bertukar peran selama seminggu dan masing-masing menyadari bahwa mereka lebih menghargai kehidupan semula."),
        "characters": ["Sam", "Prince Bertram", "Sam's mother", "the royal servants"], "setting": "A palace kitchen and the prince's chamber.",
        "theme": ("Experiencing another person's responsibilities can change one's perspective.", "pag-unawa sa buhay ng iba", "memahami kehidupan orang lain"),
        "events": ["Sam accompanies his mother, a palace cook, but wanders away from the kitchen.", "He meets Prince Bertram, who looks just like him, and agrees to exchange places for a week.", "Sam finds royal life full of documents and a cold chamber, while Bertram struggles without servants.", "They resume their own lives and appreciate them more."],
        "sentences": [
            ("Isinama ni Sam ang kaniyang ina na nagluluto sa palasyo, ngunit lumabas siya ng kusina dahil nababagot.", "Sam ikut bersama ibunya yang bekerja sebagai juru masak istana, tetapi ia keluar dari dapur karena bosan."),
            ("Nagulat siya nang makatagpo ng batang kamukha niya at nalaman niyang Prinsipe Bertram pala ito.", "Ia terkejut bertemu anak yang sangat mirip dengannya dan mengetahui bahwa anak itu adalah Pangeran Bertram."),
            ("Nakiusap ang prinsipe na magpalit sila ng buhay nang isang linggo, at pumayag si Sam kahit nag-aalala siya.", "Pangeran memintanya bertukar kehidupan selama seminggu, dan Sam setuju meskipun merasa khawatir."),
            ("Napuno ang araw ni Sam ng pagpirma sa mga dokumento, at nilamig siya sa silid ng prinsipe tuwing gabi.", "Hari-hari Sam dipenuhi tanda tangan dokumen, dan ia kedinginan di kamar pangeran setiap malam."),
            ("Samantala, nahirapan si Bertram dahil hindi niya alam gawin ang mga bagay na dati'y ginagawa ng kaniyang mga tagapaglingkod.", "Sementara itu, Bertram kesulitan karena tidak tahu melakukan hal-hal yang biasanya dikerjakan para pelayannya."),
            ("Nang matapos ang isang linggo, bumalik sila sa kani-kanilang papel at kapwa mas nasiyahan sa dating pamumuhay.", "Setelah seminggu, mereka kembali ke peran masing-masing dan sama-sama lebih menikmati kehidupan semula."),
        ],
        "vocabulary": [("palasyo", "istana", "pangngalan"), ("kamukha", "mirip", "pang-uri"), ("magpalit", "bertukar", "pandiwa"), ("dokumento", "dokumen", "pangngalan"), ("nilamig", "kedinginan", "pandiwa"), ("tagapaglingkod", "pelayan", "pangngalan")],
        "expressions": [("magpalit ng buhay", "bertukar kehidupan"), ("bumalik sa kani-kanilang papel", "kembali ke peran masing-masing")],
        "grammar": ("Ang kahit ay nagpapakilala ng pagsalungat. Ang nang matapos ang isang linggo ay nag-uugnay ng pagtatapos sa sumunod na kilos.", "Meskipun memperkenalkan pertentangan. Setelah seminggu menghubungkan akhir suatu masa dengan tindakan selanjutnya."),
        "questions": [
            (("Sino si Bertram?", "Siapa Bertram?"), [("Anak ng kusinero", "Anak juru masak"), ("Prinsipe", "Pangeran"), ("Kapatid ni Sam", "Saudara Sam")], 1, ("Nagpakilala si Bertram bilang prinsipe matapos magulat si Sam sa pagkakahawig nila.", "Bertram memperkenalkan diri sebagai pangeran setelah Sam terkejut melihat kemiripan mereka.")),
            (("Ano ang naging mahirap para kay Sam sa palasyo?", "Apa yang sulit bagi Sam di istana?"), [("Pagpirma ng dokumento at malamig na silid", "Menandatangani dokumen dan kamar yang dingin"), ("Paghahanap ng kaniyang ina", "Mencari ibunya"), ("Pagtakbo sa burol", "Berlari ke bukit")], 0, ("Maraming dokumento ang pinirmahan ni Sam at nilamig siya sa silid ng prinsipe.", "Sam menandatangani banyak dokumen dan kedinginan di kamar pangeran.")),
            (("Ano ang natutuhan ng dalawang bata sa pagpapalit?", "Apa yang dipelajari kedua anak dari pertukaran itu?"), [("Mas masaya ang mamuhay sa ibang kaharian", "Lebih menyenangkan tinggal di kerajaan lain"), ("Hindi kailangan ang mga tagapaglingkod", "Pelayan tidak diperlukan"), ("Mas napahalagahan nila ang dati nilang buhay", "Mereka lebih menghargai kehidupan semula")], 2, ("Nakita nila ang hirap sa buhay ng isa't isa at kapwa mas nagustuhan ang sarili nilang kalagayan.", "Mereka melihat kesulitan dalam kehidupan satu sama lain dan lebih menyukai keadaan mereka sendiri.")),
        ],
    },
    {
        "category": "Kasaysayan at inobasyon", "summary": ("Ipinakilala ni Henry Ford ang Model T at pinabilis ang paggawa nito gamit ang magkakatulad na piyesa upang maging mas abot-kaya ang mga sasakyan.", "Henry Ford memperkenalkan Model T dan mempercepat pembuatannya dengan suku cadang seragam agar mobil lebih terjangkau."),
        "characters": ["Henry Ford", "his father", "Ford Motor Company workers", "car buyers"], "setting": "Detroit and the Ford Motor Company in the early 1900s.",
        "theme": ("Practical innovation can make useful technology available to more people.", "inobasyon at pagiging abot-kaya", "inovasi dan keterjangkauan"),
        "events": ["Henry Ford becomes a mechanic despite his father's wish that he run the family farm.", "He starts Ford Motor Company in 1903 and continues after its early struggles.", "He introduces the Model T in 1908 with interchangeable parts that speed assembly.", "Over 19 years he sells more than 15 million cars, showing that people will buy affordable vehicles."],
        "sentences": [
            ("Bata pa lang si Henry Ford ay interesado na siya sa mga karwahe, kaya nagtrabaho siyang mekaniko kahit nais ng ama niyang magpatakbo siya ng bukid.", "Sejak muda Henry Ford tertarik pada kereta kuda, sehingga ia bekerja sebagai mekanik meskipun ayahnya ingin ia mengelola pertanian."),
            ("Nang sumali siya sa kompanyang sasakyan sa Detroit, nais niyang gumawa ng kotse gamit ang mas kaunting paggawa at gastos.", "Saat bekerja di perusahaan mobil Detroit, ia ingin membuat mobil dengan lebih sedikit tenaga kerja dan biaya."),
            ("Itinatag niya ang Ford Motor Company noong 1903, bagaman hindi naging matagumpay agad ang negosyo.", "Ia mendirikan Ford Motor Company pada 1903, meskipun bisnis itu tidak langsung berhasil."),
            ("Noong 1908, pormal niyang ipinakilala ang Model T na may magkakatulad na disenyong madaling buuin.", "Pada 1908, ia secara resmi memperkenalkan Model T dengan desain seragam yang mudah dirakit."),
            ("Maaaring magkabit ang mga manggagawa ng magkakaibang piyesa, kaya nabubuo ang isang kotse sa loob lamang ng 93 minuto.", "Para pekerja dapat memasang bagian-bagian yang berbeda, sehingga satu mobil dapat dirakit hanya dalam 93 menit."),
            ("Mahigit 15 milyong Model T ang naibenta niya sa loob ng 19 taon, at ipinakitang bibili ang tao kapag abot-kaya ang presyo.", "Ia menjual lebih dari 15 juta Model T dalam 19 tahun, membuktikan orang akan membeli mobil jika harganya terjangkau."),
        ],
        "vocabulary": [("karwahe", "kereta kuda", "pangngalan"), ("mekaniko", "mekanik", "pangngalan"), ("paggawa", "tenaga kerja", "pangngalan"), ("itinatag", "mendirikan", "pandiwa"), ("piyesa", "suku cadang", "pangngalan"), ("abot-kaya", "terjangkau", "pang-uri")],
        "expressions": [("hindi naging matagumpay agad", "tidak langsung berhasil"), ("sa loob lamang ng 93 minuto", "hanya dalam 93 menit")],
        "grammar": ("Ginagamit ang kahit upang magpakita ng pagsalungat. Ang noong ay tumutukoy sa panahong naganap ang kilos.", "Meskipun menunjukkan pertentangan. Pada menandai waktu terjadinya tindakan."),
        "questions": [
            (("Anong sasakyan ang ipinakilala ni Ford noong 1908?", "Kendaraan apa yang diperkenalkan Ford pada 1908?"), [("Model T", "Model T"), ("Isang karwahe", "Kereta kuda"), ("Isang motorsiklo", "Sepeda motor")], 0, ("Pormal na ipinakilala ni Ford ang Model T noong 1908.", "Ford secara resmi memperkenalkan Model T pada 1908.")),
            (("Ano ang pakinabang ng magkakatulad na piyesa?", "Apa manfaat suku cadang yang seragam?"), [("Mas tumagal ang paglalakbay", "Perjalanan lebih lama"), ("Mas mabilis buuin ang mga kotse", "Mobil lebih cepat dirakit"), ("Hindi na kailangan ang manggagawa", "Pekerja tidak lagi diperlukan")], 1, ("Nakatulong ang mga bahaging magkakatugma upang mabuo ang kotse sa 93 minuto.", "Bagian yang seragam membantu merakit mobil dalam 93 menit.")),
            (("Ano ang ipinakita ng dami ng Model T na naibenta?", "Apa yang ditunjukkan oleh jumlah Model T yang terjual?"), [("Ayaw ng tao ng kotse", "Orang tidak menginginkan mobil"), ("Bumibili ang tao kapag abot-kaya ang presyo", "Orang membeli mobil jika harganya terjangkau"), ("Mas gusto ng tao ang karwahe", "Orang lebih menyukai kereta kuda")], 1, ("Maraming bumili ng kotse kapag mababa ang presyo nito.", "Banyak orang membeli mobil ketika harganya cukup rendah.")),
        ],
    },
    {
        "category": "Kaligayahan at pagkamalikhain", "summary": ("Natuklasan ng malungkot na pari na makasusumpong siya ng saya sa pagguhit, pagsusulat, paghahalaman, paggawa ng jam at pagpipinta.", "Pendeta yang sedih menemukan kegembiraan melalui menggambar, menulis, berkebun, membuat selai, dan melukis."),
        "characters": ["the young priest", "the wise monks"], "setting": "A monastery and the priest's home and garden.",
        "theme": ("Joy can grow when people make time for activities they love.", "paghahanap ng saya sa mga hilig", "menemukan kegembiraan melalui kegiatan yang disukai"),
        "events": ["A capable young priest feels unhappy and asks a group of monks for advice.", "The monks tell him to investigate the parts of his life he loves.", "He draws cartoons, keeps a diary, plants grain, makes berry jam, and paints his ceiling.", "He realizes happiness is easier to find when he does things he enjoys."],
        "sentences": [
            ("Malungkot ang isang batang pari kahit mahusay siya sa kaniyang propesyon at dumalaw siya sa pangkat ng matatandang monghe.", "Seorang pendeta muda merasa sedih meskipun mahir dalam pekerjaannya, lalu mengunjungi sekelompok rahib tua."),
            ("Tinanong siya ng mga monghe kung ano ang problema, at sinabi niyang hindi niya alam kung paano sumaya.", "Para rahib bertanya apa masalahnya, dan ia berkata tidak tahu bagaimana menjadi bahagia."),
            ("Pinayuhan siya ng isa sa kanila na siyasatin ang mga bagay sa buhay na talagang gusto niya.", "Salah satu rahib menasihatinya untuk menyelidiki hal-hal dalam hidup yang benar-benar ia sukai."),
            ("Kinabukasan, gumuhit siya ng mga kartun, nagsimula ng talaarawan, at nagtanim ng mga butil.", "Keesokan harinya, ia menggambar kartun, mulai menulis buku harian, dan menanam biji-bijian."),
            ("Gumawa rin siya ng jam mula sa mga berry, gumawa ng etiketa para sa mga garapon, at nagpinta ng kisame.", "Ia juga membuat selai dari buah beri, menyiapkan label untuk stoples, dan mengecat langit-langit."),
            ("Napagtanto ng pari na hindi pala mahirap sumaya kapag ginagawa niya ang mga bagay na kinagigiliwan niya.", "Pendeta itu menyadari bahwa kebahagiaan ternyata tidak sulit ditemukan ketika ia melakukan hal-hal yang disukainya."),
        ],
        "vocabulary": [("pari", "pendeta", "pangngalan"), ("monghe", "rahib", "pangngalan"), ("siyasatin", "menyelidiki", "pandiwa"), ("talaarawan", "buku harian", "pangngalan"), ("butil", "biji-bijian", "pangngalan"), ("kinagigiliwan", "disukai", "pandiwa")],
        "expressions": [("ano ang problema", "apa masalahnya"), ("mga bagay na kinagigiliwan niya", "hal-hal yang ia sukai")],
        "grammar": ("Ginagamit ang kahit upang magpahayag ng magkasalungat na katotohanan. Ang kapag + pandiwa ay nagpapakilala ng kundisyon o pagkakataon.", "Meskipun menyatakan dua fakta yang berlawanan. Ketika + kata kerja memperkenalkan kondisi atau kesempatan."),
        "questions": [
            (("Sino ang nilapitan ng pari para humingi ng payo?", "Kepada siapa pendeta meminta nasihat?"), [("Sa mga monghe", "Kepada para rahib"), ("Sa mga magsasaka", "Kepada para petani"), ("Sa kaniyang pamilya", "Kepada keluarganya")], 0, ("Dumalaw siya sa pangkat ng mga pantas na monghe.", "Ia mengunjungi sekelompok rahib bijaksana.")),
            (("Ano ang ipinayo ng mga monghe?", "Apa nasihat para rahib?"), [("Umalis sa propesyon", "Meninggalkan pekerjaannya"), ("Hanapin ang mga bagay na gusto niya", "Mencari kegiatan yang ia sukai"), ("Itigil ang pagtatanim", "Berhenti menanam")], 1, ("Sinabi nilang siyasatin niya kung anong mga bahagi ng buhay ang minamahal niya.", "Mereka menyuruhnya mencari tahu bagian hidup apa yang ia sukai.")),
            (("Alin ang ginawa ng pari matapos makipag-usap sa mga monghe?", "Apa yang dilakukan pendeta setelah berbicara dengan para rahib?"), [("Gumuhit, nagsulat at nagtanim", "Menggambar, menulis, dan menanam"), ("Naglayag sa ibang bansa", "Berlayar ke luar negeri"), ("Nagbukas ng restawran", "Membuka restoran")], 0, ("Sinimulan niya ang mga malikhaing gawain at paghahalaman na gusto niya.", "Ia mulai melakukan kegiatan kreatif dan berkebun yang disukainya.")),
        ],
    },
    {
        "category": "Pagtanggap at pagkakaibigan", "summary": ("Inampon ni Mrs. May ang batang berdeng dayuhan at natutuhan ng bayan na tanggapin siya; nagbago ang kulay niya matapos kumain ng pagkaing inihanda sa bahay.", "Mrs. May mengadopsi anak perempuan berkulit hijau dari dunia lain dan penduduk menerimanya; warnanya berubah setelah ia makan masakan rumah."),
        "characters": ["Mrs. May", "the green girl", "the townspeople", "the judge"], "setting": "A small town, a stream, and a home near the woods.",
        "theme": ("Kindness and patience help people welcome someone unfamiliar.", "pagtanggap at kabaitan", "penerimaan dan kebaikan"),
        "events": ["Townspeople find a frightened green-skinned girl by a stream and suspect her intentions.", "Mrs. May asks them not to reject the girl and adopts her despite the judge's doubts.", "The girl communicates with drawings and explains that her people live in tree nests and eat leaves.", "Mrs. May gives her home-cooked food, her skin loses its green color, and the town welcomes her."],
        "sentences": [
            ("Natagpuan ng mga tao sa isang maliit na bayan ang batang babaeng may berdeng balat sa tabi ng sapa.", "Penduduk sebuah kota kecil menemukan seorang anak perempuan berkulit hijau di tepi sungai kecil."),
            ("Nangamba sila na masama ang dahilan ng pagdating niya, ngunit naawa si Mrs. May nang makita siyang natatakot.", "Mereka khawatir ia datang dengan niat buruk, tetapi Mrs. May iba merasa iba ketika melihatnya ketakutan."),
            ("Hiniling ng matandang babae sa hukom na huwag tanggihan ang bata at nangakong aamponin niya ito.", "Perempuan tua itu meminta hakim agar tidak menolak anak tersebut dan berjanji akan mengadopsinya."),
            ("Hindi nauunawaan ni Mrs. May ang wika ng bata, kaya gumamit ito ng mga guhit upang magpaliwanag.", "Mrs. May tidak memahami bahasa anak itu, sehingga anak tersebut memakai gambar untuk menjelaskan."),
            ("Ikinuwento ng bata na galing siya sa lugar lampas sa araw kung saan nakatira ang mga tao sa pugad sa puno at kumakain ng dahon.", "Anak itu bercerita bahwa ia berasal dari tempat jauh di balik matahari, tempat orang tinggal di sarang pohon dan makan daun."),
            ("Pinakain siya ni Mrs. May ng lutong-bahay, nawala ang berdeng kulay ng kaniyang balat, at malugod siyang tinanggap ng buong bayan.", "Mrs. May memberinya masakan rumah, warna hijau kulitnya menghilang, dan seluruh kota menyambutnya dengan hangat."),
        ],
        "vocabulary": [("sapa", "sungai kecil", "pangngalan"), ("nangamba", "khawatir", "pandiwa"), ("tanggihan", "menolak", "pandiwa"), ("aamponin", "mengadopsi", "pandiwa"), ("guhit", "gambar", "pangngalan"), ("lutong-bahay", "masakan rumah", "pangngalan")],
        "expressions": [("huwag tanggihan ang bata", "jangan menolak anak itu"), ("malugod siyang tinanggap", "ia disambut dengan hangat")],
        "grammar": ("Ginagamit ang kaya upang ilahad ang paraang naging posible ang kasunod na kilos. Ang na + pandiwa ay maaaring magpahiwatig ng naganap nang pagbabago.", "Sehingga menjelaskan cara tindakan berikutnya dapat dilakukan. Kata kerja dengan awalan ter- dapat menandai perubahan yang telah terjadi."),
        "questions": [
            (("Sino ang nag-alok na mag-ampon sa berdeng bata?", "Siapa yang menawarkan diri mengadopsi anak berkulit hijau?"), [("Ang hukom", "Hakim"), ("Si Mrs. May", "Mrs. May"), ("Isang mandaragat", "Seorang pelaut")], 1, ("Hiniling ni Mrs. May na huwag tanggihan ang bata at siya ang mag-aampon dito.", "Mrs. May meminta agar anak itu tidak ditolak dan ia akan mengadopsinya.")),
            (("Paano nakipag-usap ang bata kay Mrs. May?", "Bagaimana anak itu berkomunikasi dengan Mrs. May?"), [("Sa pamamagitan ng mga guhit", "Dengan gambar"), ("Sa pamamagitan ng kanta", "Dengan lagu"), ("Sa pamamagitan ng sulat", "Dengan surat")], 0, ("Gumuhit ang bata upang ipakita ang ibig niyang sabihin.", "Anak itu menggambar untuk menjelaskan maksudnya.")),
            (("Bakit nagbago ang kulay ng balat ng bata?", "Mengapa warna kulit anak itu berubah?"), [("Nalaglag ang kaniyang costume", "Kostumnya terlepas"), ("Naligo siya sa sapa", "Ia mandi di sungai"), ("Kumain siya ng lutong-bahay sa halip na dahon", "Ia makan masakan rumah, bukan hanya daun")], 2, ("Pinakain siya ni Mrs. May ng lutong-bahay at hindi na siya kumain lamang ng berdeng dahon.", "Mrs. May memberinya masakan rumah dan ia tidak lagi hanya makan daun hijau.")),
        ],
    },
    {
        "category": "Talambuhay at pagpupunyagi", "summary": ("Naranasan ni Albert Einstein ang kahirapan at pagtanggi bago makilala ang kaniyang mga paliwanag tungkol sa mga bituin at atomo; nagpatuloy siya sa pagsasaliksik.", "Albert Einstein mengalami kemiskinan dan penolakan sebelum penjelasannya tentang bintang dan atom diakui; ia terus meneliti."),
        "characters": ["Albert Einstein", "Einstein's family", "other scientists"], "setting": "Germany, Italy, Switzerland, and Einstein's scientific career.",
        "theme": ("Persistence through hardship can lead to recognition and meaningful work.", "pagtitiyaga sa gitna ng hirap", "ketekunan menghadapi kesulitan"),
        "events": ["Einstein is interested in mathematics and statistics from elementary school.", "His family loses its income and moves from Germany to Italy; he later studies in Switzerland.", "Other scientists initially reject his work, but recognition grows over time.", "He explains the size of stars and motion of atoms, invents a refrigerator, and keeps working."],
        "sentences": [
            ("Isinilang si Albert Einstein sa Germany at interesado na siya sa matematika at estadistika noong nasa elementarya pa.", "Albert Einstein lahir di Jerman dan sudah tertarik pada matematika serta statistik saat masih sekolah dasar."),
            ("Nang mawalan ng trabaho ang kaniyang ama, nabuhay sa kahirapan ang pamilya at lumipat sila mula Germany patungong Italy.", "Ketika ayahnya kehilangan pekerjaan, keluarganya hidup dalam kemiskinan dan pindah dari Jerman ke Italia."),
            ("Nagtapos siya ng mataas na paaralan at nag-aral sa kolehiyo sa Switzerland bago magsulat tungkol sa agham.", "Ia menyelesaikan sekolah menengah dan kuliah di Swiss sebelum menulis tentang sains."),
            ("Noong una, hindi sinang-ayunan ng ibang siyentipiko ang kaniyang mga ideya at inakala nilang bigo siya.", "Awalnya, ilmuwan lain tidak menyetujui gagasannya dan mengira ia gagal."),
            ("Unti-unti siyang kinilala dahil naipaliwanag niya ang tinatayang laki ng mga bituin at galaw ng mga atomo.", "Pengakuan datang bertahap karena ia menjelaskan perkiraan ukuran bintang dan gerakan atom."),
            ("Gumawa rin siya ng makinang nagpapalamig ng pagkain at patuloy na nagtrabaho hanggang sa huling bahagi ng buhay.", "Ia juga membuat mesin untuk mendinginkan makanan dan terus bekerja hingga usia lanjut."),
        ],
        "vocabulary": [("estadistika", "statistik", "pangngalan"), ("kahirapan", "kemiskinan", "pangngalan"), ("siyentipiko", "ilmuwan", "pangngalan"), ("bigo", "gagal", "pang-uri"), ("unti-unti", "bertahap", "pang-abay"), ("nagpapalamig", "mendinginkan", "pandiwa")],
        "expressions": [("nabuhay sa kahirapan", "hidup dalam kemiskinan"), ("unti-unti siyang kinilala", "pengakuan datang bertahap")],
        "grammar": ("Ang bago + pandiwa ay nagpapakita ng pagkakasunod-sunod. Ang dahil ay nag-uugnay ng dahilan at bunga.", "Sebelum + kata kerja menunjukkan urutan. Karena menghubungkan alasan dan akibat."),
        "questions": [
            (("Saan lumipat ang pamilya ni Einstein mula Germany?", "Ke mana keluarga Einstein pindah dari Jerman?"), [("Sa Italy", "Ke Italia"), ("Sa Greece", "Ke Yunani"), ("Sa Egypt", "Ke Mesir")], 0, ("Lumipat sila sa Italy matapos mawalan ng trabaho ang ama niya.", "Mereka pindah ke Italia setelah ayahnya kehilangan pekerjaan.")),
            (("Bakit hindi agad kinilala ang gawa ni Einstein?", "Mengapa karya Einstein tidak segera diakui?"), [("Hindi siya nagsulat tungkol sa agham", "Ia tidak menulis tentang sains"), ("Hindi sinang-ayunan ng ibang siyentipiko ang kaniyang ideya", "Ilmuwan lain tidak menyetujui gagasannya"), ("Hindi siya nakapag-aral", "Ia tidak bersekolah")], 1, ("Una siyang itinuring ng ibang siyentipiko na bigo at mali ang mga ideya.", "Ilmuwan lain awalnya menganggapnya gagal dan gagasannya keliru.")),
            (("Anong dalawang paksa ang ipinaliwanag niya sa kaniyang pananaliksik?", "Dua hal apa yang ia jelaskan dalam penelitiannya?"), [("Laki ng bituin at galaw ng atomo", "Ukuran bintang dan gerakan atom"), ("Pag-ikot ng gulong at tela", "Putaran roda dan kain"), ("Tunog ng ibon at hangin", "Suara burung dan angin")], 0, ("Ipinaliwanag niya ang tinatayang laki ng bituin at ang galaw ng napakaliit na atomo.", "Ia menjelaskan perkiraan ukuran bintang dan gerakan atom yang sangat kecil.")),
        ],
    },
    {
        "category": "Pangarap at katapangan", "summary": ("Iniwan ni Jeremy ang trabaho sa minahan matapos siyang iligtas ng mga kasama at hinikayat ng isang anghel na pag-aralan ang paglalakbay sa kalawakan.", "Jeremy meninggalkan pekerjaan tambang setelah diselamatkan rekan-rekannya dan didorong malaikat untuk mengejar perjalanan ke luar angkasa."),
        "characters": ["Jeremy", "the miners", "the angel"], "setting": "An underground mine, an open field, and a space mission.",
        "theme": ("A frightening turning point can give someone courage to pursue a long-held dream.", "tapang na abutin ang pangarap", "keberanian mengejar impian"),
        "events": ["Jeremy works as a miner but spends nights gazing at stars through a telescope.", "A flood traps him underground, where he hears an angel tell him not to return to mining.", "Other miners rescue him, and he studies for two years to become an astronaut.", "He joins a space mission, sees satellites and an angel, and thanks it."],
        "sentences": [
            ("Galing sa pamilya ng mga minero si Jeremy at naghuhukay siya ng mineral at hiyas sa ilalim ng lupa.", "Jeremy berasal dari keluarga penambang dan menggali mineral serta permata di bawah tanah."),
            ("Tuwing gabi, nakahiga siya sa parang at tumitingin sa mga bituin gamit ang teleskopyo, habang nangangarap bumiyahe sa kalawakan.", "Setiap malam, ia berbaring di padang dan mengamati bintang dengan teleskop sambil bermimpi pergi ke luar angkasa."),
            ("Isang araw, bumaha sa minahan at kumapit siya sa kahoy upang hindi lumubog sa madilim na tubig.", "Suatu hari, banjir masuk ke tambang dan ia berpegangan pada kayu agar tidak tenggelam dalam air gelap."),
            ("May tinig na nagsabing anghel ito at hinikayat siyang huwag nang bumalik sa ilalim ng lupa kundi abutin ang kaniyang pangarap.", "Sebuah suara mengaku sebagai malaikat dan mendorongnya agar tidak kembali ke bawah tanah, melainkan mengejar impiannya."),
            ("Nakaligtas si Jeremy nang dumating ang mga minero, at dalawang taon siyang nag-aral upang maging astronaut.", "Jeremy selamat ketika para penambang datang, lalu belajar selama dua tahun untuk menjadi astronaut."),
            ("Nang sumali siya sa misyon, nakakita siya ng mga satelayt at ng nakangiting anghel sa labas ng sasakyang pangkalawakan.", "Saat mengikuti misi, ia melihat satelit dan malaikat tersenyum di luar pesawat ruang angkasa."),
        ],
        "vocabulary": [("minero", "penambang", "pangngalan"), ("mineral", "mineral", "pangngalan"), ("teleskopyo", "teleskop", "pangngalan"), ("bumaha", "banjir", "pandiwa"), ("lumubog", "tenggelam", "pandiwa"), ("astronaut", "astronaut", "pangngalan")],
        "expressions": [("abutin ang pangarap", "mengejar impian"), ("huwag nang bumalik", "jangan kembali lagi")],
        "grammar": ("Ginagamit ang upang + pandiwa upang ipahayag ang layunin. Ang nang dumating ay nagpapakilala ng oras ng pagbabago.", "Untuk + kata kerja menyatakan tujuan. Saat tiba memperkenalkan waktu perubahan."),
        "questions": [
            (("Ano ang trabaho ni Jeremy bago siya maging astronaut?", "Apa pekerjaan Jeremy sebelum menjadi astronaut?"), [("Minero", "Penambang"), ("Mangingisda", "Nelayan"), ("Doktor", "Dokter")], 0, ("Nagtatrabaho si Jeremy sa minahan kasama ng kaniyang pamilya.", "Jeremy bekerja di tambang bersama keluarganya.")),
            (("Ano ang nangyari sa minahan?", "Apa yang terjadi di tambang?"), [("Nagkaroon ng baha", "Terjadi banjir"), ("Nagkaroon ng sunog", "Terjadi kebakaran"), ("Gumuho ang teleskopyo", "Teleskop runtuh")], 0, ("Bumuhos ang tubig sa minahan at muntik malunod si Jeremy.", "Air mengalir masuk ke tambang dan Jeremy hampir tenggelam.")),
            (("Ano ang ginawa ni Jeremy matapos siyang mailigtas?", "Apa yang dilakukan Jeremy setelah diselamatkan?"), [("Bumalik agad sa minahan", "Segera kembali ke tambang"), ("Nag-aral upang maging astronaut", "Belajar untuk menjadi astronaut"), ("Nagtayo ng teleskopyo", "Membangun teleskop")], 1, ("Dalawang taon siyang nag-aral at sumali sa isang misyon sa kalawakan.", "Ia belajar selama dua tahun dan bergabung dalam misi luar angkasa.")),
        ],
    },
    {
        "category": "Pagtutulungan at pagdiriwang", "summary": ("Hindi natuloy nang maayos ang paligsahan ng mga hayop dahil sa aksidente, pagtatangkang magnakaw at sunog, ngunit nag-enjoy sila sa pagdiriwang.", "Lomba para hewan tidak berjalan lancar karena kecelakaan, pencurian, dan kebakaran, tetapi mereka menikmati festival."),
        "characters": ["the farm animals", "the puppy", "the duck", "the horse", "the pig", "the journalist"], "setting": "A farmyard between a barn and the farmer's garage.",
        "theme": ("Shared fun and helping one another can matter more than winning.", "pagtutulungan ang mahalaga", "kerja sama lebih penting"),
        "events": ["Farm animals plan a race whose winner would receive apples.", "They repair an unstable cart, and a puppy knocks the apples over.", "A duck tries to steal apples, then a fire in the barn interrupts the race again.", "A journalist records the animals' views; the pig says that having fun mattered most."],
        "sentences": [
            ("Nagdaos ng paligsahan sa bakuran ang mga hayop sa bukid, at mansanas ang gantimpala sa mananalo sa karera.", "Para hewan mengadakan perlombaan di halaman, dengan apel sebagai hadiah bagi pemenang."),
            ("Malayo ang kamalig sa garahe ng magsasaka, at kinailangan munang kumpunihin ang hindi matatag na kariton.", "Lumbung dan garasi petani berjauhan, dan mereka harus memperbaiki kereta yang tidak stabil terlebih dahulu."),
            ("Naitumba ng tuta ang mga mansanas kaya nadulas ang mga hayop at tumulong silang maglinis.", "Anak anjing menjatuhkan apel sehingga hewan-hewan tergelincir dan mereka membantu membersihkan."),
            ("Nang magsimula muli ang karera, sinubukan ng pato na nakawin ang mga mansanas at nagtalo sila tungkol sa pag-aresto rito.", "Saat lomba dimulai lagi, bebek mencoba mencuri apel dan mereka berdebat apakah ia dapat ditangkap."),
            ("Muli silang nahinto nang tumunog ang alarma dahil may sunog sa kamalig, kaya nagdala sila ng mga timba ng tubig.", "Mereka kembali berhenti ketika alarm berbunyi karena lumbung terbakar, sehingga mereka membawa ember berisi air."),
            ("Isinulat ng mamamahayag ang kuwento ng araw na iyon; sinabi ng baboy na mas mahalaga ang pagsasaya kaysa panalo.", "Wartawan menulis kisah hari itu; babi berkata bahwa bersenang-senang lebih penting daripada menang."),
        ],
        "vocabulary": [("bakuran", "halaman", "pangngalan"), ("gantimpala", "hadiah", "pangngalan"), ("kamalig", "lumbung", "pangngalan"), ("kariton", "kereta", "pangngalan"), ("nadulas", "tergelincir", "pandiwa"), ("alarma", "alarm", "pangngalan")],
        "expressions": [("muling nahinto", "kembali berhenti"), ("mas mahalaga ang pagsasaya", "bersenang-senang lebih penting")],
        "grammar": ("Ginagamit ang kaya upang ipakita ang bunga ng pangyayari. Ang nang magsimula muli ay nag-uugnay ng mga kilos ayon sa pagkakasunod-sunod.", "Sehingga menunjukkan akibat suatu peristiwa. Saat dimulai kembali mengurutkan tindakan."),
        "questions": [
            (("Ano ang gantimpala sa karera?", "Apa hadiah lomba?"), [("Isang supot ng mansanas", "Sekantong apel"), ("Mga perlas", "Mutiara"), ("Isang bangka", "Perahu")], 0, ("Supot na puno ng mansanas ang inilaan para sa mananalo.", "Sekantong penuh apel disediakan bagi pemenang.")),
            (("Ano ang nangyari sa kamalig na muling nagpahinto sa karera?", "Apa yang terjadi di lumbung sehingga lomba kembali dihentikan?"), [("May sunog", "Terjadi kebakaran"), ("Nawalan ito ng bubong", "Atapnya hilang"), ("Pumasok ang baha", "Air banjir masuk")], 0, ("Tumunog ang alarma dahil nasusunog ang kamalig at kailangan nila itong apulahin.", "Alarm berbunyi karena lumbung terbakar dan mereka perlu memadamkannya.")),
            (("Ano ang pinakamahalaga para sa baboy?", "Apa yang terpenting bagi babi?"), [("Maging una sa karera", "Menjadi yang pertama dalam lomba"), ("Makakuha ng mansanas", "Mendapatkan apel"), ("Magsaya ang lahat", "Semua bersenang-senang")], 2, ("Sinabi ng baboy na mahalaga ang kasiyahan kahit mahirap ang paligsahan.", "Babi mengatakan bahwa kesenangan penting meskipun perlombaan sulit.")),
        ],
    },
])

STORIES.extend([
    {
        "category": "Kayamanan at pagkamapagbigay", "summary": ("Palihim na kumuha ng ginto ang tagapagtayo mula sa libingan ng hari at ibinigay ito sa mahihirap, ngunit nahuli siya ng bantay matapos masugatan.", "Diam-diam pembangun mengambil emas dari makam raja untuk diberikan kepada kaum miskin, tetapi penjaga menangkapnya setelah ia terluka."),
        "characters": ["the king", "the tomb builder", "the guard", "the poor"], "setting": "A royal tomb built with a marked stone in its roof.",
        "theme": ("A generous motive does not erase the consequences of stealing.", "kabutihang-loob at bunga ng pagnanakaw", "niat baik dan akibat mencuri"),
        "events": ["A king builds a tomb to keep his gold after death.", "The builder marks a light roof stone and secretly enters the tomb night after night to take gold for the poor.", "The king notices the shortage and hides a guard, who wounds the builder.", "The guard follows blood drops and captures the builder, who says he gave away all the gold."],
        "sentences": [
            ("Nang maging hari ang isang lalaki, nagtayo siya ng malaking libingan upang maisama roon ang kaniyang kayamanan pagkamatay niya.", "Seorang lelaki menjadi raja dan membangun makam besar agar hartanya ikut terkubur setelah ia meninggal."),
            ("Minarkahan ng tagapagtayo ang isang magaan na batong artipisyal sa bubong upang matukoy niya iyon sa gabi.", "Pembangun menandai sebuah batu buatan yang ringan di atap agar dapat mengenalinya pada malam hari."),
            ("Gamit ang kadena, pumapasok siya sa libingan at kumukuha ng ginto upang ibigay sa mahihirap.", "Dengan rantai, ia masuk ke makam dan mengambil emas untuk diberikan kepada kaum miskin."),
            ("Napansin ng hari na kumakaunti ang ginto kaya naglagay siya ng bantay sa loob ng libingan.", "Raja menyadari emasnya berkurang, sehingga ia menempatkan penjaga di dalam makam."),
            ("Nang pumasok muli ang tagapagtayo, sinugatan siya ng bantay; sinundan nito ang mga patak ng dugo hanggang mahuli siya.", "Ketika pembangun masuk lagi, penjaga melukainya; penjaga mengikuti tetesan darah sampai menangkapnya."),
            ("Nang gumaling siya, ipinaliwanag niyang wala siyang itinira at lahat ng ginto ay ipinamahagi niya sa mga dukha.", "Setelah sembuh, ia menjelaskan bahwa ia tidak menyimpan apa pun dan telah membagikan semua emas kepada orang miskin."),
        ],
        "vocabulary": [("libingan", "makam", "pangngalan"), ("kayamanan", "harta", "pangngalan"), ("minarkahan", "menandai", "pandiwa"), ("kadena", "rantai", "pangngalan"), ("sinugatan", "melukai", "pandiwa"), ("patak", "tetesan", "pangngalan")],
        "expressions": [("kumukuha ng ginto", "mengambil emas"), ("ipinamahagi sa mga dukha", "membagikan kepada orang miskin")],
        "grammar": ("Ang upang + pandiwa ay nagpapahayag ng layunin. Ang hanggang ay nagtatakda ng hangganan ng kilos o panahon.", "Untuk + kata kerja menyatakan tujuan. Sampai menunjukkan batas tindakan atau waktu."),
        "questions": [
            (("Bakit nagtayo ng libingan ang hari?", "Mengapa raja membangun makam?"), [("Upang mailibing doon ang ginto niya", "Agar emasnya dapat dikubur di sana"), ("Upang ikulong ang tagapagtayo", "Untuk memenjarakan pembangun"), ("Upang gawing paaralan", "Untuk menjadikannya sekolah")], 0, ("Nais ng hari na makasama niya sa libingan ang kaniyang kayamanan.", "Raja ingin hartanya ikut berada di dalam makam.")),
            (("Paano pumapasok ang tagapagtayo sa libingan?", "Bagaimana pembangun masuk ke makam?"), [("Sa pintuan ng bantay", "Melalui pintu penjaga"), ("Sa pamamagitan ng minarkahang bato sa bubong", "Melalui batu bertanda di atap"), ("Sa ilalim ng ilog", "Di bawah sungai")], 1, ("Itinataas niya ang magaan na batong minarkahan niya at gumagamit ng kadena.", "Ia mengangkat batu ringan yang ditandainya dan menggunakan rantai.")),
            (("Ano ang ginawa ng tagapagtayo sa ginto?", "Apa yang dilakukan pembangun terhadap emas?"), [("Itinago niya sa kaniyang bahay", "Menyimpannya di rumah"), ("Ipinambili ng barko", "Membeli kapal"), ("Ibinigay sa mahihirap", "Memberikannya kepada kaum miskin")], 2, ("Sinabi niyang ipinamahagi niya sa mahihirap ang lahat ng ginto.", "Ia mengatakan telah membagikan semua emas kepada kaum miskin.")),
        ],
    },
    {
        "category": "Pamilya at pagpapahalaga sa buhay", "summary": ("Habang nagpapagaling sa ospital, napagtanto ng abalang doktor na napabayaan niya ang anak at nagpasiyang magpahinga at makasama ito.", "Saat pulih di rumah sakit, dokter yang sibuk menyadari bahwa ia mengabaikan putranya, lalu memutuskan beristirahat dan menghabiskan waktu bersama."),
        "characters": ["Dr. James Fry", "Steve", "the nurse"], "setting": "A hospital room and James's home after his injury.",
        "theme": ("Work should leave room for relationships and everyday joys.", "pamilya at oras para sa sarili", "keluarga dan waktu untuk diri sendiri"),
        "events": ["Busy doctor James rarely sees his son Steve.", "James slips on liquid and falls on broken glass, injuring himself.", "Steve visits, shares a movie and reading, and James notices small pleasures again.", "James regrets not spending enough time with Steve and chooses to go home and rest."],
        "sentences": [
            ("Doktor si James Fry na abalang tumutulong sa mga taong may kapansanan sa pamamagitan ng mga operasyon at sumusulat para sa isang medikal na pahayagan.", "James Fry adalah dokter sibuk yang membantu penyandang disabilitas dan menulis untuk jurnal medis."),
            ("Bihira niyang makita ang anak na si Steve dahil palagi siyang nag-oopera at nag-aaral ng mga tala ng pasyente.", "Ia jarang bertemu putranya, Steve, karena selalu melakukan operasi dan memeriksa catatan pasien."),
            ("Isang araw, nadulas siya sa likido sa sahig at nasugatan nang bumagsak sa basag na tubong salamin.", "Suatu hari, ia terpeleset di lantai yang basah dan terluka saat jatuh menimpa tabung kaca yang pecah."),
            ("Dumalaw si Steve sa ospital, nagmungkahi ng pelikula, at nag-iwan ng kuwentong kathang-isip na babasahin.", "Steve mengunjunginya di rumah sakit, mengusulkan menonton film, dan meninggalkan bacaan fiksi."),
            ("Muling napansin ni James ang sarap ng pagkain at ang saya ng pakikipag-usap sa anak habang dahan-dahang ngumunguya.", "James kembali memperhatikan nikmatnya makanan dan kesenangan berbicara dengan putranya sambil mengunyah perlahan."),
            ("Pinagsisihan niyang kulang ang panahong ibinigay niya kay Steve, kaya umuwi siyang magpapahinga at manonood sila ng pelikula.", "Ia menyesal tidak cukup meluangkan waktu untuk Steve, lalu pulang untuk beristirahat dan menonton film bersama."),
        ],
        "vocabulary": [("may kapansanan", "penyandang disabilitas", "parirala"), ("operasyon", "operasi", "pangngalan"), ("nadulas", "terpeleset", "pandiwa"), ("basag", "pecah", "pang-uri"), ("kathang-isip", "fiksi", "pangngalan"), ("pinagsisihan", "menyesal", "pandiwa")],
        "expressions": [("bihira niyang makita", "ia jarang bertemu"), ("kulang ang panahong ibinigay", "tidak cukup meluangkan waktu")],
        "grammar": ("Ang dahil ay nagpapaliwanag ng sanhi. Ang kaya ay nagpapakita ng naging pasiya o bunga.", "Karena menjelaskan sebab. Maka menunjukkan keputusan atau akibat."),
        "questions": [
            (("Bakit bihirang makita ni James si Steve?", "Mengapa James jarang bertemu Steve?"), [("Nasa ibang bansa si Steve", "Steve tinggal di luar negeri"), ("Abala si James sa trabaho", "James sibuk bekerja"), ("Nasa paaralan si James", "James berada di sekolah")], 1, ("Abala si James bilang doktor at kaunti ang panahong inilalaan niya sa anak.", "James sibuk sebagai dokter dan hanya sedikit meluangkan waktu untuk putranya.")),
            (("Paano nasugatan si James?", "Bagaimana James terluka?"), [("Nadulas siya at bumagsak sa basag na tubo", "Ia terpeleset dan jatuh menimpa tabung pecah"), ("Nabangga siya ng kotse", "Ia tertabrak mobil"), ("Nasunog ang kaniyang kamay", "Tangannya terbakar")], 0, ("Nadulas siya sa likido at bumagsak sa basag na tubong salamin.", "Ia terpeleset di cairan dan jatuh menimpa tabung kaca yang pecah.")),
            (("Ano ang ipinasiya ni James matapos mapag-isipan ang kaniyang buhay?", "Apa keputusan James setelah merenungkan hidupnya?"), [("Bumalik agad sa operasyon", "Segera kembali bekerja"), ("Umalis nang hindi nagpapaalam", "Pergi tanpa pamit"), ("Magpahinga at makasama si Steve", "Beristirahat dan bersama Steve")], 2, ("Pinili niyang umuwi, maligo at gumugol ng panahon kasama ang anak.", "Ia memilih pulang, mandi, dan menghabiskan waktu bersama putranya.")),
        ],
    },
    {
        "category": "Pagbabagong-loob at kabutihan", "summary": ("Nagbagong-buhay ang tumakas na magnanakaw matapos patawarin siya ng matandang may-ari ng kubo at hikayating piliin ang kabutihan.", "Pencuri yang melarikan diri mengubah hidup setelah pemilik kabin tua memaafkan dan mendorongnya untuk berbuat baik."),
        "characters": ["the criminal", "the old man"], "setting": "A jail, a forest, and a neat cabin behind a fence.",
        "theme": ("Understanding and compassion can encourage someone to change.", "pag-unawa at pagbabago", "pengertian dan perubahan"),
        "events": ["A thief escapes jail and finds food in a cabin in the woods.", "The elderly owner catches him, sees through his lie that he is a policeman, and identifies him as a criminal.", "The thief admits what he did and offers cash to settle the matter.", "The owner refuses money, forgives him without a penalty, and inspires him never to steal again."],
        "sentences": [
            ("Nakakulong ang isang lalaking magnanakaw at hindi siya nakokonsensiya sa pagkuha ng mga gamit ng iba.", "Seorang pencuri dipenjara dan tidak merasa bersalah karena mengambil milik orang lain."),
            ("Isang araw, nakatakas siya at nakakita ng maayos na kubo sa gubat na may bakod sa paligid.", "Suatu hari, ia melarikan diri dan menemukan kabin rapi di hutan dengan pagar di sekelilingnya."),
            ("Kinain niya ang prutas at ininom ang gatas sa loob, ngunit itinapon niya ang dosenang itlog dahil mabaho ang mga ito.", "Ia memakan buah dan meminum susu di dalam, tetapi membuang selusin telur karena baunya aneh."),
            ("Pagdating ng matandang may-ari, nagsinungaling ang lalaki at nagsabing pulis siya, ngunit agad siyang nakilala ng matanda.", "Ketika pemilik tua datang, lelaki itu berbohong dan mengaku sebagai polisi, tetapi orang tua itu langsung mengenalinya."),
            ("Inamin ng lalaki na kriminal siya at nag-alok ng kaunting pera upang bayaran ang kinain niya.", "Lelaki itu mengaku sebagai penjahat dan menawarkan sedikit uang untuk membayar makanan yang ia ambil."),
            ("Hindi tinanggap ng matanda ang pera at sinabing walang parusa; dahil sa kabaitan niya, hindi na muling nagnakaw ang lalaki.", "Orang tua itu menolak uang dan mengatakan tidak ada hukuman; karena kebaikannya, lelaki itu tidak pernah mencuri lagi."),
        ],
        "vocabulary": [("magnanakaw", "pencuri", "pangngalan"), ("nakakulong", "dipenjara", "pandiwa"), ("kubo", "kabin", "pangngalan"), ("bakod", "pagar", "pangngalan"), ("inamin", "mengaku", "pandiwa"), ("parusa", "hukuman", "pangngalan")],
        "expressions": [("hindi tinanggap ang pera", "menolak uang"), ("hindi na muling nagnakaw", "tidak pernah mencuri lagi")],
        "grammar": ("Ang ngunit ay nag-uugnay ng magkasalungat na kilos. Ang dahil sa ay nagpapakilala ng dahilan.", "Tetapi menghubungkan tindakan yang berlawanan. Karena memperkenalkan alasan."),
        "questions": [
            (("Ano ang kinain ng tumakas na lalaki sa kubo?", "Apa yang dimakan lelaki yang melarikan diri di kabin?"), [("Prutas at gatas", "Buah dan susu"), ("Karne at tinapay", "Daging dan roti"), ("Isda at bigas", "Ikan dan nasi")], 0, ("Nakakita siya ng mangkok ng prutas at bote ng gatas sa bahay.", "Ia menemukan semangkuk buah dan sebotol susu di rumah itu.")),
            (("Bakit hindi naniwala ang matanda sa lalaki?", "Mengapa orang tua itu tidak memercayai lelaki itu?"), [("Hindi siya marunong magsalita", "Ia tidak dapat berbicara"), ("Alam niyang kriminal ito", "Ia tahu lelaki itu penjahat"), ("Nakita niyang walang sapatos", "Ia melihat lelaki itu tanpa sepatu")], 1, ("Sinabi ng matanda na alam niyang kriminal ang kaniyang kausap.", "Orang tua itu mengatakan bahwa ia tahu lawan bicaranya seorang penjahat.")),
            (("Ano ang ginawa ng lalaki matapos patawarin siya?", "Apa yang dilakukan lelaki itu setelah dimaafkan?"), [("Bumalik siya sa bilangguan", "Ia kembali ke penjara"), ("Nagnakaw pa siya", "Ia mencuri lagi"), ("Hindi na siya nagnakaw", "Ia tidak mencuri lagi")], 2, ("Nagbago ang lalaki at hindi na nagnakaw kaninuman.", "Lelaki itu berubah dan tidak mencuri dari siapa pun lagi.")),
        ],
    },
    {
        "category": "Pamumuno at pag-iingat", "summary": ("Binalewala ni Kapitan William ang babala ni Thomas tungkol sa bagyo at bahura, kaya bumangga at lumubog ang kaniyang barko.", "Kapten William mengabaikan peringatan Thomas tentang badai dan terumbu, sehingga kapalnya menabrak dan tenggelam."),
        "characters": ["Captain Thomas", "Captain William", "the crews"], "setting": "Two cotton-carrying ships approaching a hurricane and coral reef.",
        "theme": ("Good leaders know when safety must come before entertainment.", "pag-iingat sa tamang panahon", "berhati-hati pada saat yang tepat"),
        "events": ["Thomas leads a strict but reliable ship, while William runs a grand ship with a carefree crew.", "Thomas spots a hurricane and warns William about the reef and coral ahead.", "William tells his crew to go below deck and keep dancing instead of turning back.", "His ship is driven into the reef, floods, and is lost; the crew blames his poor leadership."],
        "sentences": [
            ("May dalang bulak ang dalawang barko, ngunit magkaiba ang pamamalakad nina Kapitan Thomas at Kapitan William.", "Dua kapal membawa kapas, tetapi Kapten Thomas dan Kapten William memimpin dengan cara berbeda."),
            ("Mahigpit si Thomas at maayos ang kaniyang payak na barko, samantalang mahilig magsaya si William sa marangyang sasakyan.", "Thomas tegas dan kapalnya yang sederhana terawat, sementara William senang berpesta di kapalnya yang megah."),
            ("Nang makakita si Thomas ng paparating na bagyo, inayos niya ang radyo at nagbabala kay William tungkol sa bahurang korales.", "Ketika melihat badai mendekat, Thomas mengatur radio dan memperingatkan William tentang terumbu karang."),
            ("Sa halip na bumalik, inutusan ni William ang mga tauhan na bumaba sa kubyerta at magsayaw habang dumaraan ang bagyo.", "Alih-alih berbalik, William menyuruh awak kapal turun ke bawah geladak dan menari sampai badai berlalu."),
            ("Itinulak ng hangin ang barko sa bahura, bumangga ito sa korales at pumasok ang tubig sa ibaba ng kubyerta.", "Angin mendorong kapal ke terumbu, kapal menabrak karang dan air masuk ke bawah geladak."),
            ("Sinisi ng mga tauhan si William sa pagkawala ng barko; natutuhan niyang may panahong kailangang unahin ang pagiging seryoso.", "Awak kapal menyalahkan William atas hilangnya kapal; ia belajar bahwa ada saatnya keseriusan harus diutamakan."),
        ],
        "vocabulary": [("bulak", "kapas", "pangngalan"), ("mahigpit", "tegas", "pang-uri"), ("marangya", "megah", "pang-uri"), ("bahura", "terumbu", "pangngalan"), ("korales", "karang", "pangngalan"), ("pagkawala", "kehilangan", "pangngalan")],
        "expressions": [("sa halip na bumalik", "alih-alih berbalik"), ("may panahong kailangang", "ada saatnya harus")],
        "grammar": ("Ang sa halip na ay nagpapakita ng piniling ibang kilos. Ang nang ay nagpapakilala ng pangyayaring naganap bago ang pasiya.", "Alih-alih menunjukkan tindakan lain yang dipilih. Ketika memperkenalkan peristiwa sebelum keputusan."),
        "questions": [
            (("Ano ang nakita ni Thomas sa unahan?", "Apa yang dilihat Thomas di depan?"), [("Isang bagyo", "Badai"), ("Isang isla", "Pulau"), ("Isang pirata", "Bajak laut")], 0, ("Nakita ni Thomas ang paparating na hurricane at binalaan niya ang kaibigan.", "Thomas melihat badai mendekat dan memperingatkan temannya.")),
            (("Bakit binalaan ni Thomas si William?", "Mengapa Thomas memperingatkan William?"), [("May bagyo at bahurang korales sa dadaanan", "Ada badai dan terumbu karang di jalur mereka"), ("Nauubos ang bulak", "Kapas mereka habis"), ("Nawawala ang radyo", "Radio mereka hilang")], 0, ("Maaaring bumangga sa bahura ang barko kung hindi ito iikot palayo sa bagyo.", "Kapal dapat berbalik agar tidak menabrak terumbu saat badai.")),
            (("Ano ang naging bunga ng pasiya ni William?", "Apa akibat keputusan William?"), [("Nanalo siya sa karera", "Ia menang lomba"), ("Nawasak ang barko sa bahura", "Kapalnya hancur di terumbu"), ("Nakatakas ang kaniyang mga tauhan", "Awak kapalnya melarikan diri")], 1, ("Tinangay ng hangin ang barko patungo sa bahura at bumangga ito.", "Angin mendorong kapal ke terumbu dan kapal itu menabrak.")),
        ],
    },
    {
        "category": "Katotohanan at katarungan", "summary": ("Pinalaya ng ministrong kakambal ng duke ang babaeng napagbintangang mangkukulam nang malaman niyang mga insekto pala ang sumisira sa mga tanim.", "Menteri kembaran sang duke membebaskan perempuan yang dituduh penyihir setelah menemukan bahwa seranggala yang merusak tanaman."),
        "characters": ["the Duke", "the Minister", "the woman", "the field guards"], "setting": "The duke's tobacco fields and jail.",
        "theme": ("Careful investigation can expose false accusations.", "pagsisiyasat bago humatol", "menyelidiki sebelum menghakimi"),
        "events": ["The duke's tobacco plants begin dying, and guards blame a woman for singing unfamiliar words.", "The woman says she is ordinary, while the minister believes she is innocent.", "The minister examines a plant and finds small bugs eating it.", "He uses his resemblance to the duke to free her and apologizes; the duke stays focused on the plants."],
        "sentences": [
            ("Mahigpit ang tuntunin ng duke na panatilihing malusog ang mga tanim na tabako, ngunit nagsimula itong mamatay.", "Aturan utama sang duke adalah menjaga tanaman tembakau tetap sehat, tetapi tanaman itu mulai mati."),
            ("Dahil kakambal ng duke ang kaniyang punong ministro, halos magkapareho ang kanilang hitsura.", "Menteri utamanya adalah saudara kembar sang duke, sehingga penampilan mereka hampir sama."),
            ("Dinala ng mga bantay ang isang babae at sinabing mangkukulam siya dahil kumanta ito sa wikang hindi nila mabigkas.", "Para penjaga membawa seorang perempuan dan menyebutnya penyihir karena ia bernyanyi dalam bahasa yang tidak dapat mereka ucapkan."),
            ("Inakala ng duke na may sumpa ang babae, ngunit naniwala ang ministro na inosente ito at nagsiyasat ng halaman.", "Sang duke mengira perempuan itu mengutuk tanaman, tetapi menteri percaya ia tidak bersalah dan memeriksa tanaman."),
            ("Nakita ng ministro ang daan-daang kulisap na kumakain sa mga dahon, kaya nalaman niya ang tunay na dahilan.", "Menteri melihat ratusan serangga memakan daun, sehingga mengetahui penyebab sebenarnya."),
            ("Nagpanggap siyang duke upang palayain ang babae at humingi ng tawad; hindi siya pinarusahan dahil abala ang duke sa pagsagip sa mga tanim.", "Ia menyamar sebagai duke untuk membebaskan perempuan itu dan meminta maaf; ia tidak dihukum karena sang duke sibuk menyelamatkan tanaman."),
        ],
        "vocabulary": [("tabako", "tembakau", "pangngalan"), ("kakambal", "saudara kembar", "pangngalan"), ("mangkukulam", "penyihir", "pangngalan"), ("sumpa", "kutukan", "pangngalan"), ("inosente", "tidak bersalah", "pang-uri"), ("kulisap", "serangga", "pangngalan")],
        "expressions": [("nagsiyasat ng halaman", "memeriksa tanaman"), ("humingi ng tawad", "meminta maaf")],
        "grammar": ("Ang ngunit ay nag-uugnay ng magkasalungat na pasiya. Ang dahil ay nagpapakilala ng dahilan ng isang pangyayari.", "Tetapi menghubungkan keputusan yang berlawanan. Karena memperkenalkan alasan suatu peristiwa."),
        "questions": [
            (("Bakit pinaratangan ng mga bantay ang babae?", "Mengapa para penjaga menuduh perempuan itu?"), [("Dahil kumanta siya sa wikang hindi nila kilala", "Karena ia bernyanyi dalam bahasa yang tidak mereka kenal"), ("Dahil ninakaw niya ang tabako", "Karena ia mencuri tembakau"), ("Dahil kamukha niya ang duke", "Karena ia mirip sang duke")], 0, ("Inakala nilang sumpa ang awit dahil hindi nila mabigkas ang mga salita.", "Mereka mengira nyanyian itu kutukan karena tidak dapat mengucapkan katanya.")),
            (("Ano ang natuklasan ng ministro sa mga dahon?", "Apa yang ditemukan menteri pada daun?"), [("Mga butas ng bulate lamang", "Hanya lubang cacing"), ("Mga kulisap na kumakain sa mga ito", "Serangga yang memakannya"), ("Isang salamangka", "Sebuah mantra")], 1, ("Daang-daang maliliit na kulisap ang sumisira sa tanim.", "Ratusan serangga kecil merusak tanaman.")),
            (("Paano napalaya ng ministro ang babae?", "Bagaimana menteri membebaskan perempuan itu?"), [("Nagpanggap siyang duke", "Ia menyamar sebagai duke"), ("Nagbayad siya sa bantay", "Ia membayar penjaga"), ("Sinira niya ang kulungan", "Ia merusak penjara")], 0, ("Dahil kamukha niya ang duke, nagawang palabasin ng ministro ang babae.", "Karena mirip duke, menteri dapat menyuruh penjaga membebaskan perempuan itu.")),
        ],
    },
    {
        "category": "Kasanayan at pagtitiyaga", "summary": ("Tinalo ng matiyagang mangingisda si George kahit simpleng sanga at pisi lamang ang gamit niya, at ibinahagi niya ang paniniwalang kailangan ang tiyaga.", "Nelayan yang sabar mengalahkan George meski hanya memakai dahan dan tali sederhana, lalu berbagi pandangan bahwa kesabaran diperlukan."),
        "characters": ["the fisherman", "George"], "setting": "A bridge by the water near an inn.",
        "theme": ("Patience and confidence can matter more than elaborate equipment.", "tiyaga at paniniwala sa sarili", "kesabaran dan keyakinan diri"),
        "events": ["A fisherman catches fish with a branch, line, hook, and net.", "George challenges him and brings electronic tools to locate and weigh fish.", "They fish all day, and George subtracts his catch from the fisherman's total.", "The fisherman has 47 more fish and explains that patience and self-belief are his method."],
        "sentences": [
            ("Araw-araw na nakaupo sa tulay ang mangingisda at naghuhulog ng mga buto ng mansanas sa tubig.", "Setiap hari nelayan duduk di jembatan dan menjatuhkan biji apel ke air."),
            ("Pumuputol siya ng sanga, nagtatali ng pisi at matalim na kawit, at gumagamit ng malaking lambat sa huli.", "Ia memotong dahan, mengikat tali dan kail tajam, lalu memakai jaring besar untuk hasil tangkapannya."),
            ("Isang bisita sa bahay-panuluyan na si George ang nagyabang na mas mahusay siyang mangisda at hinamon siya.", "Seorang tamu penginapan bernama George membual bahwa ia nelayan yang lebih baik dan menantangnya."),
            ("Maraming elektronikong kagamitan si George, kabilang ang makinang nagpapakita kung nasaan ang mga isda at panimbang sa pamingwit.", "George membawa banyak alat elektronik, termasuk mesin penunjuk lokasi ikan dan alat penimbang pada joran."),
            ("Sa pagtatapos ng araw, binilang ni George ang kanilang huli at may apatnapu't pitong isdang lamang ang mangingisda.", "Pada akhir hari, George menghitung hasil tangkapan mereka dan nelayan itu unggul empat puluh tujuh ikan."),
            ("Ipinaliwanag ng mangingisda na simple ang pilosopiya niya: maging matiyaga at maniwala sa sarili.", "Nelayan menjelaskan bahwa filosofinya sederhana: bersabar dan percaya kepada diri sendiri."),
        ],
        "vocabulary": [("tulay", "jembatan", "pangngalan"), ("pisi", "tali", "pangngalan"), ("kawit", "kail", "pangngalan"), ("lambat", "jaring", "pangngalan"), ("kagamitan", "peralatan", "pangngalan"), ("matiyaga", "sabar", "pang-uri")],
        "expressions": [("hinamon siya", "menantangnya"), ("maniwala sa sarili", "percaya kepada diri sendiri")],
        "grammar": ("Ang kabilang ang ay nagpapakilala ng mga halimbawa sa isang pangkat. Ang na lamang ay ginagamit upang ihambing ang kabuuang bilang.", "Termasuk memperkenalkan contoh dalam suatu kelompok. Unggul sebanyak digunakan untuk membandingkan jumlah."),
        "questions": [
            (("Anong simpleng gamit ang pamingwit ng mangingisda?", "Apa alat sederhana yang dipakai nelayan?"), [("Sanga, pisi at kawit", "Dahan, tali, dan kail"), ("Radyo at kamera", "Radio dan kamera"), ("Bangka at sagwan", "Perahu dan dayung")], 0, ("Sanga ang pamalo niya at itinatali niya rito ang pisi at kawit.", "Ia memakai dahan sebagai joran dan mengikat tali serta kail padanya.")),
            (("Anong kagamitan ang dala ni George?", "Alat apa yang dibawa George?"), [("Mga palayok", "Beberapa periuk"), ("Mga elektronikong kagamitan", "Peralatan elektronik"), ("Isang kabayo", "Seekor kuda")], 1, ("Gumamit siya ng makina para makita ang lokasyon at timbangin ang isda.", "Ia memakai mesin untuk mengetahui lokasi dan berat ikan.")),
            (("Ano ang naging lamang ng mangingisda?", "Berapa keunggulan jumlah ikan nelayan?"), [("Apatnapu't pitong isda", "Empat puluh tujuh ikan"), ("Isang isda", "Satu ikan"), ("Wala", "Tidak ada")], 0, ("Apatnapu't pitong isda ang lamang ng huli ng mangingisda.", "Hasil tangkapan nelayan unggul empat puluh tujuh ikan.")),
        ],
    },
    {
        "category": "Mitolohiya at pagmamahal", "summary": ("Nagtaksil si Set kay Osiris dahil nais niyang maging hari, ngunit ibinalik ng mga diyos si Osiris tuwing tagsibol dahil sa pagmamahal ni Isis.", "Set mengkhianati Osiris demi menjadi raja, tetapi para dewa mengembalikan Osiris setiap musim semi karena cinta Isis."),
        "characters": ["Osiris", "Isis", "Set", "the Egyptians", "the Egyptian gods"], "setting": "Ancient Egypt along the fertile Nile River.",
        "theme": ("Love and care for a community can outlast betrayal.", "pagmamahal at pagtataksil", "cinta dan pengkhianatan"),
        "events": ["Osiris and Isis teach the Egyptians useful skills and receive a pyramid as a gift.", "Set envies Osiris and traps him in a wooden box during an annual tour.", "The box is carried by a flood to a foreign shore, where Isis recovers Osiris's body and obtains a grave.", "The gods honor Isis's love, make Osiris god of the underworld, and he returns every spring to help crops."],
        "sentences": [
            ("Namuno noon si Osiris sa matabang lupa sa tabi ng Ilog Nile kasama si Reyna Isis.", "Dahulu Osiris memerintah tanah subur di tepi Sungai Nil bersama Ratu Isis."),
            ("Itinuro nila sa mga Ehipsiyo ang paggawa ng gulong, muwebles, palayok at tela, kaya minahal sila ng mga tao.", "Mereka mengajarkan orang Mesir membuat roda, perabot, tembikar, dan kain, sehingga rakyat menyayangi mereka."),
            ("Lahat ay nagmahal kay Osiris maliban sa kapatid niyang si Set, na gustong pumalit sa trono.", "Semua orang menyayangi Osiris kecuali saudaranya, Set, yang ingin menggantikannya di takhta."),
            ("Sa taunang paglalakbay ni Osiris, ipinakita ni Set ang magandang kahong kahoy at hinikayat siyang humiga sa loob.", "Dalam perjalanan tahunan Osiris, Set menunjukkan kotak kayu yang indah dan mengajaknya berbaring di dalamnya."),
            ("Isinara ni Set ang kahon at itinapon sa ilog, ngunit inanod ito ng baha sa malayong pampang.", "Set menutup kotak dan melemparkannya ke sungai, tetapi banjir menghanyutkannya ke pantai jauh."),
            ("Naiuwi ni Isis ang katawan ni Osiris at nakakuha ng libingan; dahil sa pagmamahal niya, naging diyos ng daigdig-ilalim si Osiris at tumutulong tuwing tagsibol.", "Isis membawa pulang tubuh Osiris dan memperoleh makam; karena cintanya, Osiris menjadi dewa dunia bawah dan membantu setiap musim semi."),
        ],
        "vocabulary": [("mataba", "subur", "pang-uri"), ("muwebles", "perabot", "pangngalan"), ("trono", "takhta", "pangngalan"), ("taunan", "tahunan", "pang-uri"), ("inanod", "menghanyutkan", "pandiwa"), ("libingan", "makam", "pangngalan")],
        "expressions": [("pumalit sa trono", "menggantikan di takhta"), ("dahil sa pagmamahal niya", "karena cintanya")],
        "grammar": ("Ginagamit ang maliban sa upang tukuyin ang eksepsiyon. Ang dahil sa ay nagpapakilala ng dahilan.", "Kecuali menyebutkan pengecualian. Karena memperkenalkan alasan."),
        "questions": [
            (("Ano ang itinuro nina Osiris at Isis sa mga Ehipsiyo?", "Apa yang diajarkan Osiris dan Isis kepada orang Mesir?"), [("Paggawa ng kagamitan at tela", "Membuat peralatan dan kain"), ("Paglalayag sa buwan", "Berlayar ke bulan"), ("Paggawa ng barkong pirata", "Membuat kapal bajak laut")], 0, ("Itinuro nila ang mga kasanayan tulad ng paggawa ng gulong at muwebles.", "Mereka mengajarkan keterampilan seperti membuat roda dan perabot.")),
            (("Bakit ikinulong ni Set si Osiris sa kahon?", "Mengapa Set mengurung Osiris di dalam kotak?"), [("Nais niyang maging hari", "Ia ingin menjadi raja"), ("Nais niyang protektahan siya", "Ia ingin melindunginya"), ("Nais niyang magbigay ng regalo", "Ia ingin memberikan hadiah")], 0, ("Inggit si Set at nais niyang agawin ang trono.", "Set iri dan ingin merebut takhta.")),
            (("Ano ang ginagawa raw ni Osiris tuwing tagsibol?", "Apa yang konon dilakukan Osiris setiap musim semi?"), [("Tinutulungan niya ang mga magsasaka", "Ia membantu para petani"), ("Nagtatayo siya ng mga piramide", "Ia membangun piramida"), ("Naglalakbay siya sa Greece", "Ia bepergian ke Yunani")], 0, ("Bumabalik si Osiris upang tumulong na manatiling buhay ang mga pananim.", "Osiris kembali untuk membantu menjaga tanaman tetap hidup.")),
        ],
    },
    {
        "category": "Katapatan at bagong pagkakataon", "summary": ("Pinahiram ni Peter ng pamasahe ang masungit na pasahero nang mawala ang pitaka nito; namangha ang may-ari ng bangko sa katapatan niya at inalok siya ng trabaho.", "Peter meminjamkan ongkos kepada penumpang kasar yang kehilangan dompet; pemilik bank kagum pada kejujurannya dan menawarkan pekerjaan."),
        "characters": ["Peter", "the passenger", "the bank owner"], "setting": "Peter's taxi downtown and the Fourth Street Bank.",
        "theme": ("Honesty and kindness can open an unexpected opportunity.", "katapatan at kabaitan", "kejujuran dan kebaikan"),
        "events": ["Taxi driver Peter hopes to study with a scholarship and work at a bank.", "A rude passenger asks to be driven to Fourth Street Bank and cannot find his wallet.", "Peter lends him the exact fare despite being upset by the passenger's behavior.", "The passenger reveals he founded the bank, offers money, and hires Peter because he is honest."],
        "sentences": [
            ("Maliit ang suweldo ni Peter bilang drayber ng taksi sa sentro ng lungsod, ngunit gusto niya ang trabahong hindi nakababagot.", "Gaji Peter sebagai sopir taksi di pusat kota kecil, tetapi ia menyukai pekerjaan yang tidak membosankan."),
            ("Umaasa siyang makakuha ng scholarship sa kolehiyo at matuto ng matematika upang makapagtrabaho sa bangko.", "Ia berharap memperoleh beasiswa kuliah dan belajar matematika agar dapat bekerja di bank."),
            ("Isang araw, pinasakay niya ang pasaherong masungit na nag-utos na dalhin siya sa Fourth Street Bank.", "Suatu hari, ia menaikkan penumpang kasar yang menyuruhnya pergi ke Fourth Street Bank."),
            ("Pagdating nila, sampung dolyar at dalawampu't limang sentimo ang pamasahe, ngunit hindi mahanap ng lalaki ang pitaka niya.", "Setibanya di sana, ongkosnya sepuluh dolar dua puluh lima sen, tetapi lelaki itu tidak menemukan dompetnya."),
            ("Kahit galit sa asal nito, pinautang ni Peter ang eksaktong halaga upang makauwi ang pasahero.", "Meski kesal dengan sikapnya, Peter meminjamkan jumlah yang tepat agar penumpang itu dapat pulang."),
            ("Ipinagtapat ng lalaki na siya ang nagtatag ng bangko at inalok si Peter ng trabaho dahil tapat ito.", "Lelaki itu mengaku sebagai pendiri bank dan menawarkan pekerjaan kepada Peter karena ia jujur."),
        ],
        "vocabulary": [("suweldo", "gaji", "pangngalan"), ("scholarship", "beasiswa", "pangngalan"), ("pasahero", "penumpang", "pangngalan"), ("pamasahe", "ongkos", "pangngalan"), ("pinautang", "meminjamkan", "pandiwa"), ("nagtatag", "mendirikan", "pandiwa")],
        "expressions": [("kahit galit sa asal nito", "meski kesal dengan sikapnya"), ("dahil tapat ito", "karena ia jujur")],
        "grammar": ("Ginagamit ang kahit upang magpakita ng pagsalungat sa kabila ng damdamin. Ang dahil ay nag-uugnay ng dahilan sa resulta.", "Meskipun menunjukkan pertentangan dengan perasaan. Karena menghubungkan alasan dengan hasil."),
        "questions": [
            (("Saan gustong makapagtrabaho ni Peter balang araw?", "Di mana Peter ingin bekerja suatu hari nanti?"), [("Sa bangko", "Di bank"), ("Sa bukid", "Di pertanian"), ("Sa palasyo", "Di istana")], 0, ("Iniisip ni Peter na makapag-aral at makakuha ng trabaho sa bangko.", "Peter berharap dapat belajar dan memperoleh pekerjaan di bank.")),
            (("Magkano ang pamasahe ng pasahero?", "Berapa ongkos penumpang?"), [("Sampung dolyar at dalawampu't limang sentimo", "Sepuluh dolar dua puluh lima sen"), ("Limang dolyar", "Lima dolar"), ("Isang dolyar", "Satu dolar")], 0, ("Sampung dolyar at dalawampu't limang sentimo ang singil sa biyahe.", "Ongkos perjalanan itu sepuluh dolar dua puluh lima sen.")),
            (("Bakit inalok ng lalaki ng trabaho si Peter?", "Mengapa lelaki itu menawarkan pekerjaan kepada Peter?"), [("Dahil mahusay siyang sumayaw", "Karena ia pandai menari"), ("Dahil tapat siya at nagpahiram ng pera", "Karena ia jujur dan meminjamkan uang"), ("Dahil nakalimutan niya ang pitaka", "Karena ia melupakan dompet")], 1, ("Nakita ng lalaki ang katapatan at kabaitan ni Peter sa kabila ng kaniyang sariling asal.", "Lelaki itu melihat kejujuran dan kebaikan Peter meski ia sendiri bersikap kasar.")),
        ],
    },
])



def vocabulary_entry(story: dict[str, Any], word: str, meaning: str, part_of_speech: str) -> dict[str, Any]:
    paragraph = next(
        index + 1
        for index, sentence in enumerate(story["sentences"])
        if word.casefold() in sentence["fil"].casefold()
    )
    return {
        "language": "fil",
        "word": word,
        "translations": localized(meaning, word),
        "meanings": localized(meaning, f'Ang katumbas nito sa Indonesian ay “{meaning}”.'),
        "pos": part_of_speech,
        "pronunciation": word,
        "notes": localized(
            f"Kata ini muncul pada paragraf {paragraph} dalam konteks cerita.",
            f"Makikita ang salitang ito sa talata {paragraph} ng muling pagsasalaysay.",
        ),
    }


def build_questions(story_id: str, items: list[tuple[Any, ...]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    questions: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    for number, (prompt, choices, correct, reason) in enumerate(items, 1):
        qid = f"{story_id}-q{number}"
        choices_id = [choice[1] for choice in choices]
        choices_fil = [choice[0] for choice in choices]
        questions.append({
            "id": qid,
            "type": "MULTIPLE_CHOICE",
            "prompt": localized(prompt[1], prompt[0]),
            "choices": localized(choices_id, choices_fil),
            "speech": {"fil": prompt[0]},
        })
        answers.append({
            "questionId": qid,
            "answer": localized(choices_id[correct], choices_fil[correct]),
            "explanation": localized(reason[1], reason[0]),
        })
    return questions, answers


def build_story_document(spec: dict[str, Any], title: str, order: int, image_path: str) -> dict[str, Any]:
    story_id = f"book2-story-{order:02d}-{slugify(title)}"
    questions, answers = build_questions(story_id, spec["questions"])
    expressions_id = "; ".join(f'“{phrase}” — {meaning}' for phrase, meaning in spec["expressions"])
    expressions_fil = "; ".join(
        f'“{phrase}” — ang katumbas sa Indonesian ay “{meaning}”'
        for phrase, meaning in spec["expressions"]
    )
    sentences = [localized(indonesian, filipino) for filipino, indonesian in spec["sentences"]]
    summary_id, summary_fil = spec["summary"]
    tagalog_prefixes = (
        "Tinalo", "Ipinagtanggol", "Nakatakas", "Naabot", "Nakuha", "Pinatunayan", "Natalo",
        "Naging", "Iniwan", "Nangarap", "Binago", "Nanghina", "Nakakita", "Nagpalit", "Ipinakilala",
        "Natuklasan", "Inampon", "Naranasan", "Hindi", "Palihim", "Habang", "Nagbagong-buhay",
        "Binalewala", "Pinalaya", "Tinalo", "Nagtaksil", "Pinahiram",
    )
    if summary_id.startswith(tagalog_prefixes):
        summary_id, summary_fil = summary_fil, summary_id
    if order == 15:
        summary_id = "Penemuan pisau tua membawa keberuntungan dan membuka jalan bagi temuan bersejarah lain."
        summary_fil = "Nagdala ng suwerte ang natagpuang lumang kutsilyo at sinundan ito ng iba pang makasaysayang tuklas."
    return {
        "schemaVersion": 1,
        "id": story_id,
        "collectionId": COLLECTION_ID,
        "sourceOrder": order,
        "family": COLLECTION_ID,
        "category": spec["category"],
        "level": "BEGINNER",
        "order": order,
        "kind": "STORY",
        "image": image_path,
        "title": localized(title, title),
        "originalTitle": title,
        "summary": localized(summary_id, summary_fil),
        "objectives": [
            localized(f'Menelusuri sebab dan akibat dalam “{title}”.', f'Sundan ang sanhi at bunga sa “{title}”.'),
            localized(
                f'Menjelaskan tema {spec["theme"][1].lower()} melalui keputusan para tokoh.',
                f'Ipaliwanag ang temang {spec["theme"][2].lower()} sa pamamagitan ng mga pasiya ng mga tauhan.',
            ),
        ],
        "sentences": sentences,
        "sentenceCount": len(sentences),
        "speakers": [None] * len(sentences),
        "notes": [
            {"title": localized("Ungkapan berguna", "Mga kapaki-pakinabang na pahayag"), "text": localized(expressions_id, expressions_fil)},
            {"title": localized("Catatan tata bahasa", "Tala sa gramatika"), "text": localized(spec["grammar"][1], spec["grammar"][0])},
        ],
        "focus": localized([meaning for _, meaning, _ in spec["vocabulary"]], [word for word, _, _ in spec["vocabulary"]]),
        "questions": questions,
        "answers": answers,
        "vocabulary": [
            vocabulary_entry({"sentences": sentences}, word, meaning, part_of_speech)
            for word, meaning, part_of_speech in spec["vocabulary"]
        ],
        "assets": [image_path],
    }


def parse_epub(epub: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[int, bytes]]:
    with ZipFile(epub) as archive:
        opf_bytes = archive.read("OEBPS/content.opf")
        opf = ET.fromstring(opf_bytes)
        metadata = opf.find(f"{OPF_NS}metadata")
        source = {
            "type": "EPUB",
            "title": metadata.findtext(f"{DC_NS}title", default="") if metadata is not None else "",
            "creator": metadata.findtext(f"{DC_NS}creator", default="") if metadata is not None else "",
            "publisher": metadata.findtext(f"{DC_NS}publisher", default="") if metadata is not None else "",
            "epubFile": epub.name,
            "epubBytes": epub.stat().st_size,
            "epubSha256": sha256(epub.read_bytes()),
            "opfSha256": sha256(opf_bytes),
        }
        manifest = {item.attrib["id"]: item.attrib["href"] for item in opf.findall(f"{OPF_NS}manifest/{OPF_NS}item")}
        spine = [manifest[item.attrib["idref"]] for item in opf.findall(f"{OPF_NS}spine/{OPF_NS}itemref")]
        documents: list[dict[str, Any]] = []
        images: dict[int, bytes] = {}
        narratives: list[dict[str, Any]] = []
        for position, href in enumerate(spine, 1):
            path = f"OEBPS/{href}"
            data = archive.read(path)
            root = ET.fromstring(data)
            header = text(root.find(f".//{XHTML_NS}h1"))
            title = title_for(header)
            paragraphs = [text(element) for element in root.findall(f".//{XHTML_NS}p") if text(element)]
            match = re.fullmatch(r"Text/Unit_(\d{2})\.xhtml", href)
            role = "story" if match else ("cover" if href == "Text/cover.xhtml" else "reference")
            document = {
                "spinePosition": position,
                "path": path,
                "role": role,
                "title": title,
                "sha256": sha256(data),
                "paragraphCount": len(paragraphs),
                "wordCount": len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", " ".join(paragraphs))),
            }
            documents.append(document)
            if role == "story":
                number = int(match.group(1))
                image = root.find(f".//{XHTML_NS}img")
                if not paragraphs or not title or image is None:
                    raise ValueError(f"Narrative unit {number} is incomplete")
                source_image = "OEBPS/" + image.attrib["src"].replace("../", "")
                images[number] = archive.read(source_image)
                narratives.append({**document, "order": number, "sourceImage": source_image})
        if [item["order"] for item in narratives] != list(range(1, 31)):
            raise ValueError("Book 2 must have 30 numbered narrative units in spine order")
        if [item["title"] for item in narratives] != EXPECTED_TITLES:
            raise ValueError("Book 2 narrative titles do not match the verified inventory")
        return source, documents, narratives


def build(epub: Path, root: Path) -> None:
    source, documents, narratives = parse_epub(epub)
    if source["title"].casefold() != BOOK_TITLE.casefold():
        raise ValueError(f"Unexpected EPUB title: {source['title']}")
    if len(STORIES) != 30:
        raise ValueError(f"Expected 30 authored story retellings, found {len(STORIES)}")
    with ZipFile(epub) as archive:
        images = {
            index: archive.read(f"OEBPS/Images/{index:02d}.jpg")
            for index in range(1, 31)
        }

    output_dir = root / "storie" / COLLECTION_ID
    assets_dir = output_dir / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    references: list[dict[str, Any]] = []
    asset_audit: list[dict[str, Any]] = []
    story_audit: list[dict[str, Any]] = []
    for order, (spec, source_story) in enumerate(zip(STORIES, narratives, strict=True), 1):
        title = source_story["title"]
        media_type, extension, width, height = image_info(images[order])
        stem = f"{order:02d}-{slugify(title)}"
        image_path = f"assets/{stem}{extension}"
        image_target = output_dir / image_path
        image_target.write_bytes(images[order])
        asset_audit.append({
            "storyOrder": order,
            "sourcePath": source_story["sourceImage"],
            "path": f"{COLLECTION_ID}/{image_path}",
            "mediaType": media_type,
            "width": width,
            "height": height,
            "bytes": image_target.stat().st_size,
            "sha256": sha256_file(image_target),
            "optimization": "Source JPEG bytes preserved; EPUB illustrations were already compact.",
        })
        story = build_story_document(spec, title, order, image_path)
        story["category"] = category_for(story["id"], story["category"])
        story_path = output_dir / f"{stem}.json"
        story_path.write_bytes(json_bytes(story))
        story_hash = sha256_file(story_path)
        relative_path = f"{COLLECTION_ID}/{story_path.name}"
        references.append({
            "id": story["id"], "collectionId": COLLECTION_ID, "family": COLLECTION_ID,
            "category": story["category"], "level": story["level"], "order": order,
            "sourceOrder": order, "path": relative_path, "sha256": story_hash,
            "sentenceCount": story["sentenceCount"], "title": story["title"],
            "summary": story["summary"], "image": image_path, "assets": story["assets"],
        })
        story_audit.append({
            "order": order, "title": title, "sourceDocument": source_story["path"],
            "sourceSha256": source_story["sha256"],
            "sourceParagraphCount": source_story["paragraphCount"],
            "sourceWordCount": source_story["wordCount"],
            "characters": spec["characters"], "setting": spec["setting"],
            "theme": spec["theme"][0], "mainEvents": spec["events"],
            "generatedStory": relative_path, "generatedSha256": story_hash,
            "illustration": f"{COLLECTION_ID}/{image_path}",
        })

    audit = {
        "schemaVersion": 1, "source": source,
        "inspection": {
            "spineDocumentCount": len(documents), "actualNarrativeCount": len(story_audit),
            "classificationRule": "Only numbered Unit_01 through Unit_30 documents contain full narrative passages; cover, copyright, and note/reference documents are excluded.",
            "excludedDocumentCount": sum(item["role"] != "story" for item in documents),
            "excludedDocuments": [{"path": item["path"], "role": item["role"]} for item in documents if item["role"] != "story"],
        },
        "documentCount": len(documents), "documents": documents,
        "storyCount": len(story_audit), "stories": story_audit,
        "assets": {
            "availableIllustrations": len(images), "extracted": len(asset_audit),
            "skippedUnrelated": ["OEBPS/Images/cover2.jpg", "OEBPS/Images/LogoTVE.jpg"],
            "items": asset_audit,
        },
        "copyrightTreatment": "Each entry is a concise original bilingual retelling and does not reproduce or translate the complete source story text.",
    }
    audit_path = output_dir / "source-audit.json"
    audit_path.write_bytes(json_bytes(audit))
    publish_collection(
        root,
        {
            "id": COLLECTION_ID,
            "order": 2,
            "title": localized(
                "Cerita dari 4000 Essential English Words — Buku 2",
                "Mga Kuwento mula sa 4000 Essential English Words — Book 2",
            ),
            "description": localized(
                "Tiga puluh retelling ringkas dalam bahasa Tagalog dengan terjemahan Indonesia, mengikuti urutan asli Buku 2.",
                "Tatlumpung maiikling muling pagsasalaysay sa Tagalog na may salin sa Indonesian, ayon sa orihinal na ayos ng Book 2.",
            ),
        },
        references,
        audit_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    build(args.epub.resolve(), args.root.resolve())


if __name__ == "__main__":
    main()


# Each entry is an original short retelling, not a transcription of the source text.
# Sentence pairs are Indonesian first and Tagalog second.
