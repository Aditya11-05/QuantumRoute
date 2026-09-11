from __future__ import annotations

import tempfile
from pathlib import Path

from app.ml.train import train_model


def test_train_model_produces_real_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = str(Path(tmpdir) / "model.txt")
        report_path = str(Path(tmpdir) / "report.json")
        report = train_model(n_samples=800, seed=1, model_path=model_path, report_path=report_path)

        assert report.n_train > 0
        assert report.n_test > 0
        assert 0 <= report.r2 <= 1.0, "R2 should be a sane positive value for this task"
        assert report.mae >= 0
        assert report.rmse >= 0
        assert Path(model_path).exists()
        assert Path(report_path).exists()


def test_train_model_metrics_are_not_suspiciously_perfect():
    """
    R2 == 1.0 or MAE == 0 would indicate leakage or a fabricated
    metric, since our synthetic target includes injected noise. This
    test asserts genuine, imperfect learning.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = str(Path(tmpdir) / "model.txt")
        report_path = str(Path(tmpdir) / "report.json")
        report = train_model(n_samples=1500, seed=2, model_path=model_path, report_path=report_path)
        assert report.r2 < 0.999
        assert report.mae > 0.0001
