__author__ = 'psaraiva'

# coding=utf-8

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

from net import Net
from bs4 import BeautifulSoup
import urllib2
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import cookielib
import re
import time
import xbmcaddon

TUGA_IO_URL = 'http://tuga.su'
TUGA_IO_MOVIES = "/filmes/{page}?orderby={order}&from={latest}&genre={genre}"
TUGA_IO_SERIES = "/series/{page}?orderby={order}&from={latest}&genre={genre}"
TUGA_IO_PAGE_SIZE = 42
TUGA_IO_ORDER_BY_YEAR = 3
TUGA_IO_ORDER_BY_LAST = 2


def cf_evaluate_js_string(string):
    try:
        offset = 1 if string[0] == '+' else 0
        return int(
            eval(string.replace('!+[]', '1').replace('!![]', '1').replace('[]', '0').replace('(', 'str(')[offset:]))
    except:
        return


def cf_decrypt_ddos(url, agent, cookie_file):
    class NoRedirection(urllib2.HTTPErrorProcessor):
        def http_response(self, request, response):
            return response

    if len(agent) == 0:
        agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0'

    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(NoRedirection, urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', agent)]
    response = opener.open(url)

    try:
        set_cookie = str(response.headers.get('Set-Cookie'))
    except:
        set_cookie = ''

    print ['Set-Cookie', set_cookie]

    responce_html = response.read()

    js_header = '<link rel="shortcut icon" href="/Content/images/favicon.ico" type="image/x-icon" /><script type="text/javascript">'
    if js_header in responce_html:
        responce_html = responce_html.split(js_header)[-1]

    jschl = re.compile('name="jschl_vc" value="(.+?)"/>').findall(responce_html)[0]
    print ['jschl', jschl]

    try:
        cf_pass = re.compile('name="pass" value="(.+?)"/>').findall(responce_html)[0]
    except:
        cf_pass = ''

    print ['cf_pass', cf_pass]

    try:
        cf_challenge_form = \
            re.compile('<form id="challenge-form" action="(/[^"]+)" method="\D+">').findall(responce_html)[0]
    except:
        cf_challenge_form = '/cdn-cgi/l/chk_jschl'

    print ['cf_challenge_form', cf_challenge_form]

    init = re.compile(
        'setTimeout\(function\(\){\s*\n*\s*(?:var \D,\D,\D,\D, [0-9A-Za-z]+={"[0-9A-Za-z]+"|.*?.*):(.*?)};').findall(
        responce_html)[-1]
    print ['init', init]

    builder = re.compile(r"challenge-form\'\);\s*\n*\r*\a*\s*(.*)a.v").findall(responce_html)[0]
    print ['builder', builder]

    try:
        wait_time = int(re.compile(r"f.submit\(\);\s*\n*\s*},\s*(\d+)\)").findall(responce_html)[-1])
    except:
        wait_time = 5000

    print ['wait_time', wait_time]

    decrypt_value = cf_evaluate_js_string(init)
    print ['value_to_decrypt', decrypt_value]

    lines = builder.split(';')
    for line in lines:
        if len(line) > 0 and '=' in line:
            try:
                sections = line.split('=')
                line_val = cf_evaluate_js_string(sections[1])
                decrypt_value = int(eval(str(decrypt_value) + sections[0][-1] + str(line_val)))
            except:
                pass

    print ['decrypted_value', decrypt_value]

    hostname = get_domain_from_url(url)
    base_url = "http://" + hostname
    print ['base_url', base_url]
    print ['hostname', hostname, len(hostname)]

    answer = decrypt_value + len(hostname)
    print ['answer', answer]

    if cf_pass == '':
        query = '%s%s?jschl_vc=%s&jschl_answer=%s' % (str(base_url), str(cf_challenge_form), str(jschl), str(answer))
    else:
        query = '%s%s?jschl_vc=%s&pass=%s&jschl_answer=%s' % (
            str(base_url), str(cf_challenge_form), str(jschl), str(cf_pass), str(answer))
    print ['query', query]

    sleep(wait_time)

    opener = urllib2.build_opener(NoRedirection, urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', agent)]
    response = opener.open(query)
    cookie = str(response.headers.get('Set-Cookie'))
    print ['Set-Cookie', cookie]

    cj = cookielib.LWPCookieJar(cookie_file)
    cj.clear()
    request = urllib2.Request(url)
    cj.extract_cookies(response, request)
    response.close()

    final_response = opener.open(request)
    if final_response.code == 200:
        cj.save(cookie_file)
        return True

    return False


def sleep(wait_time):
    #xbmc.sleep(time)
    time.sleep(wait_time / 1000)


def get_domain_from_url(url):
    hostname = urlparse.urlparse(url).hostname
    if '/' in hostname:
        hostname = hostname.replace('/', '')

    if 'www.' in hostname:
        hostname = hostname.replace('www.', '')

    return hostname


def is_cookie_expired(url, net):
    domain = "." + get_domain_from_url(url)
    print domain
    for cookie in net._cj:
        if cookie.domain == domain:
            return cookie.is_expired()

    return True


def cf_generate_new_cookie(url, user_agent, cookie_file):
    retries = 10
    while retries > 0 and not cf_decrypt_ddos(url, user_agent, cookie_file):

        sleep(1)
        retries -= 1

    return retries > 0


def create_request(url, headers={}, data=None):
    try:
        return net.http_GET(url, headers=headers).content

    except:
        # Possible Cloudflare DDOS Protection
        net._cj.clear()
        #net.set_cookies(cf_cookie_file)

        #if is_cookie_expired(url, net):
        print "cookie_expired"
        cf_generate_new_cookie(url, user_agent, cf_cookie_file)
        net.set_cookies(cf_cookie_file)
        net.set_user_agent(user_agent)
        response = net.http_GET(url, headers=headers)
        net.save_cookies(cf_cookie_file)
        return response.content


def create_titles(raw_titles):
    titles = []
    for raw_title in raw_titles:
        titles.append(create_title(raw_title))
    return titles


def resolve_video_and_subtitles_url(base_url, path):
    title_html = create_request(base_url + path)
    query = BeautifulSoup(title_html, "html.parser")

    query_data = query("script", {"src": re.compile("php")})
    # php_link = ""
    # if (len(query_data) == 0):
    #     php_link = query("script", {"data-rocketsrc": re.compile("php")})[0].attrs["data-rocketsrc"]
    # else:
    php_link = query_data[0].attrs["src"]

    print(php_link)

    if base_url not in php_link:
        php_link = base_url + php_link
    player_data = create_request(php_link, {'Referer': base_url + path})

    #video_url = urllib.quote(re.findall(r'"(https?://\S+\.\w{3,4})"', player_data)[0], safe="%/:=&?~#+!$,;'@()*[]")
    video_url = eval('"' + player_data.split('["')[1].split('"]')[0] + '"')
    print(video_url)
    subtitles_url = base_url + urllib.quote(re.findall(r"(/subtitles/\S+\.srt)", player_data)[0], safe="%/:=&?~#+!$,;'@()*[]")

    return {"video": video_url, "subtitles": subtitles_url}


def create_title(raw_title):
    url = raw_title.attrs["href"]
    thumb = raw_title("div", {"class": "img"})[0].attrs["style"].partition("'")[-1].rpartition("'")[0]
    name = raw_title("div", {"class": "title"})[0].text.encode('utf-8')
    year = raw_title("div", {"class": "year"})[0].text.encode('utf-8')
    imdb = raw_title("div", {"class": "imdb"})[0].text.partition(" ")[-1].encode('utf-8')
    return {"url": url, "thumb": thumb, "name": name, "year": year, "imdb": imdb}


def get_movie_titles(page=1, order=TUGA_IO_ORDER_BY_LAST, latest=1, genre=0):
    html = create_request(TUGA_IO_URL +
                          TUGA_IO_MOVIES.format(page=page, order=order, latest=latest, genre=genre))
    return find_titles(html, 'filme')


def get_tv_titles(page=1, order=TUGA_IO_ORDER_BY_LAST, latest=1, genre=0):
    html = create_request(TUGA_IO_URL +
                          TUGA_IO_SERIES.format(page=page, order=order, latest=latest, genre=genre))
    return find_titles(html, 'serie')


def get_tv_show_seasons(url):
    html = create_request(TUGA_IO_URL + url)
    return find_seasons(html)


def get_tv_season_titles(url, season):
    html = create_request(TUGA_IO_URL + url)
    return find_tv_titles(html, season)


def find_titles(html, title_type):
    query = BeautifulSoup(html, "html.parser")
    return query.find_all(href=re.compile("/" + title_type + "/"))


def find_seasons(html):
    query = BeautifulSoup(html, "html.parser")
    return query.find_all("h2")


def find_tv_titles(html, season):
    query = BeautifulSoup(html, "html.parser")
    return query.find('h2', text=season).parent(href=re.compile("/episodio/"))


def search():
    search_data = urllib.urlencode({"procurar": "archer"})
    html = create_request(TUGA_IO_URL + "/procurar")
    movies = find_titles(html, 'filme')
    # series = find_titles(html, 'serie')


def build_url(query):
    return base_url + '?' + urllib.urlencode(query)


def create_root_menu():
    movies_year_folder = xbmcgui.ListItem("Filmes (Ano)", iconImage=None, thumbnailImage=None)
    movies_last_folder = xbmcgui.ListItem("Filmes (Ultimos)", iconImage=None, thumbnailImage=None)
    series_year_folder = xbmcgui.ListItem("Series (Ano)", iconImage=None, thumbnailImage=None)
    series_last_folder = xbmcgui.ListItem("Series (Ultimos)", iconImage=None, thumbnailImage=None)
    settings_folder = xbmcgui.ListItem("Definicoes", iconImage=None, thumbnailImage=None)

    # movies listItems
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "list", "folder": "movies", "page": "1", "order": TUGA_IO_ORDER_BY_YEAR}),
                                listitem=movies_year_folder, isFolder=True)
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "list", "folder": "movies", "page": "1", "order": TUGA_IO_ORDER_BY_LAST}),
                                listitem=movies_last_folder, isFolder=True)

    # series listItems
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "list", "folder": "series", "page": TUGA_IO_ORDER_BY_YEAR}),
                                listitem=series_year_folder, isFolder=True)
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "list", "folder": "series", "page": TUGA_IO_ORDER_BY_LAST}),
                                listitem=series_last_folder, isFolder=True)

    # other listItems
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=build_url({"action": "settings"}),
                                listitem=settings_folder, isFolder=True)

    xbmc.executebuiltin("Container.SetViewMode(%s)" % addon.getSetting("menuView"))
    xbmcplugin.endOfDirectory(addon_handle)


