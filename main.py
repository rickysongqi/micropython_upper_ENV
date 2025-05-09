# main.py
# Application to manage Wi-Fi, BLE, Keypad, LCD (ST7789),
# I2C Sensors, I2S Mic, WS2812 LEDs, and Multi-Page UI.
# --- VERSION WITH MULTI-PAGE UI ---

import gc
import time
import network
import struct
import math
from machine import Pin, SPI, I2C, I2S, SoftSPI, PWM
import socket
import json
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

# --- Import custom BLE Manager ---
try:
    import ble_manager
except ImportError:
    print("CRITICAL: Failed to import 'ble_manager.py'. BLE functions disabled.")
    ble_manager = None


# --- 2. Define constants and configuration ---
I2S_DEBUG_VERBOSE = True
WIFI_SSID = "501_2.4G" # Keep your SSID
WIFI_PASSWORD = "12340000" # Keep your Password
BLE_DEVICE_NAME = "ESP32S3_Sensor" # Used by ble_manager
BLE_ADVERTISEMENT_INTERVAL_US = 100000 # Used by ble_manager
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

BUZZER_PIN = 4 # <<< 新增：定义蜂鸣器引脚
BUZZER_FREQ = 4000 # <<< 新增：定义蜂鸣器频率 (Hz)

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
# <<< 新增：为 dB 显示添加布局常量 >>>
Y_BOTTOM_ROW_3_P0 = Y_BOTTOM_ROW_2_P0 + FONT_HEIGHT + PADDING
X_DB_LABEL_P0 = PADDING
X_DB_VALUE_P0 = 70 # 与 Mem 值对齐

# -- Layout Page 1: Network Details --
Y_TITLE_P1 = PADDING + 5
X_TITLE_P1 = PADDING
Y_WIFI_ICON_P1 = Y_TITLE_P1 + FONT_HEIGHT + PADDING * 2
X_WIFI_ICON_P1 = PADDING
X_SSID_LABEL_P1 = X_WIFI_ICON_P1 + 30 # Space after icon
Y_SSID_P1 = Y_WIFI_ICON_P1
X_SSID_VALUE_P1 = X_SSID_LABEL_P1 + 70 # Align value start

# 调整IP地址显示位置
Y_IP_P1 = Y_SSID_P1 + FONT_HEIGHT + PADDING * 2  # 增加垂直间距
X_IP_LABEL_P1 = PADDING  # 将标签移到最左边
X_IP_VALUE_P1 = X_IP_LABEL_P1 + 40  # 减小标签和值之间的距离，给值留更多空间

# 调整其他网络信息的位置
Y_MASK_P1 = Y_IP_P1 + FONT_HEIGHT + PADDING * 2  # 增加垂直间距
X_MASK_LABEL_P1 = X_IP_LABEL_P1
X_MASK_VALUE_P1 = X_IP_VALUE_P1

Y_GW_P1 = Y_MASK_P1 + FONT_HEIGHT + PADDING * 2  # 增加垂直间距
X_GW_LABEL_P1 = X_IP_LABEL_P1
X_GW_VALUE_P1 = X_IP_VALUE_P1

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

# --- BLE UUIDs and Flags (REMOVED - Now in ble_manager.py) ---
# _IRQ_CENTRAL_CONNECT = const(1)
# ... and all other BLE specific constants like _FLAG_READ, _ENV_SENSE_UUID etc.
# _ENV_SENSE_SERVICE = ( ... ) # Definition moved

# --- Global BLE State (REMOVED - Now managed by ble_manager.py) ---
# ble_conn_handle = None
# ble_temp_handle = None
# ... etc.
# ble_notify_enabled = { ... }
# ble_adv_payload = None
# ble_adv_interval_us = 100000

# --- Helper functions to pack sensor data according to BLE standards (REMOVED - Now in ble_manager.py) ---
# def _pack_sint16_scaled(...):
# def _pack_uint16_scaled(...):
# def _pack_uint24_scaled(...):

