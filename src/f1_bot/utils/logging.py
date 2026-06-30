import datetime
import logging
import sys

import structlog


def add_taiwan_timestamp(logger: logging.Logger, name: str, event_dict: dict) -> dict:
    tz_taiwan = datetime.timezone(datetime.timedelta(hours=8))
    event_dict["timestamp"] = datetime.datetime.now(tz_taiwan).isoformat()
    return event_dict


def setup_logging(log_level: str = "INFO", log_format: str = "auto") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Resolve renderer based on log_format
    fmt = log_format.lower()
    if fmt == "json":
        renderer = structlog.processors.JSONRenderer()
    elif fmt in ("console", "pretty", "text"):
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:  # "auto" or fallback
        renderer = (
            structlog.dev.ConsoleRenderer()
            if sys.stderr.isatty()
            else structlog.processors.JSONRenderer()
        )

    # Configure structlog to route all log calls through standard logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_taiwan_timestamp,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging root logger to use ProcessorFormatter
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.ExtraAdder(),
            structlog.processors.add_log_level,
            structlog.stdlib.add_logger_name,
            add_taiwan_timestamp,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Quiet down noisy library logs unless global level is DEBUG
    if level >= logging.INFO:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
