# -*- coding: utf-8 -*-
#

import xbmcaddon
import xbmcgui

import utilities

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )
__language__ = __settings__.getLocalizedString


def _updateXBMCMoviePlaycounts(playcount_list, progress, daemon):
    """Updates playcounts from the list passed to it and updates the progress bar"""
    count = len(playcount_list)
    index = 0

    if not daemon:
        progress.update(0, "Setting XBMC Playcounts")

    for movieid, playcount, imdbid in playcount_list:
        utilities.setXBMCMoviePlaycount(movieid, playcount, imdbid)
        index += 1

        if not daemon:
            if progress.iscanceled():
                return
            progress.update(int(float(index)/count*100), "Setting XBMC Playcounts")


def cleanMovies(daemon=False):
    """Cleans trakt.tv movie database.

    Checks if trakt contains any movies that the xbmc database doesn't and if any
    are found unlibraries them on trakt.
    """
    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", "Cleaning Movies")

    trakt_movies = utilities.traktMovieListByImdbID(utilities.getMoviesFromTrakt())
    xbmc_movies = utilities.xbmcMovieListByImdbID(utilities.getMoviesFromXBMC())

    clean_list = []
    index = 0
    length = len(trakt_movies)

    for imdbid in trakt_movies:
        if not daemon:
            index += 1
            progress.update(int(float(index)/length*100), "Cleaning Movies")

        if imdbid not in xbmc_movies:
            clean_list.append({'imdb_id': imdbid, 'title': trakt_movies[imdbid]['title'], 'year': trakt_movies[imdbid]['year']})

    if len(clean_list) > 0:
        utilities.traktJsonRequest('POST', '/movie/unlibrary/%%API_KEY%%', {'movies': clean_list})

    if not daemon:
        progress.close()


def syncMovies(daemon=False):
    """Sync playcounts and collection status between trakt and xbmc.

    Scans XBMC and trakt and updates the play count of each movie in both the xbmc
    and trakt libraries based on which is higher. If the movie exists in xbmc
    but is not collected in trakt it is set as collected too.
    """
    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", "Generating Movie Lists") # Checking XBMC Database for new seen Movies

    # Generate list of movies keyed with their imdb id
    trakt_movies = utilities.traktMovieListByImdbID(utilities.getMoviesFromTrakt())
    xbmc_movies = utilities.xbmcMovieListByImdbID(utilities.getMoviesFromXBMC())

    xbmc_playcount_update = []
    trakt_playcount_update = []
    trakt_collection_update = []

    for imdbid in xbmc_movies:
        if imdbid not in trakt_movies:
            if xbmc_movies[imdbid]['playcount'] > 0:
                trakt_collection_update.append({'imdb_id': imdbid, 'title': xbmc_movies[imdbid]['title'], 'year': xbmc_movies[imdbid]['year']})
                trakt_playcount_update.append({'imdb_id': imdbid, 'title': xbmc_movies[imdbid]['title'], 'year': xbmc_movies[imdbid]['year'], 'plays': xbmc_movies[imdbid]['playcount'], 'last_played': xbmc_movies[imdbid]['lastplayed']})
            else:
                trakt_collection_update.append({'imdb_id': imdbid, 'title': xbmc_movies[imdbid]['title'], 'year': xbmc_movies[imdbid]['year']})
            continue

        if xbmc_movies[imdbid]['playcount'] > trakt_movies[imdbid]['plays']:
            trakt_playcount_update.append({'imdb_id': imdbid, 'title': xbmc_movies[imdbid]['title'], 'year': xbmc_movies[imdbid]['year'], 'plays': xbmc_movies[imdbid]['playcount'], 'last_played': xbmc_movies[imdbid]['lastplayed']})
        elif xbmc_movies[imdbid]['playcount'] < trakt_movies[imdbid]['plays']:
            xbmc_playcount_update.append((xbmc_movies[imdbid]['movieid'], trakt_movies[imdbid]['plays'], imdbid))

    if not daemon:
        progress.update(0, "Updating Movies On Trakt")

    if len(trakt_collection_update) > 0:
        utilities.traktJsonRequest('POST', '/movie/library/%%API_KEY%%', {'movies': trakt_collection_update})

    if len(trakt_playcount_update) > 0:
        utilities.setMoviesSeenOnTrakt(trakt_playcount_update)

    if len(xbmc_playcount_update) > 0:
        if not daemon:
            _updateXBMCMoviePlaycounts(xbmc_playcount_update, None, False)
        else:
            _updateXBMCMoviePlaycounts(xbmc_playcount_update, progress, daemon)

    if not daemon:
        progress.close()


