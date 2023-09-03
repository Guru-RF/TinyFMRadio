import time
import board
import busio
import supervisor
from adafruit_bus_device.i2c_device import I2CDevice
import tinkeringtech_rda5807m
import displayio
import terminalio
import adafruit_displayio_ssd1306
from simpleio import map_range
from adafruit_bitmap_font import bitmap_font
from adafruit_progressbar import HorizontalProgressBar
from adafruit_display_text.label import Label
from digitalio import DigitalInOut, Direction, Pull


# Display
displayio.release_displays()

presets = [  # Preset stations
    10210,
    9510,
    9070,
    9950,
    10100,
    10110,
    10650
]

i_sidx = 0  # Starting at station with index 3

# Initialize i2c bus
# If your board does not have STEMMA_I2C(), change as appropriate.
i2c = busio.I2C(scl=board.GP19, sda=board.GP18)
i2c2 = busio.I2C(scl=board.GP21, sda=board.GP20)

# Receiver i2c communication
address = 0x11
vol = 3  # Default volume
band = "FM"

rds = tinkeringtech_rda5807m.RDSParser()

# Display initialization
toggle_frequency = (
    5  # Frequency at which the text changes between radio frequnecy and rds in seconds
)

rdstext = "No rds data"

# RDS text handle
def textHandle(rdsText):
    global rdstext
    rdstext = rdsText
    print(rdsText)


rds.attach_text_callback(textHandle)

# Initialize the radio classes for use.
radio_i2c = I2CDevice(i2c, address)
radio = tinkeringtech_rda5807m.Radio(radio_i2c, rds, presets[i_sidx], vol)
radio.set_band(band)  # Minimum frequency - 87 Mhz, max - 108 Mhz

# oled
display_bus = displayio.I2CDisplay(i2c2, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64, rotation=180)
display.brightness = 0.01

# Read input from serial
def serial_read():
    if supervisor.runtime.serial_bytes_available:
        command = input()
        command = command.split(" ")
        cmd = command[0]
        if cmd == "f":
            value = command[1]
            runSerialCommand(cmd, int(value))
        else:
            runSerialCommand(cmd)
        time.sleep(0.3)
        print("-> ", end="")


def runSerialCommand(cmd, value=0):
    # Executes a command
    # Starts with a character, and optionally followed by an integer, if required
    global i_sidx
    if cmd == "?":
        print(
            """\
? help
+ increase volume
- decrease volume
> next preset
< previous preset
. scan up
, scan down
f direct frequency input; e.g., 99.50 MHz is f 9950, 101.10 MHz is f 10110
i station statuss mono/stereo mode
b bass boost
u mute/unmute
r get rssi data
e softreset chip
q stops the program"""
        )

    # Volume and audio control
    elif cmd == "+":
        v = radio.volume
        if v < 15:
            radio.set_volume(v + 1)
    elif cmd == "-":
        v = radio.volume
        if v > 0:
            radio.set_volume(v - 1)

    # Toggle mute mode
    elif cmd == "u":
        radio.set_mute(not radio.mute)
    # Toggle stereo mode
    elif cmd == "s":
        radio.set_mono(not radio.mono)
    # Toggle bass boost
    elif cmd == "b":
        radio.set_bass_boost(not radio.bass_boost)

    # Frequency control
    elif cmd == ">":
        # Goes to the next preset station
        if i_sidx < (len(presets) - 1):
            i_sidx = i_sidx + 1
            radio.set_freq(presets[i_sidx])
    elif cmd == "<":
        # Goes to the previous preset station
        if i_sidx > 0:
            i_sidx = i_sidx - 1
            radio.set_freq(presets[i_sidx])

    # Set frequency
    elif cmd == "f":
        radio.set_freq(value)

    # Seek up/down
    elif cmd == ".":
        radio.seek_up()
    elif cmd == ",":
        radio.seek_down()

    # Display current signal strength
    elif cmd == "r":
        print("RSSI:", radio.get_rssi())

    # Soft reset chip
    elif cmd == "e":
        radio.soft_reset()

    # Not in help
    elif cmd == "!":
        radio.term()

    elif cmd == "i":
        # Display chip info
        s = radio.format_freq()
        print("Station: ", s)
        print("Radio info:")
        print("RDS ->", radio.rds)
        print("TUNED ->", radio.tuned)
        print("STEREO ->", not radio.mono)
        print("Audio info:")
        print("BASS ->", radio.bass_boost)
        print("MUTE ->", radio.mute)
        print("SOFTMUTE ->", radio.soft_mute)
        print("VOLUME ->", radio.volume)


print_rds = False
runSerialCommand("?", 0)

print("-> ", end="")

while True:
    serial_read()
    radio.check_rds()
    new_time = time.monotonic()
    serial_read()
