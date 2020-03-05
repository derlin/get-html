# module crawler_utils.py
# now, crawlers should use do_get(url) instead of requests.get(url)
import os

__all__ = ['do_get']

if os.getenv('RENDER_HTML', '0').lower().strip() in ['0', 'false', 'no', 'n', 'off']:
    # no environment variable, or turned off => regular requests call
    import requests


    def do_get(url, **kwargs):
        return requests.get(url)

else:
    # env variable is set => render HTML is ON!
    try:
        # import what we need, and tell the user what to do if it fails
        from requests_html import HTMLSession  # or something else
    except ModuleNotFoundError:
        print('Error: RENDER_HTML set but requests_html not found.'
              'Please, run pip install requests_html')
        exit(1)

    # define the function that uses requests-html
    _session = HTMLSession()


    def do_get(url, **kwargs):
        r = _session.get(url)
        r.html.render()
        # replace server content with the rendered one
        r._content, r.encoding = r.html.raw_html, 'utf-8'
        return r

if __name__ == '__main__':
    import sys

    r = do_get(sys.argv[1]) # url as first argument
    print(f'{url} => content of size {len(r.text)}.')

