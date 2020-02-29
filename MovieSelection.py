#!/usr/bin/python
# encoding: utf-8
#
# Movie selection interface rewritten as an additional plugin by moveq
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
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import *
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Tools import Notifications
from time import localtime

from enigma import eServiceReference, eServiceCenter, eTimer, eSize, getDesktop
import os

from MovieList import MovieList
from MovieSelectionMenu import MovieMenu
from MoviePlayer import MoviePlayerSP
from SuomipoekaTasker import spTasker, spDebugOut
from Suomipoeka import _
from DelayedFunction import DelayedFunction
from VlcPluginInterface import VlcPluginInterfaceSel

gLastPlayedMovies = None
gMS = None

def mountpoint(path, first=True):
	if first: path = os.path.realpath(path)
	if os.path.ismount(path) or len(path)==0: return path
	return mountpoint(os.path.split(path)[0], False)


class SelectionEventInfo:
	def __init__(self):
		self["DescriptionBorder"] = Pixmap()
		self["Service"] = ServiceEvent()
		self["FileSize"] = Label("")
		self.prev_descdis = not config.suomipoeka.movie_descdis.value

	def updateEventInfo(self):
		if not config.suomipoeka.movie_descdis.value:
			try:
				if self["list"].currentSelIsDirectory() or self["list"].currentSelIsVlc():
					self["FileSize"].setText("")
					self["Service"].newService(None)
				else:
					serviceref = self.getCurrent()
					self["FileSize"].setText("(%d MB)" %(os.path.getsize(serviceref.getPath())/1048576))
					self["Service"].newService(serviceref)
			except Exception, e:
				spDebugOut("[spMS] updateEventInfo exception:\n" + str(e))

	def descFieldInit(self):
		if self.prev_descdis == config.suomipoeka.movie_descdis.value: return
		self.prev_descdis = config.suomipoeka.movie_descdis.value

		if config.suomipoeka.movie_descdis.value:
			width = self["list"].instance.size().width()
			height = self["list"].instance.size().height() - self["key_red"].instance.size().height() - 2
			self["list"].instance.resize(eSize(width, height))
			self["DescriptionBorder"].hide()
		else:
			width = self["list"].instance.size().width()
			height = self["list"].instance.size().height()
			
			self["list"].instance.resize(eSize(width, height))
			self["DescriptionBorder"].show()
			self.updateEventInfo()


