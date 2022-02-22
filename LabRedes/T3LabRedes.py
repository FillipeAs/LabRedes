import socket, sys, time, argparse, random, string, statistics
from contextlib import closing

#Servidor que repete mensagens usando UDP
def udp_echo_server(pPorta, pBuffer):
    # Cria o socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, pBuffer)     
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, pBuffer)  
    
    #Define porta do socket
    nomeHost = socket.gethostname()
    ipHost = socket.gethostbyname(nomeHost)
    enderecoServidor = (ipHost, pPorta)
    print ("Iniciando servidor em %s: %s" % enderecoServidor)
    sock.bind(enderecoServidor)

    while True:
        print ("Esperando mensagem")
        data, address = sock.recvfrom(pBuffer)
        print ("\tRecebidos %s bytes de %s" % (len(data), address))
        print ("\tDados: %s" %data)
    
        if data:
            sent = sock.sendto(data, address)
            print ("\tEnviando %s bytes de volta para %s" % (sent, address))

#Servidor que repete mensagens usando TCP
def tcp_echo_server(pPorta, pBuffer):
    # Cria o socket TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    #Define tamanho do buffer de recebimento e do de envio como o recebido por parâmetro
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, pBuffer)     
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, pBuffer)      
    
    #Define o socket como reutilizável
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    #Define porta do socket
    nomeHost = socket.gethostname()
    ipHost = socket.gethostbyname(nomeHost)
    enderecoServidor = (ipHost, pPorta)
    print ("Iniciando servidor em %s: %s" % enderecoServidor)

    with closing(sock):
        sock.bind(enderecoServidor)        
        #Irá escutar e responder até 2 conexões simultâneas
        sock.listen(1)
        while True:
            print ("Esperando mensagem")
            client, address = sock.accept()
            with closing(client):
                while True:
                    #TALVEZ NECESSÁRIO QUEBRAR O BUFFER EM PARTES
                    data = client.recv(pBuffer)
                    if len(data)>0:
                        client.sendall(data)
                        print ("\tEnviando %s bytes de volta para %s" % (data, address))


