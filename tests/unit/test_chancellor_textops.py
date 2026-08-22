"""chancellor saf metin isleme fonksiyonlarinin birim testleri.

Bu testler AG/servis gerektirmez: strip/score/loop/validate fonksiyonlari
saf text-in -> out davranislarini dogrular.
"""
import pytest


class TestStripThink:
    def test_closes_think_block_removed(self, chancellor):
        # Normal durum: kapali <think> blogu silinir, cevap korunur.
        out = chancellor._strip_think("<think>ic dusunce</think>Merhaba")
        assert "ic dusunce" not in out
        assert "Merhaba" in out

    def test_unclosed_think_takes_rest(self, chancellor):
        # Hata durumu: kapanmamis think — kalan her sey think sayilir.
        out = chancellor._strip_think("Cevap<think>sonsuza dek")
        assert "sonsuza dek" not in out

    def test_empty_string_returns_empty(self, chancellor):
        # Sinir durumu.
        assert chancellor._strip_think("") == ""

    def test_no_think_block_passthrough(self, chancellor):
        # Sinir durumu: think olmayan metin degismez (strip haric).
        assert chancellor._strip_think("Duz metin") == "Duz metin"

    def test_multiline_think_removed(self, chancellor):
        # Sinir durumu: cok satirli think blogu (DOTALL).
        src = "<think>satir1\nsatir2\nsatir3</think>\nSonuc"
        out = chancellor._strip_think(src)
        assert "satir1" not in out and "Sonuc" in out


class TestScoreThink:
    def test_perfect_think_scores_high(self, chancellor):
        # Normal durum: 4 etiket + Turkce + uzunluk + arac eslesmesi = tam puan.
        text = ("[NİYET] kullanicinin istegi net.\n[STRATEJİ] once dosyayi oku.\n"
                "[GÜVENLİK] risk yok.\n[RAFİNE] adimlari kisalt.\n"
                "Walker aracini kullanacagim. " * 6)
        r = chancellor._score_think(text, tool_called="Walker")
        assert r["max"] == 100
        assert r["score"] >= 80

    def test_empty_think_scores_low(self, chancellor):
        # Sinir durumu: bos think — dusuk puan, patlama yok.
        r = chancellor._score_think("")
        assert r["score"] <= 40

    def test_tool_mismatch_penalized(self, chancellor):
        # Hata durumu: arac adi think'te gecmiyorsa puan kaybi.
        good = chancellor._score_think("[NIYET] x [STRATEJI] y Walker", tool_called="Walker")
        bad = chancellor._score_think("[NIYET] x [STRATEJI] y", tool_called="Walker")
        assert good["score"] > bad["score"]

    def test_result_schema(self, chancellor):
        # Sinir durumu: sonuc semasi sabit (score/max/detail).
        r = chancellor._score_think("test")
        assert set(r.keys()) == {"score", "max", "detail"}
        assert 0 <= r["score"] <= 100


class TestKillLoop:
    def test_repeated_sentence_truncated(self, chancellor):
        # Normal durum: ayni uzun cumle tekrari kesilir.
        s = "Bu cumle bilerek cok uzatilmis bir tekrar cumlesidir. "
        text = (s + s + s).strip()
        out = chancellor._kill_loop(text)
        assert out.count(s.strip()) < text.count(s.strip())

    def test_unique_text_untouched(self, chancellor):
        # Normal durum: benzersiz metin aynen doner.
        text = "Birinci farkli paragraf burada. Ikinci tamamen baska bir cumle."
        assert chancellor._kill_loop(text) == text

    def test_empty_returns_empty(self, chancellor):
        # Sinir durumu.
        assert chancellor._kill_loop("") == ""

    def test_short_sentences_never_flagged(self, chancellor):
        # Sinir durumu: <20 karakter cumleler dongu sayilmaz.
        text = "Kisa. Yine kisa. Ve bitti."
        assert chancellor._kill_loop(text) == text


class TestIlgValidate:
    def _valid(self):
        return "Lordum, sistem hazir."

    def test_valid_message_passes(self, chancellor):
        # Normal durum: kurallara uyan mesaj kabul.
        msg = self._valid()
        assert chancellor._ilg_validate(msg) is True

    def test_too_short_rejected(self, chancellor):
        # Sinir durumu: <10 karakter red.
        assert chancellor._ilg_validate("Lordum, ok") is False

    def test_too_long_rejected(self, chancellor):
        # Sinir durumu: >200 karakter red.
        msg = "Lordum, " + "x" * 250 + "."
        assert chancellor._ilg_validate(msg) is False

    def test_must_start_with_lordum(self, chancellor):
        # Hata durumu: 'Lordum' ile baslamayan mesaj red.
        assert chancellor._ilg_validate("Selam, buradayim.") is False

    def test_markdown_rejected(self, chancellor):
        # Hata durumu: markdown/kod isareti iceren mesaj red.
        assert chancellor._ilg_validate("Lordum, **kalin** yazdim.") is False

    def test_empty_rejected(self, chancellor):
        assert chancellor._ilg_validate("") is False


class TestIlPostProcess:
    def test_first_line_extracted(self, chancellor):
        # Normal durum: ilk paragrafin ilk satiri alinir.
        raw = "<think>plan</think>Lordum, ilk satir.\nIkinci satir\n\nTablo:"
        out = chancellor._ilg_post_process(raw)
        assert out == "Lordum, ilk satir."


class TestStripResponseLeaks:
    def test_identity_leak_removed(self, chancellor):
        # Hata durumu: kimlik sizintisi temizlenmeli.
        out = chancellor._strip_response_leaks("Komut tamam.\nBen bir yapay zekaiyim.")
        assert "yapay zeka" not in out.lower()

    def test_bold_markers_stripped(self, chancellor):
        # Normal durum: markdown kalin isaretleri kaldirilir.
        out = chancellor._strip_response_leaks("**onemli** nokta")
        assert "**" not in out and "onemli" in out

    def test_clean_text_unchanged(self, chancellor):
        # Sinir durumu: temiz metin korunur.
        src = "Sistem durumu normal."
        assert chancellor._strip_response_leaks(src) == src
