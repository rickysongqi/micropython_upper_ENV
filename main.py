# main.py
# Application to manage Wi-Fi, BLE, Keypad, LCD (ST7789),
# I2C Sensors, I2S Mic, WS2812 LEDs, and Multi-Page UI.
# --- VERSION WITH MULTI-PAGE UI ---

import gc
import time
import network
import struct
import math
from machine import Pin, SPI, I2C, I2S, SoftSPI
import socket
import json
import ubinascii # Needed for BLE address formatting
from micropython import const

try:
    import webrepl
except ImportError:
    print("Warning: webrepl module not found. WebREPL disabled.")
    webrepl = None

try:
    import neopixel
except ImportError:
    print("Error: neopixel library not found. WS2812 functions disabled.")
    neopixel = None

# --- 1. Import necessary driver/font modules ---
# (Existing imports remain the same)
try:
    import bluetooth
except ImportError:
    print("CRITICAL: Failed to import 'bluetooth' module.")
    bluetooth = None
try:
    import st7789
except ImportError:
    print("Error: ST7789 driver (st7789.py) not found.")
    st7789 = None
try:
    import si7021
except ImportError:
    print("Error: SI7021 driver (si7021.py) not found.")
    si7021 = None
try:
    import bh1750
except ImportError:
    print("Error: BH1750 driver (bh1750.py) not found.")
    bh1750 = None
try:
    import ubuntu_24 as default_font
except ImportError:
    print("Error: Converted font module ('ubuntu_24.py') not found.")
    default_font = None


# --- 2. Define constants and configuration ---
I2S_DEBUG_VERBOSE = True
WIFI_SSID = "Redmi_1D4E" # Keep your SSID
WIFI_PASSWORD = "12340000" # Keep your Password
BLE_DEVICE_NAME = "ESP32S3_Sensor"
SERVER_PORT = 8888 # <<< Define the server port

# Hardware Pins
KEY_UP_PIN = 2
KEY_DOWN_PIN = 41
KEY_LEFT_PIN = 40
KEY_RIGHT_PIN = 1
KEY_ENTER_PIN = 42
NEOPIXEL_PIN = 18
NUM_LEDS = 4
LCD_SPI_ID = 2
LCD_SCLK_PIN = 12
LCD_MOSI_PIN = 11
LCD_MISO_PIN = -1
LCD_CS_PIN = 3
LCD_DC_PIN = 46
LCD_RST_PIN = 9
LCD_BL_PIN = 8
LCD_WIDTH = 240
LCD_HEIGHT = 320
LCD_ROTATION = 2
LCD_SPI_BAUDRATE = 40000000
I2C_ID = 0
I2C_SCL_PIN = 39
I2C_SDA_PIN = 38
I2C_FREQ = 400000
SI7021_ADDR = 0x40
BH1750_ADDR = 0x23
I2S_ID = 0
I2S_BCLK_PIN = 17
I2S_WS_PIN = 16
I2S_DIN_PIN = 15
I2S_SAMPLE_RATE = 16000
I2S_BITS = 16
I2S_FORMAT = I2S.MONO
I2S_BUFFER_LEN_IN_BYTES = 4096
I2S_READ_CHUNK_SIZE = 512
I2S_ENDIANNESS = '<'

# --- UI Page Configuration ---
NUM_PAGES = 2
PAGE_MAIN = 0
PAGE_NETWORK = 1

# --- UI Layout and Style Constants ---
COLOR_BG = st7789.BLACK if st7789 else 0x0000
COLOR_FG = st7789.WHITE if st7789 else 0xFFFF
COLOR_LABEL = st7789.CYAN if st7789 else 0x07FF
COLOR_VALUE = st7789.WHITE if st7789 else 0xFFFF
COLOR_SEPARATOR = st7789.BLUE if st7789 else 0x001F
COLOR_STATUS_OK = st7789.GREEN if st7789 else 0x07E0
COLOR_STATUS_WARN = st7789.YELLOW if st7789 else 0xFFE0
COLOR_STATUS_BAD = st7789.RED if st7789 else 0xF800
COLOR_MEM = st7789.GREEN if st7789 else 0x07E0
COLOR_TITLE = st7789.YELLOW if st7789 else 0xFFE0
COLOR_PAGE_INDICATOR = st7789.MAGENTA if st7789 else 0xF81F

PADDING = 5
FONT_HEIGHT = default_font.HEIGHT if default_font else 24

# Page Indicator Position (Common to all pages)
X_PAGE_INDICATOR = LCD_WIDTH - 45 # Position near top right
Y_PAGE_INDICATOR = PADDING

# -- Layout Page 0: Main Sensors --
Y_STATUS_LINE_P0 = PADDING
X_WIFI_STATUS_P0 = PADDING
X_BLE_STATUS_P0 = 80
# IP Label removed from status bar, moved to Page 1
Y_SEPARATOR_1_P0 = Y_STATUS_LINE_P0 + FONT_HEIGHT + PADDING
Y_SENSOR_ROW_1_P0 = Y_SEPARATOR_1_P0 + PADDING + 5
X_TEMP_LABEL_P0 = PADDING
X_TEMP_VALUE_P0 = 45
X_HUM_LABEL_P0 = 120
X_HUM_VALUE_P0 = 165
Y_SENSOR_ROW_2_P0 = Y_SENSOR_ROW_1_P0 + FONT_HEIGHT + PADDING + 10
X_LUX_LABEL_P0 = PADDING
X_LUX_VALUE_P0 = 60
X_NOISE_LABEL_P0 = 120
X_NOISE_VALUE_P0 = 190
Y_SEPARATOR_2_P0 = Y_SENSOR_ROW_2_P0 + FONT_HEIGHT + PADDING + 5
Y_BOTTOM_ROW_1_P0 = Y_SEPARATOR_2_P0 + PADDING + 5
X_KEYS_LABEL_P0 = PADDING
X_KEYS_VALUE_P0 = 70
Y_BOTTOM_ROW_2_P0 = Y_BOTTOM_ROW_1_P0 + FONT_HEIGHT + PADDING
X_MEM_LABEL_P0 = PADDING
X_MEM_VALUE_P0 = 70

# -- Layout Page 1: Network Details --
Y_TITLE_P1 = PADDING + 5
X_TITLE_P1 = PADDING
Y_WIFI_ICON_P1 = Y_TITLE_P1 + FONT_HEIGHT + PADDING * 2
X_WIFI_ICON_P1 = PADDING
X_SSID_LABEL_P1 = X_WIFI_ICON_P1 + 30 # Space after icon
Y_SSID_P1 = Y_WIFI_ICON_P1
X_SSID_VALUE_P1 = X_SSID_LABEL_P1 + 70 # Align value start
Y_IP_P1 = Y_SSID_P1 + FONT_HEIGHT + PADDING
X_IP_LABEL_P1 = X_SSID_LABEL_P1
X_IP_VALUE_P1 = X_SSID_VALUE_P1
Y_MASK_P1 = Y_IP_P1 + FONT_HEIGHT + PADDING
X_MASK_LABEL_P1 = X_SSID_LABEL_P1
X_MASK_VALUE_P1 = X_SSID_VALUE_P1
Y_GW_P1 = Y_MASK_P1 + FONT_HEIGHT + PADDING
X_GW_LABEL_P1 = X_SSID_LABEL_P1
X_GW_VALUE_P1 = X_SSID_VALUE_P1

