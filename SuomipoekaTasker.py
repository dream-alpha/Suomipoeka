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
from enigma import eTimer, eConsoleAppContainer
from Components.config import *
from Screens.MessageBox import MessageBox
from Screens.Standby import *
from time import localtime
import Screens.Standby
import os

#global spDebugOut
def spDebugOut(outtxt, outfile=None, fmode="aw", forced=False):
	try:	# fails if called too early during Enigma startup
		if config.suomipoeka.debug.value or forced:
			if outfile is None:
				outfile = config.suomipoeka.folder.value +"/"+ config.suomipoeka.debugfile.value
				ltim = localtime()
				headerstr = "%04d%02d%02d %02d:%02d " %(ltim[0],ltim[1],ltim[2],ltim[3],ltim[4])
				outtxt = headerstr + outtxt + "\n"
			deb = open(outfile, fmode)
			deb.write(outtxt)
			deb.close()
	except: pass

class SuomipoekaExecutioner:
	def __init__(self, identifier):
		self.appContainer = eConsoleAppContainer()
		try:	# get() has been removed from newer CVS versions
			self.appContainer.appClosed.get().append(self.runFinished)
			self.appContainer.dataAvail.get().append(self.dataAvail)	# this will cause interfilesystem transfers to stall Enigma
		except:
			self.appContainer.appClosed.append(self.runFinished)
			self.appContainer.dataAvail.append(self.dataAvail)	# this will cause interfilesystem transfers to stall Enigma
		self.scriptlut = ["/tmp/scr"+identifier+"0.sh", "/tmp/scr"+identifier+"1.sh"]
		self.associated = [ [], [] ]
		self.executing = ""
		self.execCount = 0
		self.returnData = ""

	def isIdle(self):
		return self.executing == ""

	def shellExecute(self, string, associated=None):	# associated = tuple:(service, callback)
		string = string.replace("; ","\n")
		try:
			if associated is not None and associated != []:
				self.associated[ self.execCount & 1 ] += associated	# append whatever that's associated with the execution of the script
			sfile = self.scriptlut[ self.execCount & 1 ]
			script = open(sfile, "aw")
			script.write("\n" + string)
			script.close()
			if self.executing == "":
				spDebugOut("[spTasker] "+ sfile +" +=\n"+ string)
				self.execCurrent()
			else:
				spDebugOut("[spTasker] (bg) "+ sfile +" +=\n"+ string)
		except Exception, e:
			spDebugOut("[spTasker] shellExecute exception:\n" + str(e))

	def execCurrent(self):
		# "double buffer" with two scripts, one being executed and one being written
		self.executing = self.scriptlut[ self.execCount & 1 ]
		sfile = open(self.executing, "r")
		scr = sfile.read()
		sfile.close()

		self.appContainer.execute("sh " + self.executing)
		spDebugOut("[spTasker] executing " + self.executing + scr)
		self.execCount += 1

	def runFinished(self, retval):
		try:
			os.remove(self.executing)
			associated = self.associated[ self.execCount-1 & 1 ]
			spDebugOut("[spTasker] sh exec %s finished, return status = %s%s" %(self.executing, str(retval), self.returnData))
			for x in associated:
				if x[1] is not None:
					x[1](x[0])			# callback(service)
			self.associated[ self.execCount-1 & 1 ][:] = []	# clear list
			self.returnData = ""
			if os.path.exists(self.scriptlut[ self.execCount & 1 ]):
				spDebugOut("[spTasker] sh exec rebound")
				self.execCurrent()
			else:
				self.executing = ""
		except Exception, e:
			spDebugOut("[spTasker] runFinished exception:\n" + str(e))

	def dataAvail(self, string):
		self.returnData += "\n" + string.replace("\n","")



