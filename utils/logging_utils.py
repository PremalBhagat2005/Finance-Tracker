import logging


def setup_logging(logger_name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(logger_name)
    return logger


logger = setup_logging("finance_tracker")