# --- BLE IRQ Handler (REMOVED - Now in ble_manager.py as _irq_handler) ---
# def _ble_irq(event, data):
#    ...

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

def init_ble(device_name, adv_interval):
    """Initializes Bluetooth LE using the ble_manager."""
    if ble_manager:
        print(f"Initializing BLE via ble_manager with name: {device_name}")
        if ble_manager.initialize(device_name, adv_interval):
            print("BLE initialization successful via ble_manager.")
            return True # Indicates success
        else:
            print("BLE initialization failed via ble_manager.")
            return False # Indicates failure
    else:
        print("ble_manager not available. BLE initialization skipped.")
        return False

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
    global spi, lcd_bl_pwm, pin_bl_obj_fallback
    display_dev = None
    pin_bl_obj_fallback = None # 在函数开始处也初始化/重置
    print("--- Starting Display Initialization ---")
    pin_rst = None; pin_dc = None; pin_cs = None; pin_bl_obj = None
    try:
        pin_rst = Pin(LCD_RST_PIN, Pin.OUT) if LCD_RST_PIN is not None else None
        pin_dc = Pin(LCD_DC_PIN, Pin.OUT)
        pin_cs = Pin(LCD_CS_PIN, Pin.OUT) if LCD_CS_PIN is not None else None
        
        # --- MODIFIED: LCD Backlight Pin Handling for PWM ---
        if LCD_BL_PIN is not None:
            try:
                pin_bl_obj = Pin(LCD_BL_PIN, Pin.OUT) # 首先尝试作为普通 GPIO
                # 初始化 PWM 对象用于背光控制
                lcd_bl_pwm = PWM(pin_bl_obj)
                lcd_bl_pwm.freq(1000)  # 设置 PWM 频率 (例如 1kHz)
                lcd_bl_pwm.duty_u16(65535) # 默认全亮度 (16位占空比)
                print(f"LCD Backlight Pin {LCD_BL_PIN} initialized as PWM.")
                pin_bl_obj_fallback = None # PWM成功，不需要后备GPIO对象
            except Exception as e_pwm:
                print(f"Warning: Could not initialize LCD_BL_PIN {LCD_BL_PIN} as PWM: {e_pwm}.")
                print("Falling back to simple ON/OFF for backlight if PWM failed.")
                lcd_bl_pwm = None # PWM 初始化失败
                if pin_bl_obj: # 如果GPIO对象已创建
                    pin_bl_obj_fallback = pin_bl_obj # 使用此对象进行简单开关
                    pin_bl_obj_fallback.value(1) # 默认打开
                else:
                    pin_bl_obj_fallback = None # GPIO也未成功创建
        else:
            lcd_bl_pwm = None # 没有背光引脚
            pin_bl_obj_fallback = None

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
            reset=pin_rst, dc=pin_dc, cs=pin_cs, backlight=None,
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
        display.write(default_font, "Mem:", X_MEM_LABEL_P0, Y_BOTTOM_ROW_2_P0, COLOR_LABEL, COLOR_BG)
        # <<< 新增：绘制 dB 标签 >>>
        display.write(default_font, "dB:", X_DB_LABEL_P0, Y_BOTTOM_ROW_3_P0, COLOR_LABEL, COLOR_BG)
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
    # <<< 新增：重置 dB 字符串状态 >>>
    global prev_decibel_str

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
    prev_decibel_str = None # <<< 新增
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

