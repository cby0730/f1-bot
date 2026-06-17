import logging
import sys
from unittest import mock
import pytest
import structlog

from f1_bot.utils.logging import setup_logging


@pytest.fixture
def clean_logging():
    # Save original handlers and levels
    root = logging.getLogger()
    orig_handlers = list(root.handlers)
    orig_level = root.level

    orig_httpx = logging.getLogger("httpx").level
    orig_httpcore = logging.getLogger("httpcore").level
    orig_apscheduler = logging.getLogger("apscheduler").level

    yield

    # Restore original handlers and levels
    root.setLevel(orig_level)
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in orig_handlers:
        root.addHandler(h)

    logging.getLogger("httpx").setLevel(orig_httpx)
    logging.getLogger("httpcore").setLevel(orig_httpcore)
    logging.getLogger("apscheduler").setLevel(orig_apscheduler)


def test_setup_logging_defaults(clean_logging):
    with mock.patch("structlog.configure") as mock_configure:
        setup_logging(log_level="INFO", log_format="auto")

        mock_configure.assert_called_once()
        kwargs = mock_configure.call_args[1]

        # Verify it uses stdlib bound logger and logger factory
        assert kwargs["wrapper_class"] == structlog.stdlib.BoundLogger
        assert isinstance(kwargs["logger_factory"], structlog.stdlib.LoggerFactory)

        # Verify standard root logger is configured
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 1

        # Verify httpx, httpcore, and apscheduler levels are set to WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
        assert logging.getLogger("apscheduler").level == logging.WARNING


def test_setup_logging_debug_level(clean_logging):
    # If level is DEBUG, httpx/httpcore/apscheduler should NOT be set to WARNING
    logging.getLogger("httpx").setLevel(logging.NOTSET)
    logging.getLogger("httpcore").setLevel(logging.NOTSET)
    logging.getLogger("apscheduler").setLevel(logging.NOTSET)

    with mock.patch("structlog.configure"):
        setup_logging(log_level="DEBUG", log_format="auto")

        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert logging.getLogger("httpx").level == logging.NOTSET
        assert logging.getLogger("httpcore").level == logging.NOTSET
        assert logging.getLogger("apscheduler").level == logging.NOTSET


def test_setup_logging_format_choices(clean_logging):
    with mock.patch("structlog.configure"):
        # Test JSON
        with mock.patch("structlog.stdlib.ProcessorFormatter") as mock_formatter:
            setup_logging(log_format="json")
            mock_formatter.assert_called()
            processors = mock_formatter.call_args[1].get("processors")
            assert any(isinstance(p, structlog.processors.JSONRenderer) for p in processors)

        # Test Console (pretty)
        with mock.patch("structlog.stdlib.ProcessorFormatter") as mock_formatter:
            setup_logging(log_format="console")
            mock_formatter.assert_called()
            processors = mock_formatter.call_args[1].get("processors")
            assert any(isinstance(p, structlog.dev.ConsoleRenderer) for p in processors)

        # Test Auto (non-TTY)
        with mock.patch("sys.stderr.isatty", return_value=False):
            with mock.patch("structlog.stdlib.ProcessorFormatter") as mock_formatter:
                setup_logging(log_format="auto")
                mock_formatter.assert_called()
                processors = mock_formatter.call_args[1].get("processors")
                assert any(isinstance(p, structlog.processors.JSONRenderer) for p in processors)

        # Test Auto (TTY)
        with mock.patch("sys.stderr.isatty", return_value=True):
            with mock.patch("structlog.stdlib.ProcessorFormatter") as mock_formatter:
                setup_logging(log_format="auto")
                mock_formatter.assert_called()
                processors = mock_formatter.call_args[1].get("processors")
                assert any(isinstance(p, structlog.dev.ConsoleRenderer) for p in processors)


def test_add_taiwan_timestamp():
    from f1_bot.utils.logging import add_taiwan_timestamp
    event_dict = {}
    res = add_taiwan_timestamp(None, "test", event_dict)
    assert "timestamp" in res
    # Taiwan Time ends with +08:00 (or timezone offset +08:00)
    assert "+08:00" in res["timestamp"]
