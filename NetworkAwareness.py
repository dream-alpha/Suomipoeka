#!/usr/bin/python
# encoding: utf-8
#
# Network interfacing class for the suomipoeka plugin by moveq
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

import os
#from Components.config import config
from Components.Network import iNetwork
from SuomipoekaTasker import spDebugOut
from DelayedFunction import DelayedFunction


class NetworkAwareness:
	def __init__(self):
		self.retries = 0
		self.ip = None
		self.initialized = False

	def whatIsMyIP(self):
		if not self.initialized: self.ipLookup()
		return self.ip

	def ipLookup(self):
		os.system("ifconfig | grep Bcast | sed 's;^.*addr:;;' | sed 's: .*::' >/tmp/myip")
		file = open("/tmp/myip")
		myip = file.read()
		file.close()
		self.ip = [ int(a) for a in myip.split(".") ]
		if len(self.ip) != 4:
			self.ip = [0,0,0,0]
		else:
			self.initialized = True
		spDebugOut( "[spNET] IP = " + str(self.ip).replace(", ", ".")[1:-1] )

# this is not workihn on older Enigma2
#		if iNetwork.configuredInterfaces == []:
#			self.retries += 1
#			if self.retries <= 10:
#				DelayedFunction(4000, self.ipLookup)
#				return
#
#		self.intf = iNetwork.configuredInterfaces[0]
#		self.ip = iNetwork.getAdapterAttribute(self.intf, "ip")
#		if len(self.ip) == 4:
#			spDebugOut( "[spNET] got IP after %d retries" %(self.retries) )
#			spDebugOut( "[spNET] IFs = " + str(iNetwork.configuredInterfaces) )
#			spDebugOut( "[spNET] IP = " + str(self.ip).replace(", ", ".")[1:-1] )
#			spDebugOut( "[spNET] count = " + str(len(iNetwork.getConfiguredAdapters())) )
#			spDebugOut( "[spNET] name servers = " + str(len(iNetwork.getNameserverList())) )
#			for x in iNetwork.getAdapterList():
#				spDebugOut( "[spNET] found adapter: " + str(iNetwork.getFriendlyAdapterName(x)) + " -- " + str(x) )
#	def cleanup(self):
#		if 0:
#			iNetwork.stopLinkStateConsole()
#			iNetwork.stopRestartConsole()
#			iNetwork.stopGetInterfacesConsole()

spNET = NetworkAwareness()
