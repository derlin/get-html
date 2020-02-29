import asyncio
from pyppeteer import launch

async def render_js(url):
    browser = await launch(headless=True) # 1
    page = await browser.newPage() # 2
    await page.setViewport({'height': 1000, 'width': 1200})
    response = await page.goto(url, waitUntil='networkidle0') # 3
    content = await page.content() # 3
    await browser.close()
    return response, content # 4

if __name__ == '__main__':
    url = 'https://twitter.com/hashtag/developer'

    loop = asyncio.get_event_loop()
    response, content = loop.run_until_complete(render_js(url))