#!/usr/bin/env python3
"""
Kuroshin LitGPT MCP Server v2.0
Fine-tune yonetimi: baslat, izle, durdur.
Araçlar: litgpt_status, litgpt_train, litgpt_log, litgpt_stop
"""
import asyncio
import json
import os
import re
import signal
import subprocess
from pathlib import Path

from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent

FINETUNE_DIR = "/mnt/c/Kuroshin/finetune"
LOG_DIR = "/mnt/c/Kuroshin/logs"

server = Server("kuroshin-litgpt")


def get_datasets():
    ds_path = Path(f"{FINETUNE_DIR}/datasets")
    if not ds_path.exists():
        return []
    datasets = []
    for f in ds_path.glob("*.jsonl"):
        try:
            lines = sum(1 for _ in open(f))
            datasets.append({"name": f.stem, "file": f.name, "records": lines})
        except Exception:
            datasets.append({"name": f.stem, "file": f.name, "records": "?"})
    return datasets


MODELS = {
    "qwen1.5b": "/root/kuroshin/models/qwen_hf",
    "gemma":    "/root/kuroshin/models/gemma-hf",
}


def get_available_models() -> list[dict]:
    available = []
    for name, path in MODELS.items():
        exists = Path(path).exists()
        available.append({"name": name, "path": path, "ready": exists})
    return available


def get_report():
    report_path = f"{FINETUNE_DIR}/reports/FINETUNE_REPORT.md"
    try:
        with open(report_path) as f:
            return f.read()
    except Exception:
        return "(Rapor bulunamadi)"


def find_training_pid(model: str, version: str) -> int | None:
    """run_finetune.sh PID'ini bul."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"run_finetune.sh.*{model}.*{version}"],
            capture_output=True, text=True
        )
        pid_str = result.stdout.strip().split("\n")[0]
        if pid_str.isdigit():
            return int(pid_str)
    except Exception:
        pass
    # Alternatif: log dosyasına göre litgpt/python process ara
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"litgpt.*{model}"],
            capture_output=True, text=True
        )
        pid_str = result.stdout.strip().split("\n")[0]
        if pid_str.isdigit():
            return int(pid_str)
    except Exception:
        pass
    return None


def parse_log_stats(lines: list[str]) -> dict:
    """Log satırlarından loss/step/epoch bilgisi çıkar."""
    stats = {"step": None, "loss": None, "epoch": None, "eta": None}
    # LitGPT çıktı formatları:
    # "step 120/500: loss 2.341, lr 0.0001, ...  time ..."
    # "iter 120: loss 2.341, ..."
    patterns = [
        r"step\s+(\d+)[/\s].*?loss[:\s]+([\d.]+)",
        r"iter\s+(\d+)[:\s].*?loss[:\s]+([\d.]+)",
        r"Epoch\s+([\d.]+).*?loss[:\s]+([\d.]+)",
    ]
    for line in reversed(lines):
        for pat in patterns:
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                if "epoch" in pat.lower():
                    stats["epoch"] = m.group(1)
                    stats["loss"] = m.group(2)
                else:
                    stats["step"] = m.group(1)
                    stats["loss"] = m.group(2)
                # ETA ara
                eta_m = re.search(r"(\d+:\d+:\d+|\d+m\s*\d+s)", line)
                if eta_m:
                    stats["eta"] = eta_m.group(1)
                return stats
    return stats


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="litgpt_status",
            description=(
                "Fine-tune durumunu göster: mevcut datasetler, tamamlanan eğitimler, hazır modeller. "
                "Kullanıcı 'eğitim durumu', 'datasetler', '/litgpt' dediğinde bu aracı çağır."
            ),
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="litgpt_train",
            description=(
                "Fine-tune eğitimini BAŞLAT. "
                "model: 'qwen1.5b', 'gemma', 'claude1.2b' — "
                "dataset: mevcut dataset adı (uzantısız, örn: 'kuroshin_test_v1') — "
                "version: çıktı versiyon adı (örn: 'v1', 'v2'). "
                "Kullanıcı 'eğit', 'train', 'fine-tune başlat' dediğinde bu aracı çağır."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model":   {"type": "string", "description": "Model: qwen1.5b | gemma | claude1.2b"},
                    "dataset": {"type": "string", "description": "Dataset adı (uzantısız)"},
                    "version": {"type": "string", "description": "Çıktı versiyonu (örn: v1)"}
                },
                "required": ["model", "dataset", "version"]
            }
        ),
        Tool(
            name="litgpt_log",
            description=(
                "Devam eden fine-tune eğitiminin log çıktısını göster. "
                "İlerleme, kayıp (loss), adım sayısı, hata varsa gösterir. "
                "Kullanıcı 'eğitim nasıl gidiyor', 'log göster', 'ilerleme' dediğinde çağır."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model":   {"type": "string", "description": "Model adı (örn: qwen1.5b)"},
                    "version": {"type": "string", "description": "Versiyon (örn: v1)"},
                    "lines":   {"type": "integer", "description": "Son kaç satır gösterilsin (varsayılan: 30)"}
                },
                "required": ["model", "version"]
            }
        ),
        Tool(
            name="litgpt_stop",
            description=(
                "Devam eden fine-tune eğitimini DURDUR. "
                "Kullanıcı 'eğitimi durdur', 'iptal et', 'dur', 'stop' dediğinde bu aracı çağır."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model":   {"type": "string", "description": "Model adı (örn: qwen1.5b)"},
                    "version": {"type": "string", "description": "Versiyon (örn: v1)"}
                },
                "required": ["model", "version"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "litgpt_status":
        return await status()
    elif name == "litgpt_train":
        return await train(arguments)
    elif name == "litgpt_log":
        return await log(arguments)
    elif name == "litgpt_stop":
        return await stop(arguments)
    return [TextContent(type="text", text=f"Bilinmeyen arac: {name}")]


async def status():
    datasets = get_datasets()
    report = get_report()
    models = get_available_models()

    ds_text = "\n".join(
        f"  - {d['name']} ({d['records']} kayit)" for d in datasets
    ) or "  (dataset yok)"

    model_text = "\n".join(
        f"  {'✅' if m['ready'] else '❌'} {m['name']}" for m in models
    )

    active = subprocess.run(
        ["pgrep", "-f", "run_finetune.sh"],
        capture_output=True, text=True
    )
    training_status = "🟢 AKTİF EĞİTİM VAR" if active.stdout.strip() else "⚪ Eğitim yok"

    return [TextContent(type="text", text=f"""KUROSHIN FİNE-TUNE DURUMU
{'='*40}
EĞİTİM: {training_status}

