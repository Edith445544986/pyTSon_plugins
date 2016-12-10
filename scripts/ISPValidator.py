from ts3plugin import ts3plugin, PluginHost
from pytsonui import setupUi, getValues, ValueType
from PythonQt.QtGui import *
from PythonQt.QtCore import QUrl, Qt
from PythonQt.QtNetwork import *
from traceback import format_exc
from urllib.parse import quote as urlencode
from os import path
from configparser import ConfigParser
import ts3, ts3defines

class ISPValidator(ts3plugin):
    name = "ISP Validator"
    apiVersion = 21
    requestAutoload = True
    version = "1.0"
    author = "Bluscream"
    description = "This script will autokick everyone not using a whitelisted ISP.\n\n\nCheck out https://r4p3.net/forums/plugins.68/ for more plugins."
    offersConfigure = True
    commandKeyword = ""
    infoTitle = None
    menuItems = []
    hotkeys = []
    ini = path.join(ts3.getPluginPath(), "pyTSon", "scripts", "ISPValidator", "settings.ini")
    isps = path.join(ts3.getPluginPath(), "pyTSon", "scripts", "ISPValidator", "isps.txt")
    cfg = ConfigParser()
    requested = 0
    schid = 0
    dlg = None

    def __init__(self):
        if path.isfile(self.ini):
            self.cfg.read(self.ini)
        else:
            self.cfg['general'] = { "debug": "False", "whitelist": "True", "kickonly": "False", "bantime": "60", "failover": "False" }
            self.cfg['api'] = { "main": "http://ip-api.com/line/{ip}?fields=isp", "fallback": "http://ipinfo.io/{ip}/org" }
            self.cfg['events'] = { "onConnectStatusChangeEvent": "True", "onClientMoveEvent": "True", "onUpdateClientEvent": "True" }
            with open(self.ini, 'w') as configfile:
                self.cfg.write(configfile)
        with open(self.isps) as f:
            self.isps = f.readlines()
        ts3.logMessage(self.name+" script for pyTSon by "+self.author+" loaded from \""+__file__+"\".", ts3defines.LogLevel.LogLevel_INFO, "Python Script", 0)

    def configDialogClosed(self, r, vals):
        try:
            if r == QDialog.Accepted:
                for name, val in vals.items():
                    try:
                        if not val == self.cfg.getboolean('general', name):
                            self.cfg.set('general', str(name), str(val))
                    except:
                        ts3.logMessage(format_exc(), ts3defines.LogLevel.LogLevel_ERROR, "PyTSon", 0)
                with open(self.ini, 'w') as configfile:
                    self.cfg.write(configfile)
        except:
            ts3.logMessage(format_exc(), ts3defines.LogLevel.LogLevel_ERROR, "PyTSon", 0)

    def configure(self, qParentWidget):
        try:
            if not self.dlg:
                self.dlg = SettingsDialog(self)
            self.dlg.show()
            self.dlg.raise_()
            self.dlg.activateWindow()
        except:
            ts3.logMessage(format_exc(), ts3defines.LogLevel.LogLevel_ERROR, "PyTSon", 0)

    def onConnectStatusChangeEvent(self, serverConnectionHandlerID, newStatus, errorNumber):
        if not self.cfg.getboolean("events", "onConnectStatusChangeEvent"): return
        if newStatus == ts3defines.ConnectStatus.STATUS_CONNECTION_ESTABLISHED:
            (error, ids) = ts3.getClientList(serverConnectionHandlerID)
            if error == ts3defines.ERROR_ok:
                for _in in ids:
                    (error, _type) = ts3.getClientVariableAsInt(serverConnectionHandlerID, clientID, ts3defines.ClientPropertiesRare.CLIENT_TYPE)
                    if error == ts3defines.ERROR_ok and _type == 0:
                        self.requested = clientID;self.schid = serverConnectionHandlerID
                        ts3.requestConnectionInfo(serverConnectionHandlerID, clientID)
                    elif error == ts3defines.ERROR_ok and _type == 1: return
                    else: ts3.printMessageToCurrentTab("[[color=orange]WARNING[/color]] [color=red]ISPValidator could not resolve the client type of '%s'" % self.clientURL(serverConnectionHandlerID, clientID));return

    def onUpdateClientEvent(self, serverConnectionHandlerID, clientID, invokerID, invokerName, invokerUniqueIdentifier):
        if not self.cfg.getboolean("events", "onUpdateClientEvent"): return
        if not invokerID == 0: return
        (error, _type) = ts3.getClientVariableAsInt(serverConnectionHandlerID, clientID, ts3defines.ClientPropertiesRare.CLIENT_TYPE)
        if error == ts3defines.ERROR_ok and _type == 0:
            self.requested = clientID;self.schid = serverConnectionHandlerID
            ts3.requestConnectionInfo(serverConnectionHandlerID, clientID)
        elif error == ts3defines.ERROR_ok and _type == 1: return
        else: ts3.printMessageToCurrentTab("[[color=orange]WARNING[/color]] [color=red]ISPValidator could not resolve the client type of '%s'" % self.clientURL(serverConnectionHandlerID, clientID));return

    def onClientMoveEvent(self, serverConnectionHandlerID, clientID, oldChannelID, newChannelID, visibility, moveMessage):
        if not self.cfg.getboolean("events", "onClientMoveEvent"): return
        if oldChannelID == 0:
            (error, _type) = ts3.getClientVariableAsInt(serverConnectionHandlerID, clientID, ts3defines.ClientPropertiesRare.CLIENT_TYPE)
            if error == ts3defines.ERROR_ok and _type == 0:
                self.requested = clientID;self.schid = serverConnectionHandlerID
                ts3.requestConnectionInfo(serverConnectionHandlerID, clientID)
            elif error == ts3defines.ERROR_ok and _type == 1: return
            else: ts3.printMessageToCurrentTab("[[color=orange]WARNING[/color]] [color=red]ISPValidator could not resolve the client type of '%s'" % self.clientURL(serverConnectionHandlerID, clientID));return

    def onConnectionInfoEvent(self, serverConnectionHandlerID, clientID):
        try:
            if not self.requested == clientID: return
            (error, ip) = ts3.getConnectionVariableAsString(serverConnectionHandlerID, clientID, ts3defines.ConnectionProperties.CONNECTION_CLIENT_IP)
            if error == ts3defines.ERROR_ok:
                self.nwm = QNetworkAccessManager()
                self.nwm.connect("finished(QNetworkReply*)", self.onNetworkReply)
                self.nwm.get(QNetworkRequest(QUrl(self.cfg['api']['main'].replace("{ip}",ip))))
                if self.cfg.getboolean("general", "debug"): ts3.printMessageToCurrentTab(self.cfg['api']['main'].replace("{ip}",ip))
            else:
                (e, msg) = ts3.getErrorMessage(error)
                ts3.printMessageToCurrentTab("[[color=orange]WARNING[/color]] [color=red]ISPValidator could not resolve the IP for '%s' (Reason: %s)" % (self.clientURL(serverConnectionHandlerID, clientID),msg))
        except:
            ts3.printMessageToCurrentTab("[[color=orange]WARNING[/color]] [color=red]ISPValidator could not resolve the IP for '%s' (Reason: %s)" % (self.clientURL(serverConnectionHandlerID, clientID),format_exc()))
    def onNetworkReply(self, reply):
        if reply.error() == QNetworkReply.NoError:
            try:
                isp = reply.readAll().data().decode('utf-8')
                if isp.startswith('AS'): isp = isp.split(" ", 1)[1]
                _match = False
                for _isp in self.isps:
                    if isp == _isp: _match = True
                if not _match:
                    if self.cfg.getboolean('general', 'kickonly'):
                        ts3.requestClientKickFromServer(self.schid, self.requested, "%s is not a valid Internet Service Provider!" % isp);
                    else: ts3.banclient(self.schid, self.requested, 60, "%s is not a valid Internet Service Provider!" % isp)
            except:
                ts3.printMessageToCurrentTab("[[color=orange]WARNING[/color]] [color=red]ISPValidator could not resolve the ISP for '%s' (Reason: %s) Falling back to %s" % (self.clientURL(self.schid, self.requested),format_exc(),self.cfg['api']['fallback'].replace("{ip}",ip)))
                if self.cfg.getboolean("general", "debug"): ts3.printMessageToCurrentTab(self.cfg['api']['fallback'].replace("{ip}",ip))
                #self.nwm.get(QNetworkRequest(QUrl(self.cfg['api']['fallback'].replace("{ip}",ip))));return
        else:
            ts3.printMessageToCurrentTab("[[color=orange]WARNING[/color]] [color=red]ISPValidator could not resolve the ISP for '%s' (Reason: %s) Falling back to %s" % (self.clientURL(self.schid, self.requested),reply.errorString(),self.cfg['api']['fallback'].replace("{ip}",ip)))
            if self.cfg.getboolean("general", "debug"): ts3.printMessageToCurrentTab(self.cfg['api']['fallback'].replace("{ip}",ip))
            #self.nwm.get(QNetworkRequest(QUrl(self.cfg['api']['fallback'].replace("{ip}",ip))));return
        self.requested = 0
        reply.deleteLater()
    def clientURL(self, schid, clid, uid=None, nickname=None):
        if not nickname:
            (error, uid) = ts3.getClientVariableAsString(schid, clid, ts3defines.ClientProperties.CLIENT_UNIQUE_IDENTIFIER)
            (error, nickname) = ts3.getClientDisplayName(schid, clid)
        encodednick = urlencode(nickname)
        return "[url=client://%s/%s~%s]%s[/url]" % (clid, uid, encodednick, nickname)

