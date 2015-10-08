#Couple cool and very useful imports.

import sys, random
import socket
import struct
import threading
import time
import math
from PyQt4 import QtGui, QtCore

import proto.messages_robocup_ssl_wrapper_pb2 as wrapper
from proto.grSim_Packet_pb2 import grSim_Packet
from proto.grSim_Commands_pb2 import grSim_Commands, grSim_Robot_Command

#TODO: Using RecvVision, save the data to be used.
#      Use the data in computeAI.

MCAST_GRP = '224.5.23.2'
MCAST_PORT = 10020

SEND_ADDR = '127.0.0.1'
SEND_PORT = 20011

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', MCAST_PORT))  # use MCAST_GRP instead of '' to listen only
                             # to MCAST_GRP, not all groups on MCAST_PORT
mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

shoot = False
fakeOri = 0
playAll = True

"""
fakeOri is a state variable. It tells the bot where to
look and where to go.
0: Look at the ball, go towards the ball.
1: Look towards angle (0) and try to position to reach
   the ball from that angle.
2: Look towards angle (math.pi + math.pi / 2) and try
   to reach the ball from that angle.
3: Look towards angle (math.pi) and try to reach the
   ball from that angle.
4: Look towards angle (math.pi / 2) and try to reach
   the ball from that angle.
5: Look at the ball and rotate around the ball clockwise.
6: Look at the ball and rotate around the ball anti-
   clockwise.
7: Look at the ball and go towards it following a curve
   clockwise.
8: Look at the ball and go towards it following a curve
   anti-clockwise.
9: Look at one of the goals and go towars the ball.
10: Press R for 10. Look at the ball. Go backwards.
"""

def debugP(text):
    #print (text)
    pass #NOPE.JPG

class WorldClass:
    def __init__(self):
        self.ball = None
        self.teams = []
        self.geo = None

wc = WorldClass()

class RecvVision(QtCore.QThread):
    updated = QtCore.pyqtSignal()

    name = "recv"

    """def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name"""

    def run(self):
        print ("Starting " + self.name)
        self.recvData()
        print ("Done with " + self.name)

    def recvData(self):
        global wc

        wp = wrapper.SSL_WrapperPacket()

        while playAll:
          wp.ParseFromString(sock.recv(65536))
          if wp.detection.IsInitialized():
            debugP ("Frame number: {}".format(type(wp.detection.frame_number)))
            debugP ("Time Capture: {}".format(wp.detection.t_capture))
            debugP ("Time Sent: {}".format(wp.detection.t_sent))
            debugP ("Camera ID: {}".format(wp.detection.camera_id))

            if len(wc.teams) == 0:
                wc.teams.append(wp.detection.robots_yellow)
                wc.teams.append(wp.detection.robots_blue)
            else:
                wc.teams[0] = (wp.detection.robots_yellow)
                wc.teams[1] = (wp.detection.robots_blue)

            for i in wp.detection.balls:
              #Assuming that there is only one ball.
              #The last one will overwrite the other ones.
              wc.ball = i
              debugP ("Ball")
              debugP ("\tConfidence: {}".format(i.confidence))
              debugP ("\tx: {}".format(i.x))
              debugP ("\ty: {}".format(i.y))
              debugP ("\tz: {}".format(i.z))
            for i in wp.detection.robots_yellow:
              debugP ("Robot Yellow {}".format(i.robot_id))
              debugP ("\tConfidence: {}".format(i.confidence))
              debugP ("\tx: {}".format(i.x))
              debugP ("\ty: {}".format(i.y))
              debugP ("\tOrientation: {}".format(i.orientation))
            for i in wp.detection.robots_blue:
              debugP ("Robot Blue {}".format(i.robot_id))
              debugP ("\tConfidence: {}".format(i.confidence))
              debugP ("\tx: {}".format(i.x))
              debugP ("\ty: {}".format(i.y))
              debugP ("\tOrientation: {}".format(i.orientation))
            #debugP (wp.detection)
            pass
          if wp.geometry.IsInitialized():
            debugP (wp.geometry)
            wc.geo = wp.geometry
            pass
          debugP ("************")
          self.updated.emit()

