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
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Screens.LocationBox import LocationBox
from Tools.BoundFunction import boundFunction
import os

from SuomipoekaTasker import spTasker, spDebugOut
from Suomipoeka import _

class MovieMenu(Screen):
	def __init__(self, session, menumode, mlist, service, selections, currentPath):
		Screen.__init__(self, session)
		self.mode = menumode
		self.mlist = mlist
		self.service = service
		self.selections = selections
		self.currentPathSel = currentPath

		self.menu = []
		if menumode == "normal":
			self["title"] = StaticText(_("Choose operation"))
			if config.suomipoeka.movie_bluefunc.value == "Movie home":
				self.menu.append((_("Play last"), boundFunction(self.close, "Play last")))
			else:
				self.menu.append((_("Movie home"), boundFunction(self.close, "Movie home")))

			if os.path.exists(config.suomipoeka.movie_trashpath.value):
				if self.service is not None:
					self.menu.append((_("Delete permanently"), boundFunction(self.close, "delete")))
#				self.menu.append((_("Cleanup trashcan"), boundFunction(self.cleanTrash)))
				self.menu.append((_("Empty trashcan"), boundFunction(self.emptyTrash)))
				self.menu.append((_("Go to trashcan"), boundFunction(self.close, "trash")))
			self.menu.append((_("Remove rogue files"), boundFunction(self.remRogueFiles)))
			self.menu.append((_("Create link(s)"), boundFunction(self.createLinks)))
			self.menu.append((_("Create directory"), boundFunction(self.createDir)))
			self.menu.append((_("Bookmark directory"), boundFunction(self.bookmarkDir)))
			self.menu.append((_("Bookmarks"), boundFunction(self.openBookmark)))
		elif menumode == "plugins":
			self["title"] = StaticText(_("Choose plugin"))
			if self.service is not None:
				for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
					self.menu.append((p.description, boundFunction(self.execPlugin, p)))
		elif menumode == "bookmarks":
			self["title"] = StaticText(_("Choose bookmark"))
			try:
				bmfile = open(config.suomipoeka.folder.value + "/bookmarks.cfg", "r")
				#for x in bmfile.readline():
				#	self.menu.append((x, boundFunction(self.close, x)))
				for line in bmfile:
					self.menu.append((line, boundFunction(self.close, line)))
				bmfile.close()
			except Exception, e:
				spDebugOut("[spMM] bookmarks mode exception:\n" + str(e))

		self["menu"] = List(self.menu)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"ok":		self.okButton,
				"cancel":	self.close,
				"red":		self.redButton,
			})
		self.skinName = "Menu"
		self.onShown.append(self.onDialogShow)

	def onDialogShow(self):
		self.setTitle(_("Movie Selection Menu"))

	def okButton(self):
		try:
			self["menu"].getCurrent()[1]()
		except:pass

	def redButton(self):
		if self.mode != "bookmarks": return
		self.menu.remove(self["menu"].getCurrent())
		self["menu"].setList(self.menu)
		try:
			bmfile = open(config.suomipoeka.folder.value + "/bookmarks.cfg", "w")
			bmfile.writelines([ x[0] for x in self.menu ])
			bmfile.close()
		except Exception, e:
			spDebugOut("[spMM] redButton exception:\n" + str(e))

	def bookmarkDir(self):
		self.session.openWithCallback(self.bookmarkDirCB, LocationBox, windowTitle= _("Select Location"), text = _("Choose directory"), filename = "", currDir = self.currentPathSel+"/", minFree = 0)
	def bookmarkDirCB(self, path):
		try:
			if path.endswith("/"):	path = path[:-1]
			bmfile = open(config.suomipoeka.folder.value + "/bookmarks.cfg", "a")
			bmfile.write(path + "\n")
			bmfile.close()
		except Exception, e:
			spDebugOut("[spMM] bookmarkDirCB exception:\n" + str(e))
		self.close(None)

	def openBookmark(self):
		self.hide()
		self.session.openWithCallback(self.openBookmarkCB, MovieMenu, "bookmarks", self.mlist, self.service, self.mlist.makeSelectionList(), self.currentPathSel)
	def openBookmarkCB(self, path=None):
		if path is not None:
			path = "bookmark" + path.replace("\n","")
		self.close(path)

	def createLinks(self):
		self.session.openWithCallback(self.createLinksCB, LocationBox, windowTitle= _("Select Location"), text = _("Choose directory"), filename = "", currDir = self.currentPathSel+"/", minFree = 0)
	def createLinksCB(self, targetPath):
		try:
			if self.currentPathSel == targetPath or targetPath == None: return
			cmd = ""
			for x in self.selections:
				name = self.mlist.getFileNameOfService(x)
				cmd += '; ln -s "'+ self.currentPathSel +"/"+ name +'" "'+ targetPath + name +'"'
			if cmd != "":
				spTasker.shellExecute(cmd[2:])	# first move, then delete if expiration limit is 0
				self.close(None)
		except Exception, e:
			spDebugOut("[spMM] createLinks exception:\n" + str(e))

	def createDir(self):
		self.hide()
		self.session.openWithCallback(self.createDirCB, InputBox, title=_("Enter name for new directory."), windowTitle=_("Create directory"))

	def createDirCB(self, name):
		if name is not None:
			name = self.currentPathSel+ "/" + name
			if os.path.exists(name):
				self.session.open(MessageBox, _("Directory "+name+" already exists."), MessageBox.TYPE_ERROR)
			else:
				try:
					os.mkdir(name)
				except Exception, e:
					spDebugOut("[spMM] createDir exception:\n" + str(e))
				self.close("reload")
		else:
			self.close(None)

	def emptyTrash(self):
		self.hide()
		self.session.openWithCallback(self.emptyTrashCB, MessageBox, _("Permanently delete all files in trashcan?"), MessageBox.TYPE_YESNO)

	def emptyTrashCB(self, confirmed):
		if confirmed:
			spTasker.shellExecute("rm -f %s/*"%config.suomipoeka.movie_trashpath.value)
		self.close(None)

#	def cleanTrash(self):
#		self.close("ctrash")

	def remRogueFiles(self):
		self.hide()
		self.session.openWithCallback(self.remRogueFilesCB, MessageBox, _("Locate rogue files and remove them? (permanently if no trashcan available, may take a minute or so)"), MessageBox.TYPE_YESNO)

	def remRogueFilesCB(self, confirmed):
		if confirmed:
			self.close("rogue")
		else:
			self.close(None)

	def execPlugin(self, plugin):
		#self.hide()
		plugin(session=self.session, service=self.service)
		#self.close("reload")
