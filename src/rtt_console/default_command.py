from enum import Enum


class ConsoleCmd(Enum):
    # HELP = 'help'
    RECONNECT = 'reconnect'
    RESET = 'reset'
    POWER_ON = 'power_on'
    POWER_OFF = 'power_off'
    CLEAR = "clear"

    def _missing_(self, value:str):
        if not isinstance(value, str):
            return None
        return value

CONSOLE_COMMANDS = {cmd.value for cmd in ConsoleCmd}
