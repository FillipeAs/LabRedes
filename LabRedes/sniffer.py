
import socket, sys
import struct

ETH_P_ALL = 0x0003

def bytes_to_mac(bytesmac):
    return ":".join("{:02x}".format(x) for x in bytesmac)


"""Inicializa Socket"""
try:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(ETH_P_ALL))
except OSError as msg:
    print('Error'+str(msg))
    sys.exit(1)

print('Socket created!')

s.bind(('enp4s0',0))


"""Inicia monitoramento dos pacotes"""
while True:

    (packet,addr) = s.recvfrom(65536)

    eth_length = 14
    eth_header = packet[:14]

    eth = struct.unpack("!6s6sH",eth_header)

    print("MAC Dst: "+bytes_to_mac(eth[0]))
    print("MAC Src: "+bytes_to_mac(eth[1]))
    print("Type: "+hex(eth[2]))

    if eth[2] == 0x0800 :
        print("IP Packet")
        ip_header = packet[eth_length:20+eth_length]
        #print("ip_header: ", ip_header)
        iph = struct.unpack("!BBHHHBBH4s4s", ip_header)
        #print("iph: ", iph)
        version_ihl = iph[0]
       # print("version_ihl: ", version_ihl)
        version = version_ihl >> 4
     #   print("version: ", version)
        ihl = version_ihl & 0xF
       # print("ihl: ", ihl)
        iph_length = ihl*4
      #  print("iph_length: ", iph_length)
        ttl = iph[5]
      #  print("ttl: ", ttl)
        protocol = iph[6]
      #  print("protocol: ", protocol)
        s_addr = socket.inet_ntoa(iph[8])
        d_addr = socket.inet_ntoa(iph[9])
        print("IP Src: "+s_addr)
        print("IP Dst: "+d_addr)
        if protocol == 1:
            print("ICMP Packet")
            icmp_header = packet[iph_length+eth_length:]
            icmph = struct.unpack("!BBHHH%ds" % (len(icmp_header)-8), icmp_header)
            icmp_type = icmph[0]
            icmp_code = icmph[1]
            icmp_id = icmph[2]
            icmp_seq = icmph[3]
            icmp_payload = icmph[4]
            print("Type: ", icmp_type)
            print("Code: ", icmp_code)
            if icmp_type == 8 and icmp_code == 0:
                print("ECHO REQUEST")
            elif icmp_type == 0 and icmp_code == 0:
                print("ECHO REPLY")
    print("="*20)