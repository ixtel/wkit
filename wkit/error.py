class WKitError(Exception):
    pass


class InternalError(WKitError):
    pass


class NetworkTimeout(WKitError):
    pass


class HttpStatusNotSuccess(WKitError):
    pass


class WaitTimeout(WKitError):
    pass
