import functools
from dataclasses import dataclass, field
from typing import Union

from colorama import Fore as Clr
from pylink import JLink, JLinkException, JLinkInterfaces, library

CHIP_NAME_DEFAULT = 'STM32F407VE'
DEFAULT_BUFFER_INDEX = 0

class JLinkDongleException(Exception):

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

@dataclass
class JLinkDongle:
    interface:JLinkInterfaces = JLinkInterfaces.SWD  # type: ignore
    speed:Union[str,int] = 'auto'
    chip_name:str = CHIP_NAME_DEFAULT
    jlink:JLink = field(init=False)
    dll_path:str = ""
    pwr_target:bool = False

    def check_exception(func): # type: ignore
        @functools.wraps(func)  # type: ignore
        def wrap(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)  # type: ignore
            except JLinkException as e:
                if func.__name__ in {self.read_rtt.__name__, self.write_rtt.__name__}:  # type: ignore
                    raise JLinkDongleException(f"Do not read/write from RTT Terminal")
                raise JLinkDongleException(
                    f"{Clr.RED}ERROR:{Clr.RESET} method name: {Clr.YELLOW}{func.__name__}{Clr.RESET} : {e}")  # type: ignore
        return wrap

    @check_exception # type: ignore
    def connect(self):
        jlinkdll = None
        if self.dll_path:
            jlinkdll = library.Library()
            try:
                print(f"Using path to DLL: {self.dll_path}")
                jlinkdll.load(self.dll_path)
            except:
                print(f"ERROR: check path: {self.dll_path}")
                return
        self.jlink = JLink(lib=jlinkdll)
        self.jlink.disable_dialog_boxes()
        self.jlink.open()
        self.jlink.power_on() if self.pwr_target else self.jlink.power_off()
        self.jlink.rtt_stop()
        self.jlink.set_tif(JLinkInterfaces.SWD)
        self.jlink.connect(chip_name=self.chip_name, speed=self.speed, verbose=True) # type: ignore
        self.jlink.rtt_start()
        endian = int.from_bytes(self.jlink._device.EndianMode, 'big') # type: ignore
        endian = {0: "Little", 1: "Big"}.get(endian, f"Unknown ({endian})")
        print("\n" + "=" * 10)
        print(f"Connected to: {self.chip_name}")
        print(f"RTT RX buffers at {self.jlink.speed} kHz")
        print(f"Connected to {endian}-Endian {self.jlink.core_name()}")
        print(f"Running at {self.jlink.cpu_speed() / 1e6:.3f} MHz", end="\n" + "=" * 10 + "\n")
        return True


    @check_exception # type: ignore
    def read_rtt(self, terminal_number:int = DEFAULT_BUFFER_INDEX) -> list:
        try:
            return self.jlink.rtt_read(terminal_number, self.jlink.MAX_BUF_SIZE)
        except ValueError as e:
            print(f"Reading exception: {e}")
            raise JLinkDongleException(f"Do not read/write from RTT Terminal")

    @check_exception # type: ignore
    def write_rtt(self, data: bytes, terminal_number: int = DEFAULT_BUFFER_INDEX) -> None:
        cnt = self.jlink.rtt_write(terminal_number, data)
        while cnt < len(data):
            if cnt == 0:
                break
            cnt += self.jlink.rtt_write(terminal_number, data[cnt:])
        if cnt == 0 or cnt != len(data):
            print(f"Write error: sent {cnt} from {len(data)} bytes")

    def read_rtt_string(self, terminal_number: int = DEFAULT_BUFFER_INDEX) -> str:
        data = self.read_rtt(terminal_number=terminal_number)
        if data:
            try:
                return bytes(data).decode('utf-8')
            except:
                print(f"Do not decode: {data}")
                return ""
        return ""

    def write_rtt_sring(self, data: str, terminal_number: int = DEFAULT_BUFFER_INDEX) -> None:
        self.write_rtt(str.encode(data, 'utf-8'), terminal_number)

    @check_exception # type: ignore
    def reconnect(self):
        self.jlink.close()
        self.connect()

    @check_exception # type: ignore
    def reset_target(self):
        self.jlink.reset(ms=10, halt=False)

    @check_exception # type: ignore
    def power_on(self, on: bool) -> None:
        self.pwr_target = on
        self.jlink.power_on() if on else self.jlink.power_off()
