
import socket, sys
import struct
import time

ETH_P_ALL = 0x0003

def bytes_to_mac(bytesmac):
    return ":".join("{:02x}".format(x) for x in bytesmac)

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


#Função que implementa o contra-ataque ao ping flood
def counterFlood(ipAtaque, hostsVizinhos):
    print("\tINICIANDO CONTRA-ATAQUE DDoS")
    type = 8
    code = 0
    mychecksum = 0
    identifier = 12345
    seqnumber = 0
    payload = b"pingpong"

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
    ip_saddr = socket.inet_aton(ipAtaque)
    ip_ihl_ver = (ip_ver << 4) + ip_ihl

    #LOOP PODE SER DAQUI
    while True:
        for key in hostsVizinhos:
            if not key == ipAtaque:
                ip_daddr = socket.inet_aton(key) #Substituir por cada máquina vizinha 

                # Pack IP header fields
                ip_header = struct.pack("!BBHHHBBH4s4s", ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off, ip_ttl,
                    ip_proto, ip_check, ip_saddr, ip_daddr)

                # Destination IP address
                dest_addr = socket.gethostbyname(key)
                #print("\tRequesting back-up, ", dest_addr)

                # Send icmp_packet to address = (host, port)
                sSend.sendto(ip_header+icmp_packet, (dest_addr,0))

    #ATE AQUI


#MAIN
#Define o valor base para detectar um ping flood
if len(sys.argv) > 1:
    if sys.argv[1].isnumeric():
        floodDelta = int(sys.argv[1])
    else:
        floodDelta = 5
else:
    floodDelta = 5
    #Dicionário de máquinas identificadas, {Ip_Origem: requests_recebidos}
dictHosts = {}

#Inicializa Socket
try:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(ETH_P_ALL))
    sSend = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp"))
    s.bind(('eth0',0))
except OSError as msg:
    print('Error'+str(msg))
    sys.exit(1)

print('Socket created!')

sSend.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

tempoLimite = 1.3

#Começa a contabilizar o tempo
tempoInicial = time.time()
#Inicia o relógio
time.clock() 
tempoPassado = 0

#Inicia monitoramento dos pacotes
while True:


    (packet,addr) = s.recvfrom(65536)

    eth_length = 14
    eth_header = packet[:14]

    eth = struct.unpack("!6s6sH",eth_header)

    #print("MAC Dst: "+bytes_to_mac(eth[0]))
    #print("Type: "+hex(eth[2]))

    #print("eth[2]: ",eth[2])
    if eth[2] == 0x0800 :
        ip_header = packet[eth_length:20+eth_length]
        #print("ip_header: ", ip_header)
        iph = struct.unpack("!BBHHHBBH4s4s", ip_header)
        #print("iph: ", iph)
        version_ihl = iph[0]
        #print("version_ihl: ", version_ihl)
        version = version_ihl >> 4
        #print("version: ", version)
        ihl = version_ihl & 0xF
        #print("ihl: ", ihl)
        iph_length = ihl*4
        #print("iph_length: ", iph_length)
        ttl = iph[5]
        #print("ttl: ", ttl)
        protocol = iph[6]
        #print("protocol: ", protocol)
        s_addr = socket.inet_ntoa(iph[8])
        #print("s_addr: ", s_addr)


        #d_addr = socket.inet_ntoa(iph[9])
        #print("IP Dst: "+d_addr)

        #Se é um pacote ICMP:
        #print("Protocol: ", protocol)
        if protocol == 1:
            icmp_header = packet[iph_length+eth_length:]
            icmph = struct.unpack("!BBHHH%ds" % (len(icmp_header)-8), icmp_header)
            icmp_type = icmph[0]
            icmp_code = icmph[1]
            icmp_id = icmph[2]
            icmp_seq = icmph[3]
            icmp_payload = icmph[4]
            #print("Type: ", icmp_type)
            #print("Code: ", icmp_code)

            #Se é um echo request, contabilizar
            if icmp_type == 8 and icmp_code == 0:
                
                print("="*20)
                print("ECHO REQUEST")
                #print("MAC Src: "+bytes_to_mac(eth[1]))
                print("\tIP Src: "+s_addr)

                #Se o endereço de ip origem é novo, adiciona, se não, atualiza
                if not s_addr in dictHosts:
                    dictHosts[s_addr] = 0
                else:
                    dictHosts[s_addr] += 1

                #Verifica se algum host está dando flood Ping
                for key in dictHosts:
                    if dictHosts[key] > floodDelta:
                        #Se há ataque, inicia contra ataque DDoS
                        print("\tATAQUE DETECTADO vindo de ", key)
                        print("\tChamadas:")
                        print(dictHosts)
                        counterFlood(key, dictHosts)


                #Se o tempo passado é maior que o limite em segundos, reseta os contadores
                tempoPassado = time.time() - tempoInicial
                print("Tempo passado: ", tempoPassado)

                if tempoPassado > tempoLimite:
                    print("\tZera dict")
                    print(dictHosts)
                    tempoPassado = 0
                    tempoInicial = time.time()
                    time.clock() 
                    for key in dictHosts:                        
                        dictHosts[key] = 0

            #elif icmp_type == 0 and icmp_code == 0:
            #    print("ECHO REPLY")