# -*- coding: utf-8 -*-
#

import xbmcaddon
import utilities

__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.traktutilities" )

def ratingCheck(curVideo, watchedTime, totalTime, playlistLength):
    __settings__ = xbmcaddon.Addon( "script.traktutilities" ) #read settings again, encase they have changed
    # you can disable rating in options
    rateMovieOption = __settings__.getSetting("rate_movie")
    rateEpisodeOption = __settings__.getSetting("rate_episode")
    rateEachInPlaylistOption = __settings__.getSetting("rate_each_playlist_item")
    rateMinViewTimeOption = __settings__.getSetting("rate_min_view_time")

    if (watchedTime/totalTime)*100>=float(rateMinViewTimeOption):
        if (playlistLength <= 1) or (rateEachInPlaylistOption == 'true'):
            if curVideo['type'] == 'movie' and rateMovieOption == 'true':
                doRateMovie(curVideo['id'])
            if curVideo['type'] == 'episode' and rateEpisodeOption == 'true':
                doRateEpisode(curVideo['id'])

# ask user if they liked the movie
def doRateMovie(movieid=None, imdbid=None, title=None, year=None):
    if movieid != None:
        match = utilities.getMovieDetailsFromXbmc(movieid, ['imdbnumber', 'title', 'year'])
        if not match:
            #add error message here
            return

        imdbid = match['imdbnumber']
        title = match['title']
        year = match['year']

    # display rate dialog
    import windows
    gui = windows.RateMovieDialog("rate.xml", __settings__.getAddonInfo('path'), "Default")
    gui.initDialog(imdbid, title, year, utilities.getMovieRatingFromTrakt(imdbid, title, year))
    gui.doModal()
    del gui

# ask user if they liked the episode
def doRateEpisode(episodeId):
    match = utilities.getEpisodeDetailsFromXbmc(episodeId, ['showtitle', 'season', 'episode'])
    if not match:
        #add error message here
        return

    tvdbid = None #match['tvdbnumber']
    title = match['showtitle']
    year = None #match['year']
    season = match['season']
    episode = match['episode']

    # display rate dialog
    import windows
    gui = windows.RateEpisodeDialog("rate.xml", __settings__.getAddonInfo('path'), "Default")
    gui.initDialog(tvdbid, title, year, season, episode, utilities.getEpisodeRatingFromTrakt(tvdbid, title, year, season, episode))
    gui.doModal()
    del gui
