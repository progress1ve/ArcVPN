import io
import json
import unittest
from unittest.mock import patch

from scripts.reconcile_yookassa_amounts import provider_amount_kopecks


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class YooKassaReconcileTests(unittest.TestCase):
    def test_provider_amount_is_converted_to_kopecks(self):
        response = _Response(json.dumps({"amount": {"value": "300.00"}}).encode())
        with patch("urllib.request.urlopen", return_value=response):
            self.assertEqual(provider_amount_kopecks("shop", "secret", "payment"), 30000)
