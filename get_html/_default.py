from enum import IntEnum

import requests

#: Default user-agent if not overriden
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.89 Safari/537.36'
#: Timeout used in requests.get
GET_TIMEOUT = 60
#: Timeout used when rendering page using requests-html
RENDER_TIMEOUT = 60


class Modes(IntEnum):
    """Available modes"""
    DEFAULT = 0
    RENDER_JS_MONO = 1
    RENDER_JS_MULTI = 2


#: Environment variable to switch between Modes
ENV_VARIABLE = 'RENDER_JS'


def default_get(url, headers=None, timeout=GET_TIMEOUT) -> requests.Response:
    if headers is None:
        headers = dict()
    headers.setdefault('User-Agent', DEFAULT_USER_AGENT)

    # ignore SSL certificates
    resp = requests.get(url, verify=False, stream=True, headers=headers, timeout=timeout)
    # this triggers content decoding, thus can generate ContentDecodingError
    _ = resp.content
    return resp
