#!/usr/bin/env python

# Episode renamer - Copyright 2008 Stavros Korokithakis
# Released under the GNU GPL.
# You can find the latest version at http://www.poromenos.org

import urllib2
import optparse
import re
import os
import sys
import subprocess
import random

def parse_imdb_page(page):
    episode_names = {}
    page = page.replace("\n", "")
    episode_names["title"] = re.search("<b>&#34;(.*?)&#34; \(.*?\)</b>", page).groups()[0]
    episodes = re.findall("""<td align="right" bgcolor="#eeeeee">(?P<season>\d+)\.(?P<episode>\d+)&#160;</td> *<td><a .*?>(.*?)</a></td>""", page)
    for season, episode, name in episodes:
        episode_names[(int(season), int(episode))] = name
    return episode_names

def rename_files(episode_names, preview=False, use_ap=False):
    series_parser = re.compile("^.*s *(?P<series>\d+) *e *(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE)
    for filename in os.listdir("."):
        matches = series_parser.search(filename)
        try:
            match_dict = matches.groupdict()
        except AttributeError:
            continue

        series = int(match_dict["series"])
        episode = int(match_dict["episode"])
        extension = match_dict["extension"]

        try:
            new_filename = "%s - S%sE%s - %s.%s" % (episode_names["title"], str(series).zfill(2), str(episode).zfill(2), episode_names[(series, episode)], extension)
        except KeyError:
            print 'Could not rename "%s"' % filename
        new_filename = re.sub("[\?\[\]\/\\\=\+\<\>\:\\;\",\*\|]", "", new_filename)
        print """Renaming "%s" to "%s"...""" % (filename, new_filename)
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
    parser = optparse.OptionParser(usage="%prog [options] <IMDB id>", version="Episode rename 0.1\nThis program is released under the GNU GPL.")
    parser.add_option("-p", "--preview", dest="preview", action="store_true", help="don't actually rename anything")
    parser.add_option("-a", "--use-atomic-parsley", dest="use_atomic_parsley", action="store_true", help="use AtomicParsley to fill in the files' tags")
    parser.set_defaults(preview=False)
    (options, arguments)=parser.parse_args()

    if len(arguments) != 1:
        parser.print_help()
        sys.exit(1)

    page_url = "http://www.imdb.com/title/%s/epdate" % arguments[0]

    try:
        page = urllib2.urlopen(page_url).read()
    except urllib2.HTTPError, error:
        print "An HTTP error occurred, HTTP code %s." % error.code
        sys.exit()

    episode_names = parse_imdb_page(page)
    rename_files(episode_names, options.preview, options.use_atomic_parsley)
    print "Done."

if __name__ == "__main__":
    main()