class SuomipoekaTasker:
	def __init__(self):
		self.restartTimer = eTimer()
		self.restartTimer.timeout.get().append(self.RestartTimerStart)
		self.minutes = 0
		self.timerActive = False
		self.executioners = []
		self.executioners.append( SuomipoekaExecutioner("A") )
		self.executioners.append( SuomipoekaExecutioner("B") )
		self.executioners.append( SuomipoekaExecutioner("C") )

	def shellExecute(self, string, associated=None):
		for x in self.executioners:
			if x.isIdle():
				x.shellExecute(string, associated)
				return
		# all were busy, just append to any task list randomly
		import random
		self.executioners[ random.randint(0, 2) ].shellExecute(string, associated)

	def Initialize(self, session):
		self.session = session
		if config.suomipoeka.enigmarestart.value:
			from DelayedFunction import DelayedFunction
			DelayedFunction(60 * 1000, self.RestartTimerStart, True)	# delay auto restart timer to make sure there's time for clock init

	def ShowAutoRestartInfo(self):
		# call the Execute/Stop function to update minutes
		if config.suomipoeka.enigmarestart.value:
			self.RestartTimerStart(True)
		else:
			self.RestartTimerStop()

		from Suomipoeka import _
		if self.timerActive:
			mints = self.minutes % 60
			hours = self.minutes / 60
			self.session.open(MessageBox, _("Next Enigma auto-restart in ")+ str(hours) +" h "+ str(mints) +" min", MessageBox.TYPE_INFO, 4)
		else:
			self.session.open(MessageBox, _("Enigma auto-restart is currently not active."), MessageBox.TYPE_INFO, 4)

	def RestartTimerStop(self):
		self.restartTimer.stop()
		self.timerActive = False
		self.minutes = 0

	def InitRestart(self):
		if Screens.Standby.inStandby:
			self.LaunchRestart(True)	# no need to query if in standby mode
		else:
			# query from the user if it is ok to restart now
			stri = _("Suomipoeka Enigma2 auto-restart launching, continue? Select no to postpone by one hour.")
			self.session.openWithCallback(self.LaunchRestart, MessageBox, stri, MessageBox.TYPE_YESNO, 30)

	def LaunchRestart(self, confirmFlag=True):
		if confirmFlag:
			spDebugOut("+++ Enigma restart NOW")
			if Screens.Standby.inStandby or config.suomipoeka.enigmarestart_stby.value:
				spDebugOut("!", config.suomipoeka.folder.value + "/suomipoeka_standby_flag.tmp", fmode="w", forced=True)
			else:
				self.shellExecute("rm -rf " + config.suomipoeka.folder.value + "/suomipoeka_standby_flag.tmp")
			self.session.open(TryQuitMainloop, 3)
			# this means that we're going to be re-instantiated after Enigma has restarted
		else:
			self.RestartTimerStart(True, 60)

	def RestartTimerStart(self, initializing=False, postponeDelay=0):
		try:
			self.restartTimer.stop()
			self.timerActive = False

			lotime = localtime()
			wbegin = config.suomipoeka.enigmarestart_begin.value
			wend = config.suomipoeka.enigmarestart_end.value
			xtimem = lotime[3]*60 + lotime[4]
			ytimem = wbegin[0]*60 + wbegin[1]
			ztimem = wend[0]*60 + wend[1]

			if ytimem > ztimem:	ztimem += 12*60
			spDebugOut("+++ Local time is " +str(lotime[3:5]) + ", auto-restart window is %s - %s" %(str(wbegin), str(wend)) )

			if postponeDelay > 0:
				self.restartTimer.start(postponeDelay * 60000, False)
				self.timerActive = True
				mints = postponeDelay % 60
				hours = postponeDelay / 60
				spDebugOut("+++ User postponed auto-restart by " +str(hours)+ "h " +str(mints)+ "min")
				return

			minsToGo = ytimem - xtimem
			if xtimem > ztimem:	minsToGo += 24*60

			if initializing or minsToGo > 0:
				if minsToGo < 0:		# if initializing
					minsToGo += 24*60	# today's window already passed
				elif minsToGo == 0:
					minsToGo = 1
				self.restartTimer.start(minsToGo * 60000, False)
				self.timerActive = True
				self.minutes = minsToGo
				mints = self.minutes % 60
				hours = self.minutes / 60
				spDebugOut("+++ Auto restart rescheduled in " +str(hours)+ "h " +str(mints)+ "min")
			else:
				recordings = len(self.session.nav.getRecordings())
				next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
				if not recordings and (((next_rec_time - time()) > 360) or next_rec_time < 0):
					spDebugOut("--> spTasker.InitRestart()")
					self.InitRestart()
				else:
					spDebugOut("+++ REC in progress, auto restart rescheduled in 15 min")
					self.minutes = 15
					self.restartTimer.start(15*60*1000, False)
					self.timerActive = True
		except Exception, e:
			spDebugOut("[spTasker] RestartTimerStart exception:\n" + str(e))

spTasker = SuomipoekaTasker()
