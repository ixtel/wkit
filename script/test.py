import logging
import time
from grab.proxylist import ProxyList
from multiprocessing import Process

from wkit import Browser

GUI = 0


def click(url=None, proxy=None):
    traffic_rules = {
        'reject_url': [],
        'reject_path': [],
        #'abort_content_type': ['image/*'],
    }
    br = Browser(gui=GUI, traffic_rules=traffic_rules)
    doc = br.go(url, timeout=20, proxy=proxy)
    try:
        print(doc.select('//title').text())
    except Exception as ex:
        logging.error('', exc_info=ex)
    print(br.content_type_stats)


def main(**kwargs):
    logging.basicConfig(level=logging.DEBUG)

    pl = ProxyList()
    pl.load_file('/web/proxy-us.txt')
    proxy = pl.get_random_proxy()

    urls = [
        'http://jabbim.com',
    ]

    pool = []
    for url in urls:
        pro = Process(target=click, kwargs={'url': url,
                                            'proxy': proxy.get_address()})
        pro._start_time = time.time()
        pro.daemon = True
        pro.start()
        pool.append(pro)

    TIMEOUT = None
    while True:
        if not pro.is_alive():
            break
        else:
            time.sleep(0.5)
            if TIMEOUT and time.time() - pro._start_time > TIMEOUT:
                pro.terminate()
