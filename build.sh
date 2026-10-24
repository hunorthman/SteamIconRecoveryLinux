#!/bin/bash

# ==============================================================================
# HG Soft - SteamIconRecoveryLinux Csomagoló / Build Szkript
# ==============================================================================

PACKAGE_NAME="SteamIconRecoveryLinux"
VERSION="1.0"
BUILD_DIR="build_tmp"
OUTPUT_TAR="${PACKAGE_NAME}-v${VERSION}.tar.gz"

echo "[*] Build folyamat indítása..."

# 1. Kötelező fájlok ellenőrzése (most már az uninstall.sh is benne van!)
REQUIRED_FILES=("SteamIconRecoveryLinux.py" "icon.png" "installer.sh" "uninstall.sh")

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "[!] HIBA: A(z) '$file' hiányzik a build könyvtárból!"
        exit 1
    fi
done

# 2. Ideiglenes build könyvtár takarítása és létrehozása
rm -rf "$BUILD_DIR" "$OUTPUT_TAR"
mkdir -p "$BUILD_DIR"

# 3. Fájlok másolása
echo "[*] Fájlok előkészítése a csomagoláshoz..."
cp SteamIconRecoveryLinux.py "$BUILD_DIR/"
cp icon.png "$BUILD_DIR/"
cp installer.sh "$BUILD_DIR/"
cp uninstall.sh "$BUILD_DIR/"

# Futtatási jogok érvényesítése
chmod +x "$BUILD_DIR/installer.sh"
chmod +x "$BUILD_DIR/uninstall.sh"
chmod +x "$BUILD_DIR/SteamIconRecoveryLinux.py"

# 4. Tar.gz csomag létrehozása
echo "[*] Archívum csomagolása: $OUTPUT_TAR..."
tar -czf "$OUTPUT_TAR" -C "$BUILD_DIR" .

# Ideiglenes mappák törlése
rm -rf "$BUILD_DIR"

echo "=================================================="
echo " [v] Build sikeres! Csomag elkészült: $OUTPUT_TAR"
echo "=================================================="