def update_leds(pixels, current_time_ms, alert_status, effective_leds_enabled):
    """Handles updating the WS2812 LEDs with individual brightness/phase and gamma correction.
    'effective_leds_enabled' combines physical and BLE control."""
    global alert_active, alert_flash_step, alert_next_action_time
    global buzzer_pwm # <<< 访问全局蜂鸣器 PWM 对象
    # --- NEW: Access BLE control state for buzzer ---
    ble_buzzer_logic_enabled = True # Default to true if ble_manager not available
    if ble_manager:
        ble_buzzer_logic_enabled = ble_manager.get_buzzer_alert_logic_enabled_ble()


    if not pixels and not buzzer_pwm: return

    # 检查 LED 是否被禁用 (基于组合状态)
    if not effective_leds_enabled: # MODIFIED: Use effective_leds_enabled
        if pixels and any(pixels): 
            pixels.fill((0, 0, 0))
            pixels.write()
        # 确保在禁用 LED 时蜂鸣器也停止 (如果蜂鸣器逻辑也关闭或LED关闭意味着一切关闭)
        # 这里的逻辑是：如果effective_leds_enabled为false，则LED不亮。
        # 蜂鸣器的警报逻辑与此独立，受 ble_buzzer_logic_enabled 和 alert_active 控制。
        # 所以，这里不应仅仅因为LED关闭就关闭蜂鸣器，除非设计如此。
        # 警报期间的蜂鸣器在下面处理。
        # 正常模式下蜂鸣器应关闭，在下面处理。
        pass # LED部分已处理

    if alert_active:
        # --- 警报逻辑 ---
        if current_time_ms >= alert_next_action_time:
            step = alert_flash_step % (ALERT_TOTAL_FLASHES * 2)
            if step % 2 == 0: # ON 步骤
                if pixels and effective_leds_enabled: pixels.fill(ALERT_COLOR); pixels.write() # MODIFIED
                # <<< MODIFIED: 启动蜂鸣器，但要检查BLE控制 >>>
                if buzzer_pwm and ble_buzzer_logic_enabled: # Check BLE setting
                    buzzer_pwm.freq(BUZZER_FREQ)
                    buzzer_pwm.duty_u16(32768) # 50% 占空比
                alert_next_action_time = current_time_ms + ALERT_FLASH_ON_MS
            else: # OFF 步骤
                if pixels and effective_leds_enabled: pixels.fill((0, 0, 0)); pixels.write() # MODIFIED
                # <<< MODIFIED: 停止蜂鸣器 (如果之前启动了) >>>
                if buzzer_pwm and ble_buzzer_logic_enabled: # Check BLE setting (though it would have been off anyway if not enabled)
                    buzzer_pwm.duty_u16(0) # 关闭
                alert_next_action_time = current_time_ms + ALERT_FLASH_OFF_MS
            alert_flash_step += 1
            if alert_flash_step >= ALERT_TOTAL_FLASHES * 2:
                alert_active = False
                # <<< MODIFIED: 确保警报结束后蜂鸣器停止 (如果之前启动了) >>>
                if buzzer_pwm and ble_buzzer_logic_enabled:
                    buzzer_pwm.duty_u16(0)
        return # 警报期间不运行正常效果

    # --- 正常呼吸效果 ---
    # <<< 新增：确保正常模式下蜂鸣器是关闭的 >>>
    if buzzer_pwm and buzzer_pwm.duty_u16() > 0: # 如果蜂鸣器还在响，关闭它
        buzzer_pwm.duty_u16(0)

    if not pixels or not effective_leds_enabled: # MODIFIED: Check effective_leds_enabled
        # 如果LED被禁用（物理或蓝牙），即使pixels对象存在，也在此处返回，不执行呼吸效果
        if pixels and any(pixels): # 确保如果从使能状态变为禁用，LED确实关闭
            pixels.fill((0,0,0))
            pixels.write()
        return

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

    # Initialize BLE using the new function, passing constants from main.py
    ble_initialized_successfully = init_ble(BLE_DEVICE_NAME, BLE_ADVERTISEMENT_INTERVAL_US)
    # The actual 'ble' object is now managed within ble_manager

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

    # <<< 新增：初始化蜂鸣器 PWM >>>
    try:
        buzzer_pin_obj = Pin(BUZZER_PIN, Pin.OUT)
        buzzer_pwm = PWM(buzzer_pin_obj)
        buzzer_pwm.duty_u16(0) # 初始关闭
        buzzer_pwm.freq(BUZZER_FREQ) # 设置默认频率
        print(f"Buzzer PWM initialized on Pin {BUZZER_PIN}.")
    except Exception as e:
        print(f"Error initializing Buzzer PWM: {e}")
        buzzer_pwm = None # 初始化失败则设为 None

    # --- Main loop state variables ---
    current_page = PAGE_MAIN
    last_key_press_time = 0 # For debouncing page switch
    last_right_key_press_time = 0 # NEW: Debounce timer for right key LED toggle
    # leds_enabled is now the PHYSICAL button state.
    # BLE control will be checked separately.
    physical_leds_enabled = True # Renamed from leds_enabled

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
    prev_mem_free_str = None
    # <<< 新增：dB 显示状态 >>>
    prev_decibel_str = None
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
    # <<< 新增：当前 dB 值变量 >>>
    current_decibel_val = 0.0 # 用于存储计算出的相对 dB 值

    # --- NEW: LCD Backlight PWM global reference (initialized in init_display) ---
    lcd_bl_pwm = None # Will be assigned in init_display if successful

    # <<< 新增：在主循环外或开始处定义当前客户端状态变量 >>>
    current_client_socket = None
    current_client_addr = None

    gc.collect()
    print(f"Initial free memory: {gc.mem_free()} bytes")
    print(f"[MAIN] Peripherals initialized. Entering main loop...")

    # --- Main Loop ---
    try:
        while True:
            current_time_ms = time.ticks_ms()
            page_changed = False # Flag to check if page was switched this iteration

            # --- NEW: Get BLE control states ---
            ble_led_control_on = True
            ble_buzzer_logic_enabled = True
            ble_screen_on = True
            ble_screen_brightness_val = 255 # 0-255
            if ble_manager and ble_initialized_successfully:
                ble_led_control_on = ble_manager.get_led_control_state_ble()
                ble_buzzer_logic_enabled = ble_manager.get_buzzer_alert_logic_enabled_ble()
                ble_screen_on = ble_manager.get_screen_state_ble()
                ble_screen_brightness_val = ble_manager.get_screen_brightness_ble()
            
            # --- Determine effective LED enabled state ---
            # Combines physical button toggle AND BLE control setting
            effective_leds_enabled_this_loop = physical_leds_enabled and ble_led_control_on


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
                        physical_leds_enabled = not physical_leds_enabled # Toggle the PHYSICAL state
                        print(f"Physical LEDs {'Enabled' if physical_leds_enabled else 'Disabled'}")
                        last_right_key_press_time = current_time_ms # Update right key debounce timer
                        # Optional: Force update LEDs immediately after toggle
                        # The main LED update call later in the loop will handle this.
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
                    
                    # --- MODIFIED: Check BLE buzzer logic before activating alert with sound ---
                    # Alert visual (LED) will still happen based on effective_leds_enabled_this_loop
                    if temp_trig or humi_trig or lux_trig:
                        print(f"ALERT: T:{temp_trig}/{temp_diff:.1f} H:{humi_trig}/{humi_diff:.1f} L:{lux_trig}/{lux_diff:.1f}")
                        alert_active = True # Activate alert state
                        alert_flash_step = 0
                        alert_next_action_time = current_time_ms
                        # The buzzer part of the alert is handled in update_leds, which checks ble_buzzer_logic_enabled

                prev_temperature_val = current_temperature_val
                prev_humidity_val = current_humidity_val
                prev_lux_val = current_lux_val

                # --- SEND BLE NOTIFICATIONS/INDICATIONS via ble_manager ---
                if ble_manager and ble_initialized_successfully:
                    ble_manager.update_sensor_data_and_send( # MODIFIED: Renamed function call
                        current_temperature_val,
                        current_humidity_val,
                        current_lux_val,
                        current_noise_rms # Pass current_noise_rms, which is the smoothed value
                    )
                # --- END BLE SEND ---

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

                               # <<< 新增：计算相对分贝值 >>>
                               if current_noise_rms > 0:
                                   # 使用 max(1.0, rms) 避免 log10(<=0) 问题并设置基线
                                   # 这提供了一个相对 dB 值，不是绝对 dB SPL
                                   try:
                                       # 注意：micropython 可能没有 math.log10，但有 math.log
                                       # log10(x) = log(x) / log(10)
                                       # log(10) 约等于 2.302585
                                       current_decibel_val = 20 * (math.log(max(1.0, current_noise_rms)) / 2.302585)
                                   except (ValueError, AttributeError): # 处理可能的错误或缺失 log
                                       current_decibel_val = 0.0 # 或错误指示符
                               else:
                                   current_decibel_val = 0.0 # 对于静音或错误，显示 0 dB

                               # --- Check RMS Trigger (using raw value against previous raw value) ---
                               if prev_rms_val >= 0 and not alert_active:
                                   rms_diff = raw_rms_value_this_cycle - prev_rms_val # Compare raw vs raw
                                   if rms_diff >= RMS_THRESHOLD_DIFF:
                                       print(f"ALERT TRIGGER: RMS increased by {rms_diff:.1f} (Raw: {raw_rms_value_this_cycle:.1f})")
                                       # --- MODIFIED: Activate alert state, buzzer handled in update_leds ---
                                       alert_active = True 
                                       alert_flash_step = 0
                                       alert_next_action_time = current_time_ms
                               prev_rms_val = raw_rms_value_this_cycle # Update previous *raw* value for next comparison

                               # --- SEND BLE NOTIFICATION (Noise) via ble_manager ---
                               # This is now handled by the single call to update_sensor_data_and_notify
                               # which includes the noise data.
                               # if ble_manager and ble_initialized_successfully and ble_manager.is_connected():
                               #    if _notify_enabled_flags in ble_manager (internal) for noise is true:
                               #        # The actual send happens in update_sensor_data_and_notify
                               #        pass
                               # --- END BLE NOTIFICATION (Noise) ---

                           else: # calculated_rms < 0 (Error)
                               # Keep the last known smoothed value for display
                               print(f"[RMS CALC] Error calculating RMS.")
                               # Optionally reset prev_rms_val if error is persistent
                               # prev_rms_val = -1
                               # <<< 新增：在 RMS 计算错误时也设置 dB 为 0 >>>
                               current_decibel_val = 0.0
                except Exception as e:
                    # Keep the last known smoothed value for display
                    print(f"[I2S READ] ERROR: {e}")
                    # <<< 新增：在 I2S 读取错误时也设置 dB 为 0 >>>
                    current_decibel_val = 0.0

            # Format string for display uses the SMOOTHED value (current_noise_rms)
            current_noise_level_str = f"{current_noise_rms:.1f}" if current_noise_rms >= 0 else "Err" # Display smoothed value
            # <<< 新增：格式化 dB 值字符串 >>>
            current_decibel_str = f"{current_decibel_val:.1f}dB"

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
            # Get status from ble_manager
            ble_is_active_status = False
            ble_is_connected_status = False
            if ble_manager and ble_initialized_successfully:
                ble_is_active_status = ble_manager.is_active()
                ble_is_connected_status = ble_manager.is_connected()

            current_ble_status_str_p0 = f"BLE{'✓' if ble_is_connected_status else ('-' if ble_is_active_status else '✗')}"
            ble_status_color_p0 = COLOR_STATUS_OK if ble_is_connected_status else (COLOR_STATUS_WARN if ble_is_active_status else COLOR_STATUS_BAD)

            # --- g. Get Memory Status (Timed) ---
            current_mem_free_str = prev_mem_free_str if prev_mem_free_str is not None else "N/A"
            if time.ticks_diff(current_time_ms, last_mem_update_ms) >= mem_update_interval_ms:
                 last_mem_update_ms = current_time_ms
                 current_mem_free_str = f"{gc.mem_free()}"
            current_mem_free_val = gc.mem_free() # Get current value for TCP response

            # === REVISED TCP SERVER HANDLING ===
            # --- Check for data from existing client OR accept new connection ---

            # 1. 处理当前连接的客户端
            if current_client_socket is not None:
                try:
                    # 设置非常短的超时或非阻塞模式读取
                    current_client_socket.setblocking(False) # 设置为非阻塞
                    command_bytes = None
                    try:
                        command_bytes = current_client_socket.readline()
                    except OSError as read_e:
                        # 在非阻塞模式下，如果没有数据会引发 OSError (EAGAIN/EWOULDBLOCK)
                        if read_e.args[0] == 11: # EAGAIN / EWOULDBLOCK
                             pass # 没有数据，正常，继续主循环
                        else:
                             raise # 其他读取错误，抛出给外层处理

                    current_client_socket.setblocking(True) # 读完后恢复阻塞模式（可选，看后续操作）

                    if command_bytes == b'': # 空字节串通常表示连接已关闭
                        print(f"客户端 {current_client_addr} 主动断开连接")
                        current_client_socket.close()
                        current_client_socket = None
                        current_client_addr = None
                    elif command_bytes is not None: # 收到有效数据
                        command = command_bytes.decode('utf-8').strip()
                        print(f"收到来自 {current_client_addr} 的命令: {command}")

                        # --- 处理命令 ---
                        if command == "GET_CURRENT":
                            data = {
                                "timestamp_ms": current_time_ms,
                                "page": current_page,
                                "wifi_status": "Connected" if wifi_connected else "Disconnected",
                                "ble_status": "Active" if ble_is_active_status else "Inactive",
                                "temperature_c": current_temperature_val if current_temperature_val > -990 else None,
                                "humidity_percent": current_humidity_val if current_humidity_val > -990 else None,
                                "lux": current_lux_val if current_lux_val > -990 else None,
                                "noise_rms_smoothed": current_noise_rms if current_noise_rms >= 0 else None,
                                "keys_pressed": current_pressed_key_names,
                                "mem_free_bytes": current_mem_free_val
                            }
                            response_json = json.dumps(data)
                            try:
                                current_client_socket.sendall((response_json + '\n').encode('utf-8'))
                                print(f"已发送当前数据到 {current_client_addr}")
                            except Exception as send_e:
                                print(f"发送数据到 {current_client_addr} 时出错: {send_e}")
                                current_client_socket.close()
                                current_client_socket = None
                                current_client_addr = None
                        elif command == "GET_HISTORY":
                            # ... (处理 HISTORY 命令) ...
                             try:
                                current_client_socket.sendall(b"HISTORY_NOT_IMPLEMENTED\n")
                                print(f"已发送 HISTORY_NOT_IMPLEMENTED 到 {current_client_addr}")
                             except Exception as send_e:
                                print(f"发送数据到 {current_client_addr} 时出错: {send_e}")
                                current_client_socket.close()
                                current_client_socket = None
                                current_client_addr = None
                        else:
                            # ... (处理未知命令) ...
                             try:
                                current_client_socket.sendall(b"UNKNOWN_COMMAND\n")
                                print(f"已发送 UNKNOWN_COMMAND 到 {current_client_addr}")
                             except Exception as send_e:
                                print(f"发送数据到 {current_client_addr} 时出错: {send_e}")
                                current_client_socket.close()
                                current_client_socket = None
                                current_client_addr = None
                        # 注意：处理完一个命令后，不会 break，等待下一次主循环再读取

                except Exception as client_e:
                    # 处理当前客户端时发生错误
                    print(f"处理客户端 {current_client_addr} 时出错: {client_e}")
                    if current_client_socket:
                        current_client_socket.close()
                    current_client_socket = None
                    current_client_addr = None

            # 2. 如果没有客户端连接，尝试接受新连接
            elif server_socket: # 只有在 server_socket 初始化成功时才尝试
                try:
                    # 使用 accept 的超时或非阻塞模式
                    # server_socket 本身在初始化时设置了 settimeout(0.1)
                    new_client_socket, new_addr = server_socket.accept()
                    print(f"接受到新的 TCP 连接，来自: {new_addr}")

                    # 如果已有连接，则拒绝新连接（简单策略，也可选择断开旧的）
                    # if current_client_socket is not None:
                    #    print(f"已有客户端连接，拒绝新连接 {new_addr}")
                    #    new_client_socket.close()
                    # else:

                    # 保存新连接
                    current_client_socket = new_client_socket
                    current_client_addr = new_addr
                    # 设置新 socket 为非阻塞或短超时，以便后续读取
                    current_client_socket.setblocking(False) # 设置非阻塞读取

                    # 发送 CONNECTED 消息
                    try:
                        current_client_socket.setblocking(True) # 发送时临时用阻塞
                        current_client_socket.sendall(b"CONNECTED\n")
                        current_client_socket.setblocking(False) # 恢复非阻塞
                    except Exception as send_e:
                        print(f"发送 CONNECTED 到 {new_addr} 时出错: {send_e}")
                        current_client_socket.close()
                        current_client_socket = None
                        current_client_addr = None

                except OSError as e:
                    # 这是预期的，如果没有等待连接
                    expected_errnos = (11, 116) # EAGAIN/EWOULDBLOCK, ETIMEDOUT
                    if e.args[0] in expected_errnos:
                        pass # 没有等待的连接，正常，继续主循环
                    else:
                        print(f"服务器 socket accept 错误: {e}")
                except Exception as e:
                    print(f"服务器 accept 时发生意外错误: {e}")

            # === END OF REVISED TCP SERVER HANDLING ===

            # --- NEW: Screen On/Off and Brightness Control via BLE ---
            if lcd_bl_pwm: # If PWM for backlight is available
                if ble_screen_on:
                    # Convert 0-255 brightness from BLE to 0-65535 for duty_u16
                    duty_cycle = int((ble_screen_brightness_val / 255) * 65535)
                    lcd_bl_pwm.duty_u16(duty_cycle)
                else:
                    lcd_bl_pwm.duty_u16(0) # Screen off via PWM
            elif pin_bl_obj_fallback: # Fallback to simple GPIO control
                if ble_screen_on:
                    pin_bl_obj_fallback.value(1) # Screen on
                else:
                    pin_bl_obj_fallback.value(0) # Screen off
            # If both are None, no BLE backlight control is possible

            # --- h. Update Display based on Current Page ---
            # --- MODIFIED: Only update display if screen is supposed to be ON via BLE ---
            if display and default_font and ble_screen_on:
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
                    prev_mem_free_str = update_text_field(display, X_MEM_VALUE_P0, Y_BOTTOM_ROW_2_P0, current_mem_free_str, prev_mem_free_str, default_font, COLOR_MEM, COLOR_BG)
                    # <<< 新增：更新 dB 显示 >>>
                    prev_decibel_str = update_text_field(display, X_DB_VALUE_P0, Y_BOTTOM_ROW_3_P0, current_decibel_str, prev_decibel_str, default_font, COLOR_VALUE, COLOR_BG)
                elif current_page == PAGE_NETWORK:
                    prev_wifi_icon_str_p1 = update_text_field(display, X_WIFI_ICON_P1, Y_WIFI_ICON_P1, current_wifi_icon_str_p1, prev_wifi_icon_str_p1, default_font, wifi_status_color_p0, COLOR_BG) # Use same color as status
                    prev_ssid_str_p1 = update_text_field(display, X_SSID_VALUE_P1, Y_SSID_P1, current_ssid_str_p1, prev_ssid_str_p1, default_font, COLOR_VALUE, COLOR_BG)
                    prev_ip_str_p1 = update_text_field(display, X_IP_VALUE_P1, Y_IP_P1, current_ip_str_p1, prev_ip_str_p1, default_font, COLOR_VALUE, COLOR_BG)
                    prev_mask_str_p1 = update_text_field(display, X_MASK_VALUE_P1, Y_MASK_P1, current_mask_str_p1, prev_mask_str_p1, default_font, COLOR_VALUE, COLOR_BG)
                    prev_gw_str_p1 = update_text_field(display, X_GW_VALUE_P1, Y_GW_P1, current_gw_str_p1, prev_gw_str_p1, default_font, COLOR_VALUE, COLOR_BG)


            # --- i. Update WS2812 LEDs (Timed) ---
            if (pixels or buzzer_pwm) and time.ticks_diff(current_time_ms, last_led_update_ms) >= LED_UPDATE_INTERVAL_MS:
                last_led_update_ms = current_time_ms
                # Pass alert_active status and the *effective* LED enabled state
                update_leds(pixels, current_time_ms, alert_active, effective_leds_enabled_this_loop)

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
        if current_client_socket: # <<< 新增：清理当前客户端连接 >>>
            try: current_client_socket.close(); print("Closed any active client socket.")
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
        
        # --- MODIFIED: Display cleanup ---
        if lcd_bl_pwm: # If PWM was used for backlight
            try: 
                lcd_bl_pwm.duty_u16(0) # Turn off backlight
                lcd_bl_pwm.deinit()
                print("LCD Backlight PWM deinitialized and turned off.")
            except Exception as e: print(f"Warn: Could not deinit/off backlight PWM: {e}")
        elif pin_bl_obj_fallback: # Fallback for simple backlight pin
            try:
                pin_bl_obj_fallback.value(0) # Turn off backlight
                print("LCD Backlight simple GPIO turned off.")
                # Pin objects usually don't need deinit unless reconfigured,
                # but good practice if no longer used.
                # pin_bl_obj_fallback.init(Pin.IN) 
            except Exception as e: print(f"Warn: Could not turn off simple backlight GPIO: {e}")
        elif display: 
            # This assumes init_display might have used a simple Pin object for backlight
            # For now, we rely on the st7789 driver not needing explicit backlight pin deinit,
            # or that it's handled if 'backlight' arg was passed to ST7789 constructor.
            # If LCD_BL_PIN was set but PWM init failed, init_display might have set pin_bl_obj.value(1)
            # We would need a global reference to pin_bl_obj to control it here.
            # Let's refine init_display to make pin_bl_obj global if PWM fails.
            try:
                # If st7789 driver has a way to turn off backlight, call it here.
                # Example: if hasattr(display, 'backlight') and callable(display.backlight): display.backlight(0)
                # Or, if we made pin_bl_obj global in init_display on PWM fail:
                # global pin_bl_obj_fallback # (would need to be defined globally)
                # if pin_bl_obj_fallback: pin_bl_obj_fallback.value(0)
                print("Display object exists, specific backlight pin turn-off not explicitly handled here without PWM.")
            except Exception as e: print(f"Warn: Error during non-PWM display cleanup: {e}")
            
        if wifi and wifi.active():
            try: wifi.active(False); print("WiFi deactivated.")
            except Exception as e: print(f"Error deactivating WiFi: {e}")
        
        # Deinitialize BLE via ble_manager
        if ble_manager and ble_initialized_successfully:
            try:
                ble_manager.deinitialize()
                print("BLE deinitialized via ble_manager.")
            except Exception as e:
                print(f"Error deinitializing BLE via ble_manager: {e}")

        if buzzer_pwm: # <<< 新增：清理蜂鸣器 PWM >>>
             try: buzzer_pwm.deinit(); print("Buzzer PWM deinitialized.")
             except Exception as e: print(f"Error deinit Buzzer PWM: {e}")
        print("Cleanup complete. Application finished.")