class MovieSelectionSP(Screen, HelpableScreen, SelectionEventInfo, VlcPluginInterfaceSel):
	def __init__(self, session):
		Screen.__init__(self, session)
		SelectionEventInfo.__init__(self)
		CoolWide = getDesktop(0).size().width()
		skinpath = str(resolveFilename)
		self.skinName = "MovieSelectionSP"
		if CoolWide == 720:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/CoolSkin/MovieSelectionSP_720.xml"
		elif CoolWide == 1024:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/CoolSkin/MovieSelectionSP_1024.xml"
		else:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/CoolSkin/MovieSelectionSP_1280.xml"
		Cool = open(skin)
		self.skin = Cool.read()
		Cool.close()
		self.wasClosed = True
		self.playerInstance = None
		self.selectIdx = -1
		self.cursorDir = 0
		self.currentGrnText = _("Alpha sort")
		self["wait"] = Label(_("Reading directory..."))
		self["list"] = MovieList()
		self["key_red"] = Button()
		self["key_green"] = Button()
		self["key_yellow"] = Button()
		self["key_blue"] = Button()
		global gMS
		gMS = self
		self["actions"] = HelpableActionMap(self, "PluginMovieSelectionActions",
			{
				"bOK":		(self.movieSelected,		_("Play selected movie(s)")),
				"bOKL":		(self.unUsed,				"-"),
				"bEXIT":	(self.abort, 				_("Close movie list")),
				"bMENU":	(self.openMenu,				_("Open menu")),
				"bINFO":	(self.showEventInformation,	_("Show event info")),
				"bINFOL":	(self.unUsed,				"-"),
				"bRed":		(self.deleteFile,			_("Delete file or empty dir")),
				"bGreen":	(self.toggleSort,			_("Toggle sort mode")),
				"bYellow":	(self.moveMovie,			_("Move selected movie(s)")),
				"bBlue":	(self.blueFunc,				_("Movie home / Play last (configurable)")),
				"bRedL":	(self.unUsed,				"-"),
				"bGreenL":	(self.unUsed,				"-"),
				"bYellowL":	(self.openScriptMenu,		_("Open shell script menu")),
				"bBlueL":	(self.openBookmarks,		_("Open bookmarks")),
				"bLeftUp":	(self.keyPress,				_("Move cursor page up")),
				"bRightUp":	(self.keyPress,				_("Move cursor page down")),
				"bUpUp":	(self.keyPressU,			_("Move cursor up")),
				"bDownUp":	(self.keyPressD,			_("Move cursor down")),
				"bBqtPlus":	(self.bouquetPlus,			_("Move cursor 1/2 page up")),
				"bBqtMnus":	(self.bouquetMinus,			_("Move cursor 1/2 page down")),
				"bArrowR":	(self.unUsed,				"-"),
				"bArrowRL":	(self.unUsed,				"-"),
				"bArrowL":	(self.unUsed,				"-"),
				"bArrowLL":	(self.unUsed,				"-"),
				"bVIDEO":	(self.selectionToggle,		_("Toggle service selection")),
				"bAUDIO":	(self.openMenuPlugins,		_("Available plugins menu")),
				"bAUDIOL":	(self.unUsed,				"-"),
				"bMENUL":	(self.openMenuPlugins,		_("Available plugins menu")),
				"bTV":		(self.reloadList,			_("Reload movie file list")),
				"bTVL":		(self.unUsed,				"-"),
				"bRADIO":	(self.viewedToggle,			_("Toggle viewed / not viewed")),
				"bRADIOL":	(self.unUsed,				"-"),
				"bTEXT":	(self.multiSelect,			_("Start / end multiselection")),
				"bTEXTL":	(self.unUsed,				"-")
			})
		self["actions"].csel = self
		HelpableScreen.__init__(self)

		self.currentPathSel = config.suomipoeka.movie_homepath.value
		self.parentStack = []
		self.onExecBegin.append(self.onDialogShow)

	def unUsed(self):
		self.session.open(MessageBox, _("No functionality set..."), MessageBox.TYPE_INFO)

	def keyPress(self):		# these only catch the key-Up events, not key-Down or repeat
		self.cursorDir = 0
		DelayedFunction(config.suomipoeka.movie_descdelay.value, self.updateAfterKeyPress)
	def keyPressU(self):
		self.cursorDir = -1
		DelayedFunction(config.suomipoeka.movie_descdelay.value, self.updateAfterKeyPress)
	def keyPressD(self):
		self.cursorDir = 1
		DelayedFunction(config.suomipoeka.movie_descdelay.value, self.updateAfterKeyPress)

	def updateAfterKeyPress(self):
		self.updateTitle()
		if not self.browsingVLC():	self.updateEventInfo()

	def bouquetPlus(self):
		self["list"].moveToIndex( max(self["list"].getCurrentIndex()-8, 0) )

	def bouquetMinus(self):
		self["list"].moveToIndex( min(self["list"].getCurrentIndex()+8, self["list"].__len__()-1) )

	def multiSelect(self):
		if self.browsingVLC(): return
		if self.selectIdx == -1:
			if self["list"].currentSelIsDirectory(): return
			self.selectIdx = self["list"].getCurrentIndex()
		else:
			if self["list"].currentSelIsDirectory() or self.selectIdx==-1: return
			idx = self["list"].getCurrentIndex()
			adder = 1-2*(idx<self.selectIdx)
			for i in range(self.selectIdx, idx+adder, adder): self["list"].multiSelectIdx(i)
			self.selectIdx = -1
		self.updateTitle()

	def selectionToggle(self):
		if not self["list"].currentSelIsDirectory() and not self.browsingVLC():
			self["list"].toggleSelection()
			if config.suomipoeka.movielist_selmove.value != "o":
				if self.cursorDir == -1 and config.suomipoeka.movielist_selmove.value == "b":
					self["list"].moveToIndex( max(self["list"].getCurrentIndex()-1, 0) )
				else:
					self["list"].moveToIndex( min(self["list"].getCurrentIndex()+1, self["list"].__len__()-1) )
			self.updateAfterKeyPress()

	def viewedToggle(self, service=None, onlyViewed=False):
		try:
			if service is None:
				service = self.getCurrent()
			name = service.getPath()
			if not name.endswith(".ts"): return
			cuts  = name +".cuts"
			cutsr = name +".cutsr"
			if os.path.exists(cuts) and not onlyViewed:
				os.rename(cuts, cutsr)
			elif os.path.exists(cutsr) and not os.path.exists(cuts):
				os.rename(cutsr, cuts)
			else:
				open(cuts, 'a').close()
			self["list"].invalidateCurrent()
		except Exception, e:
			spDebugOut("[spMS] viewedToggle exception:\n" + str(e))

	def showEventInformation(self):
		from Screens.EventView import EventViewSimple
		from ServiceReference import ServiceReference
		evt = self["list"].getCurrentEvent()
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))

	def onDialogShow(self):
		if self.wasClosed:
			self.wasClosed = False
			self["key_red"].text = _("Delete")
			self["key_green"].text = self.currentGrnText
			self["key_yellow"].text = _("Move")
			self["key_blue"].text = _(config.suomipoeka.movie_bluefunc.value)
			if config.suomipoeka.movie_reload.value or self["list"].newRecordings or self["list"].__len__() == 0:
				DelayedFunction(50, self.reloadList)
			self.initCursor()
			self.updateTitle()
			try: self.descFieldInit()
			except:	pass
			self.updateEventInfo()

	def initCursor(self):
		if self.playerInstance is None:	# detect movie player state (None == not open)
			if config.suomipoeka.movielist_gotonewest.value:
				self.cursorToNewest()
		else:
			if config.suomipoeka.movielist_gotonewestp.value:
				self.cursorToNewest()
			else:
				service = self.playerInstance.currentlyPlayedMovie()
				if service is not None:
					self["list"].moveTo(service)

	def cursorToNewest(self):
		if config.suomipoeka.movielist_reversed.value:
			self["list"].moveToIndex(self["list"].__len__()-1)
		else:
			self["list"].moveToIndex(0)

	def blueFunc(self):
		if config.suomipoeka.movie_bluefunc.value == "Movie home": self.changeDir(config.suomipoeka.movie_homepath.value)
		elif config.suomipoeka.movie_bluefunc.value == "Play last": self.playLast()

	def changeDir(self, path):
		self.parentStack[:] = []	# clear the list
		self.currentPathSel = path
		self.reloadList()
		self.cursorToNewest()

	def setPlayerInstance(self, player):
		try:
			self.playerInstance = player
		except Exception, e:
			spDebugOut("[spMS] setPlayerInstance exception:\n" + str(e))

	def openPlayer(self, playlist):
		if self.playerInstance is None:
			Notifications.AddNotification(MoviePlayerSP, playlist, self)
		else:
			DelayedFunction(50, self.playerInstance.movieSelected, playlist)

	def playLast(self):
		global gLastPlayedMovies
		if gLastPlayedMovies is None:
			self.session.open(MessageBox, _("Last played movie/playlist not available..."), MessageBox.TYPE_ERROR, 10)
		else:
			self.wasClosed = True
			self.close(None)
			self.openPlayer(gLastPlayedMovies)

	def moveTo(self):
		self.updateAfterKeyPress()

	def getCurrent(self):
		return self["list"].getCurrent()

	def delPathSel(self, path):
		if path != "..":
			path = self.currentPathSel+ "/" + path
			if os.path.exists(path):
				if len(os.listdir(path))>0:
					self.session.open(MessageBox, _("Directory is not empty."), MessageBox.TYPE_ERROR, 10)
				else:
					spTasker.shellExecute('rmdir "' + path +'"')
					return True
		else:
			self.session.open(MessageBox, _("Cannot delete the parent directory."), MessageBox.TYPE_ERROR, 10)
		return False

	def setNextPathSel(self, nextdir):
		moveToIdx = 0
		if nextdir == "..":
			if self.currentPathSel != "" and self.currentPathSel != "/":
				if len(self.parentStack) > 0:
					popped = self.parentStack.pop()
					self.currentPathSel = popped[0]
					moveToIdx = popped[1]
				else:
					# in this case we'll just go to the idx 0
					self.currentPathSel = os.path.split(self.currentPathSel)[0]
		else:
			if os.path.exists(self.currentPathSel+ "/" + nextdir):
				self.parentStack.append((self.currentPathSel, self["list"].getCurrentIndex()))
				if self.currentPathSel == "/": self.currentPathSel = ""
				self.currentPathSel += "/" + nextdir
			elif nextdir == "VLC servers" or self.browsingVLC():
				self.parentStack.append((self.currentPathSel, self["list"].getCurrentIndex()))
				self.currentPathSel += "/" + nextdir
		self.reloadList(moveToIdx)

	def movieSelected(self):
		try:
			global gLastPlayedMovies
			current = self.getCurrent()
			if current is not None:
				if self["list"].currentSelIsDirectory():
					self.setNextPathSel( self["list"].getCurrentSelDir() )
				elif self["list"].currentSelIsVlc():
					entry = self["list"].list[ self["list"].getCurrentIndex() ]
					self.vlcMovieSelected(entry)
				else:
					playlist = self["list"].makeSelectionList()
					spDebugOut("[spMS] Playlist len = " + str(len(playlist)))
					if not self["list"].serviceBusy(playlist[0]):
						gLastPlayedMovies = [] + playlist	# force a copy instead of an reference!
						self.wasClosed = True
						self.close(None)
						self.openPlayer(gLastPlayedMovies)
					else:
						self.session.open(MessageBox, _("File not available."), MessageBox.TYPE_ERROR, 10)
		except Exception, e:
			spDebugOut("[spMS] movieSelected exception:\n" + str(e))

	def openMenu(self):
		current = self.getCurrent()
		if self["list"].currentSelIsDirectory() or self.browsingVLC(): current = None
		self.session.openWithCallback(self.menuCallback, MovieMenu, "normal", self["list"], current, self["list"].makeSelectionList(), self.currentPathSel)

	def openBookmarks(self):
		self.session.openWithCallback(self.openBookmarksCB, MovieMenu, "bookmarks", self["list"], None, self["list"].makeSelectionList(), self.currentPathSel)
	def openBookmarksCB(self, path=None):
		if path is not None:
			path = "bookmark" + path.replace("\n","")
			self.menuCallback(path)

	def openMenuPlugins(self):
		current = self.getCurrent()
		if not self["list"].currentSelIsDirectory() and not self.browsingVLC():
			self.session.openWithCallback(self.menuCallback, MovieMenu, "plugins", self["list"], current, self["list"].makeSelectionList(), self.currentPathSel)

	def menuCallback(self, selection=None):
		if selection is not None:
			if selection == "Play last": self.playLast()
			elif selection == "Movie home": self.changeDir(config.suomipoeka.movie_homepath.value)
			elif selection == "reload": self.reloadList()
			elif selection == "ctrash": self.purgeExpiredFromTrash()
			elif selection == "trash": self.changeDir(config.suomipoeka.movie_trashpath.value)
			elif selection == "delete": self.deleteFile(True)
			elif selection == "rogue": self.rogueFiles()
			elif selection.startswith("bookmark"): self.changeDir(selection[8:])

	def openScriptMenu(self):
		if self.browsingVLC():	#self["list"].getCurrentSelDir() == "VLC servers"
			self.session.open(MessageBox, _("No script operation for VLC streams."), MessageBox.TYPE_ERROR)
			return
		try:
			list = []
			paths = ["/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/script/", "/etc/enigma2/suomipoeka/"]

			for path in paths:
				for e in os.listdir(path):
					if not os.path.isdir(path + e):
						if e.endswith(".sh"):
							list.append([e, path+e])
						elif e.endswith(".py"):
							list.append([e, path+e])

			if len(list) == 0:
				self.session.open(MessageBox, paths[0]+"\n\n   or" + paths[1]+"\n\n" + _("Does not contain any scripts."), MessageBox.TYPE_ERROR)
				return

			dlg = self.session.openWithCallback(self.scriptCB, ChoiceBox, " ", list)
			dlg.setTitle(_("Choose script"))
			dlg["list"].move(0,30)

		except Exception, e:
			spDebugOut("[spMS] openScriptMenu exception:\n" + str(e))

	def scriptCB(self, result=None):
		if result is None: return

		env = "export SP_OUTDIR=%s"%config.suomipoeka.folder.value
		env += " SP_HOME=%s"%config.suomipoeka.movie_homepath.value
		env += " SP_PATH_LIMIT=%s"%config.suomipoeka.movie_pathlimit.value
		env += " SP_TRASH=%s"%config.suomipoeka.movie_trashpath.value
		env += " SP_TRASH_DAYS=%s"%config.suomipoeka.movie_trashcan_limit.value

		current = self["list"].getCurrentSelPath().replace(" ","\ ")
		if os.path.exists(result[1]):
			if result[1].endswith(".sh"):
				spTasker.shellExecute("%s; sh %s %s %s" %(env, result[1], self.currentPathSel, current))
			elif result[1].endswith(".py"):
				spTasker.shellExecute("%s; python %s %s %s" %(env, result[1], self.currentPathSel, current))

	def rogueFiles(self):
		from RogueFileCheck import RogueFileCheck
		check = RogueFileCheck(config.suomipoeka.movie_homepath.value, config.suomipoeka.movie_trashpath.value)
		spTasker.shellExecute( check.getScript(config.suomipoeka.movie_trashpath.value) )
		self.session.open(MessageBox, check.getStatistics(), MessageBox.TYPE_INFO)

	def deleteFile(self, permanently=False):
		if self.browsingVLC(): return
		self.permanentDel  = permanently or config.suomipoeka.movie_trashcan_limit.value == 0
		self.permanentDel |= self.currentPathSel == config.suomipoeka.movie_trashpath.value
		self.permanentDel |= mountpoint(self.currentPathSel) != mountpoint(config.suomipoeka.movie_trashpath.value)
		current = self.getCurrent()	# make sure there is atleast one entry in the list
		if current is not None:
			selectedlist = self["list"].makeSelectionList()
			if self["list"].currentSelIsDirectory() and len(selectedlist) == 1 and current==selectedlist[0]:
				# try to delete an empty directory
				if self.delPathSel(self["list"].getCurrentSelDir()):
					self["list"].removeService(selectedlist[0])
			else:
				if self["list"].serviceBusy(selectedlist[0]): return
				if selectedlist and len(selectedlist)>0:
					self.recsToStop = []
					self.remRecsToStop = False
					for e in selectedlist:
						mpath = e.getPath()
						if self["list"].recControl.isRecording(mpath):
							self.recsToStop.append(mpath)
						if self["list"].recControl.isRemoteRecording(mpath):
							self.remRecsToStop = True
					if len(self.recsToStop)>0:
						self.stopRecordQ()
					else:
						self.deleteMovieQ(selectedlist, self.remRecsToStop)

	def stopRecordQ(self):
		try:
			filenames = ""
			for e in self.recsToStop:
				filenames += "\n" + e.split("/")[-1][:-3]
			self.session.openWithCallback(self.stopRecordConfirmation, MessageBox, _("Stop ongoing recording?\n") + filenames, MessageBox.TYPE_YESNO)
		except Exception, e:
			spDebugOut("[spMS] stopRecordQ exception:\n" + str(e))

	def stopRecordConfirmation(self, confirmed):
		if not confirmed: return
		# send as a list?
		stoppedAll=True
		for e in self.recsToStop:
			stoppedAll = stoppedAll and self["list"].recControl.stopRecording(e)
		if not stoppedAll:
			self.session.open(MessageBox, _("Not stopping any repeating timers. Modify them with the timer editor."), MessageBox.TYPE_INFO, 10)

	def deleteMovieQ(self, selectedlist, remoteRec):
		try:
			self.moviesToDelete = selectedlist
			self.delCurrentlyPlaying = False
			rm_add = ""
			if remoteRec:
				rm_add = _(" Deleting remotely recorded and it will display an rec-error dialog on the other DB.")

			if self.playerInstance is not None:
