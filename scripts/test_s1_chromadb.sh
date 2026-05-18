#!/bin/bash
# S1 Doğrulama Testi — ChromaDB HTTP Servis
# Lordum bu scripti manuel çalıştırarak S1'i doğrular:
# wsl -d Ubuntu-22.04 -- bash /mnt/c/Kuroshin/scripts/test_s1_chromadb.sh

VENV="/root/kuroshin/venv"
PORT=8100

echo "======================================"
echo " S1 — ChromaDB HTTP Servis Testi"
echo "======================================"

# 1. venv kontrolü
echo ""
echo "[1] Venv kontrol ediliyor..."
if [ -d "$VENV" ]; then
    echo "    ✅ Venv bulundu: $VENV"
else
    echo "    ❌ Venv bulunamadı: $VENV"
    exit 1
fi

# 2. chromadb paketi kontrolü
echo ""
echo "[2] chromadb paketi kontrol ediliyor..."
source "$VENV/bin/activate"
if python3 -c "import chromadb; print('    ✅ chromadb sürüm:', chromadb.__version__)" 2>/dev/null; then
    :
else
    echo "    ❌ chromadb yüklü değil. Çözüm: pip install chromadb"
    exit 1
fi

# 3. chroma CLI kontrolü
echo ""
echo "[3] chroma CLI kontrol ediliyor..."
CHROMA_BIN="$VENV/bin/chroma"
if [ -f "$CHROMA_BIN" ]; then
    echo "    ✅ chroma CLI: $CHROMA_BIN"
else
    echo "    ⚠️  chroma CLI venv/bin içinde yok — sistem PATH deneniyor..."
    if command -v chroma &>/dev/null; then
        CHROMA_BIN=$(command -v chroma)
        echo "    ✅ chroma CLI bulundu: $CHROMA_BIN"
    else
        echo "    ❌ chroma CLI bulunamadı."
        echo "    Çözüm: pip install 'chromadb[cli]' veya pip install chromadb --upgrade"
        exit 1
    fi
fi

# 4. ChromaDB servisi çalışıyor mu kontrol et
echo ""
echo "[4] Port $PORT kontrol ediliyor..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/api/v2/heartbeat 2>/dev/null || echo "000")
if [ "$HEALTH" = "200" ] || [ "$HEALTH" = "204" ]; then
    echo "    ✅ ChromaDB HTTP servisi AKTIF (port $PORT)"
else
    echo "    ⚠️  ChromaDB henüz çalışmıyor (HTTP $HEALTH)"
    echo "    Kuroshin.bat Walker Modu ile başlatın."
fi

# 5. Data dizini kontrolü
echo ""
echo "[5] Data dizini kontrol ediliyor..."
DATA_DIR="/mnt/c/Kuroshin/data/chroma_db"
if [ -f "$DATA_DIR/chroma.sqlite3" ]; then
    SIZE=$(du -sh "$DATA_DIR/chroma.sqlite3" 2>/dev/null | cut -f1)
    echo "    ✅ chroma.sqlite3 mevcut (boyut: $SIZE)"
else
    echo "    ℹ️  chroma.sqlite3 yok — ilk başlatmada oluşacak."
fi

echo ""
echo "======================================"
echo " Test tamamlandı."
echo "======================================"
