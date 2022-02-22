import select, socket, sys, queue, time
import struct

ETH_P_ALL = 0x0003



# usage [1st ip ] [last ip] [dns server]
ip_range = range(int.from_bytes(socket.inet_aton(sys.argv[1]),"big") , int.from_bytes(socket.inet_aton(sys.argv[2]),"big"))
dns_ip = int.from_bytes(socket.inet_aton(sys.argv[3]),"big")

ip_used = dict()
used = dict()


my_mac = b"\x00\x00\x00\xaa\x00\x10"

lease_time = 100

def checksum(msg):
    s = 0
    msg = (msg + b'\x00') if len(msg)%2 else msg
    for i in range(0, len(msg), 2):
        w = msg[i] + (msg[i+1] << 8)
        s = s + w
        s = (s & 0xffff) + (s >> 16)
    s = ~s & 0xffff
    return socket.ntohs(s)


#retorna uma resposta se a mensagem for dhcp dhcp  
def udp(udp_header, ip_o,ip_d):
    udph = udp_header[:8]
    udph = struct.unpack("!HHHH", udph)
    s_port = udph[0]
    d_port = udph[1]
    if s_port != 68: return 0,-1,-1 # n e dhcp
    ips, ports, data = dhcp(udp_header[8:], int.from_bytes(socket.inet_aton(ip_o),"big"))
    #Calculo do checksum do UDP
    if(ips[0] == 0): return 0,-1,-1 
    packet = struct.pack("!HHHH",ports[0],ports[1],len(data),0)
    protocol = 17 #udp
    pseudo_header = struct.pack("!4s4sBBH",ips[0],ips[1],0,protocol,len(data))
    checksum_udp = checksum(pseudo_header + packet + data)
    packet = struct.pack("!HHHH",ports[0],ports[1],len(data),checksum_udp)

    return  packet + data, ips[0],ips[1]


#verifica qual tipo da mensagem dhcp, resposndendo se for um discover ou request
def dhcp(dhcp_packet, ip_o):
    type_d = dhcp_packet[240: 243]
    type_d = struct.unpack("!BBB", type_d) # 53, length, type
    if type_d[2] == 1: # se eh discover manda um offer
        return dhcp_offer(dhcp_packet)
    elif type_d[2] == 3: # se eh request manda um ack
        return dhcp_ack(dhcp_packet)
    elif type_d[2] == 7:    
        if ip_o in used:
            del used[ip_o]
    return (0,0), (0,0), dhcp_packet

#cria o pacote offer para responder a mensagem dicover do cliente
def dhcp_offer(dhcp_packet):
    global used, dns_ip, lease_time
    #seleciona um ip para oferecer
    chosen_ip = 0
    for i in ip_range:
        if i  not in used:
            chosen_ip  = i
            break
    ip_offered = int.to_bytes(chosen_ip,4,byteorder="big")
    used[chosen_ip] = 0

    ip_src = int.to_bytes(dns_ip,4,"big")
    ip_dest = socket.inet_aton("255.255.255.255") 
    src_port = 67
    dest_port = 68

    dhcph = dhcp_packet[:240]
    dhcph = struct.unpack("!BBBB4sHH4s4s4s4s16s64s128s4s", dhcph) # vai ate magic cookie 

    #monta o pacote offer
    opcode = 2 # reply
    hw_type = 1 #ethernet
    hw_len = 6
    hops = dhcph[3]
    xid = dhcph[4]
    ip_used[xid] = ip_offered
    sec = 0 
    broad_flag = 0
    ciaddr =  int.to_bytes(0,4,"big")
    yiaddr = ip_offered
    siaddr = ip_src
    giaddr = int.to_bytes(0,4,"big")
    chaddr = dhcph[11] 
    server_name = int.to_bytes(0,64,"big")
    filename = int.to_bytes(0,128,"big")
    magic_cookie = dhcph[-1]
    
    #dhcp message type
    dhcp_msg_type = (53 << 16) | (1 << 8) | 2 #offer
    dhcp_msg_type = int.to_bytes(dhcp_msg_type,3,"big")

    #dhcp submask
    dhcp_submask_op = (1 << 40) | (4 << 32) | 4294967040 # 255.255.255.0 to int
    dhcp_submask_op = int.to_bytes(dhcp_submask_op,6,"big")
    
    #dhcp server ident
    dhcp_server_id = (54 << 40) | (4 << 32) | int.from_bytes(ip_src,"big")
    dhcp_server_id = int.to_bytes(dhcp_server_id,6,"big")
    
    #ip lease time
    dhcp_lease = (51 << 40) | ( 4 << 32) | lease_time # 10min
    dhcp_lease = int.to_bytes(dhcp_lease,6,"big")
    
    #router
    dhcp_router = (3 << 40) | ( 4 << 32) | 167772161 # 10.0.0.1 to int
    dhcp_router = int.to_bytes(dhcp_router,6,"big")
    
    #domain name 
    name = b'teste.com'
    name_len = len(name) + 2
    dhcp_dname = (15 << (8 * (len(name) + 1)) ) | (len(name) << (8 * len(name)) ) | int.from_bytes(name,"big")
    dhcp_dname = int.to_bytes(dhcp_dname,name_len,"big")
    #dns
    dhcp_dns = (6 << 40) | (4 << 32) | dns_ip # 10.0.0.10
    dhcp_dns = int.to_bytes(dhcp_dns,6,"big")
    end = 255
    pad_len = 32 - 6 - name_len
    padding =  int.to_bytes(0,pad_len,"big")     
    
    pacote = struct.pack("!BBBB4sHH4s4s4s4s16s64s128s4s3s6s6s6s6s"+ str(name_len) +"s6sB" + str(pad_len) +'s', 
            opcode,hw_type,hw_len, hops,xid,sec,broad_flag,ciaddr,
            yiaddr,siaddr,giaddr, chaddr,server_name,
            filename,magic_cookie,dhcp_msg_type,
            dhcp_submask_op,dhcp_server_id,dhcp_lease,dhcp_router,dhcp_dname,dhcp_dns, end,padding)

 
    return (ip_src,ip_dest), (src_port,dest_port), pacote

