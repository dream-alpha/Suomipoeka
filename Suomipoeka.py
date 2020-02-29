#!/usr/bin/python
# encoding: utf-8
#
# Suomipoeka plugin by moveq
# Copyright (C) 2007-2010 moveq / Suomipoeka team (suomipoeka@gmail.com)
# If you feel like donating to support the development, that may be done
# via PayPal (account: suomipoeka@gmail.com).
#
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
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Language import *
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.ServiceScan import *
#from Screens.Standby import *
import Screens.Standby
from Tools import Notifications
from enigma import eServiceEvent
import os, struct, gettext

from SuomipoekaTasker import spTasker, spDebugOut
from DelayedFunction import DelayedFunction
from NetworkAwareness import spNET

SuomipoekaVersion = "V1.0.1"
SuomipoekaAbout = "Suomipoeka plugin " +SuomipoekaVersion+ " by moveq. Aimed to enhance the recordings list user experience and also to give better localisation support with different GUI & EPG languages.\n\nPlugin's usage is free and the source is licensed under GPL. If you wish to support the development, donations may be done via PayPal (account: suomipoeka@gmail.com).\n\nContact at: suomipoeka@gmail.com.\n\nmodded by Coolman & Swiss-MAD"

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

def setEPGLanguage(dummy=None):
	if config.suomipoeka.epglang.value:
		spDebugOut("Setting EPG language: " + str(config.suomipoeka.epglang.value))
	 	eServiceEvent.setEPGLanguage(config.suomipoeka.epglang.value)
language.addCallback(setEPGLanguage)
DelayedFunction(5000, setEPGLanguage)

def localeInit():
	lang = language.getLanguage()[:2] # getLanguage returns e.g. "fi_FI" for "language_country"
	os.environ["LANGUAGE"] = lang # Enigma doesn't set this (or LC_ALL, LC_MESSAGES, LANG). gettext needs it!
	gettext.bindtextdomain("Suomipoeka", resolveFilename(SCOPE_PLUGINS, "Extensions/Suomipoeka/locale"))

def _(txt):
	if language.getActiveLanguage() == "en_EN": return txt
	return gettext.dgettext("Suomipoeka", txt)

def setupKeyResponseValues(dummy=None):
	# currently not working on DM500/DM600, wrong input dev files?
	e1 = os.open("/dev/input/event0", os.O_RDWR)
	e2 = os.open("/dev/input/event0", os.O_RDWR)
	s1 = struct.pack("LLHHl", 0, 0, 0x14, 0x00, config.suomipoeka.key_repeat.value)
	s2 = struct.pack("LLHHl", 0, 0, 0x14, 0x01, config.suomipoeka.key_period.value)
	size = struct.calcsize("LLHHl")
	os.write(e1, s1)
	os.write(e2, s1)
	os.write(e1, s2)
	os.write(e2, s2)
	os.close(e1)
	os.close(e2)

trashCleanCall = None

def trashCleanSetup(dummyparam=None):
	try:
		global trashCleanCall
		if trashCleanCall is not None:
			trashCleanCall.cancel()

		if config.suomipoeka.movie_trashcan_clean.value is True:
			cltime = config.suomipoeka.movie_trashcan_ctime.value
			lotime = localtime()
			ltime = lotime[3]*60 + lotime[4]
			ctime = cltime[0]*60 + cltime[1]
			seconds = 60 * (ctime - ltime)
			if seconds < 0:
				seconds += 86400	# 24*60*60
			if seconds < 60:
				seconds = 60
			from MovieSelection import gMS
			trashCleanCall = DelayedFunction(1000*seconds, gMS.purgeExpiredFromTrash)
			DelayedFunction(2000, gMS.purgeExpiredFromTrash)
			from SuomipoekaTasker import spDebugOut
			spDebugOut("Next trashcan cleanup in " + str(seconds) + " seconds")
	except Exception, e:
		from SuomipoekaTasker import spDebugOut
		spDebugOut("[sp] trashCleanSetup exception:\n" + str(e))

def suomipoekaStartup(session):
	if not os.path.exists(config.suomipoeka.folder.value):
		spTasker.shellExecute("mkdir " + config.suomipoeka.folder.value)
	spDebugOut("+++ Suomipoeka "+SuomipoekaVersion+" startup")

 	if config.suomipoeka.epglang.value:
	 	eServiceEvent.setEPGLanguage(config.suomipoeka.epglang.value)
	setupKeyResponseValues()
	DelayedFunction(5000, trashCleanSetup)

	# Go into standby if the reason for restart was Suomipoeka auto-restart
	if os.path.exists(config.suomipoeka.folder.value + "/suomipoeka_standby_flag.tmp"):
		spDebugOut("+++ Going into Standby mode after auto-restart")
		Notifications.AddNotification(Screens.Standby.Standby)
		spTasker.shellExecute("rm -f " + config.suomipoeka.folder.value + "/suomipoeka_standby_flag.tmp")

