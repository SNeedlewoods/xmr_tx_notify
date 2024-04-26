#! /usr/bin/python3

# <--------------------------- pre-import Constants --------------------------->

# Don't change anything in here

# Modes

# Receive a notification with the <tx_amount> and a pre-defined message,
# when a tx is received.
# (Easy mode)
MODE_NOTIFICATION = 0
# Receive a notification with a <donator_name>, <message> & <tx_amount>,
# when a couple conditions are met:
#   - a tx is received
#   - (tx_id, donator_name, message) tuple is received in time by
#       MessageReceiver and tx_id refers to a recently received tx, which
#       hasn't been displayed yet.
# (Advanced mode)
MODE_DONATION     = 1

# Currently supported operating systems
SUPPORTED_OS = ["Linux", "Windows"]

# Output prefix
PRE_MSG = "Main"


# <---------------------------- pre-import Config ----------------------------->

# - Set to True in case you don't care about extra dependencies and want
#   something "fancy". (Notification popup with custom size, font, background
#   image, colors, sound)
# - Set to False to just use OS dependent notification system without sound and
#   without the need for special dependencies.
IS_FANCY_NOTIFY = True
# Set to one of the modes listet above
MODE = MODE_DONATION


# <---------------------------------- Import ---------------------------------->

import json         # Misc
import time         # Misc
import threading    # Misc
import requests     # Talk to monero-wallet-rpc
import platform     # run OS dependent code

from src.misc import *

# Exit if OS is not supported
OS = platform.system()
if not OS in SUPPORTED_OS:
    printe(PRE_MSG, f"OS `{OS}` not implemented.\n"\
            f"Currently there's only support for: {', '.join(str(os) for os in SUPPORTED_OS)}.")

if OS == "Linux":
    # Window hacks (if IS_FANCY_NOTIFY) / Notification (else)
    import subprocess

if IS_FANCY_NOTIFY:
    # Sets environment variables for pygame
    import os
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    # Popup display + text + sound
    import pygame

    if "Windows" in OS:
        import win32gui

if MODE == MODE_DONATION:
    from src.bots.irc_bot import IRCBot as MessageReceiver


# <---------------------------- post-import Config ---------------------------->

# monero-wallet-rpc
RPC_IP   = "127.0.0.1"
RPC_PORT = 18099
RPC_LOGIN_USERNAME = "notification_wallet"
RPC_LOGIN_PASSWORD = "password"

RPC_URL = f"http://{RPC_IP}:{RPC_PORT}/json_rpc"
RPC_LOGIN_AUTH = requests.auth.HTTPDigestAuth(RPC_LOGIN_USERNAME, RPC_LOGIN_PASSWORD)

# Display
if IS_FANCY_NOTIFY:
    # If you have multiple screens e.g.
    #       1. [ screen_1 ] [ screen_2 ]
    #           and you want the pop-up to appear on the left of [ screen_2 ],
    #           you have to set WINDOW_POS_X to the width of [ screen_1 ]
    #       2. [ screen_2 ] [ screen_1 ]
    #           and you want the pop-up to appear on the left of [ screen_2 ],
    #           you have to set WINDOW_POS_X to the negative width of [ screen_2 ]
    # You maybe have to play around with these to get the desired result.
    WINDOW_POS_X  =    0
    WINDOW_POS_Y  =    0
    WINDOW_WIDTH  =  600
    WINDOW_HEIGHT =  300

    # Any character beyond will be cut off and not shown in pop-up
    MAX_LEN_ROWS = 7
    # Auto-wrap messages, characters per line.
    MAX_LEN_LINE = 30

# Notification pop-up message
if MODE == MODE_NOTIFICATION:
    DEFAULT_NOTIFICATION_NAME    = "Miner"
    NOTIFICATION_PREFIX          = "  mined"
    DEFAULT_NOTIFICATION_MESSAGE = ""
elif MODE == MODE_DONATION:
    DEFAULT_NOTIFICATION_NAME    = "anon"
    NOTIFICATION_PREFIX          = "donated"
    DEFAULT_NOTIFICATION_MESSAGE = "*had nothing to say*"
    # - Set to 0 to get instantly notified, without waiting for a message.
    # - Set to -1 to wait until message arrives, if you never receive a message
    #   for a given tx_id you'll never get notified.
    # - Otherwise set this to reasonable amount to wait for donator to write
    #   and MessageReceiver to pick up the message.
    WAIT_SECONDS_UNTIL_TX_SHOWN = 300

# How long notification appears on screen.
SHOW_NOTIFICATION_DURATION_SECONDS = 8
# How often the monero-wallet-rpc gets called to look for new incoming tx.
# Average block time is 120 seconds.
SCAN_INTERVAL_SECONDS = 40