def create_titles_menu():

    # extract item args
    page = int(args.get('page', '1')[0])
    folder = args.get('folder', None)[0]
    order = args.get('order', str(TUGA_IO_ORDER_BY_LAST))[0]

    if folder == "movies":
        titles_html = get_movie_titles(page=page, order=order)
        action = 'play'
        is_playable = 'true'
        is_folder = False
        view = "moviesView"

    elif folder == "series":
        titles_html = get_tv_titles(page=page, order=order)
        action = "seasons"
        is_playable = 'false'
        view = "seriesView"
        is_folder = True

    titles = create_titles(titles_html)

    for title in titles:
        title['action'] = action
        title['base_url'] = TUGA_IO_URL

        url = build_url(title)
        title_item = xbmcgui.ListItem(title['name'], iconImage=build_url_with_cookie(TUGA_IO_URL, title["thumb"]),
                                      thumbnailImage=build_url_with_cookie(TUGA_IO_URL, title["thumb"]))
        title_item.setInfo('Video', {'Year': title['year'], 'Rating': title['imdb'], })
        title_item.setProperty('IsPlayable', is_playable)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=title_item, isFolder=is_folder)

    if len(titles) == TUGA_IO_PAGE_SIZE:
        next_folder = xbmcgui.ListItem("Proxima pagina", iconImage=None, thumbnailImage=None)
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=build_url({"action": "list", "folder": folder, "page": str(page + 1), "order": order}),
                                    listitem=next_folder, isFolder=True)

    xbmc.executebuiltin("Container.SetViewMode(%s)" % addon.getSetting(view))
    xbmcplugin.endOfDirectory(addon_handle)


