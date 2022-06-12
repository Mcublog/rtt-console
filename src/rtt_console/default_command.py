from enum import Enum


class ConsoleCmd(Enum):
    # HELP = 'help'
    RECONNECT = 'reconnect'
    RESET = 'reset'
    POWER_ON = 'power_on'
    POWER_OFF =  'power_off'

CONSOLE_COMMANDS = {cmd.value for cmd in ConsoleCmd}