#cria o pacote ack para responder a mensagem request do cliente
def dhcp_ack(dhcp_packet):
    global dns_ip, lease_time
    src_port = 67
    dest_port = 68
    ip_src = int.to_bytes(dns_ip,4,"big")
    ip_dest = socket.inet_aton("255.255.255.255") #broadcast

    dhcph = dhcp_packet[:240]
    dhcph = struct.unpack("!BBBB4sHH4s4s4s4s16s64s128s4s", dhcph) # vai ate magic cookie 

    dhcp_opt = dhcp_packet[249:255]
    ip_requested = struct.unpack("!BB4s", dhcp_opt) 
    xid = dhcph[4]

    if ip_requested[0] == 50 and int.from_bytes(ip_requested[2],"big") not in used:
        if xid in ip_used:
            del used[int.from_bytes(ip_used[xid], "big")]
            del ip_used[xid]
        return (0,0), (0,0), dhcp_packet


    #monta o pacote offer
    opcode = 2 # reply
    hw_type = 1 #ethernet
    hw_len = 6
    hops = dhcph[3]
    
    if xid not in ip_used: return (0,0), (0,0), dhcp_packet
    ip_offered = ip_used[xid]
    sec = 0 
    broad_flag = 0
    ciaddr =  int.to_bytes(0,4,"big")
    yiaddr = ip_offered
    siaddr = ip_src
    giaddr = int.to_bytes(0,4,"big")
    chaddr = dhcph[11] #acho q eh 11
    server_name = int.to_bytes(0,64,"big")
    filename = int.to_bytes(0,128,"big")
    magic_cookie = dhcph[-1]
    


    #dhcp message type
    dhcp_msg_type = (53 << 16) | (1 << 8) | 5 #ack
    dhcp_msg_type = int.to_bytes(dhcp_msg_type,3,"big")

    #dhcp submask
    dhcp_submask_op = (1 << 40) | (4 << 32) | 4294967040 # 255.255.255.0 to int
    dhcp_submask_op = int.to_bytes(dhcp_submask_op,6,"big")
    
    #dhcp server ident
    dhcp_server_id = (54 << 40) | (4 << 32) | int.from_bytes(ip_src,"big")
    dhcp_server_id = int.to_bytes(dhcp_server_id,6,"big")
    
    #ip lease time
    dhcp_lease = (51 << 40) | ( 4 << 32) | lease_time # 10min
    dhcp_lease = int.to_bytes(dhcp_lease,6,"big")
    
    #router
    dhcp_router = (3 << 40) | ( 4 << 32) | 167772161 # 10.0.0.1 to int
    dhcp_router = int.to_bytes(dhcp_router,6,"big")

    #domain name 
    name = b'teste.com'
    name_len = len(name) + 2
    dhcp_dname = (15 << (8 * (len(name) + 1)) ) | (len(name) << (8 * len(name)) ) | int.from_bytes(name,"big")
    dhcp_dname = int.to_bytes(dhcp_dname,name_len,"big")
    #dns
    dhcp_dns = (6 << 40) | (4 << 32) | dns_ip # 10.0.0.10
    dhcp_dns = int.to_bytes(dhcp_dns,6,"big")
    end = 255
    pad_len = 32 - 6 - name_len
    padding =  int.to_bytes(0,pad_len,"big")     



    #zera lease time
    used[int.from_bytes(ip_used[xid],"big")] = 0

    pacote = struct.pack("!BBBB4sHH4s4s4s4s16s64s128s4s3s6s6s6s6s"+ str(name_len) +"s6sB" + str(pad_len) +'s', 
            opcode,hw_type,hw_len, hops,xid,sec,broad_flag,ciaddr,
            yiaddr,siaddr,giaddr, chaddr,server_name,
            filename,magic_cookie,dhcp_msg_type,
            dhcp_submask_op,dhcp_server_id,dhcp_lease,dhcp_router,dhcp_dname,dhcp_dns, end,padding)

 
 
    return (ip_src,ip_dest), (src_port,dest_port), pacote