# --- LED Effect Configuration ---
# Increase update frequency for smoother perceived transitions
LED_UPDATE_INTERVAL_MS = 10 # From 20ms to 10ms (100 Hz)
# Increase speed for more obvious effect (try values like 1.2, 1.5, etc.)
BREATH_SPEED = 2 # Example speed
BREATH_COLOR_BASE = (180, 255, 180)
# Decrease minimum brightness to make the "dim" phase darker
BREATH_MIN_BRIGHTNESS = 0.05 # Example: Decreased from 0.15 to 0.05
# NEW: Define phase shift between adjacent LEDs (e.g., pi/2 for 4 LEDs gives a nice chase)
PHASE_SHIFT_PER_LED = math.pi / 2.0 # Adjust as needed (e.g., math.pi / NUM_LEDS)
# NEW: Gamma correction value (adjust slightly if needed, 2.2 is common)
GAMMA_VALUE = 2.2
ALERT_COLOR = (255, 0, 0)
ALERT_FLASH_ON_MS = 150
ALERT_FLASH_OFF_MS = 100
ALERT_TOTAL_FLASHES = 2

# --- Sensor Trigger Thresholds (Tune!) ---
TEMP_THRESHOLD_DIFF = 3.0
HUMI_THRESHOLD_DIFF = 15.0
LUX_THRESHOLD_DIFF = 500.0
RMS_THRESHOLD_DIFF = 1500.0

# --- Key Debounce ---
KEY_DEBOUNCE_MS = 200 # Prevent rapid page switching

# --- BLE UUIDs and Flags (Using standard Environmental Sensing Service where applicable) ---
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4) # Custom definition might be needed depending on MicroPython version

# Flags for characteristics
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

# Environmental Sensing Service UUID (Standard)
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# Standard Characteristic UUIDs (Examples)
_TEMP_CHAR_UUID = bluetooth.UUID(0x2A6E) # Temperature
_HUMID_CHAR_UUID = bluetooth.UUID(0x2A6F) # Humidity
# Custom Characteristic UUIDs (If standard ones aren't suitable or for others)
# Generate custom UUIDs using a tool like uuidgenerator.net
# Example: 128-bit UUID xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
_LUX_CHAR_UUID = bluetooth.UUID(0x2AFB)   # Illuminance (Standard)
# Custom UUID for Noise Level - Generate your own unique 128-bit UUID!
_NOISE_CHAR_UUID = bluetooth.UUID("8eb6184d-bec0-41b0-8eba-e350662524ff") 
# _KEYS_CHAR_UUID removed

# Define the structure of our Environmental Sensing Service
# (Service UUID, (Characteristic UUID, Flags, Optional Descriptors)... )
_ENV_SENSE_SERVICE = (
    _ENV_SENSE_UUID,
    (
        (_TEMP_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,), # Temperature Characteristic (Read + Notify)
        (_HUMID_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,), # Humidity Characteristic (Read + Notify)
        (_LUX_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,),   # Custom Lux Characteristic (Read + Notify)
        (_NOISE_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,), # Custom Noise Characteristic (Read + Notify)
    ),
)

# --- Global BLE State ---
ble_conn_handle = None
# Handles for our characteristics (filled during service registration)
ble_temp_handle = None
ble_humid_handle = None
ble_lux_handle = None
ble_noise_handle = None
# ble_keys_handle removed
ble_notify_enabled = { # Track notify state for each characteristic
    'temp': False, 'humid': False, 'lux': False, 'noise': False # Removed 'keys'
}

# --- Helper functions to pack sensor data according to BLE standards ---

def _pack_sint16_scaled(value, scale_factor=1, default_val=0x8000):
    """Packs a value into sint16 (little-endian), scaled. 0x8000 = N/A for sint16."""
    if value is None:
        return struct.pack('<h', default_val) # Use standard N/A value if possible
    try:
        scaled_val = int(float(value) * scale_factor)
        # Clamp to sint16 range
        scaled_val = max(-32768, min(32767, scaled_val))
        return struct.pack('<h', scaled_val)
    except Exception:
        return struct.pack('<h', default_val)

def _pack_uint16_scaled(value, scale_factor=1, default_val=0xFFFF):
    """Packs a value into uint16 (little-endian), scaled. 0xFFFF = N/A for uint16."""
    if value is None:
        return struct.pack('<H', default_val)
    try:
        scaled_val = int(float(value) * scale_factor)
        # Clamp to uint16 range
        scaled_val = max(0, min(65535, scaled_val))
        return struct.pack('<H', scaled_val)
    except Exception:
        return struct.pack('<H', default_val)

def _pack_uint24_scaled(value, scale_factor=1, default_val=0xFFFFFF):
    """Packs a value into uint24 (3 bytes, little-endian), scaled. 0xFFFFFF = N/A."""
    if value is None:
        # Create 3 bytes for N/A
        return default_val.to_bytes(3, 'little')
    try:
        scaled_val = int(float(value) * scale_factor)
        # Clamp to uint24 range
        scaled_val = max(0, min(16777215, scaled_val))
        return scaled_val.to_bytes(3, 'little')
    except Exception:
         return default_val.to_bytes(3, 'little')

# --- BLE IRQ Handler ---
def _ble_irq(event, data):
    global ble_conn_handle, ble_notify_enabled
    global ble_temp_handle, ble_humid_handle, ble_lux_handle, ble_noise_handle # Removed ble_keys_handle
    global current_temperature_val, current_humidity_val, current_lux_val, current_noise_rms # Removed current_pressed_key_names (it's still updated but not read via BLE IRQ now)

    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle, _, addr = data
        ble_conn_handle = conn_handle
        addr_str = ubinascii.hexlify(addr, ':').decode()
        print(f"BLE Connected: handle={conn_handle}, addr={addr_str}")
        # Reset notify flags on new connection
        for key in ble_notify_enabled: ble_notify_enabled[key] = False

    elif event == _IRQ_CENTRAL_DISCONNECT:
        conn_handle, _, _ = data
        if conn_handle == ble_conn_handle:
            print(f"BLE Disconnected: handle={conn_handle}")
            ble_conn_handle = None
            # Optionally stop advertising or keep advertising
            # advertise() # Restart advertising if needed

    elif event == _IRQ_GATTS_WRITE:
        conn_handle, attr_handle = data
        # This handles writes to the CCCD (Client Characteristic Configuration Descriptor)
        # which enable/disable notifications.
        # Check which characteristic's CCCD was written
        value = ble.gatts_read(attr_handle)
        notify_state = value[0] == 1 # 0x0001 for notifications enabled

        if attr_handle == ble_temp_handle + 1: # CCCD is usually handle + 1
             ble_notify_enabled['temp'] = notify_state
             print(f"BLE Temp Notify: {'Enabled' if notify_state else 'Disabled'}")
        elif attr_handle == ble_humid_handle + 1:
             ble_notify_enabled['humid'] = notify_state
             print(f"BLE Humid Notify: {'Enabled' if notify_state else 'Disabled'}")
        elif attr_handle == ble_lux_handle + 1:
             ble_notify_enabled['lux'] = notify_state
             print(f"BLE Lux Notify: {'Enabled' if notify_state else 'Disabled'}")
        elif attr_handle == ble_noise_handle + 1:
             ble_notify_enabled['noise'] = notify_state
             print(f"BLE Noise Notify: {'Enabled' if notify_state else 'Disabled'}")
        # elif attr_handle == ble_keys_handle + 1: # Removed keys handler
        #      ble_notify_enabled['keys'] = notify_state
        #      print(f"BLE Keys Notify: {'Enabled' if notify_state else 'Disabled'}")

    # Note: Read requests might not generate an IRQ in all MicroPython BLE stacks.
    # Some stacks handle reads directly based on gatts_write in the main loop or
    # require explicit read response in the IRQ handler.
    # The following is a common pattern if an IRQ *is* generated.
    elif event == _IRQ_GATTS_READ_REQUEST:
         conn_handle, attr_handle = data
         print(f"BLE Read Request: handle={conn_handle}, attr={attr_handle}")
         # Determine which characteristic is being read and provide the current value
         # The BLE stack might handle sending the data implicitly after this handler returns,
         # or you might need ble.gatts_read_rsp(). Consult your port's documentation.
         # For now, we assume the stack handles sending after we write the value.
         if attr_handle == ble_temp_handle:
             ble.gatts_write(ble_temp_handle, _pack_sint16_scaled(current_temperature_val if current_temperature_val > -990 else None, 100))
         elif attr_handle == ble_humid_handle:
             ble.gatts_write(ble_humid_handle, _pack_uint16_scaled(current_humidity_val if current_humidity_val > -990 else None, 100))
         elif attr_handle == ble_lux_handle:
              ble.gatts_write(ble_lux_handle, _pack_uint24_scaled(current_lux_val if current_lux_val > -990 else None, 100))
         elif attr_handle == ble_noise_handle:
              ble.gatts_write(ble_noise_handle, _pack_sint16_scaled(current_noise_rms if current_noise_rms >= 0 else None, 10))
         # elif attr_handle == ble_keys_handle: # Removed keys handler
         #      ble.gatts_write(ble_keys_handle, _pack_string(current_pressed_key_names))


