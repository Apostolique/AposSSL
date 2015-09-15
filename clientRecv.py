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
    print (wp.detection)
    pass
  if wp.geometry.IsInitialized():
    print (wp.geometry)
    pass
  print ("************")
