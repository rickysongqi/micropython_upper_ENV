# main.py
# Application to manage Wi-Fi, BLE, Keypad, LCD (ST7789),
# I2C Sensors (SI7021, BH1750), I2S Mic, and WS2812 LEDs.
# --- VERSION WITH WS2812 EFFECTS ---

import gc
import time
import network
import struct
import math
from machine import Pin, SPI, I2C, I2S, SoftSPI
# --- Add Neopixel import ---
try:
    import neopixel
except ImportError:
    print("Error: neopixel library not found. WS2812 functions disabled.")
    neopixel = None

# --- 1. Import necessary driver/font modules ---
# (Existing imports remain the same)
# WARNING: Bluetooth import check
try:
    import bluetooth
except ImportError:
    print("CRITICAL: Failed to import 'bluetooth' module.")
    bluetooth = None

# Display Driver
try:
    import st7789
except ImportError:
    print("Error: ST7789 driver (st7789.py) not found. Display functions disabled.")
    st7789 = None

# Sensor Drivers
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

# Font Module (Ensure this is the correct name of your converted font file)
try:
    import ubuntu_24 as default_font
except ImportError:
    print("Error: Converted font module ('ubuntu_24.py') not found.")
    default_font = None


# --- 2. Define constants and configuration ---
I2S_DEBUG_VERBOSE = False

# Network Config
WIFI_SSID = "Redmi_1D4E"
WIFI_PASSWORD = "12340000"
BLE_DEVICE_NAME = "ESP32S3_Sensor"

# Hardware Pins
KEY_UP_PIN = 2
KEY_DOWN_PIN = 41
KEY_LEFT_PIN = 40
KEY_RIGHT_PIN = 1
KEY_ENTER_PIN = 42

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

# --- WS2812 NeoPixel Configuration ---
NEOPIXEL_PIN = 18
NUM_LEDS = 4

# --- UI Layout and Style Constants ---
# (Existing constants remain the same)
COLOR_BG = st7789.BLACK if st7789 else 0x0000
COLOR_FG = st7789.WHITE if st7789 else 0xFFFF
COLOR_LABEL = st7789.CYAN if st7789 else 0x07FF
COLOR_VALUE = st7789.WHITE if st7789 else 0xFFFF
COLOR_SEPARATOR = st7789.BLUE if st7789 else 0x001F
COLOR_STATUS_OK = st7789.GREEN if st7789 else 0x07E0
COLOR_STATUS_WARN = st7789.YELLOW if st7789 else 0xFFE0
COLOR_STATUS_BAD = st7789.RED if st7789 else 0xF800
COLOR_MEM = st7789.GREEN if st7789 else 0x07E0
PADDING = 5
FONT_HEIGHT = default_font.HEIGHT if default_font else 24
Y_STATUS_LINE = PADDING
X_WIFI_STATUS = PADDING
X_BLE_STATUS = 80
X_IP_LABEL = 140
X_IP_VALUE = 170
Y_SEPARATOR_1 = Y_STATUS_LINE + FONT_HEIGHT + PADDING
Y_SENSOR_ROW_1 = Y_SEPARATOR_1 + PADDING + 5
X_TEMP_LABEL = PADDING
X_TEMP_VALUE = 45
X_HUM_LABEL = 120
X_HUM_VALUE = 165
Y_SENSOR_ROW_2 = Y_SENSOR_ROW_1 + FONT_HEIGHT + PADDING + 10
X_LUX_LABEL = PADDING
X_LUX_VALUE = 60
X_NOISE_LABEL = 120
X_NOISE_VALUE = 190
Y_SEPARATOR_2 = Y_SENSOR_ROW_2 + FONT_HEIGHT + PADDING + 5
Y_BOTTOM_ROW_1 = Y_SEPARATOR_2 + PADDING + 5
X_KEYS_LABEL = PADDING
X_KEYS_VALUE = 70
Y_BOTTOM_ROW_2 = Y_BOTTOM_ROW_1 + FONT_HEIGHT + PADDING
X_MEM_LABEL = PADDING
X_MEM_VALUE = 70


