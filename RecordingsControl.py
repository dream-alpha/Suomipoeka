#!/usr/bin/python
# encoding: utf-8
#
# Recordings manipulation class for the movie list by moveq
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

from enigma import iRecordableService
from Components.config import config
from RecordTimer import AFTEREVENT
import NavigationInstance
import pickle, os

from RecordEventObserver import RecordEventObserver
from SuomipoekaTasker import spTasker, spDebugOut
from DelayedFunction import DelayedFunction
from NetworkAwareness import spNET

class RecordingsControl:
	def __init__(self, recStateChange):
		self.recStateChange = recStateChange
		self.recObserver = RecordEventObserver(self.recEvent)
		self.recList = []
		self.recRemoteList = []
		self.recFile = None
		# if Enigma2 has crashed, we need to recreate the list of the ongoing recordings
		for timer in NavigationInstance.instance.RecordTimer.timer_list:
			self.recEvent(timer)

	def recEvent(self, timer):
		# StateWaiting=0, StatePrepared=1, StateRunning=2, StateEnded=3
		try:
			if timer.justplay: return
			inform = False
			try: timer.Filename
			except: timer.calculateFilename()

			filename = os.path.split(timer.Filename)[1]
			if timer.state == timer.StatePrepared:	pass
			elif timer.state == timer.StateRunning:	# timer.isRunning()
				if not filename in self.recList:
					self.recList.append(filename)
					inform = True
					spDebugOut("[spRC] REC START for: " + filename)
			else: #timer.state == timer.StateEnded:
				if filename in self.recList:
					try: os.rename(timer.Filename + ".ts.cuts", timer.Filename + ".ts.cutsr") # switch to unwatched
					except: pass
					self.recList.remove(filename)
					inform = True
					spDebugOut("[spRC] REC END for: " + filename)
					try:
						spTasker.shellExecute(timer.fixMoveCmd)
						spDebugOut("[spRC] File had been moved while recording was in progress, moving left over files..")
					except: pass

				if config.suomipoeka.timer_autocln.value:
					DelayedFunction(2000, NavigationInstance.instance.RecordTimer.cleanup)	# postpone to avoid crash in basic timer delete by user
			if inform:
				self.recFileUpdate()
				self.recStateChange(self.recList)
				#DelayedFunction(500, self.recStateChange, self.recList)

		except Exception, e:
			spDebugOut("[spRC] recEvent exception:\n" + str(e))

	def isRecording(self, filename):
		try:
			if filename[0] == "/": 			filename = os.path.split(filename)[1]
			if filename.endswith(".ts"):	filename = filename[:-3]
			return filename in self.recList
		except Exception, e:
			spDebugOut("[spRC] isRecording exception:\n" + str(e))
			return False

	def isRemoteRecording(self, filename):
		try:
			if filename[0] == "/": 			filename = os.path.split(filename)[1]
			if filename.endswith(".ts"):	filename = filename[:-3]
			return filename in self.recRemoteList
		except Exception, e:
			spDebugOut("[spRC] isRemoteRecording exception:\n" + str(e))
			return False

	def stopRecording(self, filename):
		try:
			if filename[0] == "/":			filename = os.path.split(filename)[1]
			if filename.endswith(".ts"):	filename = filename[:-3]
			if filename in self.recList:
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if timer.isRunning() and not timer.justplay and timer.Filename.find(filename)>=0:
						if timer.repeated: return False
						timer.afterEvent = AFTEREVENT.NONE
						NavigationInstance.instance.RecordTimer.removeEntry(timer)
						spDebugOut("[spRC] REC STOP for: " + filename)
						return True
			else:
				spDebugOut("[spRC] OOPS stop REC for nonexistent: " + filename)
		except Exception, e:
			spDebugOut("[spRC] stopRecording exception:\n" + str(e))
		return False

	def fixTimerPath(self, old, new):
		try:
			if old.endswith(".ts"):	old = old[:-3]
			if new.endswith(".ts"):	new = new[:-3]
			for timer in NavigationInstance.instance.RecordTimer.timer_list:
				if timer.isRunning() and not timer.justplay and timer.Filename == old:
					timer.dirname = os.path.split(new)[0] + "/"
					timer.fixMoveCmd = 'mv "'+ timer.Filename +'."* "'+ timer.dirname +'"'
					timer.Filename = new
					spDebugOut("[spRC] fixed path: " + new)
					break

		except Exception, e:
			spDebugOut("[spRC] fixTimerPath exception:\n" + str(e))

	def remoteInit(self, ip):
		try:
			if ip is not None:
				self.recFile = config.suomipoeka.folder.value + "/db_%s.rec" %str(ip).replace(", ", ".")[1:-1]
		except Exception, e:
			spDebugOut("[spRC] remoteInit exception:\n" + str(e))

	def recFileUpdate(self):
		try:
			if self.recFile is None: self.remoteInit( spNET.whatIsMyIP() )
			if self.recFile is None: return	# was not able to get IP
			recf = open(self.recFile, "wb")
			pickle.dump(self.recList, recf)
			recf.close()
		except Exception, e:
			spDebugOut("[spRC] recFileUpdate exception:\n" + str(e))

	def recFilesRead(self):
		if self.recFile is None: self.recFileUpdate()
		if self.recFile is None: return
		self.recRemoteList = []
		try:
			for x in os.listdir(config.suomipoeka.folder.value):
				if x.endswith(".rec") and x != self.recFile.split("/")[-1]:
#					spDebugOut("[spRC] reading " + x)
					recf = open(config.suomipoeka.folder.value +"/"+ x, "rb")
					self.recRemoteList += pickle.load(recf)
					recf.close()
#				else:
#					spDebugOut("[spRC] skipped " + x)

		except Exception, e:
			spDebugOut("[spRC] recFilesRead exception:\n" + str(e))