# --- 3. Initialization Functions ---
# (Keep existing init functions: init_wifi, init_ble, init_keypad, init_i2c_sensors, init_display, init_i2s, calculate_rms)
# <<< Add your existing init functions here >>>
def init_wifi(ssid, password):
    """Initializes and connects to Wi-Fi."""
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print(f"Connecting to WiFi network '{ssid}'...")
        sta_if.active(True)
        try:
            sta_if.connect(ssid, password)
            # Wait for connection with a timeout
            max_wait = 15
            while max_wait > 0:
                if sta_if.isconnected():
                    break
                max_wait -= 1
                print(".", end="")
                time.sleep(1)

            if sta_if.isconnected():
                print("\nWiFi Connected!")
                print("Network config:", sta_if.ifconfig())
                return sta_if
            else:
                print("\nWiFi connection timed out.")
                sta_if.active(False) # Turn off if connection failed
                return None
        except OSError as e:
            print(f"\nError connecting to WiFi: {e}")
            sta_if.active(False)
            return None
    else:
        print("WiFi already connected.")
        return sta_if

def init_ble(device_name):
    """Initializes Bluetooth LE, registers services, and starts advertising."""
    global ble # Make ble instance global if needed
    global ble_temp_handle, ble_humid_handle, ble_lux_handle, ble_noise_handle # Removed ble_keys_handle

    if bluetooth is None:
        print("BLE init skipped: bluetooth module not available.")
        return None

    ble = bluetooth.BLE()
    if not ble.active():
        print("Activating Bluetooth...")
        try:
            ble.active(True)
        except Exception as e:
            print(f"Error activating BLE: {e}")
            return None

    print("Configuring BLE GATT services...")
    try:
        # Register the Environmental Sensing service and characteristics
        # Returns tuple of value handles
        handles = ble.gatts_register_services((_ENV_SENSE_SERVICE,))
        ble_temp_handle = handles[0][0]
        ble_humid_handle = handles[0][1]
        ble_lux_handle = handles[0][2]
        ble_noise_handle = handles[0][3]
        # ble_keys_handle = handles[0][4] # Removed
        print("GATT Service Registered:")
        print(f"  Temp Handle: {ble_temp_handle} (Standard: 0x2A6E)")
        print(f"  Humid Handle: {ble_humid_handle} (Standard: 0x2A6F)")
        print(f"  Lux Handle: {ble_lux_handle} (Standard: 0x2AFB)")
        print(f"  Noise Handle: {ble_noise_handle} (Custom: {_NOISE_CHAR_UUID})") # Print the correct custom UUID
    except Exception as e:
        print(f"Error registering GATT services: {e}")
        ble.active(False)
        return None

    # Set BLE IRQ handler *after* service registration
    ble.irq(_ble_irq)
    print("BLE IRQ handler set.")

    print("Configuring BLE advertisement...")
    # Advertise device name and the Environmental Sensing Service UUID
    adv_payload = bytearray()
    adv_payload.extend(b'\x02\x01\x06') # Flags: LE General Discoverable Mode
    # Service UUID List (16-bit) - Add _ENV_SENSE_UUID (0x181A)
    adv_payload.extend(b'\x03\x03\x1A\x18') # Length=3, Type=Complete list of 16-bit Service UUIDs, UUID=0x181A
    # Complete Local Name
    name_bytes = bytes(device_name, 'utf-8')
    adv_payload.extend(bytes([len(name_bytes) + 1, 0x09])) # Length, Type=Complete Local Name
    adv_payload.extend(name_bytes)

    interval_us = 100000 # 100ms interval
    try:
        ble.gap_advertise(interval_us, adv_data=adv_payload)
        print(f"BLE advertising started as '{device_name}' with ESS service.")
        return ble
    except Exception as e:
        print(f"Error starting BLE advertising: {e}")
        # Fallback might be needed if payload is too long
        try:
             print("Advertising fallback: name only")
             adv_payload_fallback = bytearray()
             adv_payload_fallback.extend(b'\x02\x01\x06')
             adv_payload_fallback.extend(bytes([len(name_bytes) + 1, 0x09]))
             adv_payload_fallback.extend(name_bytes)
             ble.gap_advertise(interval_us, adv_data=adv_payload_fallback)
             print("BLE advertising started (name only).")
             return ble
        except Exception as e_fb:
             print(f"Error starting fallback advertising: {e_fb}")
             ble.active(False)
             return None

def init_keypad():
    """Initializes keypad GPIO pins."""
    print("Initializing Keypad...")
    keys = {
        'up': Pin(KEY_UP_PIN, Pin.IN, Pin.PULL_UP),
        'down': Pin(KEY_DOWN_PIN, Pin.IN, Pin.PULL_UP),
        'left': Pin(KEY_LEFT_PIN, Pin.IN, Pin.PULL_UP),
        'right': Pin(KEY_RIGHT_PIN, Pin.IN, Pin.PULL_UP),
        'enter': Pin(KEY_ENTER_PIN, Pin.IN, Pin.PULL_UP)
    }
    print("Keypad initialized.")
    return keys

def init_i2c_sensors():
    """Initializes I2C bus and attempts to initialize sensors."""
    i2c = None
    sensor_th = None
    sensor_l = None
    print("Initializing I2C bus...")
    try:
        i2c = I2C(I2C_ID, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=I2C_FREQ)
        print(f"I2C Bus {I2C_ID} initialized.")
        devices = i2c.scan()
        print("Detected I2C devices:", [hex(d) for d in devices])

        # Initialize SI7021 if driver loaded and device detected
        if si7021 and SI7021_ADDR in devices:
            try:
                sensor_th = si7021.SI7021(i2c)
                print("SI7021 Temp/Hum sensor initialized.")
            except Exception as e:
                print(f"Error initializing SI7021 driver: {e}")
        elif si7021:
            print(f"SI7021 not found at address {hex(SI7021_ADDR)}")

        # Initialize BH1750 if driver loaded and device detected
        if bh1750 and BH1750_ADDR in devices:
            try:
                sensor_l = bh1750.BH1750(i2c)
                print("BH1750 Light sensor initialized.")
            except Exception as e:
                print(f"Error initializing BH1750 driver: {e}")
        elif bh1750:
                print(f"BH1750 not found at address {hex(BH1750_ADDR)}")

    except Exception as e:
        print(f"FATAL: Error initializing I2C Bus {I2C_ID}: {e}")
        i2c = None

    return i2c, sensor_th, sensor_l

