from get_html.js_renderer import JsRenderer

import pytest


@pytest.fixture(scope='module')
def renderer():
    r = JsRenderer()
    try:
        yield r
    finally:
        r.close()


def test_response(renderer: JsRenderer):
    url = 'http://www.twitter.com'  # this will redirect to https://twitter.com
    r = renderer.render(url)
    assert r.status_code == 200
    assert r.reason == 'OK', 'reason not ok'
    assert r.text == r.content.decode(r.encoding), 'wrong encoding'
    assert len(r.history) > 0, 'no redirect ??'


def test_404(renderer: JsRenderer):
    r = renderer.render('https://github.com/afadfadfaf/adsfa-not-exist')
    assert r.status_code == 404
    assert r.reason == 'Not Found'


@pytest.mark.parametrize(
    'url', [
        'https://meertjes-stuff.blogspot.com/search/label/Link%20Your%20Stuff',  # whut ?? this one is strange
        'https://www.investing.com/indices/major-indices',  # has websocket
        # 'http://data.fis-ski.com/dynamic/athlete-biography.html?sector=AL&competitorid=147749&type=result',  # don't remember, but was problematic
    ])
def test_potentially_problematic_urls(renderer: JsRenderer, url):
    r = renderer.render(url)
    assert r.status_code == 200
    assert len(r.content) > 0
