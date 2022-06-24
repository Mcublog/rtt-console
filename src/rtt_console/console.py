#!/usr/bin/env python

import argparse
import functools
import os
import time
from queue import Queue
from threading import Event, Thread
from typing import Callable, Union

from colorama import Fore as Clr
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import patch_stdout

from rtt_console.default_command import CONSOLE_COMMANDS, ConsoleCmd
from rtt_console.jlink_dongle import JLinkDongle, JLinkDongleException
from rtt_console.version import VERSION

DESCRIPTION = f'RTT Console {Clr.GREEN}v{VERSION}{Clr.RESET}'
CHIP_NAME_DEFAULT = 'STM32F407VE'

cmd_queue = Queue()
completer = WordCompleter(list(CONSOLE_COMMANDS))

JLinkIsBroken = False
JLinkCmdSuccess = True

ENDLINE = "\n"

def exception_handling(func: Callable):

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except JLinkDongleException as e:
            print(e)
            if func.__name__ == "reconnect":
                time.sleep(1)
            return JLinkIsBroken

    return wrap


@exception_handling
def connect(jlink: JLinkDongle) -> bool:
    jlink.connect()
    return JLinkCmdSuccess


@exception_handling
def reconnect(jlink: JLinkDongle) -> bool:
    jlink.reconnect()
    return JLinkCmdSuccess


@exception_handling
def write_cmd(jlink: JLinkDongle, cmd: str) -> bool:
    jlink.write_rtt_sring(f"{cmd}{ENDLINE}")
    return JLinkCmdSuccess


@exception_handling
def read_data(jlink: JLinkDongle) -> Union[str, bool]:
    return jlink.read_rtt_string(0)

@exception_handling
def reset_target(jlink: JLinkDongle) -> bool:
    jlink.reset_target()
    return JLinkCmdSuccess

@exception_handling
def power_on(jlink: JLinkDongle, on:bool) -> bool:
    jlink.power_on(on)
    return JLinkCmdSuccess


def reading_input(kill_evt: Event):
    session = PromptSession()
    input_cmd_string = ""
    while not kill_evt.wait(0.01):
        with patch_stdout(raw=True):
            try:
                input_cmd_string = session.prompt("> ", auto_suggest=AutoSuggestFromHistory(), completer=completer)
            except KeyboardInterrupt:
                print(f"Exit from: {DESCRIPTION}")
                break
            cmd_queue.put(input_cmd_string)
    kill_evt.set()


def main():
    parser = argparse.ArgumentParser(prog='console', description=DESCRIPTION)
    parser.add_argument(f'-t',
                        '--target',
                        type=str,
                        help=f'Target chip name (example: {CHIP_NAME_DEFAULT})',
                        default=CHIP_NAME_DEFAULT)

    parser.add_argument(f'-s', '--speed', type=int, help='Target speed (default: auto)', required=False, default=0)
    parser.add_argument('-p', '--path', type=str, help='Path to JLink DLL', required=False, default="")
    parser.add_argument('-pwr',
                        '--power',
                        help='Power on target by JLink',
                        required=False,
                        default=False)

    args = parser.parse_args()
    args.speed = 'auto' if args.speed == 0 else args.speed
    jlink = JLinkDongle(chip_name=args.target, speed=args.speed, dll_path=args.path, pwr_target=args.power)
    jlink_broken = connect(jlink)

    kill_evt = Event()
    input: Thread = Thread(target=reading_input, args=([kill_evt]), daemon=True)
    input.start()

    while not kill_evt.wait(0.01):
        # Try to reconnect to JLink
        if jlink_broken == JLinkIsBroken:
            jlink_broken = reconnect(jlink)
        # Read data from console input queue
        if not cmd_queue.empty():
            cmd = cmd_queue.get_nowait()
            if cmd == ConsoleCmd.RESET.value:
                jlink_broken = reset_target(jlink)
            elif cmd == ConsoleCmd.RECONNECT.value:
                jlink_broken = JLinkIsBroken
            elif cmd in {ConsoleCmd.POWER_ON.value, ConsoleCmd.POWER_OFF.value}:
                power_on(jlink, True if "on" in cmd else False)
            elif cmd == ConsoleCmd.CLEAR.value:
                os.system('cls' if os.name=='nt' else 'clear')
            else:
                jlink_broken = write_cmd(jlink, cmd)
        # Read data from JLink
        if rx_data := read_data(jlink):
            print(rx_data, end="")
        elif rx_data == JLinkIsBroken:
            jlink_broken = JLinkIsBroken


if __name__ == "__main__":
    main()
