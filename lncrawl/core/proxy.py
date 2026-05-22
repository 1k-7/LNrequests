import logging

logger = logging.getLogger(__name__)

def load_proxies(proxy_file: str):
    pass

def get_a_proxy(scheme: str = "http", timeout: float = 0):
    return None

def remove_faulty_proxies(faulty_url: str):
    pass

def wait_for_first_proxy(scheme: str, timeout: float = 0):
    return False

def start_proxy_fetcher():
    logger.info("Proxy fetcher has been disabled.")

def stop_proxy_fetcher(*args, **kwargs):
    pass
