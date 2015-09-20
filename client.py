#Couple cool and very useful imports.

import sys
import socket
import struct
import threading
import time
import math

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

wc = WorldClass()

class RecvVision(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

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
            pass
          debugP ("************")

def computeDistance(x1, y1, x2, y2):
    xdis = x1 - x2
    ydis = y1 - y2
    distance = math.sqrt(xdis * xdis + ydis * ydis)

    return distance

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

#Inverts the rotation and doubles an angle.
def ida(angle):
    return (math.pi * 2 - angle) * 2

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

        packet = grSim_Packet()
        packet.commands.isteamyellow = True
        packet.commands.timestamp = 0.0
        command = packet.commands.robot_commands.add()
        command.id = 0

        command.wheelsspeed = False
        command.wheel1 = 0
        command.wheel2 = 0
        command.wheel3 = 0
        command.wheel4 = 0
        command.veltangent = 0 #positive -> Go forward
        command.velnormal = 0 #positive -> Go left side
        command.velangular = 0 #Rotate by angle

        command.kickspeedz = 0
        command.spinner = False

        while playAll and len(wc.teams) == 0:
            pass

        while playAll:
            goalX = -3100
            goalY = 0

            if not shoot:
                command.kickspeedx = 0
                bX = wc.ball.x
                bY = wc.ball.y
            else:
                command.kickspeedx = 10
                bX = goalX
                bY = goalY
                shoot = False

            pX = wc.teams[0][0].x
            pY = wc.teams[0][0].y

            angle = math.atan2((bY - pY), (bX - pX))
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
                ballDist = computeDistance(bX, bY, pX, pY) - 100
                feather = 700
                featherMin = 100

                fromAngle = angle
                goalAngle = math.atan2((goalY - pY), (goalX - pX))
                diff = 0
                if (angle - goalAngle) % (math.pi * 2) < (goalAngle - angle) % (math.pi * 2):
                    diff = -((angle - goalAngle) % (math.pi * 2))
                else:
                    diff = ((goalAngle - angle) % (math.pi * 2))

                print ("Dist: {}".format(ballDist))
                if ballDist <= featherMin:
                    print ("\tFinal")
                    aimAngle = angle + ida(goalAngle)
                    angle = goalAngle
                elif ballDist <= feather:
                    #TODO: My sure to rotate towards the cloest angle.
                    print ("\tMid")
                    #This is a weighted average.
                    #featherAngle = ((goalAngle * (feather - ballDist + featherMin) + fromAngle * (ballDist + featherMin)) / (feather + featherMin * 2)) % (math.pi * 2)
                    featherAngle = (fromAngle + (diff * ((feather - ballDist - featherMin) / (feather - featherMin))))
                    aimAngle = angle + ida(featherAngle)
                    angle = featherAngle
                else:
                    print ("\tFar")
                    aimAngle = - wc.teams[0][0].orientation
                    angle = angle
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
                command.velnormal = 1 / ratioY
                command.veltangent = 1 / ratioX
            else:
                command.velnormal = -1 / ratioY
                command.veltangent = -1 / ratioX

            #angle = 0

            angleDiff = ((math.pi + (angle - wc.teams[0][0].orientation)) % (math.pi * 2)) - math.pi

            command.velangular = angleDiff * 10

            print ("Mode: {}".format(fakeOri))
            print ("Angle: {}".format(angle))
            print ("Diff: {}".format(angleDiff))
            print ("RatioX: {}".format(ratioX))
            print ("RatioY: {}".format(ratioY))

            print ("Ball at:")
            print ("\tx: {}".format(wc.ball.x))
            print ("\ty: {}".format(wc.ball.y))
            print ("Robot 0 of {}:".format(len(wc.teams[0])))
            print ("\tx: {}".format(wc.teams[0][0].x))
            print ("\ty: {}".format(wc.teams[0][0].y))
            print ("\tOri: {}".format(wc.teams[0][0].orientation))

            print ("************")

            udpsocket.sendto(packet.SerializeToString(), (SEND_ADDR, SEND_PORT))

            time.sleep(0.01)

            pass

thread1 = RecvVision("recv")
thread2 = AposAI("send")
thread1.start()
thread2.start()

txtInput = ""
while txtInput is not "q":
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

print ("I had a good life. This is it though.")