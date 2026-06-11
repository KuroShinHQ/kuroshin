"""
Sci-Hub erişim modülü — ISP TLS/SNI bypass
Yöntem: DNS ile IP çöz → IP doğrudan + Host header + verify=False
"""
import re
import socket
import os
import curl_cffi.requests as req
from bs4 import BeautifulSoup

SCIHUB_HOST = "sci-hub.st"
FALLBACK_HOSTS = ["sci-hub.se", "sci-hub.ru", "sci-hub.red"]


def _resolve_ip(host: str) -> str | None:
    """8.8.8.8 üzerinden DNS çözümle (ISP DNS bloğunu atla)."""
    try:
        import subprocess
        out = subprocess.check_output(
            ["nslookup", host, "8.8.8.8"], timeout=8, text=True, stderr=subprocess.DEVNULL
        )
        # "Address: x.x.x.x" satırını bul (son eşleşme = asıl IP)
        matches = re.findall(r"Address:\s+([\d\.]+)", out)
        # 8.8.8.8 kendisi ilk satırda, sonrakiler hedef IP
        ips = [ip for ip in matches if ip != "8.8.8.8"]
        return ips[-1] if ips else None
    except Exception:
        return None


def _fetch_page(ip: str, host: str, path: str = "/") -> req.Response | None:
    try:
        r = req.get(
            f"https://{ip}{path}",
            headers={"Host": host, "Referer": f"https://{host}/"},
            impersonate="chrome131",
            verify=False,
            timeout=15,
        )
        return r
    except Exception as e:
        print(f"[scihub] fetch FAIL {host}{path}: {e}")
        return None


def _find_pdf_path(html: str) -> str | None:
    """HTML'den PDF path'ini çıkar."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. <a href="...pdf">
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            return a["href"]

    # 2. <embed type="application/pdf" src="...">
    for e in soup.find_all("embed", {"type": "application/pdf"}):
        if e.get("src"):
            return e["src"]

    # 3. <iframe id="pdf" src="...">
    for i in soup.find_all("iframe", id="pdf"):
        if i.get("src"):
            return i["src"]

    # 4. location.href veya window.open içinde PDF
    m = re.search(r'["\']([^"\']+\.pdf[^"\']*)["\']', html)
    if m:
        return m.group(1)

    return None


def download_paper(doi: str, out_path: str = "./paper.pdf") -> bool:
    """
    DOI ile Sci-Hub'dan PDF indir.
    Döner: True (başarılı) / False (başarısız)
    """
    # Host listesi dene
    hosts = [SCIHUB_HOST] + FALLBACK_HOSTS

    for host in hosts:
        print(f"[scihub] Deneniyor: {host}")
        ip = _resolve_ip(host)
        if not ip:
            print(f"[scihub] DNS çözülemedi: {host}")
            continue

        print(f"[scihub] IP: {ip}")

        # 1. DOI sayfasını çek
        doi_path = f"/{doi.lstrip('/')}"
        r = _fetch_page(ip, host, doi_path)
        if not r or r.status_code != 200:
            print(f"[scihub] DOI sayfa FAIL: HTTP {r.status_code if r else 'N/A'}")
            continue

        title_tag = BeautifulSoup(r.text, "html.parser").find("title")
        print(f"[scihub] Makale: {title_tag.text.strip() if title_tag else 'N/A'}")

        # 2. PDF path bul
        pdf_path = _find_pdf_path(r.text)
        if not pdf_path:
            print(f"[scihub] PDF path bulunamadı")
            # Captcha veya makale yok olabilir
            print(r.text[:500])
            continue

        print(f"[scihub] PDF path: {pdf_path}")

        # 3. PDF'i indir
        pdf_r = _fetch_page(ip, host, pdf_path if pdf_path.startswith("/") else f"/{pdf_path}")
        if not pdf_r or pdf_r.status_code != 200:
            print(f"[scihub] PDF indirme FAIL: HTTP {pdf_r.status_code if pdf_r else 'N/A'}")
            continue

        if pdf_r.content[:4] != b"%PDF":
            print(f"[scihub] Geçersiz PDF (magic bytes: {pdf_r.content[:4]})")
            print(pdf_r.text[:300])
            continue

        # 4. Kaydet
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(pdf_r.content)

        print(f"[scihub] ✅ PDF kaydedildi: {out_path} ({len(pdf_r.content):,} bytes)")
        return True

    print(f"[scihub] ❌ Tüm hostlar başarısız")
    return False


if __name__ == "__main__":
    import sys

    doi = sys.argv[1] if len(sys.argv) > 1 else "10.1145/3375633"
    out = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/paper_{doi.replace('/', '_')}.pdf"

    print(f"DOI: {doi}")
    print(f"Çıktı: {out}")
    success = download_paper(doi, out)
    sys.exit(0 if success else 1)
