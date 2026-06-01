# FAZ A Fix Patches (1 Haz 2026)

## Patch 1: SYSTEM_PROMPT — Çoğul kimlik yasağı

`agents/kuroshin_chancellor.py` line ~1505, KIMLIK bölümüne ek:

```
- ÇOĞUL KİMLİK YASAK: "Yapayız", "Yapay zekayız", "Biz bir yapay zekayız", "Bizim modelimiz" gibi
  ÇOĞUL ZAMIRLAR ASLA KULLANMA. Tekilsin, "Ben Kuroshin'im."
- ASLA "Biz yapay/AI/model" çoğul birinci şahıs kullanma — sen TEKİL bir varlıksın.
```

## Patch 2: _RESPONSE_LEAK_PATTERNS — 3 yeni desen

`line ~145 öncesi, _RESPONSE_LEAK_PATTERNS sonuna:`

```python
# FAZ A (1 Haz 2026): Çoğul "yapayız" drift — KIMLIK ihlali
_re_global.compile(r'\b[Bb]iz\s+(?:bir\s+)?yapay\s+zek[aâ]y?[ıi]z\b[^.]*\.?', _re_global.IGNORECASE),
_re_global.compile(r'\byapay\s+zek[aâ]y[ıi]z\b[^.]*\.?', _re_global.IGNORECASE),
_re_global.compile(r'\b[Bb]iz\s+(?:bir\s+)?dil\s+modelleriy[ıi]z\b[^.]*\.?', _re_global.IGNORECASE),
# Bold asterisk strip (içeriği korur, sadece ** çıkarır)
# Bu pattern compile + replace yerine ayrıca işlenir (sub değil, kaldır)
```

## Patch 3: Bold strip post-filter

`_strip_response_leaks` sonrası ek function ya da inline:

```python
def _strip_bold_asterisks(text: str) -> str:
    """Markdown **bold** -> içerik (düz metin)."""
    return _re_global.sub(r'\*\*([^*\n]+?)\*\*', r'\1', text)
```

`process_message` line ~4402 sonrası:
```python
content = _strip_bold_asterisks(content)
```

## Patch 4: Episodic adaptive threshold

`_EPISODIC_MIN_SCORE = 0.45` constant → fonksiyon:

```python
def _episodic_threshold(em) -> float:
    """Corpus boyutuna göre adaptive: sparse permissive, dense katı."""
    cnt = em.collection_count if em else 0
    if cnt < 50:    return 0.30  # sparse — recall yakala
    if cnt < 500:   return 0.45  # mevcut default
    return 0.55                  # dense — noise kes
```

`_get_episodic_context` içinde:
```python
threshold = _episodic_threshold(em)
good = [h for h in hits if h.get("score", 0) >= threshold and ...]
```
