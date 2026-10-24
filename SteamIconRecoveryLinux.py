#!/usr/bin/env python3
import os
import re
import glob
import json
import subprocess

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton,
    QTextEdit, QProgressBar, QMessageBox, QGroupBox
)

# Konfigurációs fájl útvonala (~/.config/hgsoft/SteamIconRecoveryLinux.conf)
CONFIG_DIR = os.path.expanduser("~/.config/hgsoft")
CONFIG_FILE = os.path.join(CONFIG_DIR, "SteamIconRecoveryLinux.conf")

# Külső ikon útvonala a py fájl mellett
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ICON_PATH = os.path.join(SCRIPT_DIR, "icon.png")

APPLICATIONS_DIR = os.path.expanduser("~/.local/share/applications")
ICON_DIR = os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps")

POSSIBLE_STEAM_PATHS = [
    os.path.expanduser("~/.local/share/Steam"),
    os.path.expanduser("~/.steam/steam"),
    os.path.expanduser("~/.steam/root"),
    os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam")
]

# ------------------------------------------------------------------------------
# Konfiguráció kezelése
# ------------------------------------------------------------------------------
def load_api_key():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("steamgriddb_api_key", "")
        except Exception:
            pass
    return ""

def save_api_key(api_key):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"steamgriddb_api_key": api_key.strip()}, f, indent=4)
        return True
    except Exception:
        return False

