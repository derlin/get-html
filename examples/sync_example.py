import asyncio
import logging
import sys
import time

from get_html import HtmlRenderer

# == setup

# print debug messages from the get-html module (but not the others, as pyppeteer2 is really verbose)
logging.basicConfig(level=logging.WARNING, stream=sys.stdout)
logging.getLogger('get_html').setLevel(logging.DEBUG)

# a bunch of URLs to render
urls = ['https://twitter.com', 'https://xkcd.com', 'https://reddit.com']
start = time.time()

# create a renderer
renderer = HtmlRenderer()

# == render !

for url in urls:
    res = renderer.render(url)
    print(f' - {url} ({res.status_code}) has a content-length of {len(res.text)}')

print(f'\nCompleted all tasks in {time.time() - start :.2f} seconds:')