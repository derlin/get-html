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
    _session.browser # will execute "self.loop = asyncio.get_event_loop()" from main

    def do_get(url, **kwargs):
        r = _session.get(url)
        r.html.render()
        # replace server content with the rendered one
        r._content, r.encoding = r.html.raw_html, 'utf-8'
        return r

if __name__ == '__main__':

    import threading

    urls = ['https://twitter.com', 'https://reddit.com']  # etc.
    num_workers = 2


    class Worker(threading.Thread):

        def __init__(self, urls):
            super().__init__()
            self.urls = urls

        def run(self):
            for u in self.urls:
                r = do_get(u)
                print(f'{threading.current_thread().name}: {u} => content of size {len(r.text)}.')


    workers = [Worker(urls) for i in range(num_workers)]

    for w in workers:
        w.start()

    for w in workers:
        w.join()
