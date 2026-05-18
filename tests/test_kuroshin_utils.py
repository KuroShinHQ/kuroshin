"""
pytest tests/test_kuroshin_utils.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from kuroshin_utils import estimate_vram, setup_logger
import tempfile, logging


class TestEstimateVram:
    def test_gemma4_q4km(self):
        v = estimate_vram("google_gemma-4-E4B-it-Q4_K_M.gguf")
        # 4B * 0.55 = 2.2
        assert abs(v - 2.2) < 0.5

    def test_qwen_7b_q4km(self):
        v = estimate_vram("Qwen2.5-7B-Instruct-Q4_K_M.gguf")
        # 7 * 0.55 = 3.85
        assert 3.0 < v < 5.0

    def test_unknown_model(self):
        v = estimate_vram("unknown-model.gguf")
        assert v == 0.0

    def test_f16_large(self):
        v = estimate_vram("llama3-70b-f16.gguf")
        # 70 * 2.0 = 140.0
        assert v > 100.0

    def test_q8_model(self):
        v = estimate_vram("mistral-7b-q8_0.gguf")
        # 7 * 1.0 = 7.0
        assert abs(v - 7.0) < 0.5


class TestSetupLogger:
    def test_returns_logger(self):
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            path = f.name
        logger = setup_logger("test_logger_01", path)
        assert isinstance(logger, logging.Logger)
        logger.info("test mesaj")

    def test_idempotent(self):
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            path = f.name
        l1 = setup_logger("test_logger_02", path)
        l2 = setup_logger("test_logger_02", path)
        # ikinci çağrı yeni handler eklememeli
        assert l1 is l2
        assert len(l1.handlers) == len(l2.handlers)
