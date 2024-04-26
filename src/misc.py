IS_DEBUG =  False

# Converts from atomic units (piconero) to rounded str in Monero.
def amt2str(amount : int):
    return f"{amount/10**12:9.5f}"


# Print message.
def printm(pre : str, msg : str):
    print(f"[*] MSG [{pre}]: {msg}")

# Print error message.
def printe(pre : str, msg : str):
    print(f"[-] ERR [{pre}]: {msg}")
    exit(-1)

# Print warning message.
def printw(pre : str, msg : str):
    print(f"[/] WRN [{pre}]: {msg}")

# Print debug message, if debug is enabled.
def printd(pre : str, msg : str):
    if IS_DEBUG:
        print(f"[#] DBG [{pre}]: {msg}")


