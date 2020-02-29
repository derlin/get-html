if __name__ == '__main__':
    import argparse
    import logging
    import threading

    from get_html.env_defined_get import do_get

    # https://www.fis-ski.com/DB/general/athlete-biography.html?sector=AL&competitorid=147749&type=result

    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', type=argparse.FileType('r'))
    parser.add_argument('-t', '--threads', type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    urls = []
    for line in args.input_file:
        u = line.strip()
        if u.startswith('http'):
            urls.append(u)
        else:
            print(f'{u}: not a regular URL. Skipping')


    class Worker(threading.Thread):

        def __init__(self, urls):
            super().__init__()
            self.urls = urls

        def run(self):
            for u in self.urls:
                try:
                    r = do_get(u)
                    print(
                        f'@@ {u}: {r.status_code} {r.reason}. Content length: {len(r.text)}, encoding {r.encoding}. Redirects: {len(r.history)}. Elapsed: {r.elapsed}.')
                except Exception as e:
                    print(f'@@ {u}: ERROR ! {e}')


    n = min(args.threads, len(urls))

    if n <= 1:
        Worker(urls).run()

    else:
        workers = [Worker(urls[i::n]) for i in range(n)]

        for w in workers:
            w.start()

        for w in workers:
            w.join()
