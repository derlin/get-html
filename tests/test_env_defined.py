import threading

import pytest
import pytest_check as check

from . import load_doget_module
from get_html import Modes

urls = ['https://twitter.com', 'https://reddit.com', 'https://xkcd.com', 'https://amazon.de']
n = 2


@pytest.mark.parametrize('mode', Modes)
def test_modes(mode):
    with load_doget_module(mode) as hg:
        check.is_true(hg.mode == mode)
        r = hg.do_get('https://twitter.com')
        check.is_true(r.status_code == 200)


class Worker(threading.Thread):

    def __init__(self, urls, mode):
        super().__init__()
        self.urls, self.mode = urls, mode

    def run(self):
        from get_html.env_defined_get import do_get, mode
        check.is_true(mode == self.mode)
        for u in self.urls:
            try:
                r = do_get(u)
                check.is_true(r.status_code == 200, u)
            except Exception as e:
                check.is_true(False, e)


@pytest.mark.parametrize('mode', [Modes.RENDER_HTML_MONO, Modes.RENDER_HTML_MULTI])
def test_threads(mode):
    with load_doget_module(mode) as hg:
        # create an run threads
        workers = [Worker(urls[i::n], mode) for i in range(n)]
        for w in workers:  w.start()
        for w in workers: w.join()
        # ensure we have one renderer assigned to each thread
        all_renderers = list(hg._RENDERER.values())
        assert len(all_renderers) == 2
        # ensure the renderers shared/not shared between threads depending on mode
        assert (all_renderers[0] == all_renderers[1]) == (mode == Modes.RENDER_HTML_MONO)