def init_display():
    """Initializes SPI bus and ST7789 LCD."""
    global spi
    display_dev = None
    print("--- Starting Display Initialization ---")
    pin_rst = None; pin_dc = None; pin_cs = None; pin_bl = None
    try:
        pin_rst = Pin(LCD_RST_PIN, Pin.OUT) if LCD_RST_PIN is not None else None
        pin_dc = Pin(LCD_DC_PIN, Pin.OUT)
        pin_cs = Pin(LCD_CS_PIN, Pin.OUT) if LCD_CS_PIN is not None else None
        pin_bl = Pin(LCD_BL_PIN, Pin.OUT) if LCD_BL_PIN is not None else None
        if pin_bl: pin_bl.value(1)
    except Exception as e:
        print(f"FATAL: Error initializing CONTROL PINS: {e}")
        return None

    spi = None
    try:
        print(f"--> Attempting to init Hardware SPI ID: {LCD_SPI_ID}")
        spi = SPI(LCD_SPI_ID, baudrate=LCD_SPI_BAUDRATE,
                  sck=Pin(LCD_SCLK_PIN), mosi=Pin(LCD_MOSI_PIN),
                  miso=Pin(LCD_MISO_PIN) if LCD_MISO_PIN != -1 else None)
        print(f"  SUCCESS: Hardware SPI ID {LCD_SPI_ID} initialized OK.")
    except Exception as e_hw_spi:
        print(f"  ERROR: Failed to initialize Hardware SPI ID {LCD_SPI_ID}: {e_hw_spi}")
        spi = None

    if spi is None:
        print("Hardware SPI failed. Attempting SoftSPI fallback...")
        try:
             spi = SoftSPI(baudrate=10000000,
                           sck=Pin(LCD_SCLK_PIN), mosi=Pin(LCD_MOSI_PIN),
                           miso=Pin(LCD_MISO_PIN) if LCD_MISO_PIN != -1 else None)
             print("  Software SPI initialized OK (Lower Performance).")
        except Exception as e_sw_spi:
             print(f"FATAL: Failed to initialize Software SPI: {e_sw_spi}")
             return None

    if st7789 is None:
        print("FATAL: st7789 driver module not loaded, cannot instantiate.")
        if spi: spi.deinit()
        return None

    try:
        print("Initializing ST7789 driver instance...")
        display_dev = st7789.ST7789(
            spi, LCD_WIDTH, LCD_HEIGHT,
            reset=pin_rst, dc=pin_dc, cs=pin_cs, backlight=pin_bl,
            rotation=LCD_ROTATION, color_order=st7789.BGR
        )
        print("Display driver instance created successfully.")
    except Exception as e_driver:
        print(f"FATAL: Error initializing ST7789 DRIVER INSTANCE: {e_driver}")
        if spi: spi.deinit()
        display_dev = None

    return display_dev

def init_i2s():
    """Initializes I2S peripheral for audio input."""
    i2s_dev = None
    read_buf = None
    print("[I2S INIT] Initializing I2S for microphone...")
    try:
        sck_pin = Pin(I2S_BCLK_PIN)
        ws_pin = Pin(I2S_WS_PIN)
        sd_pin = Pin(I2S_DIN_PIN)
        i2s_dev = I2S(I2S_ID,
                      sck=sck_pin, ws=ws_pin, sd=sd_pin,
                      mode=I2S.RX, bits=I2S_BITS, format=I2S_FORMAT,
                      rate=I2S_SAMPLE_RATE, ibuf=I2S_BUFFER_LEN_IN_BYTES)
        read_buf = bytearray(I2S_READ_CHUNK_SIZE)
        print("[I2S INIT] I2S Initialized successfully.")
    except Exception as e:
        print(f"[I2S INIT] FATAL: Error initializing I2S: {e}")
        if i2s_dev:
            try: i2s_dev.deinit()
            except Exception: pass
        i2s_dev = None
        read_buf = None
    return i2s_dev, read_buf

def calculate_rms(audio_buffer, bytes_read):
    """Calculates the Root Mean Square (RMS) of the audio samples."""
    if bytes_read == 0: return 0.0
    if I2S_BITS == 16: bytes_per_sample, unpack_code = 2, 'h'
    elif I2S_BITS == 32: bytes_per_sample, unpack_code = 4, 'i'
    else: return -1.0
    num_samples = bytes_read // bytes_per_sample
    bytes_to_process = num_samples * bytes_per_sample
    if num_samples == 0: return 0.0
    try:
        format_string = I2S_ENDIANNESS + unpack_code * num_samples
        samples = struct.unpack(format_string, audio_buffer[:bytes_to_process])
    except Exception as e: return -1.0
    sum_sq = 0.0
    for sample in samples: sum_sq += float(sample) * float(sample)
    if num_samples == 0: return 0.0
    mean_sq = sum_sq / num_samples
    try:
        if mean_sq < 0: return -1.0
        rms = math.sqrt(mean_sq)
        return rms
    except Exception as e: return -1.0

# --- 4. UI & LED Helper Functions ---

def draw_page_layout(display, page_index):
    """Draws the static layout elements for the given page."""
    if not display or not default_font: return
    print(f"Drawing layout for Page {page_index}...")
    display.fill(COLOR_BG) # Clear screen for new page layout

    # Draw Page Indicator (Common to all pages)
    page_text = f"{page_index + 1}/{NUM_PAGES}"
    # Calculate width to clear previous indicator if needed (optional, as fill clears anyway)
    # indicator_width = display.write_width(default_font, "P?/N") if hasattr(display,'write_width') else 40
    # display.fill_rect(X_PAGE_INDICATOR, Y_PAGE_INDICATOR, indicator_width, FONT_HEIGHT, COLOR_BG)
    display.write(default_font, page_text, X_PAGE_INDICATOR, Y_PAGE_INDICATOR, COLOR_PAGE_INDICATOR, COLOR_BG)

    if page_index == PAGE_MAIN:
        display.hline(0, Y_SEPARATOR_1_P0, display.width, COLOR_SEPARATOR)
        display.hline(0, Y_SEPARATOR_2_P0, display.width, COLOR_SEPARATOR)
        # Labels for Page 0
        display.write(default_font, "T:", X_TEMP_LABEL_P0, Y_SENSOR_ROW_1_P0, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "H:", X_HUM_LABEL_P0, Y_SENSOR_ROW_1_P0, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "Lux:", X_LUX_LABEL_P0, Y_SENSOR_ROW_2_P0, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "Noise:", X_NOISE_LABEL_P0, Y_SENSOR_ROW_2_P0, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "Keys:", X_KEYS_LABEL_P0, Y_BOTTOM_ROW_1_P0, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "Mem:", X_MEM_LABEL_P0, Y_BOTTOM_ROW_2_P0, COLOR_LABEL, COLOR_BG)
    elif page_index == PAGE_NETWORK:
        display.write(default_font, "Network Info", X_TITLE_P1, Y_TITLE_P1, COLOR_TITLE, COLOR_BG)
        # WiFi Icon Placeholder (simple text for now)
        display.write(default_font, "NET", X_WIFI_ICON_P1, Y_WIFI_ICON_P1, COLOR_LABEL, COLOR_BG)
        # Labels for Page 1
        display.write(default_font, "SSID:", X_SSID_LABEL_P1, Y_SSID_P1, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "IP:", X_IP_LABEL_P1, Y_IP_P1, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "Mask:", X_MASK_LABEL_P1, Y_MASK_P1, COLOR_LABEL, COLOR_BG)
        display.write(default_font, "GW:", X_GW_LABEL_P1, Y_GW_P1, COLOR_LABEL, COLOR_BG)
    print(f"Layout drawn for Page {page_index}.")


