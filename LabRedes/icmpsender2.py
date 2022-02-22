# Exemplo de envio de ICMP Echo Request usando socket raw
# - utilização de AF_INET
# - preenchimento manual do header IP - setsockopt IP_HDRINCL
# - checksum do IP calculado automaticamente (iniciado com 0)
# - cálculo de checksum do header ICMP

import socket, sys
import struct

# 16-bit one's complement of the one's complement sum of the ICMP message starting with the Type field
# the checksum field should be cleared to zero before generating the checksum
def checksum(msg):
    s = 0
    # add padding if not multiple of 2 (16 bits)
    msg = (msg + b'\x00') if len(msg)%2 else msg
    for i in range(0, len(msg), 2):
        w = msg[i] + (msg[i+1] << 8)
        s = s + w
        s = (s & 0xffff) + (s >> 16)
    s = ~s & 0xffff
    return socket.ntohs(s)

# Create socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp"))
except OSError as msg:
    print('Error'+str(msg))
    sys.exit(1)

print('Socket created!')

###################
# Include IP header
s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
# This option controls whether datagrams may be broadcast from the socket. The value has type int; a nonzero value means “yes”.
#s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

##########################
# ICMP Echo Request Header
type = 8
code = 0
mychecksum = 0
identifier = 12345
seqnumber = 0
payload = b"istoehumteste"

# Pack ICMP header fields
icmp_packet = struct.pack("!BBHHH%ds"%len(payload), type, code, mychecksum, identifier, seqnumber, payload)

# Calculate checksum
mychecksum = checksum(icmp_packet)
# print("Checksum: {:02x}".format(mychecksum))

# Repack with checksum
icmp_packet = struct.pack("!BBHHH%ds"%len(payload), type, code, mychecksum, identifier, seqnumber, payload)

# Header IP
ip_ver = 4
ip_ihl = 5
ip_tos = 0
ip_tot_len = 0 # automaticamente preenchido - AF_INET
ip_id = 54321
ip_frag_off = 0
ip_ttl = 255
ip_proto = socket.IPPROTO_ICMP
ip_check = 0  # automaticamente preenchido - AF_INET
ip_saddr = socket.inet_aton("10.0.0.12")
ip_daddr = socket.inet_aton("10.0.0.14")

ip_ihl_ver = (ip_ver << 4) + ip_ihl

# Pack IP header fields
ip_header = struct.pack("!BBHHHBBH4s4s", ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off, ip_ttl,
    ip_proto, ip_check, ip_saddr, ip_daddr)

########################

# Destination IP address
dest_ip = "10.0.0.14"
dest_addr = socket.gethostbyname(dest_ip)

# Send icmp_packet to address = (host, port)
s.sendto(ip_header+icmp_packet, (dest_addr,0))