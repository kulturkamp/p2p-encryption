import socket
import threading

# client (and server) are from Thread for simultaneous work
class Client(threading.Thread): 
    def __init__(self, chatApp):
        super(Client, self).__init__()
        self.chatApp = chatApp
        self.isConnected = False

    def run(self):       
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5)

    def conn(self, args):
        # cant connect without a nickname
        if self.chatApp.nickname == '':
            self.chatApp.sysMsg('Nickname is not set. /help')
            return False

        host = args[0] # IP of peer
        port = int(args[1]) # Port of peer
        self.chatApp.sysMsg(f'Connecting to {host} on port {port}')
        try:
            self.socket.connect((host, port))
        except socket.error:
            self.chatApp.sysMsg('Connection timed out')
            return False
        
        # sending initial info including RSA public key
        self.socket.send(f'/init {self.chatApp.nickname} {self.chatApp.hostname} {self.chatApp.port} {self.chatApp.cryptography.serialised_public_ley}'.encode())
        self.chatApp.sysMsg('Connected')
        self.isConnected = True
    
    # ChatApp reseting socket with this
    def stop(self):
        self.socket.close()
        self.socket = None

    # send data to a peer
    def send(self, msg):
        if msg != '':
            try:
                self.socket.sendall(b' '.join(msg))                
                return True
            except socket.error as e:
                self.chatApp.sysMsg('Could not send data to peer. Disconnecting socket...')
                self.chatApp.sysMsg(e)
                self.isConnected = False
                return False


    


