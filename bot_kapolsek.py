import os
import re
import random
from datetime import datetime, timedelta, timezone
import requests
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("POSKO_EMAIL", "").strip()
PASSWORD = os.environ.get("POSKO_PASSWORD", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

NAMA_PELAPOR = "AKP AGUS SUYANTO, S.H., M.H."

# ==========================================================
# LINK FOLDER GOOGLE DRIVE STOK FOTO DOKUMENTASI
# ==========================================================
FOLDER_URLS = {
    # Harian QW7
    "qw7_1": "https://drive.google.com/drive/folders/10cTeMmc067qHy1TtRXnqS6uQYuYeMO84",
    "qw7_2": "https://drive.google.com/drive/folders/1X-MEjPb1g7uxksdtKyrTQlpui2eCtFMJ",
    "qw7_3": "https://drive.google.com/drive/folders/1RDdRwoFQT_6sM_fuI6lxaHI8HyatKT48",
    "qw7_4": "https://drive.google.com/drive/folders/1VIZ6BCtiGMWIHs7qsT_dr03cUsr3NKJ9",
    # Mingguan QW1
    "qw1_1": "https://drive.google.com/drive/folders/1XX38ZQyxI0sDaMXJWivwOyE9qnefWYFa",
    "qw1_2": "https://drive.google.com/drive/folders/10cTeMmc067qHy1TtRXnqS6uQYuYeMO84",
    "qw1_3": "https://drive.google.com/drive/folders/1X-MEjPb1g7uxksdtKyrTQlpui2eCtFMJ",
    "qw1_4": "https://drive.google.com/drive/folders/1RDdRwoFQT_6sM_fuI6lxaHI8HyatKT48",
    "qw1_5": "https://drive.google.com/drive/folders/1VIZ6BCtiGMWIHs7qsT_dr03cUsr3NKJ9",
    "qw1_6": "https://drive.google.com/drive/folders/1iuJbE0UhBq7QGIcAiod6I2mOS8e181r9",
    "qw1_7": "https://drive.google.com/drive/folders/1OjDhQuUbJhOtHaFXXY63sZccmLl_fs_Q",
    "qw1_8": "https://drive.google.com/drive/folders/1FcnVWFZJmzPueHfFCKQitd5RgyXKsH33",
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
        print("Gagal kirim notif:", e)

def ambil_foto_drive(key_folder):
    folder_url = FOLDER_URLS.get(key_folder, "")
    if not folder_url:
        return "https://drive.google.com", 1, 1
    folder_id = folder_url.rstrip("/").split("/")[-1].split("?")[0]
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    
    wib_now = datetime.now(timezone(timedelta(hours=7)))
    hari_ini = wib_now.day
    
    file_links = []
    try:
        res = requests.get(embed_url, timeout=15)
        ids = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", res.text)
        if not ids:
            ids = re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', res.text)
        seen = set()
        for fid in ids:
            if fid != folder_id and fid not in seen:
                seen.add(fid)
                file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")
    except Exception as e:
        print(f"Gagal scan folder {key_folder}:", e)
        
    if file_links:
        idx = hari_ini % len(file_links)
        return file_links[idx], idx + 1, len(file_links)
    return folder_url, 1, 1

def tutup_saran_jika_ada(page):
    try:
        # Menghapus kotak saran default dengan menekan tanda '×' pada Saran 1
        btn_close = page.locator("button:has-text('×'), [aria-label='Close'], button.delete-btn").first
        if btn_close.is_visible(timeout=1500):
            btn_close.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

def buka_kegiatan_qw1(page, teks_giat):
    # 1. Pastikan tab QW1 Ruang Publik Aman terpilih
    tab_qw1 = page.locator("button, div").filter(has_text=re.compile(r"QW1\s+Ruang\s+Publik\s+Aman", re.I)).last
    tab_qw1.scroll_into_view_if_needed()
    tab_qw1.click()
    page.wait_for_timeout(2000)

    # 2. Klik kegiatan di daftar bawah
    item_giat = page.locator("div, button").filter(has_text=re.compile(teks_giat, re.I)).last
    item_giat.scroll_into_view_if_needed()
    item_giat.click()
    page.wait_for_timeout(3000)

    # 3. Pastikan pelaksana 'Kapolsek' terpilih dan isi nama pejabat pelaksana
    btn_kapolsek = page.locator("button:has-text('Kapolsek')").first
    if btn_kapolsek.is_visible():
        btn_kapolsek.click()
        page.wait_for_timeout(500)

    input_pejabat = page.locator("input[placeholder*='AKBP Budi Santoso'], input[placeholder*='pejabat pelaksana']").first
    if input_pejabat.is_visible():
        input_pejabat.fill(NAMA_PELAPOR)
        page.wait_for_timeout(500)

def submit_laporan(page, kode_giat, nama_giat, link_foto, no_foto, tot_foto):
    tutup_saran_jika_ada(page)
    
    # Isi link Google Drive
    input_drive = page.locator("input[placeholder*='drive.google.com']").first
    input_drive.scroll_into_view_if_needed()
    input_drive.fill(link_foto)
    page.wait_for_timeout(1000)

    # Klik tombol Kirim Laporan
    btn_kirim = page.locator("button:has-text('Kirim laporan')").last
    btn_kirim.scroll_into_view_if_needed()
    btn_kirim.click()
    page.wait_for_timeout(5000)

    nama_ss = f"bukti_{kode_giat}.png"
    page.screenshot(path=nama_ss)
    kirim_notif_telegram(
        f"✅ Laporan Kapolsek {kode_giat} berhasil dikirim!\n\n"
        f"📌 Kegiatan: {nama_giat}\n"
        f"👮 Pelapor: {NAMA_PELAPOR}\n"
        f"📸 Foto ke-{no_foto} dari {tot_foto}\n"
        f"🔗 Link: {link_foto}",
        nama_ss
    )

def isi_qw7_harian(page):
    # QW7.1 Satu desa satu Bhabinkamtibmas
    page.locator("button, div").filter(has_text=re.compile(r"QW7\s+Polres\s+Kuat", re.I)).last.click()
    page.wait_for_timeout(1500)
    page.locator("div, button").filter(has_text=re.compile(r"QW7\.1", re.I)).last.click()
    page.wait_for_timeout(2000)
    page.locator("input[placeholder*='pejabat pelaksana'], input[placeholder*='AKBP']").first.fill(NAMA_PELAPOR)
    nums = page.locator("input[type='number']")
    if nums.count() >= 2:
        nums.nth(0).fill("17")
        nums.nth(1).fill("17")
    page.locator("textarea").first.fill("Upaya pemenuhan dilaporkan kepada pimpinan secara berkala")
    page.locator("button:has-text('Ya')").first.click()
    link, no, tot = ambil_foto_drive("qw7_1")
    submit_laporan(page, "QW7.1", "Satu desa satu Bhabinkamtibmas", link, no, tot)

    # QW7.2 Penataan personel
    page.locator("button, div").filter(has_text=re.compile(r"QW7\s+Polres\s+Kuat", re.I)).last.click()
    page.wait_for_timeout(1500)
    page.locator("div, button").filter(has_text=re.compile(r"QW7\.2", re.I)).last.click()
    page.wait_for_timeout(2000)
    page.locator("input[placeholder*='pejabat pelaksana'], input[placeholder*='AKBP']").first.fill(NAMA_PELAPOR)
    num72 = page.locator("input[type='number']").first
    if num72.is_visible():
        num72.fill("0")
    link, no, tot = ambil_foto_drive("qw7_2")
    submit_laporan(page, "QW7.2", "Penataan personel", link, no, tot)

    # QW7.3 Polsek siaga 24 jam
    page.locator("button, div").filter(has_text=re.compile(r"QW7\s+Polres\s+Kuat", re.I)).last.click()
    page.wait_for_timeout(1500)
    page.locator("div, button").filter(has_text=re.compile(r"QW7\.3", re.I)).last.click()
    page.wait_for_timeout(2000)
    page.locator("input[placeholder*='pejabat pelaksana'], input[placeholder*='AKBP']").first.fill(NAMA_PELAPOR)
    nums73 = page.locator("input[type='number']")
    if nums73.count() >= 2:
        nums73.nth(0).fill("0")
        nums73.nth(1).fill("4")
    page.locator("button:has-text('Ya')").first.click()
    link, no, tot = ambil_foto_drive("qw7_3")
    submit_laporan(page, "QW7.3", "Polsek siaga 24 jam", link, no, tot)

    # QW7.4 Perkara ringan dan rembuk warga
    page.locator("button, div").filter(has_text=re.compile(r"QW7\s+Polres\s+Kuat", re.I)).last.click()
    page.wait_for_timeout(1500)
    page.locator("div, button").filter(has_text=re.compile(r"QW7\.4", re.I)).last.click()
    page.wait_for_timeout(2000)
    page.locator("input[placeholder*='pejabat pelaksana'], input[placeholder*='AKBP']").first.fill(NAMA_PELAPOR)
    nums74 = page.locator("input[type='number']")
    if nums74.count() >= 2:
        nums74.nth(0).fill("0")
        nums74.nth(1).fill("0")
    link, no, tot = ambil_foto_drive("qw7_4")
    submit_laporan(page, "QW7.4", "Perkara ringan dan rembuk warga", link, no, tot)

def jalankan_robot_kapolsek():
    wib_sekarang = datetime.now(timezone(timedelta(hours=7)))
    hari_ke = wib_sekarang.weekday()  # 0=Senin, 1=Selasa, 2=Rabu, 3=Kamis, 4=Jumat, 5=Sabtu, 6=Minggu
    nama_hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][hari_ke]

    kirim_notif_telegram(f"🤖 Memulai Bot Kapolsek Posko PBM...\n📅 Hari: {nama_hari}, {wib_sekarang.strftime('%d-%m-%Y')}\n👮 Pelapor: {NAMA_PELAPOR}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(viewport={"width": 412, "height": 915}, ignore_https_errors=True)
        page = context.new_page()

        try:
            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Login jika diminta
            if page.locator("input[type='password']").count() > 0:
                page.locator("input[type='email'], input[type='text']").first.fill(EMAIL)
                page.locator("input[type='password']").first.fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_timeout(5000)

            # Pilih Jabatan Kapolsek / Wakapolsek
            page.locator("input[placeholder*='Nama dan pangkat pelapor']").fill(NAMA_PELAPOR)
            page.locator("select").first.select_option(label="Kapolsek/Wakapolsek (12 kegiatan)")
            page.wait_for_timeout(2000)

            # ----------------------------------------------------
            # 1. JALANKAN KEGIATAN MINGGUAN QW1 SESUAI HARI
            # ----------------------------------------------------
            # SENIN: QW1.1 & QW1.2
            if hari_ke == 0:
                # QW1.1 Gatur Pagi
                buka_kegiatan_qw1(page, "QW1.1")
                in_loc = page.locator("xpath=//*[contains(text(), 'Nama lokasi')]/following::input")
                in_loc.nth(0).fill("SIMPANG 4 PASAR JATISRONO")
                in_loc.nth(1).fill("(-7.8273967, 111.1285832)")
                page.locator("select").nth(1).select_option(label="Rawan keramaian")
                page.locator("select").nth(2).select_option(label="Gatur")
                page.locator("select").nth(3).select_option(label="3")
                link, no, tot = ambil_foto_drive("qw1_1")
                submit_laporan(page, "QW1.1", "Gatur pagi", link, no, tot)

                # QW1.2 Polisi Peduli Pendidikan (Polidik)
                buka_kegiatan_qw1(page, "QW1.2")
                in_sek = page.locator("xpath=//*[contains(text(), 'Nama sekolah')]/following::input")
                in_sek.nth(0).fill("SMP NEGERI 1 JATISRONO")
                in_sek.nth(1).fill("(-7.828105, 111.127891)")
                page.locator("textarea").first.fill("Sekolah berada di jalur utama dan membutuhkan pembinaan kamtibmas pelajar")
                page.locator("button:has-text('Penyuluhan')").first.click()
                page.locator("input[type='number']").first.fill("50")
                link, no, tot = ambil_foto_drive("qw1_2")
                submit_laporan(page, "QW1.2", "Polisi peduli pendidikan", link, no, tot)

            # RABU: QW1.4 Kumpul Bersama Masyarakat
            elif hari_ke == 2:
                buka_kegiatan_qw1(page, "QW1.4")
                in_km = page.locator("xpath=//*[contains(text(), 'Nama lokasi kumpul')]/following::input")
                in_km.nth(0).fill("BALAI DESA JATISRONO")
                in_km.nth(1).fill("(-7.826500, 111.125400)")
                page.locator("textarea").first.fill("Pusat kegiatan warga untuk menyerap aspirasi dan keluhan kamtibmas")
                page.locator("xpath=//*[contains(text(), 'Komunitas')]/following::input[1]").fill("Tokoh Masyarakat dan Warga Desa Jatisrono")
                link, no, tot = ambil_foto_drive("qw1_4")
                submit_laporan(page, "QW1.4", "Kumpul bersama masyarakat", link, no, tot)

            # KAMIS: QW1.3 Polisi Peduli Pengangguran (Poliran)
            elif hari_ke == 3:
                buka_kegiatan_qw1(page, "QW1.3")
                page.locator("button:has-text('Merekrut')").first.click()
                page.locator("select").first.select_option(label="Rapat dengan mitra")
                page.locator("xpath=//*[contains(text(), 'Pihak kerja sama')]/following::input[1]").fill("Balai Latihan Kerja & Tokoh Pemuda Jatisrono")
                link, no, tot = ambil_foto_drive("qw1_3")
                submit_laporan(page, "QW1.3", "Polisi peduli pengangguran", link, no, tot)

            # JUMAT: QW1.5 & QW1.6
            elif hari_ke == 4:
                # QW1.5 Green Policing
                buka_kegiatan_qw1(page, "QW1.5")
                in_gp = page.locator("xpath=//*[contains(text(), 'Nama lokasi')]/following::input")
                in_gp.nth(0).fill("LINGKUNGAN MAPOLSEK JATISRONO")
                in_gp.nth(1).fill("(-7.827400, 111.128500)")
                page.locator("textarea").first.fill("Penghijauan dan pemeliharaan lingkungan asri di wilayah Polsek")
                page.locator("button:has-text('Kerja bakti kebersihan')").first.click()
                page.locator("xpath=//*[contains(text(), 'Pihak yang terlibat')]/following::input[1]").fill("Warga sekitar dan Anggota Polsek")
                link, no, tot = ambil_foto_drive("qw1_5")
                submit_laporan(page, "QW1.5", "Green policing", link, no, tot)

                # QW1.6 Jumat Keliling (Jumling)
                buka_kegiatan_qw1(page, "QW1.6")
                in_jm = page.locator("xpath=//*[contains(text(), 'Nama masjid')]/following::input")
                in_jm.nth(0).fill("MASJID NURUL HUDA")
                in_jm.nth(1).fill("(-7.8260946, 111.1280397)")
                page.locator("textarea").first.fill("Masjid besar di wilayah Jatisrono dengan jamaah ramai")
                page.locator("select").last.select_option(label="Jamaah")
                link, no, tot = ambil_foto_drive("qw1_6")
                submit_laporan(page, "QW1.6", "Jumat keliling (Jumling)", link, no, tot)

            # SABTU: QW1.7 Subuh Keliling (Suling)
            elif hari_ke == 5:
                buka_kegiatan_qw1(page, "QW1.7")
                in_sl = page.locator("xpath=//*[contains(text(), 'Nama masjid')]/following::input")
                in_sl.nth(0).fill("MASJID NURUL HUDA")
                in_sl.nth(1).fill("(-7.8260946, 111.1280397)")
                page.locator("textarea").first.fill("Masjid utama yang berada di pinggir jalan raya rawan laka dan pencurian")
                page.locator("select").last.select_option(label="Jamaah")
                link, no, tot = ambil_foto_drive("qw1_7")
                submit_laporan(page, "QW1.7", "Subuh keliling (Suling)", link, no, tot)

            # MINGGU: QW1.8 Minggu Kasih
            elif hari_ke == 6:
                buka_kegiatan_qw1(page, "QW1.8")
                in_mk = page.locator("xpath=//*[contains(text(), 'Nama tempat ibadah')]/following::input")
                in_mk.nth(0).fill("GEREJA SANTA MARIA JATISRONO")
                in_mk.nth(1).fill("(-7.829100, 111.130200)")
                page.locator("textarea").first.fill("Memberikan rasa aman dan nyaman pada saat ibadah berlangsung")
                page.locator("select").last.select_option(label="Pengamanan")
                link, no, tot = ambil_foto_drive("qw1_8")
                submit_laporan(page, "QW1.8", "Minggu kasih", link, no, tot)

            # ----------------------------------------------------
            # 2. JALANKAN 4 KEGIATAN HARIAN QW7 (SETIAP HARI)
            # ----------------------------------------------------
            isi_qw7_harian(page)

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
