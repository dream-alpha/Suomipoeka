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
from Components.config import *
from Components.GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Tools.LoadPixmap import LoadPixmap
from time import localtime
from skin import parseColor, parseFont
from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, eServiceReference, eServiceCenter

from RecordingsControl import RecordingsControl
from DelayedFunction import DelayedFunction
from SuomipoekaTasker import spDebugOut
from Suomipoeka import _
from VlcPluginInterface import VlcPluginInterfaceList

import NavigationInstance
import os

currentSelectionCount = 0


class MovieList(GUIComponent, VlcPluginInterfaceList):
	instance = None
	extensions = ["ts","mpg","mpeg","mp3","mp4","ogg","avi","mkv"]
	def __init__(self):
		MovieList.instance = self
		self.list = []
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.CoolFont = parseFont("Regular;20", ((1,1),(1,1)))
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, self.CoolFont)
		self.l.setFont(2, gFont("Regular", 16))

		self.l.setBuildFunc(self.buildMovieListEntry)
		self.l.setItemHeight(25)

		self.CoolDirPos = 410
		self.CoolMoviePos = 48
		self.CoolMovieSize = 360
		self.CoolDatePos = 380
		self.CoolTimePos = 470

		self.alphaSort = False
		self.newRecordings = False
		self.selectionList = None
		self.recControl = RecordingsControl(self.recStateChange)
		self.highlightsMov = []
		self.highlightsDel = []
		self.backPic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/back.png')
		self.dirPic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/dir.png')
		self.mov1Pic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/movie_yes.png')
		self.mov2Pic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/movie.png')
		self.mov3Pic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/movie_red.png')
		self.mov4Pic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/movie_yel.png')
		self.mp3Pic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/music.png')
		self.vlcPic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/vlc.png')
		self.vlcdPic = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/vlcdir.png')
		self.loadPath = config.suomipoeka.movie_homepath.value + "/"
		self.serviceHandler = eServiceCenter.getInstance()
		self.onSelectionChanged = []


	def applySkin(self, desktop, parent):
		attribs = [ ]
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "CoolFont":
					self.CoolFont = parseFont(value, ((1,1),(1,1)))
					self.l.setFont(1, self.CoolFont)
				elif attrib == "CoolDirPos":
					self.CoolDirPos = int(value)
				elif attrib == "CoolMoviePos":
					self.CoolMoviePos = int(value)
				elif attrib == "CoolMovieSize":
					self.CoolMovieSize = int(value)
				elif attrib == "CoolDatePos":
					self.CoolDatePos = int(value)
				elif attrib == "CoolTimePos":
					self.CoolTimePos = int(value)
				else:
					attribs.append((attrib, value))
		self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, parent)


	def selectionChanged(self):
		for f in self.onSelectionChanged:
			try:
				f()
			except Exception, e:
				spDebugOut("[spML] External observer exception: \n" + str(e))

	def recStateChange(self, recList):
		try:
			DelayedFunction(3000, self.reload, self.loadPath)
		except Exception, e:
			spDebugOut("[spML] recStateChange exception:\n" + str(e))

	def setAlphaSort(self, trueOrFalse):
		self.alphaSort = trueOrFalse

	def buildMovieListEntry(self, serviceref, sortkey, datesort, moviestring, filename, selnum):
		if datesort is None:
			res = [ None ]
			pmap = [self.dirPic, self.vlcdPic][sortkey=="VLCd" or filename=="VLC servers"]
			if filename=="..": pmap = self.backPic
			res.append(MultiContentEntryPixmapAlphaTest(pos=(0,2), size=(22,40), png=pmap, **{}))
			res.append(MultiContentEntryText(pos=(30, 0), size=(310, 40), font=1, flags=RT_HALIGN_LEFT, text=filename))
			res.append(MultiContentEntryText(pos=(self.CoolDirPos, 0), size=(200, 40), font=1, flags=RT_HALIGN_LEFT, text=_("Directory")))
			return res

		date, time, pixmap = "---.---  ", "---:---", self.mov1Pic
		nameWithPath = self.loadPath + filename
		if config.suomipoeka.movie_mark.value and not os.path.exists(nameWithPath + ".cuts"):
			pixmap = self.mov2Pic

		if datesort == "VLCs":
			date, time, pixmap = "VLC", " stream", self.vlcPic
		elif not datesort.startswith("0000"):
			# datesort = YYMMDDTTTT
			if datesort[6:10] != "3333":
			  time = datesort[6:8] + ":" + datesort[8:10]
			date = datesort[4:6] + "." + datesort[2:4] + "." + "  " #+ datesort[0:2]
		elif filename.endswith(".mp3"):
			date, time, pixmap = "MP3", " audio", self.mp3Pic
			moviestring = moviestring[:-4]
		elif filename.endswith(".ogg"):
			date, time, pixmap = "OGG", " audio", self.mp3Pic
			moviestring = moviestring[:-4]
		elif filename.endswith(".mpg"):
			date, time = "MPEG", " video"
			moviestring = moviestring[:-4]
		elif filename.endswith(".mpeg"):
			date, time = "MPEG", " video"
			moviestring = moviestring[:-5]
		elif filename.endswith(".avi"):
			date, time = "AVI", " video"
			moviestring = moviestring[:-4]
		elif filename.endswith(".mkv"):
			date, time = "MKV", " video"
			moviestring = moviestring[:-4]


		selnumtxt = ""
		if selnum == 9999: selnumtxt = "[M]"
		elif selnum == 9998: selnumtxt = "[D]"
		elif selnum > 0: selnumtxt = "%02d" % selnum
		if serviceref in self.highlightsMov: selnumtxt = "[M]"
		elif serviceref in self.highlightsDel: selnumtxt = "[D]"

		if self.recControl.isRecording(nameWithPath):
			date, pixmap = "REC...  ", self.mov3Pic
		elif self.recControl.isRemoteRecording(nameWithPath):
			date, pixmap = "rec...  ", self.mov4Pic
		res = [ None ]
		res.append(MultiContentEntryText(pos=(self.CoolDatePos, 0), size=(90, 40), font=1, flags=RT_HALIGN_RIGHT, text=date))
		res.append(MultiContentEntryText(pos=(self.CoolMoviePos, 0), size=(self.CoolMovieSize, 40), font=1, flags=RT_HALIGN_LEFT, text=moviestring))
		res.append(MultiContentEntryText(pos=(self.CoolTimePos, 0), size=(85, 40), font=1, flags=RT_HALIGN_LEFT, text=time))
		res.append(MultiContentEntryText(pos=(0, 0), size=(26, 40), font=1, flags=RT_HALIGN_LEFT, text=selnumtxt))
		if config.suomipoeka.movie_icons.value and selnum == 0:
			res.append(MultiContentEntryPixmapAlphaTest(pos=(0,2), size=(20,20), png=pixmap, **{}))
		return res

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def getCurrentEvent(self):
		l = self.l.getCurrentSelection()
		return l and l[0] and self.serviceHandler.info(l[0]).getEvent(l[0])

	def getCurrent(self):
		l = self.l.getCurrentSelection()
		return l and l[0]

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def removeService(self, service):
		for l in self.list[:]:
			if l[0] == service:
				self.list.remove(l)
		self.l.setList(self.list)

	def serviceBusy(self, service):
		return service in self.highlightsMov or service in self.highlightsDel

	def serviceMoving(self, service):
		return service in self.highlightsMov

	def serviceDeleting(self, service):
		return service in self.highlightsDel

	def highlightService(self, enable, mode, service):
		if enable:
			if mode == "move":
				self.highlightsMov.append(service)
				self.toggleSelection(service, 9999)
			elif mode == "del":
				self.highlightsDel.append(service)
				self.toggleSelection(service, 9998)
		else:
			if mode == "move":
				self.highlightsMov.remove(service)
			elif mode == "del":
				self.highlightsDel.remove(service)

	def __len__(self):
		return len(self.list)

	def makeSelectionList(self):
		selList = [ ]
		global currentSelectionCount
		if currentSelectionCount == 0:
			# if no selections made, select the current cursor position
			single = self.l.getCurrentSelection()
			if single:
				selList.append(single[0])
		else:
			selList = self.selectionList
		return selList

	def resetSelectionList(self):
		self.selectionList = None
		global currentSelectionCount
		currentSelectionCount = 0

	def multiSelectIdx(self, index):
		self.toggleSelection(self.list[index][0])

	def toggleSelection(self, service=None, overrideNum=None):
		global currentSelectionCount
		x, index = None, 0
		if service is None:
			if self.l.getCurrentSelection() is None: return
			index = self.getCurrentIndex()
			x = self.list[index]
		else:
			for e in self.list:
				if e[0] == service:
					x = e
					break
				index += 1

		if x is None: return
		if self.selectionList == None:
			self.selectionList = [ ]

		newselnum = x[5]	# init with old selection number
		if overrideNum == None:
			if self.serviceBusy(x[0]): return	# no toggle if file being operated on
			# basic selection toggle
			if newselnum == 0:
				# was not selected
				currentSelectionCount += 1
				newselnum = currentSelectionCount
				self.selectionList.append(x[0]) # append service
			else:
				# was selected, reset selection number and decrease all that had been selected after this
				newselnum = 0
				currentSelectionCount -= 1
				count = 0
				if x is not None:
					self.selectionList.remove(x[0]) # remove service
				for i in self.list:
					if i[5] > x[5]:
						self.list.remove(self.list[count])
						self.list.insert(count, (i[0],i[1],i[2],i[3],i[4],i[5]-1))
						self.l.invalidateEntry(count) # force redraw
					count += 1
		else:
			newselnum = overrideNum * (newselnum == 0)

		self.list.remove(self.list[index])
		self.list.insert(index, (x[0],x[1],x[2],x[3],x[4],newselnum))
		self.l.invalidateEntry(index) # force redraw of the modified item

	def invalidateService(self, service):
		i = 0
		for entry in self.list:
			if entry[0] == service:
				self.l.invalidateEntry(i) # force redraw of the item
				break
			i += 1

	def invalidateCurrent(self):
		self.l.invalidateEntry(self.getCurrentIndex())

	def getLenghtOfCurrent(self):
		ref = self.getCurrent()
		return (self.serviceHandler.info(ref).getLength(ref)+30)/60

	def getFileNameOfService(self, service):
		for entry in self.list:
			if entry[0] == service:
				return entry[4]
		return None

	def createDirlist(self, loadPath):
		subdirlist = []
		filelist = []
		dirlist = os.listdir(loadPath)	# only need to deal with spaces when executing in shell
		# add sub directories to the list
		for p in dirlist:
			if p.startswith(".") and (loadPath + p) != config.suomipoeka.movie_trashpath.value: continue
			if config.suomipoeka.movie_trashcan_hide.value:
				# TODO: dereference links for comparison?
				if (loadPath + p) == config.suomipoeka.movie_trashpath.value: continue
			if os.path.isdir(loadPath + p):
				subdirlist.append(p)
			else:
				ext = p.split(".")[-1]
				if ext in MovieList.extensions:
					filelist.append((p, ext))

		subdirlist.sort(key=str.lower)
		if loadPath != "/" and loadPath[:-1] != config.suomipoeka.movie_pathlimit.value:
			subdirlist.insert(0, "..")
		if loadPath[:-1] == config.suomipoeka.movie_homepath.value:
			if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/VlcPlayer/VlcServerConfig.pyc") and not config.suomipoeka.movie_vlc_hide.value:
				subdirlist.insert(0, "VLC servers")
		return subdirlist, filelist

	def reload(self, loadPath):
		global currentSelectionCount
		currentSelectionCount = 0
		if not loadPath.endswith("/"): loadPath += "/"
		self.loadPath = loadPath
		self.selectionList = None
		self.list = []
		self.newRecordings = False
		self.recControl.recFilesRead()	# get a list of current remote recordings

		spDebugOut("[spML] LOAD PATH:\n" + loadPath)
		if loadPath.endswith("VLC servers/"):
			self.reloadVlcServers()
			return
		elif loadPath.find("VLC servers/")>0:
			self.reloadVlcFilelist()
			return

		subdirlist, list = self.createDirlist(loadPath)

		# add sub directories to the list
		if subdirlist is not None:
			for dirp in subdirlist:
				self.list.append((eServiceReference("2:0:1:0:0:0:0:0:0:0:" + dirp), None, None, None, dirp, 0))

		tmplist = []
		for (filename, ext) in list:
			mpath = loadPath + filename
			if ext == "ts":
				serviceref = eServiceReference("1:0:0:0:0:0:0:0:0:0:" + mpath)
			else:
				serviceref = eServiceReference("4097:0:0:0:0:0:0:0:0:0:" + mpath)
			moviestring = ""