MEVCUT DATASETLERveri:
{ds_text}

KULLANILABİLİR MODELLER:
{model_text}

EĞİTİM GEÇMİŞİ:
{report}
{'='*40}
Eğitim başlatmak için: model ve dataset söyle.
İlerleme için: "log göster" de.""")]


async def train(args: dict):
    model = args.get("model", "").strip()
    dataset = args.get("dataset", "").strip()
    version = args.get("version", "v1").strip()

    if not model or not dataset:
        return [TextContent(type="text", text="Model ve dataset adı gerekli.")]

    ds_file = f"{FINETUNE_DIR}/datasets/{dataset}.jsonl"
    if not Path(ds_file).exists():
        datasets = get_datasets()
        ds_names = [d['name'] for d in datasets]
        return [TextContent(type="text", text=f"Dataset bulunamadi: {dataset}\nMevcut: {', '.join(ds_names) or 'yok'}")]

    # Model mevcut mu kontrol et
    if model not in MODELS:
        model_names = ", ".join(MODELS.keys())
        return [TextContent(type="text", text=f"Bilinmeyen model: {model}\nMevcut modeller: {model_names}")]
    if not Path(MODELS[model]).exists():
        return [TextContent(type="text", text=f"❌ Model checkpoint bulunamadı: {MODELS[model]}\nModeli indirmek gerekiyor.")]

    # Zaten çalışan eğitim var mı?
    existing_pid = find_training_pid(model, version)
    if existing_pid:
        return [TextContent(type="text", text=f"⚠️ Bu model/versiyon zaten eğitimde (PID: {existing_pid}).\nÖnce durdurmak için: 'eğitimi durdur' de.")]

    log_file = f"{LOG_DIR}/finetune_{model}_{version}.log"

    # Log dizini oluştur
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.Popen(
            ["bash", f"{FINETUNE_DIR}/scripts/run_finetune.sh", model, version, dataset],
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        return [TextContent(type="text", text=f"""FİNE-TUNE BAŞLATILDI ✅
{'='*40}
Model   : {model}
Dataset : {dataset}
Versiyon: {version}
PID     : {proc.pid}
Log     : {log_file}