# --- LED Effect Configuration ---
LED_UPDATE_INTERVAL_MS = 40  # How often to update LED brightness/color (for breathing)
BREATH_SPEED = 0.8           # Lower values make breathing slower (radians per second)
BREATH_COLOR_BASE = (180, 255, 180) # Greenish-white base color (R, G, B)
BREATH_MIN_BRIGHTNESS = 0.1  # Minimum brightness factor (0.0 to 1.0)

ALERT_COLOR = (255, 0, 0)   # Red
ALERT_FLASH_ON_MS = 150     # Duration of red light during flash
ALERT_FLASH_OFF_MS = 100    # Duration of darkness between flashes
ALERT_TOTAL_FLASHES = 2     # Number of red flashes for an alert

# --- Sensor Trigger Thresholds (Tune these!) ---
# These define the *increase* needed to trigger an alert
TEMP_THRESHOLD_DIFF = 3.0     # Increase of 3 degrees C
HUMI_THRESHOLD_DIFF = 15.0    # Increase of 15% RH
LUX_THRESHOLD_DIFF = 500.0   # Increase of 500 Lux (highly dependent on environment)
RMS_THRESHOLD_DIFF = 1500.0  # Increase in RMS value (very dependent on mic sensitivity/gain!)


# --- 3. Initialization Functions ---
# (Existing init functions: init_wifi, init_ble, init_keypad, init_i2c_sensors, init_display, init_i2s, calculate_rms)
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
    """Initializes Bluetooth LE and starts advertising."""
    if bluetooth is None: # Check if import failed earlier
        print("BLE init skipped: bluetooth module not available.")
        return None

    ble = bluetooth.BLE()
    if not ble.active():
        print("Activating Bluetooth...")
        ble.active(True)

    print("Configuring BLE advertisement...")
    # Construct payload: Flags + Complete Local Name
    adv_payload = bytearray()
    # Flags: LE General Discoverable Mode, BR/EDR Not Supported
    adv_payload.extend(b'\x02\x01\x06')
    # Complete Local Name
    name_bytes = bytes(device_name, 'utf-8')
    adv_payload.extend(bytes([len(name_bytes) + 1, 0x09])) # Length byte, Type byte (0x09)
    adv_payload.extend(name_bytes)

    interval_us = 100000 # 100ms interval
    try:
        # Correct way: Call gap_advertise on the BLE instance
        ble.gap_advertise(interval_us, adv_data=adv_payload)
        print(f"BLE advertising started as '{device_name}'")
        return ble
    except Exception as e:
        # Use Exception for broader compatibility, OSError common
        print(f"Error starting BLE advertising: {e}")
        print("BLE advertising payload may be too long or invalid.")
        # Fallback: Try advertising only flags
        try:
            print("Attempting to advertise with minimal payload (Flags only)...")
            ble.gap_advertise(interval_us, adv_data=b'\x02\x01\x06')
            print("Minimal BLE advertising started.")
            return ble
        except Exception as e_minimal:
            print(f"Error starting minimal BLE advertising: {e_minimal}")
            ble.active(False) # Deactivate if advertising fails completely
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
                # Optional: Set mode/power on if needed by driver/hardware
                # sensor_l.power_on()
                # sensor_l.set_mode(bh1750.CONT_HIGH_RES_MODE_1)
                print("BH1750 Light sensor initialized.")
            except Exception as e:
                print(f"Error initializing BH1750 driver: {e}")
        elif bh1750:
                print(f"BH1750 not found at address {hex(BH1750_ADDR)}")

    except Exception as e:
        print(f"FATAL: Error initializing I2C Bus {I2C_ID}: {e}")
        i2c = None # Ensure i2c is None if bus init failed

    return i2c, sensor_th, sensor_l

