import time
from threading import Thread

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.patch_stdout import patch_stdout
from pylink import JLink, JLinkInterfaces, JLinkRTTException

CHIP_NAME = 'STM32F407VE'

def main():
    jlink = JLink()
    # jlink.disable_dialog_boxes()
    jlink.open()
    jlink.set_tif(JLinkInterfaces.SWD)
    jlink.connect(chip_name=CHIP_NAME.lower(), speed='auto', verbose=True)
    jlink.rtt_start()
    jlink_rtt_num_rx_buffers = 0
    for _ in range(20):
        try:
            jlink_rtt_num_rx_buffers = jlink.rtt_get_num_up_buffers()
            break
        except JLinkRTTException as e:
            if "The RTT Control Block has not yet been found" in str(e):
                time.sleep(0.1)
            else:
                raise e
    endian = int(jlink._device.EndianMode[0])
    endian = {0: "Little", 1: "Big"}.get(endian, f"Unknown ({endian})")
    print(f"RTT (using {jlink_rtt_num_rx_buffers} RX buffers at {jlink.speed} kHz)"
          f" connected to {endian}-Endian {jlink.core_name()}"
          f" running at {jlink.cpu_speed() / 1e6:.3f} MHz")

    Thread(target=reading_rtt, args=([jlink])).start()
    session = PromptSession()
    print(f"ENTER COMMAND '?' -HELP")
    while True:
        # Try reading all buffers until some data is available
        # for i in range(jlink_rtt_num_rx_buffers):
        with patch_stdout(raw=True):
            input_cmd_string = session.prompt("> ", auto_suggest=AutoSuggestFromHistory())
            print(input_cmd_string)


def reading_rtt(jlink:JLink):
    while True:
        rx_data = jlink.rtt_read(0, jlink.MAX_BUF_SIZE)
        if rx_data:
            print(bytes(rx_data).decode('utf-8'))
        time.sleep(0.01)


if __name__ == "__main__":
    main()
