import time

from wkit.error import WaitTimeout


class WaitMixin(object):
    def wait_for(self, event, timeout_msg='Time is up!',
                 timeout=None):
        from wkit.browser import DEFAULT_WAIT_TIMEOUT

        if timeout is None:
            timeout = DEFAULT_WAIT_TIMEOUT
        start = time.time()
        while True:
            result = event()
            if result:
                return result
            else:
                if time.time() > start + timeout:
                    raise WaitTimeout(timeout_msg)
                self.sleep(0.1)

    def wait_for_page_loaded(self, timeout=None):
        self.wait_for(lambda: self._page_loaded,
                      'Unable to load the page', timeout)

    def wait_for_element(self, query, timeout=None):
        self.wait_for(lambda: self.element_exists(query),
                      'Can\'t find element: %s' % query,
                      timeout)

    def wait_for_response(self, timeout=None):
        def event():
            url = self.get_url()
            for res in self.resource_list:
                if url == res.url.rstrip('/'):
                    return res

        msg = ('Can\'t find response associated'
               ' with current web document: %s' % self.get_url())
        return self.wait_for(event, msg, timeout)