def _parseXBMCStructure():
    """Generate a useful structure for TV syncing from XBMC"""
    xbmc_raw_shows = utilities.getTVShowsFromXBMC()
    xbmc_raw_episodes = utilities.getEpisodesFromXBMC()
    xbmc_map_tvshowid_tvdbid = {}

    xbmc_shows = {}

    for show in xbmc_raw_shows:
        xbmc_map_tvshowid_tvdbid[show['tvshowid']] = show['imdbnumber']
        xbmc_shows[show['imdbnumber']] = {}
        xbmc_shows[show['imdbnumber']]['year'] = show['year']
        xbmc_shows[show['imdbnumber']]['title'] = show['title']
        xbmc_shows[show['imdbnumber']]['data'] = {}

    for episode in xbmc_raw_episodes:
        tvdbid = xbmc_map_tvshowid_tvdbid[episode['tvshowid']]
        season_num = episode['season']
        episode_num = episode['episode']

        if not season_num in xbmc_shows[tvdbid]['data']:
            xbmc_shows[tvdbid]['data'][season_num] = {}

        xbmc_shows[tvdbid]['data'][season_num][episode_num] = (episode['episodeid'], episode['playcount'])

    return xbmc_shows


def _parseTraktStructure():
    """Generate a useful structure for TV syncing with Trakt"""
    trakt_shows = {}
    trakt_collected = utilities.getTVShowCollectionFromTrakt()
    trakt_watched = utilities.getWatchedTVShowsFromTrakt()

    for show in trakt_collected:
        tvdbid = show['tvdb_id']
        trakt_shows[tvdbid] = {}
        trakt_shows[tvdbid]['title'] = show['title']
        trakt_shows[tvdbid]['year'] = show['year']
        trakt_shows[tvdbid]['data'] = {}

        for season in show['seasons']:
            seasonid = season['season']
            trakt_shows[tvdbid]['data'][seasonid] = {}

            for episode in season['episodes']:
                trakt_shows[tvdbid]['data'][seasonid][episode] = (True, False) # (Collected, Watched)

    for show in trakt_watched:
        tvdbid = show['tvdb_id']
        if tvdbid not in trakt_shows:
            trakt_shows[tvdbid] = {}
            trakt_shows[tvdbid]['title'] = show['title']
            trakt_shows[tvdbid]['year'] = show['year']
            trakt_shows[tvdbid]['data'] = {}

        for season in show['seasons']:
            seasonid = season['season']
            if seasonid not in trakt_shows[tvdbid]['data']:
                trakt_shows[tvdbid]['data'][seasonid] = {}

            for episode in season['episodes']:
                if episode not in trakt_shows[tvdbid]['data'][seasonid]:
                    trakt_shows[tvdbid]['data'][seasonid][episode] = (False, True)
                else:
                    trakt_shows[tvdbid]['data'][seasonid][episode] = (True, True)

    return trakt_shows


def _generateShowNotOnTrakt(shows, tvdbid):
    """Generate the collected and watched episodes from XBMC for a show that's not on trakt"""
    watched_episodes = {}
    collected_episodes = {}

    watched_episodes['tvdb_id'] = collected_episodes['tvdb_id'] = tvdbid
    watched_episodes['title'] = collected_episodes['title'] = shows[tvdbid]['title']
    watched_episodes['year'] = collected_episodes['year'] = shows[tvdbid]['year']
    watched_episodes['episodes'], collected_episodes['episodes'] = [], []

    for season_num in shows[tvdbid]['data']:
        for episode_num in shows[tvdbid]['data'][season_num]:
            playcount = shows[tvdbid]['data'][season_num][episode_num][1]
            if playcount > 0:
                watched_episodes['episodes'].append({'season': season_num, 'episode': episode_num})
            collected_episodes['episodes'].append({'season': season_num, 'episode': episode_num})

    if len(watched_episodes['episodes']) == 0:
        watched_episodes = None
    if len(collected_episodes['episodes']) == 0:
        collected_episodes = None

    return (collected_episodes, watched_episodes)


def _generateShowOnTrakt(xbmc_shows, trakt_shows, tvdbid):
    """Generate the collected and watched episodes from both XBMC and Trakt for a show that's on trakt"""
    version = utilities.getXBMCMajorVersion()

    watched_episodes = {}
    collected_episodes = {}

    watched_episodes['tvdb_id'] = collected_episodes['tvdb_id'] = tvdbid
    watched_episodes['title'] = collected_episodes['title'] = trakt_shows[tvdbid]['title']
    watched_episodes['year'] = collected_episodes['year'] = trakt_shows[tvdbid]['year']
    watched_episodes['episodes'], collected_episodes['episodes'] = [], []

    xbmc_new_plays = []

    for season_num in xbmc_shows[tvdbid]['data']:
        for episode_num in xbmc_shows[tvdbid]['data'][season_num]:
            xbmc_episodeid, xbmc_played = xbmc_shows[tvdbid]['data'][season_num][episode_num]
            try:
                trakt_collected, trakt_played = trakt_shows[tvdbid]['data'][season_num][episode_num]
            except KeyError:
                trakt_collected, trakt_played = False, False

            if not trakt_collected:
                collected_episodes['episodes'].append({'season': season_num, 'episode': episode_num})
            if not trakt_played and xbmc_played > 0:
                watched_episodes['episodes'].append({'season': season_num, 'episode': episode_num})
            if xbmc_played == 0 and trakt_played:
                if version >= 12:
                    xbmc_new_plays.append(xbmc_episodeid)
                else:
                    xbmc_new_plays.append((tvdbid, season_num, episode_num))

    if len(watched_episodes['episodes']) == 0:
        watched_episodes = None
    if len(collected_episodes['episodes']) == 0:
        collected_episodes = None

    return (collected_episodes, watched_episodes, xbmc_new_plays)