İlerlemeyi takip etmek için: "log göster" de.
Durdurmak için: "eğitimi durdur" de.""")]
    except Exception as e:
        return [TextContent(type="text", text=f"Baslatma hatasi: {str(e)[:300]}")]


async def log(args: dict):
    model = args.get("model", "").strip()
    version = args.get("version", "v1").strip()
    n_lines = int(args.get("lines", 30))

    if not model or not version:
        return [TextContent(type="text", text="Model ve versiyon gerekli.")]

    log_file = f"{LOG_DIR}/finetune_{model}_{version}.log"

    if not Path(log_file).exists():
        return [TextContent(type="text", text=f"Log dosyası bulunamadı: {log_file}\nHenüz eğitim başlatılmadı olabilir.")]

    try:
        with open(log_file) as f:
            all_lines = f.readlines()
    except Exception as e:
        return [TextContent(type="text", text=f"Log okunamadı: {e}")]

    tail = all_lines[-n_lines:] if len(all_lines) > n_lines else all_lines
    tail_text = "".join(tail).strip()

    # Eğitim durumu
    pid = find_training_pid(model, version)
    if pid:
        run_state = f"🟢 ÇALIŞIYOR (PID: {pid})"
    else:
        # Log sonuna bak
        last_lines_str = "".join(all_lines[-5:]).lower()
        if any(w in last_lines_str for w in ["error", "traceback", "exception", "killed"]):
            run_state = "🔴 HATA İLE DURDU"
        elif any(w in last_lines_str for w in ["complete", "finished", "saved", "done", "tamamlandi"]):
            run_state = "✅ TAMAMLANDI"
        else:
            run_state = "⚪ DURDU (sebep belirsiz)"

    # İstatistik çıkar
    stats = parse_log_stats(all_lines)
    stats_lines = []
    if stats["step"]:
        stats_lines.append(f"Adım   : {stats['step']}")
    if stats["epoch"]:
        stats_lines.append(f"Epoch  : {stats['epoch']}")
    if stats["loss"]:
        stats_lines.append(f"Loss   : {stats['loss']}")
    if stats["eta"]:
        stats_lines.append(f"ETA    : {stats['eta']}")
    stats_text = "\n".join(stats_lines) if stats_lines else "(henüz veri yok)"

    total = len(all_lines)
    return [TextContent(type="text", text=f"""FİNE-TUNE LOG — {model} {version}
{'='*40}
Durum  : {run_state}
{stats_text}
Toplam : {total} satır | Son {min(n_lines, total)} gösteriliyor
{'─'*40}
{tail_text}
{'='*40}
Durdurmak için: "eğitimi durdur" de.""")]


async def stop(args: dict):
    model = args.get("model", "").strip()
    version = args.get("version", "v1").strip()

    if not model or not version:
        return [TextContent(type="text", text="Model ve versiyon gerekli.")]

    pid = find_training_pid(model, version)

    if not pid:
        return [TextContent(type="text", text=f"⚪ {model} {version} için aktif eğitim bulunamadı.")]

    try:
        # Process grubunu öldür (start_new_session=True ile başlatıldı)
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        await asyncio.sleep(2)
        # Hâlâ çalışıyorsa SIGKILL
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass  # Zaten durmuş
        return [TextContent(type="text", text=f"""EĞİTİM DURDURULDU ✅
{'='*40}
Model   : {model}
Versiyon: {version}
PID     : {pid}

Log dosyası korundu: {LOG_DIR}/finetune_{model}_{version}.log
Son durumu görmek için: "log göster" de.""")]
    except Exception as e:
        return [TextContent(type="text", text=f"Durdurma hatası: {str(e)}\nManüel: kill -9 {pid}")]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
