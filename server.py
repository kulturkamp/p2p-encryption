import socket
import threading
import time
from api import deserialize_tuple
import logging

# server (and client) are from Thread for simultaneous work
class Server(threading.Thread): 
    def __init__(self, chatApp): 
        super(Server, self).__init__()
        self.chatApp = chatApp
        self.port = self.chatApp.port 
        self.host = "" 
        self.hasConnection = False 
        self.stopSocket = False

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.socket.bind((self.host, self.port))
        self.socket.listen()

        self.chatApp.sysMsg(f'Started server on port {self.port}')

    def run(self):
        conn, addr = self.socket.accept() 
        if self.stopSocket:
            exit(1)
        # first received bytes are initial info
        init = conn.recv(9*1024)
        self.hasConnection = True        
        self.initialize(init)
        
        # listening loop
        while True:
            if len(self.chatApp.ChatForm.chatFeed.values) > self.chatApp.ChatForm.y - 10:
                self.chatApp.clearChat()
            data = conn.recv(99999*1024)

            if not data:
                self.chatApp.sysMsg('Received empty message')
                self.chatApp.sysMsg('Disconnecting...')
                break
            splitted = data.split(b' ')

            if splitted[0] == b'/file':
                # removing command text
                data = data.replace(splitted[0] + b' ', b'')
                self.process_file(data)
            elif splitted[0] == b'/nick':
                data = data.replace(splitted[0] + b' ', b'')
                self.change_peer_nickname(data)
            elif splitted[0] == b'/quit':
                self.peer_quit()
            else:
                dec_data = self.chatApp.cryptography.decrypt_bytes(data)
                self.chatApp.ChatForm.chatFeed.values.append(f'{self.chatApp.peer} > {dec_data.decode()}')
                self.chatApp.ChatForm.chatFeed.display()


    def initialize(self, init):
        if not init: 
            self.chatApp.peer = 'unknown'
            self.chatApp.peerPort = "unknown"
            self.chatApp.peerIP = 'unknown'
            self.chatApp.peerPubKey = 'unknown'
        else: 
            splitted = init.split(b' ')           

            self.chatApp.peer = splitted[1].decode()    
            self.chatApp.peerIP = splitted[2].decode()
            self.chatApp.peerPort = splitted[3].decode()
            try:
                self.chatApp.peerPubKey = deserialize_tuple(splitted[4].decode())
            except Exception as e:
                self.chatApp.sysMsg('Something vent wrong during deserealizing peer publick key.')
                logging.exception(e)
                return

        if not self.chatApp.chatClient.isConnected:
            if self.chatApp.peerIP == "unknown" or self.chatApp.peerPort == "unknown":
                self.chatApp.sysMsg('Cant /connectback, peer IP and/or port is unknown.')
            else:
                self.chatApp.sysMsg('A client connected to you. To connect to them type /connectback.')
                self.chatApp.sysMsg(f'Their IP is {self.chatApp.peerIP}, theit port: {self.chatApp.peerPort}')

        self.chatApp.sysMsg(f'{self.chatApp.peer} joined chat.')

    # ChatApp reseting socket with this
    def stop(self):
        if self.hasConnection:
            self.socket.close()
        else:
            self.stopSocket = True
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('localhost', self.port))
            time.sleep(0.2)
            self.socket.close()
        self.socket = None
        
    # change peers nickname here
    def change_peer_nickname(self, nick):
        oldNick = self.chatApp.peer
        self.chatApp.peer = nick.decode()
        self.chatApp.sysMsg(f'{oldNick} change name to {nick.decode()}')

    # if peer somehow left
    def peer_quit(self):
        self.chatApp.chatClient.isConnected = False
        self.chatApp.sysMsg(f'{self.chatApp.peer} left the chat.')        
        self.chatApp.restart()

    def process_file(self, arg):        
        filename = arg.split(b' ')[0]
        enc_bts = arg.replace(filename + b' ', b'')
        try:
            dec_bts = self.chatApp.cryptography.decrypt_bytes(enc_bts)
        except ValueError as e:
            self.chatApp.sysMsg('File was too big.')
            return
        with open(f'[RECEIVED]{filename.decode()}', 'wb') as f:
            f.write(dec_bts)

        self.chatApp.sysMsg(f'File {filename.decode()} was received')


    