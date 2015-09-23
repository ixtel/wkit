import logging
import time
from grab.proxylist import ProxyList
from multiprocessing import Process

from wkit import Browser

GUI = True


def click(url=None, proxy=None):
    br = Browser(gui=GUI)
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
        'http://yandex.ru/',
        'http://mail.ru/',
    ]

    pool = []
    for url in urls:
        pro = Process(target=click, kwargs={'url': url,
                                            'proxy': proxy.get_address()})
        pro.start()
        pool.append(pro)

    for pro in pool:
        pro.join()
