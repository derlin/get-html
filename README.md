# get-html: get raw or rendered HTML (for humans)

**<p align=center>Read all the details on how I started implementing this at ⇝
[Rendering-HTML_a-journey](https://github.com/derlin/get-html/blob/master/blog/Rendering-HTML_a-journey.md) ⇜ </p>**

This module is made for anyone needing to scrape HTML (i.e. scrape the web).

It knows how to do only one thing, but does it well: getting HTML from a web page. The kind of HTML is up to you. Either:

* the **raw HTML**, directly from the server or,
* the **rendered HTML**, after JS/AJAX calls.

Moreover, it is made such that you can use a unique method throughout your project, 
and switch between the two behaviors at launch by setting an environment variable.

## HtmlRenderer: a class to seamlessly render a page

`HtmlRenderer` handles all the specific `pyppeteer` stuff for you. It is also thread-safe.

### "sync" usage 

Here is a **typical usage**:

```python
from get_html import HtmlRenderer

renderer = HtmlRenderer()
try:  
    # use the renderer. The underlying browser will be instantiated on first call to render.
    response = renderer.render(url='https://xkcd.com')
    html = response.text # or resposne.content to get the raw bytes
    # ... etc.
finally:
    # close the underlying browser
    renderer.close()
```

Or simply use a **context manager**:
```python
from get_html import create_renderer

with create_renderer() as renderer:  
    # use the renderer. The underlying browser will be instanciated on first call to render
    response = renderer.render(url='https://xkcd.com')
    html = response.text # or resposne.content to get the raw bytes

# here, the underlying browser will be closed
```

If you need to **manipulate the page** before getting the content, pass an *async* function to `render`.
It will be called after the page loaded, but before the HTML content is fetched.
For example:
```python
from get_html import create_renderer

async def scroll_to_end(page):
    # https://github.com/miyakogi/pyppeteer/issues/205#issuecomment-470886682
    await page.evaluate('{window.scrollBy(0, document.body.scrollHeight);}')

with create_renderer() as renderer: 
    response = renderer.render('https://9gag.com', manipulate_page_func=scroll_to_end)
```

### "async" usage 

All public methods have an *async* counterpart. When using *async*, however, you need to ensure that

1. the browser is created once,
2. the browser is closed once.
 
By default, the browser is launched upon first use, usually on the first call of `render`. 
When using *async*, this may be a problem, as multiple coroutine will try to create the browser multiple times.
To avoid this, ensure you trigger the browser creation *before* launching the other tasks (same for closing, wait for all tasks to complete).

A concrete example is available in
[examples/async_example.py](https://github.com/derlin/blob/master/examples/async_example.py). Here is the gist:

```python
import asyncio
from get_html import HtmlRenderer

loop = asyncio.get_event_loop()
renderer = HtmlRenderer()

# trigger the browser creation only once, before the tasks
loop.run_until_complete(renderer.async_browser)

# .. TASKS WITH RENDERING CALLS ... 
#    e.g. loop.run_until_complete(someRenderingTask())

# finally close the browser once the tasks completed
loop.run_until_complete(renderer.async_close())
```

## do_get: seemlessly switch between behaviors

```python
from get_html.env_defined_get import do_get

response = do_get('https://xkcd.com')
assert response.status_code == 200

html_bytes = response.content
html_string = response.text
```

The actual behavior of `do_get` will depend on the environment variable `RENDER_HTML`:

* `RENDER_HTML=[1|y|true|on]`: `do_get` will launch a chromium instance under the hood and render the page (rendered HTML)
* `RENDER_HTML=<anything BUT 2>` (default): `do_get` will forward the call to `requests.get` (raw HTML). 
  Do **NOT** use `2` before reading through the multi-threading section.

If rendering support is on, a browser instance will be launched **on module load**, and will be kept alive throughout the life of the application.
Keep that in mind if you have low-memory (chromium !!).

## Multi-threading

`HtmlRenderer` is thread-safe.

For `do_get` with rendering support, there are two possibilities.

1. Create **only one browser**, shared by all threads. In this case, only one thread can execute `render` at a time (locking mechanism);
2. Create **one browser per thread**. In this case, threads can render in parallel. But be careful, each time a new thread calls `do_get`,
  *a new browser is launched*, that will keep running until the end of the program (or until you call `get_html.env_defined_get.close()`).

Enable mode (2) by setting `RENDER_HTML=2`. But again, ensure you don't have too many threads, since chromium needs a lot of memory.

## Running tests

On Windows/Linux:
```bash
pip install tox
tox
```

On Mac (see https://github.com/tox-dev/tox/issues/1485):
```bash
pip install "tox<3.7"
tox
```

## Common errors

**`libXX not found` (Linux)**

See [issue #290 of puppeteer](https://github.com/puppeteer/puppeteer/issues/290#issuecomment-480247488)

```bash
sudo apt-get install gconf-service libasound2 libatk1.0-0 libatk-bridge2.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget
``` 