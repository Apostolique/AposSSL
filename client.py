#Couple cool and very useful imports.

import sys
import socket
import struct
import threading

import proto.messages_robocup_ssl_wrapper_pb2 as wrapper
from proto.grSim_Packet_pb2 import grSim_Packet
from proto.grSim_Commands_pb2 import grSim_Commands, grSim_Robot_Command

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtNetwork import *

#TODO: Using RecvVision, save the data to be used.
#      Use the data in computeAI.

MCAST_GRP = '224.5.23.2'
MCAST_PORT = 10020

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', MCAST_PORT))  # use MCAST_GRP instead of '' to listen only
                             # to MCAST_GRP, not all groups on MCAST_PORT
mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

playAll = True

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

            wc.teams.append(wp.detection.robots_yellow)
            wc.teams.append(wp.detection.robots_blue)

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

class AposAI(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):
        print ("Starting " + self.name)
        self.computeAI()
        print ("Done with " + self.name)

    def computeAI(self):
        while playAll:
            if len(wc.teams) > 0:
                print ("Ball at:")
                print ("\tx: {}".format(wc.ball.x))
                print ("\ty: {}".format(wc.ball.y))
                print ("Robot 0 of {}:".format(len(wc.teams[0])))
                print ("\tx: {}".format(wc.teams[0][0].x))
                print ("\ty: {}".format(wc.teams[0][0].y))
                print ("\tOri: {}".format(wc.teams[0][0].orientation))

                print ("************")

                pass

thread1 = RecvVision("recv")
thread2 = AposAI("send")
thread1.start()
thread2.start()

input()
playAll = False

print ("I had a good life. This is it though.")