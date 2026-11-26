#!/usr/bin/env python3
"""Build the RoLang story collection from 4000 Essential English Words - Book 1."""

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


BOOK_TITLE = "4000 essential english words - Book 1"
COLLECTION_ID = "4000-essential-english-words-book-1"
XHTML_NS = "{http://www.w3.org/1999/xhtml}"
OPF_NS = "{http://www.idpf.org/2007/opf}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def localized(indonesian: str, filipino: str) -> dict[str, str]:
    return {"id": indonesian, "fil": filipino}


def slugify(value: str) -> str:
    value = value.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def xml_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def strip_unit_number(value: str) -> str:
    value = re.sub(r"^\d+\.\s*", "", value).strip()
    return re.sub(r"\(\d+\)$", "", value).strip()


def image_info(data: bytes) -> tuple[str, str, int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", data[16:24])
        return "image/png", ".png", width, height
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("Unsupported EPUB illustration format")
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        length = int.from_bytes(data[offset:offset + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[offset + 3:offset + 5], "big")
            width = int.from_bytes(data[offset + 5:offset + 7], "big")
            return "image/jpeg", ".jpg", width, height
        offset += length
    raise ValueError("Could not read JPEG dimensions")


def vocabulary_entry(story: dict[str, Any], word: str, meaning: str, part_of_speech: str) -> dict[str, Any]:
    paragraph = next(
        index + 1 for index, (_, filipino) in enumerate(story["sentences"])
        if word.casefold() in filipino.casefold()
    )
    return {
        "language": "fil",
        "word": word,
        "translations": localized(meaning, word),
        "meanings": localized(meaning, f"Ang katumbas nito sa Indonesian ay “{meaning}”."),
        "pos": part_of_speech,
        "pronunciation": word,
        "notes": localized(
            f"Kata ini muncul pada paragraf {paragraph} dalam konteks cerita.",
            f"Makikita ang salitang ito sa talata {paragraph} ng muling pagsasalaysay.",
        ),
    }


def build_questions(story_id: str, questions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prompts: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    for index, question in enumerate(questions, 1):
        question_id = f"{story_id}-q{index}"
        choices_id = [choice[0] for choice in question["choices"]]
        choices_fil = [choice[1] for choice in question["choices"]]
        correct = question["correct"]
        prompts.append({
            "id": question_id,
            "type": "MULTIPLE_CHOICE",
            "prompt": localized(question["prompt"][0], question["prompt"][1]),
            "choices": localized(choices_id, choices_fil),
            "speech": {"fil": question["prompt"][1]},
        })
        answers.append({
            "questionId": question_id,
            "answer": localized(choices_id[correct], choices_fil[correct]),
            "explanation": localized(question["reason"][0], question["reason"][1]),
        })
    return prompts, answers


STORIES: list[dict[str, Any]] = []

STORIES.extend([
    {
        "title": "The Lion and the Rabbit",
        "category": "Fabel dan kecerdikan",
        "summary": (
            "Seekor kelinci memakai kecerdikannya untuk membebaskan hewan-hewan hutan dari singa yang kejam.",
            "Ginamit ng isang kuneho ang kaniyang talino upang mailigtas ang mga hayop sa malupit na leon.",
        ),
        "characters": ["the lion", "the rabbit", "the other forest animals"],
        "setting": "A forest and a deep well.",
        "theme": ("Intelligence can overcome brute force.", "kecerdikan melawan kekuatan", "talino laban sa dahas"),
        "events": [
            "The animals arrange to send the lion one animal per day.",
            "The rabbit arrives late and invents a rival lion.",
            "The rabbit leads the lion to a well, where the lion mistakes his reflection for the rival.",
            "The lion jumps into the well, freeing the other animals.",
        ],
        "sentences": [
            ("Di sebuah hutan, seekor singa kejam membunuh banyak hewan setiap hari.", "Sa isang gubat, araw-araw na pumapatay ng maraming hayop ang malupit na leon."),
            ("Untuk menyelamatkan yang lain, para hewan sepakat mengirim satu hewan kepadanya setiap hari.", "Upang mailigtas ang iba, nakipagkasundo ang mga hayop na magpadala sa kaniya ng isang hayop bawat araw."),
            ("Ketika tiba giliran kelinci, ia sengaja datang terlambat dan berkata bahwa singa lain yang mengaku sebagai raja telah menghadangnya.", "Nang ang kuneho na ang nakatakdang pumunta, sinadya nitong dumating nang huli at sinabi na hinarang siya ng isa pang leon na nag-aangking hari."),
            ("Singa yang marah meminta ditunjukkan saingannya, lalu kelinci membawanya ke sebuah sumur yang dalam.", "Galit na ipinahanap ng leon ang kaniyang karibal, kaya dinala siya ng kuneho sa isang malalim na balon."),
            ("Singa melihat pantulannya sendiri di air dan mengira itulah musuhnya.", "Nakita ng leon ang sarili niyang repleksiyon sa tubig at inakalang iyon ang kalaban."),
            ("Ia langsung melompat untuk menyerang, tetapi tidak pernah berhasil keluar dari sumur.", "Agad siyang tumalon upang umatake, ngunit hindi na siya nakaahon sa balon."),
            ("Berkat tipu daya cerdas kelinci, para hewan terbebas dari ketakutan.", "Dahil sa matalinong panlilinlang ng kuneho, nakalaya sa takot ang mga hayop."),
        ],
        "vocabulary": [
            ("gubat", "hutan", "pangngalan"), ("malupit", "kejam", "pang-uri"),
            ("nakipagkasundo", "membuat kesepakatan", "pandiwa"), ("hinarang", "menghadang", "pandiwa"),
            ("balon", "sumur", "pangngalan"), ("repleksiyon", "pantulan", "pangngalan"),
            ("nakaahon", "berhasil keluar", "pandiwa"), ("panlilinlang", "tipu daya", "pangngalan"),
        ],
        "expressions": [("Upang mailigtas ang iba", "untuk menyelamatkan yang lain"), ("inakalang iyon ang kalaban", "mengira itulah musuhnya")],
        "grammar": (
            "Upang + verba menyatakan tujuan. Nang dapat dipakai untuk menandai waktu terjadinya suatu tindakan.",
            "Ginagamit ang upang + pandiwa upang ipahayag ang layunin. Ginagamit ang nang upang tukuyin ang oras ng isang pangyayari.",
        ),
        "questions": [
            {"prompt": ("Mengapa para hewan membuat kesepakatan dengan singa?", "Bakit nakipagkasundo ang mga hayop sa leon?"), "choices": [("Agar tidak semuanya dibunuh", "Upang hindi sila mapatay na lahat"), ("Agar singa pindah hutan", "Upang lumipat ng gubat ang leon"), ("Agar kelinci menjadi raja", "Upang maging hari ang kuneho")], "correct": 0, "reason": ("Kesepakatan itu dimaksudkan untuk melindungi hewan-hewan yang lain.", "Layunin ng kasunduan na maprotektahan ang ibang mga hayop.")},
            {"prompt": ("Ke mana kelinci membawa singa?", "Saan dinala ng kuneho ang leon?"), "choices": [("Ke sungai", "Sa ilog"), ("Ke sumur yang dalam", "Sa malalim na balon"), ("Ke gua", "Sa kuweba")], "correct": 1, "reason": ("Kelinci memakai sumur untuk memperlihatkan pantulan singa.", "Ginamit ng kuneho ang balon upang makita ng leon ang sariling repleksiyon.")},
            {"prompt": ("Mengapa singa melompat ke dalam sumur?", "Bakit tumalon ang leon sa balon?"), "choices": [("Ia ingin minum", "Gusto niyang uminom"), ("Ia mengejar kelinci", "Hinahabol niya ang kuneho"), ("Ia mengira pantulannya adalah singa lain", "Akala niya ay ibang leon ang kaniyang repleksiyon")], "correct": 2, "reason": ("Singa tidak menyadari bahwa wajah di air adalah pantulannya sendiri.", "Hindi naunawaan ng leon na sarili niyang mukha ang nasa tubig.")},
        ],
    },
    {
        "title": "The Laboratory",
        "category": "Misteri keluarga",
        "summary": ("Mia dan Liz menyelidiki suara menakutkan dari laboratorium ayah Mia dan menemukan kejutan ulang tahun.", "Inusisa nina Mia at Liz ang nakatatakot na tunog sa laboratoryo at natuklasan ang sorpresang regalo ng ama ni Mia."),
        "characters": ["Mia", "Liz", "Mia's father"],
        "setting": "Mia's house and her father's locked laboratory at night.",
        "theme": ("Fear can come from mistaken assumptions.", "ketakutan akibat dugaan yang salah", "takot na bunga ng maling akala"),
        "events": ["Mia hears a frightening laugh behind the locked laboratory door.", "Liz persuades Mia to enter when the door is left unlocked.", "The girls panic in the dark room.", "Mia's father reveals that the laugh comes from a birthday doll."],
        "sentences": [
            ("Ayah Mia memiliki laboratorium rahasia di rumah dan selalu menguncinya.", "May lihim na laboratoryo sa bahay ang ama ni Mia at palagi niya itong ikinakandado."),
            ("Suatu malam, Mia mendengar tawa keras yang menakutkan dari dalam.", "Isang gabi, nakarinig si Mia ng malakas at nakatatakot na halakhak mula sa loob."),
            ("Keesokan harinya, sahabatnya Liz datang dan mendorong Mia untuk mencari asal suara itu.", "Kinabukasan, dumalaw ang kaibigan niyang si Liz at hinikayat siyang alamin ang pinagmulan ng tunog."),
            ("Saat ayah Mia pergi makan malam dan pintunya tertinggal terbuka, kedua gadis itu masuk dengan hati-hati.", "Nang umalis ang ama ni Mia para maghapunan at maiwang bukas ang pinto, maingat na pumasok ang dalawang babae."),
            ("Di ruangan gelap, bau bahan kimia dan tawa yang terdengar lagi membuat mereka semakin takut sehingga Mia berteriak.", "Sa madilim na silid, lalo silang natakot sa amoy ng mga kemikal at sa muling halakhak kaya sumigaw si Mia."),
            ("Ayahnya datang dan menunjukkan bahwa suara itu hanya berasal dari boneka cantik yang dibuatnya untuk ulang tahun Mia.", "Dumating ang ama at ipinakitang mula lamang sa isang magandang manika ang tunog; ginawa niya ito para sa kaarawan ni Mia."),
            ("Ketakutan mereka hilang ketika mengetahui bahwa rahasia laboratorium itu adalah hadiah, bukan monster.", "Nawala ang kanilang takot nang malaman nilang regalo, hindi halimaw, ang lihim sa laboratoryo."),
        ],
        "vocabulary": [("laboratoryo", "laboratorium", "pangngalan"), ("ikinakandado", "mengunci", "pandiwa"), ("halakhak", "tawa keras", "pangngalan"), ("hinikayat", "mendorong", "pandiwa"), ("pinagmulan", "asal", "pangngalan"), ("kemikal", "bahan kimia", "pangngalan"), ("manika", "boneka", "pangngalan"), ("halimaw", "monster", "pangngalan")],
        "expressions": [("mula lamang sa isang magandang manika", "hanya berasal dari sebuah boneka cantik"), ("Nawala ang kanilang takot", "ketakutan mereka hilang")],
        "grammar": ("Nang memperkenalkan peristiwa yang menjadi latar bagi tindakan berikutnya. Para sa menandai penerima atau tujuan.", "Ipinakikilala ng nang ang pangyayaring pinagmulan ng kasunod na kilos. Tinutukoy ng para sa ang tatanggap o layunin."),
        "questions": [
            {"prompt": ("Apa yang awalnya membuat Mia takut?", "Ano ang unang ikinatakot ni Mia?"), "choices": [("Cahaya terang", "Maliwanag na ilaw"), ("Tawa keras dari laboratorium", "Malakas na halakhak mula sa laboratoryo"), ("Pintu yang rusak", "Sirang pinto")], "correct": 1, "reason": ("Mia mendengar tawa yang ia kira berasal dari sesuatu yang jahat.", "Nakarinig si Mia ng halakhak na inakala niyang mula sa masamang nilalang.")},
            {"prompt": ("Mengapa Mia dan Liz dapat masuk?", "Bakit nakapasok sina Mia at Liz?"), "choices": [("Pintunya tidak terkunci", "Hindi nakakandado ang pinto"), ("Mereka memecahkan jendela", "Binasag nila ang bintana"), ("Ayah Mia mengundang mereka", "Inanyayahan sila ng ama ni Mia")], "correct": 0, "reason": ("Ayah Mia pergi makan tanpa mengunci kembali pintu laboratorium.", "Umalis ang ama ni Mia nang hindi muling ikinandado ang pinto.")},
            {"prompt": ("Apa rahasia sebenarnya di laboratorium?", "Ano talaga ang lihim sa laboratoryo?"), "choices": [("Eksperimen berbahaya", "Mapanganib na eksperimento"), ("Monster", "Halimaw"), ("Boneka ulang tahun untuk Mia", "Manika para sa kaarawan ni Mia")], "correct": 2, "reason": ("Ayah Mia sedang membuat boneka yang dapat tertawa sebagai hadiah.", "Gumagawa ang ama ni Mia ng manikang tumatawa bilang regalo.")},
        ],
    },
    {
        "title": "The Report",
        "category": "Petualangan luar angkasa",
        "summary": ("Seorang alien membantu Lee menyelesaikan model planet untuk proyek kelompoknya setelah membawanya melihat ruang angkasa.", "Tinulungan ng isang nilalang mula sa kalawakan si Lee na gumawa ng modelo ng planeta matapos siyang dalhin sa kalawakan."),
        "characters": ["Lee", "Jack", "Claire", "a friendly alien"],
        "setting": "A library, an alien ship, outer space, and Earth.",
        "theme": ("Responsibility and unexpected help can solve a difficult problem.", "tanggung jawab dan bantuan", "pananagutan at tulong"),
        "events": ["Lee worries because his part of the group project is unfinished.", "An alien takes him into space after hearing his wish for help.", "Lee observes the moon and Mars.", "The alien helps Lee build a model of Mars and returns him to Earth."],
        "sentences": [
            ("Di perpustakaan, Lee cemas karena belum membuat model planet untuk proyek kelompoknya bersama Jack dan Claire.", "Sa aklatan, nag-aalala si Lee dahil hindi pa niya nagagawa ang modelo ng planeta para sa pangkatang proyekto nila nina Jack at Claire."),
            ("Jack telah menulis laporan dan Claire telah menggambar peta bintang, sehingga bagian Lee menjadi satu-satunya yang belum selesai.", "Naisulat na ni Jack ang ulat at naiguhit na ni Claire ang mapa ng mga bituin, kaya bahagi na lamang ni Lee ang kulang."),
            ("Lee tidak memahami bagan di buku dan berharap dapat melihat sebuah planet secara langsung.", "Hindi maunawaan ni Lee ang mga tsart sa aklat at hiniling niyang sana ay makakita siya ng planeta nang personal."),
            ("Tiba-tiba, sebuah kapal asing membawanya menemui alien ramah yang menawarkan bantuan.", "Bigla siyang dinala ng isang kakaibang sasakyan sa isang palakaibigang nilalang mula sa kalawakan na nag-alok ng tulong."),
            ("Mereka terbang melewati awan dan bulan, lalu mengamati Mars dan bagian-bagian alam semesta.", "Lumipad sila lampas sa mga ulap at buwan, saka pinagmasdan ang Mars at iba pang bahagi ng uniberso."),
            ("Dalam perjalanan pulang, alien itu membantu Lee membuat model Mars yang jelas dan menarik.", "Sa pag-uwi, tinulungan ng nilalang si Lee na gumawa ng malinaw at kahanga-hangang modelo ng Mars."),
            ("Lee kembali ke Bumi dengan gembira karena kini ia dapat memenuhi tanggung jawabnya kepada kelompok.", "Masayang nakauwi sa Daigdig si Lee dahil magagampanan na niya ang kaniyang pananagutan sa pangkat."),
        ],
        "vocabulary": [("aklatan", "perpustakaan", "pangngalan"), ("pangkatang proyekto", "proyek kelompok", "parirala"), ("modelo", "model", "pangngalan"), ("planeta", "planet", "pangngalan"), ("tsart", "bagan", "pangngalan"), ("kalawakan", "ruang angkasa", "pangngalan"), ("uniberso", "alam semesta", "pangngalan"), ("pananagutan", "tanggung jawab", "pangngalan")],
        "expressions": [("nag-alok ng tulong", "menawarkan bantuan"), ("magagampanan na niya ang kaniyang pananagutan", "ia kini dapat memenuhi tanggung jawabnya")],
        "grammar": ("Hindi pa menyatakan bahwa sesuatu belum terjadi sampai sekarang. Sana ay dipakai untuk menyampaikan harapan.", "Ipinahihiwatig ng hindi pa na hindi pa nangyayari ang isang bagay. Ginagamit ang sana ay sa pagpapahayag ng hangarin."),
        "questions": [
            {"prompt": ("Apa bagian Lee dalam proyek kelompok?", "Ano ang bahagi ni Lee sa pangkatang proyekto?"), "choices": [("Menulis laporan", "Sumulat ng ulat"), ("Menggambar peta", "Gumuhit ng mapa"), ("Membuat model planet", "Gumawa ng modelo ng planeta")], "correct": 2, "reason": ("Jack menangani laporan dan Claire menangani peta, sedangkan Lee harus membuat model.", "Si Jack ang gumawa ng ulat at si Claire ang gumuhit ng mapa, samantalang modelo ang kay Lee.")},
            {"prompt": ("Mengapa alien membawa Lee ke ruang angkasa?", "Bakit dinala ng nilalang si Lee sa kalawakan?"), "choices": [("Untuk membantunya memahami planet", "Upang tulungan siyang maunawaan ang mga planeta"), ("Untuk menyembunyikan proyeknya", "Upang itago ang kaniyang proyekto"), ("Untuk mencari Jack", "Upang hanapin si Jack")], "correct": 0, "reason": ("Lee memerlukan pengalaman langsung agar dapat membuat model yang baik.", "Kailangan ni Lee ng tuwirang karanasan upang makagawa ng mahusay na modelo.")},
            {"prompt": ("Model planet apa yang dibawa Lee pulang?", "Anong modelo ng planeta ang iniuwi ni Lee?"), "choices": [("Bumi", "Daigdig"), ("Mars", "Mars"), ("Bulan", "Buwan")], "correct": 1, "reason": ("Alien membantu Lee membuat model Mars dalam perjalanan kembali ke Bumi.", "Tinulungan ng nilalang si Lee na gumawa ng modelo ng Mars habang pauwi.")},
        ],
    },
    {
        "title": "The Dog’s Bell",
        "category": "Fabel dan perilaku",
        "summary": ("Seekor anjing yang suka menggigit mengira lonceng peringatannya membuatnya populer, tetapi anjing lain menjelaskan kebenarannya.", "Inakala ng asong nangangagat na popular siya dahil sa kaniyang kampana, ngunit ipinaliwanag ng ibang aso ang tunay na dahilan."),
        "characters": ["John", "John's dog", "John's friend", "the villagers", "other dogs"],
        "setting": "A village and its streets.",
        "theme": ("A reputation is not admirable when it comes from harmful behavior.", "reputasi dan akibat perilaku", "reputasyon at bunga ng asal"),
        "events": ["John's dog repeatedly bites villagers.", "A friend suggests a bell so people can hear the dog coming.", "The dog believes the attention makes him popular.", "Other dogs explain that the bell merely helps people avoid him."],
        "sentences": [
            ("Anjing John sering menggigit orang, sehingga seluruh desa merasa khawatir dan menjauhi rumah John.", "Madalas mangagat ng tao ang aso ni John, kaya nababahala ang buong nayon at umiiwas sa bahay ni John."),
            ("John mencoba melatihnya dengan sabar, tetapi kebiasaan buruk itu tidak berubah.", "Matiyagang sinubukan ni John na turuan ito, ngunit hindi nagbago ang masamang ugali."),
            ("Seorang teman menyarankan agar lonceng dipasang di leher anjing supaya warga mendengarnya datang.", "Iminungkahi ng isang kaibigan na lagyan ng kampana ang leeg ng aso upang marinig ng mga tao ang paglapit nito."),
            ("Cara itu berhasil karena orang dapat menghindar sebelum anjing mendekat.", "Naging mabisa iyon dahil nakaiiwas ang mga tao bago pa makalapit ang aso."),
            ("Namun, anjing itu justru membanggakan loncengnya dan mengira semua orang memandangnya karena ia populer.", "Subalit ipinagmamalaki ng aso ang kampana at inakalang tinitingnan siya ng lahat dahil popular siya."),
            ("Anjing-anjing lain menertawakannya dan berkata bahwa lonceng itu hanya menjadi peringatan agar orang menjauh.", "Pinagtawanan siya ng ibang mga aso at sinabing babala lamang ang kampana upang makaiwas ang mga tao."),
            ("Ia pun belajar bahwa terkenal karena alasan yang salah bukanlah sesuatu yang baik.", "Natutuhan niyang hindi mabuti ang maging kilala sa maling dahilan."),
        ],
        "vocabulary": [("mangagat", "menggigit", "pandiwa"), ("nababahala", "khawatir", "pang-uri"), ("kampana", "lonceng", "pangngalan"), ("leeg", "leher", "pangngalan"), ("umiiwas", "menjauh", "pandiwa"), ("ipinagmamalaki", "membanggakan", "pandiwa"), ("popular", "populer", "pang-uri"), ("dahilan", "alasan", "pangngalan")],
        "expressions": [("upang marinig ng mga tao", "agar orang-orang dapat mendengar"), ("sa maling dahilan", "karena alasan yang salah")],
        "grammar": ("Kaya menghubungkan sebab dengan akibat. Upang + verba menjelaskan tujuan pemasangan lonceng.", "Iniuugnay ng kaya ang sanhi at bunga. Ipinapaliwanag ng upang + pandiwa ang layunin ng paglalagay ng kampana."),
        "questions": [
            {"prompt": ("Mengapa lonceng dipasang pada anjing?", "Bakit nilagyan ng kampana ang aso?"), "choices": [("Agar terlihat cantik", "Upang gumanda ito"), ("Agar warga mendengarnya datang", "Upang marinig ng mga tao ang paglapit nito"), ("Agar dapat menemukan rumah", "Upang mahanap nito ang bahay")], "correct": 1, "reason": ("Bunyi lonceng memberi warga waktu untuk menjauh dari anjing yang suka menggigit.", "Binibigyan ng tunog ng kampana ng panahon ang mga tao na makaiwas sa nangangagat na aso.")},
            {"prompt": ("Apa yang disangka anjing tentang loncengnya?", "Ano ang akala ng aso tungkol sa kaniyang kampana?"), "choices": [("Lonceng membuatnya populer", "Ginagawa siyang popular ng kampana"), ("Lonceng membuatnya lambat", "Pinababagal siya ng kampana"), ("Lonceng milik John", "Kay John ang kampana")], "correct": 0, "reason": ("Anjing salah menafsirkan perhatian warga sebagai kekaguman.", "Maling inakala ng aso na paghanga ang pagtingin ng mga tao.")},
            {"prompt": ("Apa pelajaran utama cerita?", "Ano ang pangunahing aral ng kuwento?"), "choices": [("Semua perhatian itu baik", "Mabuti ang lahat ng atensiyon"), ("Anjing harus memakai perhiasan", "Dapat magsuot ng palamuti ang aso"), ("Ketenaran karena perilaku buruk bukan hal positif", "Hindi mabuti ang kasikatang mula sa masamang asal")], "correct": 2, "reason": ("Lonceng membuat anjing dikenal, tetapi hanya karena orang takut digigit.", "Nakilala ang aso dahil sa kampana, ngunit dahil lamang sa takot ng mga tao na makagat.")},
        ],
    },
    {
        "title": "The Jackal and the Sun Child",
        "category": "Legenda hewan",
        "summary": ("Seekor jakal membawa anak matahari demi sebuah kalung, tetapi panasnya meninggalkan tanda hitam permanen di punggungnya.", "Pinasan ng isang tsakal ang batang mula sa araw kapalit ng kuwintas, ngunit nag-iwan ang init ng permanenteng itim na bakas sa kaniyang likod."),
        "characters": ["the jackal", "the sun child"],
        "setting": "A desert, a rock, and a field of flowers.",
        "theme": ("A tempting reward can hide serious consequences.", "imbalan dan konsekuensi", "gantimpala at bunga"),
        "events": ["The sun child offers the jackal a necklace for carrying her home.", "Her heat painfully burns the jackal's back.", "The jackal runs and jumps into flowers to make her fall off.", "The heat leaves the black mark associated with jackals."],
        "sentences": [
            ("Di gurun, seekor jakal bertemu anak bercahaya yang berasal dari matahari.", "Sa disyerto, nakatagpo ang isang tsakal ng makinang na batang mula sa araw."),
            ("Anak itu meminta digendong pulang dan menawarkan kalung sebagai imbalan.", "Hiniling ng bata na pasan siya pauwi at nag-alok ng kuwintas bilang kapalit."),
            ("Jakal menyetujui tawaran itu, tetapi panas dari tubuh anak tersebut segera membakar punggungnya.", "Pumayag ang tsakal, ngunit agad na nasusunog sa init ng bata ang kaniyang likod."),
            ("Ia meminta anak itu turun, tetapi anak matahari tetap berpegangan.", "Nakiusap siyang bumaba ang bata, ngunit patuloy itong kumapit."),
            ("Jakal berlari secepat mungkin lalu melompat ke padang bunga ketika anak itu sedang melihat langit.", "Tumakbo nang napakabilis ang tsakal at saka tumalon sa parang ng mga bulaklak habang nakatingin sa langit ang bata."),
            ("Anak itu terguling dari punggungnya, sehingga jakal dapat melarikan diri.", "Gumulong ang bata mula sa kaniyang likod kaya nakatakas ang tsakal."),
            ("Namun, panas itu meninggalkan jejak hitam, dan sejak saat itu punggung jakal berwarna gelap.", "Ngunit nag-iwan ng itim na bakas ang init, at mula noon ay maitim na ang likod ng tsakal."),
        ],
        "vocabulary": [("disyerto", "gurun", "pangngalan"), ("tsakal", "jakal", "pangngalan"), ("pasan", "menggendong", "pandiwa"), ("kuwintas", "kalung", "pangngalan"), ("nasusunog", "terbakar", "pandiwa"), ("parang", "padang", "pangngalan"), ("gumulong", "terguling", "pandiwa"), ("bakas", "jejak", "pangngalan")],
        "expressions": [("bilang kapalit", "sebagai imbalan"), ("mula noon", "sejak saat itu")],
        "grammar": ("Habang menunjukkan dua tindakan yang berlangsung bersamaan. Mula noon menandai perubahan yang terus berlaku sesudah suatu peristiwa.", "Ipinakikita ng habang ang dalawang kilos na sabay na nangyayari. Tinutukoy ng mula noon ang pagbabagong nagpatuloy matapos ang isang pangyayari."),
        "questions": [
            {"prompt": ("Apa yang ditawarkan anak matahari kepada jakal?", "Ano ang inalok ng batang mula sa araw sa tsakal?"), "choices": [("Kalung", "Kuwintas"), ("Makanan", "Pagkain"), ("Rumah", "Bahay")], "correct": 0, "reason": ("Kalung menjadi imbalan agar jakal mau membawanya pulang.", "Ang kuwintas ang kapalit upang pasanin siya ng tsakal pauwi.")},
            {"prompt": ("Mengapa jakal berusaha menurunkan anak itu?", "Bakit pinababa ng tsakal ang bata?"), "choices": [("Anak itu terlalu berisik", "Masyadong maingay ang bata"), ("Panasnya menyakiti punggung jakal", "Masakit sa likod ng tsakal ang init"), ("Jakal tersesat", "Naliligaw ang tsakal")], "correct": 1, "reason": ("Tubuh anak matahari sangat panas dan membakar punggung jakal.", "Napakainit ng katawan ng bata at nasusunog ang likod ng tsakal.")},
            {"prompt": ("Apa yang menjelaskan punggung hitam jakal dalam legenda ini?", "Ano ang paliwanag ng alamat sa maitim na likod ng tsakal?"), "choices": [("Lumpur gurun", "Putik sa disyerto"), ("Bunga berwarna hitam", "Maiitim na bulaklak"), ("Bekas panas anak matahari", "Bakas ng init ng batang mula sa araw")], "correct": 2, "reason": ("Panas anak matahari meninggalkan tanda yang tidak hilang.", "Nag-iwan ng bakas na hindi nawala ang init ng batang mula sa araw.")},
        ],
    },
    {
        "title": "The Friendly Ghost",
        "category": "Kisah hantu dan keselamatan",
        "summary": ("Hantu seorang perempuan baik menakut-nakuti anak-anak agar mereka menjauh dari sungai yang sedang meluap dan kembali ke rumah.", "Tinakot ng multo ng isang mabait na babae ang mga bata upang mailayo sila sa umaapaw na ilog at maihatid pauwi."),
        "characters": ["the friendly ghost", "a group of children", "their dog"],
        "setting": "A riverside community during a dark rainstorm.",
        "theme": ("A frightening appearance can conceal a protective intention.", "penampilan dan niat baik", "anyo at mabuting layunin"),
        "events": ["A kind woman becomes a ghost who still wants to protect children.", "Children become lost beside a rising river during a storm.", "The ghost frightens and follows them away from the river.", "The children reach home before the flood becomes dangerous."],
        "sentences": [
            ("Seorang perempuan baik yang mencintai anak-anak tetap menjaga komunitasnya setelah menjadi hantu.", "Patuloy na binantayan ng isang mabait na babaeng naging multo ang kaniyang pamayanan at ang mga bata roon."),
            ("Suaranya menakutkan, meskipun niatnya bukan mencelakakan siapa pun.", "Nakatatakot ang kaniyang tinig kahit wala siyang layuning manakit."),
            ("Suatu malam, beberapa anak dan anjing mereka tersesat di dekat sungai saat hujan lebat.", "Isang gabi, naligaw sa tabi ng ilog ang ilang bata at ang kanilang aso habang malakas ang ulan."),
            ("Air sungai terus naik, tetapi dalam kegelapan mereka tidak tahu jalan pulang.", "Patuloy na tumaas ang tubig, ngunit hindi nila alam ang daan pauwi sa dilim."),
            ("Hantu itu muncul dan berteriak agar mereka pergi, sehingga anak-anak ketakutan dan berlari menjauh.", "Nagpakita ang multo at sumigaw ng “Lumayo kayo!” kaya natakot at tumakbo palayo ang mga bata."),
            ("Ia mengikuti mereka sampai mereka tiba dengan selamat di rumah.", "Sinundan niya ang mga bata hanggang ligtas silang nakarating sa bahay."),
            ("Ketika sungai meluap, mereka menyadari bahwa hantu yang menakutkan itu sebenarnya telah menyelamatkan mereka.", "Nang umapaw ang ilog, naunawaan nilang iniligtas pala sila ng nakatatakot na multo."),
        ],
        "vocabulary": [("pamayanan", "komunitas", "pangngalan"), ("multo", "hantu", "pangngalan"), ("naligaw", "tersesat", "pandiwa"), ("ilog", "sungai", "pangngalan"), ("tumaas", "naik", "pandiwa"), ("palayo", "menjauh", "pang-abay"), ("umapaw", "meluap", "pandiwa"), ("iniligtas", "menyelamatkan", "pandiwa")],
        "expressions": [("Lumayo kayo!", "Menjauhlah!"), ("iniligtas pala sila", "ternyata ia telah menyelamatkan mereka")],
        "grammar": ("Kahit menyatakan pertentangan: suara hantu menakutkan meskipun niatnya baik. Pala menandai penemuan atau kesadaran baru.", "Ginagamit ang kahit sa pagsalungat: nakatatakot ang tinig kahit mabuti ang layunin. Ipinahihiwatig ng pala ang bagong natuklasan o naunawaan."),
        "questions": [
            {"prompt": ("Mengapa anak-anak takut kepada hantu?", "Bakit natakot ang mga bata sa multo?"), "choices": [("Suaranya menakutkan", "Nakatatakot ang kaniyang tinig"), ("Ia mengambil anjing mereka", "Kinuha niya ang kanilang aso"), ("Ia memadamkan bulan", "Pinatay niya ang liwanag ng buwan")], "correct": 0, "reason": ("Hantu itu baik, tetapi suara dan teriakannya terdengar menakutkan.", "Mabuti ang multo, ngunit nakatatakot ang kaniyang tinig at sigaw.")},
            {"prompt": ("Bahaya apa yang mengancam anak-anak?", "Anong panganib ang nagbanta sa mga bata?"), "choices": [("Pohon tumbang", "Bumagsak na puno"), ("Sungai yang meluap", "Umaapaw na ilog"), ("Hewan liar", "Mabangis na hayop")], "correct": 1, "reason": ("Hujan membuat permukaan sungai terus naik hingga berbahaya.", "Patuloy na tumaas ang ilog dahil sa ulan hanggang maging mapanganib ito.")},
            {"prompt": ("Apa tujuan sebenarnya dari teriakan hantu?", "Ano ang tunay na layunin ng pagsigaw ng multo?"), "choices": [("Mengusir anak-anak dari komunitas", "Paalisin ang mga bata sa pamayanan"), ("Membuat mereka menangis", "Paiyakin sila"), ("Mengarahkan mereka menjauh dari sungai dan pulang", "Ilayo sila sa ilog at ihatid pauwi")], "correct": 2, "reason": ("Dengan membuat mereka berlari, hantu menuntun anak-anak ke tempat yang aman.", "Sa pagpapatakbo sa kanila, naihatid ng multo ang mga bata sa ligtas na lugar.")},
        ],
    },
    {
        "title": "The Best Prince",
        "category": "Kepemimpinan",
        "summary": ("Raja Minos memilih Jason yang baik hati sebagai penerus, sementara dua putra yang lebih tua kehilangan kesempatan karena bertengkar.", "Pinili ni Haring Minos ang mabait na si Jason bilang tagapagmana habang nawala ang pagkakataon ng dalawang nakatatandang anak dahil sa kanilang pag-aaway."),
        "characters": ["King Minos", "Theseus", "Pelias", "Jason"],
        "setting": "King Minos's palace and kingdom.",
        "theme": ("Kindness and peace are stronger qualifications for leadership than force.", "kepemimpinan melalui kebaikan", "pamumuno sa pamamagitan ng kabaitan"),
        "events": ["The sick king must choose one of his three sons as successor.", "Theseus and Pelias argue and draw their swords.", "Minos chooses peaceful, kind Jason.", "The older brothers regret missing their father's final moments and accept Jason."],
        "sentences": [
            ("Raja Minos yang sakit harus memilih penerus dari tiga putranya.", "Kailangang pumili ng tagapagmana ang maysakit na si Haring Minos mula sa kaniyang tatlong anak."),
            ("Theseus mengandalkan kekuatan, sedangkan Pelias membanggakan keahliannya memakai senjata.", "Umasa si Theseus sa kaniyang lakas, samantalang ipinagmalaki ni Pelias ang galing niya sa sandata."),
            ("Keduanya saling menantang dan bertarung karena masing-masing ingin menguasai kerajaan.", "Naghamon at naglaban ang dalawa dahil kapwa nila gustong angkinin ang kaharian."),
            ("Jason, putra bungsu, tetap berada di sisi ayahnya dan memahami kesedihan sang raja.", "Nanatili sa tabi ng ama ang bunsong si Jason at naunawaan niya ang lungkot ng hari."),
            ("Minos memilih Jason karena kebaikannya dapat membawa perdamaian dan mencegah perang.", "Pinili ni Minos si Jason dahil makapagdudulot ng kapayapaan ang kaniyang kabaitan at maiiwasan niya ang digmaan."),
            ("Setelah raja wafat, Theseus dan Pelias menyesal karena pertengkaran membuat mereka tidak sempat berpamitan.", "Pagkamatay ng hari, nagsisi sina Theseus at Pelias dahil hindi sila nakapagpaalam bunga ng kanilang pag-aaway."),
            ("Mereka menerima Jason sebagai raja dan menyadari bahwa ia memang pilihan terbaik.", "Tinanggap nila si Jason bilang hari at kinilalang siya ang karapat-dapat mamuno."),
        ],
        "vocabulary": [("tagapagmana", "penerus", "pangngalan"), ("sandata", "senjata", "pangngalan"), ("naghamon", "menantang", "pandiwa"), ("naglaban", "bertarung", "pandiwa"), ("kaharian", "kerajaan", "pangngalan"), ("kabaitan", "kebaikan", "pangngalan"), ("kapayapaan", "perdamaian", "pangngalan"), ("nagsisi", "menyesal", "pandiwa")],
        "expressions": [("ang karapat-dapat mamuno", "orang yang pantas memimpin"), ("bunga ng kanilang pag-aaway", "akibat pertengkaran mereka")],
        "grammar": ("Samantalang membandingkan dua sifat atau tindakan yang berbeda. Dahil memperkenalkan alasan pemilihan Jason.", "Ginagamit ang samantalang sa paghahambing ng magkaibang katangian o kilos. Ipinakikilala ng dahil ang dahilan ng pagpili kay Jason."),
        "questions": [
            {"prompt": ("Mengapa Minos tidak memilih Theseus atau Pelias?", "Bakit hindi pinili ni Minos sina Theseus o Pelias?"), "choices": [("Mereka terlalu muda", "Masyado silang bata"), ("Pertengkaran mereka dapat memecah kerajaan", "Maaaring hatiin ng kanilang pag-aaway ang kaharian"), ("Mereka tidak berada di istana", "Wala sila sa palasyo")], "correct": 1, "reason": ("Minos khawatir persaingan mereka akan menimbulkan perang dan kebingungan.", "Nag-alala si Minos na magdudulot ng digmaan at kaguluhan ang kanilang tunggalian.")},
            {"prompt": ("Sifat apa yang membuat Jason dipilih?", "Anong katangian ang dahilan kung bakit pinili si Jason?"), "choices": [("Kebaikan", "Kabaitan"), ("Kekuatan fisik", "Lakas ng katawan"), ("Keahlian pedang", "Galing sa espada")], "correct": 0, "reason": ("Raja percaya kebaikan Jason akan membawa perdamaian.", "Naniwala ang hari na magdadala ng kapayapaan ang kabaitan ni Jason.")},
            {"prompt": ("Apa yang disesali kedua kakak Jason?", "Ano ang pinagsisihan ng dalawang kapatid ni Jason?"), "choices": [("Tidak memenangkan perlombaan", "Hindi sila nanalo sa paligsahan"), ("Kehilangan pedang", "Nawala ang kanilang espada"), ("Tidak sempat berpamitan kepada ayah", "Hindi sila nakapagpaalam sa ama")], "correct": 2, "reason": ("Mereka sibuk bertarung ketika ayah mereka menjalani saat-saat terakhirnya.", "Abala sila sa paglalaban habang nasa huling sandali ang kanilang ama.")},
        ],
    },
    {
        "title": "How the Sun and the Moon Were Made",
        "category": "Mitos Inuit",
        "summary": ("Dalam sebuah kisah Inuit, seorang gadis mengungkap kejahatan saudaranya lalu mengejarnya hingga mereka menjadi bulan dan matahari.", "Sa isang kuwentong Inuit, natukoy ng isang dalaga ang masamang ginawa ng kaniyang kapatid at hinabol ito hanggang maging buwan at araw silang dalawa."),
        "characters": ["a kind girl", "her mean brother"],
        "setting": "An Inuit party, the woods, and the sky.",
        "theme": ("Wrongdoing is exposed and carries lasting consequences.", "pengungkapan kesalahan dan akibatnya", "pagbubunyag ng kasalanan at bunga nito"),
        "events": ["The siblings attend a party.", "Someone attacks the girl in darkness.", "She uses black dirt in her decorated hair to identify the attacker as her brother.", "They chase each other with fire, grow enormous, and become the moon and sun."],
        "sentences": [
            ("Sebuah kisah Inuit bercerita tentang gadis baik dan adik laki-lakinya yang kejam.", "Isang kuwentong Inuit ang nagsasalaysay tungkol sa mabait na dalaga at sa masamang nakababatang kapatid niyang lalaki."),
            ("Mereka pergi ke sebuah pesta, tetapi ketika lampu dipadamkan seseorang menarik rambut dan merobek pakaian gadis itu.", "Pumunta sila sa isang piging, ngunit nang patayin ang ilaw ay may humila sa buhok at pumunit sa damit ng dalaga."),
            ("Untuk mengenali pelakunya, ia menata rambutnya lagi dengan perhiasan dan menaruh kotoran hitam di dalamnya.", "Upang makilala ang may sala, inayos niyang muli ang buhok na may mga hiyas at nilagyan iyon ng maitim na uling."),
            ("Serangan itu terulang, lalu ia menemukan satu-satunya orang yang tangannya menjadi hitam: saudaranya sendiri.", "Naulit ang pangyayari at natukoy niya ang kaisa-isang may maitim na kamay—ang sarili niyang kapatid."),
            ("Anak laki-laki itu melarikan diri ke hutan, dan gadis tersebut mengejarnya sambil keduanya membawa api sebagai penerang.", "Tumakas sa gubat ang lalaki at hinabol siya ng dalaga habang kapwa sila may dalang apoy bilang tanglaw."),
            ("Saat berlari, tubuh mereka membesar dan mereka naik ke angkasa.", "Habang tumatakbo, lumaki ang kanilang mga katawan at umakyat sila sa kalangitan."),
            ("Gadis itu menjadi bulan, saudaranya menjadi matahari, dan sejak itu mereka saling mengejar di langit.", "Naging buwan ang dalaga at naging araw ang kapatid niya; mula noon ay naghahabulan sila sa langit."),
        ],
        "vocabulary": [("kuwentong Inuit", "kisah Inuit", "parirala"), ("piging", "pesta", "pangngalan"), ("hiyas", "perhiasan", "pangngalan"), ("uling", "arang hitam", "pangngalan"), ("natukoy", "mengidentifikasi", "pandiwa"), ("hinabol", "mengejar", "pandiwa"), ("tanglaw", "penerang", "pangngalan"), ("kalangitan", "angkasa", "pangngalan")],
        "expressions": [("nang patayin ang ilaw", "ketika lampu dipadamkan"), ("mula noon ay naghahabulan sila", "sejak itu mereka saling mengejar")],
        "grammar": ("Nang + bentuk verba menandai waktu ketika peristiwa lain terjadi. Kapwa menegaskan bahwa dua tokoh melakukan atau memiliki hal yang sama.", "Ginagamit ang nang + pandiwa upang tukuyin ang oras ng ibang pangyayari. Binibigyang-diin ng kapwa na pareho ang ginagawa o taglay ng dalawang tauhan."),
        "questions": [
            {"prompt": ("Bagaimana gadis itu menandai pelaku?", "Paano minarkahan ng dalaga ang may sala?"), "choices": [("Dengan cat merah", "Sa pulang pintura"), ("Dengan kotoran hitam di rambutnya", "Sa maitim na uling sa kaniyang buhok"), ("Dengan air", "Sa tubig")], "correct": 1, "reason": ("Kotoran hitam berpindah ke tangan orang yang kembali menarik rambutnya.", "Lumipat ang maitim na uling sa kamay ng muling humila sa kaniyang buhok.")},
            {"prompt": ("Siapa yang ternyata menyerang gadis itu?", "Sino pala ang nanakit sa dalaga?"), "choices": [("Saudaranya", "Kaniyang kapatid"), ("Orang asing", "Isang estranghero"), ("Temannya", "Kaniyang kaibigan")], "correct": 0, "reason": ("Ia mengenali saudaranya sebagai satu-satunya orang bertangan hitam.", "Nakilala niya ang kapatid bilang kaisa-isang may maitim na kamay.")},
            {"prompt": ("Menjadi apakah kedua saudara itu?", "Ano ang kinahinatnan ng magkapatid?"), "choices": [("Bintang dan awan", "Bituin at ulap"), ("Gunung dan sungai", "Bundok at ilog"), ("Bulan dan matahari", "Buwan at araw")], "correct": 2, "reason": ("Gadis itu menjadi bulan, sedangkan saudaranya menjadi matahari.", "Naging buwan ang dalaga, samantalang naging araw ang kaniyang kapatid.")},
        ],
    },
    {
        "title": "The Starfish",
        "category": "Kepedulian dan tindakan",
        "summary": ("Seorang gadis kecil menunjukkan bahwa menyelamatkan satu bintang laut tetap berarti, meskipun ia tidak dapat menyelamatkan semuanya.", "Ipinakita ng isang batang babae na mahalaga pa ring mailigtas ang isang bituing-dagat kahit hindi niya kayang iligtas ang lahat."),
        "characters": ["the narrator", "a little girl"],
        "setting": "An island beach at evening after the tide leaves starfish on the sand.",
        "theme": ("A small action matters to the individual it helps.", "arti tindakan kecil", "halaga ng munting kilos"),
        "events": ["The narrator sees many starfish stranded by the waves.", "A little girl asks for help and then begins throwing starfish back.", "The narrator argues that she cannot save all of them.", "She answers that saving one still matters to that starfish."],
        "sentences": [
            ("Saat berjalan sore di pantai sebuah pulau, seorang pelancong melihat banyak bintang laut terdampar di pasir.", "Habang naglalakad sa dalampasigan ng isang pulo, nakakita ang isang manlalakbay ng maraming bituing-dagat na napadpad sa buhangin."),
            ("Sebagian kembali terbawa ombak, tetapi yang lain akan mati jika tetap berada di luar air.", "Nadala ng alon pabalik ang ilan, ngunit mamamatay ang iba kung mananatili sila sa labas ng tubig."),
            ("Pelancong itu sedih, tetapi merasa jumlahnya terlalu banyak untuk ditolong.", "Nalungkot ang manlalakbay, ngunit inakala niyang napakarami ng mga ito upang matulungan."),
            ("Seorang gadis kecil juga sedih lalu mulai melemparkan bintang laut satu per satu ke laut.", "Nalungkot din ang isang batang babae at nagsimulang ibalik sa dagat ang mga bituing-dagat nang isa-isa."),
            ("Pelancong itu berkata bahwa ia tidak mungkin menyelamatkan semuanya.", "Sinabi ng manlalakbay na hindi niya kayang iligtas ang lahat."),
            ("Gadis itu mengangkat seekor bintang laut dan menjawab bahwa ia tetap dapat menyelamatkan yang satu ini.", "Itinaas ng bata ang isang bituing-dagat at sinabing maililigtas pa rin niya ang isang ito."),
            ("Ia melemparkannya ke air, membuktikan bahwa setiap tindakan baik memiliki arti bagi yang ditolong.", "Inihagis niya iyon sa tubig at pinatunayan na may kabuluhan ang bawat mabuting kilos sa inililigtas nito."),
        ],
        "vocabulary": [("dalampasigan", "pantai", "pangngalan"), ("bituing-dagat", "bintang laut", "pangngalan"), ("napadpad", "terdampar", "pandiwa"), ("alon", "ombak", "pangngalan"), ("mamamatay", "akan mati", "pandiwa"), ("isa-isa", "satu per satu", "pang-abay"), ("iligtas", "menyelamatkan", "pandiwa"), ("kabuluhan", "arti", "pangngalan")],
        "expressions": [("hindi niya kayang iligtas ang lahat", "ia tidak mampu menyelamatkan semuanya"), ("may kabuluhan ang bawat mabuting kilos", "setiap tindakan baik memiliki arti")],
        "grammar": ("Kung menyatakan syarat: bintang laut akan mati jika tidak kembali ke air. Bawat menekankan setiap anggota dalam suatu kelompok.", "Ginagamit ang kung sa kondisyon: mamamatay ang bituing-dagat kung hindi ito makababalik sa tubig. Binibigyang-diin ng bawat ang isa-isang kasapi ng pangkat."),
        "questions": [
            {"prompt": ("Mengapa bintang laut di pasir berada dalam bahaya?", "Bakit nanganganib ang mga bituing-dagat sa buhangin?"), "choices": [("Mereka terlalu dingin", "Masyado silang nilalamig"), ("Mereka akan mati di luar air", "Mamamatay sila sa labas ng tubig"), ("Burung mengejar mereka", "Hinahabol sila ng mga ibon")], "correct": 1, "reason": ("Bintang laut yang tidak kembali ke laut tidak dapat bertahan hidup.", "Hindi mabubuhay ang mga bituing-dagat na hindi makababalik sa dagat.")},
            {"prompt": ("Apa yang dilakukan gadis kecil?", "Ano ang ginawa ng batang babae?"), "choices": [("Mengumpulkan kerang", "Nangolekta ng kabibe"), ("Menunggu ombak", "Naghintay ng alon"), ("Melemparkan bintang laut kembali ke air", "Ibinalik sa tubig ang mga bituing-dagat")], "correct": 2, "reason": ("Ia menyelamatkan sebanyak yang dapat dijangkaunya satu per satu.", "Iniligtas niya nang isa-isa ang kaya niyang abutin.")},
            {"prompt": ("Apa makna jawaban ‘saya dapat menyelamatkan yang satu ini’?", "Ano ang ibig sabihin ng “maililigtas ko ang isang ito”?"), "choices": [("Satu tindakan tetap berguna bagi yang ditolong", "Mahalaga pa rin ang isang kilos sa tinutulungan"), ("Hanya satu bintang laut yang penting", "Iisa lamang ang mahalagang bituing-dagat"), ("Tidak perlu mencoba", "Hindi kailangang sumubok")], "correct": 0, "reason": ("Gadis itu berfokus pada perbedaan nyata yang dapat ia buat sekarang.", "Nakatuon ang bata sa tunay na pagbabagong kaya niyang gawin sa sandaling iyon.")},
        ],
    },
    {
        "title": "The First Peacock",
        "category": "Mitologi Yunani",
        "summary": ("Argos yang bermata seratus gagal menjaga sapi Hera setelah ditidurkan oleh musik, lalu matanya diabadikan pada ekor merak dan di langit.", "Nabigo ang sandaang-matang si Argos na bantayan ang baka ni Hera matapos siyang patulugin ng musika, kaya inilagay ang kaniyang mga mata sa buntot ng paboreal at sa kalangitan."),
        "characters": ["Argos", "Hera", "Zeus", "a musician", "Hera's cow"],
        "setting": "Ancient Greece and the night sky.",
        "theme": ("Deception can cause an innocent servant to suffer consequences.", "penipuan dan akibatnya", "panlilinlang at bunga nito"),
        "events": ["Argos uses his hundred eyes to guard Hera's special cow.", "Zeus sends a musician whose song puts Argos to sleep.", "Zeus steals the cow and Hera transforms Argos into a peacock.", "Argos's eyes appear on the peacock's tail, and Zeus later places his image among the stars."],
        "sentences": [
            ("Dalam mitologi Yunani, Argos dilahirkan dengan seratus mata dan menjadi penjaga yang sangat waspada.", "Sa mitolohiyang Griyego, isinilang si Argos na may sandaang mata at naging napakaingat na tagapagbantay."),
            ("Dewi Hera menyuruhnya menjaga sapi kesayangannya dan memisahkannya dari semua orang.", "Inutusan siya ng diyosang si Hera na bantayan ang paborito nitong baka at ilayo iyon sa lahat."),
            ("Zeus ingin mengambil sapi itu, maka ia mengirim seorang pemain musik untuk memainkan lagu yang menenangkan.", "Nais kunin ni Zeus ang baka kaya nagpadala siya ng musikero upang tumugtog ng nakaaantok na awit."),
            ("Musik tersebut membuat semua mata Argos tertutup dan ia pun tertidur.", "Dahil sa tugtog, napikit ang lahat ng mata ni Argos at nakatulog siya."),
            ("Zeus membawa pergi sapi itu, dan Hera yang marah menghukum Argos dengan mengubahnya menjadi merak.", "Kinuha ni Zeus ang baka, at bilang parusa ay ginawang paboreal ng galit na si Hera si Argos."),
            ("Seratus matanya menjadi pola pada ekor merak yang lebar.", "Naging mga hugis sa malapad na buntot ng paboreal ang kaniyang sandaang mata."),
            ("Karena melihat penderitaan Argos, Zeus kemudian menempatkan gambarnya sebagai gugusan bintang agar tetap terlihat di langit.", "Nang makita ang hirap ni Argos, inilagay ni Zeus ang kaniyang larawan bilang konstelasyon upang manatili ito sa kalangitan."),
        ],
        "vocabulary": [("mitolohiyang Griyego", "mitologi Yunani", "parirala"), ("sandaang mata", "seratus mata", "parirala"), ("tagapagbantay", "penjaga", "pangngalan"), ("diyosa", "dewi", "pangngalan"), ("musikero", "pemain musik", "pangngalan"), ("nakatulog", "tertidur", "pandiwa"), ("paboreal", "merak", "pangngalan"), ("konstelasyon", "gugusan bintang", "pangngalan")],
        "expressions": [("bilang parusa", "sebagai hukuman"), ("upang manatili ito sa kalangitan", "agar tetap berada di langit")],
        "grammar": ("Kaya memperkenalkan akibat dari keinginan Zeus. Bilang + nomina dapat menunjukkan fungsi atau keadaan, seperti bilang parusa.", "Ipinakikilala ng kaya ang bunga ng kagustuhan ni Zeus. Maaaring ipakita ng bilang + pangngalan ang gamit o kalagayan, gaya ng bilang parusa."),
        "questions": [
            {"prompt": ("Mengapa Argos cocok menjadi penjaga?", "Bakit mahusay na tagapagbantay si Argos?"), "choices": [("Ia mempunyai seratus mata", "May sandaang mata siya"), ("Ia dapat terbang", "Nakakalipad siya"), ("Ia seorang dewa", "Isa siyang diyos")], "correct": 0, "reason": ("Banyak matanya memungkinkan sebagian tetap berjaga ketika yang lain beristirahat.", "Dahil sa dami ng kaniyang mata, may nananatiling gising habang nagpapahinga ang iba.")},
            {"prompt": ("Bagaimana Zeus membuat Argos tertidur?", "Paano pinatulog ni Zeus si Argos?"), "choices": [("Dengan makanan", "Sa pagkain"), ("Dengan musik", "Sa musika"), ("Dengan ramuan", "Sa inumin")], "correct": 1, "reason": ("Lagu pemain musik membuat Argos kehilangan fokus dan menutup semua matanya.", "Dahil sa awit ng musikero, nawalan ng pokus si Argos at napikit ang lahat ng mata niya.")},
            {"prompt": ("Di mana mata Argos ditempatkan dalam cerita?", "Saan inilagay ang mga mata ni Argos sa kuwento?"), "choices": [("Pada sayap elang", "Sa pakpak ng agila"), ("Pada kulit sapi", "Sa balat ng baka"), ("Pada ekor merak", "Sa buntot ng paboreal")], "correct": 2, "reason": ("Hera mengubah mata-mata itu menjadi pola pada ekor merak.", "Ginawang mga hugis ni Hera sa buntot ng paboreal ang mga mata.")},
        ],
    },
])

STORIES.extend([
    {
        "title": "Katy",
        "category": "Kebaikan dan kesehatan",
        "summary": ("Katy tetap menghibur pasien lain meskipun menderita sakit otak, lalu kembali membantu rumah sakit setelah operasinya berhasil.", "Patuloy na pinasaya ni Katy ang ibang pasyente kahit may karamdaman siya sa utak, at bumalik siyang tumulong sa ospital matapos ang matagumpay na operasyon."),
        "characters": ["Katy", "the nurse narrator", "Tommy", "doctors", "other patients"],
        "setting": "A hospital before and after Katy's brain operation.",
        "theme": ("Kindness and courage can inspire an entire community during illness.", "kebaikan dan keberanian saat sakit", "kabaitan at tapang sa panahon ng sakit"),
        "events": ["A nurse meets eight-year-old Katy, who has a painful problem at the base of her brain.", "Katy uses her limited strength to play with, paint for, and gather flowers for other patients.", "Doctors successfully operate on her.", "After recovering, Katy returns to read and play with hospital patients."],
        "sentences": [
            ("Seorang perawat bertemu Katy yang berusia delapan tahun di rumah sakit karena ia mengalami nyeri akibat masalah pada bagian bawah otaknya.", "Nakilala ng isang nars ang walong taong gulang na si Katy sa ospital dahil may matinding kirot mula sa suliranin sa ibabang bahagi ng kaniyang utak."),
            ("Meskipun tubuhnya lemah, Katy duduk bersama Tommy dan bermain agar anak kecil itu merasa gembira.", "Kahit mahina ang katawan, umupo si Katy sa tabi ni Tommy at nakipaglaro upang mapasaya ang batang pasyente."),
            ("Ia jarang menunjukkan rasa sakit dan selalu mencari cara untuk membuat pasien lain tersenyum.", "Bihira niyang ipakita ang sakit at palagi siyang naghahanap ng paraan upang mapangiti ang ibang mga pasyente."),
            ("Katy melukis untuk seorang pasien tua dan mengambil bunga bagi gadis kecil yang sakit.", "Gumuhit si Katy para sa matandang pasyente at kumuha ng mga bulaklak para sa isang batang babaeng may sakit."),
            ("Para dokter segera melakukan operasi pada otaknya, dan prosedur itu berhasil.", "Agad nagsagawa ang mga doktor ng operasyon sa kaniyang utak, at naging matagumpay iyon."),
            ("Sebulan kemudian Katy pulih dan boleh meninggalkan rumah sakit.", "Pagkaraan ng isang buwan, gumaling si Katy at nakauwi mula sa ospital."),
            ("Namun, ia terus kembali untuk bermain dan membaca bersama para pasien; karena kabutihan dan keberaniannya, semua orang menganggapnya pahlawan.", "Gayunman, patuloy siyang bumalik upang makipaglaro at magbasa sa mga pasyente; dahil sa kaniyang kabutihan at tapang, itinuring siya ng lahat na bayani."),
        ],
        "vocabulary": [("nars", "perawat", "pangngalan"), ("kirot", "nyeri", "pangngalan"), ("utak", "otak", "pangngalan"), ("pasyente", "pasien", "pangngalan"), ("operasyon", "operasi", "pangngalan"), ("matagumpay", "berhasil", "pang-uri"), ("gumaling", "pulih", "pandiwa"), ("kabutihan", "kebaikan", "pangngalan")],
        "expressions": [("kahit mahina ang katawan", "meskipun tubuh lemah"), ("itinuring siya ng lahat na bayani", "semua orang menganggapnya pahlawan")],
        "grammar": ("Kahit menyatakan kontras antara kondisi Katy dan tindakannya. Upang + verba menjelaskan tujuan ia bermain dan kembali ke rumah sakit.", "Ipinakikita ng kahit ang salungatan ng kalagayan at kilos ni Katy. Ipinapahayag ng upang + pandiwa ang layunin ng kaniyang pakikipaglaro at pagbabalik sa ospital."),
        "questions": [
            {"prompt": ("Mengapa Katy berada di rumah sakit?", "Bakit nasa ospital si Katy?"), "choices": [("Ada masalah pada otaknya", "May suliranin sa kaniyang utak"), ("Ia mengunjungi Tommy", "Dumalaw siya kay Tommy"), ("Ia bekerja sebagai perawat", "Nagtatrabaho siya bilang nars")], "correct": 0, "reason": ("Dokter menemukan masalah menyakitkan di bagian bawah otak Katy.", "Natuklasan ng mga doktor ang masakit na suliranin sa ibabang bahagi ng utak ni Katy.")},
            {"prompt": ("Bagaimana Katy membantu pasien lain sebelum operasi?", "Paano tinulungan ni Katy ang ibang pasyente bago ang operasyon?"), "choices": [("Ia memberi mereka obat", "Binigyan niya sila ng gamot"), ("Ia bermain, melukis, dan membawa bunga", "Nakipaglaro, gumuhit, at nagdala siya ng bulaklak"), ("Ia mengantar mereka pulang", "Inihatid niya sila pauwi")], "correct": 1, "reason": ("Katy memakai tenaga yang dimilikinya untuk menghibur orang lain.", "Ginamit ni Katy ang natitira niyang lakas upang pasayahin ang iba.")},
            {"prompt": ("Apa yang dilakukan Katy setelah pulih?", "Ano ang ginawa ni Katy matapos gumaling?"), "choices": [("Ia pindah jauh", "Lumipat siya sa malayo"), ("Ia melupakan rumah sakit", "Kinalimutan niya ang ospital"), ("Ia kembali membantu para pasien", "Bumalik siyang tumulong sa mga pasyente")], "correct": 2, "reason": ("Ia terus datang untuk bermain dengan anak-anak dan membaca bagi pasien yang lebih tua.", "Patuloy siyang dumalaw upang makipaglaro sa mga bata at magbasa sa matatandang pasyente.")},
        ],
    },
    {
        "title": "A Better Reward",
        "category": "Kepedulian pada hewan",
        "summary": ("Jenny mengejar pencuri makanan dan menemukan induk anjing yang memberi makan anak-anaknya; menyelamatkan mereka menjadi hadiah yang lebih baik.", "Hinabol ni Jenny ang magnanakaw ng pagkain at natuklasang inang aso pala itong nagpapakain sa mga tuta; ang pagliligtas sa kanila ang naging mas mabuting gantimpala."),
        "characters": ["Jenny", "Jim", "a mother dog", "the puppies", "restaurant staff", "the police"],
        "setting": "A restaurant delivery area and the neighborhood around a customer's house.",
        "theme": ("Compassion can be more rewarding than money or punishment.", "belas kasih sebagai hadiah", "habag bilang gantimpala"),
        "events": ["Jenny reads about an uncaught food thief and a police reward.", "Against Jim's advice, she chases the thief after a delivery is stolen.", "She discovers a thin mother dog feeding puppies.", "The restaurant workers adopt the dogs, and Jenny values her new dog over the cash reward."],
        "sentences": [
            ("Jenny bekerja mengantar makanan dan membaca berita tentang pencuri yang mengambil porsi sangat besar.", "Naghahatid ng pagkain si Jenny at nakabasa siya ng balita tungkol sa magnanakaw na kumukuha ng napakaraming pagkain."),
            ("Polisi menawarkan hadiah, tetapi manajernya, Jim, memperingatkan agar ia tidak mengejar siapa pun sendirian.", "Nag-alok ng gantimpala ang pulisya, ngunit binalaan siya ng manager na si Jim na huwag humabol nang mag-isa."),
            ("Ketika makanan hilang dari mobilnya saat pengantaran, Jenny tetap mengejar suara di sekitar sudut jalan.", "Nang mawala ang pagkain sa kaniyang sasakyan habang naghahatid, hinabol pa rin ni Jenny ang tunog sa kanto."),
            ("Ia terkejut menemukan seekor induk anjing kurus dan beberapa anak anjing sedang memakan makanan itu.", "Nagulat siyang makita ang payat na inang aso at ilang tuta na kumakain ng ninakaw na pagkain."),
            ("Jenny mengerti bahwa induk itu mencuri banyak karena harus memberi makan anak-anaknya.", "Naunawaan ni Jenny na marami itong kinukuha upang mapakain ang mga tuta."),
            ("Ia memberi mereka makanan lagi dan membawa semuanya ke restoran, tempat para pekerja mengadopsi setiap anak anjing.", "Muli niya silang pinakain at dinala sa restoran, kung saan inampon ng mga manggagawa ang bawat tuta."),
            ("Jenny tidak lagi mengejar uang hadiah; anjing barunya dan kesempatan menunjukkan belas kasih menjadi hadiah yang lebih baik.", "Hindi na salapi ang hinabol ni Jenny; ang bagong aso at pagkakataong magpakita ng habag ang naging mas mabuting gantimpala."),
        ],
        "vocabulary": [("naghahatid", "mengantar", "pandiwa"), ("magnanakaw", "pencuri", "pangngalan"), ("gantimpala", "hadiah", "pangngalan"), ("hinabol", "mengejar", "pandiwa"), ("payat", "kurus", "pang-uri"), ("tuta", "anak anjing", "pangngalan"), ("inampon", "mengadopsi", "pandiwa"), ("habag", "belas kasih", "pangngalan")],
        "expressions": [("huwag humabol nang mag-isa", "jangan mengejar sendirian"), ("mas mabuting gantimpala", "hadiah yang lebih baik")],
        "grammar": ("Upang menjelaskan tujuan induk anjing mengambil makanan. Mas + adjektiva membandingkan nilai dua jenis hadiah.", "Ipinakikilala ng upang ang layunin ng inang aso sa pagkuha ng pagkain. Inihahambing ng mas + pang-uri ang halaga ng dalawang gantimpala."),
        "questions": [
            {"prompt": ("Siapa ‘pencuri’ makanan sebenarnya?", "Sino pala ang “magnanakaw” ng pagkain?"), "choices": [("Seekor induk anjing", "Isang inang aso"), ("Seorang pelanggan", "Isang kostumer"), ("Jim", "Si Jim")], "correct": 0, "reason": ("Jenny menemukan anjing itu bersama anak-anaknya setelah mengikuti suara.", "Natagpuan ni Jenny ang aso kasama ang mga tuta matapos sundan ang tunog.")},
            {"prompt": ("Mengapa anjing itu mengambil begitu banyak makanan?", "Bakit napakaraming pagkain ang kinukuha ng aso?"), "choices": [("Untuk menyimpannya", "Upang itago iyon"), ("Untuk memberi makan anak-anaknya", "Upang pakainin ang mga tuta"), ("Untuk menjualnya", "Upang ipagbili iyon")], "correct": 1, "reason": ("Induk yang kurus itu berusaha memenuhi kebutuhan beberapa anak anjing.", "Sinisikap ng payat na ina na mapakain ang ilang tuta.")},
            {"prompt": ("Apa hadiah yang lebih baik bagi Jenny?", "Ano ang mas mabuting gantimpala para kay Jenny?"), "choices": [("Berita di koran", "Balita sa diyaryo"), ("Makanan gratis", "Libreng pagkain"), ("Anjing baru dan keselamatan para anak anjing", "Bagong aso at kaligtasan ng mga tuta")], "correct": 2, "reason": ("Jenny lebih menghargai menyelamatkan dan mengadopsi anjing daripada menerima uang.", "Mas pinahalagahan ni Jenny ang pagliligtas at pag-ampon kaysa salapi.")},
        ],
    },
    {
        "title": "The camp",
        "category": "Perkemahan dan persahabatan",
        "summary": ("Stacie membenci perkemahan sampai permainan merebut bendera menunjukkan bahwa ia dapat bersenang-senang, membantu tim, dan mendapat teman.", "Ayaw ni Stacie sa kampo hanggang ipakita ng larong agawan ng watawat na kaya niyang magsaya, tumulong sa koponan, at magkaroon ng mga kaibigan."),
        "characters": ["Stacie", "her parents", "blue-team campers", "red-team campers"],
        "setting": "A noisy summer camp near an airport and its forest game area.",
        "theme": ("Trying an unwanted new experience can reveal confidence and friendship.", "mencoba pengalaman baru", "pagsubok sa bagong karanasan"),
        "events": ["Stacie resents being sent to a camp with plain food, swimming, noise, and spider webs.", "She attends water-safety class and reluctantly joins a water-gun flag game.", "Stacie discovers that she enjoys the game and captures the red flag.", "Her blue team wins, and she enjoys the remaining week with new friends."],
        "sentences": [
            ("Stacie ingin berlibur di hotel, tetapi orang tuanya mengirimnya ke perkemahan yang menurutnya sangat buruk.", "Nais magbakasyon ni Stacie sa hotel, ngunit ipinadala siya ng mga magulang sa kampong napakapangit para sa kaniya."),
            ("Ia tidak menyukai air untuk sarapan, kewajiban berenang, suara pesawat, atau sarang laba-laba di atas tempat tidur.", "Ayaw niya sa tubig na inumin sa almusal, sa sapilitang paglangoy, sa ingay ng eroplano, at sa sapot sa ibabaw ng kama."),
            ("Setelah kelas keselamatan air, Stacie harus ikut permainan dua tim yang memakai pistol air dan berebut bendera.", "Matapos ang klase sa kaligtasan sa tubig, kinailangang sumali si Stacie sa laro ng dalawang koponan na may water gun at agawan ng watawat."),
            ("Meskipun merasa bukan atlet, ia bersembunyi di balik pohon dan berhasil mengenai pemain tim merah.", "Kahit inakala niyang hindi siya atleta, nagtago siya sa likod ng puno at natamaan ang manlalaro ng pulang koponan."),
            ("Stacie mulai menikmati permainan, maju lebih jauh, dan melihat bendera merah dijaga seorang lawan.", "Nagsimula siyang masiyahan sa laro, sumulong, at nakita ang pulang watawat na binabantayan ng kalaban."),
            ("Ia menembak penjaga itu, mengambil bendera, dan berlari kembali sehingga tim biru menang.", "Tinamaan niya ang bantay, kinuha ang watawat, at tumakbo pabalik kaya nagwagi ang asul na koponan."),
            ("Sejak itu Stacie menikmati sisa minggu di perkemahan dan mendapat teman-teman baru.", "Mula noon ay nasiyahan si Stacie sa natitirang linggo sa kampo at nagkaroon ng mga bagong kaibigan."),
        ],
        "vocabulary": [("kampo", "perkemahan", "pangngalan"), ("sapot", "sarang laba-laba", "pangngalan"), ("koponan", "tim", "pangngalan"), ("watawat", "bendera", "pangngalan"), ("nagtago", "bersembunyi", "pandiwa"), ("sumulong", "maju", "pandiwa"), ("nagwagi", "menang", "pandiwa"), ("kaibigan", "teman", "pangngalan")],
        "expressions": [("kahit inakala niyang hindi siya atleta", "meskipun ia merasa bukan atlet"), ("mula noon ay nasiyahan siya", "sejak itu ia menikmatinya")],
        "grammar": ("Kahit memperkenalkan tindakan yang bertentangan dengan keyakinan Stacie. Kaya menghubungkan keberhasilannya mengambil bendera dengan kemenangan tim.", "Ipinakikilala ng kahit ang kilos na salungat sa paniniwala ni Stacie. Iniuugnay ng kaya ang pagkuha niya sa watawat at ang panalo ng koponan."),
        "questions": [
            {"prompt": ("Mengapa Stacie awalnya membenci perkemahan?", "Bakit ayaw ni Stacie sa kampo noong una?"), "choices": [("Kondisinya tidak sesuai dengan keinginannya", "Hindi tugma sa gusto niya ang mga kalagayan doon"), ("Tidak ada permainan", "Walang anumang laro"), ("Orang tuanya tinggal bersamanya", "Kasama niya roon ang mga magulang")], "correct": 0, "reason": ("Makanan, kegiatan, kebisingan, dan tempat tidur semuanya berbeda dari liburan yang ia inginkan.", "Iba sa gusto niyang bakasyon ang pagkain, gawain, ingay, at tulugan.")},
            {"prompt": ("Apa tujuan permainan tim?", "Ano ang layunin ng laro ng mga koponan?"), "choices": [("Membangun tenda", "Magtayo ng tolda"), ("Merebut bendera lawan", "Kunin ang watawat ng kalaban"), ("Berenang paling jauh", "Lumangoy nang pinakamalayo")], "correct": 1, "reason": ("Kedua tim harus melindungi bendera sendiri sambil berusaha mengambil bendera lawan.", "Kailangang bantayan ng bawat koponan ang sariling watawat habang kinukuha ang sa kalaban.")},
            {"prompt": ("Apa yang mengubah sikap Stacie?", "Ano ang nagpabago sa saloobin ni Stacie?"), "choices": [("Ia pindah ke hotel", "Lumipat siya sa hotel"), ("Pesawat berhenti terbang", "Tumigil ang mga eroplano"), ("Ia menikmati permainan, membantu tim menang, dan mendapat teman", "Nasiyahan siya sa laro, tumulong manalo, at nagkaroon ng kaibigan")], "correct": 2, "reason": ("Keberhasilan dalam permainan membuat Stacie melihat sisi menyenangkan dari perkemahan.", "Dahil sa tagumpay sa laro, nakita ni Stacie ang masayang bahagi ng kampo.")},
        ],
    },
    {
        "title": "A Strong Friendship",
        "category": "Kerja sama",
        "summary": ("Tim yang kuat dan Jack yang cerdas menyelamatkan kota bersalju dengan menggabungkan kemampuan mereka dan akhirnya menjadi sahabat.", "Iniligtas ng malakas na si Tim at matalinong si Jack ang bayang nabalot ng niyebe sa pamamagitan ng pagsasama ng kanilang kakayahan, at naging magkaibigan sila."),
        "characters": ["Tim", "Jack", "the snowbound townspeople"],
        "setting": "A town buried in snow and narrow passages beneath it.",
        "theme": ("Different strengths become powerful through cooperation and friendship.", "kekuatan berbeda dalam kerja sama", "magkakaibang lakas sa pagtutulungan"),
        "events": ["Strong, famous Tim and smart, jealous Jack compete for recognition.", "A snowstorm traps the town without food.", "Jack finds passages; Tim breaks ice blocks until exhausted.", "Jack retrieves food and guides Tim home, teaching both men friendship."],
        "sentences": [
            ("Tim dikenal sebagai orang terkuat di kota, sedangkan Jack adalah orang paling pintar tetapi iri karena jarang diperhatikan.", "Kilala si Tim bilang pinakamalakas sa bayan, samantalang si Jack ang pinakamatalino ngunit naiinggit dahil bihira siyang mapansin."),
            ("Badai salju menutup seluruh kota dan membuat penduduk kekurangan makanan.", "Tinabunan ng bagyo ng niyebe ang buong bayan at kinulang sa pagkain ang mga mamamayan."),
            ("Tim dan Jack pergi bersama; Jack menemukan lorong-lorong sempit di bawah salju yang menuju kota lain.", "Magkasamang umalis sina Tim at Jack; nakakita si Jack ng makikitid na lagusan sa ilalim ng niyebe patungo sa ibang bayan."),
            ("Ketika balok es menghalangi jalan, Tim memecahkannya dengan kekuatan sampai ia sangat lelah.", "Nang humarang ang mga bloke ng yelo, binasag iyon ni Tim gamit ang lakas hanggang mapagod siya nang husto."),
            ("Jack melanjutkan perjalanan sendirian, mengambil makanan, lalu kembali kepada Tim.", "Nagpatuloy mag-isa si Jack, kumuha ng pagkain, at saka bumalik kay Tim."),
            ("Karena Tim tidak ingat lorong pulang, Jack menjadi penunjuk jalan, sementara Tim membantu membawa persediaan.", "Dahil hindi maalala ni Tim ang daan pauwi, gumabay si Jack habang tumulong naman si Tim sa pagdala ng pagkain."),
            ("Dengan saling mendukung, mereka menyelamatkan kota dan belajar bahwa persahabatan lebih penting daripada persaingan.", "Sa pagtutulungan, nailigtas nila ang bayan at natutuhan nilang mas mahalaga ang pagkakaibigan kaysa tunggalian."),
        ],
        "vocabulary": [("pinakamalakas", "paling kuat", "pang-uri"), ("pinakamatalino", "paling pintar", "pang-uri"), ("niyebe", "salju", "pangngalan"), ("lagusan", "lorong", "pangngalan"), ("yelo", "es", "pangngalan"), ("mapagod", "menjadi lelah", "pandiwa"), ("gumabay", "menuntun", "pandiwa"), ("pagtutulungan", "kerja sama", "pangngalan")],
        "expressions": [("sa pagtutulungan", "melalui kerja sama"), ("mas mahalaga kaysa tunggalian", "lebih penting daripada persaingan")],
        "grammar": ("Pinaka- membentuk tingkat paling tinggi, seperti pinakamalakas. Samantalang membandingkan peran Tim dan Jack.", "Binubuo ng pinaka- ang sukdulang antas, gaya ng pinakamalakas. Inihahambing ng samantalang ang mga papel nina Tim at Jack."),
        "questions": [
            {"prompt": ("Apa masalah yang dihadapi kota?", "Ano ang suliranin ng bayan?"), "choices": [("Salju menutup kota dan makanan menipis", "Tinabunan ng niyebe ang bayan at naubos ang pagkain"), ("Sungai meluap", "Umapaw ang ilog"), ("Jembatan terbakar", "Nasunog ang tulay")], "correct": 0, "reason": ("Badai membuat penduduk tidak dapat keluar untuk mendapatkan persediaan.", "Dahil sa bagyo, hindi makalabas ang mga tao upang kumuha ng pagkain.")},
            {"prompt": ("Bagaimana kekuatan Tim membantu perjalanan?", "Paano nakatulong ang lakas ni Tim sa paglalakbay?"), "choices": [("Ia menemukan lorong", "Natagpuan niya ang lagusan"), ("Ia memecahkan penghalang es", "Binasag niya ang mga harang na yelo"), ("Ia menggambar peta", "Gumuhit siya ng mapa")], "correct": 1, "reason": ("Tim membuka jalan melalui balok-balok es yang tidak dapat mereka lewati.", "Binuksan ni Tim ang daan sa mga blokeng yelong hindi nila madaanan.")},
            {"prompt": ("Apa kontribusi penting Jack?", "Ano ang mahalagang ambag ni Jack?"), "choices": [("Ia membuat salju mencair", "Tinunaw niya ang niyebe"), ("Ia mengangkat semua es", "Binuhat niya ang lahat ng yelo"), ("Ia menemukan jalan, mengambil makanan, dan menuntun pulang", "Nakahanap siya ng daan, kumuha ng pagkain, at gumabay pauwi")], "correct": 2, "reason": ("Pengetahuan dan arah Jack melengkapi kekuatan fisik Tim.", "Kinumpleto ng talino at paggabay ni Jack ang lakas ng katawan ni Tim.")},
        ],
    },
    {
        "title": "Joe’s Pond",
        "category": "Lingkungan",
        "summary": ("Terinspirasi video pencemaran, Joe mengorganisasi keluarga dan teman untuk membersihkan kolam taman selama enam minggu.", "Dahil sa bidyo tungkol sa polusyon, nag-organisa si Joe ng pamilya at mga kaibigan upang linisin ang lawa sa parke sa loob ng anim na linggo."),
        "characters": ["Joe", "Joe's grandfather", "family members", "friends and volunteers"],
        "setting": "A school, a public park, and a trash-filled pond.",
        "theme": ("Persistent community action can repair a damaged environment.", "aksi bersama untuk lingkungan", "sama-samang pagkilos para sa kapaligiran"),
        "events": ["A school video shows factory trash making river communities sick.", "Joe recognizes similar pollution in a park pond.", "His grandfather encourages him to continue the family's tradition of helping people.", "Joe organizes six weeks of cleanup until the pond is free of trash and safe for swimming."],
        "sentences": [
            ("Di sekolah, Joe menonton video tentang pabrik yang membuang sampah ke sungai dan membuat penduduk sakit.", "Sa paaralan, nanood si Joe ng bidyo tungkol sa pabrikang nagtatapon ng basura sa ilog at nagpapasakit sa mga naninirahan."),
            ("Video itu menjelaskan bahwa orang biasa dapat membuat perubahan bagi lingkungan mereka.", "Ipinaliwanag ng bidyo na kayang gumawa ng pagbabago ng karaniwang tao para sa kapaligiran."),
            ("Saat berjalan di taman, Joe melihat masalah serupa: kolam penuh gelas plastik dan sampah lain.", "Habang naglalakad sa parke, nakita ni Joe ang katulad na suliranin: punô ng plastik na baso at iba pang basura ang lawa."),
            ("Kakeknya mengingatkan bahwa membantu orang merupakan tradisi keluarga dan menyarankan Joe membersihkan taman.", "Ipinaalala ng kaniyang lolo na tradisyon ng pamilya ang pagtulong at iminungkahi niyang linisin ni Joe ang parke."),
            ("Joe mengorganisasi keluarga dan teman, lalu memberi setiap orang tongkat tajam untuk memungut sampah dengan aman.", "Nag-organisa si Joe ng pamilya at mga kaibigan at binigyan ang bawat isa ng matulis na patpat upang pulutin nang ligtas ang basura."),
            ("Mereka bekerja setiap minggu selama enam minggu, dan Joe selalu hadir meskipun para pembantu berganti-ganti.", "Linggo-linggo silang nagtrabaho sa loob ng anim na linggo, at laging naroon si Joe kahit nagpapalit ang ibang tumutulong."),
            ("Akhirnya air bersih dari sampah dan orang dapat berenang lagi, sehingga Joe melihat hasil nyata dari kepeduliannya.", "Sa huli, nalinis ang tubig at nakalangoy muli ang mga tao, kaya nakita ni Joe ang tunay na bunga ng malasakit sa kapaligiran."),
        ],
        "vocabulary": [("basura", "sampah", "pangngalan"), ("kapaligiran", "lingkungan", "pangngalan"), ("lawa", "kolam", "pangngalan"), ("nag-organisa", "mengorganisasi", "pandiwa"), ("matulis", "tajam", "pang-uri"), ("pulutin", "memungut", "pandiwa"), ("linggo-linggo", "setiap minggu", "pang-abay"), ("nalinis", "menjadi bersih", "pandiwa")],
        "expressions": [("gumawa ng pagbabago", "membuat perubahan"), ("malasakit sa kapaligiran", "kepedulian terhadap lingkungan")],
        "grammar": ("Upang + verba menyatakan tujuan memakai tongkat. Kahit menandai bahwa Joe tetap hadir walaupun relawan lain berubah.", "Ipinahahayag ng upang + pandiwa ang layunin ng paggamit ng patpat. Tinutukoy ng kahit na nanatili si Joe kahit nagpapalit ang ibang boluntaryo."),
        "questions": [
            {"prompt": ("Apa yang menginspirasi Joe membersihkan kolam?", "Ano ang nagbigay-inspirasyon kay Joe na linisin ang lawa?"), "choices": [("Video sekolah tentang pencemaran", "Bidyo sa paaralan tungkol sa polusyon"), ("Perlombaan taman", "Paligsahan sa parke"), ("Surat dari pabrik", "Liham mula sa pabrika")], "correct": 0, "reason": ("Video membantu Joe menghubungkan sampah di air dengan bahaya bagi manusia.", "Tinulungan ng bidyo si Joe na iugnay ang basura sa tubig at ang panganib nito sa tao.")},
            {"prompt": ("Untuk apa para relawan memakai tongkat tajam?", "Para saan ang matutulis na patpat ng mga tumulong?"), "choices": [("Menanam pohon", "Magtanim ng puno"), ("Memungut sampah", "Pulutin ang basura"), ("Mengukur air", "Sukatin ang tubig")], "correct": 1, "reason": ("Ujung tongkat membuat pengambilan sampah lebih mudah dan aman.", "Pinadali at ginawang mas ligtas ng dulo ng patpat ang pagpulot ng basura.")},
            {"prompt": ("Apa hasil setelah enam minggu?", "Ano ang resulta matapos ang anim na linggo?"), "choices": [("Kolam ditutup", "Isinara ang lawa"), ("Pabrik pindah", "Lumipat ang pabrika"), ("Kolam bebas sampah dan dapat dipakai berenang", "Wala nang basura sa lawa at maaari nang languyan")], "correct": 2, "reason": ("Kerja berulang kelompok itu memulihkan kebersihan air.", "Naibalik ng paulit-ulit na gawain ng pangkat ang kalinisan ng tubig.")},
        ],
    },
    {
        "title": "Archie and His Donkey",
        "category": "Fabel dan keputusan",
        "summary": ("Archie terus mengikuti nasihat setiap orang tentang cara membawa keledainya ke pasar, lalu kehilangan keledai dan kesempatan menjualnya.", "Sinunod ni Archie ang bawat payo tungkol sa pagdadala ng kaniyang asno sa bayan, kaya nawala ang asno at ang pagkakataong maipagbili ito."),
        "characters": ["Archie", "his son Tom", "a woman", "a farmer", "teenage boys", "the donkey"],
        "setting": "A long road to town and the town entrance.",
        "theme": ("Trying to please everyone can destroy one's own judgment and goal.", "keputusan mandiri", "sariling pagpapasya"),
        "events": ["Archie and Tom take a donkey to town to sell it.", "A woman says Archie should ride; a farmer later advises that neither should ride and that they should carry it.", "They arrive late while carrying the heavy donkey.", "Teenagers mock and stone them; the donkey escapes, leaving Archie with nothing."],
        "sentences": [
            ("Archie membutuhkan uang, jadi ia dan putranya, Tom, membawa keledai ke kota untuk dijual.", "Kailangan ni Archie ng pera, kaya dinala nila ng anak niyang si Tom ang asno sa bayan upang maipagbili."),
            ("Seorang perempuan mengatakan orang pintar seharusnya menunggangi keledai, maka Archie segera naik.", "Sinabi ng isang babae na dapat sumakay sa asno ang matalinong tao, kaya agad na sumakay si Archie."),
            ("Kemudian seorang petani menyarankan agar Archie turun demi menjaga kondisi hewan dan meminta Tom yang lebih ringan naik.", "Pagkaraan, pinayuhan sila ng magsasaka na bumaba si Archie upang manatiling malusog ang hayop at si Tom na mas magaan ang sumakay."),
            ("Petani itu lalu menambahkan bahwa sebaiknya tidak seorang pun menungganginya dan mereka harus menggendong keledai.", "Idinagdag pa ng magsasaka na walang dapat sumakay at kailangan nilang buhatin ang asno."),
            ("Archie mengikuti setiap nasihat, sehingga perjalanan menjadi lambat dan mereka tiba saat malam.", "Sinunod ni Archie ang bawat payo kaya bumagal ang lakad at gabi na sila dumating."),
            ("Sekelompok remaja menertawakan mereka dan melempar batu; keledai menendang, jatuh, lalu melarikan diri.", "Pinagtawanan sila ng mga binatilyo at binato; sumipa ang asno, nahulog, at saka nakawala."),
            ("Archie pulang tanpa uang dan belajar bahwa ia tidak dapat menyenangkan semua orang; ia harus membuat keputusan sendiri.", "Umuwi si Archie nang walang pera at natutuhang hindi mapalulugdan ang lahat; kailangan niyang gumawa ng sariling pagpapasya."),
        ],
        "vocabulary": [("asno", "keledai", "pangngalan"), ("maipagbili", "dijual", "pandiwa"), ("sumakay", "menunggang", "pandiwa"), ("pinayuhan", "menasihati", "pandiwa"), ("buhatin", "menggendong", "pandiwa"), ("pinagtawanan", "ditertawakan", "pandiwa"), ("nakawala", "melarikan diri", "pandiwa"), ("pagpapasya", "pengambilan keputusan", "pangngalan")],
        "expressions": [("hindi mapalulugdan ang lahat", "tidak semua orang dapat disenangkan"), ("sariling pagpapasya", "keputusan sendiri")],
        "grammar": ("Dapat dan kailangan menyatakan kewajiban atau saran kuat. Kaya menunjukkan akibat Archie mengikuti semua nasihat.", "Ipinahahayag ng dapat at kailangan ang tungkulin o matibay na payo. Ipinakikita ng kaya ang bunga ng pagsunod ni Archie sa lahat ng payo."),
        "questions": [
            {"prompt": ("Mengapa Archie membawa keledai ke kota?", "Bakit dinala ni Archie ang asno sa bayan?"), "choices": [("Untuk menjualnya", "Upang ipagbili iyon"), ("Untuk mengikuti perlombaan", "Upang isali sa karera"), ("Untuk mengunjungi petani", "Upang dalawin ang magsasaka")], "correct": 0, "reason": ("Archie membutuhkan uang dan berharap mendapatkannya dari penjualan keledai.", "Kailangan ni Archie ng pera at umaasang makukuha iyon sa pagbebenta ng asno.")},
            {"prompt": ("Mengapa Archie dan Tom akhirnya menggendong keledai?", "Bakit binuhat nina Archie at Tom ang asno?"), "choices": [("Keledai terluka", "Nasugatan ang asno"), ("Mereka mengikuti saran petani", "Sinunod nila ang payo ng magsasaka"), ("Jalan tertutup", "Sarado ang daan")], "correct": 1, "reason": ("Petani menyatakan bahwa tidak seorang pun seharusnya menunggangi hewan yang tampak lelah.", "Sinabi ng magsasaka na walang dapat sumakay sa hayop na mukhang pagod.")},
            {"prompt": ("Apa akibat akhir dari mengikuti semua nasihat?", "Ano ang huling bunga ng pagsunod sa lahat ng payo?"), "choices": [("Keledai terjual mahal", "Naipagbili nang mahal ang asno"), ("Mereka menjadi terkenal", "Naging sikat sila"), ("Keledai kabur dan Archie tidak mendapat uang", "Nakatakas ang asno at walang nakuhang pera si Archie")], "correct": 2, "reason": ("Cara membawa yang aneh memicu ejekan dan kekacauan hingga keledai lolos.", "Nagdulot ng pangungutya at gulo ang kakaibang pagdadala hanggang makatakas ang asno.")},
        ],
    },
    {
        "title": "The Spider and the Bird",
        "category": "Fabel dan persahabatan",
        "summary": ("Seekor burung yang terjebak gagal menjawab teka-teki laba-laba, tetapi perjalanan mencari makanan membuat keduanya menjadi sahabat.", "Nabigo ang ibong nasilo na sagutin ang palaisipan ng gagamba, ngunit ang paglalakbay nila para humanap ng pagkain ang naging simula ng pagkakaibigan."),
        "characters": ["the large spider", "the small bird"],
        "setting": "A forest web and a flight over the surrounding landscape.",
        "theme": ("A fair bargain and shared experience can turn fear into friendship.", "kesepakatan yang menjadi persahabatan", "kasunduang nauwi sa pagkakaibigan"),
        "events": ["A spider tests trapped insects with puzzles before deciding whether to eat them.", "A bird becomes trapped and bargains for a chance to answer.", "She answers 'the sky' to a riddle whose answer is Hawaii and must provide valuable food.", "The bird carries the spider on a bug-finding tour, and they become friends."],
        "sentences": [
            ("Seekor laba-laba besar biasa memberi teka-teki sulit kepada serangga yang terperangkap di jaringnya.", "Mahilig magbigay ng mahirap na palaisipan ang isang malaking gagamba sa mga insektong nasisilo sa kaniyang sapot."),
            ("Suatu hari seekor burung kecil tersangkut dan terlalu lelah untuk membebaskan diri.", "Isang araw, nasilo ang isang maliit na ibon at naubusan ng lakas upang makawala."),
            ("Burung membuat kesepakatan: jika jawabannya benar ia bebas, tetapi jika salah ia akan memberi hadiah berharga.", "Nakipagkasundo ang ibon: kung tama ang sagot ay palalayain siya, ngunit kung mali ay magbibigay siya ng mahalagang regalo."),
            ("Laba-laba bertanya tempat untuk melihat pantai, gurun, dan pegunungan sekaligus.", "Itinanong ng gagamba kung saang lugar makikita nang sabay ang baybayin, disyerto, at kabundukan."),
            ("Burung menjawab langit, tetapi jawaban yang dimaksud laba-laba adalah Hawaii.", "Sumagot ang ibon ng kalangitan, ngunit Hawaii ang tamang sagot ng gagamba."),
            ("Sebagai hadiah, burung membawa laba-laba terbang mengelilingi hutan dan mencari banyak serangga untuk dimakan.", "Bilang regalo, isinakay ng ibon ang gagamba sa paglipad sa gubat at naghanap sila ng maraming insekto."),
            ("Setelah pulang, keduanya menjadi sahabat dan tidak pernah lagi mencoba saling memakan.", "Pagkauwi, nabuo ang kanilang pagkakaibigan at hindi na nila muling sinubukang kainin ang isa't isa."),
        ],
        "vocabulary": [("palaisipan", "teka-teki", "pangngalan"), ("gagamba", "laba-laba", "pangngalan"), ("sapot", "jaring", "pangngalan"), ("nasilo", "terperangkap", "pandiwa"), ("ibon", "burung", "pangngalan"), ("nakipagkasundo", "membuat kesepakatan", "pandiwa"), ("insekto", "serangga", "pangngalan"), ("pagkakaibigan", "persahabatan", "pangngalan")],
        "expressions": [("kung tama ang sagot", "jika jawabannya benar"), ("hindi na nila muling sinubukan", "mereka tidak pernah mencoba lagi")],
        "grammar": ("Kung ... ngunit kung ... membandingkan dua akibat berdasarkan syarat yang berbeda. Isa't isa menyatakan tindakan timbal balik.", "Inihahambing ng kung ... ngunit kung ... ang dalawang bunga ng magkaibang kondisyon. Ipinahahayag ng isa't isa ang kilos na pabalikan."),
        "questions": [
            {"prompt": ("Apa jawaban teka-teki menurut laba-laba?", "Ano ang sagot sa palaisipan ayon sa gagamba?"), "choices": [("Hawaii", "Hawaii"), ("Langit", "Kalangitan"), ("Hutan", "Gubat")], "correct": 0, "reason": ("Hawaii memiliki pantai, wilayah kering, dan pegunungan dalam satu tempat.", "May baybayin, tuyong lugar, at kabundukan ang Hawaii sa iisang pook.")},
            {"prompt": ("Apa yang diberikan burung setelah jawabannya salah?", "Ano ang ibinigay ng ibon matapos magkamali?"), "choices": [("Sarang baru", "Bagong pugad"), ("Perjalanan terbang dan makanan serangga", "Paglipad at pagkaing insekto"), ("Batu berharga", "Mamahaling bato")], "correct": 1, "reason": ("Burung membawa laba-laba berkeliling dan menemukan makanan yang diinginkannya.", "Inilibot ng ibon ang gagamba at nakahanap sila ng pagkaing gusto nito.")},
            {"prompt": ("Bagaimana hubungan mereka berakhir?", "Ano ang naging ugnayan nila sa huli?"), "choices": [("Mereka tetap bermusuhan", "Nanatili silang magkaaway"), ("Burung memakan laba-laba", "Kinain ng ibon ang gagamba"), ("Mereka menjadi sahabat", "Naging magkaibigan sila")], "correct": 2, "reason": ("Pengalaman bersama mengubah ancaman awal menjadi saling percaya.", "Binago ng magkasamang karanasan ang unang banta tungo sa pagtitiwala.")},
        ],
    },
    {
        "title": "The Party",
        "category": "Keluarga",
        "summary": ("Badai salju membatalkan pesta ulang tahun Cody, tetapi kedatangan kakek-neneknya mengubah hari itu menjadi ulang tahun terbaik.", "Kinansela ng bagyo ng niyebe ang handaan ni Cody, ngunit ginawang pinakamagandang kaarawan ng pagdating ng kaniyang lolo't lola ang araw na iyon."),
        "characters": ["Cody", "Cody's father", "Cody's grandparents", "the band"],
        "setting": "Cody's new house and garage during a snowstorm.",
        "theme": ("The presence of loved ones matters more than elaborate entertainment.", "kehadiran keluarga lebih penting dari acara", "presensiya ng pamilya higit sa handaan"),
        "events": ["Cody plans a birthday party with a band at his new home.", "Heavy snow forces the stage indoors, then keeps the band and other performers away.", "The party is canceled, and Cody misses his old home and grandparents.", "His grandparents arrive despite the delay, and their visit makes the birthday special."],
        "sentences": [
            ("Setelah keluarganya pindah ke kota baru, Cody merencanakan pesta ulang tahun dengan sebuah band.", "Matapos lumipat ang pamilya sa bagong bayan, nagplano si Cody ng handaan sa kaarawan na may banda."),
            ("Pada pagi pesta, salju tebal menutupi tanah sehingga panggung harus dipindahkan ke garasi.", "Sa umaga ng handaan, makapal na niyebe ang tumakip sa lupa kaya inilipat ang entablado sa garahe."),
            ("Band kemudian membatalkan kedatangan, dan tidak ada pesulap yang mau bepergian dalam badai.", "Pagkatapos ay hindi tumuloy ang banda, at walang salamangkero ang gustong bumiyahe sa gitna ng bagyo."),
            ("Ayah Cody akhirnya membatalkan pesta, membuat Cody sedih dan semakin merindukan kakek-neneknya.", "Sa huli ay kinansela ng ama ang handaan kaya nalungkot si Cody at lalo niyang hinanap ang kaniyang lolo't lola."),
            ("Tak lama kemudian sebuah mobil yang dikenalnya berhenti di halaman: kakek dan neneknya berhasil datang meskipun terlambat karena salju.", "Maya-maya ay huminto sa bakuran ang pamilyar na sasakyan: dumating ang kaniyang lolo't lola kahit nahuli sila dahil sa niyebe."),
            ("Mereka berbagi sundae kesukaan Cody dan mendengarkan ceritanya tentang kota baru.", "Nagsalo sila sa paboritong sundae ni Cody at nakinig sa mga kuwento niya tungkol sa bagong bayan."),
            ("Tanpa band atau sulap, kehadiran keluarga membuatnya menyebut hari itu ulang tahun terbaiknya.", "Kahit walang banda o mahika, ginawa ng presensiya ng pamilya ang araw na iyon bilang pinakamagandang kaarawan niya."),
        ],
        "vocabulary": [("lumipat", "pindah", "pandiwa"), ("kaarawan", "ulang tahun", "pangngalan"), ("banda", "band", "pangngalan"), ("niyebe", "salju", "pangngalan"), ("garahe", "garasi", "pangngalan"), ("kinansela", "membatalkan", "pandiwa"), ("lolo't lola", "kakek-nenek", "parirala"), ("sundae", "es krim sundae", "pangngalan")],
        "expressions": [("hindi tumuloy ang banda", "band tidak jadi datang"), ("pinakamagandang kaarawan", "ulang tahun terbaik")],
        "grammar": ("Kahit menyatakan bahwa kebahagiaan terjadi meskipun hiburan batal. Dahil sa menjelaskan penyebab keterlambatan dan perubahan rencana.", "Ipinakikita ng kahit ang saya sa kabila ng kanseladong libangan. Ipinapaliwanag ng dahil sa ang sanhi ng pagkahuli at pagbabago ng plano."),
        "questions": [
            {"prompt": ("Apa yang menyebabkan rencana pesta berubah?", "Ano ang nagpabago sa plano ng handaan?"), "choices": [("Badai salju", "Bagyo ng niyebe"), ("Cody sakit", "Nagkasakit si Cody"), ("Rumah terlalu kecil", "Masyadong maliit ang bahay")], "correct": 0, "reason": ("Salju menghalangi pertunjukan luar ruangan dan perjalanan para penghibur.", "Pinigilan ng niyebe ang palabas sa labas at ang pagbiyahe ng mga tagapagtanghal.")},
            {"prompt": ("Siapa yang datang sebagai kejutan?", "Sino ang dumating bilang sorpresa?"), "choices": [("Band", "Ang banda"), ("Kakek dan nenek Cody", "Ang lolo't lola ni Cody"), ("Teman lama", "Dating kaibigan")], "correct": 1, "reason": ("Cody mengenali mobil mereka di halaman setelah pesta dibatalkan.", "Nakilala ni Cody ang kanilang sasakyan sa bakuran matapos kanselahin ang handaan.")},
            {"prompt": ("Mengapa Cody akhirnya menyebutnya ulang tahun terbaik?", "Bakit naging pinakamagandang kaarawan iyon para kay Cody?"), "choices": [("Ia menerima banyak hadiah", "Marami siyang natanggap na regalo"), ("Badai segera berhenti", "Agad tumigil ang bagyo"), ("Ia dapat bersama kakek-nenek yang dirindukannya", "Nakasama niya ang lolo't lolang hinahanap niya")], "correct": 2, "reason": ("Kebersamaan keluarga lebih bermakna baginya daripada band atau pertunjukan sulap.", "Mas mahalaga sa kaniya ang pagsasama ng pamilya kaysa banda o mahika.")},
        ],
    },
    {
        "title": "How the World Got Light",
        "category": "Mitos dan kebebasan",
        "summary": ("Raven menipu presiden babi yang menyimpan matahari di dalam kantong, lalu melepaskan cahaya bagi semua hewan di Darkland.", "Nilinlang ni Raven ang presidenteng baboy na nagtago ng araw sa isang supot at pinalaya ang liwanag para sa lahat ng hayop sa Darkland."),
        "characters": ["the pig president", "Raven", "the animals of Darkland"],
        "setting": "Darkland, the president's house, and the sky.",
        "theme": ("Clever resistance can free a resource hoarded by an unjust ruler.", "perlawanan cerdas terhadap penguasa zalim", "matalinong paglaban sa di-makatarungang pinuno"),
        "events": ["The pig president keeps all light and the sun inside a bag.", "The animals hold a contest and choose Raven as the smartest.", "Raven imitates a crying baby so the president opens his door.", "Raven steals the bag, releases the sun into the sky, and gives everyone light."],
        "sentences": [
            ("Di Darkland, presiden babi yang kejam menyimpan seluruh cahaya dunia di dalam sebuah kantong.", "Sa Darkland, itinago ng malupit na presidenteng baboy ang lahat ng liwanag ng mundo sa isang supot."),
            ("Ia ingin kota tetap gelap agar hewan-hewan tidak dapat bekerja atau berkembang.", "Nais niyang manatiling madilim ang bayan upang hindi makapagtrabaho o umunlad ang mga hayop."),
            ("Para hewan mengadakan perlombaan pengetahuan dan memilih burung gagak bernama Raven sebagai yang paling cerdas.", "Nagsagawa ang mga hayop ng paligsahan sa talino at pinili ang uwak na si Raven bilang pinakamatalino."),
            ("Raven mendekati rumah presiden dan meniru tangisan bayi dengan suara keras.", "Lumapit si Raven sa bahay ng pangulo at ginaya nang malakas ang iyak ng sanggol."),
            ("Ketika presiden membuka pintu untuk menghentikan suara itu, Raven terbang melewatinya dan mengambil kantong lembut tersebut.", "Nang buksan ng pangulo ang pinto upang patahimikin ang tunog, lumipad si Raven lampas sa kaniya at kinuha ang malambot na supot."),
            ("Di dalamnya ada matahari; Raven membawanya tinggi dan meletakkannya di langit.", "Nasa loob ang araw; dinala iyon ni Raven sa itaas at inilagay sa kalangitan."),
            ("Meskipun presiden marah, Raven telah membebaskan cahaya untuk semua dan Darkland tidak lagi gelap.", "Kahit nagalit ang pangulo, pinalaya na ni Raven ang liwanag para sa lahat at hindi na madilim ang Darkland."),
        ],
        "vocabulary": [("liwanag", "cahaya", "pangngalan"), ("supot", "kantong", "pangngalan"), ("paligsahan", "perlombaan", "pangngalan"), ("uwak", "burung gagak", "pangngalan"), ("pinakamatalino", "paling cerdas", "pang-uri"), ("ginaya", "meniru", "pandiwa"), ("kalangitan", "langit", "pangngalan"), ("pinalaya", "membebaskan", "pandiwa")],
        "expressions": [("liwanag para sa lahat", "cahaya untuk semua"), ("hindi na madilim", "tidak gelap lagi")],
        "grammar": ("Upang + verba menyatakan maksud presiden maupun Raven. Hindi na menandai keadaan lama yang telah berakhir.", "Ipinahahayag ng upang + pandiwa ang layunin ng pangulo at ni Raven. Tinutukoy ng hindi na ang dating kalagayang natapos na."),
        "questions": [
            {"prompt": ("Mengapa Darkland tetap gelap?", "Bakit nanatiling madilim ang Darkland?"), "choices": [("Presiden menyimpan cahaya dan matahari", "Itinago ng pangulo ang liwanag at araw"), ("Raven takut terbang", "Takot lumipad si Raven"), ("Para hewan menyukai malam", "Gusto ng mga hayop ang gabi")], "correct": 0, "reason": ("Penguasa itu menahan sumber cahaya agar hanya dirinya yang menguasainya.", "Inangkin ng pinuno ang pinagmumulan ng liwanag para sa sarili lamang.")},
            {"prompt": ("Mengapa Raven dipilih?", "Bakit pinili si Raven?"), "choices": [("Ia paling kuat", "Siya ang pinakamalakas"), ("Ia memenangkan perlombaan kecerdasan", "Nanalo siya sa paligsahan sa talino"), ("Ia tinggal bersama presiden", "Nakatira siya sa pangulo")], "correct": 1, "reason": ("Tugas mencuri cahaya memerlukan hewan yang dapat membuat rencana cerdik.", "Kailangan sa gawain ang hayop na makagagawa ng matalinong plano.")},
            {"prompt": ("Bagaimana Raven membuat presiden membuka pintu?", "Paano pinabuksan ni Raven ang pinto?"), "choices": [("Ia mengetuk dengan batu", "Kumatok siya gamit ang bato"), ("Ia memanggil semua hewan", "Tinawag niya ang lahat ng hayop"), ("Ia meniru tangisan bayi", "Ginaya niya ang iyak ng sanggol")], "correct": 2, "reason": ("Suara bayi yang keras mengganggu presiden sampai ia keluar.", "Nainis ang pangulo sa malakas na iyak kaya binuksan niya ang pinto.")},
        ],
    },
    {
        "title": "Cats and Secrets",
        "category": "Asal-usul ungkapan",
        "summary": ("Beth membongkar penjual curang yang mengganti anak babi dengan kucing di dalam kantong, menjelaskan asal idiom ‘let the cat out of the bag.’",
                    "Ibinunyag ni Beth ang manlolokong nagpalit ng biik ng pusa sa loob ng supot, na nagpapaliwanag sa idyomang “let the cat out of the bag.”"),
        "characters": ["Beth", "the dishonest seller", "Beth's friends", "a judge", "the cats"],
        "setting": "A market area in an old section of England and a judge's court.",
        "theme": ("Evidence exposes deception, and a revealed secret cannot be hidden again.", "bukti yang membongkar penipuan", "ebidensiyang nagbubunyag ng panlilinlang"),
        "events": ["A dishonest seller offers Beth a cheap baby pig.", "He gives her a closed bag containing a cat instead.", "When he returns, Beth and her friends take the case to a judge.", "Beth opens the seller's bag, releases another cat as evidence, and exposes his secret."],
        "sentences": [
            ("Idiom Inggris ‘let the cat out of the bag’ berarti membocorkan sebuah rahasia.", "Ang idyomang Ingles na “let the cat out of the bag” ay nangangahulugang ibunyag ang isang lihim."),
            ("Menurut kisah asalnya, seorang penjual licik menawarkan anak babi yang sangat murah kepada perempuan bernama Beth.", "Ayon sa kuwentong pinagmulan, nag-alok ang isang manloloko ng napakamurang biik sa babaeng si Beth."),
            ("Setelah menerima satu koin emas, penjual itu menyerahkan kantong tertutup dan segera pergi.", "Matapos tumanggap ng isang gintong barya, ibinigay ng tindero ang nakasarang supot at mabilis na umalis."),
            ("Ketika Beth membuka kantong, seekor kucing keluar, bukan anak babi yang telah dibelinya.", "Nang buksan ni Beth ang supot, pusa at hindi biik ang lumabas mula rito."),
            ("Saat penjual kembali untuk menipu orang lain, Beth memberi tahu teman-temannya dan mereka membawanya kepada hakim.", "Nang bumalik ang tindero upang manloko muli, sinabi ni Beth sa mga kaibigan ang nangyari at dinala nila siya sa hukom."),
            ("Hakim meminta bukti, maka Beth membuka kantong milik penjual dan membiarkan seekor kucing lain keluar.", "Humingi ng ebidensiya ang hukom kaya binuksan ni Beth ang supot ng tindero at pinalabas ang isa pang pusa."),
            ("Rahasia penipuan itu terbongkar dan penjual dipenjara; karena itulah mengeluarkan kucing dari kantong berarti mengungkap rahasia.", "Nabunyag ang lihim ng pandaraya at nakulong ang tindero; kaya ang pagpapalabas ng pusa sa supot ay naging sagisag ng pagbubunyag ng lihim."),
        ],
        "vocabulary": [("idyoma", "idiom", "pangngalan"), ("ibunyag", "membocorkan", "pandiwa"), ("lihim", "rahasia", "pangngalan"), ("manloloko", "penipu", "pangngalan"), ("biik", "anak babi", "pangngalan"), ("supot", "kantong", "pangngalan"), ("hukom", "hakim", "pangngalan"), ("ebidensiya", "bukti", "pangngalan")],
        "expressions": [("ibunyag ang isang lihim", "membocorkan sebuah rahasia"), ("humingi ng ebidensiya", "meminta bukti")],
        "grammar": ("Nang + verba menandai waktu saat rahasia ditemukan. Kaya memperkenalkan hubungan antara peristiwa pasar dan makna idiom.", "Tinutukoy ng nang + pandiwa ang oras nang matuklasan ang lihim. Ipinakikilala ng kaya ang ugnayan ng pangyayari sa palengke at kahulugan ng idyoma."),
        "questions": [
            {"prompt": ("Apa arti idiom ‘let the cat out of the bag’?", "Ano ang kahulugan ng idyomang “let the cat out of the bag”?"), "choices": [("Membocorkan rahasia", "Ibunyag ang lihim"), ("Membeli hewan", "Bumili ng hayop"), ("Pergi ke pasar", "Pumunta sa palengke")], "correct": 0, "reason": ("Cerita menghubungkan keluarnya kucing dengan terbukanya penipuan yang dirahasiakan.", "Iniugnay ng kuwento ang paglabas ng pusa sa pagkabunyag ng nakatagong pandaraya.")},
            {"prompt": ("Apa yang sebenarnya diterima Beth?", "Ano talaga ang natanggap ni Beth?"), "choices": [("Anak babi", "Biik"), ("Kucing di dalam kantong", "Pusa sa loob ng supot"), ("Sayuran", "Gulay")], "correct": 1, "reason": ("Penjual mengganti hewan yang dijanjikan dengan kucing.", "Pinalitan ng tindero ng pusa ang ipinangakong biik.")},
            {"prompt": ("Bagaimana Beth membuktikan penipuan kepada hakim?", "Paano pinatunayan ni Beth ang pandaraya sa hukom?"), "choices": [("Ia menunjukkan koin", "Ipinakita niya ang barya"), ("Ia membawa saksi dari kota lain", "Nagdala siya ng saksi mula sa ibang bayan"), ("Ia membuka kantong penjual dan mengeluarkan kucing", "Binuksan niya ang supot ng tindero at pinalabas ang pusa")], "correct": 2, "reason": ("Kucing dalam kantong menunjukkan langsung cara penjual menukar anak babi.", "Tuwirang ipinakita ng pusa sa supot kung paano ipinapalit ng tindero ang biik.")},
        ],
    },
])

STORIES.extend([
    {
        "title": "Princess Rose and the Creature",
        "category": "Dongeng dan penerimaan",
        "summary": ("Putri Rose yang ditinggalkan di hutan menerima Henry tanpa menilai penampilannya, lalu kasih sayangnya mematahkan perubahan wujud Henry.", "Tinanggap ni Prinsesa Rose si Henry nang hindi hinuhusgahan ang anyo nito, at binago ng kaniyang pagmamahal ang nilalang pabalik sa tunay nitong pagkatao."),
        "characters": ["Princess Rose", "the jealous queen", "Henry"],
        "setting": "A kingdom, a forest, and the route to Henry's ship.",
        "theme": ("Acceptance looks beyond outward appearance.", "penerimaan melampaui penampilan", "pagtanggap na higit sa panlabas na anyo"),
        "events": ["The jealous queen puts Rose to sleep and abandons her in a forest.", "Rose dreams of the man she will marry.", "She meets the green, horned creature Henry and spends a pleasant day with him.", "Rose kisses Henry, who changes into the man from her dream, and they marry."],
        "sentences": [
            ("Ratu merasa iri kepada kecantikan putrinya, Rose, lalu memberinya minuman tidur dan meninggalkannya di hutan.", "Nagselos ang reyna sa kagandahan ng anak niyang si Rose, kaya pinainom niya ito ng pampatulog at iniwan sa gubat."),
            ("Dalam tidurnya, sang putri bermimpi tentang pria berambut dan bermata cokelat yang kelak akan dinikahinya.", "Habang natutulog, napanaginipan ng prinsesa ang lalaking kayumanggi ang buhok at mga mata na mapapangasawa niya balang araw."),
            ("Ketika terbangun, Rose bertemu makhluk hijau berbulu yang bertanduk dan berhidung seperti babi.", "Pagkagising, nakilala ni Rose ang mabalahibo at berdeng nilalang na may sungay at ilong na parang baboy."),
            ("Makhluk bernama Henry itu bersikap baik, dan Rose tidak takut kepadanya.", "Mabait ang nilalang na nagngangalang Henry, at hindi natakot sa kaniya si Rose."),
            ("Mereka mengumpulkan buah beri, menangkap ikan, dan menikmati percakapan sepanjang hari.", "Nangolekta sila ng mga berry, nanghuli ng isda, at nasiyahan sa kanilang usapan buong araw."),
            ("Saat Henry mengajak Rose ikut pulang dengan kapalnya, Rose mencium hidungnya sebagai tanda sayang.", "Nang anyayahan ni Henry si Rose na sumama sa kaniyang barko, hinalikan siya ng prinsesa sa ilong bilang tanda ng pagmamahal."),
            ("Seketika tanduk dan bulunya hilang; Henry menjadi pria dalam mimpi Rose, lalu mereka menikah dan hidup bahagia.", "Agad na nawala ang sungay at balahibo ni Henry; siya ang lalaking nasa panaginip ni Rose, at nagpakasal silang dalawa."),
        ],
        "vocabulary": [("nagselos", "merasa iri", "pandiwa"), ("prinsesa", "putri", "pangngalan"), ("nilalang", "makhluk", "pangngalan"), ("sungay", "tanduk", "pangngalan"), ("nanghuli", "menangkap", "pandiwa"), ("barko", "kapal", "pangngalan"), ("pagmamahal", "kasih sayang", "pangngalan"), ("nagpakasal", "menikah", "pandiwa")],
        "expressions": [("bilang tanda ng pagmamahal", "sebagai tanda kasih sayang"), ("sumama sa kaniyang barko", "ikut bersamanya ke kapal")],
        "grammar": ("Nang memperkenalkan peristiwa yang memicu perubahan Henry. Bilang tanda ng menjelaskan fungsi suatu tindakan sebagai lambang.", "Ipinakikilala ng nang ang pangyayaring nagpasimula sa pagbabago ni Henry. Ipinapaliwanag ng bilang tanda ng ang kilos na nagsisilbing sagisag."),
        "questions": [
            {"prompt": ("Mengapa ratu meninggalkan Rose di hutan?", "Bakit iniwan ng reyna si Rose sa gubat?"), "choices": [("Ia iri kepada kecantikan Rose", "Nagselos siya sa kagandahan ni Rose"), ("Rose ingin berlayar", "Gustong maglayag ni Rose"), ("Henry memintanya", "Hiniling iyon ni Henry")], "correct": 0, "reason": ("Ratu tidak tahan lagi bersaing dengan putrinya yang lebih cantik.", "Hindi matanggap ng reyna na mas maganda sa kaniya ang kaniyang anak.")},
            {"prompt": ("Bagaimana sikap Rose kepada Henry saat pertama bertemu?", "Ano ang saloobin ni Rose kay Henry nang una silang magkita?"), "choices": [("Ia langsung melarikan diri", "Agad siyang tumakas"), ("Ia tidak takut dan menerima Henry", "Hindi siya natakot at tinanggap niya si Henry"), ("Ia menyuruh Henry pergi", "Pinaalis niya si Henry")], "correct": 1, "reason": ("Rose melihat kebaikan Henry meskipun penampilannya tidak biasa.", "Nakita ni Rose ang kabaitan ni Henry sa kabila ng kakaiba nitong anyo.")},
            {"prompt": ("Apa yang terjadi setelah Rose mencium Henry?", "Ano ang nangyari matapos halikan ni Rose si Henry?"), "choices": [("Rose tertidur lagi", "Muling nakatulog si Rose"), ("Kapal berangkat tanpa mereka", "Umalis ang barko nang wala sila"), ("Henry berubah menjadi pria dalam mimpi Rose", "Naging lalaki sa panaginip ni Rose si Henry")], "correct": 2, "reason": ("Ciuman Rose mengakhiri wujud Henry sebagai makhluk bertanduk.", "Tinapos ng halik ni Rose ang anyo ni Henry bilang nilalang na may sungay.")},
        ],
    },
    {
        "title": "The Crazy Artist",
        "category": "Seni dan inovasi",
        "summary": ("Karya eksperimental Frenhofer mula-mula ditolak para seniman, tetapi kemudian dipahami sebagai karya besar yang mendahului zamannya.", "Noong una ay tinanggihan ng ibang pintor ang eksperimental na obra ni Frenhofer, ngunit kalaunan ay kinilala itong dakilang likhang nauna sa panahon nito."),
        "characters": ["Frenhofer", "other artists", "later critics and viewers"],
        "setting": "Frenhofer's apartment and the wider art world.",
        "theme": ("New art may need time before people understand it.", "inovasi yang belum langsung dipahami", "bagong likhang hindi agad nauunawaan"),
        "events": ["Successful painter Frenhofer abandons his old career to pursue a new method.", "He works on one painting for years and neglects his health.", "Other artists reject the crowded lines, colors, shapes, and symbols.", "Over time, critics and the public recognize the painting's importance."],
        "sentences": [
            ("Frenhofer pernah menjadi pelukis terkenal yang menjual karya berkualitas tinggi dan mengajar seni.", "Dating tanyag na pintor si Frenhofer na nagbebenta ng mahuhusay na obra at nagtuturo ng sining."),
            ("Kemudian ia meninggalkan kehidupan nyaman itu untuk mencoba cara melukis yang sama sekali baru.", "Iniwan niya ang maginhawang buhay upang subukan ang isang ganap na bagong pamamaraan ng pagpipinta."),
            ("Ia mengurung diri di apartemen dan mengerjakan satu lukisan siang malam selama bertahun-tahun sampai tubuhnya menjadi kurus.", "Nagkulong siya sa apartment at nagtrabaho sa iisang larawan araw at gabi sa loob ng maraming taon hanggang sa siya ay mangayayat."),
            ("Saat akhirnya diperlihatkan, lukisan itu penuh garis, warna, bentuk, dan simbol tanpa gambar biasa.", "Nang ipakita niya ang natapos na obra, punô iyon ng mga guhit, kulay, hugis, at simbolo sa halip na karaniwang larawan."),
            ("Para seniman lain mengkritiknya karena mereka tidak memahami keindahan atau maksudnya.", "Pinuna iyon ng ibang mga pintor dahil hindi nila naunawaan ang ganda o kahulugan nito."),
            ("Namun, seiring berjalannya waktu, artikel dan penonton mulai memuji keberanian karya tersebut.", "Ngunit sa paglipas ng panahon, nagsimulang purihin ng mga artikulo at manonood ang katapangan ng obra."),
            ("Lukisan Frenhofer akhirnya diakui sebagai bukti bahwa sesuatu yang baru tidak otomatis buruk.", "Sa huli, kinilala ang likha ni Frenhofer bilang patunay na hindi masama ang isang bagay dahil lamang sa bago ito."),
        ],
        "vocabulary": [("pintor", "pelukis", "pangngalan"), ("obra", "karya seni", "pangngalan"), ("pamamaraan", "cara", "pangngalan"), ("guhit", "garis", "pangngalan"), ("hugis", "bentuk", "pangngalan"), ("simbolo", "simbol", "pangngalan"), ("pinuna", "mengkritik", "pandiwa"), ("kinilala", "mengakui", "pandiwa")],
        "expressions": [("sa paglipas ng panahon", "seiring berjalannya waktu"), ("dahil lamang sa bago ito", "hanya karena hal itu baru")],
        "grammar": ("Noong una ... ngunit kalaunan dapat dipakai untuk membandingkan perubahan pendapat dari waktu ke waktu. Dahil lamang sa menekankan alasan yang tidak cukup.", "Ginagamit ang noong una ... ngunit kalaunan upang ihambing ang pagbabago ng pananaw sa paglipas ng panahon. Binibigyang-diin ng dahil lamang sa ang hindi sapat na dahilan."),
        "questions": [
            {"prompt": ("Mengapa Frenhofer menjadi sangat kurus?", "Bakit labis na nangayayat si Frenhofer?"), "choices": [("Ia bekerja terus dan jarang makan", "Patuloy siyang gumawa at bihirang kumain"), ("Ia bepergian jauh", "Naglakbay siya nang malayo"), ("Ia kehilangan rumah", "Nawalan siya ng bahay")], "correct": 0, "reason": ("Ia menghabiskan siang dan malam untuk lukisan yang sama sambil mengabaikan kebutuhan tubuhnya.", "Ginugol niya ang araw at gabi sa iisang obra at napabayaan ang kaniyang katawan.")},
            {"prompt": ("Bagaimana reaksi awal para seniman lain?", "Ano ang unang reaksiyon ng ibang mga pintor?"), "choices": [("Mereka langsung membelinya", "Agad nila itong binili"), ("Mereka tidak memahami dan mengkritiknya", "Hindi nila ito naunawaan at pinuna nila ito"), ("Mereka meniru lukisan itu", "Ginaya nila ang larawan")], "correct": 1, "reason": ("Bentuk dan simbol yang tidak biasa membuat mereka menganggap karya itu buruk.", "Dahil sa kakaibang hugis at simbolo, inakala nilang pangit ang obra.")},
            {"prompt": ("Apa yang akhirnya dipahami orang tentang lukisan itu?", "Ano ang naunawaan ng mga tao tungkol sa obra sa huli?"), "choices": [("Lukisan itu belum selesai", "Hindi pa tapos ang obra"), ("Frenhofer memakai bahan murah", "Murang materyales ang ginamit ni Frenhofer"), ("Kebaruan tidak berarti keburukan", "Hindi nangangahulugang masama ang pagiging bago")], "correct": 2, "reason": ("Waktu membantu orang melihat nilai dari cara melukis Frenhofer yang baru.", "Tinulungan ng panahon ang mga tao na makita ang halaga ng bagong pamamaraan ni Frenhofer.")},
        ],
    },
    {
        "title": "The Farmer and the Cats",
        "category": "Kerja keras dan rasa syukur",
        "summary": ("Arthur dan Maria yang terancam utang mendapat bantuan rahasia dari kucing-kucing mereka untuk menyelesaikan panen dan membayar tuan tanah.", "Lihim na tinulungan ng mga pusa sina Arthur at Maria na matapos ang ani at mabayaran ang panginoong maylupa."),
        "characters": ["Arthur", "Maria", "the town lord", "the farm cats"],
        "setting": "A poor farm after a fire, during the autumn harvest.",
        "theme": ("Unexpected helpers deserve gratitude and care.", "bantuan tak terduga dan rasa syukur", "di-inaasahang tulong at pasasalamat"),
        "events": ["A fire leaves poor Arthur and Maria with only their cats and a debt.", "The lord threatens punishment if they do not pay after harvest.", "Each night, unseen helpers complete as much fieldwork as the farmers.", "The cats finish the harvest and leave money; Arthur and Maria discover and reward them."],
        "sentences": [
            ("Arthur dan Maria adalah petani miskin yang berutang kepada tuan tanah.", "Mahihirap na magsasaka sina Arthur at Maria na may utang sa panginoong maylupa."),
            ("Setelah bangunan pertanian terbakar dan hampir semua hewan pergi, hanya kucing-kucing mereka yang tetap tinggal.", "Nang masunog ang gusali sa bukid at magsialis ang halos lahat ng hayop, ang mga pusa lamang ang nanatili."),
            ("Tuan tanah mengancam akan menambah utang dan memenjarakan Arthur jika panen tidak segera dibayar.", "Nagbanta ang panginoong maylupa na daragdagan ang utang at ipakukulong si Arthur kung hindi sila makababayad matapos ang ani."),
            ("Pasangan itu bekerja keras di ladang, tetapi setiap pagi mereka menemukan dua kali lebih banyak baris tanaman yang telah selesai.", "Nagsikap ang mag-asawa sa bukirin, ngunit tuwing umaga ay doble ang hanay ng pananim na natatapos."),
            ("Dalam seminggu seluruh panen selesai; kemudian hasil panen menghilang dan sebuah kantong uang muncul di tengah ladang.", "Sa loob ng isang linggo ay natapos ang buong ani; pagkaraan, nawala ang mga pananim at may lumitaw na supot ng salapi sa gitna ng bukid."),
            ("Arthur dan Maria mengintip lewat lubang dan melihat kucing-kucing mereka menari serta memakan jagung setelah bekerja diam-diam.", "Sumilip sina Arthur at Maria sa isang butas at nakita ang mga pusang sumasayaw at kumakain ng mais matapos tumulong nang palihim."),
            ("Mereka menyadari siapa penolongnya, lalu berterima kasih dan merawat kucing-kucing itu dengan lebih baik.", "Nalaman nilang ang mga pusa ang tumulong, kaya nagpasalamat sila at higit na inalagaan ang mga ito."),
        ],
        "vocabulary": [("magsasaka", "petani", "pangngalan"), ("utang", "utang", "pangngalan"), ("masunog", "terbakar", "pandiwa"), ("ani", "panen", "pangngalan"), ("bukirin", "ladang", "pangngalan"), ("supot", "kantong", "pangngalan"), ("palihim", "diam-diam", "pang-abay"), ("nagpasalamat", "berterima kasih", "pandiwa")],
        "expressions": [("tuwing umaga", "setiap pagi"), ("tumulong nang palihim", "membantu secara diam-diam")],
        "grammar": ("Tuwing + waktu menyatakan kejadian yang berulang. Nang pada tumulong nang palihim menghubungkan verba dengan cara tindakan dilakukan.", "Tinutukoy ng tuwing + oras ang paulit-ulit na pangyayari. Iniuugnay ng nang sa tumulong nang palihim ang pandiwa at ang paraan ng kilos."),
        "questions": [
            {"prompt": ("Mengapa Arthur dan Maria harus memanen tanpa bantuan hewan besar?", "Bakit kinailangang mag-ani nina Arthur at Maria nang walang malalaking hayop?"), "choices": [("Hewan-hewan pergi setelah kebakaran", "Nagsialis ang mga hayop matapos ang sunog"), ("Mereka menjual semua hewan", "Ipinagbili nila ang lahat ng hayop"), ("Tuan tanah mengambilnya", "Kinuha iyon ng panginoong maylupa")], "correct": 0, "reason": ("Kebakaran membuat sebagian besar hewan meninggalkan pertanian; hanya kucing yang tinggal.", "Dahil sa sunog, umalis ang karamihan ng hayop at mga pusa lamang ang naiwan.")},
            {"prompt": ("Siapa yang menyelesaikan pekerjaan pada malam hari?", "Sino ang nagtapos ng gawain sa gabi?"), "choices": [("Tuan tanah", "Ang panginoong maylupa"), ("Kucing-kucing", "Ang mga pusa"), ("Tetangga", "Ang mga kapitbahay")], "correct": 1, "reason": ("Arthur dan Maria melihat sendiri kucing-kucing berada di ladang setelah pekerjaan selesai.", "Nakita nina Arthur at Maria ang mga pusa sa bukid matapos matapos ang gawain.")},
            {"prompt": ("Apa yang muncul setelah hasil panen menghilang?", "Ano ang lumitaw matapos mawala ang ani?"), "choices": [("Kereta baru", "Bagong kariton"), ("Surat dari raja", "Liham mula sa hari"), ("Kantong berisi uang", "Supot na may salapi")], "correct": 2, "reason": ("Uang itu memungkinkan pasangan tersebut membayar utang kepada tuan tanah.", "Dahil sa salapi, nabayaran ng mag-asawa ang kanilang utang.")},
        ],
    },
    {
        "title": "A Magical Book",
        "category": "Fantasi dan tanggung jawab",
        "summary": ("Buku ajaib memberi Sarah kemampuan mengendalikan orang; setelah menyelamatkan pelatihnya, ia memilih memakai kekuatan itu hanya untuk kebaikan.", "Binigyan ng mahiwagang aklat si Sarah ng kakayahang kontrolin ang iba; matapos iligtas ang kaniyang coach, nagpasiya siyang gamitin lamang iyon sa kabutihan."),
        "characters": ["Sarah", "Sarah's friend", "Sarah's basketball coach", "people at a local store"],
        "setting": "Sarah's home, school, a local store, and a street.",
        "theme": ("Power should be used responsibly to help rather than harm.", "tanggung jawab dalam memakai kekuatan", "pananagutan sa paggamit ng kapangyarihan"),
        "events": ["Sarah receives a gold-paged magical book.", "The book gives her power to control people, which she uses for jokes and trouble.", "She sees her coach about to walk in front of a bus and stops him with the power.", "Sarah limits herself to using the power for good."],
        "sentences": [
            ("Sarah sangat suka membaca dan suatu hari menerima buku kecil yang dicetak pada lembaran emas.", "Mahilig magbasa si Sarah at isang araw ay nakatanggap siya ng maliit na aklat na nakalimbag sa mga pahinang ginto."),
            ("Kisah dalam buku ajaib itu tentang seorang anak yang dapat mengendalikan tindakan orang lain.", "Ang kuwento sa mahiwagang aklat ay tungkol sa batang kayang kontrolin ang kilos ng ibang tao."),
            ("Setelah terus membacanya, Sarah memperoleh kekuatan yang sama.", "Matapos niya itong basahin nang paulit-ulit, nagkaroon din si Sarah ng gayong kapangyarihan."),
            ("Mula-mula ia menyuruh temannya membuat lelucon dan menyebabkan orang-orang di toko jatuh demi hiburan.", "Noong una, pinagawa niya ng mga kalokohan ang kaibigan at pinabagsak ang mga tao sa tindahan para lamang matawa."),
            ("Kemudian Sarah melihat pelatihnya hampir melangkah ke depan bus yang melaju.", "Pagkatapos, nakita ni Sarah na muntik nang humakbang sa harap ng bus ang kaniyang coach."),
            ("Ia segera memakai kekuatannya untuk menghentikan sang pelatih dan menyelamatkannya.", "Agad niyang ginamit ang kapangyarihan upang pahintuin at iligtas ang coach."),
            ("Sejak itu, Sarah menetapkan batas: kekuatan tersebut hanya boleh digunakan untuk kebaikan, bukan untuk membuat orang menderita.", "Mula noon, nagtakda si Sarah ng hangganan: gagamitin lamang ang lakas sa kabutihan at hindi upang pahirapan ang iba."),
        ],
        "vocabulary": [("mahiwagang", "ajaib", "pang-uri"), ("kontrolin", "mengendalikan", "pandiwa"), ("kapangyarihan", "kekuatan", "pangngalan"), ("kalokohan", "lelucon nakal", "pangngalan"), ("tindahan", "toko", "pangngalan"), ("bus", "bus", "pangngalan"), ("iligtas", "menyelamatkan", "pandiwa"), ("kabutihan", "kebaikan", "pangngalan")],
        "expressions": [("para lamang matawa", "hanya untuk tertawa"), ("gagamitin lamang sa kabutihan", "hanya akan dipakai untuk kebaikan")],
        "grammar": ("Noong una ... mula noon memperlihatkan perubahan perilaku. Upang + verba menyatakan tujuan Sarah menghentikan pelatihnya.", "Ipinakikita ng noong una ... mula noon ang pagbabago ng asal. Ipinahahayag ng upang + pandiwa ang layunin ni Sarah sa pagpapatigil sa coach."),
        "questions": [
            {"prompt": ("Dari mana Sarah memperoleh kekuatannya?", "Saan nakuha ni Sarah ang kaniyang kapangyarihan?"), "choices": [("Dari buku ajaib", "Sa mahiwagang aklat"), ("Dari pelatih", "Sa coach"), ("Dari pertandingan", "Sa paligsahan")], "correct": 0, "reason": ("Kekuatan muncul setelah Sarah terus membaca buku berhalaman emas.", "Lumitaw ang kapangyarihan matapos paulit-ulit basahin ni Sarah ang aklat na may pahinang ginto.")},
            {"prompt": ("Peristiwa apa yang mengubah cara Sarah memakai kekuatan?", "Anong pangyayari ang nagpabago sa paggamit ni Sarah ng kapangyarihan?"), "choices": [("Ia mendapat nilai buruk", "Nakakuha siya ng mababang marka"), ("Ia menyelamatkan pelatih dari bus", "Iniligtas niya ang coach mula sa bus"), ("Bukunya hilang", "Nawala ang kaniyang aklat")], "correct": 1, "reason": ("Menyelamatkan pelatih menunjukkan bahwa kekuatan itu lebih berguna untuk membantu.", "Ipinakita ng pagliligtas sa coach na mas mahalaga ang lakas kapag ginagamit sa pagtulong.")},
            {"prompt": ("Aturan apa yang dibuat Sarah pada akhirnya?", "Anong tuntunin ang itinakda ni Sarah sa huli?"), "choices": [("Tidak membaca lagi", "Hindi na magbabasa"), ("Memakai kekuatan hanya di sekolah", "Sa paaralan lamang gagamitin ang lakas"), ("Memakai kekuatan hanya untuk kebaikan", "Sa kabutihan lamang gagamitin ang lakas")], "correct": 2, "reason": ("Ia tidak ingin lagi menyusahkan atau menyakiti orang demi kesenangan.", "Ayaw na niyang gambalain o saktan ang iba para sa katuwaan.")},
        ],
    },
    {
        "title": "The Big Race",
        "category": "Fabel dan ketekunan",
        "summary": ("Kelinci yang terlalu percaya diri tertidur saat berlomba, sehingga kura-kura yang terus berjalan memenangkan perlombaan.", "Nakatulog sa gitna ng karera ang sobrang kumpiyansang kuneho, kaya nanalo ang pagong na patuloy na lumakad."),
        "characters": ["the rabbit", "the turtle", "the duck", "the dog", "spectating animals"],
        "setting": "A long animal race across fields and roads.",
        "theme": ("Steady effort can defeat careless overconfidence.", "ketekunan melawan kesombongan", "tiyaga laban sa labis na kumpiyansa"),
        "events": ["A duck sells tickets to a long race between a rabbit and a turtle.", "The rabbit quickly gains a large lead.", "Certain of victory, the rabbit eats and sleeps.", "The turtle keeps moving and reaches the finish first."],
        "sentences": [
            ("Seekor anjing membeli tiket untuk menyaksikan perlombaan panjang antara kelinci dan kura-kura.", "Bumili ng tiket ang isang aso upang panoorin ang mahabang karera ng kuneho at pagong."),
            ("Semua penonton mengira kelinci akan menang mudah karena ia jauh lebih cepat.", "Inakala ng lahat na madaling mananalo ang kuneho dahil higit siyang mabilis."),
            ("Saat perlombaan dimulai, kelinci segera meninggalkan kura-kura yang berjalan lambat.", "Nang magsimula ang karera, agad na naiwan ng kuneho ang mabagal na pagong."),
            ("Karena terlalu percaya diri, kelinci berhenti makan rumput lalu tidur sebelum mencapai garis akhir.", "Dahil sobra ang kaniyang kumpiyansa, huminto ang kuneho upang kumain ng damo at pagkatapos ay natulog bago makarating sa dulo."),
            ("Kura-kura tetap berjalan dengan sabar tanpa berhenti.", "Patuloy namang lumakad ang pagong nang may tiyaga at hindi nagpahinga."),
            ("Ketika kelinci terbangun, kura-kura sudah hampir melewati garis akhir dan tidak dapat dikejar lagi.", "Nang magising ang kuneho, malapit nang tumawid sa finish line ang pagong at hindi na niya ito naabutan."),
            ("Kura-kura menerima hadiah, dan anjing menyadari bahwa usaha terbaik lebih penting daripada kecepatan saja.", "Tinanggap ng pagong ang gantimpala, at naunawaan ng aso na mas mahalaga ang buong pagsisikap kaysa bilis lamang."),
        ],
        "vocabulary": [("karera", "perlombaan", "pangngalan"), ("kuneho", "kelinci", "pangngalan"), ("pagong", "kura-kura", "pangngalan"), ("mabilis", "cepat", "pang-uri"), ("mabagal", "lambat", "pang-uri"), ("kumpiyansa", "kepercayaan diri", "pangngalan"), ("tiyaga", "ketekunan", "pangngalan"), ("gantimpala", "hadiah", "pangngalan")],
        "expressions": [("bago makarating sa dulo", "sebelum mencapai akhir"), ("hindi na niya ito naabutan", "ia tidak dapat menyusulnya lagi")],
        "grammar": ("Bago + verba menunjukkan bahwa satu tindakan terjadi sebelum tindakan lain. Patuloy na menandai tindakan yang terus berlangsung.", "Tinutukoy ng bago + pandiwa na nauna ang isang kilos sa iba. Ipinakikita ng patuloy na ang kilos na hindi humihinto."),
        "questions": [
            {"prompt": ("Mengapa kelinci merasa aman untuk tidur?", "Bakit inakala ng kuneho na maaari siyang matulog?"), "choices": [("Ia jauh di depan dan terlalu percaya diri", "Malayo ang lamang niya at sobra ang kumpiyansa niya"), ("Perlombaan dibatalkan", "Kinansela ang karera"), ("Kura-kura pulang", "Umuwi ang pagong")], "correct": 0, "reason": ("Kelinci menganggap kura-kura terlalu lambat untuk mengejarnya.", "Inakala ng kuneho na napakabagal ng pagong upang makahabol.")},
            {"prompt": ("Bagaimana kura-kura memenangkan perlombaan?", "Paano nanalo ang pagong sa karera?"), "choices": [("Ia mengambil jalan pintas", "Dumaan siya sa maikling ruta"), ("Ia terus berjalan tanpa berhenti", "Patuloy siyang lumakad nang hindi humihinto"), ("Ia membangunkan kelinci", "Ginising niya ang kuneho")], "correct": 1, "reason": ("Ketekunan kura-kura membawanya ke garis akhir saat kelinci tidur.", "Dinala ng tiyaga ang pagong sa finish line habang natutulog ang kuneho.")},
            {"prompt": ("Apa yang dipelajari anjing?", "Ano ang natutuhan ng aso?"), "choices": [("Tiket perlombaan terlalu mahal", "Masyadong mahal ang tiket"), ("Semua kura-kura cepat", "Mabilis ang lahat ng pagong"), ("Usaha sungguh-sungguh dapat mengalahkan kecepatan tanpa disiplin", "Kayang talunin ng pagsisikap ang bilis na walang disiplina")], "correct": 2, "reason": ("Kura-kura tidak cepat, tetapi ia memberikan usaha terbaik sampai selesai.", "Hindi mabilis ang pagong, ngunit ibinigay niya ang buong pagsisikap hanggang wakas.")},
        ],
    },
    {
        "title": "Adams County’s Gold",
        "category": "Petualangan dan harta",
        "summary": ("Tom dan Brad mengikuti petunjuk dari buku tua, menemukan koin emas serta peta menuju sisa harta Adams County.", "Sinundan nina Tom at Brad ang mga palatandaan sa sinaunang aklat at nakakita ng gintong barya at mapa patungo sa natitirang kayamanan ng Adams County."),
        "characters": ["Tom", "Brad", "Jeff", "Joe"],
        "setting": "Adams Academy and a nearby forest in Adams County.",
        "theme": ("Curiosity and cooperation turn an ordinary day into discovery.", "rasa ingin tahu dan kerja sama", "pag-uusisa at pagtutulungan"),
        "events": ["Tom looks for something fun to do on Saturday.", "Brad shows him an 1870 book containing clues to hidden gold.", "They interpret a flat tree underground as a buried board and dig for it.", "They find a gold coin and a map leading to more treasure."],
        "sentences": [
            ("Pada hari Sabtu di Adams Academy, Tom mencari kegiatan karena teman-temannya yang lain sibuk.", "Isang Sabado sa Adams Academy, naghanap si Tom ng gagawin dahil abala ang iba niyang kaibigan."),
            ("Ia menemukan Brad sedang membaca buku kuno terbitan 1870 tentang kekayaan tersembunyi di Adams County.", "Nakita niya si Brad na nagbabasa ng sinaunang aklat mula 1870 tungkol sa nakatagong kayamanan sa Adams County."),
            ("Buku itu memuat petunjuk pertama: mencari pohon datar di bawah tanah.", "Nasa aklat ang unang palatandaan: hanapin ang patag na puno sa ilalim ng lupa."),
            ("Brad menduga pohon itu sebenarnya papan kayu yang menutup tempat penyimpanan emas.", "Inakala ni Brad na ang tinutukoy ay isang tabla na nakatakip sa pinagtaguan ng ginto."),
            ("Mereka menggali di hutan sepanjang pagi sampai alat Brad membentur benda keras.", "Naghukay sila sa gubat buong umaga hanggang tumama sa matigas na bagay ang kagamitan ni Brad."),
            ("Di bawah papan yang pecah, mereka menemukan lubang berisi satu koin emas.", "Sa ilalim ng nabasag na tabla, nakakita sila ng butas na may isang gintong barya."),
            ("Tom juga menemukan peta menuju sisa harta, lalu mereka segera melanjutkan petualangan.", "Nakakita rin si Tom ng mapa patungo sa natitirang kayamanan, kaya agad nilang ipinagpatuloy ang pakikipagsapalaran."),
        ],
        "vocabulary": [("sinaunang", "kuno", "pang-uri"), ("kayamanan", "harta", "pangngalan"), ("palatandaan", "petunjuk", "pangngalan"), ("tabla", "papan kayu", "pangngalan"), ("naghukay", "menggali", "pandiwa"), ("barya", "koin", "pangngalan"), ("mapa", "peta", "pangngalan"), ("pakikipagsapalaran", "petualangan", "pangngalan")],
        "expressions": [("nakatagong kayamanan", "harta tersembunyi"), ("ipinagpatuloy ang pakikipagsapalaran", "melanjutkan petualangan")],
        "grammar": ("Inakala na memperkenalkan tafsiran yang belum pasti. Kaya menunjukkan akibat penemuan peta: mereka melanjutkan pencarian.", "Ipinakikilala ng inakala na ang paliwanag na hindi pa tiyak. Ipinakikita ng kaya ang bunga ng pagkakita sa mapa: ipinagpatuloy nila ang paghahanap."),
        "questions": [
            {"prompt": ("Apa yang membuat Tom tertarik ikut Brad?", "Ano ang nag-udyok kay Tom na sumama kay Brad?"), "choices": [("Buku tua tentang emas tersembunyi", "Sinaunang aklat tungkol sa nakatagong ginto"), ("Pertandingan sepak bola", "Laro ng soccer"), ("Konser sekolah", "Konsiyerto sa paaralan")], "correct": 0, "reason": ("Mencari harta dari petunjuk buku terdengar seperti kegiatan Sabtu yang menarik.", "Naging kawili-wiling gawain sa Sabado ang paghahanap ng kayamanan mula sa mga palatandaan.")},
            {"prompt": ("Apa arti ‘pohon datar’ menurut Brad?", "Ano ang kahulugan ng “patag na puno” ayon kay Brad?"), "choices": [("Akar besar", "Malaking ugat"), ("Papan di bawah tanah", "Tabla sa ilalim ng lupa"), ("Pohon yang tumbang", "Bumagsak na puno")], "correct": 1, "reason": ("Brad menafsirkan kata itu sebagai papan yang mungkin menutup emas.", "Ipinaliwanag ni Brad na maaaring tabla iyon na nakatakip sa ginto.")},
            {"prompt": ("Apa yang mereka temukan di bawah papan?", "Ano ang nakita nila sa ilalim ng tabla?"), "choices": [("Sepatu dan surat", "Sapatos at liham"), ("Buku lain", "Isa pang aklat"), ("Koin emas dan peta", "Gintong barya at mapa")], "correct": 2, "reason": ("Koin membuktikan ada harta, sedangkan peta menunjukkan pencarian belum selesai.", "Pinatunayan ng barya ang kayamanan at ipinakita ng mapa na may hahanapin pa.")},
        ],
    },
    {
        "title": "The Race for Water",
        "category": "Air dan lingkungan",
        "summary": ("Seorang anak menipu Langit agar menurunkan hujan di bukit sehingga air mengalir kembali memenuhi sungai kota.", "Nilinlang ng isang bata ang Langit na magpaulan sa burol kaya muling napuno ang ilog ng bayan."),
        "characters": ["a determined boy", "the Sky", "the townspeople"],
        "setting": "A riverside town and a hill during a drought.",
        "theme": ("Water must be appreciated, and clever action can repair communal mistakes.", "menghargai air dan memperbaiki kesalahan", "pagpapahalaga sa tubig at pagwawasto ng pagkakamali"),
        "events": ["The townspeople waste abundant river water.", "The Sky stops the rain and the river dries.", "A boy challenges the Sky to fill puddles before he reaches a hilltop.", "Rain runs downhill into the river instead, filling it and teaching the town to conserve water."],
        "sentences": [
            ("Sebuah kota memiliki banyak air sungai, tetapi penduduknya terus membuang-buangnya.", "Maraming tubig sa ilog ng isang bayan, ngunit patuloy itong sinasayang ng mga mamamayan."),
            ("Langit memperingatkan mereka, lalu menghentikan hujan ketika mereka tidak mau mendengarkan.", "Binalaan sila ng Langit at pagkatapos ay pinigil ang ulan nang hindi sila makinig."),
            ("Pada musim panas, sungai mengering dan penduduk menderita kekeringan.", "Pagsapit ng tag-init, natuyo ang ilog at dumanas ng tagtuyot ang bayan."),
            ("Seorang anak menganggap hukuman itu tidak adil dan menantang Langit berlomba menuju puncak bukit.", "Inisip ng isang bata na hindi makatarungan ang parusa, kaya hinamon niya ang Langit sa isang karera patungo sa tuktok ng burol."),
            ("Langit harus membuat genangan sebelum anak itu tiba, maka hujan deras turun di lereng.", "Kailangang makabuo ng mga lusak ang Langit bago makarating ang bata, kaya malakas itong nagpaulan sa dalisdis."),
            ("Air tidak membentuk genangan; semuanya mengalir turun dan memenuhi sungai.", "Hindi nabuo ang mga lusak; umagos pababa ang lahat ng tubig at napuno ang ilog."),
            ("Anak itu menang, dan penduduk berjanji akan menghargai air serta tidak menyia-nyiakannya lagi.", "Nanalo ang bata, at nangako ang mga tao na pahahalagahan ang tubig at hindi na ito sasayangin."),
        ],
        "vocabulary": [("sinasayang", "menyia-nyiakan", "pandiwa"), ("tagtuyot", "kekeringan", "pangngalan"), ("hinamon", "menantang", "pandiwa"), ("burol", "bukit", "pangngalan"), ("lusak", "genangan", "pangngalan"), ("umagos", "mengalir", "pandiwa"), ("napuno", "menjadi penuh", "pandiwa"), ("pahahalagahan", "akan menghargai", "pandiwa")],
        "expressions": [("hindi makatarungan", "tidak adil"), ("hindi na ito sasayangin", "tidak akan menyia-nyiakannya lagi")],
        "grammar": ("Bago + verba menandai batas waktu dalam tantangan. Hindi na menyatakan penghentian kebiasaan mulai sekarang.", "Tinutukoy ng bago + pandiwa ang hangganan ng oras sa hamon. Ipinahihiwatig ng hindi na ang pagtigil sa dating gawain mula ngayon."),
        "questions": [
            {"prompt": ("Mengapa Langit menghentikan hujan?", "Bakit pinigil ng Langit ang ulan?"), "choices": [("Penduduk menyia-nyiakan air", "Sinasayang ng mga tao ang tubig"), ("Anak itu memintanya", "Hiniling iyon ng bata"), ("Sungai terlalu dalam", "Masyadong malalim ang ilog")], "correct": 0, "reason": ("Langit ingin menghukum kota karena tidak menghargai persediaan airnya.", "Nais parusahan ng Langit ang bayan dahil hindi nito pinahalagahan ang tubig.")},
            {"prompt": ("Bagaimana tantangan anak itu mengisi sungai?", "Paano napuno ng hamon ng bata ang ilog?"), "choices": [("Ia menggali saluran sendiri", "Siya mismo ang naghukay ng kanal"), ("Hujan di bukit mengalir turun ke sungai", "Umagos sa ilog ang ulan mula sa burol"), ("Langit membawa ember", "Nagdala ng timba ang Langit")], "correct": 1, "reason": ("Lereng tidak menahan genangan, sehingga semua air hujan bergerak menuju sungai.", "Hindi nanatili ang tubig bilang lusak sa dalisdis kaya umagos lahat iyon sa ilog.")},
            {"prompt": ("Apa yang dijanjikan penduduk?", "Ano ang ipinangako ng mga mamamayan?"), "choices": [("Meninggalkan kota", "Lisanin ang bayan"), ("Tidak memakai sungai", "Huwag gamitin ang ilog"), ("Menghargai dan tidak membuang-buang air", "Pahalagahan at huwag sayangin ang tubig")], "correct": 2, "reason": ("Mereka akhirnya memahami bahwa air merupakan sumber daya yang harus dijaga.", "Naunawaan nilang ang tubig ay yamang kailangang ingatan.")},
        ],
    },
    {
        "title": "The Little Red Chicken",
        "category": "Fabel dan kerja",
        "summary": ("Ayam merah membuat roti sendiri setelah kucing menolak membantu, lalu mengajarinya bahwa keinginan harus disertai usaha.", "Gumawa mag-isa ng tinapay ang pulang manok matapos tumangging tumulong ang pusa, at itinuro nitong kailangang pagsikapan ang nais makuha."),
        "characters": ["the little red chicken", "the cat", "town customers"],
        "setting": "A small-town store and the place where the chicken makes bread.",
        "theme": ("People should work for what they want instead of depending on others.", "usaha dan kemandirian", "pagsisikap at sariling sikap"),
        "events": ["A cat wants bread, but the chicken's store has only wheat.", "The cat refuses the chicken's offer to help make bread.", "The chicken grinds the wheat and bakes bread alone.", "She refuses to give or sell it to the cat and advises him to grow his own wheat."],
        "sentences": [
            ("Seekor ayam merah kecil mempunyai toko, tetapi suatu hari hanya tersisa satu kantong gandum.", "May tindahan ang munting pulang manok, ngunit isang araw ay isang supot na trigo na lamang ang natira."),
            ("Seekor kucing ingin membeli roti dan marah ketika ayam mengatakan bahwa ia harus membantu membuatnya.", "Nais bumili ng tinapay ang isang pusa at nagalit nang sabihin ng manok na kailangan niyang tumulong sa paggawa nito."),
            ("Kucing menolak bekerja dan bahkan tidak mau berbicara baik-baik dengan ayam.", "Tumanggi ang pusa na magtrabaho at ayaw man lamang makipag-usap nang maayos sa manok."),
            ("Ayam memilih jumlah gandum yang tepat, menumbuknya, lalu memanggang roti segar sendiri.", "Pinili ng manok ang tamang dami ng trigo, dinikdik iyon, at saka naghurno ng sariwang tinapay nang mag-isa."),
            ("Ketika roti siap, kucing meminta bagian dan menawarkan uang, tetapi ayam tetap menolak.", "Nang handa na ang tinapay, humingi ng bahagi at nag-alok ng bayad ang pusa, ngunit tumanggi pa rin ang manok."),
            ("Ayam menjelaskan bahwa kucing tidak boleh bergantung pada orang lain untuk melakukan semua pekerjaan.", "Ipinaliwanag ng manok na hindi dapat umasa ang pusa sa iba para gawin ang lahat ng trabaho."),
            ("Ia menyarankan kucing menanam gandum sendiri agar dapat menikmati hasil usahanya.", "Iminungkahi niyang magtanim ang pusa ng sariling trigo upang makain nito ang bunga ng sariling pagsisikap."),
        ],
        "vocabulary": [("tindahan", "toko", "pangngalan"), ("trigo", "gandum", "pangngalan"), ("tinapay", "roti", "pangngalan"), ("tumulong", "membantu", "pandiwa"), ("dinikdik", "menumbuk", "pandiwa"), ("naghurno", "memanggang", "pandiwa"), ("tumanggi", "menolak", "pandiwa"), ("pagsisikap", "usaha", "pangngalan")],
        "expressions": [("hindi dapat umasa sa iba", "tidak boleh bergantung kepada orang lain"), ("bunga ng sariling pagsisikap", "hasil usaha sendiri")],
        "grammar": ("Dapat dan hindi dapat menyatakan anjuran positif atau larangan. Upang memperkenalkan tujuan menanam gandum.", "Ginagamit ang dapat at hindi dapat sa payo at pagbabawal. Ipinakikilala ng upang ang layunin ng pagtatanim ng trigo."),
        "questions": [
            {"prompt": ("Apa yang tersedia di toko ayam?", "Ano ang natira sa tindahan ng manok?"), "choices": [("Satu kantong gandum", "Isang supot na trigo"), ("Banyak roti", "Maraming tinapay"), ("Sebuah alat baru", "Bagong kagamitan")], "correct": 0, "reason": ("Toko hampir kosong dan hanya gandum yang dapat diolah menjadi roti.", "Halos walang laman ang tindahan at trigo lamang ang maaaring gawing tinapay.")},
            {"prompt": ("Mengapa ayam tidak memberi roti kepada kucing?", "Bakit hindi binigyan ng manok ng tinapay ang pusa?"), "choices": [("Kucing tidak punya uang", "Walang pera ang pusa"), ("Kucing menolak membantu membuatnya", "Tumangging tumulong ang pusa sa paggawa nito"), ("Roti itu rusak", "Sira ang tinapay")], "correct": 1, "reason": ("Ayam mengerjakan seluruh proses sendirian setelah kucing menolak bekerja.", "Ginawa ng manok nang mag-isa ang lahat matapos tumangging magtrabaho ang pusa.")},
            {"prompt": ("Apa saran ayam kepada kucing?", "Ano ang payo ng manok sa pusa?"), "choices": [("Mencuri roti", "Magnakaw ng tinapay"), ("Menunggu pemberian", "Maghintay ng ibibigay"), ("Menanam gandum dan bekerja sendiri", "Magtanim ng trigo at magsikap")], "correct": 2, "reason": ("Dengan menanam gandum, kucing dapat memperoleh roti dari usahanya sendiri.", "Sa pagtatanim ng trigo, makakakuha ang pusa ng tinapay mula sa sariling pagsisikap.")},
        ],
    },
    {
        "title": "Shipwrecked",
        "category": "Bertahan hidup",
        "summary": ("Mantan pengacara yang egois terdampar di pulau, belajar hidup sederhana, dan akhirnya memilih menetap ketika bantuan datang.", "Napadpad sa isang pulo ang dating makasariling abogado, natutong mamuhay nang payak, at piniling manatili roon nang dumating ang sasagip sa kaniya."),
        "characters": ["Simon Yates", "Mrs. Yates", "a ship captain", "rescuers"],
        "setting": "A ship at sea and a remote island.",
        "theme": ("Hardship can transform a person's values and definition of happiness.", "perubahan nilai melalui kesulitan", "pagbabago ng pagpapahalaga sa hirap"),
        "events": ["Selfish lawyer Simon loses his job and money and plans a new life abroad.", "A wave throws him from a ship, and he reaches an island alone.", "He builds shelter and tools, lives on fish and rainwater, and grows content.", "When rescuers arrive, Simon refuses to leave his simpler life."],
        "sentences": [
            ("Simon Yates adalah pengacara egois yang hanya membantu orang kaya, sehingga banyak orang tidak menyukainya.", "Makasariling abogado si Simon Yates na mayayaman lamang ang tinutulungan, kaya marami ang ayaw sa kaniya."),
            ("Setelah kehilangan pekerjaan dan uang, ia berlayar ke luar negeri untuk memulai hidup baru.", "Matapos mawalan ng trabaho at pera, naglayag siya sa ibang bansa upang magsimulang muli."),
            ("Menjelang akhir perjalanan, badai datang dan sebuah gelombang menyapu Simon dari kapal.", "Malapit sa dulo ng paglalakbay, dumating ang bagyo at tinangay ng alon si Simon mula sa barko."),
            ("Ia berenang sampai ke sebuah pulau, lalu membangun rumah pohon, membuat alat, menangkap ikan, dan menampung air hujan.", "Lumangoy siya hanggang sa isang pulo at gumawa roon ng bahay sa puno, mga kagamitan, at sisidlan ng tubig-ulan; nanghuli rin siya ng isda."),
            ("Sedikit demi sedikit, Simon mampu mengatasi masalah dan menikmati hidup yang lebih sederhana.", "Unti-unti niyang nalutas ang mga suliranin at natutuhang masiyahan sa payak na pamumuhay."),
            ("Akhirnya sebuah kapal menemukan dirinya dan menawarkan perjalanan pulang.", "Sa wakas, nakita siya ng isang barko at inalok na ihatid pauwi."),
            ("Simon menolak karena ia lebih memilih kedamaian pulau daripada kehidupan lamanya yang penuh uang dan ketidakadilan.", "Tumanggi si Simon dahil mas pinili niya ang payapang buhay sa pulo kaysa sa dati niyang buhay na puno ng salapi at kawalang-katarungan."),
        ],
        "vocabulary": [("abogado", "pengacara", "pangngalan"), ("makasarili", "egois", "pang-uri"), ("naglayag", "berlayar", "pandiwa"), ("tinangay", "tersapu", "pandiwa"), ("pulo", "pulau", "pangngalan"), ("sisidlan", "wadah", "pangngalan"), ("payak", "sederhana", "pang-uri"), ("tumanggi", "menolak", "pandiwa")],
        "expressions": [("upang magsimulang muli", "untuk memulai kembali"), ("mas pinili niya", "ia lebih memilih")],
        "grammar": ("Matapos + verba/nomina menandai tindakan yang sudah selesai sebelum tindakan berikutnya. Mas ... kaysa membentuk perbandingan pilihan.", "Tinutukoy ng matapos + pandiwa/pangngalan ang natapos na kilos bago ang kasunod. Binubuo ng mas ... kaysa ang paghahambing ng dalawang pagpipilian."),
        "questions": [
            {"prompt": ("Mengapa banyak orang tidak menyukai Simon sebelum kecelakaan?", "Bakit ayaw ng maraming tao kay Simon bago ang aksidente?"), "choices": [("Ia hanya membantu orang kaya", "Mayayaman lamang ang tinutulungan niya"), ("Ia takut berlayar", "Takot siyang maglayag"), ("Ia tinggal di pulau", "Nakatira siya sa pulo")], "correct": 0, "reason": ("Kebijakan Simon mengabaikan orang miskin dan ketidakadilan sosial.", "Binalewala ng patakaran ni Simon ang mahihirap at kawalang-katarungan.")},
            {"prompt": ("Bagaimana Simon bertahan hidup di pulau?", "Paano nabuhay si Simon sa pulo?"), "choices": [("Ia menemukan hotel", "Nakakita siya ng hotel"), ("Ia membuat tempat tinggal dan alat serta mencari makanan", "Gumawa siya ng tirahan at kagamitan at humanap ng pagkain"), ("Ia kembali berenang ke kapal", "Lumangoy siyang pabalik sa barko")], "correct": 1, "reason": ("Simon belajar memenuhi kebutuhannya sendiri dengan bahan dari pulau.", "Natutuhan ni Simon na tugunan ang pangangailangan gamit ang mga bagay sa pulo.")},
            {"prompt": ("Mengapa Simon tidak ikut kapal penyelamat?", "Bakit hindi sumama si Simon sa sasagip na barko?"), "choices": [("Ia tidak melihat kapal", "Hindi niya nakita ang barko"), ("Kapal itu terlalu kecil", "Masyadong maliit ang barko"), ("Ia lebih bahagia dengan hidup sederhana di pulau", "Mas masaya siya sa payak na buhay sa pulo")], "correct": 2, "reason": ("Pengalaman bertahan hidup telah mengubah pandangannya tentang kebahagiaan.", "Binago ng karanasan ang pananaw niya tungkol sa kaligayahan.")},
        ],
    },
    {
        "title": "The seven cities of gold",
        "category": "Sejarah dan penjelajahan",
        "summary": ("Coronado mengejar kabar tentang tujuh kota emas, tetapi menemukan permukiman tanah biasa dan pulang tanpa harta.", "Hinabol ni Coronado ang balita tungkol sa pitong lungsod na ginto, ngunit karaniwang pamayanang luwad ang natagpuan niya at umuwi siyang walang kayamanan."),
        "characters": ["Coronado", "three hundred expedition members", "residents of the cities", "Coronado's friends"],
        "setting": "A westward Spanish expedition and earthen settlements.",
        "theme": ("Greed and unquestioned rumors distort how people see real communities.", "keserakahan dan kabar yang tidak diuji", "kasakiman at di-sinusuring balita"),
        "events": ["Coronado hears extravagant reports about seven golden cities.", "He leads three hundred men west to find them.", "They encounter ordinary earthen cities whose residents feed them and deny that gold exists there.", "A final glint of sunlight tempts Coronado, but he accepts the truth and returns home."],
        "sentences": [
            ("Perwira Spanyol bernama Coronado mendengar kabar tentang tujuh kota yang dinding dan peralatannya terbuat dari emas.", "Nakarinig ang Espanyol na opisyal na si Coronado ng balita tungkol sa pitong lungsod na yari raw sa ginto ang mga pader at kagamitan."),
            ("Tanpa memeriksa kebenaran cerita itu, ia membawa tiga ratus orang, kuda, dan makanan dalam ekspedisi ke barat.", "Hindi niya sinuri kung totoo ang kuwento at nagsama siya ng tatlong daang tao, mga kabayo, at pagkain sa ekspedisyong pakanluran."),
            ("Setelah perjalanan panjang, mereka menemukan beberapa kota, tetapi rumah-rumahnya terbuat dari tanah liat, bukan emas.", "Matapos ang mahabang paglalakbay, nakakita sila ng mga lungsod, ngunit luwad at hindi ginto ang mga bahay."),
            ("Penduduk memakai pakaian sederhana dan makan sayuran dari mangkuk biasa.", "Payak ang damit ng mga naninirahan at gulay mula sa karaniwang mangkok ang kanilang pagkain."),
            ("Malam itu penduduk menjamu rombongan dan menasihati Coronado agar pulang karena tidak ada emas di sana.", "Nang gabing iyon, pinakain ng mga naninirahan ang pangkat at pinayuhan si Coronado na umuwi dahil walang ginto roon."),
            ("Saat berangkat, sinar matahari memantul pada rumah-rumah tanah dan sesaat tampak seperti emas.", "Sa pag-alis, tumama ang sinag ng araw sa mga bahay na luwad at sandaling nagmukhang ginto ang mga iyon."),
            ("Coronado menyadari bahwa itu hanya cahaya, lalu meninggalkan kota-kota tersebut dan pulang.", "Naunawaan ni Coronado na liwanag lamang iyon, kaya iniwan niya ang mga lungsod at umuwi."),
        ],
        "vocabulary": [("opisyal", "perwira", "pangngalan"), ("ginto", "emas", "pangngalan"), ("ekspedisyon", "ekspedisi", "pangngalan"), ("luwad", "tanah liat", "pangngalan"), ("naninirahan", "penduduk", "pangngalan"), ("pinayuhan", "menasihati", "pandiwa"), ("sinag", "sinar", "pangngalan"), ("liwanag", "cahaya", "pangngalan")],
        "expressions": [("walang ginto roon", "tidak ada emas di sana"), ("liwanag lamang iyon", "itu hanya cahaya")],
        "grammar": ("Yari sa atau gawa sa menyatakan bahan pembuat. Raw menandai informasi yang hanya didengar dari orang lain.", "Ipinahahayag ng yari sa o gawa sa ang materyales ng isang bagay. Ipinakikita ng raw na narinig lamang sa iba ang impormasyon."),
        "questions": [
            {"prompt": ("Mengapa Coronado pergi ke barat?", "Bakit naglakbay pakanluran si Coronado?"), "choices": [("Untuk mencari tujuh kota emas", "Upang hanapin ang pitong lungsod na ginto"), ("Untuk menjual sayuran", "Upang magbenta ng gulay"), ("Untuk mengunjungi keluarga", "Upang dalawin ang pamilya")], "correct": 0, "reason": ("Ia percaya cerita bahwa kota-kota itu berisi kekayaan besar.", "Naniwala siya sa kuwentong punô ng kayamanan ang mga lungsod.")},
            {"prompt": ("Terbuat dari apakah kota-kota yang ia temukan?", "Ano ang materyales ng mga lungsod na nakita niya?"), "choices": [("Perak", "Pilak"), ("Tanah liat", "Luwad"), ("Kaca", "Salamin")], "correct": 1, "reason": ("Bangunan yang sebenarnya berwarna cokelat dan dibuat dari tanah, bukan logam mulia.", "Kayumanggi at yari sa lupa ang tunay na mga gusali, hindi sa mamahaling metal.")},
            {"prompt": ("Apa yang sempat tampak seperti emas ketika Coronado pulang?", "Ano ang sandaling nagmukhang ginto nang pauwi si Coronado?"), "choices": [("Piring penduduk", "Mga plato ng mga naninirahan"), ("Pakaian para prajurit", "Damit ng mga kawal"), ("Sinar matahari pada rumah tanah", "Sinag ng araw sa mga bahay na luwad")], "correct": 2, "reason": ("Pantulan cahaya menciptakan kilau sesaat, tetapi Coronado tahu itu bukan emas.", "Lumikha ng panandaliang kislap ang liwanag, ngunit alam ni Coronado na hindi iyon ginto.")},
        ],
    },
])


SOURCE_TITLES = [
    "The Lion and the Rabbit",
    "The Laboratory",
    "The Report",
    "The Dog’s Bell",
    "The Jackal and the Sun Child",
    "The Friendly Ghost",
    "The Best Prince",
    "How the Sun and the Moon Were Made",
    "The Starfish",
    "The First Peacock",
    "Princess Rose and the Creature",
    "The Crazy Artist",
    "The Farmer and the Cats",
    "A Magical Book",
    "The Big Race",
    "Adams County’s Gold",
    "The Race for Water",
    "The Little Red Chicken",
    "Shipwrecked",
    "The seven cities of gold",
    "Katy",
    "A Better Reward",
    "The camp",
    "A Strong Friendship",
    "Joe’s Pond",
    "Archie and His Donkey",
    "The Spider and the Bird",
    "The Party",
    "How the World Got Light",
    "Cats and Secrets",
]
if len({story["title"] for story in STORIES}) != len(STORIES):
    raise ValueError("Duplicate story title in generated data")
_stories_by_title = {story["title"]: story for story in STORIES}
if set(_stories_by_title) != set(SOURCE_TITLES):
    raise ValueError("Generated story titles do not match the Book 1 inventory")
STORIES = [_stories_by_title[title] for title in SOURCE_TITLES]


def build_story_document(spec: dict[str, Any], order: int, image_path: str) -> dict[str, Any]:
    story_id = f"book1-story-{order:02d}-{slugify(spec['title'])}"
    questions, answers = build_questions(story_id, spec["questions"])
    expressions_id = "; ".join(f"“{phrase}” — {meaning}" for phrase, meaning in spec["expressions"])
    expressions_fil = "; ".join(
        f"“{phrase}” — ang katumbas sa Indonesian ay “{meaning}”"
        for phrase, meaning in spec["expressions"]
    )
    document = {
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
        "title": localized(spec["title"], spec["title"]),
        "originalTitle": spec["title"],
        "summary": localized(spec["summary"][0], spec["summary"][1]),
        "objectives": [
            localized(
                f"Menelusuri sebab dan akibat dalam “{spec['title']}”.",
                f"Sundan ang sanhi at bunga sa “{spec['title']}”.",
            ),
            localized(
                f"Menjelaskan tema {spec['theme'][1].lower()} melalui keputusan para tokoh.",
                f"Ipaliwanag ang temang {spec['theme'][2].lower()} sa pamamagitan ng mga pasiya ng mga tauhan.",
            ),
        ],
        "sentences": [localized(indonesian, filipino) for indonesian, filipino in spec["sentences"]],
        "sentenceCount": len(spec["sentences"]),
        "speakers": [None] * len(spec["sentences"]),
        "notes": [
            {
                "title": localized("Ungkapan berguna", "Mga kapaki-pakinabang na pahayag"),
                "text": localized(expressions_id, expressions_fil),
            },
            {
                "title": localized("Catatan tata bahasa", "Tala sa gramatika"),
                "text": localized(spec["grammar"][0], spec["grammar"][1]),
            },
        ],
        "focus": localized(
            [meaning for _, meaning, _ in spec["vocabulary"]],
            [word for word, _, _ in spec["vocabulary"]],
        ),
        "questions": questions,
        "answers": answers,
        "vocabulary": [
            vocabulary_entry(spec, word, meaning, part_of_speech)
            for word, meaning, part_of_speech in spec["vocabulary"]
        ],
        "assets": [image_path],
    }
    return document


def parse_epub(epub: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[int, bytes]]:
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
            "epubSha256": sha256_file(epub),
            "opfSha256": sha256_bytes(opf_bytes),
        }
        manifest = {
            item.attrib["id"]: item.attrib["href"]
            for item in opf.findall(f"{OPF_NS}manifest/{OPF_NS}item")
        }
        spine = [
            manifest[item.attrib["idref"]]
            for item in opf.findall(f"{OPF_NS}spine/{OPF_NS}itemref")
        ]
        documents: list[dict[str, Any]] = []
        narratives: list[dict[str, Any]] = []
        images: dict[int, bytes] = {}
        for position, href in enumerate(spine, 1):
            path = f"OEBPS/{href}"
            data = archive.read(path)
            root = ET.fromstring(data)
            title = strip_unit_number(xml_text(root.find(f".//{XHTML_NS}h1")))
            paragraphs = [xml_text(value) for value in root.findall(f".//{XHTML_NS}p") if xml_text(value)]
            image = root.find(f".//{XHTML_NS}img")
            role = "story" if re.fullmatch(r"Text/Unit_\d{2}\.xhtml", href) else "reference"
            if href == "Text/cover.xhtml":
                role = "cover"
            document = {
                "spinePosition": position,
                "path": path,
                "role": role,
                "title": title,
                "sha256": sha256_bytes(data),
                "paragraphCount": len(paragraphs),
                "wordCount": len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", " ".join(paragraphs))),
            }
            documents.append(document)
            if role == "story":
                number = int(re.search(r"(\d{2})", href).group(1))
                if image is None:
                    raise ValueError(f"Story {number} has no illustration")
                image_href = image.attrib["src"].replace("../", "OEBPS/")
                image_data = archive.read(image_href)
                images[number] = image_data
                narratives.append({
                    **document,
                    "order": number,
                    "sourceImage": image_href,
                })
        return source, documents, narratives, images


def build(epub: Path, root: Path) -> None:
    source, documents, narratives, images = parse_epub(epub)
    if source["title"].casefold() != BOOK_TITLE.casefold():
        raise ValueError(f"Unexpected EPUB title: {source['title']}")
    if len(STORIES) != 30 or len(narratives) != 30 or sorted(images) != list(range(1, 31)):
        raise ValueError("Book 1 must contain exactly 30 illustrated narrative units")
    output_dir = root / "storie" / COLLECTION_ID
    assets_dir = output_dir / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    references: list[dict[str, Any]] = []
    asset_audit: list[dict[str, Any]] = []
    story_audit: list[dict[str, Any]] = []
    for order, (spec, source_story) in enumerate(zip(STORIES, narratives, strict=True), 1):
        if source_story["order"] != order or source_story["title"] != spec["title"]:
            raise ValueError(
                f"Source title mismatch at unit {order}: {source_story['title']!r} != {spec['title']!r}"
            )
        media_type, extension, width, height = image_info(images[order])
        stem = f"{order:02d}-{slugify(spec['title'])}"
        image_path = f"assets/{stem}{extension}"
        image_target = output_dir / image_path
        image_target.write_bytes(images[order])
        image_hash = sha256_file(image_target)
        asset_audit.append({
            "storyOrder": order,
            "sourcePath": source_story["sourceImage"],
            "path": f"{COLLECTION_ID}/{image_path}",
            "mediaType": media_type,
            "width": width,
            "height": height,
            "bytes": image_target.stat().st_size,
            "sha256": image_hash,
            "optimization": "source bytes preserved; EPUB asset was already compressed",
        })

        story = build_story_document(spec, order, image_path)
        story_path = output_dir / f"{stem}.json"
        story_path.write_bytes(json_bytes(story))
        story_hash = sha256_file(story_path)
        relative_story_path = f"{COLLECTION_ID}/{story_path.name}"
        references.append({
            "id": story["id"],
            "collectionId": COLLECTION_ID,
            "family": story["family"],
            "category": story["category"],
            "level": story["level"],
            "order": order,
            "sourceOrder": order,
            "path": relative_story_path,
            "sha256": story_hash,
            "sentenceCount": story["sentenceCount"],
            "title": story["title"],
            "summary": story["summary"],
            "image": image_path,
            "assets": story["assets"],
        })
        story_audit.append({
            "order": order,
            "title": spec["title"],
            "sourceDocument": source_story["path"],
            "sourceSha256": source_story["sha256"],
            "sourceParagraphCount": source_story["paragraphCount"],
            "sourceWordCount": source_story["wordCount"],
            "characters": spec["characters"],
            "setting": spec["setting"],
            "theme": spec["theme"][0],
            "mainEvents": spec["events"],
            "generatedStory": relative_story_path,
            "generatedSha256": story_hash,
            "illustration": f"{COLLECTION_ID}/{image_path}",
        })

    audit = {
        "schemaVersion": 1,
        "source": source,
        "inspection": {
            "spineDocumentCount": len(documents),
            "actualNarrativeCount": len(story_audit),
            "classificationRule": "Only numbered Unit_01 through Unit_30 documents contain complete narratives; cover and Note documents are excluded.",
            "excludedDocumentCount": sum(value["role"] != "story" for value in documents),
            "excludedDocuments": [
                {"path": value["path"], "role": value["role"]}
                for value in documents if value["role"] != "story"
            ],
        },
        "documentCount": len(documents),
        "documents": documents,
        "storyCount": len(story_audit),
        "stories": story_audit,
        "assets": {
            "availableIllustrations": len(images),
            "extracted": len(asset_audit),
            "skippedUnrelated": ["OEBPS/Images/cover.jpg"],
            "items": asset_audit,
        },
        "copyrightTreatment": "Each entry is a concise original bilingual retelling and does not reproduce or translate the complete source story text.",
    }
    audit_path = root / "storie" / "source-audit.json"
    audit_path.write_bytes(json_bytes(audit))

    index = {
        "schemaVersion": 1,
        "id": COLLECTION_ID,
        "languagePair": {"reference": "id", "target": "fil"},
        "title": localized(
            "Cerita dari 4000 Essential English Words — Buku 1",
            "Mga Kuwento mula sa 4000 Essential English Words — Book 1",
        ),
        "description": localized(
            "Tiga puluh retelling ringkas dalam bahasa Tagalog dengan terjemahan Indonesia, mengikuti urutan asli buku.",
            "Tatlumpung maiikling muling pagsasalaysay sa Tagalog na may salin sa Indonesian, ayon sa orihinal na ayos ng aklat.",
        ),
        "storyCount": len(references),
        "sourceAudit": {"path": "source-audit.json", "sha256": sha256_file(audit_path)},
        "stories": references,
    }
    index_path = root / "storie" / "index.json"
    index_path.write_bytes(json_bytes(index))

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stories"] = {"index": "storie/index.json", "sha256": sha256_file(index_path)}
    manifest_path.write_bytes(json_bytes(manifest))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    build(args.epub.resolve(), args.root.resolve())


if __name__ == "__main__":
    main()
