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
i2c = busio.I2C(scl=board.GP19, sda=board.GP18)
i2c2 = busio.I2C(scl=board.GP21, sda=board.GP20)

# Receiver i2c communication
address = 0x11
radio_i2c = I2CDevice(i2c, address)

vol = 100  # Default volume
band = "FM"

rds = tinkeringtech_rda5807m.RDSParser()
radio = tinkeringtech_rda5807m.Radio(radio_i2c, rds, presets[i_sidx], vol)
radio.set_band(band)  # Minimum frequency - 87 Mhz, max - 108 Mhz

# Display initialization
initial_time = time.monotonic()  # Initial time - used for timing
toggle_frequency = 5  # Frequency at which the text changes between radio frequnecy and rds in seconds

display_bus = displayio.I2CDisplay(i2c2, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64, rotation=180)
display.brightness = 0.01

rdstext = "No rds data"


def drawText(text):
    # Write text on display
    global display
    # Make the display context
    splash = displayio.Group()
    display.show(splash)

    color_bitmap = displayio.Bitmap(128, 32, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0x000000  # Black

    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
    splash.append(bg_sprite)

    # Split text into two lines
    temp = text.split(" ")
    line1 = temp[0]
    line2 = " ".join(temp[1:])
    # Check that lines are not empty
    if not line1.strip() or not line2.strip():
        warning = "Unclear rds data"
        text_area_1 = Label(terminalio.FONT, text=warning, color=0xFFFF00, x=5, y=5)
        splash.append(text_area_1)
    else:
        # Line 1
        text_area_1 = Label(terminalio.FONT, text=line1, color=0xFFFF00, x=5, y=5)
        splash.append(text_area_1)
        # Line 2
        text_area_2 = Label(terminalio.FONT, text=line2, color=0xFFFF00, x=5, y=20)
        splash.append(text_area_2)


# RDS text handle
def textHandle(rdsText):
    global rdstext
    rdstext = rdsText
    print(rdsText)
rds.attach_text_callback(textHandle)


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
    global presets
    if cmd == "?":
        print("? help")
        print("+ increase volume")
        print("- decrease volume")
        print("> next preset")
        print("< previous preset")
        print(". scan up ")
        print(", scan down ")
        print("f direct frequency input")
        print("i station status")
        print("s mono/stereo mode")
        print("b bass boost")
        print("u mute/unmute")
        print("r get rssi data")
        print("e softreset chip")
        print("q stops the program")

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
        radio.set_bassboost(not radio.bassBoost)

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
        print("RSSI: " + str(radio.get_rssi()))

    # Soft reset chip
    elif cmd == "e":
        radio.soft_reset()

    # Not in help
    elif cmd == "!":
        radio.term()

    elif cmd == "i":
        # Display chip info
        s = radio.format_freq()
        print("Station: " + s)
        print("Radio info: ")
        print("RDS -> " + str(radio.rds))
        print("TUNED -> " + str(radio.tuned))
        print("STEREO -> " + str(not radio.mono))
        print("Audio info: ")
        print("BASS -> " + str(radio.bass_boost))
        print("MUTE -> " + str(radio.mute))
        print("SOFTMUTE -> " + str(radio.soft_mute))
        print("VOLUME -> " + str(radio.volume))


print_rds = False
radio.sendRDS = rds.process_data
runSerialCommand("?", 0)

print("-> ", end="")

while True:
        serial_read()
        #radio.checkRDS()
        new_time = time.monotonic()
        if (new_time - initial_time) > toggle_frequency:
            print_rds = not print_rds
            if print_rds:
                if rdstext == "":
                    drawText("No rds data")
                else:
                    if len(rdstext.split(" ")) > 1:
                        drawText(rdstext)
                    else:
                        drawText("Unclear rds data")
            else:
                drawText(radio.format_freq())
            initial_time = new_time
