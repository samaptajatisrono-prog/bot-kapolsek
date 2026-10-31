import os
import re
import random
from datetime import datetime, date, timedelta, timezone
import requests
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("POSKO_EMAIL", "").strip()
PASSWORD = os.environ.get("POSKO_PASSWORD", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

DEFAULT_LINK = "https://drive.google.com/file/d/17KmVFmPU-OZk0dBdbVgF7AZ6ayhGWPyl/view?usp=drivesdk"
NAMA_KAPOLSEK = "AKP AGUS SUYANTO, S.H., M.H."
TANGGAL_PATOKAN = date(2026, 10, 29)

# ==========================================================
# LINK FOLDER GOOGLE DRIVE DOKUMENTASI LENGKAP RESMI
# ==========================================================
FOLDER_URLS = {
    # Mingguan QW1 (Ruang Publik Aman)
    "qw1_1": "https://drive.google.com/drive/folders/1XX38ZQyxI0sDaMXJWivwOyE9qnefWYFa",
    "qw1_2": "https://drive.google.com/drive/folders/12CLn8rAEPxckKFVmtov4le3KMXhY0xAb",
    "qw1_3": "https://drive.google.com/drive/folders/184HLRI-mk0DBKL7R5NeOmSB6aVAjKPRF",
    "qw1_4": "https://drive.google.com/drive/folders/19WHhOjuMIQnq8xV2AEprbFyWYHChJiqm",
    "qw1_5": "https://drive.google.com/drive/folders/1h1vPRGgHsla7gkl9yeASMiuR2XwXTC7p",
    "qw1_6": "https://drive.google.com/drive/folders/1iuJbE0UhBq7QGIcAiod6I2mOS8e181r9",
    "qw1_7": "https://drive.google.com/drive/folders/1OjDhQuUbJhOtHaFXXY63sZccmLl_fs_Q",
    "qw1_8": "https://drive.google.com/drive/folders/1FcnVWFZJmzPueHfFCKQitd5RgyXKsH33",
    # Harian QW7 (Polres Kuat, Polsek Tangguh)
    "qw7_1": "https://drive.google.com/drive/folders/10cTeMmc067qHy1TtRXnqS6uQYuYeMO84",
    "qw7_2": "https://drive.google.com/drive/folders/1X-MEjPb1g7uxksdtKyrTQlpui2eCtFMJ",
    "qw7_3": "https://drive.google.com/drive/folders/1RDdRwoFQT_6sM_fuI6lxaHI8HyatKT48",
    "qw7_4": "https://drive.google.com/drive/folders/1VIZ6BCtiGMWIHs7qsT_dr03cUsr3NKJ9",
}

# ==========================================================
# DATA GILIRAN 4 SEKOLAH (SMA/SMK/MA) UNTUK QW1.2 POLIDIK
# ==========================================================
VARIASI_QW1_2_POLIDIK = [
    {
        "sekolah": "SMA NEGERI 1 JATISRONO, Jl. Raya Wonogiri-Ponorogo Km. 26, Watangsono, Jatisrono",
        "koordinat": "(-7.824890, 111.131250)",
        "pertimbangan": "Sekolah menengah atas berada di jalur utama sehingga membutuhkan pembinaan kamtibmas dan tertib berlalu lintas",
        "peserta": "60",
        "materi": "Pencegahan perkelahian pelajar, perundungan (bullying), dan keselamatan berlalu lintas",
    },
    {
        "sekolah": "SMK PANCASILA 2 JATISRONO, Ngrandu, Gunungsari, Jatisrono",
        "koordinat": "(-7.831520, 111.128410)",
        "pertimbangan": "Antisipasi potensi perkelahian pelajar serta pembinaan kedisiplinan siswa SMK di wilayah Jatisrono",
        "peserta": "55",
        "materi": "Pembinaan karakter pelajar, pencegahan tawuran antar pelajar, dan larangan penggunaan knalpot brong",
    },
    {
        "sekolah": "SMK PANCASILA 6 JATISRONO, Jl. Garuda Pancasila, Gunungsari, Jatisrono",
        "koordinat": "(-7.829450, 111.127680)",
        "pertimbangan": "Jumlah siswa yang banyak sehingga perlu edukasi kesadaran hukum dan pencegahan kenakalan remaja",
        "peserta": "50",
        "materi": "Kesadaran hukum kalangan pelajar, pencegahan perkelahian pelajar, dan bijak bermedia sosial",
    },
    {
        "sekolah": "MA AL AMANAH, Sempon, Pandeyan, Jatisrono",
        "koordinat": "(-7.821840, 111.116920)",
        "pertimbangan": "Membekali siswa madrasah dengan wawasan kamtibmas serta pencegahan kenakalan remaja di lingkungan sekolah",
        "peserta": "45",
        "materi": "Edukasi bahaya kenakalan remaja, perkelahian pelajar, narkoba, dan ketertiban umum",
    },
]

VARIASI_QW1_3_POLIRAN = [
    "Pemerintah Desa dan Pelaku UMKM Kecamatan Jatisrono",
    "Karang Taruna dan Kelompok Tani Desa Jatisari Jatisrono",
    "Paguyuban UMKM dan Tokoh Pemuda Desa Gunungsari Jatisrono",
    "Pemerintah Desa Watangrejo dan Komunitas Wirausaha Muda Jatisrono",
]

VARIASI_QW1_4_KUMPUL = [
    {
        "lokasi": "BALAI DESA JATISRONO",
        "koordinat": "(-7.826500, 111.125400)",
        "pertimbangan": "Pusat kegiatan warga untuk menyerap aspirasi dan keluhan kamtibmas secara langsung",
        "komunitas": "Tokoh Masyarakat dan Warga Desa Jatisrono",
    },
    {
        "lokasi": "BALAI DESA GUNUNGSARI JATISRONO",
        "koordinat": "(-7.834120, 111.129800)",
        "pertimbangan": "Mempererat silaturahmi serta menampung saran kamtibmas dari perangkat desa dan warga",
        "komunitas": "Perangkat Desa dan Paguyuban Warga Gunungsari",
    },
    {
        "lokasi": "BALAI DESA JATISARI JATISRONO",
        "koordinat": "(-7.821500, 111.122300)",
        "pertimbangan": "Lokasi strategis pertemuan warga guna menjaga stabilitas keamanan lingkungan desa",
        "komunitas": "Tokoh Agama, Tokoh Masyarakat, dan Warga Desa Jatisari",
    },
    {
        "lokasi": "KAWASAN PASAR JATISRONO",
        "koordinat": "(-7.827393, 111.128544)",
        "pertimbangan": "Titik kumpul aktivitas ekonomi warga yang memerlukan komunikasi aktif terkait pemeliharaan kamtibmas",
        "komunitas": "Paguyuban Pedagang dan Warga Sekitar Pasar Jatisrono",
    },
]

VARIASI_QW1_5_GREEN = [
    {
        "lokasi": "LINGKUNGAN MAPOLSEK JATISRONO",
        "koordinat": "(-7.827400, 111.128500)",
        "pertimbangan": "Penghijauan dan pemeliharaan kebersihan lingkungan pelayanan publik di Mapolsek Jatisrono",
        "pihak": "Anggota Polsek Jatisrono dan Warga Masyarakat Sekitar",
    },
    {
        "lokasi": "SEKITAR LAPANGAN JATISRONO",
        "koordinat": "(-7.826800, 111.127900)",
        "pertimbangan": "Menjaga kebersihan dan keasrian ruang terbuka publik yang sering digunakan masyarakat Jatisrono",
        "pihak": "Personel Polsek Jatisrono, Perangkat Desa, dan Warga",
    },
    {
        "lokasi": "SEKITAR TUGU BINTANG JATISRONO",
        "koordinat": "(-7.827279, 111.128768)",
        "pertimbangan": "Mewujudkan ruang publik yang bersih, sehat, dan asri di pusat keramaian Kecamatan Jatisrono",
        "pihak": "Anggota Polsek Jatisrono dan Relawan Kebersihan Warga",
    },
    {
        "lokasi": "LINGKUNGAN DESA JATISRONO",
        "koordinat": "(-7.826500, 111.125400)",
        "pertimbangan": "Kerja bakti bersama masyarakat guna menjaga kelestarian lingkungan dan mencegah genangan air",
        "pihak": "Polsek Jatisrono, Pemerintah Desa, dan Warga Masyarakat",
    },
]

def kirim_notif_telegram(pesan, foto_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        if foto_path and os.path.exists(foto_path):
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open(foto_path, "rb") as f:
                requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": pesan[:1000]}, files={"photo": f}, timeout=20)
        else:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT_ID, "text": pesan[:4000]}, timeout=20)
    except Exception as e:
        print("Gagal kirim ke Telegram:", e)

