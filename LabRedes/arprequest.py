# ARP Request

import socket, sys
import struct

# Misc functions
mac2bytes = lambda m: bytes.fromhex(m.replace(':',''))

# Create socket
try:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, 0)
except OSError as msg:
    print('Error'+str(msg))
    sys.exit(1)

print('Socket created!')

s.bind(('eth0',0))

############
# ARP Header
htype = 1
ptype = 0x0800
hlen = 6
plen = 4
op = 1 # request
src_mac = mac2bytes('00:00:00:aa:00:00')
src_ip = socket.inet_aton("10.0.0.10")
target_mac = mac2bytes('00:00:00:00:00:00')
target_ip = socket.inet_aton("10.0.0.11")

arp_hdr = struct.pack("!HHBBH6s4s6s4s", htype, ptype, hlen, plen, op, src_mac, src_ip, target_mac, target_ip)

#################
# Ethernet Header
dest_mac = mac2bytes('ff:ff:ff:ff:ff:ff')   # MAC Destino - 6 bytes
source_mac = mac2bytes('00:00:00:aa:00:00') # MAC Origem - 6 bytes
protocol = 0x0806   # Type - 2 bytes

eth_hdr = struct.pack("!6s6sH", dest_mac, source_mac, protocol)

##################

packet = eth_hdr+arp_hdr

s.send(packet)