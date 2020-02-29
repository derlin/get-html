# get-html: get raw or rendered HTML (for humans)

**<p align=center>Read all the details on how I implemented this at ⇝
[Rendering-JS_a-journey](https://github.com/derlin/get-html/blob/master/blog/Rendering-JS_a-journey.md) ⇜ </p>**

This module is made for anyone needing to scrape HTML (i.e. scrape the web).

It knows how to do only one thing, but does it well: getting HTML from a web page. The kind of HTML is up to you. Either:

* the **raw HTML**, directly from the server or,
* the **rendered HTML**, after JS/AJAX calls.

Moreover, it is made such that you can use a unique method throughout your project, 
and switch between the two behaviors at launch by setting an environment variable.

**<p align=center>Read all the details on how I implemented this at ⇝
[Rendering-JS_a-journey](https://github.com/derlin/get-html/blob/master/blog/Rendering-JS_a-journey.md) ⇜ </p>**

## JsRenderer: a class to seamlessy render a page

`JsRenderer` handles all the specific `pyppeteer` stuff for you. It is also thread-safe.

Here is a typical usage:

```python
from get_html import JsRenderer

renderer = JsRenderer()
try:  
    # use the renderer. The underlying browser will be instantiated on first call to render.
    response = renderer.render(url='https://xkcd.com')
    html = response.text # or resposne.content to get the raw bytes
    # ... etc.
finally:
    # close the underlying browser
    renderer.close()
```

Or simply use a context manager:
```python
from get_html import create_renderer

with create_renderer() as renderer:  
    # use the renderer. The underlying browser will be instanciated on first call to render
    response = renderer.render(url='https://xkcd.com')
    html = response.text # or resposne.content to get the raw bytes

# here, the underlying browser will be closed
```

## do_get: seemlessly switch between behaviors

```python
from get_html.env_defined_get import do_get

response = do_get('https://xkcd.com')
assert response.status_code == 200

html_bytes = response.content
html_string = response.text
```

The actual behavior of `do_get` will depend on the environment variable `RENDER_JS`:

* `RENDER_JS=[1|y|true|on]`: `do_get` will launch a chromium instance under the hood and render the page (rendered HTML)
* `RENDER_JS=<anything BUT 2>` (default): `do_get` will forward the call to `requests.get` (raw HTML). 
  Do **NOT** use `2` before reading through the multi-threading section.

If rendering support is on, a browser instance will be launched **on module load**, and will be kept alive throughout the life of the application.
Keep that in mind if you have low-memory (chromium !!).

## Multi-threading

`JsRenderer` is thread-safe.

For `do_get` with rendering support, there are two possibilities.

1. Create **only one browser**, shared by all threads. In this case, only one thread can execute `render` at a time (locking mechanism);
2. Create **one browser per thread**. In this case, threads can render in parallel. But be careful, each time a new thread calls `do_get`,
  *a new browser is launched*, that will keep running until the end of the program (or until you call `get_html.env_defined_get.close()`).

Enable mode (2) by setting `RENDER_JS=2`. But again, ensure you don't have too many threads, since chromium needs a lot of memory.

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