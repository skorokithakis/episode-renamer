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


class Show:
    def __init__(self, title="", rating=0):
        self.title = title
        self.episodes = {}

def parse_imdb(page):
    """Parse an IMDB page."""
    # Remove &#160; (nbsp) entities.
    page = page.replace("&#160;", "")
    soup = BeautifulSoup(page, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
    title = re.search("\"?(.*?)\"? *?\(.*?\)", soup.title.string).group(1)
    show = Show(title)

    table = soup.find("h4").findNext("table")
    for tr in table.findChildren("tr")[1:]:
        tds = tr.findChildren("td")
        season, episode = tds[0].contents[0].split(".")
        show.episodes[(int(season), int(episode))] = {"title": tds[1].a.contents[0]}
        show.episodes[(int(season), int(episode))]["rating"] = tds[2].contents[0]

    return show

def parse_epguides(page):
    """Parse an epguides page."""
    soup = BeautifulSoup(page, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
    page = unicode(soup).replace("\n", "")
    show = Show()
    try:
        show.title = re.search("""<h1><a href="http://.*?">(.*?)</a></h1>""", page).groups()[0]
    except AttributeError:
        print "Could not find show title, cannot continue."
        sys.exit()
    episodes = re.findall("\d+. +(?P<season>\d+) *\- *(?P<episode>\d+).*?\d+ +[A-Za-z]+ +\d+ +<a target.*?>(?P<name>.*?)</a>", page)
    for season, episode, name in episodes:
        show.episodes[(int(season), int(episode))] = {"title": name}
    return show

SITES = [
    {"url": "http://epguides.com/%s/",
     "domain": "epguides.com",
     "urlparser": "epguides.com\/(.*?)\/",
     "parser": parse_epguides,
     },
    {"url": "http://www.imdb.com/title/%s/epdate",
     "domain": "imdb.com",
     "urlparser": "imdb\.com\/title\/(.*?)\/",
     "parser": parse_imdb,
    },
        ]

def search_show(name, site):
    """Search Google for the page best matching the given show name."""
    google_url = "http://www.google.com/search?q=site%%3A%s+%s" % (site["domain"], urllib.quote(name))

    # Bastard Google...
    request = urllib2.Request(google_url)
    request.add_header("User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.4) Gecko/20070515 Firefox/2.0.0.4")
    page = urllib2.urlopen(request).read()

    soup = BeautifulSoup(page)
    result = soup.find("a", "l")["href"]

    show_id = re.search(site["urlparser"], result).group(1)
    return show_id

def rename_files(show, file_mask, preview=False, use_ap=False):
    series_parser = [
        re.compile("^.*?s *(?P<series>\d+) *e *(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
        re.compile("^.*?(?P<series>\d+)x(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
        re.compile("^(?:.*?\D|)(?P<series>\d{1,2})(?P<episode>\d{2})(?:\D.*|)\.(?P<extension>.*?)$", re.IGNORECASE),
        ]
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

        info_dictionary = {"show": show.title,
                           "series_num": series,
                           "episode_num": episode,
                           "extension": extension}

        try:
            info_dictionary.update(show.episodes[(series, episode)])
            new_filename = file_mask % info_dictionary
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
                proc = subprocess.Popen(("AtomicParsley", filename, "-o", temp_filename, "--TVShowName", show.title, "--stik", "TV Show", "--TVSeasonNum", str(series), "--TVEpisodeNum", str(episode), "--TVEpisode", show.episodes[(series, episode)]["title"], "--title", show.episodes[(series, episode)]["title"]))
                proc.wait()
                os.remove(filename)
                try:
                    os.rename(temp_filename, new_filename)
                except:
                    print "There was an error while renaming the file."
            else:
                try:
                    os.rename(filename, new_filename)
                except:
                    print "There was an error while renaming the file."

def main():
    parser = optparse.OptionParser(usage="%prog [options] <show id from the URL>", version="Episode renamer %s\nThis program is released under the GNU GPL." % VERSION)
    parser.add_option("-e",
                      "--use-epguides",
                      dest="use_epguides",
                      action="store_true",
                      help="use epguides.com instead of IMDB")
    parser.add_option("-p",
                      "--preview",
                      dest="preview",
                      action="store_true",
                      help="don't actually rename anything")
    parser.add_option("-m",
                      "--mask",
                      dest="mask",
                      default="%(show)s - S%(series_num)02dE%(episode_num)02d - %(title)s.%(extension)s",
                      metavar="MASK",
                      action="store",
                      type="string",
                      help="the filename mask to use when renaming (default: \"%default\")")
    parser.add_option("-g",
                      "--google",
                      dest="google",
                      action="store_true",
                      help="search Google for the episode list based on the show name")
    parser.add_option("-a",
                      "--use-atomic-parsley",
                      dest="use_atomic_parsley",
                      action="store_true",
                      help="use AtomicParsley to fill in the files' tags")
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

    show = site["parser"](page)
    rename_files(show, options.mask, options.preview, options.use_atomic_parsley)
    print "Done."

if __name__ == "__main__":
    main()
