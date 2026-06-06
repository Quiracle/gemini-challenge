from __future__ import annotations

import logging
import unittest
from unittest import mock

from nba_ingestion import __main__


class MainCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root_logger = logging.getLogger()
        self.original_handlers = list(self.root_logger.handlers)
        self.original_level = self.root_logger.level

    def tearDown(self) -> None:
        self.root_logger.handlers = self.original_handlers
        self.root_logger.setLevel(self.original_level)

    def test_main_logs_concise_error_without_debug_traceback(self) -> None:
        with (
            mock.patch("sys.argv", ["nba_ingestion"]),
            mock.patch("nba_ingestion.__main__.run_pipeline", side_effect=RuntimeError("blocked")),
            self.assertLogs("nba_ingestion.__main__", level="ERROR") as logs,
            self.assertRaises(SystemExit) as exit_context,
        ):
            __main__.main()

        self.assertEqual(exit_context.exception.code, 1)
        log_output = "\n".join(logs.output)
        self.assertIn("Pipeline failed: blocked", log_output)
        self.assertIn("--log-level DEBUG", log_output)
        self.assertNotIn("Traceback", log_output)

    def test_main_logs_exception_when_debug_enabled(self) -> None:
        with (
            mock.patch("sys.argv", ["nba_ingestion", "--log-level", "DEBUG"]),
            mock.patch("nba_ingestion.__main__.run_pipeline", side_effect=RuntimeError("blocked")),
            self.assertLogs("nba_ingestion.__main__", level="ERROR") as logs,
            self.assertRaises(SystemExit) as exit_context,
        ):
            __main__.main()

        self.assertEqual(exit_context.exception.code, 1)
        self.assertIn("Pipeline failed", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
