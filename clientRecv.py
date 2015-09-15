import socket
import struct

import proto.messages_robocup_ssl_wrapper_pb2 as wrapper

MCAST_GRP = '224.5.23.2'
MCAST_PORT = 10020

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', MCAST_PORT))  # use MCAST_GRP instead of '' to listen only
                             # to MCAST_GRP, not all groups on MCAST_PORT
mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

wp = wrapper.SSL_WrapperPacket()

while True:
  wp.ParseFromString(sock.recv(65536))
  if wp.detection.IsInitialized():
    print ("Frame number:", wp.detection.frame_number)
    print ("Time Capture:", wp.detection.t_capture)
    print ("Time Sent:", wp.detection.t_sent)
    print ("Camera ID:", wp.detection.camera_id)
    for i in wp.detection.balls:
      print ("Ball")
      print ("\tConfidence:", i.confidence)
      print ("\tx:", i.x)
      print ("\ty:", i.y)
      print ("\tz:", i.z)
    for i in wp.detection.robots_yellow:
      print ("Robot Yellow", i.robot_id)
      print ("\tConfidence:", i.confidence)
      print ("\tx:", i.x)
      print ("\ty:", i.y)
      print ("\tOrientation:", i.orientation)
    for i in wp.detection.robots_blue:
      print ("Robot Blue", i.robot_id)
      print ("\tConfidence:", i.confidence)
      print ("\tx:", i.x)
      print ("\ty:", i.y)
      print ("\tOrientation:", i.orientation)
    #print (wp.detection)
    pass
  if wp.geometry.IsInitialized():
    print (wp.geometry)
    pass
  print ("************")
