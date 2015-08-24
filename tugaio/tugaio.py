__author__ = 'psaraiva'

# coding=utf-8

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

import httplib
from bs4 import BeautifulSoup
import re
import urllib2
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

TUGA_IO_URL = 'http://tuga.io'
TUGA_KIDS_URL = 'http://kids.tuga.io'
TUGA_IO_MOVIES = "/filmes/{page}?orderby={order}&from={latest}&genre={genre}"
TUGA_IO_SERIES = "/series/{page}?orderby={order}&from={latest}&genre={genre}"
TUGA_IO_PAGE_SIZE = 42


def create_request(url):
    httplib.HTTPConnection.debuglevel = 1
    request = urllib2.Request(url)
    request.add_header('User-Agent',
                       'Mozilla/5.0 (compatible;)')
    opener = urllib2.build_opener()
    return opener.open(request).read()


def create_titles(raw_titles):
    titles = []
    for raw_title in raw_titles:
        title = create_title(raw_title)
        titles.append(title)
    return titles


def resolve_video_and_subtitles_url(base_url, path):
    html = create_request(base_url + path)
    query = BeautifulSoup(html, "html.parser")
    video_url = "http://" + urllib.quote(urllib.unquote(
        query("script", text=re.compile("file:"))[0].text.strip().partition("'http://")[-1].partition("'")[0]))
    subtitles_url = base_url + \
                    query("script", text=re.compile("file:"))[0].text.strip().split("file:")[3].partition('"')[
                        -1].partition('"')[0]
    return {"video": video_url, "subtitles": subtitles_url}


def create_title(raw_title):
    url = raw_title.attrs["href"]
    thumb = raw_title("div", {"class": "img"})[0].attrs["style"].partition("'")[-1].rpartition("'")[0]
    name = raw_title("div", {"class": "title"})[0].text.encode('utf-8')
    year = raw_title("div", {"class": "year"})[0].text.encode('utf-8')
    imdb = raw_title("div", {"class": "imdb"})[0].text.partition(" ")[-1].encode('utf-8')
    return {"url": url, "thumb": thumb, "name": name, "year": year, "imdb": imdb}


def get_movie_titles(page=1, order=2, latest=1, genre=0):
    html = create_request(TUGA_IO_URL +
                          TUGA_IO_MOVIES.format(page=page, order=order, latest=latest, genre=genre))

    return find_titles(html, 'filme')


def get_tv_titles(page=1, order=2, latest=1, genre=0):
    html = create_request(TUGA_IO_URL +
                          TUGA_IO_SERIES.format(page=page, order=order, latest=latest, genre=genre))

    return find_titles(html, 'serie')


def get_tv_show_seasons(url):
    html = create_request(TUGA_IO_URL + url)
    return find_seasons(html)


def get_tv_season_titles(url, season):
    html = create_request(TUGA_IO_URL + url)
    return find_tv_titles(html, season)


def get_kids_titles(page=1, order=2, latest=1, genre=0):
    html = create_request(TUGA_KIDS_URL +
                          TUGA_IO_MOVIES.format(page=page, order=order, latest=latest, genre=genre))

    return find_titles(html, 'filme')


def find_titles(html, title_type):
    query = BeautifulSoup(html, "html.parser")
    return query.find_all(href=re.compile("/" + title_type + "/"))


def find_seasons(html):
    query = BeautifulSoup(html, "html.parser")
    return query.find_all("h2")


def find_tv_titles(html, season):
    query = BeautifulSoup(html, "html.parser")
    return query.find('h2', text=season).parent(href=re.compile("/episodio/"))


def build_url(query):
    return base_url + '?' + urllib.urlencode(query)


def create_root_menu():
    movies_folder = xbmcgui.ListItem("Filmes", iconImage=None, thumbnailImage=None)
    series_folder = xbmcgui.ListItem("Series", iconImage=None, thumbnailImage=None)
    kids_folder = xbmcgui.ListItem("Infantil", iconImage=None, thumbnailImage=None)
    settings_folder = xbmcgui.ListItem("Definicoes", iconImage=None, thumbnailImage=None)

    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "list", "folder": "movies", "page": "1"}),
                                listitem=movies_folder, isFolder=True)
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "list", "folder": "series", "page": "1"}),
                                listitem=series_folder, isFolder=True)
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "list", "folder": "kids", "page": "1"}),
                                listitem=kids_folder, isFolder=True)
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "settings"}),
                                listitem=settings_folder, isFolder=True)
    xbmc.executebuiltin("Container.SetViewMode(%s)" % addon.getSetting("menuView"))
    xbmcplugin.endOfDirectory(addon_handle)


