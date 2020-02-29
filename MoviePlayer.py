#!/usr/bin/python
# encoding: utf-8
#
# New movie player written by moveq
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
from enigma import eTimer, iPlayableService
from Components.config import *
from Components.ActionMap import HelpableActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Screens.Screen import Screen
from Screens.InfoBarGenerics import InfoBarSeek
from Screens.InfoBar import MoviePlayer, InfoBar
from Screens.MessageBox import MessageBox

from Suomipoeka import _
from SuomipoekaTasker import spDebugOut
from DelayedFunction import DelayedFunction

import os

gStopped = False
gClosedByDelete = False
gPlayerOpenedList = False

def movieListState(state):
	global gPlayerOpenedList
	gPlayerOpenedList = state
	#spDebugOut("[spPlayer] movieListState = %s" %str(state))


class MoviePlayerSP(MoviePlayer):
	def __init__(self, session, playlist, recordings):
		# MoviePlayer.__init__ will start playback for the given service!!
		MoviePlayer.__init__(self, session, session.nav.getCurrentlyPlayingServiceReference())
		self.skinName = "MoviePlayer"

		self["actions"] = HelpableActionMap(self, "PluginPlayerActions",
			{
				"bInfo":		(self.openEventView,	_("show event details")),
				"leavePlayer":	(self.leavePlayer,		_("Stop playback")),
				"bRADIO":		(self.btnRadio, 		_("Open extensions menu"))
			})

		self.playInit(playlist, recordings)
		self.onShown.append(self.onDialogShow)

	def __del__(self):
		try:
			from MovieSelection import gMS
			global gStopped, gClosedByDelete, gPlayerOpenedList
			if gStopped:
				spDebugOut("[spPlayer] Player closed by user")
				if config.suomipoeka.movie_reopen.value:
					DelayedFunction(80, gMS.session.execDialog, gMS)		# doesn't crash Enigma2 subtitle functionality
			elif gClosedByDelete:
				spDebugOut("[spPlayer] closed due to file delete")
				DelayedFunction(80, gMS.session.execDialog, gMS)		# doesn't crash Enigma2 subtitle functionality
			else:
				spDebugOut("[spPlayer] closed due to playlist EOF")
				if config.suomipoeka.movie_reopenEOF.value:
					DelayedFunction(80, gMS.session.execDialog, gMS)
				if gPlayerOpenedList: # did the player close while movie list was open?
					DelayedFunction(80, gMS.session.execDialog, gMS)		# doesn't crash Enigma2 subtitle functionality
			movieListState(False)
		except Exception, e:
			spDebugOut("[spPlayer] __del__ exception:\n" + str(e))

	def playInit(self, playlist, recordings):
		self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.playlist = playlist
		self.playcount = -1
		self.recordings = recordings
		self.firstStart = False
		self.currentlyPlaying = None
		self.recordings.setPlayerInstance(self)

	def onDialogShow(self):
		if self.firstStart:
			return
		self.firstStart = True
		self.evEOF()	# begin playback

	def btnRadio(self):
		try:
			InfoBar.instance.showExtensionSelection()
		except Exception, e:
			spDebugOut("[spPlayer] btnRadio exception:\n" + str(e))

	def doEofInternal(self, playing): # override from InfoBar.py
		DelayedFunction(2000, self.evEOF)

	def evEOF(self, needToClose=False):
		# see if there are more to play
		if (self.playcount+1) < len(self.playlist):
			self.playcount += 1
			service = self.playlist[self.playcount]
			self.currentlyPlaying = service
			if os.path.exists(service.getPath()):
				self.recordings.viewedToggle(service, True)		# rename .cutsr to .cuts if user has toggled it
				self.session.nav.playService(service)
				self.currentlyPlaying = service
				self.setSeekState(InfoBarSeek.SEEK_STATE_PLAY)
				self.doSeek(0)
				DelayedFunction(200, self.setAudioTrack)
				DelayedFunction(1000, self.setSubtitleState, True)
			else:
				self.session.open(MessageBox, _("Skipping movie, the file does not exist.\n\n") + service.getPath(), MessageBox.TYPE_ERROR, 10)
				self.evEOF(needToClose)
		else:
			if 0:
				MoviePlayer.handleLeave(self, config.usage.on_movie_eof.value)
			else:
				if needToClose or config.usage.on_movie_eof.value != "pause":	# ask, movielist, quit or pause
					global gClosedByDeleteleavePlayer
					gClosedByDelete = needToClose
					self.leavePlayer(False)

	def leavePlayer(self, stopped=True):
		self.setSubtitleState(False)
		global gPlayerOpenedList, gStopped
		gStopped = stopped
		if gPlayerOpenedList and not stopped:	# for some strange reason "not stopped" has to be checked to avoid a bug (???)
			self.recordings.close(None)
			#spDebugOut("[spPlayer] closing movie list")
		self.recordings.setPlayerInstance(None)
