import asyncio
import logging
import sys
import time

from get_html import HtmlRenderer

# == setup

# print debug messages from the get-html module (but not the others, as pyppeteer2 is really verbose)
logging.basicConfig(level=logging.WARNING, stream=sys.stdout)
logging.getLogger('get_html').setLevel(logging.DEBUG)

# a bunch of URLs to render asynchronously
urls = ['https://twitter.com', 'https://xkcd.com', 'https://reddit.com']
start = time.time()

# create a renderer, get hold of a loop
renderer = HtmlRenderer()
loop = asyncio.get_event_loop()

# == launch tasks

# trigger the browser creation only once, before the tasks
loop.run_until_complete(renderer.async_browser)
# render all URLs asynchronously
results = loop.run_until_complete(asyncio.gather(
    *[renderer.async_render(url, wait_until='load') for url in urls]
))
# close the browser once the tasks completed
loop.run_until_complete(renderer.async_close())

# == do something with the results

print(f'\nCompleted all tasks in {time.time() - start :.2f} seconds:')
for url, res in zip(urls, results):
    print(f' - {url} ({res.status_code}) has a content-length of {len(res.text)}')
