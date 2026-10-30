import os
import re
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
# LINK FOLDER GOOGLE DRIVE DOKUMENTASI
# ==========================================================
FOLDER_URLS = {
    # Mingguan QW1 (Ruang Publik Aman)
    "qw1_1": "https://drive.google.com/drive/folders/1XX38ZQyxI0sDaMXJWivwOyE9qnefWYFa",
    "qw1_2": "https://drive.google.com/drive/folders/10cTeMmc067qHy1TtRXnqS6uQYuYeMO84",
    "qw1_3": "https://drive.google.com/drive/folders/1X-MEjPb1g7uxksdtKyrTQlpui2eCtFMJ",
    "qw1_4": "https://drive.google.com/drive/folders/1RDdRwoFQT_6sM_fuI6lxaHI8HyatKT48",
    "qw1_5": "https://drive.google.com/drive/folders/1VIZ6BCtiGMWIHs7qsT_dr03cUsr3NKJ9",
    "qw1_6": "https://drive.google.com/drive/folders/1iuJbE0UhBq7QGIcAiod6I2mOS8e181r9",
    "qw1_7": "https://drive.google.com/drive/folders/1OjDhQuUbJhOtHaFXXY63sZccmLl_fs_Q",
    "qw1_8": "https://drive.google.com/drive/folders/1FcnVWFZJmzPueHfFCKQitd5RgyXKsH33",
    # Harian QW7 (Polres Kuat, Polsek Tangguh)
    "qw7_1": "https://drive.google.com/drive/folders/10cTeMmc067qHy1TtRXnqS6uQYuYeMO84",
    "qw7_2": "https://drive.google.com/drive/folders/1X-MEjPb1g7uxksdtKyrTQlpui2eCtFMJ",
    "qw7_3": "https://drive.google.com/drive/folders/1RDdRwoFQT_6sM_fuI6lxaHI8HyatKT48",
    "qw7_4": "https://drive.google.com/drive/folders/1VIZ6BCtiGMWIHs7qsT_dr03cUsr3NKJ9",
}

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
    # Langsung menuju bagian 2. PILIH QUICK WINS DAN KEGIATAN
    seksi_dua = page.get_by_text("2. PILIH QUICK WINS DAN KEGIATAN").first
    if seksi_dua.is_visible():
        seksi_dua.scroll_into_view_if_needed()

    # Klik tab Quick Wins (Ruang Publik Aman / Polres Kuat, Polsek Tangguh)
    tab = page.get_by_text(teks_tab).first
    tab.scroll_into_view_if_needed()
    tab.click()
    page.wait_for_timeout(1500)

    # Klik tombol kegiatan di bagian 2 (menggunakan .last agar melewati kotak pengingat di atas)
    giat = page.get_by_text(nama_giat, exact=True).last
    giat.scroll_into_view_if_needed()
    giat.click()
    page.wait_for_timeout(2500)

    # Pastikan tombol Pelaksana 'Kapolsek' diklik
    try:
        btn_kapolsek = page.get_by_role("button", name="Kapolsek", exact=True).first
        if btn_kapolsek.is_visible():
            btn_kapolsek.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    # Isi Nama dan pangkat pejabat pelaksana
    inp_pejabat = page.get_by_label("Nama dan pangkat pejabat pelaksana")
    inp_pejabat.scroll_into_view_if_needed()
    inp_pejabat.fill(NAMA_KAPOLSEK)
    page.wait_for_timeout(500)

def isi_lokasi_dan_koordinat(page, nama_lokasi, titik_koordinat):
    page.locator("input[placeholder*='Nama tempat']").first.fill(nama_lokasi)
    page.locator("input[placeholder*='Tempel koordinat']").first.fill(titik_koordinat)
    page.wait_for_timeout(500)

