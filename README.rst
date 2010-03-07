===========
Description
===========

Episode renamer is a simple python script that renames folders of TV episode video files to their proper names.

You can run it in a directory containing episode files of a show as:

episode-renamer.py -g "Show name"

and it will rename all files in the current directory with their proper titles. It also supports AtomicParsley for setting the correct tags for iTunes.

Engines
-------

Episode renamer supports various engines for getting episode names:

* imdbapi.poromenos.org - A third party service that parses the IMDB API. More reliable, as IMDB scraping might fail.
* epguides.com - Updated frequently and with good data.
* IMDB - Sometimes might fall a bit behind and fail to scrape.

Installation
------------

To install episode renamer you have multiple options:

* With pip (preferred), do "pip install episode-renamer".
* With setuptools, do easy_install episode-renamer.
* To install the source, download it from http://github.com/skorokithakis/episode-renamer/ and do "python setup.py install".

Usage
-----

To run episode renamer, just switch to the directory that contains your show's files, and run:

    ./episoderenamer.py -d "Show name"

If you want to use AtomicParsley to set all the correct tags, first make sure AtomicParsley is installed and run:

    ./episoderenamer.py -ad "Show name"

The rest of the options are explained by running:

    ./episoderenamer.py -h

