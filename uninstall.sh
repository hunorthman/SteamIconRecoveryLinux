#!/bin/bash

# ==============================================================================
# HG Soft - SteamIconRecoveryLinux Eltávolító Szkript
# ==============================================================================

APP_NAME="SteamIconRecoveryLinux"
INSTALL_DIR="$HOME/.$APP_NAME"
BIN_LINK="$HOME/.local/bin/steamiconrecovery"
DESKTOP_FILE="$HOME/.local/share/applications/SteamIconRecoveryLinux.desktop"
CONFIG_FILE="$HOME/.config/hgsoft/SteamIconRecoveryLinux.conf"
CONFIG_DIR="$HOME/.config/hgsoft"

echo "=================================================="
echo "   $APP_NAME eltávolítása - HG Soft"
echo "=================================================="

# 1. Rejtett telepítési könyvtár törlése
if [ -d "$INSTALL_DIR" ]; then
    echo "[*] Telepítési könyvtár törlése: $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
fi

# 2. Szimbolikus link törlése a ~/.local/bin mappából
if [ -f "$BIN_LINK" ] || [ -L "$BIN_LINK" ]; then
    echo "[*] Futtatható parancs törlése: $BIN_LINK"
    rm -f "$BIN_LINK"
fi

# 3. KDE Plasma menübejegyzés törlése
if [ -f "$DESKTOP_FILE" ]; then
    echo "[*] KDE menübejegyzés törlése: $DESKTOP_FILE"
    rm -f "$DESKTOP_FILE"
fi

# 4. Elmentett API kulcs és konfiguráció törlése
if [ -f "$CONFIG_FILE" ]; then
    echo "[*] Elmentett API kulcs és konfiguráció törlése: $CONFIG_FILE"
    rm -f "$CONFIG_FILE"

    # Ha a hgsoft mappa üressé vált, azt is letakarítjuk
    if [ -d "$CONFIG_DIR" ] && [ -z "$(ls -A "$CONFIG_DIR")" ]; then
        rmdir "$CONFIG_DIR"
    fi
fi

# 5. KDE Plasma menü cache frissítése
echo "[*] Menü cache frissítése..."
kbuildsycoca6 --noincremental > /dev/null 2>&1 || kbuildsycoca5 --noincremental > /dev/null 2>&1

echo "=================================================="
echo " [v] A SteamIconRecoveryLinux sikeresen és nyomtalanul eltávolítva!"
echo "=================================================="
