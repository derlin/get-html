# Rendering HTML: a journey

This article is an account of my development process that took place in **February 2020** (Python 3) and ended to the library in this repo.

It was a sort of detective work, going from libraries to exceptions until I had learned enough (and waisted enough time) to write the code that does exactly what I need in the proper fashion. Hope you will enjoy the journey as well.

**Libraries used in this article**

* `requests`, version 2.23.0
* `requests-html`, version 0.10.0
* `pyppeteer`, version 0.0.25
* `pyppeteer2`, version 0.2.2

**Contents**:

- [Context & motivations](#context---motivations)
- [Rendering HTML using Python](#rendering-html-using-python)
- [First implementation (requests-html)](#first-implementation--requests-html-)
  * [Make it work with threads](#make-it-work-with-threads)
    + [First problem, asyncio loop from thread](#first-problem--asyncio-loop-from-thread)
    + [Second problem, "concurrency"](#second-problem---concurrency-)
  * [Make it work in a real case scenario](#make-it-work-in-a-real-case-scenario)
    + [Exception: Target.closed](#exception--targetclosed)
    + [The program hangs](#the-program-hangs)
  * [Waiting for AJAX to load](#waiting-for-ajax-to-load)
  * [Make the environment reproducible](#make-the-environment-reproducible)
- [Screw it start again from scratch](#screw-it-start-again-from-scratch)
  * [HtmlRenderer](#jsrenderer)
    + [Threading](#threading)
    + [Wait for page load](#wait-for-page-load)
    + [Fetch more than one tweet](#fetch-more-than-one-tweet)
    + [Fallback](#fallback)
    + [Requests compatibility](#requests-compatibility)
  * [Seamlessly choose the implementation from an environment variable](#seamlessly-choose-the-implementation-from-an-environment-variable)
      - [IMPORTANT NOTICES](#important-notices)
  * [Still problems, pyppeteer2 to the rescue](#still-problems--pyppeteer2-to-the-rescue)
- [Conclusion](#conclusion)

# Context & motivations

First, let me explain the context a bit. I am currently working on an automated crawler that targets Swiss German sentences. Without going into the details, the code base quite evolved over the months and I have from the beginning tried to make it very flexible: all the "tools" in my pipeline inherit from some interface and can be chosen/configured at runtime using a yaml file. This makes it great for the user, but a nightmare for the developer.

Anyhow, the first step in crawling the web is to get the page content, that is the actual HTML from where I then extract the text. Currently, all my crawler implementations rely on [requests](https://requests.readthedocs.io/en/master/) to do this job. It is a great library which is a breeze to use. *However*, it only returns the HTML sent by the server, which is not always the same as the rendered HTML you would see in a browser. Indeed, websites these days rely more and more on AJAX calls and DOM manipulation to load text content.

The best example being Twitter: as of November 2019, you could still grasp some tweets by using a `GET https://twitter.com/#some-hashtag`. But those days are gone. If you do this now, the only text you'll get will be:

> We've detected that JavaScript is disabled in your browser.
> Would you like to proceed to legacy Twitter?
> Something went wrong, but don't fret - let's give it another shot.

So on modern websites, the only way to get the content of a page is to *actually render* the page in a browser.

# Rendering HTML using Python

I have been aware of tools such as [selenium](https://www.selenium.dev/) or [puppeteer](https://github.com/puppeteer/puppeteer) (and its unofficial python port [pyppeteer](https://miyakogi.github.io/pyppeteer/reference.html)). However, they seemed kind of hard to work with, required a lot of setup and the learning curve was just too steep for me to even try.

And then, I found [request-html](https://github.com/psf/requests-html), a library based on pyppeteer, 
which is supposed to do all the heavy-lifting for us.
From their README, rendering a page and getting the content seemed as easy as:

```python
from requests_html import HTMLSession
sessions = HTMLSession()
r = session.get('https://pythonclock.org')
r.html.render() # maagic !!
r.html # <= rendered dom, yeah
```

Seeing how easy it is, I had to make the jump and finally implement this in my pipeline.

# First implementation (requests-html)

OK, so the integration should be easy peasy. At that time, the biggest question to me was how to implement it. I want the user to have the choice, but I don't want to alter my crawlers too much. Also, I already have a hierarchy of classes for the crawlers. Adding an option to the constructor means changing every child... Also, I don't want to force users to install heavy libraries such as pyppeteer if they don't need them. So for now let's be simple:

1. Instead of calling `requests.get` in the crawler, call a function `do_get` defined in a new module
2. In this new module, `crawler_utils` use a big if that will define `do_get` using `requests-html` (and do the necessary imports) only if some environment variable is set. If not, silently fallback to the default `requests` call.
3. Since `requests_html` is an optional dependency, put the module import in a try-catch and give the user a meaningful message if the module is not found.

So, my brand new `crawler_utils` module looks a bit like that (most basic version, see `00-crawler_utils.py`):

```python
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
        r._content = r.html.raw_html  # replace server content with the rendered one
        return r
```

Great: when I launch my pipeline on my machine using the "dev" settings (no threads, just a small bunch of URLs to crawl),  it works like a charm. Me happy.

## Make it work with threads

I implemented and tested the code, now let's see in "production". First, let's launch the pipeline using multiple workers (implemented using threads):

> RuntimeError: There is no current event loop in thread 'Thread-X'.\
> RuntimeError: There is no current event loop in thread 'Thread-Y'.\
> ...

### First problem, asyncio loop from thread

Not really familiar with the whole asyncio stuff, I google a bit and find an issue in requests-html exactly about that: 
[Issue Rendering Javascript in a Thread](https://github.com/psf/requests-html/issues/155). 
In [this helpful comment](https://github.com/psf/requests-html/issues/155#issuecomment-377723137), it seems to be related to the `asyncio.get_event_loop`  call made on the first instantiation of the underlying browser. This call only works from the main thread.
One way to get around is thus to trigger the creation of the browser in the main thread by calling `.browser`. Let's try (see `01-crawler_utils.py`):

```python
# in crawler_utils.py, in the definition (the module is loaded by the main thread)
# define the function that uses requests-html
_session = HTMLSession()
_session.browser # will execute "self.loop = asyncio.get_event_loop()" from main

# def do_get() ...
```

and ... ? Yes, the error disappears, but now we have a new problem:

> RuntimeError: This event loop is already running

### Second problem, "concurrency"

OK, so now the problem is multiple threads try to use the same event loop at the same time, which can only handle one at a time (in sync mode). As an easy way out, let's add some locking mechanism using `threading.Lock`, as shown in `02-crawler_utils.py`:

```python
# in crawler_utils.py, in the definition (the module is loaded by the main thread)
# define the function that uses requests-html
_session = HTMLSession()
_session.browser # trigger the browser creation

import threading
lock = threading.Lock()

def do_get(url, **kwargs):
    try: 
        _lock.acquire()
        r = _session.get(url)
        r.html.render()
        r._content = r.html.raw_html  # replace server content with the rendered one
        return r
    finally:
        _lock.release()
```

Note that now, there is no concurrency at all while fetching HTTP resources, so the threads are useless except if we have other significant IO task down the pipeline (which I do). Also, now one problematic URL may potentially block the whole program for several minutes, until it reaches a timeout... But at least it works, or does it ?

## Make it work in a real case scenario

Now, my next move is to actually run my crawler in "production" using my new piece of code. I thus deploy the changes to the server, launch the crawler and everything seems to work. I relax and go get a coffee. However, when I go back, my logs show this dreaded exception for each visited URL:

> [INFO] XX failed. Exception: pyppeteer.errors.NetworkError: Protocol error Target.createTarget: Target closed.

### Exception: Target.closed

Googling this error, I find this exact [issue in pyppeteer's repo](https://github.com/miyakogi/pyppeteer/issues/234#issuecomment-518215288), posted in July, 2019: "*This [Target closed] error is escalated when multiple tasks are performed asynchronously，when there's only one URL in it, it's okay to scrapy.*" Another user reports, "*I am facing the same issue when i access 3 links one after other and always happens with the 3rd link irrespective of what url it is.*"  So, does it mean my efforts were in vain ? That pyppeteer, and thus requests-html, is unusable in a crawler environment ?

Well, fortunately, the [last comment of the thread](https://github.com/miyakogi/pyppeteer/issues/234#issuecomment-518215288) gives me hope again. It seems the problem comes from websockets that are not handled correctly and make the browser misbehave. His solution: downgrading the websockets library to version 6:

```python
pip install websockets==6
```

I do it in my virtualenv, and to ensure users will do the same (remember, rendering is currently a hidden feature in my program, thus the dependencies are not listed in setup.py), I add a check in `crawler_utils`:

```python
try:
    import websockets
    # v6 to avoid `pyppeteer.errors.NetworkError: Protocol error Target.createTarget: Target closed.`
    # See https://github.com/miyakogi/pyppeteer/issues/234#issuecomment-518215288
    wv = websockets.__version__
    if not wv.strip().startswith('6'):
        print(f'Wrong websockets version {wv}, should be v6.'
               'Please run pip install websockets==6')
        exit(1)
except ModuleNotFoundError:
    pass
```

Launching again and ...

Well, no error, but after crawling 12-15 URLs, the system hangs. Systematically. But there is no error of any kind, no clue. What is going on ? 

### The program hangs

My first intuition is that I screwed something with the lock and there is a deadlock. But the lock is systematically released in a `finally` close... Using `strace`, `gdb` and other tools, I can see that the program behaves properly: it is the requests-html `render()` method that is stuck.

Google being my friend, I finally get my answer, again in [an issue from the pyppeteer repo](https://github.com/miyakogi/pyppeteer/issues/167). [MemoryAndDream explains](https://github.com/miyakogi/pyppeteer/issues/167#issuecomment-442389039):

> *I have find the problem. I need set `'dumpio': True` in `launch`,or `subprocess.Popen` chrome will be stuck if the stderr is too large!*"

OK, so the problem is that some buffer gets filled, and Chrome is stuck waiting for something to consume its [crazy amount] of logs.

There is no way to change this behavior from `requests-html`, except by altering the source code itself. At this point I am desperate, so I just add a note somewhere and edit `venv/lib/python3.7/site-packages/requests_html.py`, passing `dumpio=True` to the `pyppeteer.launch` method.

This works, but gosh this pyppeteer is verbose !

## Waiting for AJAX to load

By this point, I finally have something working. I let it run for a while and play some more with the code. One of my first motivations at rendering pages during crawling was to be able to scrape Twitter and the like. So I try twitter again, expecting to see some tweets this time. Instead, I get:

```text
Something went wrong, but don’t fret — let’s give it another shot.
```

By now, I became familiar with `requests-html` and how they use `pyppeteer` behind the scenes. Looking at the `render()` method, I can see it is creating a new page, loading the URL and then asking for its content. The most important call being:

```python
await page.goto(url, options={'timeout': int(timeout * 1000)})
```

Looking at the API documentation of pyppeteer's [` Page.goto` method](https://miyakogi.github.io/pyppeteer/reference.html#pyppeteer.page.Page.goto), I see there is an interesting option called `waitUntil`:

> `waitUntil` (str|List[str]): When to consider navigation succeeded, defaults to `load`. [...] Events can be either:
>
> - `load`: when `load` event is fired.
> - `domcontentloaded`: when the `DOMContentLoaded` event is fired.
> - `networkidle0`: when there are no more than 0 network connections for at least 500 ms.
> - `networkidle2`: when there are no more than 2 network connections for at least 500 ms.

Hence, requests-html only waits for the `load` event, which lets virtually no time for the AJAX resources to be loaded, let alone injected into the DOM. In order to get the content of JS-heavy websites (e.g. Twitter), we need at least `networkidle2`.

There is no option in requests-html, so once again I edit the file inside my virtualenv:

```python
# in requests_html.py, _async_render method:
await page.goto(url, options={'timeout': int(timeout * 1000)}, waitUntil='networkidle0')
```

With this change, I can now see tweets alright.

## Make the environment reproducible

I finally have a working version that does what I need, but with a lot of compromises:

* the crawler is now a bottleneck, with only one thread at a time making an HTTP request (`threading.lock`);
* I have to manually change files in my environment for the system to work, which is suboptimal: I can easily forget it during a reinstall. Even explained in a README, chances are I (and others) will overlook it.

To circumvent the latter, I could make pull requests (which [I did](https://github.com/psf/requests-html/pull/366), at least for the `waitUntil` shenanigan). However, pull requests may take time to be processed, be rejected, etc.

(As a side note, my pull request "*failed all tests*", and looking at the Travis build history, there is a bug in `.travis-ci.yaml` making *any* pull request fail at installing dependencies. It has been going on for more than 6 months, so I don't expect my changes to be accepted soon.)

Another way is to fork and simply use my version of requests-html, but it means having to maintain it, ensure I merge the latest changes from the original, and it won't be available through pip (I could use another package name, but it wouldn't be fair).

# Screw it start again from scratch

After all these troubles, I am now familiar with the requests-html internals. I can see that I don't need most of what it offers, and the things I need the most (`dumpio=True`, waiting for `networkidle0`) are not covered.

Moreover, one thing I dislike is the fact that to render a page, I need first to get the html using `requests`. Indeed, the implementation is such that with requests-html, to call render we first need a response, hence to call the `requests.get` method once.
So crawling one URL means firing at least two `GET`. This detail is what really convinced me to simply reimplement the part I need.

## HtmlRenderer

Basically, what I need to do to render HTML (with JS support) is:

1. launch a pyppeteer instance (i.e. a browser)
2. create a new page (`browser.newPage`)
3. load the URL in the page (`page.goto`, which returns a response object with precious info), waiting for the network to cool down (`networkidle0`)
4. get the page content
5. return the response (headers, etc.) and the content in a way that is compatible with `requests`

This simple code exemplifies it (see `10-simple-example.py`):

```python
import asyncio
from pyppeteer import launch

async def render_js(url):
    browser = await launch(headless=True) # 1
    page = await browser.newPage() # 2
    response = await page.goto(url, waitUntil='networkidle0') # 3
    content = await page.content() # 3
    await browser.close()
    return response, content # 4

if __name__ == '__main__':
    url = 'https://twitter.com/hashtag/developer'
    loop = asyncio.get_event_loop()
    response, content = loop.run_until_complete(render_js(url))
```

Of course, I also want it to be compatible with threads (asyncio), not to hang (recall the `dumpio` thingy), not to launch a browser for each `GET` request, to properly handle exception, etc. Hence, the final code is a bit more complex.

See the `html_renderer` code of the module for the complete example.

### Threading

In my specific use case, I want to have two options:
* either one browser is used/shared by multiple threads,
* or each thread has its own browser.

For this, here is basically what I need:

1. The asyncio loop is initialised in the constructor. Instead of calling `asyncio.get_current_loop` (working only from main), I use `new_event_loop();
2. I protect the body of all sync method with a `threading.Lock`, to avoid concurrent accesses to the event loop (which will raise an error: "*This event loop is already running*");
3. Signals don't work in threads, so I disable them when launching pyppeteer. This was suggested by [with StackOverflow answer](https://stackoverflow.com/a/54030151);

### Wait for page load

As already discussed, multiple sites use AJAX to fetch the actual content displayed. Hence, `render` will by default wait for `networkidle0`. However, I saw that this may fail: in some instances, the background requests never stop, resulting in a `pyppeteer.errors.Timeout` exception. 
To circumvent this, I surround my `page.goto` call in a try/except and as a last resort, I try again but waiting only for `domcontentloaded` instead.

### Fetch more than one tweet

The default page viewport is quite small: 800x600. A height of 600px means that sites like twitter is only able to display one post and will wait for the scroll event to load more.
This is why I automatically set the viewport to 1200x1000.

### Fallback

In some instances the `page.goto` call returns `None` instead of throwing an exception (I posted an [issue](https://github.com/miyakogi/pyppeteer/issues/299) about it). It happens mostly when the content-encoding is wrong, e.g. says `gzip` but the actual content is not a valid gzip.
In those rare instances, `HtmlRenderer` will fallback to calling `requests`, which provides meaningful error messages.

### Requests compatibility

I want to be able to seamlessly switch between requests and HtmlRenderer. To make that possible, I construct a `requests.Response` for the information I gather from `pyppeteer`.
Most `requests.Response` attributes are directly available from the pyppeteer response. Except:
* `reason`: the reason is the status line, e.g. `OK` for 200. Most websites follow the convention (no status line or the one defined in the RFC), but it can always vary. Requests gets it from `urllib3`. With pyppeteer, I didn't find a way to get it. 
  To not leave it blank, I can: 
   + use a private lookup table of requests: `requests.status_codes._codes[resp.status_code][0]`. However, they do not match the usual reasons. For example, `404` is mapped to `not_found`, not `Not Found`. Furthermore, it's a private attributes, hence subject to change.
   + use `http.client.response`, a lookup table that maps to "status lines *for humans*". This one properly returns `Not Found`.
 I decided to use with this one, more stable and more in line with what a requests user would expect.
* `history`: the history is the list of redirections. I try to recreate it by following pyppeteer's `Response.redirectChain`, but I am not 100% sure it actually works for more than one redirect...
* `cookies`: I decided to skip this one.
    
## Seamlessly choose the implementation from an environment variable

As stated at the beginning of this post, due to how swisstext works, I wanted to control if rendering is used or not at launch without having to change the code of all my crawler implementations.

I already showed how I define a `do_get` method differently based on the value of an environment variable using requests-html.
Now that I have `HtmlRenderer` that supports threading, the code is altered in this way:

```python

_ENV_VARIABLE = 'RENDER_HTML'

if os.getenv(_ENV_VARIABLE, '0').lower().strip() in ['0', 'false', 'no', 'n', 'off']:
    logger.info('using REQUESTS for scraping')
    # => define or use default get <=

else:
    # let the user choose if one browser is created for all threads
    # or one browser should be created for each thread (_ENV_VARIABLE='2')
    one_browser_per_thread = os.getenv(_ENV_VARIABLE, '0') == '2'
    logger.info(f'using HTML_RENDERER for scraping ({"mono" if one_browser_per_thread else "multi"}-thread)')

    # == import modules

    try:
        import pyppeteer
        import asyncio
    except ModuleNotFoundError:
        print(f'Error: {_ENV_VARIABLE} set but pyppeteer not found. Please, run pip install pyppeteer2')
        exit(1)

    # == define the actual do_get

    from collections import defaultdict

    if one_browser_per_thread:
        # each thread will create its own HtmlRenderer instance
        _RENDERER = defaultdict(lambda: HtmlRenderer())
    else:
        # create one HtmlRenderer instance, shared by all threads
        renderer = HtmlRenderer()
        _RENDERER = defaultdict(lambda: renderer)

    def do_get(url, headers=None, timeout=RENDER_TIMEOUT) -> requests.Response:
        if headers is None:
            headers = dict()
        headers.setdefault('User-Agent', DEFAULT_USER_AGENT)
        renderer = _RENDERER[threading.current_thread().name]
        resp = renderer.render(url, timeout=timeout)

        return resp
```

Here, the secret is the use of a `defaultdict`, with the key being the thread name and the value an instance of `HtmlRenderer`.

**If we want one browser only**, we create one renderer when the module is imported. The `__init__.py` method will thus be called from the main thread. This same instance is attached to all the thread names.

**If we want one browser per thread**, we use `defaultdict(lambda: HtmlRenderer())` so that the first time a thread queries the dictionary, a new renderer instance will be created.

**If the chromium subprocess dies**... Well, in case the underlying browser is killed for some reason, a `pyppeteer.errors.Network` exception will be thrown in all subsequent calls.
I can't avoid the first one, but when it happens I could check the subprocess
(if `browser.subprocess.poll()` returns something other than `None`, it means it has exited)
and close the browser, so it will be recreated on the next call to `render`.

#### IMPORTANT NOTICES 

* With this implementation, the browsers are never properly closed. This is because they are created when the module imported, and apart from `atexit` there is no way of detecting when it goes "out of scope". So I actually rely on the fact that child processes will be killed when the main program terminates... (I know this is far from "clean" or "ideal"). For my needs, it is OK though.
* Using one browser per thread is only pertinent if you have few threads that use the renderer thoughout their lifetime.
  Remember: *each* thread will have its own browser running. If you spawn 1,000 threads that all call `do_get` once, you'll
  have 1,000 chromium running in the background !

## Still problems, pyppeteer2 to the rescue

After all this, I still ran into troubles. For example, the url:

* https://meertjes-stuff.blogspot.com/search/label/Link%20Your%20Stuff

leaves the browser hanging twice out of three.
I have no idea why, the call to `page.goto` just never returns, even after the timeout is way past. I tried many things without success.

On [pyppeteer's main repo](https://github.com/miyakogi/pyppeteer), I can across the issue [Is pyppeteer still maintained?](https://github.com/miyakogi/pyppeteer/issues/295) Granitosaurus replies:

> Unfortunately you're right. I couldn't get a hold of the maintainer for this, so I went ahead with `pyppeteer2` name on pypi.

So it tried using `pyppeteer2` instead. It seems to work and fixes the websockets incompatibility as well. No more websockets==6!

# Conclusion

The work of a developer is mostly about generating codes, getting some exception, googling about it and apply the fix that will trigger the next error.
This is both annoying and exhilarating, a sort of detective work that may not always end as expected.

Another important lesson is that it is never as easy as it seems at first: as a developer, you always end up "getting your hands dirty". In this case, this meant understanding asyncio and pyppeteer.

I know that this blog post will be completely outdated in a few months (the libraries will have changed, as well as the underlying chromium), but I still enjoyed the journey.
I hope it may be useful to some, fun to read for others.

Happy coding,

🐙 Derlin 🐙
