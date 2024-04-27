# xmr_tx_notify

## Contents

* [Description](#description)
* [Possible use-cases](#possible-use-cases)
* [Features](#features)
* [Demo](#demo)
* [Supported OSs](#supported-oss)
* [Dependencies](#dependencies)
* [Installation](#installation)
* [Config](#config)
* [Usage](#usage)
* [Disclaimer](#disclaimer)
* [Todo](#todo)


## Description

This application shows a notification pop-up (+ optional sound effect), when a [Monero](https://github.com/monero-project/monero) transaction is received by your wallet.  
It is also possible to [receive messages](#receive-messages) linked via transaction id.


## Possible use-cases

* Can be used by a streamer, to receive donations in Monero and display the donators name + message in a pop-up.
* If you're fancy, you could just get notifications for your mining (or even, depends on how fancy you are, regular) wallet.


## Features

### Receive Messages

Have a `MessageReceiver` wait for messages in the format '\<tx_id\>:\<message\>'. If the `tx_id` refers to a recently received transaction, the message is stored in a queue and gets displayed in a notification pop-up.  
For now there is only one kind of `MessageReceiver`, for what is planned/considered to be added see [Todo](#todo).

#### IRC-Bot

___Warning:___ Using this over clearnet exposes your IP. It is advised to use [tor](https://www.torproject.org/) (see how to [config](#config-irc_botpy)).

The IRC-Bot is just hanging out in an arbitrary channel and waits for private messages.  
`/PRIVMSG <bot_name> <tx_id>:<msg>`  
The benefits of an IRC-Bot are:
* It's easy to use for everyone:
  * Donation recipient: just change some settings in the config.
  * Donator: can use one of many IRC clients or use a webchat.
  * Developer: this was my first attempt to write a bot, and it went pretty well, I guess.
* Does not require to open ports on your router, because we rely on outgoing connections only and use the IRC network's infrastructure.  

### Sound

Play a custom sound effect, when notification pops up.


## Demo

[streamer_donation_wallet_demo.webm](https://github.com/SNeedlewoods/xmr_tx_notify/assets/43108541/cfed23bf-c040-4eec-8f5c-c4f1046e1b8e)


## Supported OSs

* Should work on most ubuntu-like systems.
* Windows 10


## Dependencies

* Get the latest [monero release](https://github.com/monero-project/monero/releases) (v0.18.3.3 at the time of writing this).

### Linux:
* Python
  * install `pip3 install pygame pysocks`
* Command line tools:
  * install with `sudo apt install notify-send wmctrl xdotool xprop`
  * optional to be able to use `launch_script_linux.sh` install `sudo apt install tmux`

### Windows:

* Python
  * install `pip3 install requests pygame pysocks pywin32`


## Installation

```
git clone https://github.com/SNeedlewoods/xmr_tx_notify
```

Create a new Monero wallet, if you don't already have a wallet you want to use for this.  
It's recommended to use a view-only wallet, this application does not check the actual balance, so there are no downsides.


## Config

Small overview of the most important settings:

### Config [xmr_tx_notify.py](xmr_tx_notify.py)

* Set `IS_FANCY_NOTIFY`:
  * `True` (default): Uses dependencies for notification.
  * `False`: Uses system level notification.
* Set `MODE`:
  * `MODE_DONATION` (default): Uses a [message receiver](#message-receiver) (and in some cases default messages).
  * `MODE_NOTIFICATION`: Uses default messages.
* Set default messages:
    * `DEFAULT_NOTIFICATION_NAME`
    * `NOTIFICATION_PREFIX`
    * `DEFAULT_NOTIFICATION_MESSAGE`
* RPC Settings:
  * These need to match the settings you use to launch `monero-wallet-rpc` (see [Usage](#usage))
    * `RPC_PORT`
    * `RPC_LOGIN_USERNAME`
    * `RPC_LOGIN_PASSWORD`
* Set window position and notification pop-up display size (default is top left corner of screen 1 with size 600x300 pixels)
  * `WINDOW_POS_X`, `WINDOW_POS_Y`, `WINDOW_WIDTH`, `WINDOW_HEIGHT`
* If you want to change the background image, or sound you can put the new files into `assets/` and make sure the names match.

### Config [irc_bot.py](irc_bot.py)

* Set IRC network:
  * `IRC_SERVER`
  * `IRC_PORT`
* Set IRC user:
  * `IRC_PASSWORD`
  * `IRC_BOTNICK`
  * `IRC_CHANNEL`
* Set `USE_PROXY`:
  * `True` (default): Uses tor browser proxy (127.0.0.1:9150).
  * `False`: Use this if you don't want to use tor.

For Tor:  
Open the Tor browser and connect to the tor network before you launch `xmr_tx_notify.py`.

### Config [launch_script_linux.sh](launch_script_linux.sh)

Using this script is optional, change settings to the same that you would use in [Usage](#usage).


## Usage

1. Launch monerod (with your usual settings)

```
cd <path_to_monerod>
./monerod
```

2. Launch wallet rpc

```
cd <path_to_monero-wallet-rpc>
./monero-wallet-rpc --wallet-file <path_to_wallet>/<wallet_file> --password '<password>' --rpc-bind-port <RPC_PORT> --rpc-login <RPC_LOGIN_USERNAME>:<RPC_LOGIN_PASSWORD>
```

These need to match the settings you used to create the (view-only) wallet:  
`--wallet-file`  
`--password`  
These need to match the settings from [config](#config-xmr_tx_notifypy):  
`--rpc-bind-port` (default: 18099)  
`--rpc-login` (default: notification_wallet:password)


3. Launch main application

```
python3 xmr_tx_notify.py
```

### Quick start (Linux only)

If you have `tmux` installed and [configured launch_srcipt](#config_launch_script.sh):

```
./launch_script_linux.sh
```

Then wait until `monero-wallet-rpc` is running and press enter (fingers crossed, everything should work).


## Disclaimer

This was written by a noob in many subjects that this application touches and my initial intention was just to get a proof of concept. It is not reviewed by anyone ~~with experience or expertise~~. So use it at you own risk (if you're using a view-only wallet for the `monero-wallet-rpc`, there shouldn't be too much risk though AFAIK (don't quote me on this)). Don't sue me pls :)


## TODO

### General

* Add a `min_amount` for a tx to be displayed, to prevent getting spammed with messages.

### Considerations

#### MessageReceiver
* IRC-Bot
  * Add feature to IRC-Bot to respond to private messages.
    * At least if a possible \<tx_id\>:\<message\> pair is detected, so the donator/message sender knows the bot isn't dead.
  * consider adding commands like:
    * help - show what bot can do (and how)
* Alternatives:
  * Twitch / YouTube / etc. bot, directly on the platform where streamer is streaming (probably best user experience from donator perspective).
  * Email (not sure about this one)


#### General
* Trust modes
  * `trust_mode` (current default)
    * Just show the notification pop-up with the message.
    * Works with one screen.
  * `no_trust_mode`
    * First show the message on another (not live streamed) screen. Then, depending on the content you can decide to:
        * decline and
          * don't show a notification at all.
          * show a notification, but don't show the message (could use default for that).
        * accept and make it appear on the shared screen.

* Add the option to remember top donators and display them on screen
  * either short-term per stream in memory
  * or long-term all-time in a persistent file