# ------------------------------------------------------------------------------
# Háttérben futó feldolgozó szál (QThread)
# ------------------------------------------------------------------------------
class RecoveryWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(dict)

    def __init__(self, with_icons, api_key):
        super().__init__()
        self.with_icons = with_icons
        self.api_key = api_key

    def download_file_curl(self, url, target_path, auth_header=None):
        try:
            cmd = [
                "curl", "-s", "-L",
                "-A", "Mozilla/5.0 (X11; Linux x86_64)",
                "--max-time", "10",
                "-o", target_path
            ]
            if auth_header:
                cmd.extend(["-H", f"Authorization: Bearer {auth_header}"])
            cmd.append(url)

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                return True
        except Exception:
            pass
        return False

    def convert_ico_to_png(self, ico_path, png_path):
        try:
            from PIL import Image
            with Image.open(ico_path) as img:
                img.save(png_path, "PNG")
            if os.path.exists(ico_path): os.remove(ico_path)
            return True
        except Exception:
            pass

        if os.system(f"convert '{ico_path}[0]' '{png_path}' > /dev/null 2>&1") == 0:
            if os.path.exists(ico_path): os.remove(ico_path)
            return True

        os.rename(ico_path, png_path)
        return True

    def fetch_icon_from_steamgriddb(self, app_id, target_png):
        if not self.api_key:
            return False

        temp_ico = os.path.join(ICON_DIR, f"temp_sgdb_{app_id}.ico")
        json_game_path = os.path.join(ICON_DIR, f"sgdb_game_{app_id}.json")
        json_icon_path = os.path.join(ICON_DIR, f"sgdb_icon_{app_id}.json")

        game_url = f"https://www.steamgriddb.com/api/v2/games/steam/{app_id}"
        if self.download_file_curl(game_url, json_game_path, auth_header=self.api_key):
            try:
                with open(json_game_path, 'r') as f:
                    game_data = json.load(f)
                    if game_data.get('success') and 'data' in game_data:
                        sgdb_game_id = game_data['data']['id']

                        icons_url = f"https://www.steamgriddb.com/api/v2/icons/game/{sgdb_game_id}"
                        if self.download_file_curl(icons_url, json_icon_path, auth_header=self.api_key):
                            with open(json_icon_path, 'r') as f_icons:
                                icons_data = json.load(f_icons)
                                if icons_data.get('success') and icons_data.get('data'):
                                    icon_url = icons_data['data'][0]['url']

                                    if self.download_file_curl(icon_url, temp_ico):
                                        self.convert_ico_to_png(temp_ico, target_png)

                                        for p in [json_game_path, json_icon_path]:
                                            if os.path.exists(p): os.remove(p)
                                        return True
            except Exception:
                pass

        for p in [json_game_path, json_icon_path]:
            if os.path.exists(p): os.remove(p)
        return False

    def find_steam_libraries(self):
        libraries = set()
        for base_path in POSSIBLE_STEAM_PATHS:
            vdf_path = os.path.join(base_path, "steamapps", "libraryfolders.vdf")
            if os.path.exists(vdf_path):
                libraries.add(os.path.join(base_path, "steamapps"))
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        paths = re.findall(r'"path"\s+"([^"]+)"', content)
                        for p in paths:
                            steamapps = os.path.join(p, "steamapps")
                            if os.path.exists(steamapps):
                                libraries.add(steamapps)
                except Exception:
                    pass
        return list(libraries)

    def parse_acf(self, acf_path):
        app_id, name = None, None
        try:
            with open(acf_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                appid_match = re.search(r'"appid"\s+"(\d+)"', content)
                name_match = re.search(r'"name"\s+"([^"]+)"', content)
                if appid_match and name_match:
                    app_id = appid_match.group(1)
                    name = name_match.group(1)
        except Exception:
            pass
        return app_id, name

    def create_desktop_file(self, app_id, name, has_custom_icon):
        os.makedirs(APPLICATIONS_DIR, exist_ok=True)
        desktop_filename = f"steam_app_{app_id}.desktop"
        desktop_filepath = os.path.join(APPLICATIONS_DIR, desktop_filename)

        icon_path = os.path.join(ICON_DIR, f"steam_icon_{app_id}.png") if has_custom_icon else "steam"

        content = f"""[Desktop Entry]
Name={name}
Comment=Play this game on Steam
Exec=steam steam://rungameid/{app_id}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Game;
"""
        with open(desktop_filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def run(self):
        self.log_signal.emit("[*] Steam könyvtárak keresése...")
        libraries = self.find_steam_libraries()

        summary = {
            "total": 0,
            "downloaded": [],
            "already_existed": [],
            "failed": []
        }

        if not libraries:
            self.log_signal.emit("[!] Nem található Steam könyvtár!")
            self.finished_signal.emit(summary)
            return

        self.log_signal.emit(f"[+] Talált Steam könyvtárak száma: {len(libraries)} db")

        manifests = []
        for lib in libraries:
            for manifest in glob.glob(os.path.join(lib, "appmanifest_*.acf")):
                app_id, name = self.parse_acf(manifest)
                if app_id and name:
                    if not any(skip in name for skip in ["Proton", "Steamworks", "Steam Linux Runtime", "Steam Controller"]):
                        manifests.append((app_id, name))

        summary["total"] = len(manifests)
        total_count = summary["total"]

        for idx, (app_id, name) in enumerate(manifests, start=1):
            self.log_signal.emit(f"\n[*] [{idx}/{total_count}] Feldolgozás: {name} ({app_id})")

            has_icon = False
            if self.with_icons:
                target_png = os.path.join(ICON_DIR, f"steam_icon_{app_id}.png")
                os.makedirs(ICON_DIR, exist_ok=True)

                if os.path.exists(target_png) and os.path.getsize(target_png) > 0:
                    self.log_signal.emit(f"   [=] Az ikon már létezett a helyi tárolóban.")
                    summary["already_existed"].append(name)
                    has_icon = True
                else:
                    if self.fetch_icon_from_steamgriddb(app_id, target_png):
                        self.log_signal.emit(f"   [+] Ikon sikeresen letöltve API-ról!")
                        summary["downloaded"].append(name)
                        has_icon = True
                    else:
                        self.log_signal.emit(f"   [-] Ikon letöltése nem sikerült (alapértelmezett ikon használata).")
                        summary["failed"].append(name)

            self.create_desktop_file(app_id, name, has_icon)
            self.progress_signal.emit(idx, total_count)

        self.log_signal.emit("\n[*] KDE Plasma cache frissítése...")
        os.system("rm -f ~/.cache/icon-cache.kcache ~/.cache/ksycoca6* ~/.cache/ksycoca5*")
        os.system("gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor > /dev/null 2>&1")
        os.system("kbuildsycoca6 --noincremental > /dev/null 2>&1 || kbuildsycoca5 --noincremental > /dev/null 2>&1")

        self.finished_signal.emit(summary)

# ------------------------------------------------------------------------------
# Fő GUI Ablak (PySide6)
# ------------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SteamIconRecoveryLinux - HG Soft")
        self.resize(700, 550)

        # Külső ikon beállítása az ablakra és a tálcára
        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))

        self.current_api_key = ""

        self.init_ui()
        self.load_settings()

        # Kizárólag akkor mutatunk indítási tájékoztatót, ha MÉG NINCS elmentve API kulcs
        if not self.current_api_key:
            self.show_startup_dialog()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. API Key Beállítások csoport
        api_group = QGroupBox("SteamGridDB API Beállítások")
        api_layout = QHBoxLayout(api_group)

        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Másold ide a SteamGridDB API kulcsodat...")
        self.api_input.setEchoMode(QLineEdit.Normal)

        self.api_display_label = QLabel()
        self.api_display_label.setStyleSheet("font-weight: bold; color: #2ecc71;")

        self.action_api_btn = QPushButton("Mentés")
        self.action_api_btn.clicked.connect(self.toggle_api_mode)

        self.get_api_btn = QPushButton("Kulcs Beszerzése")
        self.get_api_btn.clicked.connect(self.open_steamgriddb)

        api_layout.addWidget(QLabel("API Kulcs:"))
        api_layout.addWidget(self.api_input)
        api_layout.addWidget(self.api_display_label)
        api_layout.addWidget(self.action_api_btn)
        api_layout.addWidget(self.get_api_btn)
        main_layout.addWidget(api_group)

        # 2. Üzemmód választó csoport
        mode_group = QGroupBox("Visszaállítási Mód")
        mode_layout = QVBoxLayout(mode_group)

        self.radio_with_icons = QRadioButton("Visszaállítás egyedi IKONOKKAL (SteamGridDB API szükséges)")
        self.radio_no_icons = QRadioButton("Visszaállítás IKONOK NÉLKÜL (gyors, alapértelmezett Steam ikonnal)")
        self.radio_with_icons.setChecked(True)

        mode_layout.addWidget(self.radio_with_icons)
        mode_layout.addWidget(self.radio_no_icons)
        main_layout.addWidget(mode_group)

        # 3. Indító gomb
        self.start_btn = QPushButton("Indítók Visszaállítása")
        self.start_btn.setStyleSheet("font-weight: bold; padding: 10px; font-size: 14px;")
        self.start_btn.clicked.connect(self.start_recovery)
        main_layout.addWidget(self.start_btn)

        # 4. Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # 5. Log ablak
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

    def set_api_ui_state(self, is_saved):
        """ Váltás a beíró és a mentett/szerkesztő nézet között """
        if is_saved and self.current_api_key:
            self.api_input.hide()
            self.api_display_label.setText(self.current_api_key)
            self.api_display_label.show()
            self.action_api_btn.setText("Szerkesztés")
        else:
            self.api_display_label.hide()
            self.api_input.setText(self.current_api_key)
            self.api_input.show()
            self.action_api_btn.setText("Mentés")

    def toggle_api_mode(self):
        if self.api_input.isVisible():
            key = self.api_input.text().strip()
            if key:
                if save_api_key(key):
                    self.current_api_key = key
                    self.set_api_ui_state(is_saved=True)
                    QMessageBox.information(self, "Siker", "Az API kulcs sikeresen elmentve!")
                else:
                    QMessageBox.critical(self, "Hiba", "Nem sikerült elmenteni a konfigurációt!")
            else:
                QMessageBox.warning(self, "Figyelem", "Kérlek írj be egy érvényes API kulcsot!")
        else:
            self.set_api_ui_state(is_saved=False)

    def show_startup_dialog(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("SteamGridDB API Tájékoztató")
        msg.setText(
            "<b>Üdvözöl a SteamIconRecoveryLinux!</b><br><br>"
            "A játékok egyedi, nagyfelbontású ikonjainak automatikus letöltéséhez "
            "egy ingyenes <b>SteamGridDB API kulcsra</b> van szükség.<br><br>"
            "Ha nem rendelkezel kulccsal, beszerezhetsz egyet a SteamGridDB oldalán, "
            "vagy választhatod az <i>'IKONOK NÉLKÜL'</i> opciót is a gyors visszaállításhoz."
        )
        get_key_btn = msg.addButton("API Kulcs Beszerzése", QMessageBox.ActionRole)
        msg.addButton("Értettem", QMessageBox.AcceptRole)

        msg.exec()

        if msg.clickedButton() == get_key_btn:
            self.open_steamgriddb()

    def open_steamgriddb(self):
        QDesktopServices.openUrl("https://www.steamgriddb.com/profile/preferences/api")

    def load_settings(self):
        self.current_api_key = load_api_key()
        if self.current_api_key:
            self.set_api_ui_state(is_saved=True)
        else:
            self.set_api_ui_state(is_saved=False)

    def start_recovery(self):
        with_icons = self.radio_with_icons.isChecked()

        if self.api_input.isVisible() and self.api_input.text().strip():
            self.current_api_key = self.api_input.text().strip()
            save_api_key(self.current_api_key)
            self.set_api_ui_state(is_saved=True)

        if with_icons and not self.current_api_key:
            QMessageBox.warning(
                self, "Hiányzó API Kulcs",
                "Az ikonokkal történő visszaállításhoz meg kell adnod a SteamGridDB API kulcsodat!\n\n"
                "Ha nem akarsz API kulcsot használni, válaszd az 'IKONOK NÉLKÜL' opciót."
            )
            return

        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.progress_bar.setValue(0)

        self.worker = RecoveryWorker(with_icons, self.current_api_key)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text):
        self.log_text.append(text)

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def on_finished(self, summary):
        self.start_btn.setEnabled(True)

        total = summary["total"]
        downloaded = len(summary["downloaded"])
        existed = len(summary["already_existed"])
        failed = len(summary["failed"])

        summary_text = (
            "\n" + "="*50 + "\n"
            "               ÖSSZESÍTÉS\n"
             + "="*50 + f"\n"
            f"  [+] Összes feldolgozott játék: {total} db\n"
            f"  [+] Újonnan letöltött ikonok:  {downloaded} db\n"
            f"  [=] Már létező helyi ikonok:   {existed} db\n"
            f"  [-] Nem található/Hiba ikonok: {failed} db\n"
             + "="*50 + "\n"
        )

        if summary["failed"]:
            summary_text += "\nNem találhatók ikonok a következő játékokhoz:\n"
            for g in summary["failed"]:
                summary_text += f" - {g}\n"

        self.log_text.append(summary_text)

        popup_msg = (
            f"<b>A visszaállítás befejeződött!</b><br><br>"
            f"<b>Összes indító:</b> {total} db<br>"
            f"<b>Újonnan letöltve:</b> {downloaded} db<br>"
            f"<b>Már létezett:</b> {existed} db<br>"
            f"<b>Sikertelen/Hiányzó ikon:</b> {failed} db"
        )

        QMessageBox.information(self, "Folyamat Befejeződött", popup_msg)

# ------------------------------------------------------------------------------
# Alkalmazás Indítása
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication([])

    # Alkalmazásszintű ikon beállítása
    if os.path.exists(APP_ICON_PATH):
        app.setWindowIcon(QIcon(APP_ICON_PATH))

    window = MainWindow()
    window.show()
    app.exec()