def build_url_with_cookie(base_url, relative_path=''):
    tuga_io_cookie_key = '.tuga.io'
    cf_clearance_key = "cf_clearance"

    if tuga_io_cookie_key in net._cj._cookies and cf_clearance_key in net._cj._cookies[tuga_io_cookie_key]['/']:
        return base_url + relative_path + '|User-Agent=' + user_agent + '&Cookie=cf_clearance=' +\
           net._cj._cookies[tuga_io_cookie_key]['/'][cf_clearance_key].value

    return base_url + relative_path


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
        title_item = xbmcgui.ListItem(title['name'], iconImage=build_url_with_cookie(TUGA_IO_URL, title["thumb"]),
                                      thumbnailImage=build_url_with_cookie(TUGA_IO_URL, title["thumb"]))
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
    play_item = xbmcgui.ListItem(name, iconImage=build_url_with_cookie(tugaio_base_url, thumb), thumbnailImage=build_url_with_cookie(tugaio_base_url, thumb),
                                 path=resolved_url["video"])
    play_item.setSubtitles([build_url_with_cookie(resolved_url["subtitles"])])
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

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:40.0) Gecko/20100101 Firefox/40.0'
cf_cookie_file = os.path.join(os.path.dirname(__file__), 'tugaio.cache')

net = Net()
net.set_cookies(cf_cookie_file)
net.set_user_agent(user_agent)


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
