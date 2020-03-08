import setuptools
import os

# Import the README and use it as the long-description.
# Note: this will only work if 'README.rst' is present in your MANIFEST.in file!
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setuptools.setup(
    name='get-html',
    version='0.0.3',
    author='Lucy Linder',
    author_email='lucy.derlin@gmail.com',
    description='HTTP GET with JS rendering support, to get the rendered HTML from a page easily',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='Apache License 2.0',
    url='https://github.com/derlin/get-html',

    packages=setuptools.find_packages(),

    python_requires='>=3.6',

    classifiers=(
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
    ),
    install_requires=[
        'pyppeteer2==0.2.2',
        'requests>=2.23,<=2.24'
    ]
)
