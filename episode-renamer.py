#!/usr/bin/env python

# Episode renamer - Copyright 2008 Stavros Korokithakis
# Released under the GNU GPL.
# You can find the latest version at http://www.poromenos.org

import urllib
import urllib2
import optparse
import re
import os
import sys
import subprocess
import random
import htmlentitydefs
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from version import *

SITES = [
    {"url": "http://epguides.com/%s/",
     "episode_re": "\d+. +(?P<season>\d+) *\- *(?P<episode>\d+) +(?:[\d\w]+|) +\d+ +[A-Za-z]+ +\d+ +<a target.*?>(?P<name>.*?)</a>",
     "title_re": """<h1><a href="http://.*?">(.*?)</a></h1>""",
     "domain": "epguides.com",
     "urlparser": "epguides.com\/(.*?)\/",
     },
    {"url": "http://www.imdb.com/title/%s/epdate",
     "episode_re": """<td align="right" bgcolor="#eeeeee">(?P<season>\d+)\.(?P<episode>\d+).?</td> *<td><a .*?>(?P<name>.*?)</a></td>""",
     "title_re": "<title>\"?(.*?)\"? *?\(.*?\)</title>",
     "domain": "imdb.com",
     "urlparser": "imdb\.com\/title\/(.*?)\/",
    },
        ]

def search_show(name, site):
    """Search Google for the page best matching the given show name."""
    google_url = "http://www.google.com/xhtml/search?q=site%%3A%s+%s" % (site["domain"], urllib.quote(name))

    # Bastard Google...
    request = urllib2.Request(google_url)
    request.add_header("User-Agent", "User-Agent: Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.4) Gecko/20070515 Firefox/2.0.0.4")
    page = urllib2.urlopen(request).read()
    result = re.findall("<span class=\"green\">(.*?)</span>", page)[0]
    show_id = re.search(site["urlparser"], result).group(1)
    return show_id

def parse_page(page, site):
    """Parse a page, entering the episode names in a dictionary."""
    soup = BeautifulSoup(page, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
    episode_names = {}
    page = unicode(soup).replace("\n", "")
    try:
        episode_names["title"] = re.search(site["title_re"], page).groups()[0]
    except AttributeError:
        print "Could not find show title, cannot continue."
        sys.exit()
    episodes = re.findall(site["episode_re"], page)
    for season, episode, name in episodes:
        episode_names[(int(season), int(episode))] = name
    return episode_names

def rename_files(episode_names, preview=False, use_ap=False):
    series_parser = [
        re.compile("^.*?s *(?P<series>\d+) *e *(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
        re.compile("^.*?(?P<series>\d+)x(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
        ]
    title = episode_names["title"]
    for filename in os.listdir("."):
        for parser in series_parser:
            matches = parser.search(filename)
            try:
                match_dict = matches.groupdict()
                break
            except AttributeError:
                continue
        else:
            continue

        series = int(match_dict["series"])
        episode = int(match_dict["episode"])
        extension = match_dict["extension"]

        try:
            new_filename = u"%s - S%02dE%02d - %s.%s" % (title, series, episode, episode_names[(series, episode)], extension)
        except KeyError:
            print 'Episode name for  "%s" not found.' % filename
            continue
        new_filename = re.sub("[\\\/\:\*\"\?\<\>\|]", "", new_filename)
        print "Renaming \"%s\" to \"%s\"..." % (filename, new_filename.encode("ascii", "replace"))
        if not preview:
            if use_ap:
                # The temp_filename shenanigans are necessary because AP sometimes
                # chokes if it's set to overwrite the file.
                temp_filename = filename + str(random.randint(10000, 99999))
                proc = subprocess.Popen(("AtomicParsley", filename, "-o", temp_filename, "--TVShowName", episode_names["title"], "--stik", "TV Show", "--TVSeasonNum", str(series), "--TVEpisodeNum", str(episode), "--TVEpisode", episode_names[(series, episode)], "--title", episode_names[(series, episode)]))
                proc.wait()
                os.remove(filename)
                os.rename(temp_filename, new_filename)
            else:
                os.rename(filename, new_filename)

def main():
    parser = optparse.OptionParser(usage="%prog [options] <show id from the URL>", version="Episode renamer %s\nThis program is released under the GNU GPL." % VERSION)
    parser.add_option("-e", "--use-epguides", dest="use_epguides", action="store_true", help="use epguides.com instead of IMDB")
    parser.add_option("-p", "--preview", dest="preview", action="store_true", help="don't actually rename anything")
    parser.add_option("-g", "--google", dest="google", action="store_true", help="search Google for the episode list based on the show name")
    parser.add_option("-a", "--use-atomic-parsley", dest="use_atomic_parsley", action="store_true", help="use AtomicParsley to fill in the files' tags")
    parser.set_defaults(preview=False)
    (options, arguments)=parser.parse_args()

    if len(arguments) != 1:
        parser.print_help()
        sys.exit(1)

    if options.use_epguides:
        site = SITES[0]
    else:
        site = SITES[1]

    if options.google:
        show_id = search_show(arguments[0], site)
        print "Found show ID \"%s\"..." % show_id
        page_url = site["url"] % show_id
    else:
        page_url = site["url"] % arguments[0]

    try:
        page = urllib2.urlopen(page_url).read()
    except urllib2.HTTPError, error:
        print "An HTTP error occurred, HTTP code %s." % error.code
        sys.exit()

    episode_names = parse_page(page, site)
    rename_files(episode_names, options.preview, options.use_atomic_parsley)
    print "Done."

if __name__ == "__main__":
    main()
