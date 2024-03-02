"""DeferredError class taken from PIL._util.py file."""


class DeferredError:  # pylint: disable=too-few-public-methods
    """Allow failing import when using it in the client mode, without `app` dependencies."""

    def __init__(self, ex):
        self.ex = ex

    def __getattr__(self, elt):
        raise self.ex