class SettingsDialog(QDialog):
    def __init__(self,this, parent=None):
        try:
            self.this = this
            super(QDialog, self).__init__(parent)
            setupUi(self, path.join(ts3.getPluginPath(), "pyTSon", "scripts", "ISPValidator", "settings.ui"))
            self.setWindowTitle("%s Settings" % this.name )
            self.chk_debug.setChecked(this.cfg.getboolean("general", "debug"))
            if this.cfg.getboolean("general", "whitelist"): self.chk_whitelist.setChecked(True)
            else: self.chk_blacklist.setChecked(True)
            if this.cfg.getboolean("general", "kickonly"): self.chk_kick.setChecked(True);self.bantime.setEnabled(False)
            else: self.chk_ban.setChecked(True)
            self.bantime.setValue(int(this.cfg["general"]["bantime"]))
            self.api_main.setText(this.cfg["api"]["main"])
            self.api_fallback.setText(this.cfg["api"]["fallback"])
            self.chk_failover.setChecked(this.cfg.getboolean("general", "failover"))
            for event, value in this.cfg["events"].items():
                _item = QListWidgetItem(self.lst_events)
                _item.setToolTip(value)
                _item.setText(event)
                if value == "True": _item.setCheckState(Qt.Checked)
        except:
            ts3.logMessage(format_exc(), ts3defines.LogLevel.LogLevel_ERROR, "PyTSon", 0)

    def on_btn_apply_clicked(self):
        try:
            self.this.cfg.set('general', 'debug', str(self.chk_debug.isChecked()))
            if self.chk_whitelist.isChecked(): self.this.cfg.set('general', 'whitelist', 'True')
            else: self.this.cfg.set('general', 'whitelist', 'False')
            if self.chk_kick.isChecked(): self.this.cfg.set('general', 'kickonly', 'True')
            else: self.this.cfg.set('general', 'kickonly', 'False')
            self.this.cfg.set('general', 'bantime', str(self.bantime.value))
            self.this.cfg.set('api', 'main', self.api_main.text)
            self.this.cfg.set('api', 'fallback', self.api_fallback.text)
            self.this.cfg.set('general', 'failover', str(self.chk_failover.isChecked()))
            # for index in xrange(self.lst_events.count()):
            #     item = self.lst_events.item(index)
            #     for event in self.this.cfg["events"]
            #         if item.text() == event
            #             if item.isChecked():
            with open(self.this.ini, 'w') as configfile:
                self.this.cfg.write(configfile)
            self.close()
        except:
            ts3.logMessage(format_exc(), ts3defines.LogLevel.LogLevel_ERROR, "PyTSon", 0)
    def on_btn_cancel_clicked(self):
        self.close()
