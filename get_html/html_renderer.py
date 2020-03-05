import asyncio
import datetime
import logging
import threading
from contextlib import contextmanager
from http.client import responses as http_client_responses

import pyppeteer
import requests

logger = logging.getLogger(__name__)

from ._default import RENDER_TIMEOUT, GET_TIMEOUT, default_get


@contextmanager
def create_renderer(*args, **kwargs):
    """
    Create a renderer for use in a with statement. The arguments will be passed as-is to the constructor.
    Usage:
    >>> with create_renderer() as renderer:
    >>>     # use renderer
    >>>     resp = renderer.render('https://some-url.com')
    """
    renderer = HtmlRenderer(*args, **kwargs)
    try:
        yield renderer
    finally:
        renderer.close()


class HtmlRenderer:

    def __init__(self, loop=None, headless=True, ignoreHTTPSErrors=True, browser_args=['--no-sandbox']):
        """
        Create a JsRenderer, which manages one browser instance in headless mode.
        Important:
        * for non-async methods, only one call will be processed at a time (threading.Lock);
        * do not forget to call `close` in order to properly shutdown the browser.

        :param loop: the asyncio loop to use. If None, a new loop will be created.
        :param headless: launch the browser in headless mode
        :param ignoreHTTPSErrors: turn off HTTPS certificates validation
        :param browser_args: additional arguments passed to the browser at launch
        """
        self.loop = loop or asyncio.new_event_loop()  # with new, the loop will be attached to the thread calling init
        self._browser_args = dict(headless=headless, ignoreHTTPSErrors=ignoreHTTPSErrors, args=browser_args)
        self.__browser = None
        self.__lock = threading.Lock()

    @property
    async def async_browser(self):
        if self.__browser is None:
            logger.debug('launching browser')
            self.__browser = await pyppeteer.launch(
                # avoid exception "signal only works in main thread"
                # see https://stackoverflow.com/a/54030151
                handleSIGINT=False, handleSIGTERM=False, handleSIGHUP=False,
                devtools=False,
                # if not set, will freeze after ~12 requests
                # see https://github.com/miyakogi/pyppeteer/issues/167#issuecomment-442389039
                # note that another way to avoid too much output AND the bug is to change line 165 of
                # pyppeteer's launcher.py:
                #    options['stderr'] = subprocess.DEVNULL # vs subprocess.STDOUT
                dumpio=True, logLevel='ERROR',
                **self._browser_args)
        return self.__browser

    @property
    def browser(self):
        if not hasattr(self, "_browser"):
            self.__browser = self.loop.run_until_complete(self.async_browser)
        return self.__browser

    async def async_render(self, url, timeout=RENDER_TIMEOUT, wait_until='networkidle0', manipulate_page_func=None,
                           **kwargs):
        """
        Render a URL in a browser, then get the rendered HTML after JS DOM manipulation.
        :param url: the URL to render
        :param timeout: maximum time, in seconds, before giving up
        :param wait_until: see
        [`puppeteer.Page.goto`'s waitUntil](https://pptr.dev/#?product=Puppeteer&version=v2.1.1&show=api-pagegotourl-options)
        :param manipulate_page_func: an async function taking page as a parameter,
         if you need to do something such as scroll or evaluate a custom JS before getting content.
        :param kwargs: additional arguments passed to pyppeteer's Page.goto method
        :return: a `requests.Response`, with `content` set to the rendered raw HTML. The other fields should match
        the usual `Response`, except `cookies` which will always be `None`.
        """
        page, browser = None, None
        logger.debug(f'{url}: starting async render')

        try:
            browser = await self.async_browser
            start = datetime.datetime.now()
            page = await browser.newPage()
            # Make the page a bit bigger (height especially useful for sites like twitter)
            await page.setViewport({'height': 1000, 'width': 1200})
            try:
                # Load the given page (GET request, obviously.)
                response = await page.goto(url, timeout=timeout * 1000, waitUntil=wait_until, **kwargs)
            except pyppeteer.errors.TimeoutError:
                logger.info(f'{url}: timeout error on {wait_until}. Trying domcontentloaded...')
                # Try again if the navigation failed, only waiting for dom this time
                response = await page.goto(url, timeout=timeout * 1000, waitUntil='domcontentloaded', **kwargs)

            if response is None:
                # shouldn't happen, but ... see https://github.com/miyakogi/pyppeteer/issues/299
                logger.warning(f'{url}: response is None !')
                return None

            if manipulate_page_func is not None:
                await manipulate_page_func(page)
                await asyncio.sleep(0.2)  # ensure the changes have time to be "applied" (e.g. scroll)

            # Return the content of the page, JavaScript evaluated.
            content = await page.content()
            logger.debug(f'{url}: status={response.status}')
            return self._create_response(response, content, datetime.datetime.now() - start)

        except pyppeteer.errors.TimeoutError:
            logger.warning(f'{url}: timeout error (final).')
            return None
        except pyppeteer.errors.NetworkError as e:
            if browser and browser.process.poll() is not None:
                logger.warning(f'{url}: browser process is dead. Restarting')
                # the chromium process was killed...
                # close the browser so it is recreated on next call
                await self.async_close()
            raise e
        finally:
            if page:  # avoid leaking pages !!
                await page.close()

    def render(self, url, **kwargs):
        """
        Sync version of `async_render`
        :param url: the URL
        :param kwargs: see `async_render`
        :return: a `requests.Response`, with the content reflecting the HTML after the rendering.
        """
        with self.__lock:
            response = self.loop.run_until_complete(self.async_render(url=url, **kwargs))
            if response is None:
                # May happen on incorrect gzip encoding ... see https://github.com/miyakogi/pyppeteer/issues/299
                # Since I am not sure it is always the reason, back to requests which provides good
                # exception messages, such as:
                #    (Received response with content-encoding: gzip, but failed to decode it.',
                #     error('Error -3 while decompressing data: incorrect header check'))
                return default_get(url, headers=None, timeout=kwargs.get('timeout', GET_TIMEOUT))
            return response

    def _create_response(self, response, content, elapsed=None, with_history=True):
        # Create requests.Response and try to make the fields match what you would expect when using
        # requests directly. The only attributes not updated are: cookies
        resp = requests.Response()
        # url and content
        resp.url = response.url
        resp._content, resp.encoding = content.encode('utf-8'), 'utf-8'
        # headers
        resp.headers.update(response.headers)
        # status
        resp.status_code = response.status
        resp.reason = http_client_responses[response.status]  # requests.status_codes._codes[resp.status_code][0]
        # history
        if with_history:
            resp.history = [
                self._create_response(req.response, "", with_history=False)  # avoid endless recursion
                for req in response.request.redirectChain]
        # time elapsed
        resp.elapsed = elapsed if elapsed is not None else datetime.timedelta(0)
        return resp

    async def async_close(self):
        if self.__browser is not None:
            logger.debug('closing browser')
            await self.__browser.close()
        self.__browser = None

    def close(self):
        """
        Close the browser instance, if any.
        :return:
        """
        with self.__lock:
            self.loop.run_until_complete(self.async_close())
