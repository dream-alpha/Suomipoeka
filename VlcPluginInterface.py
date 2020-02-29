#!/usr/bin/python
# encoding: utf-8
#
# VLC Player Plugin integration module for SP movie list
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

from enigma import eServiceReference
import os

from SuomipoekaTasker import spDebugOut
#from DelayedFunction import DelayedFunction


class VlcFileListWrapper:
	def __init__(self):
		pass
	def getNextFile(self):
		return None, None
	def getPrevFile(self):
		return None, None


class VlcPluginInterfaceSel():
	def browsingVLC(self):
		return self.currentPathSel.find("VLC servers") > 0

	def vlcMovieSelected(self, entry):
		try:
			self.hide()
#			from Plugins.Extensions.VlcPlayer.VlcPlayer import VlcPlayer
#			dlg = self.session.open(VlcPlayer, self["list"].vlcServer, VlcFileListWrapper())
#			dlg.playfile(entry[4], entry[3])
			try:	# v2.5
				self["list"].vlcServer.play(self, entry[4], entry[3], VlcFileListWrapper())
			except:	# v2.6
				self["list"].vlcServer.play(self.session, entry[4], entry[3], VlcFileListWrapper())
			self.wasClosed = True
			self.close()
		except Exception, e:
			spDebugOut("[spVLC] vlcMovieSelected exception:\n" + str(e))


class VlcPluginInterfaceList():
	def currentSelIsVlc(self):
		try:	return self.list[self.getCurrentIndex()][2] == "VLCs"
		except:	return False

	def currentSelIsVlcDir(self):
		try:	return self.list[self.getCurrentIndex()][2] == "VLCd"
		except:	return False

	def reloadVlcServers(self):
		try:
			from Plugins.Extensions.VlcPlayer.VlcServerConfig import vlcServerConfig
			self.vlcServers = vlcServerConfig.getServerlist()	# settings change requires running this
			self.list = []
			sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + "..")	# dummy ref
			self.list.append((sref, None, None, None, "..", None))
			for srv in self.vlcServers:
				srvName = srv.getName()
				sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + srvName)	# dummy ref
				self.list.append((sref, "VLCd", None, None, srvName, None))
			self.list.sort(key=lambda x: x[1],reverse=False)
			self.l.setList(self.list)
		except:	pass

	def reloadVlcFilelist(self):
		self.list = []
		sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + "..")	# dummy ref
		self.list.append((sref, None, None, None, "..", None))

		vlcPath = self.loadPath[self.loadPath.find("VLC servers/")+12:]	# server/dir/name/
		serverName = vlcPath.split("/")[0]
		spDebugOut("[spML] path on %s = %s" %(serverName, vlcPath))
		server = None
		self.vlcServer = None
		for srv in self.vlcServers:
			if srv.getName() == serverName: server = srv	# find the server
		if server is not None:
			try:
				self.vlcServer = server
				spDebugOut("[spML] baseDir = " + server.getBasedir())
				vlcPath = vlcPath[len(serverName):]
				spDebugOut("[spML] vlcPath = " + vlcPath)
				(vlcFiles, vlcDirs) = server.getFilesAndDirs(server.getBasedir() + vlcPath, None)
				spDebugOut("[spML] got files and dirs...")
				for d in vlcDirs:
					if d[0] == "..": continue
					sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + d[0])	# dummy ref
					self.list.append((sref, "VLCd", None, None, d[0], None))
				for f in vlcFiles:
					from Plugins.Extensions.VlcPlayer.VlcFileList import MEDIA_EXTENSIONS	# , VlcFileListEntry
#					others = ["mp4", "mpeg4", "mkv"]
#					extension = f[0].split('.')[-1].lower()
#					if MEDIA_EXTENSIONS.has_key(extension) or extension in others:
					sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + f[0])	# dummy ref
					self.list.append((sref, None, "VLCs", f[0], f[1], None))
			except Exception, e:
				spDebugOut("[spML] reloadVlcFilelist exception:\n" + str(e))
		#self.list.sort(key=lambda x: x[1],reverse=False)
		self.l.setList(self.list)

