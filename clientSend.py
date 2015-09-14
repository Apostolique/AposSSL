import sys
import struct
import socket
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtNetwork import *

from grSim_Packet_pb2 import grSim_Packet
from grSim_Commands_pb2 import grSim_Commands, grSim_Robot_Command

#This can act as a template for later.

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_addr = ""
_port = 0


def disconnectUdp():
    global sending
    global udpsocket
    udpsocket.close()
    sending = False
    btnSend.setText("Send")
    btnSend.setDisabled(True)

def sendBtnClicked():
    global sending
    sending = not sending
    if not sending:
        timer.stop()
        btnSend.setText("Send")
    else:
        timer.start()
        btnSend.setText("Pause")

def resetBtnClicked():
    global reseting
    reseting = True
    edtVx.setText("0")
    edtVy.setText("0")
    edtW.setText("0")
    edtV1.setText("0")
    edtV2.setText("0")
    edtV3.setText("0")
    edtV4.setText("0")
    edtChip.setText("0")
    edtKick.setText("0")
    chkVel.setChecked(True)
    chkSpin.setChecked(False)

def reconnectUdp():
    global _addr
    global _port
    _addr = edtIp.text()
    _port = int(edtPort.text())
    #_port = edtPort.text().toUShort()
    btnSend.setDisabled(False)

def sendPacket():
    global udpsocket
    global reseting
    if reseting:
        sendBtnClicked()
        reseting = False
    packet = grSim_Packet()
    yellow = False
    if (cmbTeam.currentText()=="Yellow"):
        yellow = True
    packet.commands.isteamyellow = yellow
    packet.commands.timestamp = 0.0
    #command = grSim_Robot_Command()
    #print ("Special")
    #print(dir(packet.commands.robot_commands))
    #print ("Not Special")
    command = packet.commands.robot_commands.add()
    command.id = int(edtId.text()) if edtId.text() else 0

    command.wheelsspeed = (not chkVel.isChecked())
    command.wheel1 = float(edtV1.text()) if edtV1.text() else 0
    command.wheel2 = float(edtV2.text()) if edtV2.text() else 0
    command.wheel3 = float(edtV3.text()) if edtV3.text() else 0
    command.wheel4 = float(edtV4.text()) if edtV4.text() else 0
    command.veltangent = float(edtVx.text()) if edtVx.text() else 0
    command.velnormal = float(edtVy.text()) if edtVy.text() else 0
    command.velangular = float(edtW.text()) if edtW.text() else 0

    command.kickspeedx = float(edtKick.text()) if edtKick.text() else 0
    command.kickspeedz = float(edtChip.text()) if edtChip.text() else 0
    command.spinner = (chkSpin.isChecked())

    #dgram = QByteArray()
    #dgram.resize(packet.ByteSize())

    print(dir(packet))

    #packet.ParseFromString(dgram.data())
    #udpsocket.sendto(dgram, (_addr, _port));
    udpsocket.sendto(packet.SerializeToString(), (_addr, _port))

a = QApplication(sys.argv)

w = QMainWindow()

widget = QWidget(w)
layout = QGridLayout(widget)
widget.setLayout(layout)

w.setCentralWidget(widget)

edtIp = QLineEdit("127.0.0.1", w);
edtPort = QLineEdit("20011", w);
edtId = QLineEdit("0", w);
edtVx = QLineEdit("0", w);
edtVy = QLineEdit("0", w);
edtW  = QLineEdit("0", w);
edtV1 = QLineEdit("0", w);
edtV2 = QLineEdit("0", w);
edtV3 = QLineEdit("0", w);
edtV4 = QLineEdit("0", w);
edtChip = QLineEdit("0", w);
edtKick = QLineEdit("0", w);

w.setWindowTitle("grSim Python Client - v 1.0");