def init_display():
    """Initializes SPI bus and ST7789 LCD."""
    global spi # Assume spi is global or adjust scope as needed
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
    spi_ids_to_try = [LCD_SPI_ID] # Use the defined ID
    print(f"Attempting Hardware SPI initialization for ID: {spi_ids_to_try[0]}")
    try:
        print(f"--> Attempting to init Hardware SPI ID: {LCD_SPI_ID}")
        print(f"    SCLK={LCD_SCLK_PIN}, MOSI={LCD_MOSI_PIN}, MISO={LCD_MISO_PIN}, BAUD={LCD_SPI_BAUDRATE}")
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
             spi = SoftSPI(baudrate=10000000, # SoftSPI is slower
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
            rotation=LCD_ROTATION, color_order=st7789.BGR # Or RGB based on your screen
        )
        print("Display driver instance created successfully.")
        print("--- Display Initialization Finished ---")
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
    if I2S_DEBUG_VERBOSE:
        print(f"[RMS CALC] Received buffer (len={len(audio_buffer)}), bytes_read={bytes_read}, I2S_BITS={I2S_BITS}")
    if bytes_read == 0: return 0.0

    if I2S_BITS == 16: bytes_per_sample, unpack_code = 2, 'h'
    elif I2S_BITS == 32: bytes_per_sample, unpack_code = 4, 'i'
    else: print(f"[RMS CALC] ERROR: Unsupported I2S_BITS: {I2S_BITS}"); return -1.0

    if bytes_read % bytes_per_sample != 0:
        print(f"[RMS CALC] WARNING: bytes_read ({bytes_read}) not multiple of bytes_per_sample ({bytes_per_sample})!")
    num_samples = bytes_read // bytes_per_sample
    bytes_to_process = num_samples * bytes_per_sample
    if num_samples == 0: return 0.0

    try:
        format_string = I2S_ENDIANNESS + unpack_code * num_samples
        samples = struct.unpack(format_string, audio_buffer[:bytes_to_process])
    except Exception as e:
        print(f"[RMS CALC] ERROR during unpack: {e}")
        return -1.0

    sum_sq = 0.0
    for sample in samples: sum_sq += float(sample) * float(sample)

    # Avoid division by zero if num_samples became zero after adjustment
    if num_samples == 0: return 0.0

    mean_sq = sum_sq / num_samples
    try:
        if mean_sq < 0: print(f"[RMS CALC] ERROR: Mean square negative ({mean_sq})"); return -1.0
        rms = math.sqrt(mean_sq)
        if I2S_DEBUG_VERBOSE: print(f"[RMS CALC] Calculated RMS: {rms}")
        return rms
    except ValueError as e:
        print(f"[RMS CALC] ERROR calculating sqrt: {e}, mean_sq={mean_sq}")
        return -1.0
    except Exception as e: # Catch potential overflow etc.
        print(f"[RMS CALC] UNEXPECTED ERROR calculating RMS: {e}")
        return -1.0


# --- 4. UI & LED Helper Functions ---

def draw_initial_ui(display):
    """Draws the static parts of the UI layout."""
    if not display or not default_font: return
    print("Drawing initial UI layout...")
    display.fill(COLOR_BG)
    display.hline(0, Y_SEPARATOR_1, display.width, COLOR_SEPARATOR)
    display.hline(0, Y_SEPARATOR_2, display.width, COLOR_SEPARATOR)
    display.write(default_font, "IP:", X_IP_LABEL, Y_STATUS_LINE, COLOR_LABEL, COLOR_BG)
    display.write(default_font, "T:", X_TEMP_LABEL, Y_SENSOR_ROW_1, COLOR_LABEL, COLOR_BG)
    display.write(default_font, "H:", X_HUM_LABEL, Y_SENSOR_ROW_1, COLOR_LABEL, COLOR_BG)
    display.write(default_font, "Lux:", X_LUX_LABEL, Y_SENSOR_ROW_2, COLOR_LABEL, COLOR_BG)
    display.write(default_font, "Noise:", X_NOISE_LABEL, Y_SENSOR_ROW_2, COLOR_LABEL, COLOR_BG)
    display.write(default_font, "Keys:", X_KEYS_LABEL, Y_BOTTOM_ROW_1, COLOR_LABEL, COLOR_BG)
    display.write(default_font, "Mem:", X_MEM_LABEL, Y_BOTTOM_ROW_2, COLOR_LABEL, COLOR_BG)
    print("Initial UI drawn.")

