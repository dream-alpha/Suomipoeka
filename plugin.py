#!/usr/bin/python
# encoding: utf-8
#
# Suomipoeka plugin by moveq
# Copyright (C) 2007-2010 moveq / Suomipoeka team (suomipoeka@gmail.com)
# In case of reuse of this source code please do not remove this copyright.
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	For more information on the GNU General Public License see:
#	<http://www.gnu.org/licenses/>.
#
from Plugins.Plugin import PluginDescriptor
from Components.config import *
from Components.Language import language
from SuomipoekaTasker import spTasker, spDebugOut
from Suomipoeka import _, localeInit, SuomipoekaVersion, suomipoekaStartup, SuomipoekaMenu

def langList():
	newlist = []
	for e in language.getLanguageList():
		newlist.append( (e[0], _(e[1][0])) )
	return newlist

def langListSel():
	newlist = []
	for e in language.getLanguageList():
		newlist.append( _(e[1][0]) )
	return newlist

config.suomipoeka = ConfigSubsection()
config.suomipoeka.about = ConfigSelection(default = "1", choices = [("1", " ")])
config.suomipoeka.extmenu_plugin = ConfigYesNo()
config.suomipoeka.extmenu_list = ConfigYesNo()
config.suomipoeka.epglang = ConfigSelection(default = language.getActiveLanguage(), choices = langList() )
config.suomipoeka.sublang1 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.suomipoeka.sublang2 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.suomipoeka.sublang3 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.suomipoeka.audlang1 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.suomipoeka.audlang2 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.suomipoeka.audlang3 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.suomipoeka.autosubs = ConfigYesNo(default = True)
config.suomipoeka.autoaudio = ConfigYesNo(default = True)
config.suomipoeka.key_period = ConfigInteger(default = 100, limits = (30,900))
config.suomipoeka.key_repeat = ConfigInteger(default = 500, limits = (250,900))
config.suomipoeka.enigmarestart = ConfigYesNo(default = False)
config.suomipoeka.enigmarestart_begin = ConfigClock(default = 60*60*2)
config.suomipoeka.enigmarestart_end = ConfigClock(default = 60*60*5)
config.suomipoeka.enigmarestart_stby = ConfigYesNo()
config.suomipoeka.debug = ConfigYesNo()
config.suomipoeka.folder = ConfigText(default = "/hdd/suomipoeka", fixed_size = False, visible_width = 22)
config.suomipoeka.debugfile = ConfigText(default = "output.txt", fixed_size = False, visible_width = 22)
config.suomipoeka.ml_disable = ConfigYesNo()
config.suomipoeka.movie_bluefunc = ConfigSelection(default = "Movie home", choices = [("Movie home", _("Movie home")), ("Play last", _("Play last"))])
config.suomipoeka.movie_descdis = ConfigYesNo()
config.suomipoeka.movie_descdelay = ConfigInteger(default = 200, limits = (10,999))
config.suomipoeka.movie_icons = ConfigYesNo(default = True)
config.suomipoeka.movie_mark = ConfigYesNo(default = True)
config.suomipoeka.movie_metaload = ConfigYesNo(default = True)
config.suomipoeka.movie_reopen = ConfigYesNo()
config.suomipoeka.movie_reopenEOF = ConfigYesNo()
config.suomipoeka.movie_reload = ConfigYesNo()
config.suomipoeka.movie_homepath = ConfigText(default = "/hdd/movie", fixed_size = False, visible_width = 22)
config.suomipoeka.movie_pathlimit = ConfigText(default = "/hdd/movie", fixed_size = False, visible_width = 22)
config.suomipoeka.movie_trashpath = ConfigText(default = "/hdd/movie/.trashcan", fixed_size = False, visible_width = 22)
config.suomipoeka.movie_trashcan_hide = ConfigYesNo()
config.suomipoeka.movie_trashcan_limit = ConfigInteger(default = 7, limits = (0,999))
config.suomipoeka.movie_trashcan_clean = ConfigYesNo(default = True)
config.suomipoeka.movie_trashcan_ctime = ConfigClock(default = 0)
config.suomipoeka.movie_vlc_hide = ConfigYesNo()
config.suomipoeka.movie_hide_mov = ConfigYesNo()
config.suomipoeka.movie_hide_del = ConfigYesNo()
config.suomipoeka.movielist_reversed = ConfigYesNo()
config.suomipoeka.movielist_gotonewest = ConfigYesNo()
config.suomipoeka.movielist_gotonewestp = ConfigYesNo()
config.suomipoeka.movielist_selmove = ConfigSelection(default = "d", choices = [("d", _("down")), ("b", _("up/down")), ("o", _("off"))])
config.suomipoeka.movielist_loadtext = ConfigYesNo(default = True)
config.suomipoeka.timer_autocln = ConfigYesNo()

launch_choices = [	("None", _("No override")),
					("showMovies", _("Video-button")),
					("showTv", _("TV-button")),
					("showRadio", _("Radio-button")),
					("openQuickbutton", _("Quick-button")),
					("timeshiftStart", _("Timeshift-button"))]
config.suomipoeka.movie_launch = ConfigSelection(default = "showMovies", choices = launch_choices)

gSession = None
gRecordings = None

def showMoviesNew(dummy_self = None):
	try:
		global gSession, gRecordings
		gSession.execDialog(gRecordings)
	except Exception, e:
		spDebugOut("[showMoviesNew] exception:\n" + str(e))

def autostart(reason, **kwargs):
	if reason == 0: # start
		if kwargs.has_key("session"):
			global gSession
			gSession = kwargs["session"]

			suomipoekaStartup(gSession)
			spTasker.Initialize(gSession)

			if not config.suomipoeka.ml_disable.value:
				try:
					from Screens.InfoBar import InfoBar
					value = config.suomipoeka.movie_launch.value
					if value == "showMovies":			InfoBar.showMovies = showMoviesNew
					elif value == "showTv":				InfoBar.showTv = showMoviesNew
					elif value == "showRadio":			InfoBar.showRadio = showMoviesNew
					elif value == "openQuickbutton":	InfoBar.openQuickbutton = showMoviesNew
					elif value == "timeshiftStart":		InfoBar.startTimeshift = showMoviesNew
				except Exception, e:
					spDebugOut("[spStartup] MovieList launch override exception:\n" + str(e))

				try:
					global gRecordings
					from MovieSelection import MovieSelectionSP
					gRecordings = gSession.instantiateDialog(MovieSelectionSP)
				except Exception, e:
					spDebugOut("[spStartup] instantiateDialog exception:\n" + str(e))

def pluginOpen(session, **kwargs):
	try:
		session.open(SuomipoekaMenu)
	except Exception, e:
		spDebugOut("[pluginOpen] exception:\n" + str(e))

def recordingsOpen(session, **kwargs):
	showMoviesNew()

def Plugins(**kwargs):
	localeInit()
	descriptors = [PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, fnc = autostart)]

	show_p = [ PluginDescriptor.WHERE_PLUGINMENU ]
	if config.suomipoeka.extmenu_plugin.value:
		show_p.append( PluginDescriptor.WHERE_EXTENSIONSMENU )

	descriptors.append( PluginDescriptor(name = "Suomipoeka "+SuomipoekaVersion, description = "Suomipoeka " +_("configuration"), icon = "Suomipoeka.png", where = show_p, fnc = pluginOpen) )

	if config.suomipoeka.extmenu_list.value and not config.suomipoeka.ml_disable.value:
		descriptors.append( PluginDescriptor(name = "Suomipoeka MovieList", description = "Suomipoeka " + _("movie manipulation list"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = recordingsOpen) )
	return descriptors
