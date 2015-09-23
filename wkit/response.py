from selection import XpathSelector
from lxml.html import fromstring
import re
from PyQt4.QtNetwork import QNetworkRequest

from wkit.html import find_document_encoding

RE_CTYPE_CHARSET = re.compile(r'charset=([-a-zA-Z0-9]+)')


class HttpResponse(object):
    def __init__(self, url=None, status_code=None, headers=None,
                 content=None):
        self._dom_tree = None
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.setup()

    # *************
    # Class Methods
    # *************

    @classmethod
    def build_from_reply(cls, reply):
        url = str(reply.url().toString())
        status_code = reply.attribute(
            QNetworkRequest.HttpStatusCodeAttribute)
        if not isinstance(status_code, int):
            status_code = obj.status_code.toInt()[0]
        headers = {}
        for header in reply.rawHeaderList():
            headers[header.data()] = bytes(reply.rawHeader(header))
        content = cls.extract_content_from_reply(reply)
        return cls(
            url=url,
            status_code=status_code,
            headers=headers,
            content=content,
        )

    @classmethod
    def extract_content_from_reply(cls, reply):
        try:
            data = reply.data
        except AttributeError:
            data = reply.readAll()
        enc = reply.rawHeader('Content-Encoding').data().decode('latin')
        #if 'gzip' in enc:
        #    data = gzip.GzipFile(fileobj=BytesIO(data)).read()
        return bytes(data)

    # **************
    # Public Methods
    # **************

    def setup(self):
        self.encoding = self.detect_encoding()

    def detect_encoding(self):
        enc = find_document_encoding(self.content)
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
    def unicode_content(self):
        return self.content.decode(self.encoding, 'ignore')

    @property
    def dom_tree(self):
        if self._dom_tree is None:
            self._dom_tree = fromstring(self.unicode_content)
        return self._dom_tree

    def select(self, xpath):
        sel = XpathSelector(self.dom_tree)
        return sel.select(xpath)
