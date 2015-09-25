import logging
'''
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWebKitWidgets import QWebFrame
from PyQt5.QtCore import QByteArray
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest
'''
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkProxy
from PyQt4.QtWebKit import QWebFrame
from PyQt4.QtCore import QByteArray, QUrl
import six
from fnmatch import fnmatch
from copy import copy
from urllib.parse import urlsplit
import zlib
import itertools

from wkit.const import NETWORK_ERRORS
from wkit.error import WKitError
from wkit.logger import log_errors

logger = logging.getLogger('wkit.network')
logger_rules = logging.getLogger('wkit.network.rules')
REQ_COUNTER = itertools.count(1)


@log_errors
def handle_reply_ready_read(reply, traffic_rules):
    ct = reply.rawHeader('Content-Type').data().decode('latin')
    abort_ctype = traffic_rules.get('abort_content_type', [])
    if any(fnmatch(ct, x) for x in abort_ctype):
        logger_rules.debug('ABORT REPLY %s' % reply.url().toString())
        reply.abort()
    else:
        if not hasattr(reply, 'data'):
            reply.data = b''
        reply.data += reply.peek(reply.bytesAvailable())


class WKitNetworkAccessManager(QNetworkAccessManager):
    @log_errors
    def __init__(self, traffic_rules=None):
        if traffic_rules is None:
            self.traffic_rules = {}
        else:
            self.traffic_rules = traffic_rules
        QNetworkAccessManager.__init__(self)

    @log_errors
    def setup_cache(self, size=100 * 1024 * 1024, location='/tmp/.webkit_wrapper'):
        QDesktopServices.storageLocation(QDesktopServices.CacheLocation)
        cache = QNetworkDiskCache()
        cache.setCacheDirectory(location)
        cache.setMaximumCacheSize(size)
        self.setCache(cache)

    @log_errors
    def setup_proxy(self, proxy, proxy_userpwd=None, proxy_type='http'):
        if proxy_userpwd:
            username, password = proxy_userpwd.split(':', 1)
        else:
            username, password = '', ''
        host, port = proxy.split(':', 1)
        if proxy_type == 'http':
            proxy_type_obj = QNetworkProxy.HttpProxy
        elif proxy_type == 'socks5':
            proxy_type_obj = QNetworkProxy.Socks5Proxy
        else:
            raise WKitError('Unknown proxy type: %s' % proxy_type)
        proxy_obj = QNetworkProxy(proxy_type_obj, host, int(port), username, password)
        self.setProxy(proxy_obj)

    def get_method_name(self, qt_op):
        for key in ('get', 'post', 'put', 'head', 'delete'):
            if qt_op == getattr(self, key.title() + 'Operation'):
                return key
        return 'custom'

    @log_errors
    def createRequest(self, operation, request, data):
        method = self.get_method_name(operation)
        allowed = True 
        req_url = request.url().toString()
        if req_url.startswith('data:'):
            req_url = 'data:[%s...]' % req_url[:50]

        if operation == self.GetOperation:
            if not self.is_request_allowed(request):
                request.setUrl(QUrl('forbidden://localhost/'))
                allowed = False

        if allowed:
            if self.proxy().hostName():
                suffix = ' via proxy %s:%d' % (self.proxy().hostName(),
                                               self.proxy().port())
            else:
                suffix = ''
            logger.debug('%s [%d] %s%s' % (method.upper(), next(REQ_COUNTER),
                                           req_url, suffix))
        else:
            logger_rules.debug('REJECT REQ %s' % req_url)
        
        request.setAttribute(QNetworkRequest.CacheLoadControlAttribute,
                             QNetworkRequest.PreferCache)

        #request.setRawHeader('Accept-Encoding', 'gzip')
        reply = QNetworkAccessManager.createRequest(self, operation, request, data)
        reply.error.connect(self.handle_network_reply_error)

        reply.readyRead.connect(lambda x=reply, y=copy(self.traffic_rules):\
                                handle_reply_ready_read(x, y))
        return reply

    @log_errors
    def is_request_allowed(self, request):
        url = request.url().toString() 
        path = urlsplit(url).path
        reject_url = self.traffic_rules.get('reject_url', [])
        if any(fnmatch(url, x) for x in reject_url):
            return False
        reject_path = self.traffic_rules.get('reject_path', [])
        if any(fnmatch(path, x) for x in reject_path):
            return False
        return True

    @log_errors
    def handle_network_reply_error(self, err_code):
        #if eid not in (5, 301):
        reply = self.sender()
        #err_msg = NETWORK_ERRORS.get(err_code, 'Unknown Error') 
        logger_rules.debug('FAIL [%s] %s' % (err_code, reply.url().toString()))