# > meta load
			if config.suomipoeka.movie_metaload.value and os.path.exists(mpath + ".meta"):
				file = open(mpath + ".meta", "r")
				file.readline()
				line = file.readline()
				file.close()
				moviestring = line.rstrip("\r\n")
# < meta load
 			date = "0000"
			if filename[0:8].isdigit() and filename[9:13].isdigit() and not filename[8:1].isdigit():
				date = filename[2:8] + filename[9:13]
				if moviestring == "":
					moviestring = filename[16:]	# skips "YYYYMMDD TIME - "
					chlMarker = moviestring.find("_-_")
					if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
					else:
						chlMarker = moviestring.find(" - ")
						if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
			elif filename[0:2].isdigit() and filename[3:5].isdigit() and not filename[2:3].isdigit():
				date = filename[0:2] + filename[3:5] + filename[6:8] + "3333"
				if moviestring == "":
					moviestring = filename[11:]	# skips "YYYYMMDD TIME - "
					chlMarker = moviestring.find("_-_")
					if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
					else:
						chlMarker = moviestring.find(" - ")
						if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
			else:
				if moviestring == "":
					moviestring = filename[0:]
				# files that do not have a date, sort them alphabetically
				if config.suomipoeka.movielist_reversed.value:
					date += filename.lower()
				else:
					for x in filename.lower(): date += chr(255-ord(x))

			moviestring = moviestring.replace(".ts","").replace("_ "," ").replace("_"," ")

			sortkey = None
			if self.alphaSort: sortkey = moviestring[:16] + date

			if not (self.serviceMoving(serviceref) and config.suomipoeka.movie_hide_mov.value):
				if not (self.serviceDeleting(serviceref) and config.suomipoeka.movie_hide_del.value):
					# (service, sortkey, sortdate, sortstring, filename, selnum)
					tmplist.append((serviceref, sortkey, date, moviestring, filename, 0))

		if self.alphaSort:
			tmplist.sort(key=lambda x: x[1],reverse=config.suomipoeka.movielist_reversed.value)
		else:
			tmplist.sort(key=lambda x: x[2],reverse=not config.suomipoeka.movielist_reversed.value)

		self.list += tmplist
		self.l.setList(self.list)
		self.resetSelectionList()

	def currentSelIsDirectory(self):
		try:	return self.list[self.getCurrentIndex()][2] is None #or self.currentSelIsVlcDir()
		except:	return False

	def getCurrentSelDir(self):
		return self.list[self.getCurrentIndex()][4]

	def getCurrentSelPath(self):
		return self.loadPath + self.list[self.getCurrentIndex()][4] + (self.list[self.getCurrentIndex()][2] is None) * "/"

	def moveTo(self, serviceref):
		found = 0
		count = 0
		for x in self.list:
			if x[0] == serviceref:
				found = count
			count += 1
		self.instance.moveSelectionTo(found)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)