def computeDistance(x1, y1, x2, y2):
    xdis = x1 - x2
    ydis = y1 - y2
    distance = math.sqrt(xdis * xdis + ydis * ydis)

    return distance

def slopeFromAngle(angle):
    if angle == math.pi + math.pi / 2:
        angle += 0.01
    elif angle == math.pi / 2:
        angle -= 0.01

    return math.tan(angle - math.pi)

def pointsOnLine(slope, x, y, distance):
    b = y - slope * x
    r = math.sqrt(1 + slope * slope)

    newX1 = (x + (distance / r))
    newY1 = (y + ((distance * slope) / r))

    newX2 = (x + ((-distance) / r))
    newY2 = (y + (((-distance) * slope) / r))

    return ((newX1, newY1), (newX2, newY2))

def followAngle(angle, x, y, distance):
    slope = slopeFromAngle(angle)
    coord1, coord2 = pointsOnLine(slope, x, y, distance)

    side = (angle - math.pi / 2) % (math.pi * 2)
    if (side < math.pi):
        return coord2
    else:
        return coord1

def rotatePoint(x1, y1, x2, y2, angle):
    s = math.sin(angle)
    c = math.cos(angle)

    x1 -= x2
    y1 -= y2

    newX = x1 * c - y1 * s
    newY = x1 * s + y1 * c

    x1 = newX + x2
    y1 = newY + y2

    return (x1, y1)

#x1, y1: location of current destination
#x2, y2: direction to be looking at when at destination
#x3, y3: current position
def fetchAndRotate(x1, y1, x2, y2, x3, y3):
    destDist = computeDistance(x1, y1, x3, y3) - 100
    feather = 200
    angle = 0

    goalAngle = math.atan2((y2 - y3), (x2 - x3))
    x4, y4 = followAngle(goalAngle, x1, y1, - feather)

    destX = x1
    destY = y1

    fromAngle = math.atan2((y4 - y3), (x4 - x3))
    finalAngle = math.atan2((y1 - y3), (x1 - x3))

    if (finalAngle - goalAngle) % (math.pi * 2) < (goalAngle - finalAngle) % (math.pi * 2):
        angleT = (finalAngle - goalAngle) % (math.pi * 2)
        diff = - wc.teams[0][0].orientation + math.pi / 2
        bounded = 0.5
    else:
        angleT = (goalAngle - finalAngle) % (math.pi * 2)
        diff = - wc.teams[0][0].orientation - math.pi / 2
        bounded = -0.5

    debugP ("Dest: {}".format(((destDist % 10) - 5) / 10))
    if angleT <= math.pi / 5:# and destDist <= feather:
        debugP ("\tFinal")
        aimAngle = finalAngle + ida(goalAngle)
        angle = goalAngle

        destX = x1
        destY = y1
    elif destDist <= feather:
        #TODO: Make sure to rotate towards the cloest angle.
        debugP ("\tMid")
        aimAngle = diff
        angle = finalAngle
        #aimAngle = diff
        #angle = fromAngle
        
        destX = x1
        destY = y1
    else:
        debugP ("\tFar {}".format(bounded))
        aimAngle = - wc.teams[0][0].orientation + bounded
        angle = finalAngle# + math.sin(destDist)

        destX = x4
        destY = y4
    return (destX, destY, angle, aimAngle)

def resetCommand(command, i_id):
    command.id = i_id

    command.wheelsspeed = False
    command.wheel1 = 0
    command.wheel2 = 0
    command.wheel3 = 0
    command.wheel4 = 0
    command.veltangent = 0 #positive -> Go forward
    command.velnormal = 0 #positive -> Go left side
    command.velangular = 0 #Rotate by angle

    command.kickspeedx = 0
    command.kickspeedz = 0
    command.spinner = False

#Inverts the rotation and doubles an angle.
def ida(angle):
    return (math.pi * 2 - angle) * 2