def create_titles_menu():
    page = int(args.get('page', '1')[0])
    folder = args.get('folder', None)[0]

    tugaio_base_url = TUGA_IO_URL

    titles_html = None
    action = 'play'
    is_playable = 'true'
    is_folder = False
    if folder == "movies":
        titles_html = get_movie_titles(page=page)
        xbmc.executebuiltin("Container.SetViewMode(%s)" % addon.getSetting("moviesView"))
    elif folder == "series":
        titles_html = get_tv_titles(page=page)
        action = "seasons"
        is_playable = 'false'
        xbmc.executebuiltin("Container.SetViewMode(%s)" % addon.getSetting("seriesView"))
        is_folder = True
    elif folder == "kids":
        titles_html = get_kids_titles(page=page)
        tugaio_base_url = TUGA_KIDS_URL

    titles = create_titles(titles_html)

    for title in titles:
        title['action'] = action
        title['base_url'] = tugaio_base_url

        url = build_url(title)
        title_item = xbmcgui.ListItem(title['name'], iconImage=tugaio_base_url + title['thumb'],
                                      thumbnailImage=tugaio_base_url + title['thumb'])
        title_item.setInfo('Video', {'Year': title['year'], 'Rating': title['imdb'], })
        title_item.setProperty('IsPlayable', is_playable)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=title_item, isFolder=is_folder)

    if len(titles) == TUGA_IO_PAGE_SIZE:
        next_folder = xbmcgui.ListItem("Proxima pagina", iconImage=None, thumbnailImage=None)
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=build_url({"action": "list", "folder": folder, "page": str(page + 1)}),
                                    listitem=next_folder, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)


def create_seasons_menu():
    url = args.get('url', None)[0]
    seasons = get_tv_show_seasons(url)

    for season in seasons:
        season_item = xbmcgui.ListItem(season.text.strip())
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=build_url(
                                        {"url": url, "action": "list_season", "folder": season.text, "page": "1"}),
                                    listitem=season_item, isFolder=True)

    xbmc.executebuiltin("Container.SetViewMode(%s)" % addon.getSetting("menuView"))
    xbmcplugin.endOfDirectory(addon_handle)


def create_episodes_menu():
    url = args.get('url', None)[0]
    season = args.get('folder', None)[0]
    raw_titles = get_tv_season_titles(url, season)
    titles = create_titles(raw_titles)

    for title in titles:
        title['action'] = "play"
        title['base_url'] = TUGA_IO_URL

        url = build_url(title)
        title_item = xbmcgui.ListItem(title['name'], iconImage=TUGA_IO_URL + title['thumb'],
                                      thumbnailImage=TUGA_IO_URL + title['thumb'])
        title_item.setProperty('IsPlayable', "true")
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=title_item)

    xbmc.executebuiltin("Container.SetViewMode(%s)" % addon.getSetting("episodesView"))
    xbmcplugin.endOfDirectory(addon_handle)


def play_title():
    url = args.get('url', None)[0]
    name = args.get('name', None)[0]
    thumb = args.get('thumb', None)[0]
    tugaio_base_url = args.get('base_url', None)[0]

    resolved_url = resolve_video_and_subtitles_url(tugaio_base_url, url)
    play_item = xbmcgui.ListItem(name, iconImage=tugaio_base_url + thumb, thumbnailImage=tugaio_base_url + thumb,
                                 path=resolved_url["video"])
    play_item.setSubtitles([resolved_url["subtitles"]])
    xbmcplugin.setResolvedUrl(handle=addon_handle, succeeded=True, listitem=play_item)


def show_settings():
     xbmc.executebuiltin("Addon.OpenSettings(%s)" % id_addon)


def get_action():
    return args.get('action', None)[0]


id_addon = xbmcaddon.Addon().getAddonInfo("id")
addon = xbmcaddon.Addon(id_addon)
addon_folder = addon.getAddonInfo('path')
getSetting = xbmcaddon.Addon().getSetting
images_folder = os.path.join(addon_folder, 'resources', 'media')
fanart = os.path.join(addon_folder, 'fundo.png')
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])
xbmcplugin.setContent(addon_handle, 'movies')


if len(args) == 0:
    create_root_menu()

elif get_action() == "list":
    create_titles_menu()

elif get_action() == "seasons":
    create_seasons_menu()

elif get_action() == "list_season":
    create_episodes_menu()

elif get_action() == 'play':
    play_title()

elif get_action() == 'settings':
    show_settings()
