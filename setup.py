from setuptools import setup
from version import VERSION
setup(
    name='episode-renamer',
    author='Stavros Korokithakis',
    author_email='stavros@korokithakis.net',
    version=VERSION,
    py_modules=['episoderenamer', 'version'],
    description='TV episode renamer',
    long_description="TV episode renamer SCRIPT",
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Multimedia :: Video',
    ],
    install_requires=["BeautifulSoup==3.0.7a"],
    entry_points = {
        'console_scripts':[
            'episoderenamer = episoderenamer:main'
        ]
    },
    
)
