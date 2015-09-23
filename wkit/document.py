from selection import XpathSelector
from lxml.html import fromstring
import re

from wkit.html import find_document_encoding

RE_CTYPE_CHARSET = re.compile(r'charset=([-a-zA-Z0-9]+)')


class Document(object):
    def __init__(self):
        self._dom_tree = None

    def parse(self):
        self.encoding = self.detect_encoding()

    def unicode_body(self):
        return bytes(self.body).decode(self.encoding, 'ignore')

    def live_body(self):
        return self._page.mainFrame().toHtml()

    def detect_encoding(self):
        enc = find_document_encoding(self.body)
        if not enc:
            ctype = self.headers.get('Content-Type', '')
            try:
                enc = RE_CTYPE_CHARSET.search(ctype).group(1)
            except AttributeError:
                pass
        if not enc:
            enc = 'utf-8'
        return enc

    @property
    def dom_tree(self):
        if self._dom_tree is None:
            self._dom_tree = fromstring(self.unicode_body())
        return self._dom_tree

    def select(self, xpath):
        sel = XpathSelector(self.dom_tree)
        return sel.select(xpath)
