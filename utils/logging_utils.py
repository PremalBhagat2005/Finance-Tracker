import logging
from rich.console import Console
from rich.logging import RichHandler

def setup_logging(logger_name: str) -> logging.Logger:
    console = Console()
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    logger = logging.getLogger(logger_name)
    return logger


logger = setup_logging("finance_tracker")
