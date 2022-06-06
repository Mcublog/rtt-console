#!/usr/bin/env python

import argparse
import functools
import time
from queue import Queue
from threading import Event, Thread
from typing import Callable

from colorama import Fore as Clr
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.patch_stdout import patch_stdout

from rtt_console.jlink_dongle import JLinkDongle, JLinkDongleException
from rtt_console.version import VERSION

DESCRIPTION = f'RTT Console {Clr.GREEN}v{VERSION}{Clr.RESET}'
CHIP_NAME_DEFAULT = 'STM32F407VE'

cmd_queue = Queue()


def exception_handling(func: Callable):

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except JLinkDongleException as e:
            print(e)
            return False

    return wrap


@exception_handling
def connect(jlink: JLinkDongle) -> bool:
    jlink.connect()
    return True


@exception_handling
def reconnect(jlink: JLinkDongle) -> bool:
    jlink.reconnect()
    return True


@exception_handling
def write_cmd(jlink: JLinkDongle, cmd: str) -> bool:
    jlink.write_rtt_sring(cmd + "\n")
    return True


@exception_handling
def read_data(jlink: JLinkDongle) -> str | bool:
    return jlink.read_rtt_string(0)

@exception_handling
def reset_target(jlink: JLinkDongle) -> bool:
    jlink.reset_target()
    return True


HELP_CMD = {'help', 'h'}
RECONNECT_CMD = {'reconnect', 'r'}
RESET_CMD = {'reset', 'rst'}

def conole_read_input(kill_evt: Event):
    session = PromptSession()
    input_cmd_string = ""
    while not kill_evt.wait(0.01):
        with patch_stdout(raw=True):
            try:
                input_cmd_string = session.prompt("> ", auto_suggest=AutoSuggestFromHistory())
            except KeyboardInterrupt as e:
                print(e)
                kill_evt.set()
                return
            cmd_queue.put(input_cmd_string)


def main():
    parser = argparse.ArgumentParser(prog='console', description=DESCRIPTION)
    parser.add_argument(f'-t',
                        '--target',
                        type=str,
                        help=f'Target chip name (example: {CHIP_NAME_DEFAULT})',
                        required=True)

    parser.add_argument(f'-s', '--speed', type=int, help='Target speed (default: auto)', required=False, default=0)
    args = parser.parse_args()

    try_to_reconnect = False
    if args.speed == 0:
        args.speed = 'auto'
    jlink = JLinkDongle(chip_name=args.target, speed=args.speed)
    if connect(jlink) == False:
        return
    kill_evt = Event()
    input: Thread = Thread(target=conole_read_input, args=([kill_evt]), daemon=True)
    input.start()
    while not kill_evt.wait(0.01):
        if try_to_reconnect:
            try_to_reconnect = False if reconnect(jlink) else True
            time.sleep(1)
            continue
        if not cmd_queue.empty():
            cmd = cmd_queue.get()
            if cmd in RECONNECT_CMD:
                try_to_reconnect = True
            elif cmd in RESET_CMD:
                try_to_reconnect = not reset_target(jlink)
            else:
                try_to_reconnect = not write_cmd(jlink, cmd)
        rx_data = read_data(jlink)
        if rx_data:
            print(rx_data, end="")
        if rx_data == False:
            try_to_reconnect = True


if __name__ == "__main__":
    main()
