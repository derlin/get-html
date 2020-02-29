import setuptools

setuptools.setup(
    name='get-html',
    version='0.1.0',
    author='Lucy Linder',
    author_email='lucy.derlin@gmail.com',
    description='HTTP GET with JS rendering support, to get the rendered HTML from a page easily',
    license='Apache License 2.0',
    url='https://github.com/derlin/http-get',

    packages=setuptools.find_packages(),
    
    python_requires='>=3.6',

    classifiers=(
        'Programming Language :: Python :: 3',
        'License :: Apache License 2.0',
        'Operating System :: OS Independent',
    ),
    install_requires=[
        'pyppeteer2==0.2.2',
        'requests>=2.23,<=2.24'
    ]
)