class SuomipoekaMenu(ConfigListScreen, Screen):
	skin = """
	<screen name="SuomipoekaMenu" position="center,center" size="620,470" title="SuomipoekaMenu">
		<widget name="config" position="10,10" size="605,400" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/key-red.png" position="66,425" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Suomipoeka/img/key-green.png" position="412,425" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<widget name="key_red" position="66,425" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
		<widget name="key_green" position="412,425" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "SuomipoekaMenu"
		self.skin = SuomipoekaMenu.skin

		self["actions"] = ActionMap(["ChannelSelectBaseActions", "OkCancelActions", "ColorActions"],
		{
			"ok":			self.keyOK,
			"cancel":		self.keyCancel,
			"red":			self.keyCancel,
			"green": 		self.keySaveNew,
			"nextBouquet":	self.bouquetPlus,
			"prevBouquet":	self.bouquetMinus,
		}, -2)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(" ")
		self["key_blue"] = Button(" ")

		self.list = []
		ConfigListScreen.__init__(self, self.list)

		self.onShown.append(self.onDialogShow)

		self.list.append(getConfigListEntry(_("About"), config.suomipoeka.about, None, self.showInfo))
		self.list.append(getConfigListEntry(_("Button to override for MovieList launch"), config.suomipoeka.movie_launch, self.launchListSet, None))
		self.list.append(getConfigListEntry(_("Show plugin config in extensions menu"), config.suomipoeka.extmenu_plugin, self.needsRestart, None))
		self.list.append(getConfigListEntry(_("Show MovieList in extensions menu"), config.suomipoeka.extmenu_list, self.needsRestart, None))
		self.list.append(getConfigListEntry(_("Preferred EPG language"), config.suomipoeka.epglang, setEPGLanguage, None))
		self.list.append(getConfigListEntry(_("Primary playback subtitle language"), config.suomipoeka.sublang1, None, None))
		self.list.append(getConfigListEntry(_("Secondary playback subtitle language"), config.suomipoeka.sublang2, None, None))
		self.list.append(getConfigListEntry(_("Tertiary playback subtitle language"), config.suomipoeka.sublang3, None, None))
		self.list.append(getConfigListEntry(_("Enable playback auto-subtitling"), config.suomipoeka.autosubs, None, None))
		self.list.append(getConfigListEntry(_("Primary playback audio language"), config.suomipoeka.audlang1, None, None))
		self.list.append(getConfigListEntry(_("Secondary playback audio language"), config.suomipoeka.audlang2, None, None))
		self.list.append(getConfigListEntry(_("Tertiary playback audio language"), config.suomipoeka.audlang3, None, None))
		self.list.append(getConfigListEntry(_("Enable playback auto-language selection"), config.suomipoeka.autoaudio, None, None))
		self.list.append(getConfigListEntry(_("Movie home home path"), config.suomipoeka.movie_homepath, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("Movie trashcan path"), config.suomipoeka.movie_trashpath, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("How many days files may remain in trashcan"), config.suomipoeka.movie_trashcan_limit, None, None))
		self.list.append(getConfigListEntry(_("Enable daily trashcan cleanup"), config.suomipoeka.movie_trashcan_clean, trashCleanSetup))
		self.list.append(getConfigListEntry(_("Daily trashcan cleanup time"), config.suomipoeka.movie_trashcan_ctime, trashCleanSetup))

		self.list.append(getConfigListEntry(_("Disable MovieList"), config.suomipoeka.ml_disable, self.needsRestart, None))
		self.list.append(getConfigListEntry(_("MovieList path access limit"), config.suomipoeka.movie_pathlimit, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("MovieList desc field update delay"), config.suomipoeka.movie_descdelay, None, None))
		self.list.append(getConfigListEntry(_("MovieList file order reverse"), config.suomipoeka.movielist_reversed, None, None))
		self.list.append(getConfigListEntry(_("MovieList open with cursor on newest (TV mode)"), config.suomipoeka.movielist_gotonewest, None, None))
		self.list.append(getConfigListEntry(_("MovieList open with cursor on newest (player)"), config.suomipoeka.movielist_gotonewestp, None, None))
		self.list.append(getConfigListEntry(_("MovieList cursor predictive move after selection"), config.suomipoeka.movielist_selmove, None, None))
		self.list.append(getConfigListEntry(_("MovieList show movie icons"), config.suomipoeka.movie_icons, None, None))
		self.list.append(getConfigListEntry(_("MovieList show icon indication for non-watched"), config.suomipoeka.movie_mark, None, None))
		self.list.append(getConfigListEntry(_("MovieList try to load titles from .meta files"), config.suomipoeka.movie_metaload, None, None))
		self.list.append(getConfigListEntry(_("MovieList re-open list after Movie end"), config.suomipoeka.movie_reopenEOF, None, None))
		self.list.append(getConfigListEntry(_("MovieList re-open list after STOP-press"), config.suomipoeka.movie_reopen, None, None))
		self.list.append(getConfigListEntry(_("MovieList display directory reading text"), config.suomipoeka.movielist_loadtext, None, None))
		self.list.append(getConfigListEntry(_("MovieList always reload after open"), config.suomipoeka.movie_reload, None, None))
		self.list.append(getConfigListEntry(_("MovieList blue button function"), config.suomipoeka.movie_bluefunc, None, None))
		self.list.append(getConfigListEntry(_("MovieList hide movies being moved"), config.suomipoeka.movie_hide_mov, None, None))
		self.list.append(getConfigListEntry(_("MovieList hide movies being deleted"), config.suomipoeka.movie_hide_del, None, None))
		self.list.append(getConfigListEntry(_("MovieList hide trashcan directory"), config.suomipoeka.movie_trashcan_hide, None, None))
		self.list.append(getConfigListEntry(_("MovieList hide VLC directory"), config.suomipoeka.movie_vlc_hide, None, None))
		self.list.append(getConfigListEntry(_("Automatic timers list cleaning"), config.suomipoeka.timer_autocln, None, None))

		self.list.append(getConfigListEntry(_("Enigma daily auto-restart"), config.suomipoeka.enigmarestart, self.autoRestartInfo, self.autoRestartInfo))
		self.list.append(getConfigListEntry(_("Enigma auto-restart window begin"), config.suomipoeka.enigmarestart_begin, self.autoRestartInfo, self.autoRestartInfo))
		self.list.append(getConfigListEntry(_("Enigma auto-restart window end"), config.suomipoeka.enigmarestart_end, self.autoRestartInfo, self.autoRestartInfo))
		self.list.append(getConfigListEntry(_("Force standby after auto-restart"), config.suomipoeka.enigmarestart_stby, None, None))

		self.list.append(getConfigListEntry(_("Suomipoeka output directory"), config.suomipoeka.folder, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("Enable Suomipoeka debug output"), config.suomipoeka.debug, self.dbgChange, None))
		self.list.append(getConfigListEntry(_("Debug output file name"), config.suomipoeka.debugfile, None, None))
		self.list.append(getConfigListEntry(_("Key period value (30-900)"), config.suomipoeka.key_period, setupKeyResponseValues, None))
		self.list.append(getConfigListEntry(_("Key repeat value (250-900)"), config.suomipoeka.key_repeat, setupKeyResponseValues, None))
		try:
			self.list.append(getConfigListEntry(_("Enable component video in A/V Settings"), config.av.yuvenabled, self.needsRestart, None))
		except: pass

		self.needsRestartFlag = False

	def onDialogShow(self):
		self.setTitle("Suomipoeka! "+ SuomipoekaVersion)

	def bouquetPlus(self):
		self["config"].setCurrentIndex( max(self["config"].getCurrentIndex()-16, 0) )

	def bouquetMinus(self):
		self["config"].setCurrentIndex( min(self["config"].getCurrentIndex()+16, len(self.list)-1) )

	def needsRestart(self, dummy=None):
		self.needsRestartFlag = True

	def autoRestartInfo(self, dummy=None):
		spTasker.ShowAutoRestartInfo()

	def launchListSet(self, value):
		if value is not None:
			self.needsRestart()

	def dbgChange(self, value):
		if value == True:
			pass
		else:
			spTasker.shellExecute("rm -f " + config.suomipoeka.folder.value + config.suomipoeka.debugfile.value)

	def validatePath(self, value):
		if not os.path.exists(str(value)):
			self.session.open(MessageBox, _("Given path %s does not exist. Please change." % str(value)), MessageBox.TYPE_ERROR)

	def dirSelected(self, res):
		if res is not None:
			if res[-1:] == "/":
				res = res[:-1]
			self.list[self["config"].getCurrentIndex()][1].value = res

	def openLocationBox(self):
		try:
			path = self.list[ self["config"].getCurrentIndex() ][1].value + "/"
			from Screens.LocationBox import LocationBox
			self.session.openWithCallback(self.dirSelected, LocationBox, text = _("Choose directory"), filename = "", currDir = path, minFree = 100)
		except:
			pass

	def keyOK(self):
		try:
			self.list[self["config"].getCurrentIndex()][3]()
		except:
			pass

	def showRestart(self):
		spTasker.ShowAutoRestartInfo()

	def showInfo(self):
		self.session.open(MessageBox, SuomipoekaAbout, MessageBox.TYPE_INFO)

	def keySaveNew(self):
		for entry in self.list:
			if entry[1].isChanged():
				entry[1].save()
				if entry[2] is not None:
					entry[2](entry[1].value)	# execute value changed -function
		if self.needsRestartFlag:
			self.session.open(MessageBox, _("Some settings changes require GUI restart to take effect."), MessageBox.TYPE_INFO, 10)
		self.keySave()
		self.close()

	def keyCancel(self):
		for entry in self.list:
			if entry[1].isChanged():
				entry[1].cancel()
		self.close()