#Cliente que repete mensagens usando UDP
#IMPLEMENTAR CONTROLE DE TIMEOUT PARA NÂO BLOQUEAR PROGRAMA com select.select(), socket.setblocking, 
def udp_echo_client(pPorta, pIP, pInc, pNum, pBuffer):
    # Cria o socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #sock.setblocking(False) #Define o socket como bloqueante para que não espere para sempre a resposta de uma mensagem

    server_address = (pIP, pPorta)
    print ("Conectando com servidor em %s: %s" % server_address)

    try:
        #auxiliares
        medLatFin = []
        medVazFin = []
        #enquanto não mandou pacotes de todos os tamanhos
        pacEnv = 0
        #pacRecb = 0
        pacPerdido = 0
        latAcum = []
        #jitterAcum = []
        vazAcum = []
        for tam in range(pInc[0], pInc[1]+1, pInc[2]):
            #manda um número especificado por parâmetro de cada tamanho de pacote
            numTrans = 0
            for _ in range(0,int(pNum)):
                #Gera mensagem aleatória
                message = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(tam))
                #print ("\tEnviando: %s" % message)
                tempoInit = time.time() #Guarda momento de envio                
                sent = sock.sendto(message.encode('utf-8'), server_address)                
                tempoVazEnd = time.time() #Guarda momento de fim do envio
                #Marca que enviou o pacote
                pacEnv +=1 

                # Recebe Resposta
                try:
                    sock.settimeout(1.0)
                    data, server = sock.recvfrom(pBuffer)
                except socket.timeout: #Se deu timeout
                    pacPerdido +=1
                    #sleep(1)
                    #print 'recv timed out, retry later'
                    #tempoEnd = time.time() #Guarda momento de recebimento
                    #continue #Passa para próxima mensagem
                except socket.error:# Erro inesperado
                    print("Socket error")
                    sys.exit(1)
                else: #Recebeu algo
                    if len(data) == 0: #Recebey mensagem vazia
                        print("Servidor encerrou")
                        sys.exit(0)
                    else: #Recebeu resposta
                        #Guarda momento de recebimento
                        tempoEnd = time.time()
                        latAcum += [(tempoEnd - tempoInit)*1000/2] #Round trip time /2 e convertido em milisegundos       
                        #Idem latência porém apenas se pacote recebido
                        #jitterAcum += [(tempoEnd - tempoInit)*1000/2] 
                        #Marca que recebeu resposta
                        #pacRecb +=1 
                
                numTrans +=1         
                vazAcum += [(tam/1000) / (tempoVazEnd - tempoInit)] #Tamanho do pacote em kilobytes enviados pelo tempo em segundos
     
                if len(latAcum) > 1:
                    latStdDev = statistics.stdev(latAcum) #Desvio padrão em ms
                else:
                    latStdDev = -1
     
                if len(vazAcum) > 1:
                    vazStdDev = statistics.stdev(vazAcum) #Desvio padrão em kb/s
                else:
                    vazStdDev = -1

                latMed = sum(latAcum)/numTrans  #Media em ms           
                vazMed = sum(vazAcum)/numTrans  #media da vazão em kb/s
                
                pacPercent = pacPerdido/pacEnv*100       #Porcentagem de pacotes perdidos
                #jitter = statistics.stdev(jitterAcum) #Jitter em milisegundos

                #FAZER EXIBIÇAO DOS DADOS
                print("--------------------------------------------------------------------------------------------------------")
                print("numTrans., tamPct(bytes), med.Lat(ms), stdDevLat(ms), medVaz(kb/s), stdDevVaz(kb/s), PctPerd.(%), Jitter")
                print(numTrans, tam, "%.2f" %latMed, "%.2f" %latStdDev, "%.2f" %vazMed, "%.2f" %vazStdDev, "%.2f" %pacPercent, "%.2f" %latStdDev)
                medLatFin += [round(latMed, 2)]
                medVazFin += [round(vazMed, 2)]

                '''
                >>-número da transmissão (valor incremental iniciando em 1) com um tamanho específico de pacote (payload)
                >>-tamanho do pacote (payload) transmitido em bytes
                -média e desvio padrão da latência para transmissão dos dados (considerando a quantidade de transmissões) em milissegundos
                    A latência deve ser calculada através da divisão do RTT (Round Trip Time) por 2.
                -média e desvio padrão da vazão de transmissão dos dados (considerando a quantidade de transmissões) em kbytes/s
                -porcentagem de pacotes transferidos corretamente (sem perda) - de zero até um
                -jitter
                    -O jitter deve ser calculado como o desvio padrão das latências (desconsiderando pacotes perdidos).
                    -O atraso máximo que deve ser considerado no UDP para identificar uma perda é de 1 segundo.'''

    finally:
        print ("Fechando conexão com Servidor")
        print(medLatFin)
        print(medVazFin)
        #Aqui
        sock.close()