#				if nowPlaying is not None:
#					self.delCurrentlyPlaying = nowPlaying in selectedlist
				nowPlaying = self.playerInstance.currentlyPlayedMovie().getPath().split("/")[-1]
				for s in selectedlist:
					if s.getPath().split("/")[-1] == nowPlaying:
						self.delCurrentlyPlaying = True
						break

			entrycount = len(selectedlist)
			delStr = _("Delete") + _(" permanently")*self.permanentDel
			if entrycount == 1:
				service = selectedlist[0]
				name = "\n\n" + self["list"].getFileNameOfService(service).replace(".ts","")
				if not self.delCurrentlyPlaying:
					self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + "?" + rm_add + name, MessageBox.TYPE_YESNO)
				else:
					self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + _(" currently played?") + rm_add + name, MessageBox.TYPE_YESNO)
			else:
				if entrycount > 1:
					movienames = "\n\n"
					i = 0
					for service in selectedlist:
						if i >= 5 and entrycount > 5:	# show only 5 entries in the file list
							movienames += "..."
							break
						i += 1
						name = self["list"].getFileNameOfService(service).replace(".ts","")	# TODO: None check
						if len(name) > 48:
							name = name[:48] + "..."	# limit the name string
						movienames += name + "\n"*(i<entrycount)
					if not self.delCurrentlyPlaying:
						self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + _(" all selected video files?")+rm_add+movienames, MessageBox.TYPE_YESNO)
					else:
						self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + _(" all selected video files? The currently playing movie is also one of the selections and its playback will be stopped.")+rm_add+movienames, MessageBox.TYPE_YESNO)
		except Exception, e:
			self.session.open(MessageBox, _("Delete error:\n") + str(e), MessageBox.TYPE_ERROR)
			spDebugOut("[spMS] deleteMovieQ exception:\n" + str(e))

	def deleteMovieConfimation(self, confirmed):
		if confirmed and self.moviesToDelete is not None and len(self.moviesToDelete)>0:
			if self.delCurrentlyPlaying:
				if self.playerInstance is not None:
					self.playerInstance.removeFromPlaylist(self.moviesToDelete)
			delete = config.suomipoeka.movie_trashcan_limit.value==0 or self.permanentDel
			if os.path.exists(config.suomipoeka.movie_trashpath.value) or delete:
				# if the user doesn't want to keep the movies in the trash, purge immediately
				self.execFileOp(config.suomipoeka.movie_trashpath.value, self.moviesToDelete, op="delete", purgeTrash=delete)
				for x in self.moviesToDelete:
					self.lastPlayedCheck(x)
				self["list"].resetSelectionList()
			elif not delete:
				self.session.openWithCallback(self.trashcanCreate, MessageBox, _("Delete failed because the trashcan directory does not exist. Attempt to create it now?"), MessageBox.TYPE_YESNO)
			self.moviesToDelete = None
			self.updateAfterKeyPress()

	def lastPlayedCheck(self, service):
		global gLastPlayedMovies
		try:
			if gLastPlayedMovies is not None:
				if service in gLastPlayedMovies:
					gLastPlayedMovies.remove(service)
				if len(gLastPlayedMovies) == 0:
					gLastPlayedMovies = None
		except Exception, e:
			spDebugOut("[spMS] lastPlayedCheck exception:\n" + str(e))

	def abort(self):
		if self.playerInstance is not None:
			self.playerInstance.movieSelected(None)
			#DelayedFunction(50, self.playerInstance.movieSelected, None)
		self.wasClosed = True
		self.close(None)

	def toggleSort(self):
		if self.browsingVLC(): return
		if self["key_green"].text == _("Alpha sort"):
			self["key_green"].text = _("Date sort")
			self.currentGrnText = _("Date sort")
			self["list"].setAlphaSort(True)
		else:
			self["key_green"].text = _("Alpha sort")
			self.currentGrnText = _("Alpha sort")
			self["list"].setAlphaSort(False)
		self.reloadList()

	def loading(self, loading=True):
		if loading:
			self["list"].hide()
			self["wait"].show()
		else:
			self["wait"].hide()
			self["list"].show()

	def reloadList(self, moveToIdx=-1, mayOpenDialog=True):
		if config.suomipoeka.movielist_loadtext.value:
			DelayedFunction(1, self.loading)
			DelayedFunction(5, self.reloadList2, moveToIdx, mayOpenDialog)
			DelayedFunction(10, self.loading, False)
		else:
			self.reloadList2(moveToIdx, mayOpenDialog)

	def reloadList2(self, moveToIdx=-1, mayOpenDialog=True):
		self.selectIdx = -1
		try:
			if os.path.exists(self.currentPathSel) or self.browsingVLC():
				self["list"].reload(self.currentPathSel + "/"*(self.currentPathSel != "/"))
				if moveToIdx >= 0: self["list"].moveToIndex(moveToIdx)
				self.updateAfterKeyPress()
			else:
				if mayOpenDialog:
					self.session.open(MessageBox, _("Error: path '%s' not available!" % self.currentPathSel), MessageBox.TYPE_ERROR)
				else:
					Notifications.AddNotification(MessageBox, _("Error: path '%s' not available!" % self.currentPathSel), MessageBox.TYPE_ERROR)
		except Exception, e:
			spDebugOut("[spMS] reloadList exception:\n" + str(e))

	def updateTitle(self):
		if self.selectIdx != -1:
			self.setTitle(_("*** Multiselection active ***"))
			return
		lotime = localtime()
		title = "[%02d:%02d] " %(lotime[3],lotime[4])
		if os.path.exists(self.currentPathSel+"/"):
			stat = os.statvfs(self.currentPathSel+"/")
			free = (stat.f_bavail if stat.f_bavail!=0 else stat.f_bfree) * stat.f_bsize / 1048576
			if free >= 10240:	#unit in Giga bytes if more than 10 GB free
				title = "(%d GB) " %(free/1024)
			else:
				title = "(%d MB) " %(free)

		title += self.currentPathSel + (self.currentPathSel=="")*"/"

		if not self["list"].currentSelIsDirectory() and not self.browsingVLC():
			try:
				service = self.getCurrent()
				if service is not None and config.suomipoeka.movie_descdis.value:
					lenght = self["list"].getLenghtOfCurrent()
					title += " <" + ("%d min, "%lenght) * (lenght>0)
					title += "%d MB>" %(os.path.getsize(service.getPath())/1048576)
			except Exception, e:
				spDebugOut("[spMS] updateTitle exception:\n" + str(e))
		title = title.replace(config.suomipoeka.movie_homepath.value+"/", ".../")
		self.setTitle(title)

	def moveMovie(self):
		if self.browsingVLC() or self["list"].getCurrentSelDir() == "VLC servers": return
		current = self.getCurrent()
		if current is not None:
			selectedlist = self["list"].makeSelectionList()
			dialog = False
			if self["list"].currentSelIsDirectory():
				if current != selectedlist[0]:	# first selection != cursor pos?
					targetPath = self.currentPathSel
					if self["list"].getCurrentSelDir() == "..":
						targetPath = os.path.split(targetPath)[0]
					else:
						targetPath += "/" + self["list"].getCurrentSelDir()
					self.execFileOp(targetPath, selectedlist)
					self["list"].resetSelectionList()
				else:
					if len(selectedlist) == 1:
						self.session.open(MessageBox, _("How to move files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow."), MessageBox.TYPE_ERROR, 10)
					else:
						dialog = True
			else:
				dialog = True
			if dialog:
				try:
					from Screens.LocationBox import LocationBox
					if len(selectedlist)==1 and self["list"].serviceBusy(selectedlist[0]): return
					self.tmpSelList = selectedlist
					self.session.openWithCallback(self.mvDirSelected, LocationBox, windowTitle= _("Select Location"), text = _("Choose directory"),
						filename = "", currDir = self.currentPathSel+"/", minFree = 0)
				except:
					self.session.open(MessageBox, _("How to move files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow."), MessageBox.TYPE_ERROR, 10)

	def mvDirSelected(self, targetPath):
		if targetPath is not None:
			self.execFileOp(targetPath, self.tmpSelList)
			self["list"].resetSelectionList()
			self.tmpSelList = None

	def moveRecCheck(self, serviceref, targetPath):
		try:
			path = serviceref.getPath()
			if self["list"].recControl.isRecording(path):
				self["list"].recControl.fixTimerPath(path, path.replace(self.currentPathSel, targetPath))
		except Exception, e:
			spDebugOut("[spMS] moveRecCheck exception:\n" + str(e))

	def execFileOp(self, targetPath, selectedlist, op="move", purgeTrash=False):
		mvCmd = ""
		rmCmd = ""
		association = []
		for service in selectedlist:
			name = os.path.splitext( self["list"].getFileNameOfService(service) )[0]
			if name is not None:
				if op=="delete":	# target == trashcan
					if purgeTrash or self.currentPathSel == targetPath or mountpoint(self.currentPathSel) != mountpoint(targetPath):
						# direct delete from the trashcan or network mount (no copy to trashcan from different mountpoint)
						rmCmd += '; rm -f "'+ self.currentPathSel +"/"+ name +'."*'
					else:
						# create a time stamp with touch
						mvCmd += '; touch "'+ self.currentPathSel +"/"+ name +'."*'
						# move movie into the trashcan
						mvCmd += '; mv "'+ self.currentPathSel +"/"+ name +'."* "'+ targetPath +'/"'
					association.append((service, self.delCB))	# put in a callback for this particular movie
					self["list"].highlightService(True, "del", service)
					if config.suomipoeka.movie_hide_del.value:
						self["list"].removeService(service)
				elif op == "move":
					#if mountpoint(self.currentPathSel) == mountpoint(targetPath):
					#	#self["list"].removeService(service)	# normal direct move
					#	pass
					#else:
					# different mountpoint? -> reset user&group
					if mountpoint(targetPath) != mountpoint(config.suomipoeka.movie_homepath.value):		# CIFS to HDD is ok!
						# need to change file ownership to match target filesystem file creation
						tfile = targetPath + "/owner_test"
						sfile = "\""+ self.currentPathSel +"/"+ name +".\"*"
						mvCmd += "; touch %s;ls -l %s | while read flags i owner group crap;do chown $owner:$group %s;done;rm %s" %(tfile,tfile,sfile,tfile)
					mvCmd += '; mv "'+ self.currentPathSel +"/"+ name +'."* "'+ targetPath +'/"'
					association.append((service, self.moveCB))	# put in a callback for this particular movie
					self["list"].highlightService(True, "move", service)
					if config.suomipoeka.movie_hide_mov.value:
						self["list"].removeService(service)
					self.moveRecCheck(service, targetPath)
				self.lastPlayedCheck(service)
		if (mvCmd + rmCmd) != "":
			spTasker.shellExecute((mvCmd + rmCmd)[2:], association)	# first move, then delete if expiration limit is 0

	def moveCB(self, service):
		self["list"].highlightService(False, "move", service)	# remove the highlight
		if not config.suomipoeka.movie_hide_mov.value:
			self["list"].removeService(service)
		self.updateTitle()

	def delCB(self, service):
		self["list"].highlightService(False, "del", service)	# remove the highlight
		if not config.suomipoeka.movie_hide_del.value:
			self["list"].removeService(service)
		self.updateTitle()

	def purgeExpiredFromTrash(self):
		try:
			if os.path.exists(config.suomipoeka.movie_trashpath.value):
				purgeCmd = ""
				dirlist = os.listdir(config.suomipoeka.movie_trashpath.value)
				for movie in dirlist:
					if movie[-3:] != ".ts": continue
					fullpath = config.suomipoeka.movie_trashpath.value +"/"+ movie
					currTime = localtime()
					expTime = localtime(os.stat(fullpath).st_mtime + 24*60*60*config.suomipoeka.movie_trashcan_limit.value)

					if currTime > expTime:
						purgeCmd += "; rm -f \"%s\"*" % fullpath.replace(".ts","")
				if purgeCmd != "":
					spTasker.shellExecute(purgeCmd[2:])
					spDebugOut("[spMS] trashcan cleanup activated")
				else:
					spDebugOut("[spMS] trashcan cleanup: nothing to delete...")
		except Exception, e:
			spDebugOut("[spMS] purgeExpiredFromTrash exception:\n" + str(e))

	def trashcanCreate(self, confirmed):
		try:
			os.makedirs(config.suomipoeka.movie_trashpath.value)
			self.reloadList()	# reload to show the trashcan
		except Exception, e:
			self.session.open(MessageBox, _("Trashcan create failed. Check mounts and permissions."), MessageBox.TYPE_ERROR)
			spDebugOut("[spMS] trashcanCreate exception:\n" + str(e))