def update_text_field(display, x, y, new_text, prev_text, font, fg_color, bg_color):
    """Updates a text field on the display only if the text has changed."""
    if not display or not font: return prev_text
    if new_text != prev_text:
        if prev_text is not None and prev_text != "":
            try:
                if hasattr(display, 'write_width'):
                    prev_width = display.write_width(font, prev_text)
                else:
                    prev_width = len(prev_text) * (font.MAX_WIDTH if hasattr(font, 'MAX_WIDTH') else 15)
                # Add a small buffer to clear area slightly wider, prevents artifacts
                display.fill_rect(x, y, prev_width + 2, font.HEIGHT, bg_color)
            except Exception as e:
                print(f"Error clearing prev text '{prev_text}' at ({x},{y}): {e}")
        try:
            display.write(font, new_text, x, y, fg_color, bg_color)
        except Exception as e:
            print(f"Error writing new text '{new_text}' at ({x},{y}): {e}")
            return prev_text
        return new_text
    return prev_text

def update_leds(pixels, current_time_ms, alert_status):
    """Handles updating the WS2812 LEDs based on normal or alert state."""
    global alert_active, alert_flash_step, alert_next_action_time # Allow modification

    if not pixels: return # Do nothing if neopixel not initialized

    # --- Alert State Logic ---
    if alert_active:
        if current_time_ms >= alert_next_action_time:
            step = alert_flash_step % (ALERT_TOTAL_FLASHES * 2) # 0=R1_ON, 1=R1_OFF, 2=R2_ON, 3=R2_OFF

            if step % 2 == 0: # Turn ON step
                pixels.fill(ALERT_COLOR)
                pixels.write()
                alert_next_action_time = current_time_ms + ALERT_FLASH_ON_MS
                print(f"Alert Flash {step//2 + 1} ON")
            else: # Turn OFF step
                pixels.fill((0, 0, 0))
                pixels.write()
                alert_next_action_time = current_time_ms + ALERT_FLASH_OFF_MS
                print(f"Alert Flash {step//2 + 1} OFF")

            alert_flash_step += 1

            if alert_flash_step >= ALERT_TOTAL_FLASHES * 2:
                alert_active = False # Alert finished
                print("Alert Finished.")
                # Immediately switch back to normal breathing calculation for next cycle
                # Optional: Add a small cooldown before normal breathing resumes fully bright?
        # If alert active but not time for next action, do nothing (hold current state)
        return # Don't run normal effect during alert animation

    # --- Normal Breathing State Logic ---
    # Calculate time in seconds for smooth animation independent of loop speed
    t = current_time_ms / 1000.0

    # Calculate brightness factor using sine wave (0.0 to 1.0)
    # Add BREATH_MIN_BRIGHTNESS to ensure it doesn't go completely dark
    # (math.sin(t * BREATH_SPEED) + 1) / 2 gives 0.0 to 1.0 oscillation
    brightness_factor = ((math.sin(t * BREATH_SPEED) + 1) / 2) * (1.0 - BREATH_MIN_BRIGHTNESS) + BREATH_MIN_BRIGHTNESS

    # Calculate current color by scaling the base color
    # Use max(0, ...) to prevent potential negative values due to float precision
    # Clamp R, G, B values to 0-255
    r = max(0, min(255, int(BREATH_COLOR_BASE[0] * brightness_factor)))
    g = max(0, min(255, int(BREATH_COLOR_BASE[1] * brightness_factor)))
    b = max(0, min(255, int(BREATH_COLOR_BASE[2] * brightness_factor)))
    current_color = (r, g, b)

    # Apply to all LEDs
    pixels.fill(current_color)
    pixels.write()