def ambil_foto_dari_folder(page, key_folder, mode="harian"):
    folder_url = FOLDER_URLS.get(key_folder, "")
    if not folder_url:
        return DEFAULT_LINK, 1, 1
    folder_id = folder_url.rstrip("/").split("/")[-1].split("?")[0]
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"

    wib_today = datetime.now(timezone(timedelta(hours=7))).date()
    selisih_hari = max(0, (wib_today - TANGGAL_PATOKAN).days)
    indeks_urut = selisih_hari if mode == "harian" else (selisih_hari // 7)

    file_links = []
    try:
        res = requests.get(embed_url, timeout=20)
        ids = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", res.text)
        if not ids:
            ids = re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', res.text)
        seen = set()
        for fid in ids:
            if fid != folder_id and fid not in seen:
                seen.add(fid)
                file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")

        if not file_links:
            page.goto(folder_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            html = page.content()
            ids2 = re.findall(r'data-id="([a-zA-Z0-9_-]{25,})"', html)
            for fid in ids2:
                if fid != folder_id and fid not in seen:
                    seen.add(fid)
                    file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")
    except Exception as e:
        print(f"Gagal scan folder {key_folder}:", e)

    if file_links:
        idx = indeks_urut % len(file_links)
        return file_links[idx], idx + 1, len(file_links)
    return DEFAULT_LINK, 1, 1

def tutup_saran_jika_ada(page):
    try:
        tombol_x = page.locator("button:has-text('×')")
        for i in range(tombol_x.count()):
            if tombol_x.nth(i).is_visible():
                tombol_x.nth(i).click()
                page.wait_for_timeout(500)
    except Exception:
        pass

def buka_tab_dan_kegiatan(page, teks_tab, nama_giat):
    seksi_dua = page.get_by_text("2. PILIH QUICK WINS DAN KEGIATAN").first
    if seksi_dua.is_visible():
        seksi_dua.scroll_into_view_if_needed()

    tab = page.get_by_text(teks_tab).first
    tab.scroll_into_view_if_needed()
    tab.click()
    page.wait_for_timeout(1500)

    giat = page.get_by_text(nama_giat, exact=True).last
    giat.scroll_into_view_if_needed()
    giat.click()
    page.wait_for_timeout(2500)

    try:
        btn_kapolsek = page.get_by_role("button", name="Kapolsek", exact=True).first
        if btn_kapolsek.is_visible():
            btn_kapolsek.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    inp_pejabat = page.get_by_label("Nama dan pangkat pejabat pelaksana")
    inp_pejabat.scroll_into_view_if_needed()
    inp_pejabat.fill(NAMA_KAPOLSEK)
    page.wait_for_timeout(500)

def isi_lokasi_dan_koordinat(page, nama_lokasi, titik_koordinat):
    page.locator("input[placeholder*='Nama tempat']").first.fill(nama_lokasi)
    page.locator("input[placeholder*='Tempel koordinat']").first.fill(titik_koordinat)
    page.wait_for_timeout(500)

def kirim_dan_screenshot(page, kode, nama_giat, link_foto, no_foto, tot_foto, info_tambahan=""):
    tutup_saran_jika_ada(page)

    inputs_drive = page.locator("input[placeholder*='drive.google.com']")
    for i in range(inputs_drive.count()):
        if inputs_drive.nth(i).is_visible():
            inputs_drive.nth(i).fill(link_foto)
    page.wait_for_timeout(1000)

    btn_kirim = page.get_by_role("button", name="Kirim laporan")
    btn_kirim.scroll_into_view_if_needed()
    btn_kirim.click()
    page.wait_for_timeout(5000)

    ss_path = f"bukti_{kode.replace('.', '_')}.png"
    page.screenshot(path=ss_path)
    teks_tambahan = f"{info_tambahan}\n" if info_tambahan else ""
    kirim_notif_telegram(
        f"✅ Laporan Kapolsek {kode} berhasil dikirim!\n\n"
        f"📌 Kegiatan: {nama_giat}\n"
        f"{teks_tambahan}"
        f"👮 Pelapor & Pelaksana: {NAMA_KAPOLSEK}\n"
        f"📸 Foto ke-{no_foto} dari {tot_foto}\n"
        f"🔗 Link: {link_foto}",
        ss_path
    )

def jalankan_robot_kapolsek():
    wib_sekarang = datetime.now(timezone(timedelta(hours=7)))
    hari_ke = wib_sekarang.weekday()  # 0=Senin, 1=Selasa, 2=Rabu, 3=Kamis, 4=Jumat, 5=Sabtu, 6=Minggu
    nama_hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][hari_ke]
    indeks_minggu = max(0, (wib_sekarang.date() - TANGGAL_PATOKAN).days) // 7

    kirim_notif_telegram(
        f"🤖 Robot Kapolsek Jatisrono mulai berjalan...\n"
        f"📅 Hari: {nama_hari}, {wib_sekarang.strftime('%d-%m-%Y')}\n"
        f"👮 Kapolsek: {NAMA_KAPOLSEK}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 412, "height": 915},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        try:
            foto_harian = {
                "qw7_1": ambil_foto_dari_folder(page, "qw7_1", "harian"),
                "qw7_2": ambil_foto_dari_folder(page, "qw7_2", "harian"),
                "qw7_3": ambil_foto_dari_folder(page, "qw7_3", "harian"),
                "qw7_4": ambil_foto_dari_folder(page, "qw7_4", "harian"),
            }
            foto_qw1 = {}
            if hari_ke == 0:
                foto_qw1["qw1_1"] = ambil_foto_dari_folder(page, "qw1_1", "mingguan")
                foto_qw1["qw1_2"] = ambil_foto_dari_folder(page, "qw1_2", "mingguan")
            elif hari_ke == 2:
                foto_qw1["qw1_4"] = ambil_foto_dari_folder(page, "qw1_4", "mingguan")
            elif hari_ke == 3:
                foto_qw1["qw1_3"] = ambil_foto_dari_folder(page, "qw1_3", "mingguan")
            elif hari_ke == 4:
                foto_qw1["qw1_5"] = ambil_foto_dari_folder(page, "qw1_5", "mingguan")
                foto_qw1["qw1_6"] = ambil_foto_dari_folder(page, "qw1_6", "mingguan")
            elif hari_ke == 5:
                foto_qw1["qw1_7"] = ambil_foto_dari_folder(page, "qw1_7", "mingguan")
            elif hari_ke == 6:
                foto_qw1["qw1_8"] = ambil_foto_dari_folder(page, "qw1_8", "mingguan")

            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if page.locator("input[type='password']").count() > 0:
                page.locator("input[type='email'], input[type='text']").first.fill(EMAIL)
                page.locator("input[type='password']").first.fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_timeout(5000)

            # ==========================================================
            # 1. CARA MEMILIH KEGIATAN DAN IDENTITAS LAPORAN
            # ==========================================================
            page.get_by_label("Nama dan pangkat pelapor").fill(NAMA_KAPOLSEK)
            page.locator("select").first.select_option(label="Kapolsek/Wakapolsek (12 kegiatan)")
            page.wait_for_timeout(2000)

            # ==========================================================
            # 2. PILIH QUICK WINS DAN KEGIATAN -> LANGSUNG QW1
            # ==========================================================
            # SENIN: QW1.1 & QW1.2
            if hari_ke == 0:
                # QW1.1 Gatur pagi
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Gatur pagi (pengaturan lalu lintas Senin pagi)")
                isi_lokasi_dan_koordinat(page, "SIMPANG 4 PASAR JATISRONO", "(-7.8273967, 111.1285832)")
                page.get_by_label("Pertimbangan pilihan lokasi").select_option(label="Rawan keramaian")
                page.get_by_label("Cara bertindak di lokasi").select_option(label="Gatur")
                page.get_by_label("Jumlah lokasi gatur pagi").select_option(label="3")
                link, no, tot = foto_qw1["qw1_1"]
                kirim_dan_screenshot(page, "QW1.1", "Gatur pagi (pengaturan lalu lintas Senin pagi)", link, no, tot)

                # QW1.2 Polisi peduli pendidikan (Polidik) - Digilir Berurutan 4 Sekolah SMA/SMK/MA
                paket_polidik = VARIASI_QW1_2_POLIDIK[indeks_minggu % len(VARIASI_QW1_2_POLIDIK)]
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Polisi peduli pendidikan (Polidik)")
                isi_lokasi_dan_koordinat(page, paket_polidik["sekolah"], paket_polidik["koordinat"])
                page.locator("textarea[placeholder*='Alasan lokasi dipilih']").first.fill(paket_polidik["pertimbangan"])
                page.get_by_role("button", name="Penyuluhan", exact=True).click()
                page.locator("input[type='number']").first.fill(paket_polidik["peserta"])
                try:
                    page.locator("textarea[placeholder*='Tema pekan ini']").first.fill(paket_polidik["materi"])
                except Exception:
                    pass
                link, no, tot = foto_qw1["qw1_2"]
                kirim_dan_screenshot(
                    page, "QW1.2", "Polisi peduli pendidikan (Polidik)", link, no, tot,
                    f"🏫 Sekolah: {paket_polidik['sekolah']}\n📍 Koordinat: {paket_polidik['koordinat']}"
                )

            # RABU: QW1.4 Kumpul bersama masyarakat - Digilir Berurutan
            elif hari_ke == 2:
                paket_kumpul = VARIASI_QW1_4_KUMPUL[indeks_minggu % len(VARIASI_QW1_4_KUMPUL)]
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Kumpul bersama masyarakat")
                isi_lokasi_dan_koordinat(page, paket_kumpul["lokasi"], paket_kumpul["koordinat"])
                page.locator("textarea[placeholder*='Alasan lokasi dipilih']").first.fill(paket_kumpul["pertimbangan"])
                try:
                    page.get_by_label("Komunitas atau paguyuban yang ditemui").fill(paket_kumpul["komunitas"])
                except Exception:
                    page.locator("xpath=//*[contains(text(), 'Komunitas atau paguyuban')]/following::input[1]").fill(paket_kumpul["komunitas"])
                link, no, tot = foto_qw1["qw1_4"]
                kirim_dan_screenshot(
                    page, "QW1.4", "Kumpul bersama masyarakat", link, no, tot,
                    f"📍 Lokasi: {paket_kumpul['lokasi']}\n👥 Komunitas: {paket_kumpul['komunitas']}"
                )

            # KAMIS: QW1.3 Polisi peduli pengangguran (Poliran) - Digilir Berurutan
            elif hari_ke == 3:
                mitra_pilihan = VARIASI_QW1_3_POLIRAN[indeks_minggu % len(VARIASI_QW1_3_POLIRAN)]
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Polisi peduli pengangguran (Poliran)")
                page.get_by_role("button", name="Merekrut (pemetaan dan pendataan warga usia produktif)").click()
                page.locator("select").nth(1).select_option(label="Rapat dengan mitra")
                page.locator("input[placeholder*='Nama mitra']").first.fill(mitra_pilihan)
                link, no, tot = foto_qw1["qw1_3"]
                kirim_dan_screenshot(
                    page, "QW1.3", "Polisi peduli pengangguran (Poliran)", link, no, tot,
                    f"🤝 Mitra: {mitra_pilihan}"
                )

            # JUMAT: QW1.5 & QW1.6
            elif hari_ke == 4:
                # QW1.5 Green policing - Digilir Berurutan
                paket_green = VARIASI_QW1_5_GREEN[indeks_minggu % len(VARIASI_QW1_5_GREEN)]
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Green policing")
                isi_lokasi_dan_koordinat(page, paket_green["lokasi"], paket_green["koordinat"])
                page.locator("textarea[placeholder*='Alasan lokasi dipilih']").first.fill(paket_green["pertimbangan"])
                page.get_by_role("button", name="Kerja bakti kebersihan", exact=True).click()
                page.locator("input[placeholder*='Warga, Pemda']").first.fill(paket_green["pihak"])
                link, no, tot = foto_qw1["qw1_5"]
                kirim_dan_screenshot(
                    page, "QW1.5", "Green policing", link, no, tot,
                    f"🌱 Lokasi: {paket_green['lokasi']} {paket_green['koordinat']}"
                )

                # QW1.6 Jumat keliling (Jumling)
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Jumat keliling (Jumling)")
                isi_lokasi_dan_koordinat(page, "MASJID NURUL HUDA", "(-7.8260946, 111.1280397)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Masjid besar di Jatisrono dengan jamaah ramai")
                page.get_by_label("Peran").select_option(label="Jamaah")
                link, no, tot = foto_qw1["qw1_6"]
                kirim_dan_screenshot(page, "QW1.6", "Jumat keliling (Jumling)", link, no, tot)

            # SABTU: QW1.7 Subuh keliling (Suling)
            elif hari_ke == 5:
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Subuh keliling (Suling)")
                isi_lokasi_dan_koordinat(page, "MASJID NURUL HUDA", "(-7.8260946, 111.1280397)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Masjid utama di pinggir jalan raya yang membutuhkan kehadiran Polri")
                page.get_by_label("Peran").select_option(label="Jamaah")
                link, no, tot = foto_qw1["qw1_7"]
                kirim_dan_screenshot(page, "QW1.7", "Subuh keliling (Suling)", link, no, tot)

            # MINGGU: QW1.8 Minggu kasih
            elif hari_ke == 6:
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Minggu kasih")
                isi_lokasi_dan_koordinat(page, "GEREJA SANTA MARIA JATISRONO", "(-7.829100, 111.130200)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Memberikan rasa aman dan nyaman kepada jemaat saat ibadah berlangsung")
                page.get_by_label("Peran").fill("Pengamanan dan dialog kamtibmas bersama jemaat")
                link, no, tot = foto_qw1["qw1_8"]
                kirim_dan_screenshot(page, "QW1.8", "Minggu kasih", link, no, tot)

            # ==========================================================
            # 3. LANJUT KEGIATAN HARIAN QW7.1 s/d QW7.4 (SETIAP HARI)
            # ==========================================================
            # QW7.1 Satu desa satu Bhabinkamtibmas
            buka_tab_dan_kegiatan(page, "Polres Kuat, Polsek Tangguh", "Satu desa satu Bhabinkamtibmas")
            nums71 = page.locator("input[type='number']")
            if nums71.count() >= 2:
                nums71.nth(0).fill("17")
                nums71.nth(1).fill("17")
            page.get_by_label("Upaya pemenuhan satu Bhabinkamtibmas satu desa").fill("Upaya pemenuhan dilaporkan kepada pimpinan secara berkala")
            page.get_by_role("button", name="Ya", exact=True).first.click()
            link, no, tot = foto_harian["qw7_1"]
            kirim_dan_screenshot(page, "QW7.1", "Satu desa satu Bhabinkamtibmas", link, no, tot)

            # QW7.2 Penataan personel
            buka_tab_dan_kegiatan(page, "Polres Kuat, Polsek Tangguh", "Penataan personel")
            page.locator("input[type='number']").first.fill("0")
            link, no, tot = foto_harian["qw7_2"]
            kirim_dan_screenshot(page, "QW7.2", "Penataan personel", link, no, tot)

            # QW7.3 Polsek siaga 24 jam
            buka_tab_dan_kegiatan(page, "Polres Kuat, Polsek Tangguh", "Polsek siaga 24 jam")
            nums73 = page.locator("input[type='number']")
            if nums73.count() >= 2:
                nums73.nth(0).fill("0")
                nums73.nth(1).fill("4")
            page.get_by_role("button", name="Ya", exact=True).first.click()
            link, no, tot = foto_harian["qw7_3"]
            kirim_dan_screenshot(page, "QW7.3", "Polsek siaga 24 jam", link, no, tot)

            # QW7.4 Perkara ringan dan rembuk warga
            buka_tab_dan_kegiatan(page, "Polres Kuat, Polsek Tangguh", "Perkara ringan dan rembuk warga")
            nums74 = page.locator("input[type='number']")
            if nums74.count() >= 2:
                nums74.nth(0).fill("0")
                nums74.nth(1).fill("0")
            link, no, tot = foto_harian["qw7_4"]
            kirim_dan_screenshot(page, "QW7.4", "Perkara ringan dan rembuk warga", link, no, tot)

        except Exception as e:
            err_ss = "error_kapolsek.png"
            try:
                page.screenshot(path=err_ss)
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan Kapolsek:\n{str(e)}", err_ss)
            except Exception:
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan Kapolsek:\n{str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    jalankan_robot_kapolsek()