#		self.close(None)	# triggers the destructor
#		self.session.nav.playService(self.lastservice)
		self.close(self.lastservice)

	def showMovies(self):
		try:
			movieListState(True)
			DelayedFunction(20, self.session.execDialog, self.recordings)
		except Exception, e:
			spDebugOut("[spPlayer] showMovies exception:\n" + str(e))

	def removeFromPlaylist(self, deletedlist):
		callEOF = False
		for x in deletedlist:
			xp = x.getPath().split("/")[-1]
			if xp == self.currentlyPlaying.getPath().split("/")[-1]:
				callEOF = True
			for p in self.playlist:
				if xp == p.getPath().split("/")[-1]:
					self.playlist.remove(p)
		if callEOF:
			#spDebugOut("[spPlayer] removeFromPlaylist: calling EOF")
			self.playcount -= 1	# need to go one back since the current was removed
			self.evEOF(True)	# force playback of the next movie or close the player if none left

	def currentlyPlayedMovie(self):
		return self.currentlyPlaying

	def movieSelected(self, playlist):
		movieListState(False)
		if playlist is not None and len(playlist) > 0:
			#spDebugOut("[spPlayer] movieSelected: Playlist len = " + str(len(playlist)))
			self.playcount = -1
			self.playlist = playlist
			self.evEOF()	# start playback of the first movie
#		else:
#			spDebugOut("[spPlayer] list closed, no movie selected...")

	def tryAudioEnable(self, alist, match, tracks):
		index = 0
		for e in alist:
			if e.find(match) >= 0:
				spDebugOut("[spPlayer] audio track match: " + str(e))
				tracks.selectTrack(index)
				return True
			index += 1
		return False

	def setAudioTrack(self):
		try:
			if not config.suomipoeka.autoaudio.value: return
			from Tools.ISO639 import LanguageCodes as langC
			service = self.session.nav.getCurrentService()
			tracks = service and service.audioTracks()
			nTracks = tracks and tracks.getNumberOfTracks() or 0
			if nTracks == 0: return
			trackList = []
			for i in range(nTracks):
				audioInfo = tracks.getTrackInfo(i)
				lang = audioInfo.getLanguage()
				if langC.has_key(lang):
					lang = langC[lang][0]
				desc = audioInfo.getDescription()
				trackList += [str(lang) + " " + str(desc)]
#				spDebugOut("[spPlayer] audioTrack language: " + str(lang) + " " + str(desc))
			for audiolang in [config.suomipoeka.audlang1.value, config.suomipoeka.audlang2.value, config.suomipoeka.audlang3.value]:
				if self.tryAudioEnable(trackList, audiolang, tracks): break
		except Exception, e:
			spDebugOut("[spPlayer] audioTrack exception:\n" + str(e))

	def trySubEnable(self, slist, match):
		for e in slist:
			if match == e[2]:
				spDebugOut("[spPlayer] subtitle match: " + str(e))
				if self.selected_subtitle != e[0]:
					self.subtitles_enabled = False
					self.selected_subtitle = e[0]
					self.subtitles_enabled = True
					return True
		return False

	def setSubtitleState(self, enabled):
		try:
			if not config.suomipoeka.autosubs.value or not enabled: return
			from Tools.ISO639 import LanguageCodes as langC
			s = self.getCurrentServiceSubtitle()
			lt = [ (e, (e[0]==0 and "DVB" or e[0]==1 and "TXT" or "???")) for e in (s and s.getSubtitleList() or [ ]) ]
			l = [ [e[0], e[1], langC.has_key(e[0][4]) and langC[e[0][4]][0] or e[0][4] ] for e in lt ]
			for sublang in [config.suomipoeka.sublang1.value, config.suomipoeka.sublang2.value, config.suomipoeka.sublang3.value]:
				if self.trySubEnable(l, sublang): break
		except Exception, e:
			spDebugOut("[spPlayer] setSubtitleState exception:\n" + str(e))

	def startCheckLockTimer(self):
		# LT image specific
		pass
