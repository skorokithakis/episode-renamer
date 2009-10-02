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
import md5

from version import *

SERIES_PARSER = [
    re.compile("^.*?s *(?P<series>\d+) *e *(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
    re.compile("^.*?(?P<series>\d+)x(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
    re.compile("^(?:.*?\D|)(?P<series>\d{1,2})(?P<episode>\d{2})(?:\D.*|)\.(?P<extension>.*?)$", re.IGNORECASE),
    ]
    
class Show:
    def __init__(self, title=""):
        self.title = title
        self.attributes = {}
        self.episodes = {}


def get_page(page_url):
    try:
        return urllib2.urlopen(page_url).read()
    except urllib2.HTTPError, error:
        print "An HTTP error occurred, HTTP code %s." % error.code
        sys.exit()

def search_show(name, site):
    """Search Google for the page best matching the given show name."""
    google_url = "http://www.google.com/search?q=site%%3A%s+%s" % (site["domain"], urllib.quote(name))

    # Bastard Google...
    request = urllib2.Request(google_url)
    request.add_header("User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.4) Gecko/20070515 Firefox/2.0.0.4")
    page = urllib2.urlopen(request).read()

    from BeautifulSoup import BeautifulSoup
    soup = BeautifulSoup(page)
    result = soup.find("a", "l")["href"]

    show_id = re.search(site["urlparser"], result).group(1)
    return show_id

def parse_imdbapi(show_id, options):
    """Get the episodes from imdbapi."""
    import simplejson 
    results = simplejson.loads(urllib2.urlopen("http://imdbapi.poromenos.org/json/?name=%s" % urllib.quote(show_id)).read())
    if results == None or "shows" in results:
        print "Show not found."
        sys.exit()
    show = Show(results.keys()[0])
    for episode in results[show.title]["episodes"]:
        show.episodes[(episode["season"], episode["number"])] = {"title": episode["name"]}
    return show

def parse_imdb(show_id, options):
    """Parse an IMDB page."""

    site = {"url": "http://www.imdb.com/title/%s/epdate",
            "domain": "imdb.com",
            "urlparser": "imdb\.com\/title\/(.*?)\/",
           }

    if options.google:
        show_id = search_show(show_id, site)
        print "Found show ID \"%s\"..." % show_id

    page = get_page(site["url"] % show_id)

    from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
    # Remove &#160; (nbsp) entities.
    page = page.replace("&#160;", "")
    soup = BeautifulSoup(page, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
    matches = re.search("(?:&#x22;|)(.*?)(?:&#x22;|) *?\((.*?)\)", soup.title.string)
    title = matches.group(1)
    try:
        year = matches.group(2)
    except IndexError:
        year = None
    show = Show(title)
    if options.use_atomic_parsley:
        show.attributes["artwork"] = urllib2.urlopen(soup.find("a", attrs={"name": "poster"}).findNext("img")["src"]).read()
    show.attributes["year"] = year

    table = soup.find("h4").findNext("table")
    for tr in table.findChildren("tr")[1:]:
        tds = tr.findChildren("td")
        season, episode = tds[0].contents[0].split(".")
        show.episodes[(int(season), int(episode))] = {"title": tds[1].a.contents[0]}
        show.episodes[(int(season), int(episode))]["rating"] = tds[2].contents[0]

    return show

def parse_epguides(show_id, options):
    """Parse an epguides page."""

    site = {"url": "http://epguides.com/%s/",
            "domain": "epguides.com",
            "urlparser": "epguides.com\/(.*?)\/",
           }

    if options.google:
        show_id = search_show(show_id, site)
        print "Found show ID \"%s\"..." % show_id

    page = get_page(site["url"] % show_id)

    from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
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

def parse_filename(show, filename, file_mask):
    for parser in SERIES_PARSER:
        matches = parser.search(filename)
        try:
            match_dict = matches.groupdict()
            break
        except AttributeError:
            continue
    else:
        raise Exception("Filename not matched.")

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
        print 'Episode name for "%s" not found.' % filename
        raise Exception
    new_filename = re.sub("[\\\/\:\*\"\?\<\>\|]", "", new_filename)
    
    return new_filename, info_dictionary

def rename_files(show, file_mask, preview=False, use_ap=False):
    for filename in os.listdir("."):
        try:
            new_filename, info_dictionary = parse_filename(show, filename, file_mask)
        except:
            print 'Episode name for "%s" not found.' % filename
            continue

        print "Renaming \"%s\" to \"%s\"..." % (filename, new_filename.encode("ascii", "replace"))
        if not preview:
            if use_ap:
                # The temp_filename shenanigans are necessary because AP sometimes
                # chokes if it's set to overwrite the file.
                temp_filename = filename + str(random.randint(10000, 99999))
                arguments = ["AtomicParsley",
                             filename,
                             "-o", temp_filename,
                             "--TVShowName", info_dictionary["show"],
                             "--stik", "TV Show",
                             "--TVSeasonNum", str(info_dictionary["series_num"]),
                             "--TVEpisodeNum", str(info_dictionary["episode_num"]),
                             "--TVEpisode", show.episodes[(info_dictionary["series_num"], info_dictionary["episode_num"])]["title"],
                             "--title", show.episodes[(info_dictionary["series_num"], info_dictionary["episode_num"])]["title"]]
                if "year" in show.episodes[(info_dictionary["series_num"], info_dictionary["episode_num"])]:
                    arguments.extend(["--year", show.episodes[(info_dictionary["series_num"], info_dictionary["episode_num"])]["year"]])
                elif "year" in show.attributes:
                    arguments.extend(["--year", show.attributes["year"]])

                artwork_file = None
                if "artwork" in show.episodes[(info_dictionary["series_num"], info_dictionary["episode_num"])]:
                    artwork_filename = md5.md5(str(random.randint(10000, 100000))).hexdigest()
                    artwork_file = open(artwork_filename, "wb")
                    artwork_file.write(show.episodes[(info_dictionary["series_num"], info_dictionary["episode_num"])]["artwork"])
                    artwork_file.close()
                    arguments.extend(["--artwork", "REMOVE_ALL", "--artwork", artwork_filename])
                elif "artwork" in show.attributes:
                    artwork_filename = md5.md5(str(random.randint(10000, 100000))).hexdigest()
                    artwork_file = open(artwork_filename, "wb")
                    artwork_file.write(show.attributes["artwork"])
                    artwork_file.close()
                    arguments.extend(["--artwork", "REMOVE_ALL", "--artwork", artwork_filename])

                proc = subprocess.Popen(tuple(arguments))
                proc.wait()
                if proc.returncode == 0:
                    os.remove(filename)

                    try:
                        os.rename(temp_filename, new_filename)
                    except:
                        print "There was an error while renaming the file."

                if artwork_file:
                    os.remove(artwork_filename)
            else:
                try:
                    os.rename(filename, new_filename)
                except:
                    print "There was an error while renaming the file."

def main():
    parser = optparse.OptionParser(usage="%prog [options] <show id from the URL>", version="Episode renamer %s\nThis program is released under the GNU GPL." % VERSION)
    parser.add_option("-a",
                      "--use-atomic-parsley",
                      dest="use_atomic_parsley",
                      action="store_true",
                      help="use AtomicParsley to fill in the files' tags")
    parser.add_option("-d",
                      "--use-imdbapi",
                      dest="use_imdbapi",
                      action="store_true",
                      help="use imdbapi.poromenos.org")
    parser.add_option("-e",
                      "--use-epguides",
                      dest="use_epguides",
                      action="store_true",
                      help="use epguides.com")
    parser.add_option("-i",
                      "--use-imdb",
                      dest="use_imdb",
                      action="store_true",
                      help="use imdb.com")
    parser.add_option("-m",
                      "--mask",
                      dest="mask",
                      default="%(show)s - S%(series_num)02dE%(episode_num)02d - %(title)s.%(extension)s",
                      metavar="MASK",
                      action="store",
                      type="string",
                      help="the filename mask to use when renaming (default: \"%default\")")
    parser.add_option("-p",
                      "--preview",
                      dest="preview",
                      action="store_true",
                      help="don't actually rename anything")
    parser.add_option("-g",
                      "--google",
                      dest="google",
                      action="store_true",
                      help="search Google for the episode list based on the show name")
    parser.set_defaults(preview=False)
    (options, arguments)=parser.parse_args()

    if len(arguments) != 1:
        parser.print_help()
        sys.exit(1)

    if options.use_imdb:
        parser = parse_imdb
    elif options.use_epguides:
        parser = parse_epguides
    else:
        parser = parse_imdbapi

    show = parser(arguments[0], options)
    rename_files(show, options.mask, options.preview, options.use_atomic_parsley)
    print "Done."

if __name__ == "__main__":
    main()