# <----------------------------------- Init ----------------------------------->

if IS_FANCY_NOTIFY:
    pygame.init()
    # Set window position, pygame does not come with this functionality.
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{WINDOW_POS_X},{WINDOW_POS_Y}"

    # Load assets
    # can be found and easily changed in `assets/`.

    # Works with 300x300 image with transparent background.
    # May need some adjustments for different sizes.
    if OS == "Linux":
        DONATION_BG_PNG = pygame.image.load("assets/donation_bg.png")
        DONATION_SOUND  = pygame.mixer.Sound("assets/donation_sound.wav")
        MONERO_ICON_PNG = pygame.image.load("assets/monero_icon.png")
    elif OS == "Windows":
        DONATION_BG_PNG = pygame.image.load(r"assets\donation_bg.png")
        DONATION_SOUND  = pygame.mixer.Sound(r"assets\donation_sound.wav")
        MONERO_ICON_PNG = pygame.image.load(r"assets\monero_icon.png")

    # Fonts
    FONT_SMALL      = pygame.font.Font(None, 24)
    FONT_MED        = pygame.font.Font(None, 30)
    FONT_MED_BOLD   = pygame.font.Font(None, 32)
    FONT_BIG_BOLD   = pygame.font.Font(None, 48)

    FONT_MED_BOLD.set_bold(True)
    FONT_BIG_BOLD.set_bold(True)


# <---------------------------------- Global ---------------------------------->

last_scan_time    = 0
pop_up_start_time = 0
rpc_call_id       = 0


# <-------------------------------- Functions --------------------------------->

# monero-wallet-rpc
def rpc_call(method : str, params : dict = {}):
    global rpc_call_id

    try:
        res = requests.post(RPC_URL,
                            headers = {"Content-Type":"application/json"},
                            auth    = RPC_LOGIN_AUTH,
                            data    = json.dumps({"jsonrpc":"2.0",
                                                  "id":str(rpc_call_id),
                                                  "method":method,
                                                  "params":params}))
    except requests.exceptions.ConnectionError:
        printe(PRE_MSG, f"Unable to connect to wallet rpc: {RPC_URL}\n"\
                        f"Make sure monero-wallet-rpc is running and the config in {__file__} is set accordingly.")

    if res.status_code != 200:
        printe(PRE_MSG, f"Response status code: {res.status_code}\n"\
                        f"Response:\n{res.text}")

    if "error" in res.json():
        printe(PRE_MSG, f"\nMethod: {method}\n"\
                        f"Params: {params}\n"\
                        f"RPC-response: {res.json()}")

    rpc_call_id += 1
    return res.json()



# Notification pop-up
def notification_pop_up(user_name : str,
                        amount : float,
                        message : str):

    if IS_FANCY_NOTIFY:
        if OS == "Linux":
            notification_fancy_pop_up_linux(user_name, amount, message)
        elif OS == "Windows":
            notification_fancy_pop_up_windows(user_name, amount, message)
    else:
        notification_non_fancy_pop_up(user_name, amount, message)


# Uses OS dependent notification method
def notification_non_fancy_pop_up(user_name : str,
                                  amount : float,
                                  message : str):

    if OS == "Linux":
        subprocess.Popen(["notify-send",
                      user_name,
                      f"{NOTIFICATION_PREFIX} {amt2str(amount)} {message}"])
    elif OS == "Windows":
        printw(PRE_MSG, "TODO : implement notification_non_fancy_pop_up() for Windows.")


