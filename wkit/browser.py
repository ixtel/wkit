"""
Credits:
* https://code.google.com/p/webscraping/source/browse/webkit.py
* https://github.com/jeanphix/Ghost.py/blob/master/ghost/ghost.py
"""
from PyQt4.QtCore import (QEventLoop, QUrl, QTimer, QByteArray,
                          QSize, qInstallMsgHandler, QtDebugMsg, QtWarningMsg,
                          QtCriticalMsg, QtFatalMsg)
from PyQt4.QtGui import QApplication
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtNetwork import (QNetworkAccessManager, QNetworkRequest,
                             QNetworkCookieJar, QNetworkCookie)
import logging
from six.moves.urllib.parse import urlsplit, urljoin
from collections import Counter
from random import choice
import time

from wkit.network import WKitNetworkAccessManager
from wkit.error import (WKitError, InternalError,
                        HttpStatusNotSuccess, WaitTimeout)
from wkit.logger import configure_logger
from wkit.response import HttpResponse
import wkit

logger = logging.getLogger('wkit')
logger_response = logging.getLogger('wkit.network.response')
DEFAULT_USER_AGENT = 'WKit %s' % wkit.__version__
DEFAULT_WAIT_TIMEOUT = 10
DEFAULT_PAGE_LOAD_TIMEOUT = 10


class QTMessageProxy(object):
    def __init__(self, logger):
        self.logger = logger

    def __call__(self, msgType, wtf, msg):
        #print('1)', msgType)
        #print('2)', msg)
        #print('3)', zz)
        levels = {
            QtDebugMsg: 'debug',
            QtWarningMsg: 'warn',
            QtCriticalMsg: 'critical',
            QtFatalMsg: 'fatal',
        }
        getattr(self.logger, levels[msgType])(msg)


qt_logger = configure_logger('qt', 'QT', logging.DEBUG, logging.StreamHandler())
qInstallMsgHandler(QTMessageProxy(qt_logger))


class WKitWebView(QWebView):
    def setApplication(self, app):
        self.app = app

    def closeEvent(self, event):
        self.app.quit()

    def sizeHint(self):
        viewport_size = (800, 600)
        return QSize(*viewport_size)


class WKitWebPage(QWebPage):
    user_agent = None

    def set_user_agent(self, ua):
        self.user_agent = ua

    def userAgentForUrl(self, url):
        return self.user_agent

    def shouldInterruptJavaScript(self):
        return True

    def javaScriptAlert(self, frame, msg):
        logger.error('JS ALERT: %s' % msg) 
    def javaScriptConfirm(self, frame, msg):
        logger.error('JS CONFIRM: %s' % msg)

    def javaScriptPrompt(self, frame, msg, default):
        logger.error('JS PROMPT: %s' % msg)

    def javaScriptConsoleMessage(self, msg, line_number, src_id):
        logger.error('JS CONSOLE MSG: %s' % msg)