def kirim_dan_screenshot(page, kode, nama_giat, link_foto, no_foto, tot_foto):
    tutup_saran_jika_ada(page)

    # Isi semua kolom link Google Drive yang tampil di form
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
    kirim_notif_telegram(
        f"✅ Laporan Kapolsek {kode} berhasil dikirim!\n\n"
        f"📌 Kegiatan: {nama_giat}\n"
        f"👮 Pelapor & Pelaksana: {NAMA_KAPOLSEK}\n"
        f"📸 Foto ke-{no_foto} dari {tot_foto}\n"
        f"🔗 Link: {link_foto}",
        ss_path
    )

def jalankan_robot_kapolsek():
    wib_sekarang = datetime.now(timezone(timedelta(hours=7)))
    hari_ke = wib_sekarang.weekday()  # 0=Senin, 1=Selasa, 2=Rabu, 3=Kamis, 4=Jumat, 5=Sabtu, 6=Minggu
    nama_hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][hari_ke]

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
            # Siapkan link foto harian QW7 dan mingguan QW1 sebelum membuka web Posko PBM
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

            # Buka website Posko PBM
            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Login jika diminta
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
            # 2. PILIH QUICK WINS DAN KEGIATAN -> LANGSUNG QW1 SESUAI JADWAL
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

                # QW1.2 Polisi peduli pendidikan (Polidik)
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Polisi peduli pendidikan (Polidik)")
                isi_lokasi_dan_koordinat(page, "SMP NEGERI 1 JATISRONO", "(-7.828105, 111.127891)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Sekolah berada di jalur utama dan membutuhkan pembinaan kamtibmas pelajar")
                page.get_by_role("button", name="Penyuluhan", exact=True).click()
                page.locator("input[type='number']").first.fill("50")
                page.get_by_label("Materi").fill("Pencegahan perkelahian pelajar dan tertib berlalu lintas")
                link, no, tot = foto_qw1["qw1_2"]
                kirim_dan_screenshot(page, "QW1.2", "Polisi peduli pendidikan (Polidik)", link, no, tot)

            # RABU: QW1.4 Kumpul bersama masyarakat
            elif hari_ke == 2:
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Kumpul bersama masyarakat")
                isi_lokasi_dan_koordinat(page, "BALAI DESA JATISRONO", "(-7.826500, 111.125400)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Pusat kegiatan warga untuk menyerap aspirasi dan keluhan kamtibmas")
                page.get_by_label("Komunitas atau paguyuban yang ditemui").fill("Tokoh Masyarakat dan Warga Desa Jatisrono")
                link, no, tot = foto_qw1["qw1_4"]
                kirim_dan_screenshot(page, "QW1.4", "Kumpul bersama masyarakat", link, no, tot)

            # KAMIS: QW1.3 Polisi peduli pengangguran (Poliran)
            elif hari_ke == 3:
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Polisi peduli pengangguran (Poliran)")
                page.get_by_role("button", name="Merekrut (pemetaan dan pendataan warga usia produktif)").click()
                page.get_by_label("Jalin kemitraan").select_option(label="Rapat dengan mitra")
                page.get_by_label("Pihak kerja sama").fill("Pemerintah Desa dan UMKM Kecamatan Jatisrono")
                link, no, tot = foto_qw1["qw1_3"]
                kirim_dan_screenshot(page, "QW1.3", "Polisi peduli pengangguran (Poliran)", link, no, tot)

            # JUMAT: QW1.5 & QW1.6
            elif hari_ke == 4:
                # QW1.5 Green policing
                buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Green policing")
                isi_lokasi_dan_koordinat(page, "LINGKUNGAN MAPOLSEK JATISRONO", "(-7.827400, 111.128500)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Penghijauan dan pemeliharaan lingkungan asri di wilayah Polsek Jatisrono")
                page.get_by_role("button", name="Kerja bakti kebersihan", exact=True).click()
                page.get_by_label("Pihak yang terlibat").fill("Anggota Polsek Jatisrono dan Warga Masyarakat")
                link, no, tot = foto_qw1["qw1_5"]
                kirim_dan_screenshot(page, "QW1.5", "Green policing", link, no, tot)

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