#verifica o cabeçãlho ip da mensagem, enviando uma resposta se uma mensagem dhcp foi recebida
def ipv4(ip_header):
    iph = ip_header[:20]
    iph = struct.unpack("!BBHHHBBH4s4s", iph)
    version_ihl = iph[0]
    ihl = version_ihl & 0xF
    iph_length = ihl*4
    tos = iph[1]
    total_len = iph[2]
    ip_id = iph[3]
    offset = iph[4]
    ttl = iph[5]
    protocol = iph[6]
    ip_checksum = 0 #montar o pacote e dpois calcular
    next_header = ip_header[iph_length:]
    s_addr = iph[8]
    d_addr = iph[9]

    if protocol == 17:  #udp
        next_header,s_addr, d_addr = udp(next_header, socket.inet_ntoa(s_addr),socket.inet_ntoa(d_addr))

        if s_addr == -1 and d_addr == -1 :
            return next_header,"error","error"
    
        #calcula o checksum e monta o header ip
        h_ip = struct.pack("!BBHHHBBH4s4s", version_ihl, tos, total_len, ip_id, offset, ttl,protocol, ip_checksum, s_addr, d_addr)
        ip_checksum = checksum(h_ip)
        h_ip = struct.pack("!BBHHHBBH4s4s", version_ihl, tos, total_len, ip_id, offset, ttl,protocol, ip_checksum, s_addr, d_addr)
        return h_ip + next_header, socket.inet_ntoa(s_addr), socket.inet_ntoa(d_addr)
    return next_header,"error","error"


def bytes_to_mac(bytesmac):
    return ":".join("{:02x}".format(x) for x in bytesmac)

#=====================================
def tick_table(t,l, lastUpdateTime, now):
    for k in list(t.keys()):
        e = t[k]
        if e > l:
            del t[k]
        else:
            t[k]+=now-lastUpdateTime

def tick_timers(lastUpdateTime):
    now = int(time.time())
    if lastUpdateTime+1 < now:
        tick_table(used, lease_time, lastUpdateTime, now)
        return now
    return lastUpdateTime
#=====================================


try:
    s0 = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(ETH_P_ALL))
    s0.bind(('eth0',0))
except OSError as msg:
    print('Error'+str(msg))
    sys.exit(1)

print('Socket created!')

inputs = [s0]
outputs = []

lastTimerUpdate = int(time.time())

while inputs:
    lastTimerUpdate = tick_timers(lastTimerUpdate)

    readable, writable, exceptional = select.select(
            inputs, outputs, inputs)
    for s in readable:
        (packet,addr) = s.recvfrom(65536)

        eth_length = 14
        eth_header = packet[:14]

        eth = struct.unpack("!6s6sH",eth_header)

        interface = "eth0" if s is s0 else "eth1"
        nexthdr = packet[14:]

        if s is s0 : # eth0 - 00:00:00:aa:00:01
            if eth[2] == 2048 : # IP
                # Header Ethernet
                protocol = eth[2]
                nexthdr,ip_s,ip_d = ipv4(nexthdr)
                if ip_s == "error":
                    continue
                source_mac = my_mac
                dest_mac = b"\xff\xff\xff\xff\xff\xff" # broadcast// eth[1] unicast               
                eth_hdr = struct.pack("!6s6sH", dest_mac, source_mac, protocol)
                packet = eth_hdr+nexthdr 
                s0.send(packet)
