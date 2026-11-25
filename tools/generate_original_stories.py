#!/usr/bin/env python3
"""Build RoLang's original bilingual story collection and discovery hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY_ROOT = ROOT / "storie"
COLLECTION = STORY_ROOT / "original-tagalog-stories"


def localized(indonesian: str, tagalog: str) -> dict[str, str]:
    return {"id": indonesian, "fil": tagalog}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


STORIES = [
    {
        "slug": "ang-payong-sa-huling-upuan", "level": "BEGINNER", "family": "daily-life",
        "category": "Kehidupan sehari-hari", "image": "travel",
        "title": ("Payung di Kursi Belakang", "Ang Payong sa Huling Upuan"),
        "summary": ("Lira menemukan payung di jeepney dan berusaha mengembalikannya sebelum hujan turun.",
                    "Nakakita si Lira ng payong sa jeep at sinikap niyang maibalik ito bago umulan."),
        "paragraphs": [
            ("Sepulang kerja, Lira naik jeepney yang hampir kosong.", "Pagkatapos ng trabaho, sumakay si Lira sa jeep na halos walang laman."),
            ("Di kursi belakang, ia melihat payung biru dengan pita kuning pada gagangnya.", "Sa huling upuan, nakita niya ang asul na payong na may dilaw na laso sa hawakan."),
            ("Sopir tidak tahu siapa pemiliknya, tetapi ia ingat seorang perempuan tua turun di dekat perpustakaan.", "Hindi alam ng drayber kung sino ang may-ari, pero naalala niyang may matandang babaeng bumaba malapit sa aklatan."),
            ("Lira turun di sana dan bertanya kepada penjaga, ‘Apakah ada yang mencari payung?’", "Bumaba roon si Lira at nagtanong sa guwardiya, ‘May naghahanap po ba ng payong?’"),
            ("Penjaga menunjuk ke arah toko roti, tempat seorang perempuan tua sedang menunggu cucunya.", "Itinuro ng guwardiya ang panaderya, kung saan naghihintay ang isang matandang babae sa kaniyang apo."),
            ("Perempuan itu mengenali pita kuning yang dibuat cucunya dan tersenyum lega.", "Nakilala ng babae ang dilaw na lasong ginawa ng kaniyang apo at napangiti siya sa ginhawa."),
            ("Saat hujan mulai turun, ia membuka payung itu dan mengajak Lira berjalan bersama sampai halte.", "Nang magsimulang umulan, binuksan niya ang payong at niyayang maglakad si Lira kasama niya hanggang hintuan."),
            ("Lira pulang sedikit terlambat, tetapi ia senang karena benda yang hilang telah kembali kepada pemiliknya.", "Medyo gabing nakauwi si Lira, pero masaya siya dahil nakabalik sa may-ari ang nawawalang gamit."),
        ],
        "vocab": [("payong", "payung", "pangngalan"), ("hawakan", "gagang", "pangngalan"), ("may-ari", "pemilik", "pangngalan"),
                  ("aklatan", "perpustakaan", "pangngalan"), ("guwardiya", "penjaga", "pangngalan"), ("panaderya", "toko roti", "pangngalan"),
                  ("ginhawa", "rasa lega", "pangngalan"), ("hintuan", "halte", "pangngalan")],
        "notes": [("Po untuk kesopanan", "Po para sa paggalang", "Gunakan po ketika berbicara sopan kepada orang yang lebih tua.", "Gamitin ang po kapag magalang na nakikipag-usap sa nakatatanda."),
                  ("Penanda ang", "Panandang ang", "Ang menandai topik tertentu, seperti ang payong.", "Tinutukoy ng ang ang paksa, gaya ng ang payong.")],
        "qa": ("Di mana perempuan tua itu menunggu?", "Saan naghihintay ang matandang babae?", "Di toko roti.", "Sa panaderya."),
        "fill": ("Lira melihat sebuah ____ biru di kursi belakang.", "Nakakita si Lira ng asul na ____ sa huling upuan.", "payung", "payong"),
        "grammar": ("Kalimat mana yang meminta informasi dengan sopan?", "Aling pangungusap ang magalang na humihingi ng impormasyon?",
                    [("Apakah ada yang mencari payung?", "May naghahanap po ba ng payong?"), ("Berikan payung itu!", "Ibigay mo ang payong!"), ("Saya tidak peduli.", "Wala akong pakialam.")], 0),
        "construction": ("Lira mengembalikan payung itu.", "Ibinalik ni Lira ang payong."),
    },
    {
        "slug": "ang-sopas-para-kay-aling-rosa", "level": "BEGINNER", "family": "food-care",
        "category": "Makanan dan kepedulian", "image": "food",
        "title": ("Sup untuk Bu Rosa", "Ang Sopas para kay Aling Rosa"),
        "summary": ("Niko belajar memasak sup sederhana untuk tetangganya yang sedang sakit.", "Natuto si Niko na magluto ng payak na sopas para sa kapitbahay niyang may sakit."),
        "paragraphs": [
            ("Pada Sabtu pagi, Niko mendengar tetangganya, Bu Rosa, sedang batuk.", "Noong Sabado ng umaga, narinig ni Niko na inuubo ang kapitbahay niyang si Aling Rosa."),
            ("Ia ingin membantu, jadi ia menelepon ibunya dan meminta resep sup ayam.", "Gusto niyang tumulong kaya tinawagan niya ang kaniyang ina at humingi ng resipe ng sopas na manok."),
            ("Ibunya berkata, ‘Potong sayuran kecil-kecil dan masukkan garam sedikit saja.’", "Sabi ng kaniyang ina, ‘Hiwain nang maliliit ang gulay at kaunting asin lang ang ilagay.’"),
            ("Niko mengikuti petunjuk, tetapi ia hampir menuangkan dua sendok garam.", "Sinunod ni Niko ang bilin, pero muntik na siyang maglagay ng dalawang kutsarang asin."),
            ("Adiknya menghentikannya dan menunjukkan sendok teh yang benar.", "Pinigilan siya ng kaniyang kapatid at ipinakita ang tamang kutsarita."),
            ("Setelah sup matang, mereka mencicipinya bersama dan menambahkan sedikit lada.", "Nang maluto ang sopas, sabay nila itong tinikman at dinagdagan ng kaunting paminta."),
            ("Bu Rosa menerima mangkuk hangat itu dan berkata bahwa aromanya membuatnya lapar.", "Tinanggap ni Aling Rosa ang mainit na mangkok at sinabing ginutom siya ng mabangong amoy nito."),
            ("Keesokan hari ia sudah merasa lebih baik, sedangkan Niko menyimpan resep itu di dapur.", "Kinabukasan, mas mabuti na ang pakiramdam niya, at itinabi naman ni Niko ang resipe sa kusina."),
        ],
        "vocab": [("inuubo", "sedang batuk", "pandiwa"), ("resipe", "resep", "pangngalan"), ("hiwain", "potonglah", "pandiwa"),
                  ("asin", "garam", "pangngalan"), ("kutsarita", "sendok teh", "pangngalan"), ("tinikman", "mencicipi", "pandiwa"),
                  ("mangkok", "mangkuk", "pangngalan"), ("kusina", "dapur", "pangngalan")],
        "notes": [("Bentuk perintah", "Pautos na anyo", "Kata seperti hiwain dan ilagay memberi petunjuk langsung.", "Ang hiwain at ilagay ay ginagamit sa tuwirang panuto."),
                  ("Kaunting", "Kaunting", "Kaunting berarti jumlah kecil dan diikuti benda.", "Ang kaunting ay tumutukoy sa maliit na dami ng isang bagay.")],
        "qa": ("Siapa yang mencegah Niko menambahkan terlalu banyak garam?", "Sino ang pumigil kay Niko na maglagay ng sobrang asin?", "Adiknya.", "Ang kaniyang kapatid."),
        "fill": ("Ibu Niko memberinya ____ sup ayam.", "Binigyan siya ng kaniyang ina ng ____ ng sopas na manok.", "resep", "resipe"),
        "grammar": ("Mana yang merupakan petunjuk memasak?", "Alin ang panuto sa pagluluto?",
                    [("Potong sayuran kecil-kecil.", "Hiwain nang maliliit ang gulay."), ("Supnya sudah habis.", "Ubos na ang sopas."), ("Bu Rosa sedang tidur.", "Natutulog si Aling Rosa.")], 0),
        "construction": ("Niko mencicipi sup hangat itu.", "Tinikman ni Niko ang mainit na sopas."),
    },
    {
        "slug": "ang-maling-hintuan", "level": "BEGINNER", "family": "travel-directions",
        "category": "Perjalanan dan arah", "image": "travel",
        "title": ("Halte yang Salah", "Ang Maling Hintuan"),
        "summary": ("Rani turun terlalu cepat dari bus dan memakai Tagalog untuk menemukan museum.", "Masyadong maagang bumaba si Rani sa bus at gumamit siya ng Tagalog upang mahanap ang museo."),
        "paragraphs": [
            ("Rani, seorang pelajar dari Indonesia, ingin mengunjungi museum kota pada hari Minggu.", "Gustong bumisita ni Rani, isang mag-aaral mula sa Indonesia, sa museo ng lungsod noong Linggo."),
            ("Ia membaca papan dengan terburu-buru dan turun satu halte terlalu cepat.", "Nagmamadali niyang binasa ang karatula at bumaba siya nang isang hintuan nang mas maaga."),
            ("Di sekelilingnya hanya ada toko, gereja kecil, dan jalan yang tidak dikenalnya.", "Mga tindahan, isang maliit na simbahan, at di-kilalang daan lamang ang nasa paligid niya."),
            ("Rani menarik napas lalu bertanya kepada penjual buah, ‘Permisi, bagaimana menuju museum?’", "Huminga nang malalim si Rani at nagtanong sa tindera ng prutas, ‘Makikiraan po, paano pumunta sa museo?’"),
            ("Penjual itu menyuruhnya berjalan lurus, menyeberang di lampu lalu lintas, lalu belok kanan.", "Sinabi ng tindera na dumiretso siya, tumawid sa ilaw-trapiko, at saka kumanan."),
            ("Rani mengulangi petunjuk itu agar tidak lupa, dan penjual tersebut mengangguk.", "Inulit ni Rani ang direksiyon upang hindi makalimot, at tumango ang tindera."),
            ("Sepuluh menit kemudian, ia melihat bendera besar di depan museum.", "Pagkaraan ng sampung minuto, nakita niya ang malaking watawat sa harap ng museo."),
            ("Ia terlambat mengikuti tur pertama, tetapi sekarang ia tahu cara bertanya dan memahami arah.", "Nahuli siya sa unang paglilibot, pero alam na niya ngayon kung paano magtanong at umunawa ng direksiyon."),
        ],
        "vocab": [("hintuan", "halte", "pangngalan"), ("karatula", "papan tanda", "pangngalan"), ("paligid", "sekitar", "pangngalan"),
                  ("dumiretso", "jalan lurus", "pandiwa"), ("tumawid", "menyeberang", "pandiwa"), ("kumanan", "belok kanan", "pandiwa"),
                  ("tumango", "mengangguk", "pandiwa"), ("watawat", "bendera", "pangngalan")],
        "notes": [("Urutan arah", "Ayos ng direksiyon", "Gunakan muna, saka, dan pagkatapos untuk mengurutkan petunjuk.", "Gamitin ang muna, saka, at pagkatapos upang ayusin ang direksiyon."),
                  ("Paano", "Paano", "Paano menanyakan cara melakukan atau mencapai sesuatu.", "Ginagamit ang paano upang itanong ang paraan ng paggawa o pagpunta.")],
        "qa": ("Kepada siapa Rani meminta petunjuk?", "Kanino nagtanong ng direksiyon si Rani?", "Kepada penjual buah.", "Sa tindera ng prutas."),
        "fill": ("Rani turun satu ____ terlalu cepat.", "Bumaba si Rani nang isang ____ nang mas maaga.", "halte", "hintuan"),
        "grammar": ("Kata tanya mana yang berarti ‘bagaimana’?", "Aling salitang pananong ang nangangahulugang ‘bagaimana’?",
                    [("paano", "paano"), ("sino", "sino"), ("kailan", "kailan")], 0),
        "construction": ("Rani berjalan lurus lalu belok kanan.", "Dumiretso si Rani at saka kumanan."),
    },
    {
        "slug": "ang-munting-hardin-sa-bubong", "level": "BEGINNER", "family": "community-environment",
        "category": "Komunitas dan lingkungan", "image": "family",
        "title": ("Kebun Kecil di Atap", "Ang Munting Hardin sa Bubong"),
        "summary": ("Para penghuni apartemen mengubah atap kosong menjadi kebun bersama.", "Ginawang hardin ng mga residente ang dating bakanteng bubong ng kanilang gusali."),
        "paragraphs": [
            ("Atap apartemen Mila dahulu panas, kosong, dan penuh pot rusak.", "Mainit, bakante, at puno ng sirang paso ang bubong ng gusali nina Mila noon."),
            ("Suatu sore, Mila mengusulkan kebun kecil kepada para tetangga.", "Isang hapon, iminungkahi ni Mila sa mga kapitbahay ang isang munting hardin."),
            ("Ada yang membawa tanah, ada yang membawa bibit tomat, dan anak-anak mengecat pot lama.", "May nagdala ng lupa, may nagdala ng binhi ng kamatis, at pinintahan ng mga bata ang lumang paso."),
            ("Mereka membagi tugas: menyiram pada pagi hari, membersihkan pada sore hari, dan mencatat pertumbuhan tanaman.", "Hinati nila ang gawain: magdilig sa umaga, maglinis sa hapon, at itala ang paglaki ng halaman."),
            ("Pada minggu pertama, hujan deras menjatuhkan dua pot di dekat pintu.", "Sa unang linggo, natumba ng malakas na ulan ang dalawang paso malapit sa pinto."),
            ("Para tetangga membuat rak rendah dari kayu agar semua pot lebih aman.", "Gumawa ang mga kapitbahay ng mababang patungang kahoy upang maging ligtas ang lahat ng paso."),
            ("Dua bulan kemudian, mereka memanen tomat, cabai, dan daun bawang untuk makan malam bersama.", "Pagkaraan ng dalawang buwan, umani sila ng kamatis, sili, at dahon ng sibuyas para sa salu-salong hapunan."),
            ("Atap itu tidak lagi kosong; setiap sore tempat itu dipenuhi tanaman, percakapan, dan tawa.", "Hindi na bakante ang bubong; tuwing hapon, puno na ito ng halaman, kuwentuhan, at tawanan."),
        ],
        "vocab": [("bubong", "atap", "pangngalan"), ("paso", "pot tanaman", "pangngalan"), ("binhi", "bibit", "pangngalan"),
                  ("magdilig", "menyiram", "pandiwa"), ("halaman", "tanaman", "pangngalan"), ("patungan", "rak atau alas", "pangngalan"),
                  ("umani", "memanen", "pandiwa"), ("tawanan", "gelak tawa", "pangngalan")],
        "notes": [("May untuk keberadaan", "May para sa pag-iral", "May memperkenalkan orang atau benda yang ada.", "Ginagamit ang may upang ipakilala ang taong o bagay na naroon."),
                  ("Agar atau upang", "Upang", "Upang memperkenalkan tujuan suatu tindakan.", "Ipinakikilala ng upang ang layunin ng isang kilos.")],
        "qa": ("Mengapa para tetangga membuat rak kayu?", "Bakit gumawa ng patungang kahoy ang mga kapitbahay?", "Agar pot lebih aman.", "Upang maging mas ligtas ang mga paso."),
        "fill": ("Anak-anak mengecat pot atau ____ lama.", "Pinintahan ng mga bata ang lumang ____.", "pot tanaman", "paso"),
        "grammar": ("Kalimat mana yang menyatakan tujuan?", "Aling pangungusap ang nagsasaad ng layunin?",
                    [("Mereka membuat rak agar pot aman.", "Gumawa sila ng patungan upang maging ligtas ang paso."), ("Hujan turun kemarin.", "Umulan kahapon."), ("Atapnya sangat panas.", "Napakainit ng bubong.")], 0),
        "construction": ("Para tetangga menanam tomat bersama.", "Sabay-sabay na nagtanim ng kamatis ang mga kapitbahay."),
    },
    {
        "slug": "ang-tahimik-na-kaklase", "level": "BEGINNER", "family": "school-work",
        "category": "Sekolah dan pekerjaan", "image": "classroom",
        "title": ("Teman Sekelas yang Pendiam", "Ang Tahimik na Kaklase"),
        "summary": ("Sebuah proyek kelompok menunjukkan bahwa ide yang tenang juga dapat memimpin.", "Ipinakita ng isang pangkatang proyekto na maaari ring manguna ang tahimik na ideya."),
        "paragraphs": [
            ("Kelas Ben mendapat tugas membuat peta tempat aman di sekitar sekolah.", "Inatasan ang klase ni Ben na gumawa ng mapa ng mga ligtas na lugar sa paligid ng paaralan."),
            ("Semua anggota kelompok berbicara bersamaan, kecuali Maya yang duduk sambil menggambar.", "Sabay-sabay magsalita ang lahat sa pangkat, maliban kay Maya na tahimik na gumuguhit."),
            ("Ben mengira Maya tidak tertarik, lalu ia bertanya apa yang sedang dibuatnya.", "Akala ni Ben ay hindi interesado si Maya kaya tinanong niya kung ano ang ginagawa nito."),
            ("Maya menunjukkan simbol sederhana untuk klinik, kantor polisi, jembatan, dan titik pertemuan.", "Ipinakita ni Maya ang payak na simbolo para sa klinika, himpilan ng pulis, tulay, at tagpuan."),
            ("Kelompok itu menyadari bahwa gambarnya membuat peta jauh lebih mudah dibaca.", "Napansin ng pangkat na naging mas madaling basahin ang mapa dahil sa kaniyang mga guhit."),
            ("Mereka berhenti saling memotong pembicaraan dan memberi setiap orang waktu menjelaskan ide.", "Tumigil sila sa pagsabat at binigyan ang bawat isa ng oras upang ipaliwanag ang ideya."),
            ("Saat presentasi, Maya menerangkan simbol, sementara Ben menjelaskan rute keluar.", "Sa presentasyon, ipinaliwanag ni Maya ang mga simbolo habang ipinaliwanag naman ni Ben ang daan palabas."),
            ("Guru memuji peta mereka dan kelompok itu belajar bahwa mendengarkan adalah bagian penting dari kerja sama.", "Pinuri ng guro ang kanilang mapa, at natutuhan ng pangkat na mahalagang bahagi ng pagtutulungan ang pakikinig."),
        ],
        "vocab": [("mapa", "peta", "pangngalan"), ("pangkat", "kelompok", "pangngalan"), ("gumuguhit", "sedang menggambar", "pandiwa"),
                  ("simbolo", "simbol", "pangngalan"), ("tagpuan", "titik pertemuan", "pangngalan"), ("pagsabat", "memotong pembicaraan", "pangngalan"),
                  ("ipaliwanag", "menjelaskan", "pandiwa"), ("pakikinig", "mendengarkan", "pangngalan")],
        "notes": [("Habang", "Habang", "Habang menghubungkan dua tindakan yang berlangsung pada waktu yang sama.", "Pinagdurugtong ng habang ang dalawang kilos na sabay na nangyayari."),
                  ("Akala", "Akala", "Akala memperkenalkan dugaan yang belum tentu benar.", "Ginagamit ang akala sa palagay na maaaring hindi tama." )],
        "qa": ("Apa yang digambar Maya?", "Ano ang iginuhit ni Maya?", "Simbol untuk peta.", "Mga simbolo para sa mapa."),
        "fill": ("Maya membuat ____ sederhana untuk klinik dan kantor polisi.", "Gumawa si Maya ng payak na ____ para sa klinika at himpilan ng pulis.", "simbol", "simbolo"),
        "grammar": ("Kata mana menghubungkan dua tindakan bersamaan?", "Aling salita ang nag-uugnay sa dalawang sabay na kilos?",
                    [("habang", "habang"), ("dahil", "dahil"), ("bukas", "bukas")], 0),
        "construction": ("Kelompok itu mendengarkan ide Maya.", "Pinakinggan ng pangkat ang ideya ni Maya."),
    },
    {
        "slug": "ang-liham-ni-lola", "level": "BEGINNER", "family": "family-friendship",
        "category": "Keluarga dan persahabatan", "image": "family",
        "title": ("Surat dari Nenek", "Ang Liham ni Lola"),
        "summary": ("Sebuah surat lama membantu keluarga Aya menyiapkan kejutan ulang tahun.", "Tumulong ang isang lumang liham sa pamilya ni Aya upang maghanda ng sorpresa sa kaarawan."),
        "paragraphs": [
            ("Seminggu sebelum ulang tahun ayahnya, Aya menemukan amplop di dalam buku masak lama.", "Isang linggo bago ang kaarawan ng kaniyang ama, nakakita si Aya ng sobre sa loob ng lumang aklat sa pagluluto."),
            ("Surat itu ditulis neneknya bertahun-tahun lalu dan berisi resep kue pisang kesukaan ayah.", "Isinulat iyon ng kaniyang lola maraming taon na ang nakaraan at naroon ang resipe ng paboritong keyk na saging ng kaniyang ama."),
            ("Tulisan tangan nenek sulit dibaca, jadi Aya meminta bantuan bibinya melalui panggilan video.", "Mahirap basahin ang sulat-kamay ng lola kaya humingi ng tulong si Aya sa kaniyang tiya sa video call."),
            ("Mereka membaca setiap baris perlahan dan menemukan catatan kecil: tambahkan kulit jeruk agar harum.", "Dahan-dahan nilang binasa ang bawat linya at nakita ang munting tala: dagdagan ng balat ng dalandan upang bumango."),
            ("Pada hari ulang tahun, Aya dan adiknya memasak saat ayah mereka pergi ke pasar.", "Sa araw ng kaarawan, nagluto sina Aya at ang kapatid niya habang nasa palengke ang kanilang ama."),
            ("Kue pertama terlalu matang, tetapi kue kedua mengembang dengan baik.", "Nasobrahan sa luto ang unang keyk, pero maayos na umalsa ang pangalawa."),
            ("Ketika ayah pulang, aroma jeruk membuatnya berhenti di pintu dan mengingat dapur nenek.", "Pag-uwi ng kanilang ama, napatigil siya sa pinto dahil ipinaalala ng amoy ng dalandan ang kusina ng lola."),
            ("Mereka makan bersama, lalu Aya menyimpan surat itu dalam bingkai agar resep dan kenangan tetap terjaga.", "Sabay-sabay silang kumain, at inilagay ni Aya sa kuwadro ang liham upang manatiling ligtas ang resipe at alaala."),
        ],
        "vocab": [("liham", "surat", "pangngalan"), ("sobre", "amplop", "pangngalan"), ("sulat-kamay", "tulisan tangan", "pangngalan"),
                  ("tala", "catatan", "pangngalan"), ("dalandan", "jeruk", "pangngalan"), ("umalsa", "mengembang", "pandiwa"),
                  ("kuwadro", "bingkai", "pangngalan"), ("alaala", "kenangan", "pangngalan")],
        "notes": [("Sina untuk beberapa nama", "Sina para sa maramihang pangalan", "Sina dipakai sebelum dua atau lebih nama orang.", "Ginagamit ang sina bago sa dalawa o higit pang pangalan ng tao."),
                  ("Upang", "Upang", "Upang menunjukkan tujuan, seperti upang bumango.", "Ipinakikita ng upang ang layunin, gaya ng upang bumango." )],
        "qa": ("Apa catatan kecil dalam resep nenek?", "Ano ang munting tala sa resipe ng lola?", "Tambahkan kulit jeruk.", "Dagdagan ng balat ng dalandan."),
        "fill": ("Aya menemukan sebuah ____ di dalam buku masak.", "Nakakita si Aya ng ____ sa loob ng aklat sa pagluluto.", "amplop", "sobre"),
        "grammar": ("Mana yang menyatakan tujuan?", "Alin ang nagsasaad ng layunin?",
                    [("Tambahkan jeruk agar harum.", "Dagdagan ng dalandan upang bumango."), ("Kuenya ada di meja.", "Nasa mesa ang keyk."), ("Ayah pergi ke pasar.", "Pumunta sa palengke ang ama.")], 0),
        "construction": ("Aya menyimpan surat nenek.", "Itinabi ni Aya ang liham ng lola."),
    },
    {
        "slug": "isang-araw-na-walang-signal", "level": "INTERMEDIATE", "family": "technology-relationships",
        "category": "Teknologi dan hubungan", "image": "friends",
        "title": ("Sehari Tanpa Sinyal", "Isang Araw na Walang Signal"),
        "summary": ("Gangguan jaringan memaksa sebuah lingkungan menemukan kembali cara berkomunikasi langsung.", "Dahil sa pagkawala ng signal, muling natutong makipag-usap nang harapan ang isang komunidad."),
        "paragraphs": [
            ("Pada Senin pagi, seluruh lingkungan kehilangan sinyal telepon dan internet setelah sebuah tiang rusak diterpa angin.", "Noong Lunes ng umaga, nawalan ng signal sa telepono at internet ang buong barangay matapos masira ng hangin ang isang poste."),
            ("Tomas merasa panik karena rapat kerjanya akan dimulai, sedangkan putrinya tidak dapat mengirim tugas sekolah.", "Nataranta si Tomas dahil magsisimula na ang pulong niya sa trabaho, samantalang hindi maipadala ng anak niya ang takdang-aralin."),
            ("Ia berjalan ke balai barangay untuk mencari kabar dan menemukan banyak orang dengan masalah serupa.", "Naglakad siya papunta sa barangay hall upang maghanap ng balita at nadatnan ang maraming taong may kaparehong problema."),
            ("Ketua lingkungan membuat papan pengumuman: satu sudut untuk pesan penting, satu meja untuk meminjam radio, dan jadwal perjalanan ke kota.", "Gumawa ang kapitan ng pisara: isang sulok para sa mahalagang mensahe, isang mesa para sa hiramang radyo, at talaan ng biyahe papuntang bayan."),
            ("Tomas menulis pesan untuk kantornya, lalu menawarkan sepeda kepada tetangga yang perlu mengambil obat.", "Sumulat si Tomas ng mensahe para sa opisina at ipinahiram ang bisikleta sa kapitbahay na kailangang kumuha ng gamot."),
            ("Anak-anak menyerahkan tugas cetak kepada guru yang berkeliling, kemudian bermain di lapangan tanpa layar.", "Ibinigay ng mga bata ang nakalimbag na takdang-aralin sa gurong umiikot, at pagkatapos ay naglaro sila sa plaza nang walang screen."),
            ("Ketika jaringan kembali pada malam hari, puluhan notifikasi berbunyi bersamaan, tetapi tidak semua orang segera pulang.", "Nang bumalik ang signal kinagabihan, sabay-sabay tumunog ang napakaraming abiso, pero hindi agad umuwi ang lahat."),
            ("Mereka menyelesaikan percakapan di balai dan memutuskan mempertahankan papan pengumuman untuk keadaan darurat berikutnya.", "Tinapos muna nila ang kuwentuhan sa barangay hall at nagpasyang panatilihin ang pisara para sa susunod na emerhensiya."),
        ],
        "vocab": [("barangay", "lingkungan administratif", "pangngalan"), ("poste", "tiang", "pangngalan"), ("nataranta", "panik", "pang-uri"),
                  ("pulong", "rapat", "pangngalan"), ("pisara", "papan pengumuman", "pangngalan"), ("ipinahiram", "dipinjamkan", "pandiwa"),
                  ("abiso", "notifikasi", "pangngalan"), ("emerhensiya", "keadaan darurat", "pangngalan")],
        "notes": [("Samantalang", "Samantalang", "Samantalang membandingkan dua keadaan yang berlangsung bersamaan.", "Inihahambing ng samantalang ang dalawang kalagayang sabay na nangyayari."),
                  ("Nang + peristiwa", "Nang + pangyayari", "Nang dapat membuka peristiwa waktu yang sudah terjadi.", "Ginagamit ang nang sa pagbubukas ng pangyayaring naganap na." )],
        "qa": ("Apa yang diputuskan warga setelah sinyal kembali?", "Ano ang napagpasyahan ng mga tao nang bumalik ang signal?", "Mempertahankan papan pengumuman.", "Panatilihin ang pisara."),
        "fill": ("Ketua lingkungan membuat sebuah ____ untuk pesan penting.", "Gumawa ang kapitan ng ____ para sa mahalagang mensahe.", "papan pengumuman", "pisara"),
        "grammar": ("Kata mana membandingkan dua keadaan bersamaan?", "Aling salita ang naghahambing sa dalawang sabay na kalagayan?",
                    [("sedangkan", "samantalang"), ("karena itu", "kaya"), ("kemarin", "kahapon")], 0),
        "construction": ("Warga mempertahankan papan pengumuman.", "Pinanatili ng mga tao ang pisara."),
    },
    {
        "slug": "ang-bangkang-bumalik", "level": "INTERMEDIATE", "family": "travel-directions",
        "category": "Perjalanan dan arah", "image": "travel",
        "title": ("Perahu yang Kembali", "Ang Bangkang Bumalik"),
        "summary": ("Sebuah kapal penumpang kembali ke pelabuhan ketika cuaca berubah mendadak.", "Bumalik sa daungan ang isang bangkang pampasahero nang biglang magbago ang panahon."),
        "paragraphs": [
            ("Dari pelabuhan, kapal kecil menuju pulau berangkat di bawah langit cerah, membawa pekerja, pedagang, dan beberapa wisatawan.", "Mula sa daungan, umalis ang maliit na bangka papunta sa isla sa ilalim ng maaliwalas na langit, sakay ang mga manggagawa, tindero, at ilang turista."),
            ("Setengah perjalanan kemudian, angin menjadi kuat dan awan gelap menutup pegunungan.", "Sa kalagitnaan ng biyahe, lumakas ang hangin at tinakpan ng madilim na ulap ang kabundukan."),
            ("Kapten mengumumkan bahwa mereka harus kembali, meskipun beberapa penumpang mengeluh tentang jadwal yang tertunda.", "Ipinahayag ng kapitan na kailangan nilang bumalik kahit nagreklamo ang ilang pasahero tungkol sa maaantalang iskedyul."),
            ("Di dekat jendela, seorang anak mulai menangis karena takut pada ombak yang menghantam lambung kapal.", "Malapit sa bintana, umiyak ang isang bata dahil natakot sa mga along humahampas sa tagiliran ng bangka."),
            ("Mara, seorang perawat, duduk di sampingnya dan mengajaknya menghitung jeda di antara gelombang.", "Umupo sa tabi niya si Mara, isang nars, at niyaya siyang bilangin ang pagitan ng bawat alon."),
            ("Perhatian anak itu beralih; ia berhenti menangis dan bahkan memberi tahu ibunya ketika ombak berikutnya datang.", "Nailipat ang pansin ng bata; tumigil siya sa pag-iyak at sinabihan pa ang kaniyang ina kapag paparating ang susunod na alon."),
            ("Kapal tiba kembali dengan selamat tepat sebelum hujan sangat lebat menutupi laut.", "Ligtas na nakabalik ang bangka bago tuluyang tabingan ng napakalakas na ulan ang dagat."),
            ("Para penumpang yang tadi mengeluh berterima kasih kepada kapten, dan perjalanan dilanjutkan keesokan pagi.", "Nagpasalamat sa kapitan ang mga pasaherong nagreklamo kanina, at ipinagpatuloy ang biyahe kinaumagahan."),
        ],
        "vocab": [("daungan", "pelabuhan", "pangngalan"), ("maaliwalas", "cerah", "pang-uri"), ("maaantala", "akan tertunda", "pandiwa"),
                  ("pasahero", "penumpang", "pangngalan"), ("alon", "gelombang", "pangngalan"), ("tagiliran", "lambung atau sisi", "pangngalan"),
                  ("pagitan", "jeda atau antara", "pangngalan"), ("ipinagpatuloy", "dilanjutkan", "pandiwa")],
        "notes": [("Kahit", "Kahit", "Kahit memperkenalkan keadaan yang tidak mengubah keputusan utama.", "Ipinakikilala ng kahit ang kalagayang hindi nakapagpapabago sa pangunahing pasya."),
                  ("Bago", "Bago", "Bago dapat diikuti tindakan yang terjadi sesudah tindakan utama.", "Sinusundan ang bago ng kilos na nangyayari matapos ang pangunahing kilos." )],
        "qa": ("Bagaimana Mara menenangkan anak itu?", "Paano pinakalma ni Mara ang bata?", "Dengan mengajaknya menghitung jeda antarombak.", "Niyaya niya itong bilangin ang pagitan ng mga alon."),
        "fill": ("Kapten memutuskan kembali ke ____.", "Nagpasya ang kapitan na bumalik sa ____.", "pelabuhan", "daungan"),
        "grammar": ("Kata mana memperkenalkan pertentangan yang tidak mengubah keputusan?", "Aling salita ang nagpapakilala ng salungat na kalagayan?",
                    [("meskipun", "kahit"), ("setelah", "pagkatapos"), ("di mana", "kung saan")], 0),
        "construction": ("Kapal kembali ke pelabuhan dengan selamat.", "Ligtas na bumalik sa daungan ang bangka."),
    },
    {
        "slug": "ang-presentasyong-walang-slides", "level": "INTERMEDIATE", "family": "school-work",
        "category": "Sekolah dan pekerjaan", "image": "classroom",
        "title": ("Presentasi Tanpa Slide", "Ang Presentasyong Walang Slides"),
        "summary": ("Pemadaman listrik mengubah presentasi gagal menjadi percakapan yang paling diingat.", "Ginawang di-malilimutang usapan ng brownout ang isang presentasyong muntik nang mabigo."),
        "paragraphs": [
            ("Dina telah menyiapkan presentasi proyek selama dua minggu dan menyimpan semua grafik di laptopnya.", "Dalawang linggong inihanda ni Dina ang presentasyon ng proyekto at nasa laptop ang lahat ng kaniyang grap."),
            ("Beberapa menit sebelum rapat, terjadi pemadaman listrik dan proyektor tidak dapat digunakan.", "Ilang minuto bago ang pulong, nagkaroon ng brownout at hindi magamit ang projector."),
            ("Manajernya menawarkan untuk menjadwalkan ulang, tetapi Dina melihat tiga benda di meja: gelas, batu kecil, dan spons.", "Inalok siya ng tagapamahala na ilipat ang iskedyul, pero nakita ni Dina ang tatlong bagay sa mesa: baso, maliit na bato, at espongha."),
            ("Ia memakai benda-benda itu untuk menjelaskan tiga jenis bahan penyaring air yang sedang diuji timnya.", "Ginamit niya ang mga iyon upang ipaliwanag ang tatlong uri ng pansala ng tubig na sinusubok ng kanilang pangkat."),
            ("Rekan-rekannya mulai mengajukan pertanyaan karena mereka dapat memegang contoh dan membandingkan beratnya.", "Nagsimulang magtanong ang mga kasamahan niya dahil nahahawakan nila ang halimbawa at naihahambing ang bigat."),
            ("Dina menggambar satu tabel sederhana di papan dan mencatat hasil terpenting tanpa membaca naskah.", "Gumuhit si Dina ng payak na talahanayan sa pisara at isinulat ang pinakamahalagang resulta nang hindi binabasa ang iskrip."),
            ("Ketika listrik kembali, tidak ada yang meminta slide; mereka justru membahas langkah uji berikutnya.", "Nang bumalik ang kuryente, walang humingi ng slides; sa halip, tinalakay nila ang susunod na hakbang sa pagsubok."),
            ("Dina tetap menyimpan grafiknya, tetapi sejak hari itu ia selalu menyiapkan cara kedua untuk menjelaskan sebuah gagasan.", "Itinabi pa rin ni Dina ang mga grap, pero mula noon ay lagi na siyang naghahanda ng ikalawang paraan upang ipaliwanag ang isang ideya."),
        ],
        "vocab": [("brownout", "pemadaman listrik", "pangngalan"), ("tagapamahala", "manajer", "pangngalan"), ("pansala", "penyaring", "pangngalan"),
                  ("sinusubok", "sedang diuji", "pandiwa"), ("kasamahan", "rekan", "pangngalan"), ("talahanayan", "tabel", "pangngalan"),
                  ("iskrip", "naskah", "pangngalan"), ("hakbang", "langkah", "pangngalan")],
        "notes": [("Sa halip", "Sa halip", "Sa halip memperkenalkan pilihan pengganti.", "Ipinakikilala ng sa halip ang kapalit na kilos o pasya."),
                  ("Nang hindi", "Nang hindi", "Nang hindi menunjukkan bahwa tindakan dilakukan tanpa tindakan lain.", "Ipinakikita ng nang hindi na ginawa ang kilos na wala ang isa pang kilos." )],
        "qa": ("Apa yang digunakan Dina untuk menggantikan slide?", "Ano ang ginamit ni Dina bilang kapalit ng slides?", "Gelas, batu kecil, spons, dan papan.", "Baso, maliit na bato, espongha, at pisara."),
        "fill": ("Dina menggambar sebuah ____ sederhana di papan.", "Gumuhit si Dina ng payak na ____ sa pisara.", "tabel", "talahanayan"),
        "grammar": ("Ungkapan mana memperkenalkan pilihan pengganti?", "Aling pahayag ang nagpapakilala ng kapalit?",
                    [("justru atau sebagai gantinya", "sa halip"), ("sebelum itu", "bago iyon"), ("di samping", "sa tabi")], 0),
        "construction": ("Dina menjelaskan gagasan tanpa slide.", "Ipinaliwanag ni Dina ang ideya nang walang slides."),
    },
    {
        "slug": "ang-ilaw-sa-lumang-paaralan", "level": "INTERMEDIATE", "family": "gentle-mystery",
        "category": "Misteri ringan", "image": "classroom",
        "title": ("Cahaya di Sekolah Lama", "Ang Ilaw sa Lumang Paaralan"),
        "summary": ("Dua saudara menyelidiki cahaya malam di gedung sekolah yang sudah ditutup.", "Inusisa ng magkapatid ang ilaw sa gabi sa isang lumang gusali ng paaralan."),
        "paragraphs": [
            ("Setiap malam selama tiga hari, Noel melihat cahaya bergerak di lantai dua sekolah lama di seberang rumahnya.", "Tuwing gabi sa loob ng tatlong araw, nakikita ni Noel ang gumagalaw na ilaw sa ikalawang palapag ng lumang paaralan sa tapat ng kanilang bahay."),
            ("Bangunan itu sedang direnovasi dan seharusnya kosong setelah pukul enam.", "Inaayos ang gusali at dapat ay wala nang tao roon pagkalipas ng alas-sais."),
            ("Adiknya, Bea, menduga ada pencuri, sedangkan Noel berpikir seorang pekerja mungkin tertinggal.", "Hinala ni Bea na may magnanakaw, samantalang naisip ni Noel na baka may naiwang manggagawa."),
            ("Mereka tidak masuk sendiri; mereka memanggil penjaga lingkungan dan menunjukkan jendela tempat cahaya muncul.", "Hindi sila pumasok nang sila lamang; tinawag nila ang tanod at itinuro ang bintanang pinagmumulan ng ilaw."),
            ("Penjaga membuka gerbang, lalu mereka mendengar suara gesekan dan kepakan dari ruang sains.", "Binuksan ng tanod ang tarangkahan at narinig nila ang kaluskos at pagaspas mula sa silid-agham."),
            ("Di dalam ruangan, seekor burung hantu kecil terjebak di balik tirai dan membuat lampu sensor menyala setiap kali terbang.", "Sa loob, may munting kuwagong naipit sa likod ng kurtina at napapailaw nito ang sensor tuwing lumilipad."),
            ("Penjaga memakai sarung tangan, membuka jendela lebar-lebar, dan membiarkan burung itu keluar.", "Nagsuot ng guwantes ang tanod, binuksan nang maluwang ang bintana, at pinalabas ang kuwago."),
            ("Malam berikutnya sekolah itu gelap kembali, tetapi Noel dan Bea kini tahu bahwa rasa ingin tahu harus ditemani kehati-hatian.", "Madilim na muli ang paaralan kinabukasan, pero alam na nina Noel at Bea na dapat samahan ng pag-iingat ang pag-uusisa."),
        ],
        "vocab": [("palapag", "lantai bangunan", "pangngalan"), ("hinala", "dugaan", "pangngalan"), ("tanod", "penjaga lingkungan", "pangngalan"),
                  ("tarangkahan", "gerbang", "pangngalan"), ("kaluskos", "suara gesekan", "pangngalan"), ("pagaspas", "kepakan", "pangngalan"),
                  ("kuwago", "burung hantu", "pangngalan"), ("pag-iingat", "kehati-hatian", "pangngalan")],
        "notes": [("Baka", "Baka", "Baka menyatakan kemungkinan, bukan kepastian.", "Ginagamit ang baka sa posibilidad, hindi sa katiyakan."),
                  ("Tuwing", "Tuwing", "Tuwing menunjukkan kejadian berulang setiap waktu tertentu.", "Ipinakikita ng tuwing ang paulit-ulit na pangyayari sa takdang oras." )],
        "qa": ("Apa penyebab cahaya bergerak itu?", "Ano ang sanhi ng gumagalaw na ilaw?", "Burung hantu yang memicu lampu sensor.", "Kuwagong nagpapaandar sa sensor ng ilaw."),
        "fill": ("Noel dan Bea memanggil ____ lingkungan.", "Tinawag nina Noel at Bea ang ____.", "penjaga", "tanod"),
        "grammar": ("Kata mana menyatakan kemungkinan?", "Aling salita ang nagsasaad ng posibilidad?",
                    [("mungkin", "baka"), ("pasti", "tiyak"), ("selalu", "lagi")], 0),
        "construction": ("Penjaga membuka gerbang sekolah.", "Binuksan ng tanod ang tarangkahan ng paaralan."),
    },
    {
        "slug": "ang-huling-basong-tubig", "level": "INTERMEDIATE", "family": "community-environment",
        "category": "Komunitas dan lingkungan", "image": "food",
        "title": ("Segelas Air Terakhir", "Ang Huling Basong Tubig"),
        "summary": ("Kekurangan air mendorong pemilik kedai dan warga berbagi sumber daya dengan lebih adil.", "Dahil sa kakulangan ng tubig, natutong magbahagi nang patas ang may-ari ng kainan at mga residente."),
        "paragraphs": [
            ("Setelah pipa utama pecah, pasokan air di lingkungan Sela dibatasi selama dua hari.", "Matapos masira ang pangunahing tubo, nilimitahan nang dalawang araw ang suplay ng tubig sa barangay ni Sela."),
            ("Kedai kecil miliknya masih memiliki satu tangki, tetapi air itu harus cukup untuk memasak, membersihkan, dan minum.", "May isang tangke pa ang kaniyang maliit na kainan, pero kailangan itong magkasya sa pagluluto, paglilinis, at pag-inom."),
            ("Pada siang hari, seorang kurir meminta segelas air setelah mengayuh sepeda di bawah panas.", "Pagsapit ng tanghali, humingi ng isang basong tubig ang isang mensahero matapos magbisikleta sa matinding init."),
            ("Sela melihat penanda tangki yang hampir kosong dan ragu sejenak sebelum memberinya air minum.", "Tiningnan ni Sela ang panukat ng halos ubos na tangke at sandaling nag-atubili bago siya nagbigay ng maiinom."),
            ("Kurir itu ternyata membawa pemberitahuan bahwa truk air akan datang, tetapi jalan sempit harus dikosongkan.", "May dala pala ang mensahero na abisong darating ang trak ng tubig, pero kailangang alisin ang mga nakaharang sa makitid na daan."),
            ("Sela mengabari tetangga, dan mereka bersama-sama memindahkan motor, meja, serta kotak dagangan.", "Binalitaan ni Sela ang mga kapitbahay at sama-sama nilang inilipat ang motorsiklo, mesa, at mga kahon ng paninda."),
            ("Ketika truk tiba, mereka membuat antrean dan mencatat jumlah wadah agar setiap rumah mendapat bagian.", "Pagdating ng trak, pumila sila at itinala ang dami ng lalagyan upang magkaroon ng bahagi ang bawat bahay."),
            ("Sela menutup kedai lebih awal, namun malam itu semua keluarga mempunyai air karena satu gelas dibagikan pada saat yang tepat.", "Maagang nagsara si Sela, ngunit may tubig ang lahat ng pamilya nang gabing iyon dahil naibahagi ang isang baso sa tamang oras."),
        ],
        "vocab": [("suplay", "pasokan", "pangngalan"), ("tangke", "tangki", "pangngalan"), ("mensahero", "kurir", "pangngalan"),
                  ("panukat", "penanda ukuran", "pangngalan"), ("nag-atubili", "ragu-ragu", "pandiwa"), ("nakaharang", "menghalangi", "pang-uri"),
                  ("lalagyan", "wadah", "pangngalan"), ("naibahagi", "telah dibagikan", "pandiwa")],
        "notes": [("Pala", "Pala", "Pala menandai informasi yang baru disadari pembicara.", "Ginagamit ang pala sa impormasyong ngayon lamang natuklasan."),
                  ("Upang", "Upang", "Upang menghubungkan tindakan dengan tujuannya.", "Pinagdurugtong ng upang ang kilos at layunin nito." )],
        "qa": ("Mengapa jalan sempit harus dikosongkan?", "Bakit kailangang alisin ang mga nakaharang sa makitid na daan?", "Agar truk air dapat lewat.", "Upang makadaan ang trak ng tubig."),
        "fill": ("Air kedai disimpan dalam sebuah ____.", "Nasa isang ____ ang tubig ng kainan.", "tangki", "tangke"),
        "grammar": ("Partikel mana menandai penemuan baru?", "Aling kataga ang nagsasaad ng bagong natuklasan?",
                    [("ternyata", "pala"), ("hanya", "lang"), ("juga", "din")], 0),
        "construction": ("Warga berbagi air dengan adil.", "Patas na nagbahagi ng tubig ang mga tao."),
    },
    {
        "slug": "ang-larawang-hindi-naipadala", "level": "INTERMEDIATE", "family": "family-friendship",
        "category": "Keluarga dan persahabatan", "image": "friends",
        "title": ("Foto yang Tidak Terkirim", "Ang Larawang Hindi Naipadala"),
        "summary": ("Sebuah foto lama yang gagal terkirim mempertemukan kembali dua sahabat.", "Muling pinagtagpo ng isang lumang larawang hindi naipadala ang dalawang magkaibigan."),
        "paragraphs": [
            ("Ketika membersihkan penyimpanan ponsel, Inez menemukan foto pasar malam yang diambil lima tahun lalu bersama sahabatnya, Cora.", "Habang nililinis ang imbakan ng telepono, nakita ni Inez ang larawan sa perya na kinunan limang taon na ang nakaraan kasama ang kaibigang si Cora."),
            ("Di bawah foto itu ada pesan yang tidak pernah terkirim karena nomor Cora sudah berubah.", "Sa ilalim ng larawan ay may mensaheng hindi naipadala dahil nagbago na ang numero ni Cora."),
            ("Mereka dahulu sering berbicara, tetapi setelah pindah kota keduanya menunggu pihak lain menghubungi lebih dulu.", "Madalas silang mag-usap noon, pero matapos lumipat ng lungsod ay kapwa nila hinintay na maunang tumawag ang isa."),
            ("Inez menemukan alamat surel Cora melalui kelompok alumni dan menulis pesan pendek tanpa mencari alasan panjang.", "Nahanap ni Inez ang email ni Cora sa samahan ng mga dating mag-aaral at sumulat siya nang maikli nang walang mahabang dahilan."),
            ("Ia melampirkan foto itu dan bertanya apakah Cora masih menyukai jagung panggang dari pasar malam.", "Isinama niya ang larawan at tinanong kung gusto pa rin ni Cora ang inihaw na mais sa perya."),
            ("Balasan datang pada hari yang sama: Cora tertawa melihat foto itu dan mengaku juga ragu untuk memulai percakapan.", "Dumating ang sagot nang araw ding iyon: natawa si Cora sa larawan at inaming nag-atubili rin siyang magsimula ng usapan."),
            ("Alih-alih bertukar banyak pesan, mereka menetapkan waktu untuk bertemu di kota yang berada di tengah perjalanan mereka.", "Sa halip na magpalitan ng maraming mensahe, nagtakda sila ng pagkikita sa lungsod na nasa gitna ng kanilang biyahe."),
            ("Mereka mengambil foto baru di sebuah kedai jagung, lalu kali ini Inez mengirimkannya sebelum mereka berpisah.", "Kumuha sila ng bagong larawan sa tindahan ng mais, at sa pagkakataong ito ay ipinadala agad iyon ni Inez bago sila naghiwalay."),
        ],
        "vocab": [("imbakan", "penyimpanan", "pangngalan"), ("perya", "pasar malam", "pangngalan"), ("kapwa", "keduanya", "panghalip"),
                  ("samahan", "kelompok atau organisasi", "pangngalan"), ("isinama", "dilampirkan", "pandiwa"), ("inihaw", "dipanggang", "pang-uri"),
                  ("nag-atubili", "ragu", "pandiwa"), ("naghiwalay", "berpisah", "pandiwa")],
        "notes": [("Kapwa", "Kapwa", "Kapwa merujuk pada dua pihak yang mengalami hal yang sama.", "Tumutukoy ang kapwa sa dalawang panig na magkatulad ang karanasan."),
                  ("Sa halip na", "Sa halip na", "Sa halip na memperkenalkan tindakan pengganti sebelum verba.", "Ipinakikilala ng sa halip na ang kapalit na kilos bago ang pandiwa." )],
        "qa": ("Mengapa pesan lama Inez tidak terkirim?", "Bakit hindi naipadala ang lumang mensahe ni Inez?", "Karena nomor Cora sudah berubah.", "Dahil nagbago na ang numero ni Cora."),
        "fill": ("Inez menemukan foto lama dari ____.", "Nakakita si Inez ng lumang larawan mula sa ____.", "pasar malam", "perya"),
        "grammar": ("Ungkapan mana memperkenalkan tindakan pengganti?", "Aling pahayag ang nagpapakilala ng kapalit na kilos?",
                    [("alih-alih", "sa halip na"), ("karena", "dahil"), ("setiap kali", "tuwing")], 0),
        "construction": ("Inez mengirim foto baru itu.", "Ipinadala ni Inez ang bagong larawan."),
    },
    {
        "slug": "ang-orasan-sa-tindahan", "level": "INTERMEDIATE", "family": "daily-life",
        "category": "Kehidupan sehari-hari", "image": "time",
        "title": ("Jam di Toko Reparasi", "Ang Orasan sa Tindahan"),
        "summary": ("Seorang tukang reparasi membantu pelanggan memahami nilai sebuah jam lama.", "Tinulungan ng isang tagapag-ayos ang kostumer na maunawaan ang halaga ng lumang orasan."),
        "paragraphs": [
            ("Arman membawa jam dinding tua ke toko reparasi karena jarumnya berhenti tepat pukul empat lewat dua belas.", "Dinala ni Arman ang lumang orasan sa pagawaan dahil huminto ang mga kamay nito sa alas-kuwatro dose."),
            ("Ia meminta tukang mengganti mesin secepat mungkin sebab apartemennya akan dijual minggu depan.", "Hiniling niyang palitan agad ang makina dahil ibebenta ang kaniyang apartment sa susunod na linggo."),
            ("Tukang bernama Celso membuka bagian belakang dan menemukan secarik kertas terlipat di dekat pegas.", "Binuksan ng tagapag-ayos na si Celso ang likod at nakakita ng nakatiklop na papel malapit sa piyesa."),
            ("Kertas itu berisi tanggal kelahiran Arman serta tulisan ayahnya: ‘Saat inilah rumah kita menjadi lengkap.’", "Nasa papel ang petsa ng kapanganakan ni Arman at sulat ng kaniyang ama: ‘Sa oras na ito nabuo ang ating tahanan.’"),
            ("Arman baru menyadari bahwa jam itu sengaja disetel pada waktu kelahirannya ketika diberikan sebagai hadiah.", "Noon lamang naunawaan ni Arman na sadyang itinakda sa oras ng kaniyang kapanganakan ang orasan nang iregalo ito."),
            ("Celso dapat membuatnya berjalan kembali, tetapi ia menyarankan agar kertas itu disimpan di tempat yang tidak menyentuh mesin.", "Mapaaandar itong muli ni Celso, pero iminungkahi niyang ilagay ang papel sa bahaging hindi sasayad sa makina."),
            ("Arman membatalkan niat menjual jam bersama perabot lama dan memilih membawanya ke rumah baru.", "Hindi na isinama ni Arman ang orasan sa mga lumang kagamitang ibebenta at pinili niya itong dalhin sa bagong bahay."),
            ("Seminggu kemudian, jam itu berdetak lagi, sementara salinan pesan ayahnya tergantung rapi di bawahnya.", "Pagkaraan ng isang linggo, tumitiktak na muli ang orasan habang maayos na nakasabit sa ilalim nito ang kopya ng mensahe ng kaniyang ama."),
        ],
        "vocab": [("orasan", "jam", "pangngalan"), ("pagawaan", "toko reparasi", "pangngalan"), ("nakatiklop", "terlipat", "pang-uri"),
                  ("piyesa", "komponen", "pangngalan"), ("kapanganakan", "kelahiran", "pangngalan"), ("sadyang", "dengan sengaja", "pang-abay"),
                  ("kagamitan", "perabot atau barang", "pangngalan"), ("tumitiktak", "berdetak", "pandiwa")],
        "notes": [("Noon lamang", "Noon lamang", "Noon lamang menekankan bahwa pemahaman baru terjadi pada saat itu.", "Binibigyang-diin ng noon lamang na sa sandaling iyon lang naunawaan ang bagay."),
                  ("Habang", "Habang", "Habang dapat menghubungkan kejadian yang berlangsung bersamaan.", "Pinag-uugnay ng habang ang mga pangyayaring sabay na nagaganap." )],
        "qa": ("Apa isi catatan yang ditemukan di dalam jam?", "Ano ang nilalaman ng talang nakita sa loob ng orasan?", "Waktu kelahiran Arman dan pesan ayahnya.", "Oras ng kapanganakan ni Arman at mensahe ng kaniyang ama."),
        "fill": ("Jam tua itu dibawa ke ____.", "Dinala ang lumang orasan sa ____.", "toko reparasi", "pagawaan"),
        "grammar": ("Ungkapan mana menekankan pemahaman yang baru terjadi?", "Aling pahayag ang nagbibigay-diin sa bagong pagkaunawa?",
                    [("baru pada saat itu", "noon lamang"), ("sejak dahulu", "mula noon"), ("setiap pagi", "tuwing umaga")], 0),
        "construction": ("Jam tua itu berdetak kembali.", "Tumitiktak na muli ang lumang orasan."),
    },
]


def exercise_set(item: dict, story_id: str) -> list[dict]:
    vocab = item["vocab"]
    qa_id, qa_fil, answer_id, answer_fil = item["qa"]
    fill_id, fill_fil, fill_answer_id, fill_answer_fil = item["fill"]
    grammar_id, grammar_fil, grammar_choices, grammar_answer = item["grammar"]
    construction_id, construction_fil = item["construction"]
    choices_id = [entry[1] for entry in vocab[:3]]
    choices_fil = [entry[0] for entry in vocab[:3]]
    return [
        {"id": f"{story_id}-comprehension", "type": "COMPREHENSION", "prompt": localized(qa_id, qa_fil),
         "answer": localized(answer_id, answer_fil), "explanation": localized("Jawabannya dinyatakan dalam cerita.", "Tuwirang binanggit sa kuwento ang sagot."), "speech": {"fil": qa_fil}},
        {"id": f"{story_id}-choice", "type": "MULTIPLE_CHOICE",
         "prompt": localized(f"Apa arti ‘{vocab[0][0]}’?", f"Ano ang kahulugan ng ‘{vocab[0][0]}’ sa Indonesian?"),
         "choices": {"id": choices_id, "fil": choices_fil}, "answer": localized(vocab[0][1], vocab[0][0]),
         "explanation": localized(f"‘{vocab[0][0]}’ berarti ‘{vocab[0][1]}’.", f"Ang katumbas ng ‘{vocab[0][0]}’ ay ‘{vocab[0][1]}’."), "speech": {"fil": vocab[0][0]}},
        {"id": f"{story_id}-vocabulary", "type": "VOCABULARY_TRANSLATION",
         "prompt": localized(f"Ketik arti ‘{vocab[1][0]}’.", f"Isulat ang kahulugan ng ‘{vocab[1][0]}’ sa Indonesian."),
         "answer": localized(vocab[1][1], vocab[1][0]),
         "explanation": localized(f"Jawabannya adalah ‘{vocab[1][1]}’.", f"Ang salitang tinutukoy ay ‘{vocab[1][0]}’."), "speech": {"fil": vocab[1][0]}},
        {"id": f"{story_id}-blank", "type": "FILL_BLANK", "prompt": localized(fill_id, fill_fil),
         "answer": localized(fill_answer_id, fill_answer_fil), "explanation": localized("Kata ini melengkapi peristiwa dalam cerita.", "Kinukumpleto ng salita ang pangyayari sa kuwento."), "speech": {"fil": fill_fil.replace("____", fill_answer_fil)}},
        {"id": f"{story_id}-grammar", "type": "GRAMMAR", "prompt": localized(grammar_id, grammar_fil),
         "choices": {"id": [choice[0] for choice in grammar_choices], "fil": [choice[1] for choice in grammar_choices]},
         "answer": localized(grammar_choices[grammar_answer][0], grammar_choices[grammar_answer][1]),
         "explanation": localized("Pilihan ini memakai bentuk yang sesuai dengan fungsi yang ditanyakan.", "Ginagamit ng sagot ang anyong angkop sa hinihinging tungkulin."), "speech": {"fil": grammar_choices[grammar_answer][1]}},
        {"id": f"{story_id}-construction", "type": "SENTENCE_CONSTRUCTION",
         "prompt": localized("Susun kalimat lengkap.", "Buuin ang kumpletong pangungusap."),
         "tokens": {"id": construction_id.split(), "fil": construction_fil.split()},
         "answer": localized(construction_id, construction_fil),
         "explanation": localized("Urutan ini membentuk kalimat lengkap.", "Ang ayos na ito ay bumubuo ng kumpletong pangungusap."), "speech": {"fil": construction_fil}},
    ]


def build_story(item: dict, order: int) -> dict:
    story_id = f"rolang-story-{order:02d}-{item['slug']}"
    vocabulary = []
    for word, translation, part_of_speech in item["vocab"]:
        vocabulary.append({
            "language": "fil", "word": word, "translations": localized(translation, word),
            "meanings": localized(f"Makna kontekstual dalam cerita: {translation}.", f"Kahulugan sa kuwento: {word}."),
            "pos": part_of_speech, "pronunciation": word,
            "notes": localized("Pelajari kata ini melalui kalimat dalam cerita.", "Pag-aralan ang salita sa pamamagitan ng pangungusap sa kuwento."),
        })
    return {
        "schemaVersion": 1, "id": story_id, "family": item["family"], "category": item["category"],
        "level": item["level"], "order": order, "kind": "STORY", "image": item["image"],
        "title": localized(*item["title"]), "summary": localized(*item["summary"]),
        "objectives": [
            localized("Memahami urutan, masalah, dan penyelesaian cerita.", "Unawain ang pagkakasunod-sunod, suliranin, at wakas ng kuwento."),
            localized("Menggunakan kosakata utama dalam konteks baru.", "Gamitin ang pangunahing bokabularyo sa bagong konteksto."),
            localized("Menjawab pertanyaan pemahaman dan tata bahasa.", "Sagutin ang mga tanong sa pag-unawa at gramatika."),
        ],
        "sentences": [localized(indonesian, tagalog) for indonesian, tagalog in item["paragraphs"]],
        "sentenceCount": len(item["paragraphs"]), "speakers": [None] * len(item["paragraphs"]),
        "notes": [{"title": localized(title_id, title_fil), "text": localized(text_id, text_fil)}
                  for title_id, title_fil, text_id, text_fil in item["notes"]],
        "focus": {"id": [v[1] for v in item["vocab"][:4]], "fil": [v[0] for v in item["vocab"][:4]]},
        "pronunciation": localized("Putar audio per paragraf dan tirukan ritme Tagalog alami.",
                                    "Pakinggan ang bawat talata at gayahin ang natural na ritmo ng Tagalog."),
        "chapters": [
            {"id": "simula", "title": localized("Awal", "Simula"), "sentenceCount": len(item["paragraphs"]) // 2},
            {"id": "wakas", "title": localized("Penyelesaian", "Wakas"), "sentenceCount": len(item["paragraphs"]) - len(item["paragraphs"]) // 2},
        ],
        "exercises": exercise_set(item, story_id), "vocabulary": vocabulary, "assets": [],
    }


def main() -> None:
    COLLECTION.mkdir(parents=True, exist_ok=True)
    references = []
    for order, item in enumerate(STORIES, 1):
        document = build_story(item, order)
        filename = f"{order:02d}-{item['slug']}.json"
        path = COLLECTION / filename
        write_json(path, document)
        references.append({
            "id": document["id"], "family": document["family"], "category": document["category"],
            "level": document["level"], "order": order, "path": f"original-tagalog-stories/{filename}",
            "sha256": sha256(path), "sentenceCount": document["sentenceCount"], "title": document["title"],
            "summary": document["summary"], "objectives": document["objectives"], "image": document["image"], "assets": [],
        })
    audit_path = STORY_ROOT / "source-audit.json"
    if not audit_path.is_file():
        raise SystemExit("Run tools/analyze_story_epub.py before generating the index")
    index = {
        "schemaVersion": 1, "id": "original-tagalog-stories", "languagePair": {"reference": "id", "target": "fil"},
        "title": localized("Cerita Tagalog Orisinal", "Mga Orihinal na Kuwentong Tagalog"),
        "description": localized("Bacaan bertingkat untuk penutur bahasa Indonesia yang belajar Tagalog.",
                                 "Mga babasahing may antas para sa mga Indones na nag-aaral ng Tagalog."),
        "storyCount": len(references), "sourceAudit": {"path": "source-audit.json", "sha256": sha256(audit_path)},
        "stories": references,
    }
    index_path = STORY_ROOT / "index.json"
    write_json(index_path, index)
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stories"] = {"index": "storie/index.json", "sha256": sha256(index_path)}
    write_json(manifest_path, manifest)
    print(f"Generated {len(references)} original stories and updated discovery hashes.")


if __name__ == "__main__":
    main()
