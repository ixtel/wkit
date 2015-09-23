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

from wkit.const import NETWORK_ERRORS
from wkit.error import WKitError
from wkit.logger import log_errors

logger = logging.getLogger('wkit.network')


@log_errors
def handle_reply_ready_read(reply):
    ct = reply.rawHeader('Content-Type').data().decode('latin')
    if ct.startswith('image/'):
        logger.debug('ABORTING %s' % reply.url().toString())
        reply.abort()
    else:
        if not hasattr(reply, 'data'):
            reply.data = b''
        reply.data += reply.peek(reply.bytesAvailable())


class WKitNetworkAccessManager(QNetworkAccessManager):
    @log_errors
    def __init__(self, forbidden_extensions=None):
        if forbidden_extensions is None:
            forbidden_extensions = []
        QNetworkAccessManager.__init__(self)
        self.forbidden_extensions = forbidden_extensions

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
            logger.debug('%s %s%s' % (method.upper(), req_url, suffix))
        else:
            logger.debug('FORBIDDEN %s' % req_url)
        
        request.setAttribute(QNetworkRequest.CacheLoadControlAttribute,
                             QNetworkRequest.PreferCache)
        reply = QNetworkAccessManager.createRequest(self, operation, request, data)
        reply.error.connect(self.handle_network_reply_error)
        reply.readyRead.connect(lambda x=reply: handle_reply_ready_read(x))
        return reply

    @log_errors
    def is_request_allowed(self, request):
        path = six.u(request.url().path())
        if path and '.' in path:
            ext = path.rsplit('.', 1)[-1].lower()
        else:
            ext = ''

        if ext and ext in self.forbidden_extensions:
            return False
        else:
            return True

    @log_errors
    def handle_network_reply_error(self, err_code):
        #if eid not in (5, 301):
        reply = self.sender()
        #err_msg = NETWORK_ERRORS.get(err_code, 'Unknown Error') 
        logger.error('FAIL [%s] %s' % (err_code, reply.url().toString()))
