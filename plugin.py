# Domoticz plugin for controlling Extron SSP 7.1
#
# Author: azvero
#
"""
<plugin key="Extron" name="Extron SSP 7.1" author="azvero" version="1.0.0" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="http://www.extron.com/">
  <params>
    <param field="Address" label="IP Address or Hostname" width="200px" required="true"/>
    <param field="Port" label="Telnet Port" width="50px" required="true" default="2001"/>
    <param field="Mode1" label="Inputs" width="400px" required="true" default="Off|1 (digital optical)|2 (digital optical)|3 (digital coax)|4 (ditial coax)|5 (analog)"/>
  </params>
</plugin>
"""
import re
import Domoticz

_CMD_GET_ALL_MUTE = "Z"
_CMD_SET_ALL_MUTE = "{muted}Z"
_CMD_GET_AUDIO_INPUT = "$"
_CMD_SET_AUDIO_INPUT = "{input}$"
_CMD_GET_VOLUME = "V"
_CMD_SET_VOLUME = "{volume}V"

_RE_MUTE = re.compile(rb"Amt(?P<muted>[01])$")
_RE_INPUT = re.compile(rb"Aud(?P<input>\d)$")
_RE_VOLUME = re.compile(rb"Vol(?P<volume>\d+)$")

_UNIT_VOLUME = 1
_UNIT_INPUT = 2

class BasePlugin(object):

    enabled = False

    def __init__(self):
        self._connection = None
        self._input = 1
        self._muted = False
        self._volume = 50

    def onStart(self):
        Domoticz.Log("onStart called")  # The first heartbeat will connect
        if not Devices:
            Domoticz.Device(Name="Volume", Unit=_UNIT_VOLUME, Type=244, Subtype=73, Switchtype=7, Image=8).Create()
            Domoticz.Device(Name="Input", Unit=_UNIT_INPUT, TypeName="Selector Switch", Options={
                "LevelActions"   : "",
                "LevelNames"     : Parameters["Mode1"],
                "LevelOffHidden" : "true",
                "SelectorStyle"  : "1"
                }, Image=5).Create()

    def onStop(self):
        Domoticz.Log("onStop called")
        self._connection.Disconnect()
        self._connection = None

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called: Status=%s Description=%s" % (
            Status, Description))
        self._Send(_CMD_GET_ALL_MUTE)
        self._Send(_CMD_GET_AUDIO_INPUT)
        self._Send(_CMD_GET_VOLUME)

    def onMessage(self, Connection, Data):
        Data = Data.strip()
        Domoticz.Log("onMessage called: Data=%s" % (
            Data,))
        match = _RE_INPUT.match(Data)
        if match:
            input = int(match.group("input"))
            Domoticz.Log("Input=%d" % input)
            self._UpdateDevice(_UNIT_INPUT, sValue=(input*10))
            return
        match = _RE_MUTE.match(Data)
        if match:
            muted = bool(int(match.group("muted")))
            Domoticz.Log("Muted=%d" % muted)
            self._UpdateDevice(_UNIT_VOLUME, nValue=int(not muted))
            return
        match = _RE_VOLUME.match(Data)
        if match:
            volume = int(match.group("volume"))
            Domoticz.Log("Volume=%d" % volume)
            self._UpdateDevice(_UNIT_VOLUME, sValue=volume)
            return

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called: Unit=%s Command=%s Level=%s Hue=%s" % (
            Unit, Command, Level, Hue))
        if Unit == _UNIT_VOLUME:
            if Command == "Set Level":
                self._Send(_CMD_SET_VOLUME.format(volume=Level))
            elif Command == "On":
                self._Send(_CMD_SET_ALL_MUTE.format(muted=0))
            elif Command == "Off":
                self._Send(_CMD_SET_ALL_MUTE.format(muted=1))
            else:
                Domoticz.Error("Unsupported volume command: %s" % Command)
        elif Unit == _UNIT_INPUT:
            if Command == "Set Level":
                self._Send(_CMD_SET_AUDIO_INPUT.format(input=(Level//10)))
            else:
                Domoticz.Error("Unsupported input command: %s" % Command)
        else:
            Domoticz.Error("Unsupported unit: %d" % Unit)

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("onNotification called: Name=%s Subject=%s Text=%s Status=%s Priority=%s Sound=%s ImageFile=%s" % (
            Name, Subject, Text, Status, Priority, Sound, ImageFile))

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")
        self._connection = None  # next heartbeat will reconnect

    def onHeartbeat(self):
        Domoticz.Log("onHeartbeat called")
        if self._connection is None:
            self._Connect()
        elif self._connection.Connected:
            pass
        else:
            Domoticz.Log("Not yet connected, ignoring the heartbeat")

    def _Connect(self):
        address = Parameters["Address"]
        port = Parameters["Port"]
        Domoticz.Log("Connecting to %s:%s" % (address, port))
        self._connection = Domoticz.Connection(
                Name="Extron connection", Transport="TCP/IP", Protocol="Line",
                Address=address, Port=port)
        self._connection.Connect()

    def _Send(self, Command):
        if self._connection and self._connection.Connected:
            Domoticz.Log("Sending %s" % Command)
            self._connection.Send(Command)
        else:
            Domoticz.Log("Not sending since not connected (%s)" % Command)

    def _UpdateDevice(self, Unit, nValue=None, sValue=None):
	# Make sure that the Domoticz device still exists (they can be deleted) before updating it
        if Unit not in Devices:
            return
        device = Devices[Unit]
        # None nValue or sValue means "leave unchanged"
        if nValue is None:
            nValue = device.nValue
        if sValue is None:
            sValue = device.sValue
        sValue = str(sValue)
        if device.nValue != nValue or device.sValue != sValue:
            Domoticz.Log("Updating unit %d: nValue=%s->%s sValue=%s->%s" % (
                Unit, device.nValue, nValue, device.sValue, sValue))
            device.Update(nValue, sValue)


_plugin = BasePlugin()
onStart = _plugin.onStart
onStop = _plugin.onStop
onConnect = _plugin.onConnect
onMessage = _plugin.onMessage
onCommand = _plugin.onCommand
onNotification = _plugin.onNotification
onDisconnect = _plugin.onDisconnect
onHeartbeat = _plugin.onHeartbeat

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
