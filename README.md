<p align="center">
  <h1 align="center">Kuroshin OS</h1>
  <p align="center">Fully-local, $0-cloud autonomous AI assistant — 35B model on 8GB VRAM</p>
</p>

<p align="center">
  <img alt="Status" src="https://img.shields.io/badge/status-Public%20v1.2-brightgreen">
  <img alt="License" src="https://img.shields.io/github/license/KuroShinHQ/kuroshin">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="Model" src="https://img.shields.io/badge/LLM-Qwen3--35B--A3B%20IQ4__XS-orange">
</p>

---

## Overview

**Kuroshin OS** is a fully-local autonomous AI assistant that runs a 35B-parameter language model on consumer 8GB VRAM hardware using IQ4\_XS quantization — with **zero cloud costs**. It features a MIRROR Thinker-Talker dual-process architecture, KILIC-KALKAN v7 prompt-injection security layer, LangGraph multi-agent orchestration, and a 26-tool Telegram bot interface.

The system is designed around the philosophy: **read schematics → read attention maps** — transitioning from electrical engineering to AI development while maintaining a systems-thinking approach.

## Key Features

- **MIRROR Architecture** — Thinker-Talker dual-process inner monologue for efficient reasoning
- **KILIC-KALKAN v7** — 52-technique prompt-injection defense layer (Iron Inquisitor 97/97 tests pass)
- **26-Tool Agent** — Telegram bot with file ops, web search, code execution, and more
- **RAG Memory** — ChromaDB + BM25 hybrid retrieval for long-term context
- **MCP Servers** — 8 local Model Context Protocol servers (echo, search, bridge, walker, council, deerflow, sequential-thinking, kurowatch-automation)
- **Desktop UI** — PyQt6 floating-orb interface with WebEngine
- **$0/month** — No API keys, no cloud, no subscriptions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM Runtime | llama.cpp (IQ4\_XS quantization, 256K context) |
| Orchestration | LangGraph, Agno, smolagents |
| LLM Proxy | LiteLLM |
| Memory | ChromaDB, Rank-BM25, FlagEmbedding |
| Anti-Bot | curl\_cffi (TLS/JA3 impersonation), nodriver, Playwright |
| Desktop UI | PyQt6, PyInstaller |
| Platform | Python 3.10+, WSL Ubuntu-22.04, Docker |
| Protocol | MCP (Model Context Protocol) |

## Project Structure

```
kuroshin/
├── src/              # Core source (agents, memory, orchestration, serving)
├── agents/           # Chancellor, Walker, Council multi-agent services
├── mcp_servers/      # 8 MCP servers
├── soul/             # Cognitive/dream engine, idle loop
├── memory/           # Qdrant/Mem0 vector store
├── models/           # Local LLM GGUF files (16.45 GB)
├── config/           # LiteLLM providers, traffic control
├── KuroRecon/        # E-commerce price intelligence module
├── kurowatch/        # Anime/manga tracker (separate repo)
├── kuroshin_floating_ui/  # Desktop floating-orb UI
├── docs/             # Handoff, architecture, project inventory
├── scripts/          # Iron Inquisitor security suite, maintenance
├── tools/            # Crawlee bridge, utilities
└── CLAUDE.md         # AI assistant directives
```

## Installation

### Prerequisites

- Python 3.10+
- WSL2 (Ubuntu 22.04) or Linux
- GPU with 8GB+ VRAM (for local LLM)
- Docker (optional, for containerized services)

### Setup

```bash
git clone https://github.com/KuroShinHQ/kuroshin.git
cd kuroshin
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Edit with your settings

# Launch
python Kuroshin.bat  # or run individual services
```

### Submodules

This repo contains independent modules:
- **KuroRecon** — Turkish e-commerce price intelligence (Trendyol/Hepsiburada/Sahibinden/Epey)
- **kuroshin\_floating\_ui** — Desktop floating-orb PyQt6 interface
- **kurowatch** — Anime/manga tracker (separate GitHub repo)

## Status

**v1.2-STABLE** — Active development. Iron Inquisitor security suite: 97/97 tests pass. Currently maintaining KuroWatch (97.6% content matched) and exploring abbliterated models on 8GB VRAM.

## License

MIT License — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
