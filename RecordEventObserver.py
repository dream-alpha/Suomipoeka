#!/usr/bin/python
# encoding: utf-8
#
# RecordEventObserver, a helper class written by moveq
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
from enigma import eTimer, iRecordableService	#eServiceReference, eServiceCenter
from SuomipoekaTasker import spDebugOut
import NavigationInstance

class RecordEventObserver:
	def __init__(self, callback):
		self.callback = callback

		try:
			NavigationInstance.instance.RecordTimer.on_state_change.append(self.recEvent)
		except Exception, e:
			spDebugOut("[spRO] Record observer add exception:\n" + str(e))

	def recEvent(self, timer):
		try:
			self.callback(timer)
		except Exception, e:
			spDebugOut("[spRO] recEvent exception:\n" + str(e))