# Uses pygame window + background image + sound
def notification_fancy_pop_up_linux(user_name : str,
                                    amount : float,
                                    message : str):

    # Get currently used window id, to give back focus after pop-up is spawned.
    subp_out = subprocess.check_output(["xdotool", "getactivewindow"])
    previously_used_window_id = subp_out.decode("UTF-8").strip("\n")

    # Check if window is fullscreen
    subp_out = subprocess.check_output(["xprop",
                                        "-id",
                                        previously_used_window_id,
                                        "_NET_WM_STATE"])
    is_prev_used_window_fullscreen = "_NET_WM_STATE_FULLSCREEN" in subp_out.decode("UTF-8").strip("\n")

    # Sound
    pygame.mixer.Sound.play(DONATION_SOUND)

    # New window
    pygame.display.init()
    pygame.display.set_caption("Monero Donation")
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT),
                                      flags=pygame.NOFRAME)

    # Hack to keep the window always on top, but don't focus.
    window_id = pygame.display.get_wm_info()["window"]
    # This is not optimal, but for now I have not found a better alternative
    # to put pop-up infront of a fullscreen window.
    # If you open/focus another window in the wrong time,
    # the notification does not get diplayed in front.
    if is_prev_used_window_fullscreen:
        subprocess.Popen(["wmctrl", "-i", "-r", str(previously_used_window_id), "-b", "add,below"])
    subprocess.Popen(["wmctrl", "-i", "-r", str(window_id), "-b", "add,above,skip_taskbar"])
    subprocess.Popen(["xdotool", "windowfocus", str(previously_used_window_id)])

    # Background
    display.fill((0,0,0), (0,0, WINDOW_WIDTH, WINDOW_HEIGHT))
    display.blit(DONATION_BG_PNG, DONATION_BG_PNG.get_rect())

    # Text
    padding_left = 22
    text = FONT_BIG_BOLD.render(user_name, True, (155, 255, 155))
    display.blit(text, (padding_left, 20))
    text = FONT_MED_BOLD.render(NOTIFICATION_PREFIX, True, (255, 255, 255))
    display.blit(text, (padding_left, 64))
    text = FONT_BIG_BOLD.render(f"{amt2str(amount)} XMR", True, (255, 102, 0))
    display.blit(text, (padding_left+92, 56))

    row = 0
    sub_str = ""
    for i in range(len(message)):
        sub_str += message[i]
        if (i != 0) and (i % MAX_LEN_LINE == 0) or (i == len(message)-1):
            text = FONT_MED.render(sub_str, True, (255, 255, 255))
            display.blit(text, (padding_left, 98+row*28))
            row += 1
            sub_str = ""
            if row == MAX_LEN_ROWS:
                break

    pygame.display.set_icon(MONERO_ICON_PNG)
    pygame.display.update()
    pygame.event.set_grab(False)

    # QUIT
    time.sleep(SHOW_NOTIFICATION_DURATION_SECONDS)
    pygame.display.quit()


# Uses pygame window + background image + sound
def notification_fancy_pop_up_windows(user_name : str,
                                      amount : float,
                                      message : str):
    # Sound
    pygame.mixer.Sound.play(DONATION_SOUND)

    # New window
    pygame.display.init()
    pygame.display.set_caption("Monero Donation")
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT),
                                      flags=pygame.NOFRAME)

    # Put pop-up in foreground
    window_id = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowPos(window_id, -1, WINDOW_POS_X, WINDOW_POS_Y, 0, 0, 1)

    # Background
    display.fill((0,0,0), (0,0, WINDOW_WIDTH, WINDOW_HEIGHT))
    display.blit(DONATION_BG_PNG, DONATION_BG_PNG.get_rect())

    # Text
    padding_left = 22
    text = FONT_BIG_BOLD.render(user_name, True, (155, 255, 155))
    display.blit(text, (padding_left, 20))
    text = FONT_MED_BOLD.render(NOTIFICATION_PREFIX, True, (255, 255, 255))
    display.blit(text, (padding_left, 64))
    text = FONT_BIG_BOLD.render(f"{amt2str(amount)} XMR", True, (255, 102, 0))
    display.blit(text, (padding_left+92, 56))
    row = 0
    sub_str = ""
    for i in range(len(message)):
        sub_str += message[i]
        if (i != 0) and (i % MAX_LEN_LINE == 0) or (i == len(message)-1):
            text = FONT_MED.render(sub_str, True, (255, 255, 255))
            display.blit(text, (padding_left, 98+row*28))
            row += 1
            sub_str = ""
            if row == MAX_LEN_ROWS:
                break

    pygame.display.set_icon(MONERO_ICON_PNG)
    pygame.display.update()
    pygame.event.set_grab(False)

    # QUIT
    time.sleep(SHOW_NOTIFICATION_DURATION_SECONDS)
    pygame.display.quit()



def update_incoming_tx_cache(incoming_tx_cache : dict,
                             already_handled_tx_ids : list,
                             block_height : int):

    global last_scan_time

    # Remove already handled txs
    for tx_id in already_handled_tx_ids:
        if tx_id in incoming_tx_cache:
            del incoming_tx_cache[tx_id]

    # Don't spam scan
    if time.mktime(time.gmtime()) - last_scan_time < SCAN_INTERVAL_SECONDS:
        return block_height

    # RPC call `get_transfers`
    args = {"in": True,
            "filter_by_height": True,
            "min_height": block_height}
    res = rpc_call("get_transfers", args)
    # DEBUG
    printd(PRE_MSG, f"get_transfers response:\n{res}")

    # For spam scan protection
    last_scan_time = time.mktime(time.gmtime())

    # No new block since last scan
    if res["result"] == {}:
        return block_height

    printd(PRE_MSG, "get_transfers response:")
    printd(PRE_MSG, res["result"])

    # Add info from freshly scanned tx to incoming_tx_cache, if tx_id is not already handled
    for inp in res["result"]["in"]:
        if inp["txid"] in incoming_tx_cache or\
                inp["txid"] in already_handled_tx_ids:
            printw(PRE_MSG, f"Skip already handled tx_id: {inp['txid']}")
            continue

        incoming_tx_cache[inp["txid"]] = {"timestamp" : time.mktime(time.gmtime()),
                                          "amount" : sum(inp['amounts'])}

        # Update next scan height
        block_height = block_height if not inp["height"] > block_height else inp["height"]

    return block_height