class Browser(object):
    _app = None

    def __init__(self, gui=False, traffic_rules=None):
        if not Browser._app:
            Browser._app = QApplication([])

        self.manager = WKitNetworkAccessManager(traffic_rules=traffic_rules)
        self.manager.finished.connect(self.handle_finished_network_reply)

        self.cookie_jar = QNetworkCookieJar()
        self.manager.setCookieJar(self.cookie_jar)

        self.page = WKitWebPage()
        self.page.setNetworkAccessManager(self.manager)

        self.view = WKitWebView()
        self.view.setPage(self.page)
        self.view.setApplication(Browser._app)
        self.view.loadFinished.connect(self.handle_page_load_finished)

        self._response = None

        if gui:
            self.view.show()


    def get_cookies(self):
        return self.cookie_jar.allCookies()

    def get_simple_cookies(self):
        res = {}
        for cookie in self.cookie_jar.allCookies():
            key = cookie.name().data().decode('latin')
            val = cookie.value().data().decode('latin')
            res[key] = val 
        return res

    def go(self, url, **kwargs):
        return self.request(url=url, **kwargs)

    def request(self, url=None, user_agent=None, cookies=None,
                timeout=DEFAULT_PAGE_LOAD_TIMEOUT,
                referer=None, method='get', data=None,
                headers=None, proxy=None, wait=True):
        # Reset things bound to previous response
        self._response = None
        self.resource_list = []
        self.page_loaded = False
        #self.view.setHtml('', QUrl('blank://'))

        # Proxy
        if proxy:
            self.manager.setup_proxy(proxy)

        # User-Agent
        if user_agent is None:
            user_agent = DEFAULT_USER_AGENT
        self.page.set_user_agent(user_agent)

        # Cookies
        if cookies is None:
            cookies = {}
        cookie_obj_list = []
        for name, value in cookies.items():
            domain = ('.' + urlsplit(url).netloc).split(':')[0]
            #print 'CREATE COOKIE %s=%s' % (name, value)
            #print 'DOMAIN = %s' % domain
            cookie_obj = QNetworkCookie(name, value)
            cookie_obj.setDomain(domain)
            cookie_obj_list.append(cookie_obj)
        #self.cookie_jar.setAllCookies(cookie_obj_list)

        # HTTP Method
        method_obj = getattr(QNetworkAccessManager, '%sOperation'
                             % method.capitalize())
        # Ensure that Content-Type is correct if method is post
        if method == 'post':
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        # POST Data
        if data is None:
            data = QByteArray()

        # Build Request object
        req = QNetworkRequest(QUrl(url))

        # Referer
        if referer:
            req.setRawHeader('Referer', referer)

        # Headers
        if headers is None:
            headers = {}
        for name, value in headers.items():
            req.setRawHeader(name, value)
        self.content_type_stats = Counter()
        
        # Spawn request
        self.view.load(req, method_obj, data)

        if wait:
            self.wait_for_page_loaded(timeout=timeout)
            return self.get_page_response()
        else:
            return None

    def sleep(self, sleep_time):
        start = time.time()
        while time.time() < start + sleep_time:
            time.sleep(0.01)
            self._app.processEvents()

    def wait_for(self, event, timeout_msg='Time is up!',
                 timeout=None):
        if timeout is None:
            timeout = DEFAULT_WAIT_TIMEOUT
        start = time.time()
        while not event():
            if time.time() > start + timeout:
                raise WaitTimeout(timeout_msg)
            self.sleep(0.1)

    def wait_for_page_loaded(self, timeout=None):
        self.wait_for(lambda: self.page_loaded,
                      'Unable to load the page', timeout)

    def wait_for_element(self, query, timeout=None):
        self.wait_for(lambda: self.element_exists(query),
                      'Can\'t find element: %s' % query,
                      timeout)

    def get_url(self):
        return self.page.mainFrame().url().toString()\
                   .split('#')[0].rstrip('/')

    def wait_for_response(self, timeout=None):
        self._response = None

        def event():
            url = self.get_url()
            for res in self.resource_list:
                if url == res.url.rstrip('/'):
                    self._response = res
                    return True
            return False

        self.wait_for(event, 'Can\'t find response associated'
                             ' with current web document: %s' % self.get_url(),
                      timeout)
        return self._response

    def get_page_response(self):
        if self._response:
            return self._response
        else:
            url = self.page.mainFrame().url().toString()\
                      .split('#')[0].rstrip('/')
            for res in self.resource_list:
                print('TEST', url, res.url.rstrip('/'))
                if url == res.url.rstrip('/'):
                    self._response = res
                    return res

        print('Resource list:')
        for res in self.resource_list:
            print(' * %s' % res.url)
        print('Current page URL: %s' % self.page.mainFrame().url().toString())
        raise InternalError('Could not associate any of loaded responses'
                            ' with requested URL: %s' % url)

    def handle_page_load_finished(self):
        self.page_loaded = True

    def handle_finished_network_reply(self, reply):
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status_code:
            if not isinstance(status_code, int):
                status_code = status_code.toInt()[0]
            logger_response.debug('HttpResource [%d]: %s' % (status_code,
                                                             reply.url().toString()))
            self.resource_list.append(HttpResponse.build_from_reply(reply))
            ctype = reply.rawHeader('Content-Type').data()\
                         .decode('latin').split(';')[0]
            self.content_type_stats[ctype] += 1

    def assert_ok_response(self):
        if self.get_page_response().status_code != 200:
            raise HttpStatusNotSuccess

    def get_html(self):
        return self.page.mainFrame().toHtml()

    def get_doc(self):
        return self.page.mainFrame().documentElement()

    def get_element(self, query):
        elem = self.get_doc().findFirst(query)
        if elem.isNull():
            raise IndexError('Could not find element: %s' % query)
        else:
            return elem

    def element_exists(self, query):
        try:
            self.get_element(query)
        except IndexError:
            return False
        else:
            return True

    def find_elements(self, query):
        return self.get_doc().findAll(query)

    def get_base_url(self):
        try:
            base = self.get_element('base[href]')
        except IndexError:
            return self.get_page_response().url
        else:
            url = base.attribute('href')
            return url or self.get_page_response().url

    def get_random_int_link(self):
        base_url = self.get_base_url()
        base_host = urlsplit(base_url).hostname
        links = []
        for elem in self.find_elements('a[href]'):
            url = urljoin(base_url, elem.attribute('href'))
            host = urlsplit(url).hostname
            if host == base_host:
                if url != self.get_page_response().url:
                    links.append(url)
            if len(links) > 50:
                break
        if links:
            return choice(links)
        else:
            return None
