from get_html.html_renderer import HtmlRenderer

import pytest
import re


@pytest.fixture(scope='module')
def renderer():
    r = HtmlRenderer()
    try:
        yield r
    finally:
        r.close()


def test_response(renderer: HtmlRenderer):
    url = 'http://www.twitter.com'  # this will redirect to https://twitter.com
    r = renderer.render(url)
    assert r.status_code == 200
    assert r.reason == 'OK', 'reason not ok'
    assert r.text == r.content.decode(r.encoding), 'wrong encoding'
    assert len(r.history) > 0, 'no redirect ??'


def test_404(renderer: HtmlRenderer):
    r = renderer.render('https://github.com/afadfadfaf/adsfa-not-exist')
    assert r.status_code == 404
    assert r.reason == 'Not Found'


@pytest.mark.parametrize(
    'url', [
        'https://meertjes-stuff.blogspot.com/search/label/Link%20Your%20Stuff',  # whut ?? this one is strange
        'https://www.investing.com/indices/major-indices',  # has websocket
        # 'http://data.fis-ski.com/dynamic/athlete-biography.html?sector=AL&competitorid=147749&type=result',  # don't remember, but was problematic
    ])
def test_potentially_problematic_urls(renderer: HtmlRenderer, url):
    r = renderer.render(url)
    assert r.status_code == 200
    assert len(r.content) > 0


def test_manipulate_page(renderer: HtmlRenderer):
    url = 'https://9gag.com/'
    r = renderer.render(url)
    num_articles = len(re.findall('<article', r.text))

    # async def fn(page):
    #     assert page is not None
    #     for _ in range(10):
    #         await page._keyboard.down('PageDown')

    async def fn(page):
        # https://github.com/miyakogi/pyppeteer/issues/205#issuecomment-470886682
        await page.evaluate('{window.scrollBy(0, document.body.scrollHeight);}')

    r = renderer.render(url, manipulate_page_func=fn)
    num_articles_after_scroll = len(re.findall('<article', r.text))
    print(num_articles, num_articles_after_scroll)
    assert num_articles_after_scroll > num_articles