#Cliente que repete mensagens usando TCP
def tcp_echo_client(pPorta, pIP, pInc, pNum, pBuffer):
    # Cria o socket TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #Define tamanho do buffer de recebimento e do de envio como o recebido por parâmetro
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, pBuffer)     
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, pBuffer)   

    #Define o socket como reutilizável
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Connect the socket to the server
    server_address = (pIP, pPorta)
    print ("Conectando com servidor em %s: %s" % server_address)

    with closing(sock):    
        # Send data
        #auxiliares
        medLatFin = []
        medVazFin = []
        latAcum = []
        vazAcum = []
        
        sock.connect(server_address)
        
        #enquanto não mandou pacotes de todos os tamanhos
        for tam in range(pInc[0], pInc[1]+1, pInc[2]):
            #manda um número especificado por parâmetro de cada tamanho de pacote            
            numTrans = 0
            for _ in range(0,int(pNum)):                
                #Gera mensagem aleatória
                message = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(tam))
                
                tempoInit = time.time() #Guarda momento de envio                
                sock.sendall(message.encode('utf-8'))
                tempoVazEnd = time.time() #Guarda momento de fim do envio
                
                # Recebe Resposta
                try:
                    #sock.settimeout(1.0)
                    data = sock.recv(pBuffer)
                except socket.error:# Erro inesperado
                    print("Socket error")
                    sys.exit(1)
                else: #Recebeu algo
                    if len(data) == 0: #Recebey mensagem vazia
                        print("Servidor encerrou")
                        sys.exit(0)
                    else: #Recebeu resposta
                        # Esperar Resposta
                        amount_received = len(data)
                        amount_expected = tam
                        while amount_received < amount_expected:
                            data = sock.recv(int(pBuffer))
                            amount_received += len(data)
                            #print ("Recebido: " % data)
                        #Guarda momento de recebimento
                        tempoEnd = time.time()
                        latAcum += [(tempoEnd - tempoInit)*1000/2] #Round trip time /2 e convertido em milisegundos
                
                numTrans +=1
                latAcum += [(tempoEnd - tempoInit)*1000/2] #Round trip time /2 e convertido em milisegundos                
                vazAcum += [(tam/1000) / (tempoVazEnd - tempoInit)] #Tamanho do pacote em kilobytes enviados pelo tempo em segundos

                latMed = sum(latAcum)/numTrans  #Media em ms
                if len(latAcum) > 1:
                    latStdDev = statistics.stdev(latAcum) #Desvio padrão em ms
                else:
                    latStdDev = -1
    
                if len(vazAcum) > 1:
                    vazStdDev = statistics.stdev(vazAcum) #Desvio padrão em kb/s
                else:
                    vazStdDev = -1

                vazMed = sum(vazAcum)/numTrans  #media da vazão em kb/s
            
                #FAZER EXIBIÇAO DOS DADOS
                print("-----------------------------------------------------------------------------------")
                print("numTrans., tamPct(bytes), med.Lat(ms), stdDevLat(ms), medVaz(kb/s), stdDevVaz(kb/s)")
                print(numTrans, tam, "%.2f" %latMed, "%.2f" %latStdDev, "%.2f" %vazMed, "%.2f" %vazStdDev)
                medLatFin += [round(latMed, 2)]
                medVazFin += [round(vazMed, 2)]
                '''Protocolo TCP
                -Número da transmissão (valor crescente começando em 1) para um tamanho específico de payload
                -Tamanho de payload em bytes
                -Média e desvio padrão da latência em milissegundos (considerando a quantidade de transmissões) 
                -Média e desvio padrão da vazão de transmissão dos dados (considerando a quantidade de transmissões) em kbytes/s
                    -A latência deve ser calculada através da divisão do RTT (Round Trip Time) por 2.'''

        print(medLatFin)
        print(medVazFin)


#FAZER UM MAIN
def main(given_args):

    #Consistência de cliente/servidor
    if not (given_args.c or given_args.s):
        print("Necessário parâmetro de cliente ou servidor -c/-s.")
    elif given_args.c and given_args.s:
        print("Informe apenas um parâmetro de cliente ou servidor -c/-s.")
    #Consistência de TCP/UDP
    elif not (given_args.t or given_args.u):
        print("Necessário parâmetro de Protocolo TCP ou UDP -t/-u.")
    elif given_args.t and given_args.u:
        print("Informe apenas um parâmetro de Protocolo TCP ou UDP -t/-u.")
    #Se tudo ok
    else:
        if given_args.c: #Se está rodando no modo Cliente
            print("Iniciando modo Cliente")
            #Parâmetros: -c -t/-u <-p> -a -w -n <-b>
            pInc = given_args.incremento.split(",")
            pIncremento = [int(pInc[0]), int(pInc[1]), int(pInc[2])]

            if given_args.t:
                    tcp_echo_client(given_args.porta, given_args.ip, pIncremento, given_args.numero, given_args.buffer)        

            elif given_args.u:
                    udp_echo_client(given_args.porta, given_args.ip, pIncremento, given_args.numero, given_args.buffer)

        elif given_args.s: #Se está rodando no modo Serivdor
            print("Iniciando modo Servidor")
            #Parâmetros: -s -t/-u <-p> <-b>
            
            if given_args.t:
                    tcp_echo_server(given_args.porta, given_args.buffer)

            elif given_args.u:
                    udp_echo_server(given_args.porta, given_args.buffer)

if __name__ == '__main__':
    #Pega os parâmetros de entrada:
    #https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(description='Socket Cliente/Servidor')
    parser.add_argument('-c', action="store_true", dest="c")
    parser.add_argument('-s', action="store_true", dest="s")
    parser.add_argument('-t', action="store_true", dest="t")
    parser.add_argument('-u', action="store_true", dest="u")
    parser.add_argument('-p', action="store", dest="porta", type=int, default=65432)
    parser.add_argument('-a', action="store", dest="ip") #, type='string'
    parser.add_argument('-w', action="store", dest="incremento", default="8,32,8")#, type='string'
    parser.add_argument('-n', action="store", dest="numero", type=int, default=4)
    parser.add_argument('-b', action="store", dest="buffer", type=int, default=131072)
    given_args = parser.parse_args() 
    main(given_args)
