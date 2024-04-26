import socket
import ssl
import socks # connect via Tor socks5 on 127.0.0.1:9050

from src.misc import *

# <---------------------------------- Config ---------------------------------->

# IRC params
IRC_SERVER   = "irc.oftc.net"    # Choose an IRC network
IRC_PORT     = 6697              # IRC standard: 6667 = plain, 6697 = TLS
# IRC Login
IRC_PASSWORD = "password"
IRC_BOTNICK  = "unnamed_bot"     # Name of the bot in IRC
IRC_CHANNEL  = "#channel-name"   # Join a channel to be easier to find

# Tor proxy settings
USE_PROXY  = True
PROXY_IP   = "127.0.0.1"
PROXY_PORT = 9150                # 9150 = tor browser, 9050 = tor daemon


# <--------------------------------- Constant --------------------------------->

# Don't touch these, unless you know what you're doing.

# Constants
CONN_TIMEOUT = 30   # in sec, socket times out if it fails to connect in time
RECV_TIMEOUT = 1    # in sec, socket blocks while recv until timeout, doesn't fail, just tries again

# IRC end of line
ENDL = "\r\n"
# Output prefix
PRE_MSG = "IRC_Bot"


# <----------------------------- Class definition ----------------------------->

class IRCBot:
    def __init__(self,
                 server   : str = IRC_SERVER,
                 port     : int = IRC_PORT,
                 password : str = IRC_PASSWORD,
                 botnick  : str = IRC_BOTNICK):

        # Init vars
        self.botnick = botnick
        self.is_joined_channel = False
        # { tx_id : {user_name : message} }
        self.potential_tx_id_msg_map = {}

        msg_extra = ""

        # Init socket
        if USE_PROXY:
            # Tor SOCKS5 proxy socket
            sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            sock.set_proxy(socks.SOCKS5, PROXY_IP, PROXY_PORT)
            msg_extra = " over tor"
        else:
            # Normal socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            msg_extra = " over clearnet"

        # Connect
        sock.settimeout(CONN_TIMEOUT)
        sock.connect((server, port))

        # TLS / SSL socket
        context = ssl.create_default_context()
        context.verify_flags &= ssl.VERIFY_ALLOW_PROXY_CERTS
        self.sock = context.wrap_socket(sock, server_hostname=server)

        self.sock.settimeout(RECV_TIMEOUT)

        # Send login commands + args to IRC server
        self.send("PASS", password)
        self.send("USER", botnick + " " + botnick + " " + botnick + " " + botnick)
        self.send("NICK", botnick)

        printm(PRE_MSG, f"Connected and sent login information to {server}:{port}{msg_extra}.")


    def send(self, command : str, msg : str):
        # command + space + \r\n
        msg_extra_len = len(command) + 1 + 2
        if msg_extra_len + len(msg) > 512:
            msg = msg[:512-msg_extra_len]
        self.sock.send(bytes(command + " " + msg + ENDL, "UTF-8"))

    def join_channel(self, channel : str):
        self.send("JOIN", channel)
        printm(PRE_MSG, f">> JOIN {channel}")
        self.is_joined_channel = True

    # Respond to server pings, so we don't get kicked
    def ping_pong(self, response : str):
        self.send("PONG :", response)
        printm(PRE_MSG, f">> PONG {response}")

    def handle_welcome(self, msg : str):
        printd(PRE_MSG, f"msg:\n{msg}\n<--msg end-->")
        if "Welcome" in msg:
            self.join_channel(IRC_CHANNEL)

    def handle_ping_pong(self, msg : str):
        if "PING :" in msg:
            start_idx = msg.find("PING :")+6
            end_idx = msg[start_idx:].find(ENDL)
            if end_idx == -1:
                self.ping_pong(msg[start_idx:])
            else:
                self.ping_pong(msg[start_idx:start_idx+end_idx])
            return True
        return False

    def handle_private_msg(self, msg : str):
        handled_priv_msg = False
        for m in msg.split(ENDL):
            if not "PRIVMSG "+self.botnick+" :" in m:
                continue
            user_name = m[1:m.find("!")]
            priv_msg = m[m.find(self.botnick+" :")+len(self.botnick)+2:]
            self.find_potential_tx_id_msg_pair(user_name, priv_msg)
            printd(PRE_MSG, "handle priv msg " + priv_msg)
            printd(PRE_MSG, "user_name " + user_name)
            handled_priv_msg = True
        return handled_priv_msg

    # Everything else is pretty generic bot stuff, this is where the customization begins.
    # Just check length and allowed chars to see if tx_id could be valid.
    # xmr_tx_notify.py will check for actual validity.
    def find_potential_tx_id_msg_pair(self, user_name : str, msg : str):
        if not ":" in msg:
            return False
        printd(PRE_MSG, "user " + user_name)
        printd(PRE_MSG, "msg " + msg)
        # Check tx_id
        tx_id = msg[msg.find("\2")+1:msg.find(":")].strip(" ")
        if len(tx_id) != 64:
            printw(PRE_MSG, f"Abort: invalid tx_id length: {len(tx_id)}")
            return False
        for chr in tx_id:
            if not ((ord(chr) >= 97 and ord(chr) <= 102) or (ord(chr) >= 48 and ord(chr) <= 57)):
                printw(PRE_MSG, f"Abort: invalid tx_id char: {chr}")
                return False

        message = msg[msg.find(":")+1:]

        if tx_id not in self.potential_tx_id_msg_map:
            printm(PRE_MSG, f"Added potential <tx_id>:<msg> pair:\n"\
                            f"\tuser: {user_name}\n"\
                            f"\ttx_id: {tx_id}\n"\
                            f"\tmessage:{message}")
            self.potential_tx_id_msg_map[tx_id] = {user_name : message}
            return True
        return False

    def recv(self):
        try:
            return self.sock.recv(2048).decode("UTF-8").strip(ENDL)
        except TimeoutError:
            return ""

    def step(self):
        irc_msg = self.recv()
        if len(irc_msg) == 0:
            return

        printd(PRE_MSG, f"IRC MSG:\n{irc_msg}")

        if not self.is_joined_channel and self.handle_welcome(irc_msg):
            pass
        elif self.handle_ping_pong(irc_msg):
            pass
        elif self.is_joined_channel and self.handle_private_msg(irc_msg):
            pass

