from contextlib import contextmanager
import os
from get_html import Modes, ENV_VARIABLE
from importlib import reload


@contextmanager
def load_doget_module(render_js=0):
    import get_html.env_defined_get as hg
    os.environ[ENV_VARIABLE] = str(int(render_js))
    hg = reload(hg)
    try:
        yield hg
    finally:
        if hasattr(hg, '_RENDERER'):
            for r in hg._RENDERER.values():
                r.close()
