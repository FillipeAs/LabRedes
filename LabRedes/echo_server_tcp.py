#!/usr/bin/env python
# Python Network Programming Cookbook, Second Edition -- Chapter - 1
# This program is optimized for Python 2.7.12 and Python 3.5.2.
# It may run on any other version with/without modifications.


import socket
import argparse
from contextlib import closing

host = 'localhost'
data_payload = 2048
backlog = 5


def echo_server(port):
    """ A simple echo server """
    # Create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enable reuse address/port
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind the socket to the port
    server_address = (host, port)
    print ("Starting up echo server  on %s port %s" % server_address)
    with closing(sock):
        sock.bind(server_address)
        # Listen to clients, backlog argument specifies the max no. of queued connections
        sock.listen(backlog)
        while True:
            print ("Waiting to receive message from client")
            client, address = sock.accept()
            with closing(client):
                while True:
                    data = client.recv(data_payload)
                    if data:
                        print ("Data: %s" %data)
                        client.send(data)
            # end connection
            #client.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Socket Server Example')
    parser.add_argument('--port', action="store", dest="port", type=int, required=True)
    given_args = parser.parse_args()
    port = given_args.port
    echo_server(port)
