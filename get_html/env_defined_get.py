import logging
import os
import threading

from ._default import *

__all__ = ['do_get', 'Modes', 'mode']

logger = logging.getLogger(__name__)

if os.getenv(ENV_VARIABLE, '0').lower().strip() in ['0', 'false', 'no', 'n', 'off']:
    logger.info('using REQUESTS for scraping')
    mode = Modes.DEFAULT
    do_get = default_get


    def close():
        pass

else:
    one_browser_per_thread = os.getenv(ENV_VARIABLE, '0') == '2'
    logger.info(f'using JS_RENDERER for scraping ({"mono" if one_browser_per_thread else "multi"}-thread)')

    # == import modules

    try:
        import pyppeteer
        import asyncio
    except ModuleNotFoundError:
        print(f'Error: {ENV_VARIABLE} set but pyppeteer not found. Please, run pip install pyppeteer2')
        exit(1)

    # == define the actual do_get

    from .html_renderer import HtmlRenderer
    from collections import defaultdict

    if one_browser_per_thread:
        # each thread will create its own renderer instance
        _RENDERER = defaultdict(lambda: HtmlRenderer())
        mode = Modes.RENDER_HTML_MULTI
    else:
        # create one renderer instance, shared by all threads
        renderer = HtmlRenderer()
        _RENDERER = defaultdict(lambda: renderer)
        mode = Modes.RENDER_HTML_MONO


    def do_get(url, headers=None, timeout=RENDER_TIMEOUT) -> requests.Response:
        if headers is None:
            headers = dict()
        headers.setdefault('User-Agent', DEFAULT_USER_AGENT)
        renderer = _RENDERER[threading.current_thread().name]
        resp = renderer.render(url, timeout=timeout)

        return resp


    def close():
        """
        Close the browser assigned to the calling thread.
        Note: in case multiple threads use the same browser, nothing will happen.
        """
        if mode == Modes.RENDER_HTML_MONO and len(_RENDERER) > 1:
            pass
        else:
            _RENDERER[threading.current_thread().name].close()