def _sendEpisodesToTrakt(collected, watched):
    """Send collected and watched statuses to trakt"""
    conn = utilities.getTraktConnection()
    for to_send in collected:
        utilities.traktJsonRequest('POST', '/show/episode/library/%%API_KEY%%', to_send, conn=conn)
    for to_send in watched:
        utilities.traktJsonRequest('POST', '/show/episode/seen/%%API_KEY%%', to_send, conn=conn)


def _updateXBMCEpisodePlaycounts(watched_episodes):
    """Update the playcount of the passed episodes"""
    version = utilities.getXBMCMajorVersion()

    if version >= 12:
        xbmc_update = []
        for episodeid in watched_episodes:
            xbmc_update.append({'jsonrpc': '2.0', 'method': 'VideoLibrary.SetEpisodeDetails', 'params':{'episodeid': episodeid, 'playcount': 1}, 'id': 1})

        if len(xbmc_update) > 0:
            utilities.setXBMCBulkEpisodePlaycount(xbmc_update)
    else:
        for tvdbid, season_num, episode_num in watched_episodes:
            utilities.setXBMCEpisodePlaycount(tvdbid, season_num, episode_num, 1)


def syncTV(daemon=False):
    """Sync playcounts and collection status between trakt and xbmc.

    Scans XBMC and trakt and updates the playcount of each episode in both the
    xbmc and trakt libraries. If the episode exists in xbmc but is not collected
    on trakt it is also set as collected on trakt.
    """
    collect_episodes = []
    watch_episodes = []

    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", "Generating TV Episode Lists")

    xbmc_shows = _parseXBMCStructure()
    trakt_shows = _parseTraktStructure()

    index = 0
    length = len(xbmc_shows)

    for tvdbid in xbmc_shows:
        if not daemon:
            if progress.iscanceled():
                return
            progress.update(int(float(index)/length*100), "Syncing Shows")

        index += 1

        if tvdbid not in trakt_shows:
            collect_trakt_episodes, watch_trakt_episodes = _generateShowNotOnTrakt(xbmc_shows, tvdbid)
        else:
            collect_trakt_episodes, watch_trakt_episodes, watched_xbmc_episodes = _generateShowOnTrakt(xbmc_shows, trakt_shows, tvdbid)
            _updateXBMCEpisodePlaycounts(watched_xbmc_episodes)

        if collect_trakt_episodes:
            collect_episodes.append(collect_trakt_episodes)
        if watch_trakt_episodes:
            watch_episodes.append(watch_trakt_episodes)

    if not daemon:
        progress.update(0, "Sending Data To Trakt")

    _sendEpisodesToTrakt(collect_episodes, watch_episodes)

    if not daemon:
        progress.close()

def _cleanShow(tvdbid, trakt_shows):
    """ Remove an entire show from the trakt library """
    to_send = {'tvdb_id': tvdbid, 'title': trakt_shows[tvdbid]['title'], 'year': trakt_shows[tvdbid]['year']}
    utilities.traktJsonRequest('POST', '/show/unlibrary/%%API_KEY%%', to_send)


def _cleanShowDiff(tvdbid, trakt_shows, xbmc_shows):
    """ Remove show episodes not on xbmc from the trakt library """
    to_send = {'tvdb_id': tvdbid, 'title': trakt_shows[tvdbid]['title'], 'year': trakt_shows[tvdbid]['year'], 'episodes': {}}
    xbmc_show = xbmc_shows[tvdbid]['data']
    trakt_show = trakt_shows[tvdbid]['data']

    for season_num in trakt_show:
        for episode_num in trakt_show[season_num]:
            if trakt_show[season_num][episode_num][0] == True and (season_num not in xbmc_show or episode_num not in xbmc_show[season_num]):
                to_send['episodes'].append({'season': season_num, 'episode': episode_num})

    utilities.traktJsonRequest('POST', '/show/episode/unlibrary', to_send)


def cleanTV(daemon=False):
    """Remove any shows and episodes on trakt that aren't in the XBMC library"""
    if not daemon:
        progress = xbmcgui.DialogProgress()
        progress.create("Trakt Utilities", "Generating TV Episode Lists")

    xbmc_shows = _parseXBMCStructure()
    trakt_shows = _parseTraktStructure()
    length = len(trakt_shows)
    index = 0

    for tvdbid in trakt_shows:
        if not daemon:
            index += 1
            progress.update(int(float(index)/length*100), "Cleaning Shows")

        if tvdbid not in xbmc_shows:
            _cleanShow(tvdbid, trakt_shows)
        else:
            _cleanShowDiff(tvdbid, trakt_shows, xbmc_shows)

    if not daemon:
        progress.close()
