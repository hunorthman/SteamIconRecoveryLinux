#!/bin/bash

# ==============================================================================
# HG Soft - SteamIconRecoveryLinux Telepítő Szkript
# ==============================================================================

APP_NAME="SteamIconRecoveryLinux"
INSTALL_DIR="$HOME/.$APP_NAME"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "=================================================="
echo "   $APP_NAME telepítése - HG Soft"
echo "=================================================="

# 1. Rejtett célkönyvtár létrehozása a Home mappában
echo "[*] Telepítési könyvtár előkészítése: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"

# 2. Fájlok másolása a rejtett mappába
echo "[*] Alkalmazásfájlok másolása..."
cp -r ./* "$INSTALL_DIR/"

# Futtatási jogok megadása
chmod +x "$INSTALL_DIR/SteamIconRecoveryLinux.py"

# 3. Szimbólikus link (futtató parancs) létrehozása a ~/.local/bin mappába
echo "[*] Futtatható parancs beállítása..."
ln -sf "$INSTALL_DIR/SteamIconRecoveryLinux.py" "$BIN_DIR/steamiconrecovery"

# 4. Asztali és Menü indító (.desktop fájl) generálása a KDE menühöz
echo "[*] KDE Plasma menübejegyzés létrehozása..."
DESKTOP_FILE="$DESKTOP_DIR/SteamIconRecoveryLinux.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=SteamIconRecoveryLinux
Comment=Steam ikonok helyreállítása Linuxon
Exec=python3 $INSTALL_DIR/SteamIconRecoveryLinux.py
Icon=$INSTALL_DIR/icon.png
Terminal=false
Type=Application
Categories=Game;Utility;Qt;
EOF

chmod +x "$DESKTOP_FILE"

# 5. KDE Plasma menü cache frissítése
echo "[*] Menü cache frissítése..."
kbuildsycoca6 --noincremental > /dev/null 2>&1 || kbuildsycoca5 --noincremental > /dev/null 2>&1

echo "=================================================="
echo " [v] A telepítés sikeresen befejeződött!"
echo ""
echo " Indítási lehetőségek:"
echo "   1. A KDE alkalmazásmenüből (Játékok / Segédprogramok almenü)"
echo "   2. Terminálból: steamiconrecovery"
echo "=================================================="