def reset_prev_ui_strings():
    """Resets all previous UI string states to force redraw on page switch."""
    global prev_wifi_status_str_p0, prev_ble_status_str_p0
    global prev_temperature_str, prev_humidity_str, prev_lux_str, prev_noise_level_str
    global prev_pressed_key_names, prev_mem_free_str
    global prev_page_indicator_str
    global prev_ssid_str_p1, prev_ip_str_p1, prev_mask_str_p1, prev_gw_str_p1
    global prev_wifi_icon_str_p1

    print("Resetting previous UI strings for page switch.")
    # Page 0
    prev_wifi_status_str_p0 = None
    prev_ble_status_str_p0 = None
    prev_temperature_str = None
    prev_humidity_str = None
    prev_lux_str = None
    prev_noise_level_str = None
    prev_pressed_key_names = None
    prev_mem_free_str = None
    # Page 1
    prev_wifi_icon_str_p1 = None
    prev_ssid_str_p1 = None
    prev_ip_str_p1 = None
    prev_mask_str_p1 = None
    prev_gw_str_p1 = None
    # Common
    prev_page_indicator_str = None


def update_text_field(display, x, y, new_text, prev_text, font, fg_color, bg_color):
    """Updates a text field only if the text has changed."""
    if not display or not font: return prev_text
    if new_text != prev_text:
        if prev_text is not None and prev_text != "":
            try:
                if hasattr(display, 'write_width'):
                    prev_width = display.write_width(font, prev_text)
                else:
                    prev_width = len(prev_text) * (font.MAX_WIDTH if hasattr(font, 'MAX_WIDTH') else 15)
                display.fill_rect(x, y, prev_width + 2, font.HEIGHT, bg_color) # Clear slightly wider
            except Exception as e: print(f"Err clear '{prev_text}': {e}")
        try:
            display.write(font, new_text, x, y, fg_color, bg_color)
        except Exception as e: print(f"Err write '{new_text}': {e}"); return prev_text
        return new_text
    return prev_text

def update_leds(pixels, current_time_ms, alert_status):
    """Handles updating the WS2812 LEDs with individual brightness/phase and gamma correction."""
    global alert_active, alert_flash_step, alert_next_action_time, leds_enabled
    if not pixels: return

    # NEW: Check if LEDs are globally disabled by the right key
    if not leds_enabled:
        if any(pixels): # Only write if pixels are not already off
            pixels.fill((0, 0, 0))
            pixels.write()
        return # Stop further processing if LEDs are off

    if alert_active:
        # --- Alert Logic (Remains the same) ---
        if current_time_ms >= alert_next_action_time:
            step = alert_flash_step % (ALERT_TOTAL_FLASHES * 2)
            if step % 2 == 0: # ON step
                pixels.fill(ALERT_COLOR); pixels.write()
                alert_next_action_time = current_time_ms + ALERT_FLASH_ON_MS
            else: # OFF step
                pixels.fill((0, 0, 0)); pixels.write()
                alert_next_action_time = current_time_ms + ALERT_FLASH_OFF_MS
            alert_flash_step += 1
            if alert_flash_step >= ALERT_TOTAL_FLASHES * 2: alert_active = False
        return # Don't run normal effect during alert
        # --- End Alert Logic ---

    # --- Normal Breathing with Phase Shift and Gamma ---
    t = current_time_ms / 1000.0

    for i in range(NUM_LEDS):
        # Calculate phase-shifted sine value for this LED
        phase_offset = i * PHASE_SHIFT_PER_LED
        sin_val = math.sin(t * BREATH_SPEED + phase_offset)

        # Calculate LINEAR brightness factor for this LED (0.0 to 1.0)
        linear_brightness_factor = ((sin_val + 1) / 2) * (1.0 - BREATH_MIN_BRIGHTNESS) + BREATH_MIN_BRIGHTNESS
        linear_brightness_factor = max(0.0, min(1.0, linear_brightness_factor)) # Clamp just in case

        # Apply Gamma Correction
        gamma_corrected_factor = linear_brightness_factor ** GAMMA_VALUE

        # Calculate color for this LED using the gamma-corrected factor
        r = max(0, min(255, int(BREATH_COLOR_BASE[0] * gamma_corrected_factor)))
        g = max(0, min(255, int(BREATH_COLOR_BASE[1] * gamma_corrected_factor)))
        b = max(0, min(255, int(BREATH_COLOR_BASE[2] * gamma_corrected_factor)))

        # Set individual LED color
        pixels[i] = (r, g, b)

    # Write colors to all LEDs once after the loop
    pixels.write()

