###
# Copyright (c) 2014, Finn Herzfeld
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs
import supybot.ircdb as ircdb
from supybot.i18n import PluginInternationalization, internationalizeDocstring

import supybot.schedule as schedule
import supybot.conf as conf
import requests
import ConfigParser
import json
import re

_ = PluginInternationalization('SeattleIncidentResponse')

@internationalizeDocstring
class SeattleIncidentResponse(callbacks.Plugin):
    """No user interaction needed. Set the config
    as described in the README."""
    pass
    
    def __init__(self, irc):
        self.__parent = super(SeattleIncidentResponse, self)
        self.__parent.__init__(irc)
        self.savefile = conf.supybot.directories.data.dirize("SeattleIncidentResponse.db")
                
        def checkForPosts():
            self.checkForIncidents(irc)
        try:
            schedule.addPeriodicEvent(checkForPosts, self.registryValue('checkinterval')*60, 'incidentresponsecheck', False)
        except AssertionError:
            schedule.removeEvent('incidentresponsecheck')
            schedule.addPeriodicEvent(checkForPosts, self.registryValue('checkinterval')*60, 'incidentresponsecheck', False)
    
    def post(self, irc, channel, msg):
        try:
            irc.queueMsg(ircmsgs.privmsg(channel, str(msg)))
        except Exception as e:
            self.log.warning("Failed to send to " + channel + ": " + str(type(e)))
            self.log.warning(str(e.args))
            self.log.warning(str(e))
    
    def checkForIncidents(self, irc):
        try:
            data = json.load(open(self.savefile))
        except Exception as inst:
            data = []
        url = "http://data.seattle.gov/resource/3k2p-39jp.json"
        self.log.debug("Retreiving %s" % url)
        request = requests.get(url).json()
        self.log.debug("Retreived and converted to JSON. %i entries" % len(request))
        try:
            messageformat = "[Inident Response] [{incident_number}][{incident_type}] {address}"
            if self.registryValue('postformat'):
                messageformat = self.registryValue('postformat')
            actuallyannounce = True
            if len(data) == 0:
                actuallyannounce = False
                self.info.log("Not actually announcing, current dataset is 0 (likely our first time)")
            for incident in request:
                if "cad_event_number" in incident:
                    if not incident['cad_event_number'] in data:
                        self.log.debug("Preparing to announce: %s" %srt(incident))
                        msg = messageformat.format(
                            cad_event_number = incident['cad_event_number'],
                            cad_cdw_id = incident['cad_cdw_id'],
                            zone_beat = incident['zone_beat'],
                            district_sector = incident['district_sector'],
                            hundred_block_location = incident['hundred_block_location'],
                            general_offense_number = incident['general_offense_number'],
                            bold = chr(002),
                            underline = "\037",
                            reverse = "\026",
                            white = "\0030",
                            black = "\0031",
                            blue = "\0032",
                            red = "\0034",
                            dred = "\0035",
                            purple = "\0036",
                            dyellow = "\0037",
                            yellow = "\0038",
                            lgreen = "\0039",
                            dgreen = "\00310",
                            green = "\00311",
                            lpurple = "\00313",
                            dgrey = "\00314",
                            lgrey = "\00315",
                            close = "\003")
                        for channel in irc.state.channels:
                            if self.registryValue('enabled', channel) and actuallyannounce:
                                self.post(irc, channel, msg)
                            else:
                                self.log.debug("Not posting to %s: %s" % (channel, msg))
                        data.append(incident['cad_event_number'])
        except Exception as e:
            self.log.info(str(incident))
            self.log.info(str(messageformat))
            self.log.warning("Whoops! Something fucked up! ")
            self.log.warning(str(type(e)))
            self.log.warning(str(e.args))
            self.log.warning(str(e))
        savefile = open(self.savefile, "w")
        savefile.write(json.dumps(data))
        savefile.close()
    
    def check(self, irc, msg, args):
        """takes no args
                
        Checks for new incident responses"""
        if ircdb.checkCapability(msg.prefix, "owner"):
            irc.reply("Checking!")
            self.checkForIncidents(irc)
        else:
            irc.reply("Fuck off you unauthorized piece of shit")
    check = wrap(check)
    
    def start(self, irc, msg, args):
        """takes no arguments

        A command to start the node checker."""
        # don't forget to redefine the event wrapper
        if ircdb.checkCapability(msg.prefix, "owner"):
            def checkForPosts():
                self.checkForIncidents(irc)
            try:
                schedule.addPeriodicEvent(checkForPosts, self.registryValue('checkinterval')*60, 'incidentresponsecheck', False)
            except AssertionError:
                irc.reply('The incident response was already running!')
            else:
                irc.reply('Incident response checker started!')
        else:
            irc.reply("Fuck off you unauthorized piece of shit")
    start = wrap(start)
    
    def stop(self, irc, msg, args):
        """takes no arguments

        A command to stop the node checker."""
        if ircdb.checkCapability(msg.prefix, "owner"):
            try:
                schedule.removeEvent('incidentresponsecheck')
            except KeyError:
                irc.reply('Error: the incident response checker wasn\'t running!')
            else:
                irc.reply('incident response checker stopped.')
        else:
            irc.reply("Fuck off you unauthorized piece of shit")
    stop = wrap(stop)

Class = SeattleIncidentResponse


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
