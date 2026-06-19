import logging
import time

LOG = logging.getLogger(__name__)


def run_loop(process_name: str) -> None:
    LOG.info("%s started", process_name)
    while True:
        time.sleep(30)
