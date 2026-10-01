"""Apply the real read-boundary checks to the checkout's documented example."""
from pathlib import Path
from unittest import mock

import test_file_worker as original


class CheckoutGeneratorTests(original.FileWorkerTests):
    def launch(self, source, output, observed=None):
        example = Path(__file__).resolve().parents[1] / 'examples/polling_generator.py'
        with mock.patch.object(original, 'WORKER', example):
            return super().launch(source, output, observed)
