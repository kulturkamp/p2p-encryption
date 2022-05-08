import npyscreen
import server as server
import client as client
from form import ChatForm
import time
import socket
import pyperclip
import os
from api import crypto, generate_sessionkey
import logging

class ChatApp(npyscreen.NPSAppManaged):
    def onStart(self):
        """npyscreen calls this on start of app"""
    
        # binding form
        if os.name == 'nt':
            os.system('title Ecnrypted P2P chat')
        self.ChatForm = self.addForm('MAIN', ChatForm, name='Ecnrypted P2P chat')


        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            self.hostname = s.getsockname()[0]
            s.close()
        except socket.error as e:
            self.sysMsg('No internet connection (very possible)')
            self.sysMsg('Could not get public IP')
            self.hostname = '0.0.0.0'

        """INITIAL NETWORK VARIABLES"""
        self.port = 3333 # Port the server runs on
        self.nickname = '' # Empty variable to be filled with users nickname
        self.peer = '' # Peer nickname
        self.peerIP = '0' # IP of peer
        self.peerPort = '0' # Port of peer
        self.historyLog = [] # Array for message log
        self.historyPos = 0 # Int for current position in message history

        """INITIAL CRYPTOGRAPHY OBJECTS"""
        self.session_key = generate_sessionkey(16)
        self.cryptography = crypto(self, self.session_key)
        self.peerPubKey = None

        """SERVER AND CLIENT THREADS"""
        self.chatServer = server.Server(self)
        self.chatServer.daemon = True
        self.chatServer.start()
        self.chatClient = client.Client(self)
        self.chatClient.start()

        """COMMANDS HANDLING"""
        # command name: [command handler, number of arguments, description for /help]
        self.commandDict = {
            'connect': [self.chatClient.conn, 2, '/connect [host] [port] | Connect to a peer'],
            'disconnect': [self.restart, 0, '/disconnect | Disconnect from the current chat'],
            'nickname': [self.nickname_command, 1, '/nickname [nickname] | Set your nickname'],
            'file': [self.file_command, 1, '/file [filename] | Encrypt and send a file to a peer'],
            'quit': [self.quit_command, 0, '/quit | Exit app'],
            'port': [self.restart, 1, '/port [port] | Restart on specified port'],
            'connectback': [self.connback_command, 0, '/connectback | Connect to the client that is connected to your server'],
            'clear': [self.clear_command, 0, '/clear | Clear feed'],
            'status': [self.status_command, 0, '/status | See current client`s status'],
            'help': [self.help_command, 0, '/help | this']
          
        }

        self.commandAliasDict = {
            'nick': 'nickname',
            'conn': 'connect',
            'q': 'quit',
            'connback': 'connectback'
        }

    # calling commands from command dict
    def handle_command(self, msg):
        msg = msg.split(' ')
        command = msg[0][1:]
        args = msg[1:]
        # if alias of command was used
        if command in self.commandAliasDict:
            command = self.commandAliasDict[command]

        if command not in self.commandDict:
            # if there is not such a command
            self.sysMsg('Command not found. /help')
        else:
            if self.commandDict[command][1] == 0:
                # command with no parameters
                self.commandDict[command][0]()
            elif len(args) == self.commandDict[command][1]:
                self.commandDict[command][0](args)
            else:
                # wrong command syntax
                self.sysMsg(f'{command} takes {self.commandDict[command][1]} argument(s), {len(args)} was found')


    # restarting app`s client and server
    def restart(self, args=None):
        self.sysMsg('Restarting sockets')
        if not args == None and args[0] != self.port:
            self.port = int(args[0])
        if self.chatClient.isConnected:
            # list for b' '.join() in self.client.send
            self.chatClient.send([b'/quit'])
            time.sleep(0.2)
        self.chatClient.stop()
        self.chatServer.stop()
        self.chatClient = client.Client(self)
        self.chatClient.start()
        self.chatServer = server.Server(self)
        self.chatServer.daemon = True
        self.chatServer.start()           

    # setting client`s name and sending it to peer
    def nickname_command(self, args):
        self.nickname = args[0]
        self.sysMsg(f'Nickname set to {args[0]}')
        if self.chatClient.isConnected:
            # list for b' '.join() in self.client.send
            self.chatClient.send([f'/nick {args[0]}'.encode()])

    # send message to a connected peer
    def send_message(self, _input):
        msg = self.ChatForm.chatInput.value #plain msg
        
        if msg == '':
            return False
        if len(self.ChatForm.chatFeed.values) > self.ChatForm.y - 11:
                self.clear_command()
        self.historyLog.append(msg)
        self.historyPos = len(self.historyLog)
        self.ChatForm.chatInput.value = ''
        self.ChatForm.chatInput.display()
        if msg.startswith('/'):
            self.handle_command(msg)
        else:
            if self.chatClient.isConnected:
                enc_msg = self.cryptography.encrypt_bytes(msg.encode())
                if self.chatClient.send(enc_msg):
                    self.ChatForm.chatFeed.values.append(f'You > {msg}')
                    self.ChatForm.chatFeed.display()
            else:
                self.sysMsg('You are not connected to a peer. /help')

    # encrypt and sent a file to a peer
    def file_command(self, filename):
        filename = filename[0]
        if self.chatClient.isConnected:
            try:
                sz = os.stat(filename).st_size
                self.sysMsg(f'Trying to send {sz} file.')
                with open(filename, 'rb') as f:
                    bts = f.read()
            except FileNotFoundError as e:
                self.sysMsg(f'File {filename} not found.')
                logging.exception(e)
                return
            enc_bts = self.cryptography.encrypt_bytes(bts)
            to_send = [b'/file'] + [filename.encode()] + enc_bts
            if self.chatClient.send(to_send):
                self.sysMsg(f'File {filename} was sent')
        else:
            self.sysMsg('You are not connected to a peer. /help') 

    # connect to a peer that is connected to the server
    def connback_command(self):
        if self.chatServer.hasConnection and not self.chatClient.isConnected:
            if self.peerIP == 'unknown' or self.peerPort == 'unknown':
                self.sysMsg('Cant connect, peer IP and/or port is unknown')
                return False
            self.chatClient.conn([self.peerIP, int(self.peerPort)])
        else:
            self.sysMsg('You are already connected')

    # clear feed
    def clear_command(self):
        self.ChatForm.chatFeed.values = []
        self.ChatForm.chatFeed.display()
            
    # exit app (used in restarting)
    def quit_command(self):
        self.sysMsg('Exiting...')
        if self.chatClient.isConnected:
            # list for b' '.join() in self.client.send
            self.chatClient.send([b'/quit'])
        self.chatClient.stop()
        self.chatServer.stop()
        exit(1)   

    # show client`s status
    def status_command(self):
        self.sysMsg('STATUS:')
        if self.chatServer: 
            serverStatus = True
        else: 
            serverStatus = False
        if self.chatClient: 
            clientStatus = True
        else: 
            clientStatus = False

        self.sysMsg(f'SERVER >>> Running: {serverStatus} | Port: {self.port} | Is connected: {self.chatServer.hasConnection}')
        self.sysMsg(f'CLIENT >>> Running: {clientStatus} | Is connected: {self.chatClient.isConnected}')
        if self.nickname != '':
            self.sysMsg(f'Nickname >>> {self.nickname}')

    # help command handler
    def help_command(self):
        # clearing feed if full
        if len(self.ChatForm.chatFeed.values) + len(self.commandDict) + 1 > self.ChatForm.y - 10:
            self.clear_command()

        self.sysMsg('Avaliable commands:')
        for command in self.commandDict:
            self.sysMsg(self.commandDict[command][2])

    """UTILITY AND FORM HANDLING UNCTIONS"""
    # display system message
    def sysMsg(self, msg):
        # hadling long messages        
        if len(self.ChatForm.chatFeed.values) > self.ChatForm.y - 10:
                self.clear_command()
        if len(str(msg)) > self.ChatForm.x - 20:
            self.ChatForm.chatFeed.values.append(f'[SYSTEM] {str(msg[:self.ChatForm.x-20])}')
            self.ChatForm.chatFeed.values.append(str(msg[self.ChatForm.x-20:]))
        else:
            self.ChatForm.chatFeed.values.append(f'[SYSTEM] {str(msg)}')
        self.ChatForm.chatFeed.display()

        # npycreen calls this on key_up to scroll sent history back
    def historyBack(self, _input):
        if not self.historyLog or self.historyPos == 0:
            return False
        self.historyPos -= 1
        self.ChatForm.chatInput.value = self.historyLog[len(self.historyLog)-1-self.historyPos]

    # npycreen calls this on key_down to scroll sent history forward
    def historyForward(self, _input):
        if not self.historyLog:
            return False
        if self.historyPos == len(self.historyLog)-1:
            self.ChatForm.chatInput.value = ''
            return True
        self.historyPos += 1
        self.ChatForm.chatInput.value = self.historyLog[len(self.historyLog)-1-self.historyPos]

    # npyscreen calls this to handle ctrl+v to paste text
    def pasteFromClipboard(self, _input):
        self.ChatForm.chatInput.value = pyperclip.paste()
        self.ChatForm.chatInput.display()
       
if __name__ == '__main__':
    chatApp = ChatApp().run()