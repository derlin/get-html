from get_html.html_renderer import create_renderer


def test_contextmanager():
    with create_renderer() as renderer:
        r = renderer.render('https://twitter.com')
        assert r.status_code == 200