lblIp = QLabel("Simulator Address", w);
lblPort = QLabel("Simulator Port", w);
lblId = QLabel("Id", w);
lblVx = QLabel("Velocity X (m/s)", w);
lblVy = QLabel("Velocity Y (m/s)", w);
lblW  = QLabel("Velocity W (rad/s)", w);
lblV1 = QLabel("Wheel1 (rad/s)", w);
lblV2 = QLabel("Wheel2 (rad/s)", w);
lblV3 = QLabel("Wheel3 (rad/s)", w);
lblV4 = QLabel("Wheel4 (rad/s)", w);
cmbTeam = QComboBox(w);
cmbTeam.addItem("Yellow");
cmbTeam.addItem("Blue");
lblChip = QLabel("Chip (m/s)", w);
lblKick = QLabel("Kick (m/s)", w);
txtInfo = QTextEdit(w);
chkVel = QCheckBox("Send Velocity? (or wheels)", w);
chkSpin = QCheckBox("Spin", w);
btnSend = QPushButton("Send", w);
btnReset = QPushButton("Reset", w);
btnConnect = QPushButton("Connect", w);
txtInfo.setReadOnly(True);
txtInfo.setHtml("This program is part of <b>grSim RoboCup SSL Simulator</b> package.<br />For more information please refer to <a href=\"http://eew.aut.ac.ir/~parsian/grsim/\">http://eew.aut.ac.ir/~parsian/grsim</a><br /><font color=\"gray\">This program is free software under the terms of GNU General Public License Version 3.</font>");
txtInfo.setFixedHeight(70);
layout.addWidget(lblIp, 1, 1, 1, 1);layout.addWidget(edtIp, 1, 2, 1, 1);
layout.addWidget(lblPort, 1, 3, 1, 1);layout.addWidget(edtPort, 1, 4, 1, 1);
layout.addWidget(lblId, 2, 1, 1, 1);layout.addWidget(edtId, 2, 2, 1, 1);layout.addWidget(cmbTeam, 2, 3, 1, 2);
layout.addWidget(lblVx, 3, 1, 1, 1);layout.addWidget(edtVx, 3, 2, 1, 1);
layout.addWidget(lblVy, 4, 1, 1, 1);layout.addWidget(edtVy, 4, 2, 1, 1);
layout.addWidget(lblW, 5, 1, 1, 1);layout.addWidget(edtW, 5, 2, 1, 1);
layout.addWidget(chkVel, 6, 1, 1, 1);layout.addWidget(edtKick, 6, 2, 1, 1);
layout.addWidget(lblV1, 3, 3, 1, 1);layout.addWidget(edtV1, 3, 4, 1, 1);
layout.addWidget(lblV2, 4, 3, 1, 1);layout.addWidget(edtV2, 4, 4, 1, 1);
layout.addWidget(lblV3, 5, 3, 1, 1);layout.addWidget(edtV3, 5, 4, 1, 1);
layout.addWidget(lblV4, 6, 3, 1, 1);layout.addWidget(edtV4, 6, 4, 1, 1);
layout.addWidget(lblChip, 7, 1, 1, 1);layout.addWidget(edtChip, 7, 2, 1, 1);
layout.addWidget(lblKick, 7, 3, 1, 1);layout.addWidget(edtKick, 7, 4, 1, 1);
layout.addWidget(chkSpin, 8, 1, 1, 4);
layout.addWidget(btnConnect, 9, 1, 1, 2);layout.addWidget(btnSend, 9, 3, 1, 1);layout.addWidget(btnReset, 9, 4, 1, 1);
layout.addWidget(txtInfo, 10, 1, 1, 4);
layout.addWidget(edtIp, 1, 2, 1, 1)

timer = QTimer(w)
timer.setInterval(20)
w.connect(edtIp, SIGNAL("textChanged()"), disconnectUdp)
w.connect(edtPort, SIGNAL("textChanged()"), disconnectUdp)
w.connect(timer, SIGNAL("timeout()"), sendPacket)
w.connect(btnConnect, SIGNAL("clicked()"), reconnectUdp)
w.connect(btnSend, SIGNAL("clicked()"), sendBtnClicked)
w.connect(btnReset, SIGNAL("clicked()"), resetBtnClicked)
btnSend.setDisabled(True)
chkVel.setChecked(True)
sending = False
reseting = False

w.show()

sys.exit(a.exec_())
