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

NAMA_KAPOLSEK = "AKP AGUS SUYANTO , S.H, M.H."
TANGGAL_PATOKAN = date(2026, 10, 29)

# ==========================================================
# LINK FOLDER GOOGLE DRIVE 8 KEGIATAN KAPOLSEK
# ==========================================================
FOLDER_URLS = {
    "qw7_1": "https://drive.google.com/drive/folders/10cTeMmc067qHy1TtRXnqS6uQYuYeMO84",
    "qw7_2": "https://drive.google.com/drive/folders/1X-MEjPb1g7uxksdtKyrTQlpui2eCtFMJ",
    "qw7_3": "https://drive.google.com/drive/folders/1RDdRwoFQT_6sM_fuI6lxaHI8HyatKT48",
    "qw7_4": "https://drive.google.com/drive/folders/1VIZ6BCtiGMWIHs7qsT_dr03cUsr3NKJ9",
    "qw1_1": "https://drive.google.com/drive/folders/1XX38ZQyxI0sDaMXJWivwOyE9qnefWYFa",
    "qw1_6": "https://drive.google.com/drive/folders/1iuJbE0UhBq7QGIcAiod6I2mOS8e181r9",
    "qw1_7": "https://drive.google.com/drive/folders/1OjDhQuUbJhOtHaFXXY63sZccmLl_fs_Q",
    "qw1_8": "https://drive.google.com/drive/folders/1FcnVWFZJmzPueHfFCKQitd5RgyXKsH33",
}

