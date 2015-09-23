import logging
import time
from grab.proxylist import ProxyList

from wkit import Browser


def main(**kwargs):
    pl = ProxyList()
    pl.load_file('/web/proxy-us.txt')
    proxy = pl.get_random_proxy()
    logging.basicConfig(level=logging.DEBUG)

    br = Browser(gui=False)
    doc = br.go('http://formyip.com', proxy=proxy.get_address())
    print(doc.select('//title').text())