# --- 5. Main Application Logic ---
if __name__ == "__main__":
    print("--- Starting Main Application ---")
    gc.collect()

    # --- Initialize peripherals ---
    wifi = init_wifi(WIFI_SSID, WIFI_PASSWORD)
    ble = init_ble(BLE_DEVICE_NAME)
    keys = init_keypad()
    i2c, temp_hum_sensor, light_sensor = init_i2c_sensors()
    i2s, i2s_buffer = init_i2s()
    display = init_display()

    # --- Initialize NeoPixel LEDs ---
    pixels = None
    if neopixel:
        try:
            pixels = neopixel.NeoPixel(Pin(NEOPIXEL_PIN), NUM_LEDS)
            pixels.fill((0, 0, 0)) # Start with LEDs off
            pixels.write()
            print(f"NeoPixel LEDs initialized on Pin {NEOPIXEL_PIN}.")
        except Exception as e:
            print(f"Error initializing NeoPixel LEDs: {e}")
            pixels = None # Ensure pixels is None if init failed
    else:
        print("NeoPixel library not available, skipping LED init.")


    # --- Draw initial UI Layout ---
    if display and default_font:
        draw_initial_ui(display)
    elif display:
         display.fill(COLOR_STATUS_BAD)

    # --- Variables for main loop ---
    last_sensor_read_ms = 0
    sensor_read_interval_ms = 1000 # Read sensors more frequently for trigger check

    last_mem_update_ms = 0
    mem_update_interval_ms = 5000

    noise_calc_interval_ms = 50
    last_noise_calc_ms = 0

    last_led_update_ms = 0 # Timing for LED effect updates

    loop_count = 0

    # --- State variables for UI updates ---
    prev_wifi_status_str = None
    prev_ble_status_str = None
    prev_ip_str = None
    prev_temperature_str = None
    prev_humidity_str = None
    prev_lux_str = None
    prev_noise_level_str = None
    prev_pressed_key_names = None
    prev_mem_free_str = None

    # --- State variables for Sensor Triggering & LED Alert ---
    # Store numeric previous values for comparison
    prev_temperature_val = 0.0
    prev_humidity_val = 0.0
    prev_lux_val = 0.0
    prev_rms_val = 0.0
    alert_active = False
    alert_flash_step = 0 # Tracks progress through the alert flash sequence
    alert_next_action_time = 0 # When the next flash on/off should happen

    current_noise_rms = 0.0 # Store the latest RMS value numerically

    gc.collect()
    print(f"Initial free memory: {gc.mem_free()} bytes")
    print(f"[MAIN] Peripherals initialized. Entering main loop...")

    # --- Main Loop ---
    try:
        while True:
            current_time_ms = time.ticks_ms()

            # --- a. Read Keypad Input ---
            pressed_list = []
            if keys:
                for name, pin in keys.items():
                    if not pin.value(): pressed_list.append(name[:1].upper())
            current_pressed_key_names = ",".join(pressed_list) if pressed_list else "--"

            # --- b. Read I2C Sensors (Timed) ---
            # Store current values numerically for logic, format strings later
            current_temperature_val = prev_temperature_val
            current_humidity_val = prev_humidity_val
            current_lux_val = prev_lux_val
            sensor_error = False

            if time.ticks_diff(current_time_ms, last_sensor_read_ms) >= sensor_read_interval_ms:
                last_sensor_read_ms = current_time_ms
                trigger_check_needed = True # Flag to check thresholds after reading

                # Read Temp/Hum
                if temp_hum_sensor:
                    try:
                        t = temp_hum_sensor.temperature()
                        h = temp_hum_sensor.humidity()
                        current_temperature_val = t
                        current_humidity_val = h
                    except Exception as e:
                        print(f"Warn: Failed reading SI7021: {e}")
                        sensor_error = True
                        current_temperature_val = -999 # Indicate error numerically
                        current_humidity_val = -999
                else: trigger_check_needed = False # Can't check if no sensor

                # Read Light
                if light_sensor:
                    try:
                        l = light_sensor.read()
                        current_lux_val = l
                    except Exception as e:
                        print(f"Warn: Failed reading BH1750: {e}")
                        sensor_error = True
                        current_lux_val = -999 # Indicate error numerically
                else: trigger_check_needed = False # Can't check if no sensor

                # --- c. Sensor Trigger Check ---
                if trigger_check_needed and not alert_active: # Only check if needed and not already alerting
                    temp_diff = current_temperature_val - prev_temperature_val
                    humi_diff = current_humidity_val - prev_humidity_val
                    lux_diff = current_lux_val - prev_lux_val
                    # RMS diff checked separately below after calculation

                    # Check thresholds (handle error values - they shouldn't trigger)
                    temp_triggered = (current_temperature_val > -990 and prev_temperature_val > -990 and temp_diff >= TEMP_THRESHOLD_DIFF)
                    humi_triggered = (current_humidity_val > -990 and prev_humidity_val > -990 and humi_diff >= HUMI_THRESHOLD_DIFF)
                    lux_triggered = (current_lux_val > -990 and prev_lux_val > -990 and lux_diff >= LUX_THRESHOLD_DIFF)

                    if temp_triggered: print(f"ALERT TRIGGER: Temperature increased by {temp_diff:.1f}C")
                    if humi_triggered: print(f"ALERT TRIGGER: Humidity increased by {humi_diff:.1f}%")
                    if lux_triggered: print(f"ALERT TRIGGER: Lux increased by {lux_diff:.1f}")

                    if temp_triggered or humi_triggered or lux_triggered:
                        alert_active = True
                        alert_flash_step = 0
                        alert_next_action_time = current_time_ms # Start flash immediately

                # Update previous values *after* comparison
                prev_temperature_val = current_temperature_val
                prev_humidity_val = current_humidity_val
                prev_lux_val = current_lux_val

            # Format sensor strings for display *after* potential update
            current_temperature_str = f"{current_temperature_val:.1f}C" if current_temperature_val > -990 else "Err"
            current_humidity_str = f"{current_humidity_val:.1f}%" if current_humidity_val > -990 else "Err"
            current_lux_str = f"{current_lux_val:.0f}" if current_lux_val > -990 else "Err"


            # --- d. Read I2S Audio & Calculate Noise ---
            # Store RMS numerically first
            new_rms_value = -1.0
            if i2s and i2s_buffer:
                bytes_read = 0
                try:
                    bytes_read = i2s.readinto(i2s_buffer)
                    if bytes_read > 0:
                        if time.ticks_diff(current_time_ms, last_noise_calc_ms) >= noise_calc_interval_ms:
                           last_noise_calc_ms = current_time_ms
                           new_rms_value = calculate_rms(i2s_buffer, bytes_read)
                           # --- Check RMS Trigger ---
                           if new_rms_value >= 0 and prev_rms_val >= 0 and not alert_active:
                               rms_diff = new_rms_value - prev_rms_val
                               if rms_diff >= RMS_THRESHOLD_DIFF:
                                   print(f"ALERT TRIGGER: RMS increased by {rms_diff:.1f} (Current: {new_rms_value:.1f})")
                                   alert_active = True
                                   alert_flash_step = 0
                                   alert_next_action_time = current_time_ms # Start flash immediately
                           # Update previous RMS value *after* comparison
                           if new_rms_value >= 0: # Only update if valid calculation
                              prev_rms_val = new_rms_value
                    # else: Handle 0 bytes read if necessary
                except Exception as e:
                    print(f"[I2S READ] CRITICAL ERROR: {e}")
                    new_rms_value = -1.0 # Indicate error

            # Update the globally accessible RMS value if it was calculated
            if new_rms_value >= 0:
                 current_noise_rms = new_rms_value
            elif new_rms_value == -1.0: # Handle calculation error state
                 current_noise_rms = -1.0

            # Format noise string for display
            current_noise_level_str = f"{current_noise_rms:.1f}" if current_noise_rms >= 0 else "Err"


            # --- e. Get Network Status & IP ---
            wifi_connected = wifi and wifi.isconnected()
            current_wifi_status_str = "WiFi ✓" if wifi_connected else "WiFi ✗"
            wifi_status_color = COLOR_STATUS_OK if wifi_connected else COLOR_STATUS_BAD
            current_ip_str = wifi.ifconfig()[0] if wifi_connected else "---"

            # --- f. Get BLE Status ---
            ble_active = ble and ble.active()
            current_ble_status_str = "BLE ✓" if ble_active else "BLE ✗"
            ble_status_color = COLOR_STATUS_OK if ble_active else COLOR_STATUS_BAD

            # --- g. Get Memory Status (Timed) ---
            current_mem_free_str = prev_mem_free_str if prev_mem_free_str is not None else "N/A"
            if time.ticks_diff(current_time_ms, last_mem_update_ms) >= mem_update_interval_ms:
                 last_mem_update_ms = current_time_ms
                 current_mem_free_str = f"{gc.mem_free()}"


            # --- h. Update Display using Partial Updates ---
            if display and default_font:
                prev_wifi_status_str = update_text_field(display, X_WIFI_STATUS, Y_STATUS_LINE, current_wifi_status_str, prev_wifi_status_str, default_font, wifi_status_color, COLOR_BG)
                prev_ble_status_str = update_text_field(display, X_BLE_STATUS, Y_STATUS_LINE, current_ble_status_str, prev_ble_status_str, default_font, ble_status_color, COLOR_BG)
                prev_ip_str = update_text_field(display, X_IP_VALUE, Y_STATUS_LINE, current_ip_str, prev_ip_str, default_font, COLOR_VALUE, COLOR_BG)
                prev_temperature_str = update_text_field(display, X_TEMP_VALUE, Y_SENSOR_ROW_1, current_temperature_str, prev_temperature_str, default_font, COLOR_VALUE, COLOR_BG)
                prev_humidity_str = update_text_field(display, X_HUM_VALUE, Y_SENSOR_ROW_1, current_humidity_str, prev_humidity_str, default_font, COLOR_VALUE, COLOR_BG)
                prev_lux_str = update_text_field(display, X_LUX_VALUE, Y_SENSOR_ROW_2, current_lux_str, prev_lux_str, default_font, COLOR_VALUE, COLOR_BG)
                prev_noise_level_str = update_text_field(display, X_NOISE_VALUE, Y_SENSOR_ROW_2, current_noise_level_str, prev_noise_level_str, default_font, COLOR_VALUE, COLOR_BG)
                prev_pressed_key_names = update_text_field(display, X_KEYS_VALUE, Y_BOTTOM_ROW_1, current_pressed_key_names, prev_pressed_key_names, default_font, COLOR_VALUE, COLOR_BG)
                prev_mem_free_str = update_text_field(display, X_MEM_VALUE, Y_BOTTOM_ROW_2, current_mem_free_str, prev_mem_free_str, default_font, COLOR_MEM, COLOR_BG)


            # --- i. Update WS2812 LEDs (Timed) ---
            if pixels and time.ticks_diff(current_time_ms, last_led_update_ms) >= LED_UPDATE_INTERVAL_MS:
                last_led_update_ms = current_time_ms
                update_leds(pixels, current_time_ms, alert_active)


            # --- j. Yield control ---
            # Determine sleep duration - potentially sleep less if alert is active?
            # For now, keep it simple.
            sleep_duration = 10 # ms
            time.sleep_ms(sleep_duration)
            loop_count += 1

            # Optional: Periodic garbage collection & Debug Print
            if loop_count % 250 == 0: # Approx every 5 seconds
                gc.collect()
                print(f"Loop {loop_count}, Mem: {gc.mem_free()}, RMS: {current_noise_rms:.1f}, Alert: {alert_active}")

    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
    finally:
        # --- Cleanup resources ---
        print("Cleaning up resources...")
        if pixels: # Turn off LEDs first
             try:
                 pixels.fill((0,0,0))
                 pixels.write()
                 print("NeoPixel LEDs turned off.")
             except Exception as e: print(f"Error turning off LEDs: {e}")
        if i2s:
            try: i2s.deinit(); print("I2S deinitialized.")
            except Exception as e: print(f"Error deinit I2S: {e}")
        if display:
            try:
                bl_pin = Pin(LCD_BL_PIN, Pin.OUT)
                bl_pin.value(0)
                print("Display backlight off.")
            except Exception as e:
                print(f"Warn: Could not turn off backlight: {e}")
        if wifi and wifi.active():
            try: wifi.active(False); print("WiFi deactivated.")
            except Exception as e: print(f"Error deactivating WiFi: {e}")
        if ble and ble.active():
            try: ble.active(False); print("Bluetooth deactivated.")
            except Exception as e: print(f"Error deactivating BLE: {e}")

        print("Cleanup complete. Application finished.")