# --- 5. Main Application Logic ---
if __name__ == "__main__":
    print("--- Starting Main Application ---")
    gc.collect()

    # --- Initialize peripherals ---
    wifi = init_wifi(WIFI_SSID, WIFI_PASSWORD)

    # --- Start WebREPL if WiFi connected and module available ---
    if wifi and wifi.isconnected() and webrepl:
        print("WiFi connected. Starting WebREPL...")
        try:
            webrepl.start()
            print("WebREPL started successfully.")
        except Exception as e:
            print(f"Error starting WebREPL: {e}")
    elif webrepl:
         print("WiFi not connected, WebREPL not started.")

    # --- Setup TCP Server Socket ---
    server_socket = None
    host_ip = None
    if wifi and wifi.isconnected():
        host_ip = wifi.ifconfig()[0]
        print(f"WiFi connected. Attempting to start TCP server on {host_ip}:{SERVER_PORT}")
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host_ip, SERVER_PORT))
            server_socket.listen(1) # Listen for 1 incoming connection
            # Set a short timeout (e.g., 0.1 seconds) or make it non-blocking (timeout=0)
            # This prevents accept() from blocking the main loop indefinitely.
            server_socket.settimeout(0.1)
            print(f"TCP Server listening on {host_ip}:{SERVER_PORT}")
        except Exception as e:
            print(f"Error setting up TCP server: {e}")
            if server_socket:
                server_socket.close()
            server_socket = None # Ensure server is not used if setup failed
    else:
        print("WiFi not connected. TCP server will not be started.")

    ble = init_ble(BLE_DEVICE_NAME)
    keys = init_keypad()
    i2c, temp_hum_sensor, light_sensor = init_i2c_sensors()
    i2s, i2s_buffer = init_i2s()
    display = init_display()
    pixels = None
    if neopixel:
        try:
            pixels = neopixel.NeoPixel(Pin(NEOPIXEL_PIN), NUM_LEDS)
            pixels.fill((0, 0, 0)); pixels.write()
            print(f"NeoPixel LEDs initialized on Pin {NEOPIXEL_PIN}.")
        except Exception as e: print(f"Error initializing NeoPixel LEDs: {e}")
    else: print("NeoPixel library not available, skipping LED init.")

    # --- Main loop state variables ---
    current_page = PAGE_MAIN
    last_key_press_time = 0 # For debouncing page switch
    last_right_key_press_time = 0 # NEW: Debounce timer for right key LED toggle
    leds_enabled = True # NEW: State variable for LED enable/disable

    # Draw initial page layout (Page 0)
    if display and default_font:
        draw_page_layout(display, current_page)
    elif display:
         display.fill(COLOR_STATUS_BAD)

    # Timing variables
    last_sensor_read_ms = 0; sensor_read_interval_ms = 1000
    last_mem_update_ms = 0; mem_update_interval_ms = 5000
    last_noise_calc_ms = 0; noise_calc_interval_ms = 50 # 可以适当调整，例如 100ms
    last_led_update_ms = 0

    loop_count = 0

    # --- State variables for UI updates ---
    # Page 0
    prev_wifi_status_str_p0 = None; prev_ble_status_str_p0 = None
    prev_temperature_str = None; prev_humidity_str = None; prev_lux_str = None; prev_noise_level_str = None
    prev_pressed_key_names = None; prev_mem_free_str = None
    # Page 1
    prev_ssid_str_p1 = None; prev_ip_str_p1 = None; prev_mask_str_p1 = None; prev_gw_str_p1 = None
    prev_wifi_icon_str_p1 = None
    # Common
    prev_page_indicator_str = None

    # --- State variables for Sensor Triggering & LED Alert ---
    prev_temperature_val = -999.0; prev_humidity_val = -999.0; prev_lux_val = -999.0;
    prev_rms_val = 0.0 # Stores the *previous raw* RMS value for triggering
    alert_active = False; alert_flash_step = 0; alert_next_action_time = 0

    # --- RMS Buffer for Smoothing Display ---
    RMS_BUFFER_SIZE = 5 # 缓冲区大小，可以调整
    rms_buffer = [0.0] * RMS_BUFFER_SIZE
    rms_buffer_index = 0
    num_valid_rms_in_buffer = 0
    current_noise_rms = 0.0 # Stores the *smoothed* RMS value for display

    gc.collect()
    print(f"Initial free memory: {gc.mem_free()} bytes")
    print(f"[MAIN] Peripherals initialized. Entering main loop...")

    # --- Main Loop ---
    try:
        while True:
            current_time_ms = time.ticks_ms()
            page_changed = False # Flag to check if page was switched this iteration

            # --- a. Read Keypad Input & Handle Page Switching / LED Toggle ---
            up_pressed = False
            down_pressed = False
            other_keys_list = [] # Track non-page-switch keys

            if keys:
                # Check page switch keys first with debounce
                if time.ticks_diff(current_time_ms, last_key_press_time) > KEY_DEBOUNCE_MS:
                    if not keys['down'].value():
                        down_pressed = True
                        new_page = (current_page + 1) % NUM_PAGES
                        if new_page != current_page:
                            current_page = new_page
                            page_changed = True
                            print(f"Switching to Page {current_page}")
                        last_key_press_time = current_time_ms # Update debounce timer
                    elif not keys['up'].value():
                        up_pressed = True
                        new_page = (current_page - 1 + NUM_PAGES) % NUM_PAGES
                        if new_page != current_page:
                            current_page = new_page
                            page_changed = True
                            print(f"Switching to Page {current_page}")
                        last_key_press_time = current_time_ms # Update debounce timer

                # NEW: Check right key for LED toggle with its own debounce
                if not keys['right'].value():
                    if time.ticks_diff(current_time_ms, last_right_key_press_time) > KEY_DEBOUNCE_MS:
                        leds_enabled = not leds_enabled # Toggle the state
                        print(f"LEDs {'Enabled' if leds_enabled else 'Disabled'}")
                        last_right_key_press_time = current_time_ms # Update right key debounce timer
                        # Optional: Force update LEDs immediately after toggle
                        if pixels: update_leds(pixels, current_time_ms, alert_active)
                # NOTE: 'R' is no longer added to other_keys_list below

                # Read other keys (no debounce needed for just display)
                if not keys['left'].value(): other_keys_list.append("L")
                # if not keys['right'].value(): other_keys_list.append("R") # Removed right key from display list
                if not keys['enter'].value(): other_keys_list.append("E")

            current_pressed_key_names = ",".join(other_keys_list) if other_keys_list else "--"
            # Optional: Add indication if UP/DOWN was pressed but debounced?
            # if up_pressed or down_pressed: current_pressed_key_names += ("U" if up_pressed else "D")


            # --- Handle Page Change ---
            if page_changed and display:
                 draw_page_layout(display, current_page)
                 reset_prev_ui_strings() # Force redraw of all fields on the new page

            # --- b. Read I2C Sensors (Timed) ---
            current_temperature_val = prev_temperature_val
            current_humidity_val = prev_humidity_val
            current_lux_val = prev_lux_val
            sensor_error = False
            trigger_check_needed = False # Default to false

            if time.ticks_diff(current_time_ms, last_sensor_read_ms) >= sensor_read_interval_ms:
                last_sensor_read_ms = current_time_ms
                trigger_check_needed = True # Flag to check thresholds

                if temp_hum_sensor:
                    try:
                        t = temp_hum_sensor.temperature(); h = temp_hum_sensor.humidity()
                        current_temperature_val = t; current_humidity_val = h
                    except Exception as e: sensor_error = True; current_temperature_val = -999; current_humidity_val = -999
                else: trigger_check_needed = False

                if light_sensor:
                    try: l = light_sensor.read(); current_lux_val = l
                    except Exception as e: sensor_error = True; current_lux_val = -999
                else: trigger_check_needed = False

                # --- c. Sensor Trigger Check (Temp/Hum/Lux) ---
                if trigger_check_needed and not alert_active:
                    temp_diff = current_temperature_val - prev_temperature_val
                    humi_diff = current_humidity_val - prev_humidity_val
                    lux_diff = current_lux_val - prev_lux_val
                    temp_trig = (current_temperature_val > -990 and prev_temperature_val > -990 and temp_diff >= TEMP_THRESHOLD_DIFF)
                    humi_trig = (current_humidity_val > -990 and prev_humidity_val > -990 and humi_diff >= HUMI_THRESHOLD_DIFF)
                    lux_trig = (current_lux_val > -990 and prev_lux_val > -990 and lux_diff >= LUX_THRESHOLD_DIFF)
                    if temp_trig or humi_trig or lux_trig:
                        print(f"ALERT: T:{temp_trig}/{temp_diff:.1f} H:{humi_trig}/{humi_diff:.1f} L:{lux_trig}/{lux_diff:.1f}")
                        alert_active = True; alert_flash_step = 0; alert_next_action_time = current_time_ms

                prev_temperature_val = current_temperature_val
                prev_humidity_val = current_humidity_val
                prev_lux_val = current_lux_val

                # --- SEND BLE NOTIFICATIONS (Temp/Hum/Lux) ---
                if ble_conn_handle is not None:
                    try:
                        if ble_notify_enabled['temp']:
                            packed_temp = _pack_sint16_scaled(current_temperature_val if current_temperature_val > -990 else None, 100)
                            ble.gatts_notify(ble_conn_handle, ble_temp_handle, packed_temp)
                            # print(f"BLE Notify Temp: {current_temperature_val}") # Optional debug
                        if ble_notify_enabled['humid']:
                            packed_hum = _pack_uint16_scaled(current_humidity_val if current_humidity_val > -990 else None, 100)
                            ble.gatts_notify(ble_conn_handle, ble_humid_handle, packed_hum)
                            # print(f"BLE Notify Humid: {current_humidity_val}") # Optional debug
                        if ble_notify_enabled['lux']:
                            packed_lux = _pack_uint24_scaled(current_lux_val if current_lux_val > -990 else None, 100)
                            ble.gatts_notify(ble_conn_handle, ble_lux_handle, packed_lux)
                            # print(f"BLE Notify Lux: {current_lux_val}") # Optional debug
                    except OSError as e:
                        print(f"Error sending BLE Temp/Hum/Lux notify: {e}")
                        # Handle potential disconnection during notify
                        if e.args[0] == 104: # ECONNRESET (common disconnect error)
                             ble_conn_handle = None # Assume disconnected
                             print("BLE connection reset during notify, handle cleared.")
                    except Exception as e:
                        print(f"Unexpected error sending BLE Temp/Hum/Lux notify: {e}")
                # --- END BLE NOTIFICATIONS (Temp/Hum/Lux) ---

            # Format strings for display (always needed for UI update check)
            current_temperature_str = f"{current_temperature_val:.1f}C" if current_temperature_val > -990 else "Err"
            current_humidity_str = f"{current_humidity_val:.1f}%" if current_humidity_val > -990 else "Err"
            current_lux_str = f"{current_lux_val:.0f}" if current_lux_val > -990 else "Err"

            # --- d. Read I2S Audio & Calculate Noise & Check Trigger ---
            raw_rms_value_this_cycle = -1.0 # Store the raw RMS calculated in this cycle
            if i2s and i2s_buffer:
                bytes_read = 0
                try:
                    bytes_read = i2s.readinto(i2s_buffer)
                    if bytes_read > 0:
                        if time.ticks_diff(current_time_ms, last_noise_calc_ms) >= noise_calc_interval_ms:
                           last_noise_calc_ms = current_time_ms
                           calculated_rms = calculate_rms(i2s_buffer, bytes_read) # Get raw RMS

                           if calculated_rms >= 0:
                               raw_rms_value_this_cycle = calculated_rms # Store the raw value

                               # --- Update RMS Buffer ---
                               rms_buffer[rms_buffer_index] = calculated_rms
                               rms_buffer_index = (rms_buffer_index + 1) % RMS_BUFFER_SIZE
                               if num_valid_rms_in_buffer < RMS_BUFFER_SIZE:
                                   num_valid_rms_in_buffer += 1

                               # --- Calculate Smoothed RMS for Display ---
                               if num_valid_rms_in_buffer > 0:
                                   # Calculate average using only the valid entries
                                   valid_buffer_slice = rms_buffer[:num_valid_rms_in_buffer]
                                   buffer_sum = sum(valid_buffer_slice)
                                   current_noise_rms = buffer_sum / num_valid_rms_in_buffer # Update the *smoothed* display variable
                               else:
                                   current_noise_rms = 0.0 # Should not happen if calculated_rms >= 0

                               # --- Check RMS Trigger (using raw value against previous raw value) ---
                               if prev_rms_val >= 0 and not alert_active:
                                   rms_diff = raw_rms_value_this_cycle - prev_rms_val # Compare raw vs raw
                                   if rms_diff >= RMS_THRESHOLD_DIFF:
                                       print(f"ALERT TRIGGER: RMS increased by {rms_diff:.1f} (Raw: {raw_rms_value_this_cycle:.1f})")
                                       alert_active = True; alert_flash_step = 0; alert_next_action_time = current_time_ms
                               prev_rms_val = raw_rms_value_this_cycle # Update previous *raw* value for next comparison

                               # --- SEND BLE NOTIFICATION (Noise) ---
                               if ble_conn_handle is not None and ble_notify_enabled['noise']:
                                    try:
                                        # Use the SMOOTHED value for notification, packed as sint16 scaled by 10
                                        packed_noise = _pack_sint16_scaled(current_noise_rms if current_noise_rms >= 0 else None, 10)
                                        ble.gatts_notify(ble_conn_handle, ble_noise_handle, packed_noise)
                                        # print(f"BLE Notify Noise: {current_noise_rms}") # Optional debug
                                    except OSError as e:
                                        print(f"Error sending BLE Noise notify: {e}")
                                        if e.args[0] == 104: # ECONNRESET
                                             ble_conn_handle = None
                                             print("BLE connection reset during noise notify, handle cleared.")
                                    except Exception as e:
                                        print(f"Unexpected error sending BLE Noise notify: {e}")
                               # --- END BLE NOTIFICATION (Noise) ---

                           else: # calculated_rms < 0 (Error)
                               # Keep the last known smoothed value for display
                               print(f"[RMS CALC] Error calculating RMS.")
                               # Optionally reset prev_rms_val if error is persistent
                               # prev_rms_val = -1

                except Exception as e:
                    # Keep the last known smoothed value for display
                    print(f"[I2S READ] ERROR: {e}")

            # Format string for display uses the SMOOTHED value (current_noise_rms)
            current_noise_level_str = f"{current_noise_rms:.1f}" if current_noise_rms >= 0 else "Err" # Display smoothed value

            # --- e. Get Network Status & Details ---
            wifi_connected = wifi and wifi.isconnected()
            # For Page 0 Status Bar
            current_wifi_status_str_p0 = "WiFi✓" if wifi_connected else "WiFi✗" # Short version for status bar
            wifi_status_color_p0 = COLOR_STATUS_OK if wifi_connected else COLOR_STATUS_BAD
            # For Page 1 Details
            current_ssid_str_p1 = WIFI_SSID if wifi_connected else "Disconnected"
            current_ip_str_p1 = "---"; current_mask_str_p1 = "---"; current_gw_str_p1 = "---"
            current_wifi_icon_str_p1 = "NET✓" if wifi_connected else "NET✗" # Simple text icon
            if wifi_connected:
                try:
                    ip_config = wifi.ifconfig()
                    current_ip_str_p1 = ip_config[0]
                    current_mask_str_p1 = ip_config[1]
                    current_gw_str_p1 = ip_config[2]
                except Exception as e:
                    print(f"Error getting ifconfig: {e}")
                    current_ip_str_p1 = "Error"; current_mask_str_p1 = "Error"; current_gw_str_p1 = "Error"


            # --- f. Get BLE Status ---
            ble_active = ble and ble.active()
            ble_is_connected = ble_conn_handle is not None
            current_ble_status_str_p0 = f"BLE{'✓' if ble_is_connected else ('-' if ble_active else '✗')}" # More detailed status
            ble_status_color_p0 = COLOR_STATUS_OK if ble_is_connected else (COLOR_STATUS_WARN if ble_active else COLOR_STATUS_BAD)

            # --- g. Get Memory Status (Timed) ---
            current_mem_free_str = prev_mem_free_str if prev_mem_free_str is not None else "N/A"
            if time.ticks_diff(current_time_ms, last_mem_update_ms) >= mem_update_interval_ms:
                 last_mem_update_ms = current_time_ms
                 current_mem_free_str = f"{gc.mem_free()}"
            current_mem_free_val = gc.mem_free() # Get current value for TCP response

            # === MOVE TCP SERVER HANDLING HERE ===
            # --- Handle TCP Server Connections ---
            client_socket = None # Reset client socket
            if server_socket: # Only try if server socket was successfully created
                try:
                    # Attempt to accept a connection (non-blocking / short timeout)
                    client_socket, addr = server_socket.accept()
                    client_socket.settimeout(5.0) # Set timeout for client operations
                    print(f"TCP Connection from: {addr}")

                    # --- Handle Client Interaction ---
                    try:
                        # 1. Send connected message
                        client_socket.sendall(b"CONNECTED\n") # Send as bytes

                        # 2. Receive command
                        command_bytes = client_socket.readline()
                        if not command_bytes:
                            print(f"Client {addr} disconnected before sending command.")
                        else:
                            command = command_bytes.decode('utf-8').strip()
                            print(f"Received command from {addr}: {command}")

                            # 3. Process command
                            if command == "GET_CURRENT":
                                # Gather current data (Now uses variables updated *this* loop iteration)
                                data = {
                                    "timestamp_ms": current_time_ms,
                                    "page": current_page,
                                    "wifi_status": "Connected" if wifi_connected else "Disconnected",
                                    "ble_status": "Active" if ble_active else "Inactive",
                                    "temperature_c": current_temperature_val if current_temperature_val > -990 else None,
                                    "humidity_percent": current_humidity_val if current_humidity_val > -990 else None,
                                    "lux": current_lux_val if current_lux_val > -990 else None,
                                    "noise_rms_smoothed": current_noise_rms if current_noise_rms >= 0 else None,
                                    "keys_pressed": current_pressed_key_names,
                                    "mem_free_bytes": current_mem_free_val # Use value obtained in step g
                                }
                                # Convert to JSON and send
                                response_json = json.dumps(data)
                                client_socket.sendall((response_json + '\n').encode('utf-8'))
                                print(f"Sent current data to {addr}")

                            elif command == "GET_HISTORY": # Example for future
                                client_socket.sendall(b"HISTORY_NOT_IMPLEMENTED\n")
                                print(f"Sent HISTORY_NOT_IMPLEMENTED to {addr}")

                            else:
                                client_socket.sendall(b"UNKNOWN_COMMAND\n")
                                print(f"Sent UNKNOWN_COMMAND to {addr}")

                    except OSError as client_e:
                        print(f"Client socket error ({addr}): {client_e}")
                    except Exception as client_e:
                         print(f"Error handling client {addr}: {client_e}")
                    finally:
                         if client_socket:
                             client_socket.close()
                             print(f"TCP Connection closed for {addr}")
                         client_socket = None # Ensure it's cleared

                except OSError as e:
                    # This is expected if no connection is pending due to the timeout
                    # Check for expected timeout errors (EAGAIN/EWOULDBLOCK or ETIMEDOUT)
                    # errno 11: EAGAIN / EWOULDBLOCK
                    # errno 116: ETIMEDOUT (seems to be used on some MicroPython ports for accept timeout)
                    expected_errnos = (11, 116)
                    if e.args[0] in expected_errnos:
                         pass # No connection waiting, this is normal, continue the main loop
                    else:
                         # Log other unexpected socket errors
                         print(f"Server socket accept error: {e}")
                         # Consider closing/reopening server socket on certain errors?
                except Exception as e:
                     print(f"Unexpected error during server accept: {e}")
            # === END OF TCP SERVER HANDLING ===


            # --- h. Update Display based on Current Page ---
            if display and default_font:
                # Update Page Indicator (Common)
                current_page_indicator_str = f"{current_page + 1}/{NUM_PAGES}"
                prev_page_indicator_str = update_text_field(display, X_PAGE_INDICATOR, Y_PAGE_INDICATOR, current_page_indicator_str, prev_page_indicator_str, default_font, COLOR_PAGE_INDICATOR, COLOR_BG)

                # Update Page Specific Fields
                if current_page == PAGE_MAIN:
                    prev_wifi_status_str_p0 = update_text_field(display, X_WIFI_STATUS_P0, Y_STATUS_LINE_P0, current_wifi_status_str_p0, prev_wifi_status_str_p0, default_font, wifi_status_color_p0, COLOR_BG)
                    prev_ble_status_str_p0 = update_text_field(display, X_BLE_STATUS_P0, Y_STATUS_LINE_P0, current_ble_status_str_p0, prev_ble_status_str_p0, default_font, ble_status_color_p0, COLOR_BG)
                    prev_temperature_str = update_text_field(display, X_TEMP_VALUE_P0, Y_SENSOR_ROW_1_P0, current_temperature_str, prev_temperature_str, default_font, COLOR_VALUE, COLOR_BG)
                    prev_humidity_str = update_text_field(display, X_HUM_VALUE_P0, Y_SENSOR_ROW_1_P0, current_humidity_str, prev_humidity_str, default_font, COLOR_VALUE, COLOR_BG)
                    prev_lux_str = update_text_field(display, X_LUX_VALUE_P0, Y_SENSOR_ROW_2_P0, current_lux_str, prev_lux_str, default_font, COLOR_VALUE, COLOR_BG)
                    prev_noise_level_str = update_text_field(display, X_NOISE_VALUE_P0, Y_SENSOR_ROW_2_P0, current_noise_level_str, prev_noise_level_str, default_font, COLOR_VALUE, COLOR_BG)
                    prev_pressed_key_names = update_text_field(display, X_KEYS_VALUE_P0, Y_BOTTOM_ROW_1_P0, current_pressed_key_names, prev_pressed_key_names, default_font, COLOR_VALUE, COLOR_BG)
                    prev_mem_free_str = update_text_field(display, X_MEM_VALUE_P0, Y_BOTTOM_ROW_2_P0, current_mem_free_str, prev_mem_free_str, default_font, COLOR_MEM, COLOR_BG)
                elif current_page == PAGE_NETWORK:
                    prev_wifi_icon_str_p1 = update_text_field(display, X_WIFI_ICON_P1, Y_WIFI_ICON_P1, current_wifi_icon_str_p1, prev_wifi_icon_str_p1, default_font, wifi_status_color_p0, COLOR_BG) # Use same color as status
                    prev_ssid_str_p1 = update_text_field(display, X_SSID_VALUE_P1, Y_SSID_P1, current_ssid_str_p1, prev_ssid_str_p1, default_font, COLOR_VALUE, COLOR_BG)
                    prev_ip_str_p1 = update_text_field(display, X_IP_VALUE_P1, Y_IP_P1, current_ip_str_p1, prev_ip_str_p1, default_font, COLOR_VALUE, COLOR_BG)
                    prev_mask_str_p1 = update_text_field(display, X_MASK_VALUE_P1, Y_MASK_P1, current_mask_str_p1, prev_mask_str_p1, default_font, COLOR_VALUE, COLOR_BG)
                    prev_gw_str_p1 = update_text_field(display, X_GW_VALUE_P1, Y_GW_P1, current_gw_str_p1, prev_gw_str_p1, default_font, COLOR_VALUE, COLOR_BG)


            # --- i. Update WS2812 LEDs (Timed) ---
            if pixels and time.ticks_diff(current_time_ms, last_led_update_ms) >= LED_UPDATE_INTERVAL_MS:
                last_led_update_ms = current_time_ms
                # Pass alert_active status to the LED update function
                update_leds(pixels, current_time_ms, alert_active)

            # --- j. Yield control ---
            time.sleep_ms(10) # Slightly shorter sleep potentially
            loop_count += 1

            # Optional: Periodic garbage collection & Debug Print
            if loop_count % 500 == 0: # Approx every 5 seconds
                gc.collect()
                # Debug print now shows smoothed RMS
                print(f"Loop {loop_count}, Page: {current_page}, Mem: {gc.mem_free()}, RMS(Smoothed): {current_noise_rms:.1f}, Alert: {alert_active}")

    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
    finally:
        # --- Cleanup resources ---
        print("Cleaning up resources...")
        if client_socket: # Should be closed already, but just in case
            try: client_socket.close(); print("Closed any dangling client socket.")
            except Exception: pass
        if server_socket:
            try: server_socket.close(); print("TCP Server socket closed.")
            except Exception as e: print(f"Error closing server socket: {e}")
        if pixels:
             try: pixels.fill((0,0,0)); pixels.write(); print("NeoPixel LEDs turned off.")
             except Exception as e: print(f"Error turning off LEDs: {e}")
        if i2s:
            try: i2s.deinit(); print("I2S deinitialized.")
            except Exception as e: print(f"Error deinit I2S: {e}")
        if display:
            try:
                bl_pin = Pin(LCD_BL_PIN, Pin.OUT); bl_pin.value(0); print("Display backlight off.")
            except Exception as e: print(f"Warn: Could not turn off backlight: {e}")
        if wifi and wifi.active():
            try: wifi.active(False); print("WiFi deactivated.")
            except Exception as e: print(f"Error deactivating WiFi: {e}")
        if ble and ble.active():
            try:
                if ble_conn_handle is not None:
                    ble.gap_disconnect(ble_conn_handle) # Disconnect if connected
                ble.active(False); print("Bluetooth deactivated.")
            except Exception as e: print(f"Error deactivating BLE: {e}")
        print("Cleanup complete. Application finished.")