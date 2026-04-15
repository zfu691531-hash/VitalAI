"""Import-hygiene tests for application entrypoints."""

from __future__ import annotations

import importlib
import unittest


class EntryPointImportTests(unittest.TestCase):
    def test_vitalai_main_can_be_imported(self) -> None:
        module = importlib.import_module("VitalAI.main")

        self.assertTrue(hasattr(module, "create_app"))
        self.assertIsNotNone(module.app)

    def test_base_package_can_be_imported_without_eager_failures(self) -> None:
        module = importlib.import_module("Base")

        self.assertIsNotNone(module.settings)