def kirim_notif_telegram(pesan, foto_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    daftar_chat_id = [cid.strip() for cid in TG_CHAT_ID.split(",") if cid.strip()]
    for cid in daftar_chat_id:
        try:
            if foto_path and os.path.exists(foto_path):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                with open(foto_path, "rb") as f:
                    requests.post(url, data={"chat_id": cid, "caption": pesan[:1000]}, files={"photo": f}, timeout=20)
            else:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                requests.post(url, data={"chat_id": cid, "text": pesan[:4000]}, timeout=20)
        except Exception as e:
            print(f"Gagal kirim ke Telegram ({cid}):", e)

def ambil_foto_dari_folder(page, key_folder, mode="harian"):
    folder_url = FOLDER_URLS.get(key_folder, "")
    folder_id = folder_url.rstrip("/").split("/")[-1].split("?")[0]
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"

    wib_now = datetime.now(timezone(timedelta(hours=7))).date()
    selisih_hari = max(0, (wib_now - TANGGAL_PATOKAN).days)
    urutan = selisih_hari if mode == "harian" else (selisih_hari // 7)

    file_links = []
    seen = set()
    try:
        res = requests.get(embed_url, timeout=20)
        ids = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", res.text)
        if not ids:
            ids = re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', res.text)
        for fid in ids:
            if fid != folder_id and fid not in seen:
                seen.add(fid)
                file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")

        if not file_links:
            page.goto(embed_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            html = page.content()
            ids2 = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", html) or re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', html)
            for fid in ids2:
                if fid != folder_id and fid not in seen:
                    seen.add(fid)
                    file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")
    except Exception as e:
        print(f"Gagal memindai folder {key_folder}:", e)

    if file_links:
        idx_terpilih = urutan % len(file_links)
        return file_links[idx_terpilih], idx_terpilih + 1, len(file_links)

    return DEFAULT_LINK, 1, 1

def hapus_kotak_saran_jika_ada(page):
    try:
        tombol_hapus = page.locator("button").filter(has_text="×")
        if tombol_hapus.count() > 0:
            tombol_hapus.first.click()
            page.wait_for_timeout(800)
    except Exception:
        pass

def buka_tab_dan_kegiatan(page, nama_tab, nama_giat):
    # Pastikan tab Quick Wins terbuka
    tab = page.locator("button, div").filter(has_text=nama_tab)
    if tab.count() > 0:
        tab.last.click()
        page.wait_for_timeout(1500)

    # Jika menu kegiatan belum muncul, klik tombol "Isi laporan" pertama
    if page.get_by_text(nama_giat).count() == 0:
        if page.get_by_role("button", name="Isi laporan").count() > 0:
            page.get_by_role("button", name="Isi laporan").first.click()
            page.wait_for_timeout(1500)

    page.get_by_text(nama_giat).first.click()
    page.wait_for_timeout(2000)

    tombol_kapolsek = page.get_by_role("button", name="Kapolsek", exact=True)
    if tombol_kapolsek.count() > 0:
        tombol_kapolsek.first.click()
    page.get_by_label("Nama dan pangkat pejabat pelaksana").fill(NAMA_KAPOLSEK)

def isi_lokasi_dan_koordinat(page, label_lokasi, nama_lokasi, titik_koordinat):
    page.get_by_label(label_lokasi).first.fill(nama_lokasi)
    page.wait_for_timeout(500)
    input_koord = page.locator("input[placeholder*='koordinat'], input[placeholder*='-'], input[placeholder*='Maps']")
    if input_koord.count() > 0:
        input_koord.first.fill(titik_koordinat)

def kirim_dan_screenshot(page, kode, nama_giat, link_foto, no_foto, tot_foto):
    hapus_kotak_saran_jika_ada(page)
    page.locator("input[placeholder*='drive.google.com']").fill(link_foto)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Kirim laporan").click()
    page.wait_for_timeout(4000)

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
    hari_ke = wib_sekarang.weekday()  # 0=Senin, 4=Jumat, 5=Sabtu, 6=Minggu
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
            foto_harian = {
                "qw7_1": ambil_foto_dari_folder(page, "qw7_1", "harian"),
                "qw7_2": ambil_foto_dari_folder(page, "qw7_2", "harian"),
                "qw7_3": ambil_foto_dari_folder(page, "qw7_3", "harian"),
                "qw7_4": ambil_foto_dari_folder(page, "qw7_4", "harian"),
            }
            foto_mingguan = None
            if hari_ke == 0:
                foto_mingguan = ambil_foto_dari_folder(page, "qw1_1", "mingguan")
            elif hari_ke == 4:
                foto_mingguan = ambil_foto_dari_folder(page, "qw1_6", "mingguan")
            elif hari_ke == 5:
                foto_mingguan = ambil_foto_dari_folder(page, "qw1_7", "mingguan")
            elif hari_ke == 6:
                foto_mingguan = ambil_foto_dari_folder(page, "qw1_8", "mingguan")

            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if page.locator("input[type='password']").count() > 0:
                page.locator("input[type='email'], input[type='text']").first.fill(EMAIL)
                page.locator("input[type='password']").first.fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_timeout(5000)

            page.get_by_label("Nama dan pangkat pelapor").fill(NAMA_KAPOLSEK)
            page.locator("select").first.select_option(label="Kapolsek/Wakapolsek (12 kegiatan)")
            page.wait_for_timeout(2500)

            # ==========================================================
            # A. INPUT HARIAN: QW7.1 s/d QW7.4
            # ==========================================================
            # --- 1. QW7.1 Satu desa satu Bhabinkamtibmas ---
            buka_tab_dan_kegiatan(page, "QW7 Polres Kuat, Polsek Tangguh", "Satu desa satu Bhabinkamtibmas")
            num_inputs = page.locator("input[type='number']")
            if num_inputs.count() >= 2:
                num_inputs.nth(0).fill("17")
                num_inputs.nth(1).fill("4")
            page.get_by_label("Upaya pemenuhan satu Bhabinkamtibmas satu desa").fill("Sudah di laporkan kepada pimpinan")
            tombol_ya = page.get_by_role("button", name="Ya", exact=True)
            if tombol_ya.count() > 0:
                tombol_ya.first.click()
            link, no, tot = foto_harian["qw7_1"]
            kirim_dan_screenshot(page, "QW7.1", "Satu desa satu Bhabinkamtibmas", link, no, tot)

            # --- 2. QW7.2 Penataan personel ---
            buka_tab_dan_kegiatan(page, "QW7 Polres Kuat, Polsek Tangguh", "Penataan personel")
            num_inputs = page.locator("input[type='number']")
            if num_inputs.count() >= 1:
                num_inputs.nth(0).fill("4")
            link, no, tot = foto_harian["qw7_2"]
            kirim_dan_screenshot(page, "QW7.2", "Penataan personel", link, no, tot)

            # --- 3. QW7.3 Polsek siaga 24 jam ---
            buka_tab_dan_kegiatan(page, "QW7 Polres Kuat, Polsek Tangguh", "Polsek siaga 24 jam")
            num_inputs = page.locator("input[type='number']")
            if num_inputs.count() >= 2:
                num_inputs.nth(0).fill("0")
                num_inputs.nth(1).fill("3")
            tombol_ya = page.get_by_role("button", name="Ya", exact=True)
            if tombol_ya.count() > 0:
                tombol_ya.first.click()
            link, no, tot = foto_harian["qw7_3"]
            kirim_dan_screenshot(page, "QW7.3", "Polsek siaga 24 jam", link, no, tot)

            # --- 4. QW7.4 Perkara ringan dan rembuk warga ---
            buka_tab_dan_kegiatan(page, "QW7 Polres Kuat, Polsek Tangguh", "Perkara ringan dan rembuk warga")
            num_inputs = page.locator("input[type='number']")
            if num_inputs.count() >= 2:
                num_inputs.nth(0).fill("0")
                num_inputs.nth(1).fill("0")
            link, no, tot = foto_harian["qw7_4"]
            kirim_dan_screenshot(page, "QW7.4", "Perkara ringan dan rembuk warga", link, no, tot)

            # ==========================================================
            # B. INPUT MINGGUAN SESUAI HARI
            # ==========================================================
            if hari_ke == 0:
                buka_tab_dan_kegiatan(page, "QW1 Ruang Publik Aman", "Gatur pagi (pengaturan lalu lintas Senin pagi)")
                isi_lokasi_dan_koordinat(page, "Nama lokasi dan titik koordinat", "SIMPANG 4 PASAR JATISRONO", "(-7.8273967, 111.1285832)")
                page.get_by_label("Pertimbangan pilihan lokasi").select_option(label="Rawan keramaian")
                page.get_by_label("Cara bertindak di lokasi").select_option(label="Gatur")
                page.get_by_label("Jumlah lokasi gatur pagi").select_option(label="3")
                link, no, tot = foto_mingguan
                kirim_dan_screenshot(page, "QW1.1", "Gatur pagi (pengaturan lalu lintas Senin pagi)", link, no, tot)

            elif hari_ke == 4:
                buka_tab_dan_kegiatan(page, "QW1 Ruang Publik Aman", "Jumat keliling (Jumling)")
                isi_lokasi_dan_koordinat(page, "Nama masjid dan titik koordinat", "MASJID NURUL HUDA", "(-7.8260946, 111.1280397)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Masjid besar di jatirono")
                page.get_by_label("Peran").select_option(label="Jamaah")
                link, no, tot = foto_mingguan
                kirim_dan_screenshot(page, "QW1.6", "Jumat keliling (Jumling)", link, no, tot)

            elif hari_ke == 5:
                buka_tab_dan_kegiatan(page, "QW1 Ruang Publik Aman", "Subuh keliling (Suling)")
                isi_lokasi_dan_koordinat(page, "Nama masjid dan titik koordinat", "MASJID NURUL HUDA", "(-7.8261218, 111.1280397)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("MASJID BESAR DI JATISRONO")
                page.get_by_label("Peran").select_option(label="Jamaah")
                link, no, tot = foto_mingguan
                kirim_dan_screenshot(page, "QW1.7", "Subuh keliling (Suling)", link, no, tot)

            elif hari_ke == 6:
                buka_tab_dan_kegiatan(page, "QW1 Ruang Publik Aman", "Minggu kasih")
                isi_lokasi_dan_koordinat(page, "Nama tempat ibadah dan titik koordinat", "GEREJA SANTA MARIA JATISRONO", "(-7.8253420, 111.1305288)")
                page.get_by_label("Pertimbangan pilihan lokasi").fill("Gereja besar di jatisrono")
                page.get_by_label("Peran").fill("PENGAMANAN")
                link, no, tot = foto_mingguan
                kirim_dan_screenshot(page, "QW1.8", "Minggu kasih", link, no, tot)

        except Exception as e:
            err_ss = "error_kapolsek.png"
            try:
                page.screenshot(path=err_ss)
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan Kapolsek:\n{str(e)}", err_ss)
            except Exception:
                kirim_notif_telegram(f"⚠️ Gagal membuka web Kapolsek:\n{str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    jalankan_robot_kapolsek()