def update_confirmed_messages(incoming_tx_cache : dict,
                              potential_msg_from_receiver : dict,
                              message_queue : list,
                              already_handled_tx_ids : list):

    for tx_id in incoming_tx_cache:
        if tx_id in potential_msg_from_receiver and not tx_id in already_handled_tx_ids:
            user_name = list(potential_msg_from_receiver[tx_id].keys())[0]
            data = {"tx_id"     : tx_id,
                    "user_name" : user_name,
                    "amount"    : incoming_tx_cache[tx_id]["amount"],
                    "message"   : potential_msg_from_receiver[tx_id][user_name]}
            printd(PRE_MSG, f"data: {data}")
            message_queue.append(data)


def update_timed_out_messages(incoming_tx_cache : dict,
                              message_queue : list,
                              already_handled_tx_ids : list):

    # Skip function if timed out messages are disabled
    if MODE == MODE_DONATION and WAIT_SECONDS_UNTIL_TX_SHOWN == -1:
        return

    for tx_id in incoming_tx_cache:
        if tx_id in already_handled_tx_ids:
            printw(PRE_MSG, "tx_id in already_handled_tx_ids, this should not happen.")
            continue

        # Use DEFAULT_ values for timed out messages
        if (MODE == MODE_DONATION and time.mktime(time.gmtime()) - incoming_tx_cache[tx_id]["timestamp"] > WAIT_SECONDS_UNTIL_TX_SHOWN)\
                or\
                MODE == MODE_NOTIFICATION:

            data = {"tx_id"     : tx_id,
                    "user_name" : DEFAULT_NOTIFICATION_NAME,
                    "amount"    : incoming_tx_cache[tx_id]["amount"],
                    "message"   : DEFAULT_NOTIFICATION_MESSAGE}
            if not data in message_queue:
                message_queue.append(data)


# <----------------------------------- Main ----------------------------------->

def main():
    global pop_up_start_time

    # {tx_id : {"timestamp" : timestamp, "amount" : amount} }
    incoming_tx_cache = {}
    # [{"tx_id" : tx_id, "name" : user_name, "message" : message, "amount" : amount}, ... ]
    message_queue = []
    already_handled_tx_ids = []

    pop_up_thread = None

    # Currently selected mode
    if MODE == MODE_NOTIFICATION:
        printm(PRE_MSG, "Running in NOTIFICATION mode.")
    elif MODE == MODE_DONATION:
        printm(PRE_MSG, "Running in DONATION mode.")
        # Init MessageReceiver
        msg_recvr = MessageReceiver()

    # Initial block height
    res = rpc_call("get_height")
    block_height = int(res["result"]["height"])
    block_height = 0
    printm(PRE_MSG, f"Initial block height: {block_height}")

    while True:
        block_height = update_incoming_tx_cache(incoming_tx_cache, already_handled_tx_ids, block_height)

        if MODE == MODE_DONATION:
            msg_recvr.step()

            if len(incoming_tx_cache) > 0:
                update_confirmed_messages(incoming_tx_cache, msg_recvr.potential_tx_id_msg_map, message_queue, already_handled_tx_ids)

        # Timed-out txs get a default user name and message, those get added to confirmed messages
        update_timed_out_messages(incoming_tx_cache, message_queue, already_handled_tx_ids)

        # Pop-Up
        if len(message_queue) > 0 and\
                (time.mktime(time.gmtime()) - pop_up_start_time > SHOW_NOTIFICATION_DURATION_SECONDS):
            m = message_queue.pop(0)
            already_handled_tx_ids.append(m["tx_id"])

            # Spawn non-blocking pop-up
            pop_up_thread = threading.Thread(target = notification_pop_up,
                                             args= (m["user_name"],
                                                    m['amount'],
                                                    m["message"]))

            pop_up_thread.start()
            pop_up_start_time = time.mktime(time.gmtime())

        while pop_up_thread != None and pop_up_thread.is_alive():
            pop_up_thread.join(0.5)
            if MODE == MODE_DONATION:
                msg_recvr.step()


if __name__ == "__main__":
    main()