#angle: The angle to face towards to.
#currentOri: The current orientation.
def getAngleDiff(angle1, angle2):
    return ((math.pi + (angle1 - angle2)) % (math.pi * 2)) - math.pi

class AposAI(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        print ("Starting " + self.name)
        self.computeAI()
        print ("Done with " + self.name)

    def computeAI(self):
        global udpsocket
        global shoot

        commandList = []

        packet = grSim_Packet()
        packet.commands.isteamyellow = True
        packet.commands.timestamp = 0.0
        commandList.append(packet.commands.robot_commands.add())
        commandList.append(packet.commands.robot_commands.add())
        resetCommand(commandList[0], 0)
        resetCommand(commandList[1], 1)

        while playAll and len(wc.teams) == 0:
            pass

        while playAll:
            #goalX = -3100
            #goalY = 0
            goalX = wc.teams[0][1].x
            goalY = wc.teams[0][1].y

            if not shoot:
                commandList[0].kickspeedx = 0
                bX = wc.ball.x
                bY = wc.ball.y
            else:
                commandList[0].kickspeedx = 5
                bX = goalX
                bY = goalY
                shoot = False

            pX = wc.teams[0][0].x
            pY = wc.teams[0][0].y

            angle = math.atan2((bY - pY), (bX - pX))
            angle2 = math.atan2((bY - wc.teams[0][1].y), (bX - wc.teams[0][1].x))
            if fakeOri == 0:
                aimAngle = - wc.teams[0][0].orientation
                angle = angle
            elif fakeOri == 1:
                aimAngle = angle + ida(0)
                angle = 0
                #aimAngle = angle + math.pi / 2
                #angle = math.pi + math.pi / 2 + math.pi / 4
            elif fakeOri == 2:
                aimAngle = angle + ida(math.pi + math.pi / 2)
                angle = math.pi + math.pi / 2
            elif fakeOri == 3:
                aimAngle = angle + ida(math.pi)
                angle = math.pi
            elif fakeOri == 4:
                aimAngle = angle + ida(math.pi / 2)
                angle = math.pi / 2
            elif fakeOri == 5:
                aimAngle = - wc.teams[0][0].orientation + math.pi / 2
                angle = angle
            elif fakeOri == 6:
                aimAngle = - wc.teams[0][0].orientation - math.pi / 2
                angle = angle
            elif fakeOri == 7:
                #You can adjust the factor. Lower means
                #that it will go towards the destination
                #using a smaller arc
                aimAngle = - wc.teams[0][0].orientation + 0.5
                angle = angle
            elif fakeOri == 8:    
                #You can adjust the factor. Lower means
                #that it will go towards the destination
                #using a smaller arc
                aimAngle = - wc.teams[0][0].orientation - 0.5
                angle = angle
            elif fakeOri == 9:
                bX, bY, angle, aimAngle = fetchAndRotate(bX, bY, goalX, goalY, pX, pY)
            elif fakeOri == 10:
                aimAngle = - wc.teams[0][0].orientation
                angle = angle

            bX, bY = rotatePoint(bX, bY, pX, pY, aimAngle)

            #angle = The angle to look towards
            #pX, pY = rotatePoint(pX, pY, bX, bY, -angle)

            tempD = computeDistance(bX, bY, pX, pY)

            if (bX == pX):
                bX += 1
            if (bY == pY):
                bY += 1

            ratioX = tempD / (bX - pX)
            ratioY = tempD / (bY - pY)

            #offsetX = bX - (bX - tempD)
            #offsetX = bY - (bY - tempD)

            if fakeOri != 10:
                commandList[0].velnormal = 1 / ratioY
                commandList[0].veltangent = 1 / ratioX
            else:
                commandList[0].velnormal = -1 / ratioY
                commandList[0].veltangent = -1 / ratioX

            #angle = 0

            angleDiff = getAngleDiff(angle, wc.teams[0][0].orientation)


            angleDiff2 = getAngleDiff(angle2, wc.teams[0][1].orientation)

            commandList[0].velangular = angleDiff * 10
            commandList[1].velangular = angleDiff2 * 10

            debugP ("Mode: {}".format(fakeOri))
            debugP ("Angle: {}".format(angle))
            debugP ("Diff: {}".format(angleDiff))
            debugP ("RatioX: {}".format(ratioX))
            debugP ("RatioY: {}".format(ratioY))

            debugP ("Ball at:")
            debugP ("\tx: {}".format(wc.ball.x))
            debugP ("\ty: {}".format(wc.ball.y))
            debugP ("Robot 0 of {}:".format(len(wc.teams[0])))
            debugP ("\tx: {}".format(wc.teams[0][0].x))
            debugP ("\ty: {}".format(wc.teams[0][0].y))
            debugP ("\tOri: {}".format(wc.teams[0][0].orientation))

            debugP ("************")

            udpsocket.sendto(packet.SerializeToString(), (SEND_ADDR, SEND_PORT))

            time.sleep(0.02)

            pass

class InputCommands(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        print ("Starting " + self.name)
        self.getCommands()
        print ("Done with " + self.name)

    def getCommands(self):
        global playAll
        global fakeOri
        global shoot
        txtInput = ""
        while txtInput is not "q" and playAll:
            txtInput = input()
            if txtInput is "s":
                shoot = True
            elif txtInput is "0":
                fakeOri = 0
            elif txtInput is "1":
                fakeOri = 1
            elif txtInput is "2":
                fakeOri = 2
            elif txtInput is "3":
                fakeOri = 3
            elif txtInput is "4":
                fakeOri = 4
            elif txtInput is "5":
                fakeOri = 5
            elif txtInput is "6":
                fakeOri = 6
            elif txtInput is "7":
                fakeOri = 7
            elif txtInput is "8":
                fakeOri = 8
            elif txtInput is "9":
                fakeOri = 9
            elif txtInput is "r":
                fakeOri = 10

        playAll = False

class FieldDisplay(QtGui.QWidget):
    #TODO: Make the gui be based on the current window size.

    def __init__(self):
        super(FieldDisplay, self).__init__()
        
        self._thread = RecvVision(self)
        self._thread.updated.connect(self.refresh)

        self.ratio = 1.0
        self.fieldOffsetX = 700
        self.fieldOffsetY = 700

        self._thread.start()

        self.initUI()
        
    def initUI(self):      
        self.setGeometry(300, 300, 1220, 820)
        self.ratio = (6000 + self.fieldOffsetY * 2) / 820
        self.setWindowTitle('SSL Visualizer')
        self.show()

    def closeEvent(self, e):
        global playAll
        playAll = False

    def resizeEvent(self, e):
        if (wc.geo is not None):
            print ("Current new size: {}, {}".format(e.size().width(), e.size().height()))
            print ("Field size: {}, {}".format(wc.geo.field.field_width, wc.geo.field.boundary_width))
            ratioX = ((wc.geo.field.field_width + self.fieldOffsetX * 2) / (e.size().width()))
            ratioY = ((wc.geo.field.goal_width + self.fieldOffsetY * 2) / (e.size().height()))
            print ("RatioX: {}".format(ratioX))
            print ("RatioY: {}".format(ratioY))
            self.ratio = max(ratioX, ratioY)
            pass

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)

        self.drawField(qp)
        qp.end()

    def drawField(self, qp):

        pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 3, QtCore.Qt.SolidLine)

        if (wc.geo is not None):
            color = QtGui.QColor(0, 0, 0)
            color.setNamedColor('#d4d4d4')
            qp.setPen(pen)

            width = wc.geo.field.field_width / self.ratio
            height = wc.geo.field.goal_width / self.ratio

            qp.setBrush(QtGui.QColor(0, 155, 0, 150))
            qp.drawRect(0, 0, width + self.fieldOffsetX * 2 / self.ratio, height + self.fieldOffsetY * 2 / self.ratio)
            qp.setBrush(QtGui.QColor(0, 155, 0, 200))
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 0), 3, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            qp.drawRect(self.fieldOffsetX / self.ratio - 250 / self.ratio, self.fieldOffsetY / self.ratio - 250 / self.ratio, width + 500 / self.ratio, height + 500 / self.ratio)
            pen = QtGui.QPen(QtGui.QColor(255, 255, 255), 3, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            qp.drawRect(self.fieldOffsetX / self.ratio, self.fieldOffsetY / self.ratio, width, height)

            pen = QtGui.QPen(QtGui.QColor(255, 255, 255), 3, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            qp.drawLine(self.fieldOffsetX / self.ratio + width / 2, self.fieldOffsetY / self.ratio, self.fieldOffsetX / self.ratio + width / 2, self.fieldOffsetY / self.ratio + height)
            qp.drawLine(self.fieldOffsetX / self.ratio, self.fieldOffsetY / self.ratio + height / 2, self.fieldOffsetX / self.ratio + width, self.fieldOffsetY / self.ratio + height / 2)
            qp.setBrush(QtGui.QColor(255, 255, 255, 0))
            circleSize = 500 / self.ratio
            qp.drawEllipse(self.fieldOffsetX / self.ratio + width / 2 - circleSize, self.fieldOffsetY / self.ratio + height / 2 - circleSize, circleSize * 2, circleSize * 2)
            #qp.drawEllipse(self.fieldOffsetX / self.ratio - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - circleSize * 2 - 250 / self.ratio, circleSize * 4, circleSize * 4)
            #qp.drawEllipse(self.fieldOffsetX / self.ratio - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - circleSize * 2 + 250 / self.ratio, circleSize * 4, circleSize * 4)
            qp.drawArc(self.fieldOffsetX / self.ratio - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - circleSize * 2 - 250 / self.ratio, circleSize * 4, circleSize * 4, 0, 90 * 16)
            qp.drawArc(self.fieldOffsetX / self.ratio - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - circleSize * 2 + 250 / self.ratio, circleSize * 4, circleSize * 4, 0, -90 * 16)

            qp.drawArc(self.fieldOffsetX / self.ratio + width - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - circleSize * 2 - 250 / self.ratio, circleSize * 4, circleSize * 4, 180 * 16, -90 * 16)
            qp.drawArc(self.fieldOffsetX / self.ratio + width - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - circleSize * 2 + 250 / self.ratio, circleSize * 4, circleSize * 4, 180 * 16, 90 * 16)

            qp.drawLine(self.fieldOffsetX / self.ratio + circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - 250 / self.ratio, self.fieldOffsetX / self.ratio + circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 + 250 / self.ratio)
            qp.drawLine(self.fieldOffsetX / self.ratio + width - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 - 250 / self.ratio, self.fieldOffsetX / self.ratio + width - circleSize * 2, self.fieldOffsetY / self.ratio + height / 2 + 250 / self.ratio)

            goalSize = 1000
            pen = QtGui.QPen(QtGui.QColor(255, 0, 0), 3, QtCore.Qt.SolidLine)
            qp.setPen(pen)
            qp.drawLine(self.fieldOffsetX / self.ratio - 250 / self.ratio, self.fieldOffsetY / self.ratio - goalSize / 2 / self.ratio + height / 2, self.fieldOffsetX / self.ratio - 250 / self.ratio, self.fieldOffsetY / self.ratio + goalSize / 2 / self.ratio + height / 2)
            qp.drawLine(self.fieldOffsetX / self.ratio - 250 / self.ratio, self.fieldOffsetY / self.ratio - goalSize / 2 / self.ratio + height / 2, self.fieldOffsetX / self.ratio, self.fieldOffsetY / self.ratio - goalSize / 2 / self.ratio + height / 2)
            qp.drawLine(self.fieldOffsetX / self.ratio - 250 / self.ratio, self.fieldOffsetY / self.ratio + goalSize / 2 / self.ratio + height / 2, self.fieldOffsetX / self.ratio, self.fieldOffsetY / self.ratio + goalSize / 2 / self.ratio + height / 2)

            qp.drawLine(self.fieldOffsetX / self.ratio + 250 / self.ratio + width, self.fieldOffsetY / self.ratio - goalSize / 2 / self.ratio + height / 2, self.fieldOffsetX / self.ratio + 250 / self.ratio + width, self.fieldOffsetY / self.ratio + goalSize / 2 / self.ratio + height / 2)
            qp.drawLine(self.fieldOffsetX / self.ratio + 250 / self.ratio + width, self.fieldOffsetY / self.ratio - goalSize / 2 / self.ratio + height / 2, self.fieldOffsetX / self.ratio + width, self.fieldOffsetY / self.ratio - goalSize / 2 / self.ratio + height / 2)
            qp.drawLine(self.fieldOffsetX / self.ratio + 250 / self.ratio + width, self.fieldOffsetY / self.ratio + goalSize / 2 / self.ratio + height / 2, self.fieldOffsetX / self.ratio + width, self.fieldOffsetY / self.ratio + goalSize / 2 / self.ratio + height / 2)

            pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 3, QtCore.Qt.SolidLine)
            qp.setPen(pen)

            robotSize = 180 / self.ratio
            for i in wc.teams[0]:
                centerX = i.x / self.ratio + (self.fieldOffsetX / self.ratio + width / 2)
                centerY = -i.y / self.ratio + (self.fieldOffsetY / self.ratio + height / 2)
                qp.setBrush(QtGui.QColor(255, 255, 0, 0))
                qp.drawEllipse(centerX - robotSize, centerY - robotSize, robotSize * 2, robotSize * 2)
                qp.setBrush(QtGui.QColor(255, 255, 0, 200))
                qp.drawEllipse(centerX - robotSize / 2, centerY - robotSize / 2, robotSize, robotSize)
                x2, y2 = followAngle(-i.orientation, centerX, centerY, robotSize)
                qp.drawLine(centerX, centerY, x2, y2)

            for i in wc.teams[1]:
                centerX = i.x / self.ratio + (self.fieldOffsetX / self.ratio + width / 2)
                centerY = -i.y / self.ratio + (self.fieldOffsetY / self.ratio + height / 2)
                qp.setBrush(QtGui.QColor(0, 0, 255, 0))
                qp.drawEllipse(centerX - robotSize, centerY - robotSize, robotSize * 2, robotSize * 2)
                qp.setBrush(QtGui.QColor(0, 0, 255, 200))
                qp.drawEllipse(centerX - robotSize / 2, centerY - robotSize / 2, robotSize, robotSize)
                x2, y2 = followAngle(-i.orientation, centerX, centerY, robotSize)
                qp.drawLine(centerX, centerY, x2, y2)

            qp.setBrush(QtGui.QColor(255, 69, 0, 200))
            ballSize = 10
            ballX = wc.ball.x / self.ratio + (self.fieldOffsetX / self.ratio + width / 2) #(wc.ball.x + width) / self.ratio
            ballY = -wc.ball.y / self.ratio + (self.fieldOffsetY / self.ratio + height / 2) #(-wc.ball.y + height) / self.ratio
            #print ("Ball x: {} and y: {}".format(ballX, ballY))
            qp.drawEllipse(ballX - (ballSize / 2), ballY - (ballSize / 2), ballSize, ballSize)


    def drawPoints(self, qp):
        qp.setPen(QtCore.Qt.red)
        size = self.size()
        
        for i in range(1000):
            x = random.randint(1, size.width()-1)
            y = random.randint(1, size.height()-1)
            qp.drawPoint(x, y)

    def refresh(self):
        self.update()

#thread1 = RecvVision("recv")
thread2 = AposAI("send")
thread3 = InputCommands("input")
#thread1.start()
thread2.start()
thread3.start()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = FieldDisplay()
    sys.exit(app.exec_())


print ("I had a good life. This is it though.")