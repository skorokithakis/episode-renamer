import re
from setuptools import setup

requires = []

try:
    import json
except ImportError:
    requires.append('simplejson>=2.0.9')

version = re.search('__version__ = "(.+?)"',
                    open('episoderenamer.py').read()).group(1)

setup(
    name='episode-renamer',
    author='Stavros Korokithakis',
    author_email='stavros@korokithakis.net',
    version=version,
    py_modules=['episoderenamer'],
    description='TV episode renamer',
    long_description="TV episode renamer SCRIPT",
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Multimedia :: Video',
    ],
    install_requires=requires,
    entry_points = {
        'console_scripts':[
            'episoderenamer = episoderenamer:main'
        ]
    },
)
