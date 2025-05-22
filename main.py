# main.py
# 管理 Wi-Fi、BLE、键盘、LCD (ST7789)、
# I2C 传感器、I2S 麦克风、WS2812 LED 和多页面 UI 的应用程序。
# --- 多页面 UI 版本 ---

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
    print("警告：未找到 webrepl 模块。WebREPL 已禁用。")
    webrepl = None

try:
    import neopixel
except ImportError:
    print("错误：未找到 neopixel 库。WS2812 功能已禁用。")
    neopixel = None

# --- 1. 导入必要的驱动/字体模块 ---
# (现有导入保持不变)
try:
    import st7789
except ImportError:
    print("错误：ST7789 驱动程序 (st7789.py) 未找到。")
    st7789 = None
try:
    import si7021
except ImportError:
    print("错误：SI7021 驱动程序 (si7021.py) 未找到。")
    si7021 = None
try:
    import bh1750
except ImportError:
    print("错误：BH1750 驱动程序 (bh1750.py) 未找到。")
    bh1750 = None
try:
    import ubuntu_24 as default_font
except ImportError:
    print("错误：转换的字体模块 ('ubuntu_24.py') 未找到。")
    default_font = None

# --- 导入自定义 BLE 管理器 ---
try:
    import ble_manager
except ImportError:
    print("严重：无法导入 'ble_manager.py'。BLE 功能已禁用。")
    ble_manager = None

# --- Import GUIManager and its constants ---
try:
    from gui_manager import GUIManager, PAGE_MAIN, PAGE_NETWORK, NUM_PAGES, \
                              X_WIFI_STATUS_P0, Y_STATUS_LINE_P0, X_BLE_STATUS_P0, \
                              X_WIFI_ICON_P1, Y_WIFI_ICON_P1, X_SSID_VALUE_P1, Y_SSID_P1, \
                              X_IP_VALUE_P1, Y_IP_P1, X_MASK_VALUE_P1, Y_MASK_P1, \
                              X_GW_VALUE_P1, Y_GW_P1, \
                              COLOR_STATUS_OK, COLOR_STATUS_BAD, COLOR_VALUE, COLOR_MEM, COLOR_BG, COLOR_STATUS_WARN, COLOR_PAGE_INDICATOR, \
                              X_LABEL_P0, X_VALUE_P0, Y_TEMP_ROW_P0, Y_HUMI_ROW_P0, Y_LUX_ROW_P0, Y_NOISE_RMS_ROW_P0, Y_NOISE_DB_ROW_P0 # 保留新的 P0 布局常量
    # 已移除旧的 P0 布局常量：
    # X_TEMP_VALUE_P0, Y_SENSOR_ROW_1_P0, X_HUM_VALUE_P0,
    # X_LUX_VALUE_P0, Y_SENSOR_ROW_2_P0, X_NOISE_VALUE_P0,
    # X_MEM_VALUE_P0, Y_BOTTOM_ROW_2_P0, X_DB_VALUE_P0, Y_BOTTOM_ROW_3_P0

    # 注意：default_font 和 st7789 被传递给 GUIManager，
    # 所以如果通过 GUIManager 访问，这里不严格需要直接导入它们的常量
except ImportError as e: # 捕获特定错误
    print(f"严重：无法从 'gui_manager.py' 导入。UI 功能已禁用。错误：{e}")
    GUIManager = None
    # 如果需要，定义常量的后备值
    PAGE_MAIN, PAGE_NETWORK, NUM_PAGES = 0, 1, 2 # 示例后备值
    COLOR_STATUS_OK, COLOR_STATUS_BAD, COLOR_VALUE, COLOR_MEM, COLOR_BG, COLOR_STATUS_WARN, COLOR_PAGE_INDICATOR = 0,0,0,0,0,0,0

# --- Import AlertManager ---
try:
    from alert_manager import AlertManager, ALERT_MODE_DIFFERENCE, ALERT_MODE_THRESHOLD_ABSOLUTE
except ImportError:
    print("严重：无法导入 'alert_manager.py'。警报功能已禁用。")
    AlertManager = None
    # 如果 AlertManager 导入失败，为常量定义后备值，以防止后续的 NameError
    ALERT_MODE_DIFFERENCE = 0 
    ALERT_MODE_THRESHOLD_ABSOLUTE = 1

# --- 定义警报颜色（目前为全局，用于 update_leds） ---
ALERT_COLOR = (255, 0, 0)

# --- 2. 定义常量和配置 ---
I2S_DEBUG_VERBOSE = True
WIFI_SSID = "501_2.4G" # 保留您的 SSID
WIFI_PASSWORD = "12340000" # 保留您的密码
BLE_DEVICE_NAME = "ESP32S3_Sensor" # 被 ble_manager 使用
BLE_ADVERTISEMENT_INTERVAL_US = 100000 # 被 ble_manager 使用
SERVER_PORT = 8888 # <<< 定义服务器端口

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
# NUM_PAGES = 2 # Moved to gui_manager.py, imported back
# PAGE_MAIN = 0 # Moved to gui_manager.py, imported back
# PAGE_NETWORK = 1 # Moved to gui_manager.py, imported back

# --- UI Layout and Style Constants ---
# All COLOR_* constants moved to gui_manager.py
# PADDING, FONT_HEIGHT moved to gui_manager.py
# All X_*, Y_* layout constants moved to gui_manager.py

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
# ALERT_COLOR, ALERT_FLASH_ON_MS, ALERT_FLASH_OFF_MS, ALERT_TOTAL_FLASHES moved to alert_manager.py
# ALERT_COLOR = (255, 0, 0) 
# ALERT_FLASH_ON_MS = 150
# ALERT_FLASH_OFF_MS = 100
# ALERT_TOTAL_FLASHES = 2

# --- Sensor Trigger Thresholds (Tune!) --- (MOVED to alert_manager.py as defaults)
# TEMP_THRESHOLD_DIFF = 3.0
# HUMI_THRESHOLD_DIFF = 15.0
# LUX_THRESHOLD_DIFF = 500.0
# RMS_THRESHOLD_DIFF = 1500.0

# --- Key Debounce ---
KEY_DEBOUNCE_MS = 200 # 防止快速页面切换

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
    """
    初始化并连接到指定的 Wi-Fi 网络。
    
    参数:
        ssid (str): 网络的 SSID（名称）
        password (str): 网络的密码
    
    返回:
        network.WLAN: 成功连接时返回网络接口对象，否则返回 None
    """
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print(f"正在连接 WiFi 网络 '{ssid}'...")
        sta_if.active(True)
        try:
            sta_if.connect(ssid, password)
            # 带超时的连接等待
            max_wait = 15
            while max_wait > 0:
                if sta_if.isconnected():
                    break
                max_wait -= 1
                print(".", end="")
                time.sleep(1)

            if sta_if.isconnected():
                print("\nWiFi 已连接！")
                print("网络配置：", sta_if.ifconfig())
                return sta_if
            else:
                print("\nWiFi 连接超时。")
                sta_if.active(False) # 连接失败时关闭
                return None
        except OSError as e:
            print(f"\n连接 WiFi 时出错：{e}")
            sta_if.active(False)
            return None
    else:
        print("WiFi 已连接。")
        return sta_if

def init_ble(device_name, adv_interval):
    """使用 ble_manager 初始化蓝牙低功耗（BLE）。"""
    if ble_manager:
        print(f"通过 ble_manager 初始化 BLE，设备名称：{device_name}")
        if ble_manager.initialize(device_name, adv_interval):
            print("通过 ble_manager 成功初始化 BLE。")
            return True # 表示成功
        else:
            print("通过 ble_manager 初始化 BLE 失败。")
            return False # 表示失败
    else:
        print("ble_manager 不可用。跳过 BLE 初始化。")
        return False

def init_keypad():
    """初始化键盘 GPIO 引脚。"""
    print("正在初始化键盘...")
    keys = {
        'up': Pin(KEY_UP_PIN, Pin.IN, Pin.PULL_UP),
        'down': Pin(KEY_DOWN_PIN, Pin.IN, Pin.PULL_UP),
        'left': Pin(KEY_LEFT_PIN, Pin.IN, Pin.PULL_UP),
        'right': Pin(KEY_RIGHT_PIN, Pin.IN, Pin.PULL_UP),
        'enter': Pin(KEY_ENTER_PIN, Pin.IN, Pin.PULL_UP)
    }
    print("键盘已初始化。")
    return keys

def init_i2c_sensors():
    """初始化 I2C 总线并尝试初始化传感器。"""
    i2c = None
    sensor_th = None
    sensor_l = None
    print("正在初始化 I2C 总线...")
    try:
        i2c = I2C(I2C_ID, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=I2C_FREQ)
        print(f"I2C 总线 {I2C_ID} 已初始化。")
        devices = i2c.scan()
        print("检测到的 I2C 设备：", [hex(d) for d in devices])

        # 如果驱动已加载且设备已检测，则初始化 SI7021
        if si7021 and SI7021_ADDR in devices:
            try:
                sensor_th = si7021.SI7021(i2c)
                print("SI7021 温湿度传感器已初始化。")
            except Exception as e:
                print(f"初始化 SI7021 驱动程序时出错：{e}")
        elif si7021:
            print(f"在地址 {hex(SI7021_ADDR)} 未找到 SI7021")

        # 如果驱动已加载且设备已检测，则初始化 BH1750
        if bh1750 and BH1750_ADDR in devices:
            try:
                sensor_l = bh1750.BH1750(i2c)
                print("BH1750 光传感器已初始化。")
            except Exception as e:
                print(f"初始化 BH1750 驱动程序时出错：{e}")
        elif bh1750:
                print(f"在地址 {hex(BH1750_ADDR)} 未找到 BH1750")

    except Exception as e:
        print(f"严重：初始化 I2C 总线 {I2C_ID} 时出错：{e}")
        i2c = None

    return i2c, sensor_th, sensor_l

def init_display():
    """初始化 SPI 总线和 ST7789 LCD。"""
    global spi, lcd_bl_pwm, pin_bl_obj_fallback
    display_dev = None
    pin_bl_obj_fallback = None # 在函数开始处也初始化/重置
    print("--- 开始显示初始化 ---")
    pin_rst = None; pin_dc = None; pin_cs = None; pin_bl_obj = None
    try:
        pin_rst = Pin(LCD_RST_PIN, Pin.OUT) if LCD_RST_PIN is not None else None
        pin_dc = Pin(LCD_DC_PIN, Pin.OUT)
        pin_cs = Pin(LCD_CS_PIN, Pin.OUT) if LCD_CS_PIN is not None else None
        
        # --- 修改：LCD 背光引脚的 PWM 处理 ---
        if LCD_BL_PIN is not None:
            try:
                pin_bl_obj = Pin(LCD_BL_PIN, Pin.OUT) # 首先尝试作为普通 GPIO
                # 初始化 PWM 对象用于背光控制
                lcd_bl_pwm = PWM(pin_bl_obj)
                lcd_bl_pwm.freq(1000)  # 设置 PWM 频率 (例如 1kHz)
                lcd_bl_pwm.duty_u16(65535) # 默认全亮度 (16位占空比)
                print(f"LCD 背光引脚 {LCD_BL_PIN} 已初始化为 PWM。")
                pin_bl_obj_fallback = None # PWM成功，不需要后备GPIO对象
            except Exception as e_pwm:
                print(f"警告：无法将 LCD_BL_PIN {LCD_BL_PIN} 初始化为 PWM：{e_pwm}。")
                print("如果 PWM 失败，则回退到简单的开/关背光。")
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
        print(f"严重：初始化控制引脚时出错：{e}")
        return None

    spi = None
    try:
        print(f"--> 尝试初始化硬件 SPI ID：{LCD_SPI_ID}")
        spi = SPI(LCD_SPI_ID, baudrate=LCD_SPI_BAUDRATE,
                  sck=Pin(LCD_SCLK_PIN), mosi=Pin(LCD_MOSI_PIN),
                  miso=Pin(LCD_MISO_PIN) if LCD_MISO_PIN != -1 else None)
        print(f"  成功：硬件 SPI ID {LCD_SPI_ID} 初始化成功。")
    except Exception as e_hw_spi:
        print(f"  错误：初始化硬件 SPI ID {LCD_SPI_ID} 失败：{e_hw_spi}")
        spi = None

    if spi is None:
        print("硬件 SPI 失败。尝试软件 SPI 后备...")
        try:
             spi = SoftSPI(baudrate=10000000,
                           sck=Pin(LCD_SCLK_PIN), mosi=Pin(LCD_MOSI_PIN),
                           miso=Pin(LCD_MISO_PIN) if LCD_MISO_PIN != -1 else None)
             print("  软件 SPI 初始化成功（性能较低）。")
        except Exception as e_sw_spi:
             print(f"严重：初始化软件 SPI 失败：{e_sw_spi}")
             return None

    if st7789 is None:
        print("严重：st7789 驱动模块未加载，无法实例化。")
        if spi: spi.deinit()
        return None

    try:
        print("初始化 ST7789 驱动程序实例...")
        display_dev = st7789.ST7789(
            spi, LCD_WIDTH, LCD_HEIGHT,
            reset=pin_rst, dc=pin_dc, cs=pin_cs, backlight=None,
            rotation=LCD_ROTATION, color_order=st7789.BGR
        )
        print("显示驱动程序实例创建成功。")
    except Exception as e_driver:
        print(f"严重：初始化 ST7789 驱动程序实例时出错：{e_driver}")
        if spi: spi.deinit()
        display_dev = None

    return display_dev

def init_i2s():
    """初始化用于音频输入的 I2S 外设。"""
    i2s_dev = None
    read_buf = None
    print("[I2S 初始化] 正在初始化 I2S 麦克风...")
    try:
        sck_pin = Pin(I2S_BCLK_PIN)
        ws_pin = Pin(I2S_WS_PIN)
        sd_pin = Pin(I2S_DIN_PIN)
        i2s_dev = I2S(I2S_ID,
                      sck=sck_pin, ws=ws_pin, sd=sd_pin,
                      mode=I2S.RX, bits=I2S_BITS, format=I2S_FORMAT,
                      rate=I2S_SAMPLE_RATE, ibuf=I2S_BUFFER_LEN_IN_BYTES)
        read_buf = bytearray(I2S_READ_CHUNK_SIZE)
        print("[I2S 初始化] I2S 成功初始化。")
    except Exception as e:
        print(f"[I2S 初始化] 严重：初始化 I2S 时出错：{e}")
        if i2s_dev:
            try: i2s_dev.deinit()
            except Exception: pass
        i2s_dev = None
        read_buf = None
    return i2s_dev, read_buf

def calculate_rms(audio_buffer, bytes_read):
    """计算音频样本的均方根（RMS）。"""
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

# def draw_page_layout(display, page_index): # MOVED to GUIManager
# def reset_prev_ui_strings(): # MOVED to GUIManager
# def update_text_field(display, x, y, new_text, prev_text, font, fg_color, bg_color): # MOVED to GUIManager

def update_leds(pixels, current_time_ms, alert_status, effective_leds_enabled):
    """
    处理 WS2812 LED 的更新，包括单独的亮度/相位和伽马校正。
    'effective_leds_enabled' 结合了物理和蓝牙控制。
    """
    global alert_active, alert_flash_step, alert_next_action_time
    global buzzer_pwm # <<< 访问全局蜂鸣器 PWM 对象

    # --- 新增：访问蓝牙控制状态 ---
    ble_buzzer_logic_enabled = True # 如果 ble_manager 不可用，默认为 true
    if ble_manager:
        ble_buzzer_logic_enabled = ble_manager.get_buzzer_alert_logic_enabled_ble()

    if not pixels and not buzzer_pwm: return

    # 检查 LED 是否被禁用
    if not effective_leds_enabled:
        if pixels and any(pixels): 
            pixels.fill((0, 0, 0))
            pixels.write()
        pass

    # --- 修改：从 alert_manager 获取警报参数 ---
    # alert_status 现在是来自 alert_mgr.get_alert_flash_parameters() 的字典或 None
    is_alert_currently_active = alert_status is not None 

    if is_alert_currently_active:
        alert_flash_params = alert_status # 这是字典
        # --- 警报逻辑 ---
        if current_time_ms >= alert_flash_params["next_action_time"]:
            step = alert_flash_params["flash_step"] % (alert_flash_params["total_flashes"] * 2)
            new_flash_step = alert_flash_params["flash_step"] + 1
            new_next_action_time = 0

            if step % 2 == 0: # ON 步骤
                if pixels and effective_leds_enabled: 
                    pixels.fill(ALERT_COLOR)
                    pixels.write()
                if buzzer_pwm and ble_buzzer_logic_enabled: 
                    buzzer_pwm.freq(BUZZER_FREQ)
                    buzzer_pwm.duty_u16(32768) 
                new_next_action_time = current_time_ms + alert_flash_params["on_ms"]
            else: # OFF 步骤
                if pixels and effective_leds_enabled: 
                    pixels.fill((0, 0, 0))
                    pixels.write()
                if buzzer_pwm and ble_buzzer_logic_enabled: 
                    buzzer_pwm.duty_u16(0) 
                new_next_action_time = current_time_ms + alert_flash_params["off_ms"]
            
            # 调用 alert_manager 更新其内部状态的闪烁周期
            # 这也将在周期结束时处理 alert_manager 中的 alert_active 重置
            if 'alert_manager_instance' in globals() and alert_manager_instance:
                alert_manager_instance.update_alert_flash_state(current_time_ms, new_flash_step, new_next_action_time)

        return # 警报期间不运行正常效果

    # --- 正常呼吸效果 ---
    # --- 正常呼吸，带相位偏移和伽马校正 ---
    t = current_time_ms / 1000.0

    for i in range(NUM_LEDS):
        # 为这个 LED 计算相位偏移的正弦值
        phase_offset = i * PHASE_SHIFT_PER_LED
        sin_val = math.sin(t * BREATH_SPEED + phase_offset)

        # 计算这个 LED 的线性亮度因子（0.0 到 1.0）
        linear_brightness_factor = ((sin_val + 1) / 2) * (1.0 - BREATH_MIN_BRIGHTNESS) + BREATH_MIN_BRIGHTNESS
        linear_brightness_factor = max(0.0, min(1.0, linear_brightness_factor)) # 夹紧以防万一

        # 应用伽马校正
        gamma_corrected_factor = linear_brightness_factor ** GAMMA_VALUE

        # 使用伽马校正后的因子计算这个 LED 的颜色
        r = max(0, min(255, int(BREATH_COLOR_BASE[0] * gamma_corrected_factor)))
        g = max(0, min(255, int(BREATH_COLOR_BASE[1] * gamma_corrected_factor)))
        b = max(0, min(255, int(BREATH_COLOR_BASE[2] * gamma_corrected_factor)))

        # 设置单个 LED 的颜色
        pixels[i] = (r, g, b)

    # 一次性将颜色写入所有 LED
    pixels.write()

# --- 5. 主应用程序逻辑 ---
if __name__ == "__main__":
    print("--- 启动主应用程序 ---")
    gc.collect()

    # --- 初始化外围设备 ---
    wifi = init_wifi(WIFI_SSID, WIFI_PASSWORD)

    # --- 如果 WiFi 已连接且模块可用，启动 WebREPL ---
    if wifi and wifi.isconnected() and webrepl:
        print("WiFi 已连接。正在启动 WebREPL...")
        try:
            webrepl.start()
            print("WebREPL 启动成功。")
        except Exception as e:
            print(f"启动 WebREPL 时出错：{e}")
    elif webrepl:
         print("WiFi 未连接，WebREPL 未启动。")

    # --- 设置 TCP 服务器套接字 ---
    server_socket = None
    host_ip = None
    if wifi and wifi.isconnected():
        host_ip = wifi.ifconfig()[0]
        print(f"WiFi 已连接。尝试在 {host_ip}:{SERVER_PORT} 上启动 TCP 服务器")
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host_ip, SERVER_PORT))
            server_socket.listen(1) # 监听 1 个传入连接
            # 设置短超时（例如 0.1 秒）或使其非阻塞（超时=0）
            # 这可以防止 accept() 无限期地阻塞主循环。
            server_socket.settimeout(0.1)
            print(f"TCP 服务器正在 {host_ip}:{SERVER_PORT} 上监听")
        except Exception as e:
            print(f"设置 TCP 服务器时出错：{e}")
            if server_socket:
                server_socket.close()
            server_socket = None # 如果设置失败，确保服务器不被使用
    else:
        print("WiFi 未连接。TCP 服务器将不会启动。")

    # 使用新函数初始化 BLE，传递来自 main.py 的常量
    ble_initialized_successfully = init_ble(BLE_DEVICE_NAME, BLE_ADVERTISEMENT_INTERVAL_US)
    # 实际的 'ble' 对象现在由 ble_manager 管理

    keys = init_keypad()
    i2c, temp_hum_sensor, light_sensor = init_i2c_sensors()
    i2s, i2s_buffer = init_i2s()
    display = init_display()
    pixels = None
    if neopixel:
        try:
            pixels = neopixel.NeoPixel(Pin(NEOPIXEL_PIN), NUM_LEDS)
            pixels.fill((0, 0, 0)); pixels.write()
            print(f"NeoPixel LED 在引脚 {NEOPIXEL_PIN} 上初始化。")
        except Exception as e: print(f"初始化 NeoPixel LED 时出错：{e}")
    else: print("NeoPixel 库不可用，跳过 LED 初始化。")

    # <<< 新增：初始化蜂鸣器 PWM >>>
    try:
        buzzer_pin_obj = Pin(BUZZER_PIN, Pin.OUT)
        buzzer_pwm = PWM(buzzer_pin_obj)
        buzzer_pwm.duty_u16(0) # 初始关闭
        buzzer_pwm.freq(BUZZER_FREQ) # 设置默认频率
        print(f"蜂鸣器 PWM 在引脚 {BUZZER_PIN} 上初始化。")
    except Exception as e:
        print(f"初始化蜂鸣器 PWM 时出错：{e}")
        buzzer_pwm = None # 初始化失败则设为 None

    # --- 初始化 GUIManager ---
    gui_mgr = None
    if GUIManager and display and default_font: # 确保显示和字体可用
        gui_mgr = GUIManager(display, default_font)
        print("GUIManager 已初始化。")
    elif not GUIManager:
        print("GUIManager 模块未加载。UI 将受限/无法正常工作。")
    elif not display:
        print("显示未初始化。未创建 GUIManager。")
    
    # --- 初始化 AlertManager ---
    alert_mgr = None
    if AlertManager:
        alert_mgr = AlertManager() # 使用 alert_manager.py 中的默认差异阈值
        print("AlertManager 已初始化。")
    else:
        print("AlertManager 模块未加载。警报功能将基本或禁用。")

    # --- 主循环状态变量 ---
    current_page = PAGE_MAIN 
    last_key_press_time = 0 
    last_right_key_press_time = 0 
    last_left_key_press_time = 0 
    physical_leds_enabled = True 

    # --- 新增：用于稳健按键检测的先前按键状态 ---
    prev_key_states = {
        'up': True, 'down': True, 'left': True, 'right': True, 'enter': True
    } # True = 释放，False = 按下（由于 PULL_UP）

    if gui_mgr: 
        gui_mgr.draw_page_layout(current_page)
    elif display: 
         display.fill(COLOR_STATUS_BAD if 'COLOR_STATUS_BAD' in globals() else 0xF800)

    # 计时变量
    last_sensor_read_ms = 0; sensor_read_interval_ms = 1000
    last_mem_update_ms = 0; mem_update_interval_ms = 5000
    last_noise_calc_ms = 0; noise_calc_interval_ms = 50 # 可以适当调整，例如 100ms
    last_led_update_ms = 0

    loop_count = 0

    # --- 状态变量，用于 UI 更新 ---
    # 所有 prev_ UI 字符串变量现在由 GUIManager 实例管理（例如，gui_mgr.prev_wifi_status_str_p0）

    # --- State variables for Sensor Triggering & LED Alert --- (MOVED to AlertManager)
    # prev_temperature_val = -999.0; prev_humidity_val = -999.0; prev_lux_val = -999.0;
    # prev_rms_val = 0.0 # Stores the *previous raw* RMS value for triggering
    # alert_active = False; alert_flash_step = 0; alert_next_action_time = 0

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
    pin_bl_obj_fallback = None # Ensure this is defined before use in finally block

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
            page_changed = False

            # --- 新增：获取 BLE 控制状态（包括新的警报控制） ---
            ble_led_control_on = True 
            ble_buzzer_logic_enabled = True
            ble_screen_on = True
            ble_screen_brightness_val = 255 # 0-255 亮度范围
            # --- 新增：BLE 警报控制变量 ---
            ble_alert_system_enabled = True # 如果 ble_manager 不可用，默认为 True
            ble_alert_mode_val = ALERT_MODE_DIFFERENCE # 如果 ble_manager 不可用，使用默认模式

            # 如果 BLE 管理器可用且成功初始化，获取具体的 BLE 控制状态
            if ble_manager and ble_initialized_successfully:
                # 获取 LED 控制状态（是否允许 LED 操作）
                ble_led_control_on = ble_manager.get_led_control_state_ble()
                
                # 获取蜂鸣器警报逻辑是否启用
                ble_buzzer_logic_enabled = ble_manager.get_buzzer_alert_logic_enabled_ble()
                
                # 获取屏幕开关状态
                ble_screen_on = ble_manager.get_screen_state_ble()
                
                # 获取屏幕亮度值
                ble_screen_brightness_val = ble_manager.get_screen_brightness_ble()
                
                # --- 新增：获取警报控制状态 ---
                # 获取警报系统是否启用
                ble_alert_system_enabled = ble_manager.get_alert_system_enabled_ble()
                
                # 获取当前警报模式
                ble_alert_mode_val = ble_manager.get_alert_mode_ble()
            
            # --- 确定硬件的有效 LED 启用状态 ---
            effective_leds_enabled_this_loop = ble_led_control_on

            # --- 将 BLE 警报模式应用到 AlertManager --- 
            if alert_mgr:
                # 如果 BLE 客户端写入的警报模式发生变化，则应用新模式
                if alert_mgr.get_current_alert_mode() != ble_alert_mode_val:
                    if alert_mgr.set_alert_mode(ble_alert_mode_val):
                        # 打印同步的警报模式（差异模式或绝对阈值模式）
                        mode_str = 'Difference' if ble_alert_mode_val == ALERT_MODE_DIFFERENCE else 'Absolute'
                        print(f"主程序：警报模式已从 BLE 同步为：{mode_str}")
                        
                        # 如果 GUI 管理器可用，显示提示信息
                        if gui_mgr: 
                            gui_mgr.set_toast(f"Alert: {mode_str}", current_time_ms)
                        
                        # 如果 BLE 管理器可用且成功初始化，通过 BLE 更新警报模式
                        if ble_manager and ble_initialized_successfully:
                            ble_manager.update_alert_mode_ble_and_notify(ble_alert_mode_val)
                    else:
                        print(f"主程序：无法从 BLE 值同步警报模式：{ble_alert_mode_val}")

            # --- a. 读取键盘输入并处理操作（改进的逻辑） ---
            up_pressed = False # 这些标志可能不再需要，保留用于特定 UI 指示
            down_pressed = False 
            other_keys_list = [] # 存储其他按键操作
            current_key_values = {} # 存储当前按键的物理状态

            if keys:
                # 1. 读取所有当前按键的物理状态
                for name, pin_obj in keys.items():
                    current_key_values[name] = pin_obj.value()

                # 2. 基于按键事件处理按键（当前按下 + 之前释放）

                # 页面切换按键（上/下）- 使用共享的去抖动计时器
                # 下键
                if not current_key_values.get('down', True) and prev_key_states.get('down', True):
                    # 检查去抖动时间间隔
                    if time.ticks_diff(current_time_ms, last_key_press_time) > KEY_DEBOUNCE_MS:
                        down_pressed = True # 可能用于 UI 反馈，现在不用于触发操作
                        # 计算新页面索引（循环）
                        new_page = (current_page + 1) % NUM_PAGES
                        if new_page != current_page:
                            current_page = new_page
                            page_changed = True
                            print(f"切换到页面 {current_page}")
                        last_key_press_time = current_time_ms
                
                # 上键（仅在下键未作为本次去抖动周期的主要操作时处理）
                # 这种结构确保如果两个键同时触发，每个去抖动间隔只切换一个页面
                # 对于上/下键，可能需要一个更健壮的逻辑，如果它们是真正独立的
                # 但对于页面切换，这种分组方法是常见的
                elif not current_key_values.get('up', True) and prev_key_states.get('up', True):
                    # 检查去抖动时间间隔
                    if time.ticks_diff(current_time_ms, last_key_press_time) > KEY_DEBOUNCE_MS:
                        up_pressed = True
                        # 计算新页面索引（循环，确保页面索引在有效范围内）
                        new_page = (current_page - 1 + NUM_PAGES) % NUM_PAGES
                        if new_page != current_page:
                            current_page = new_page
                            page_changed = True
                            print(f"切换到页面 {current_page}")
                        last_key_press_time = current_time_ms
                
                # 左键用于切换警报模式 - 独立去抖动
                if not current_key_values.get('left', True) and prev_key_states.get('left', True):
                    # 检查去抖动时间间隔
                    if time.ticks_diff(current_time_ms, last_left_key_press_time) > KEY_DEBOUNCE_MS:
                        if alert_mgr:
                            # 获取当前警报模式
                            current_mode = alert_mgr.get_current_alert_mode()
                            # 在差异模式和绝对阈值模式之间切换
                            new_mode = ALERT_MODE_THRESHOLD_ABSOLUTE if current_mode == ALERT_MODE_DIFFERENCE else ALERT_MODE_DIFFERENCE
                            
                            # 尝试设置新的警报模式
                            if alert_mgr.set_alert_mode(new_mode):
                                # 根据新模式生成描述字符串
                                mode_str = 'Difference' if new_mode == ALERT_MODE_DIFFERENCE else 'Absolute'
                                print(f"主程序：左键。警报模式切换为：{mode_str}")
                                
                                # 如果 GUI 管理器可用，显示提示信息
                                if gui_mgr: 
                                    gui_mgr.set_toast(f"Alert: {mode_str}", current_time_ms)
                                
                                # 如果 BLE 管理器可用且成功初始化，通过 BLE 更新警报模式
                                if ble_manager and ble_initialized_successfully:
                                    ble_manager.update_alert_mode_ble_and_notify(new_mode)
                            else:
                                print(f"主程序：左键。切换警报模式失败。")
                        else:
                            print("主程序：按下左键，但警报管理器不可用。")
                        
                        # 更新最后一次左键按下的时间，用于去抖动
                        last_left_key_press_time = current_time_ms 
                
                # 右键用于切换 LED 状态 - 独立去抖动
                if not current_key_values.get('right', True) and prev_key_states.get('right', True):
                    # 检查去抖动时间间隔
                    if time.ticks_diff(current_time_ms, last_right_key_press_time) > KEY_DEBOUNCE_MS:
                        # 切换物理 LED 的启用状态
                        physical_leds_enabled = not physical_leds_enabled 
                        
                        # 生成状态描述字符串
                        led_status_str = 'Enabled' if physical_leds_enabled else 'Disabled'
                        print(f"物理 LED 意图现在：{led_status_str}")
                        
                        # 如果 GUI 管理器可用，显示提示信息
                        if gui_mgr: 
                            gui_mgr.set_toast(f"LED: {led_status_str}", current_time_ms)
                        
                        # 更新最后一次右键按下的时间，用于去抖动
                        last_right_key_press_time = current_time_ms
                        
                        # 准备要设置的新有效状态
                        new_effective_state_to_set = physical_leds_enabled
                        
                        # 如果 BLE 管理器可用且成功初始化，更新并通知 LED 状态
                        if ble_manager and ble_initialized_successfully:
                            ble_manager.update_led_state_and_notify_if_changed(new_effective_state_to_set)
                
                # 回车键（如果需要类似的按一次逻辑和去抖动）
                if not current_key_values.get('enter', True) and prev_key_states.get('enter', True):
                    # 假设回车键可能需要自己的去抖动时间（如果执行关键操作）
                    # 目前只是添加到其他按键列表中
                    other_keys_list.append("E")
                elif not current_key_values.get('enter', True):
                    # 按键被按住，但不是新的按下事件
                    other_keys_list.append("E_held")  # 可选：区分按住状态

                # 3. 为下一次迭代更新先前的按键状态
                for name, val in current_key_values.items():
                    prev_key_states[name] = val
            
            # current_pressed_key_names 用于显示，可以根据 other_keys_list 调整
            current_pressed_key_names = ",".join(other_keys_list) if other_keys_list else "--"

            # --- 处理页面变更 ---
            if page_changed and gui_mgr: # 使用 gui_mgr
                 # 绘制新的页面布局
                 gui_mgr.draw_page_layout(current_page)
                 # 强制重绘所有字段
                 gui_mgr.reset_prev_ui_strings()

            # --- b. 读取 I2C 传感器（定时） ---
            # 如果 AlertManager 可用，使用其先前的温度值，否则使用默认值
            current_temperature_val = alert_mgr.prev_temperature_val if alert_mgr else -999.0
            current_humidity_val = alert_mgr.prev_humidity_val if alert_mgr else -999.0
            current_lux_val = alert_mgr.prev_lux_val if alert_mgr else -999.0
            
            # 传感器错误标志
            sensor_error = False
            # 是否需要检查触发器
            trigger_check_needed = False # 默认为 false

            # 检查是否到达传感器读取间隔
            if time.ticks_diff(current_time_ms, last_sensor_read_ms) >= sensor_read_interval_ms:
                # 更新最后一次读取时间
                last_sensor_read_ms = current_time_ms
                # 设置需要检查触发器
                trigger_check_needed = True

                # 读取温湿度传感器
                if temp_hum_sensor:
                    try:
                        # 读取温度和湿度
                        t = temp_hum_sensor.temperature()
                        h = temp_hum_sensor.humidity()
                        current_temperature_val = t
                        current_humidity_val = h
                    except Exception as e:
                        # 如果读取出错，设置错误标志和默认值
                        sensor_error = True
                        current_temperature_val = -999
                        current_humidity_val = -999
                else:
                    # 如果传感器不可用，不进行触发器检查
                    trigger_check_needed = False

                # 读取光照传感器
                if light_sensor:
                    try:
                        # 读取光照强度
                        l = light_sensor.read()
                        current_lux_val = l
                    except Exception as e:
                        # 如果读取出错，设置错误标志和默认值
                        sensor_error = True
                        current_lux_val = -999
                else:
                    # 如果传感器不可用，不进行触发器检查
                    trigger_check_needed = False

                # --- 通过 BLE 发送传感器数据通知/指示 ---
                if ble_manager and ble_initialized_successfully:
                    ble_manager.update_sensor_data_and_send(
                        current_temperature_val,
                        current_humidity_val,
                        current_lux_val,
                        current_noise_rms # 传递当前平滑的噪声 RMS 值
                    )

            # 为显示格式化传感器数据字符串（UI 更新检查始终需要）
            # 温度：如果值大于 -990，则显示带一位小数的摄氏度，否则显示 "Err"
            current_temperature_str = f"{current_temperature_val:.1f}C" if current_temperature_val > -990 else "Err"
            # 湿度：如果值大于 -990，则显示带一位小数的百分比，否则显示 "Err"
            current_humidity_str = f"{current_humidity_val:.1f}%" if current_humidity_val > -990 else "Err"
            # 光照：如果值大于 -990，则显示整数，否则显示 "Err"
            current_lux_str = f"{current_lux_val:.0f}" if current_lux_val > -990 else "Err"

            # --- d. 读取 I2S 音频并计算噪声和检查触发 ---
            # 存储本周期计算的原始 RMS 值
            raw_rms_value_this_cycle = -1.0

            # 检查 I2S 和缓冲区是否可用
            if i2s and i2s_buffer:
                bytes_read = 0
                try:
                    # 尝试从 I2S 读取数据到缓冲区
                    bytes_read = i2s.readinto(i2s_buffer)
                    
                    # 如果成功读取数据
                    if bytes_read > 0:
                        # 检查是否到达噪声计算间隔
                        if time.ticks_diff(current_time_ms, last_noise_calc_ms) >= noise_calc_interval_ms:
                           # 更新最后一次噪声计算时间
                           last_noise_calc_ms = current_time_ms
                           
                           # 计算原始 RMS 值
                           calculated_rms = calculate_rms(i2s_buffer, bytes_read)

                           # 如果 RMS 计算成功（非负）
                           if calculated_rms >= 0:
                               # 存储本周期的原始 RMS 值
                               raw_rms_value_this_cycle = calculated_rms

                               # --- 更新 RMS 缓冲区 ---
                               # 将新的 RMS 值存储到缓冲区
                               rms_buffer[rms_buffer_index] = calculated_rms
                               
                               # 更新缓冲区索引（循环）
                               rms_buffer_index = (rms_buffer_index + 1) % RMS_BUFFER_SIZE
                               
                               # 如果缓冲区未满，增加有效 RMS 数量
                               if num_valid_rms_in_buffer < RMS_BUFFER_SIZE:
                                   num_valid_rms_in_buffer += 1

                               # --- 计算用于显示的平滑 RMS ---
                               if num_valid_rms_in_buffer > 0:
                                   # 仅使用有效条目计算平均值
                                   valid_buffer_slice = rms_buffer[:num_valid_rms_in_buffer]
                                   buffer_sum = sum(valid_buffer_slice)
                                   
                                   # 更新用于显示的平滑噪声 RMS 值
                                   current_noise_rms = buffer_sum / num_valid_rms_in_buffer
                               else:
                                   # 如果没有有效条目，设置为 0
                                   current_noise_rms = 0.0

                               # <<< 新增：计算相对分贝值 >>>
                               if current_noise_rms > 0:
                                   try:
                                       # 使用对数计算相对分贝值
                                       # 注意：micropython 可能没有 math.log10，使用 log(x) / log(10)
                                       current_decibel_val = 20 * (math.log(max(1.0, current_noise_rms)) / 2.302585)
                                   except (ValueError, AttributeError):
                                       # 处理可能的错误
                                       current_decibel_val = 0.0
                               else:
                                   # 对于静音或错误，显示 0 dB
                                   current_decibel_val = 0.0
                           else:
                               # RMS 计算错误
                               print(f"[RMS 计算] 错误计算 RMS。")
                               current_decibel_val = 0.0
                except Exception as e:
                    # I2S 读取错误处理
                    print(f"[I2S 读取] 错误：{e}")
                    current_decibel_val = 0.0

            # 为显示格式化噪声水平字符串
            # 如果噪声 RMS 大于等于 0，显示带一位小数的值，否则显示 "Err"
            current_noise_level_str = f"{current_noise_rms:.1f}" if current_noise_rms >= 0 else "Err"
            
            # <<< 新增：格式化分贝值字符串 >>>
            current_decibel_str = f"{current_decibel_val:.1f}dB"

            # --- 新增：通过 AlertManager 集中式警报检查，考虑 BLE 启用状态 ---
            if alert_mgr and trigger_check_needed: # trigger_check_needed 仍然基于传感器读取间隔设置
                if ble_alert_system_enabled: # 检查是否通过 BLE 启用警报系统
                    alert_mgr.check_sensor_triggers(
                        current_time_ms,
                        current_temperature_val,
                        current_humidity_val,
                        current_lux_val,
                        raw_rms_value_this_cycle # 传递原始 RMS 值用于差异检查
                    )
                else: # 警报系统通过 BLE 禁用
                    if alert_mgr.is_alert_active(): # 如果警报已激活，则重置
                        alert_mgr.reset_alert()
                        print("主程序：通过 BLE 禁用警报系统。活动警报已重置。")
                # alert_mgr 内部更新其先前的值，因此无需在此处执行

            # --- e. 获取网络状态和详细信息 ---
            # 检查 WiFi 是否连接
            wifi_connected = wifi and wifi.isconnected()
            
            # 页面 0 状态栏的 WiFi 状态
            current_wifi_status_str_p0 = "WiFi✓" if wifi_connected else "WiFi✗" # 状态栏的简短版本
            wifi_status_color_p0 = COLOR_STATUS_OK if wifi_connected else COLOR_STATUS_BAD
            
            # 页面 1 详细信息
            current_ssid_str_p1 = WIFI_SSID if wifi_connected else "已断开连接"
            current_ip_str_p1 = "---"
            current_mask_str_p1 = "---"
            current_gw_str_p1 = "---"
            current_wifi_icon_str_p1 = "NET✓" if wifi_connected else "NET✗" # 简单的文本图标
            
            # 如果 WiFi 已连接，获取网络配置详细信息
            if wifi_connected:
                try:
                    # 获取 IP 配置（IP 地址、子网掩码、网关）
                    ip_config = wifi.ifconfig()
                    current_ip_str_p1 = ip_config[0]
                    current_mask_str_p1 = ip_config[1]
                    current_gw_str_p1 = ip_config[2]
                except Exception as e:
                    # 获取网络配置时出错
                    print(f"获取网络配置时出错：{e}")
                    current_ip_str_p1 = "错误"
                    current_mask_str_p1 = "错误"
                    current_gw_str_p1 = "错误"

            # --- f. 获取 BLE 状态 ---
            # 从 ble_manager 获取状态
            ble_is_active_status = False
            ble_is_connected_status = False
            
            # 如果 BLE 管理器可用且成功初始化，获取具体状态
            if ble_manager and ble_initialized_successfully:
                ble_is_active_status = ble_manager.is_active()
                ble_is_connected_status = ble_manager.is_connected()

            # 生成 BLE 状态字符串和颜色
            # 已连接显示 ✓，活动但未连接显示 -，未激活显示 ✗
            current_ble_status_str_p0 = f"BLE{'✓' if ble_is_connected_status else ('-' if ble_is_active_status else '✗')}"
            
            # 根据 BLE 状态设置颜色
            ble_status_color_p0 = (
                COLOR_STATUS_OK if ble_is_connected_status 
                else (COLOR_STATUS_WARN if ble_is_active_status else COLOR_STATUS_BAD)
            )

            # --- g. Get Memory Status (Timed) ---
            # Removed direct access to gui_mgr.prev_mem_free_str as it no longer exists.
            # current_mem_free_str is now primarily for potential non-UI uses or direct calculation.
            current_mem_free_str = "N/A" # Default value
            if time.ticks_diff(current_time_ms, last_mem_update_ms) >= mem_update_interval_ms:
                 last_mem_update_ms = current_time_ms
                 current_mem_free_str = f"{gc.mem_free()}"
            else:
                 current_mem_free_str = f"{gc.mem_free()}" # Or keep a local previous value if needed outside UI

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
            if gui_mgr and display and default_font and ble_screen_on: # Check gui_mgr
                # Update Page Indicator (Common)
                current_page_indicator_str = f"{current_page + 1}/{NUM_PAGES}"
                # prev_page_indicator_str updated via gui_mgr method
                gui_mgr.update_text_field(gui_mgr.x_page_indicator, gui_mgr.y_page_indicator, current_page_indicator_str, "prev_page_indicator_str", COLOR_PAGE_INDICATOR, COLOR_BG)


                # Update Page Specific Fields
                if current_page == PAGE_MAIN:
                    # prev_wifi_status_str_p0 updated via gui_mgr method
                    gui_mgr.update_text_field(X_WIFI_STATUS_P0, Y_STATUS_LINE_P0, current_wifi_status_str_p0, "prev_wifi_status_str_p0", wifi_status_color_p0, COLOR_BG)
                    gui_mgr.update_text_field(X_BLE_STATUS_P0, Y_STATUS_LINE_P0, current_ble_status_str_p0, "prev_ble_status_str_p0", ble_status_color_p0, COLOR_BG)
                    
                    # Updated sensor display calls
                    gui_mgr.update_text_field(X_VALUE_P0, Y_TEMP_ROW_P0, current_temperature_str, "prev_temperature_str", COLOR_VALUE, COLOR_BG)
                    gui_mgr.update_text_field(X_VALUE_P0, Y_HUMI_ROW_P0, current_humidity_str, "prev_humidity_str", COLOR_VALUE, COLOR_BG)
                    gui_mgr.update_text_field(X_VALUE_P0, Y_LUX_ROW_P0, current_lux_str, "prev_lux_str", COLOR_VALUE, COLOR_BG)
                    gui_mgr.update_text_field(X_VALUE_P0, Y_NOISE_RMS_ROW_P0, current_noise_level_str, "prev_noise_level_str", COLOR_VALUE, COLOR_BG)
                    gui_mgr.update_text_field(X_VALUE_P0, Y_NOISE_DB_ROW_P0, current_decibel_str, "prev_decibel_str", COLOR_VALUE, COLOR_BG)
                    
                    # Ensure the following line, which was previously around line 945 and caused the
                    # AttributeError for 'prev_mem_free_str', is definitely commented out or removed.
                    # gui_mgr.update_text_field(X_MEM_VALUE_P0, Y_BOTTOM_ROW_2_P0, current_mem_free_str, "prev_mem_free_str", COLOR_MEM, COLOR_BG)
                    
                elif current_page == PAGE_NETWORK:
                    gui_mgr.update_text_field(X_WIFI_ICON_P1, Y_WIFI_ICON_P1, current_wifi_icon_str_p1, "prev_wifi_icon_str_p1", wifi_status_color_p0, COLOR_BG) # Use same color as status
                    gui_mgr.update_text_field(X_SSID_VALUE_P1, Y_SSID_P1, current_ssid_str_p1, "prev_ssid_str_p1", COLOR_VALUE, COLOR_BG)
                    gui_mgr.update_text_field(X_IP_VALUE_P1, Y_IP_P1, current_ip_str_p1, "prev_ip_str_p1", COLOR_VALUE, COLOR_BG)
                    gui_mgr.update_text_field(X_MASK_VALUE_P1, Y_MASK_P1, current_mask_str_p1, "prev_mask_str_p1", COLOR_VALUE, COLOR_BG)
                    gui_mgr.update_text_field(X_GW_VALUE_P1, Y_GW_P1, current_gw_str_p1, "prev_gw_str_p1", COLOR_VALUE, COLOR_BG)


            # --- i. Update WS2812 LEDs (Timed) ---
            if (pixels or buzzer_pwm) and time.ticks_diff(current_time_ms, last_led_update_ms) >= LED_UPDATE_INTERVAL_MS:
                last_led_update_ms = current_time_ms
                
                current_alert_status_params = None
                if alert_mgr:
                    current_alert_status_params = alert_mgr.get_alert_flash_parameters()
                
                # ALERT_COLOR is now defined globally at the top of main.py
                # Pass alert_manager_instance to update_leds for callback
                # Ensure alert_manager_instance is accessible in update_leds if needed directly,
                # or pass necessary data/methods if preferred.
                # For now, update_leds uses the global alert_manager_instance for the callback.
                global alert_manager_instance 
                alert_manager_instance = alert_mgr 

                update_leds(pixels, current_time_ms, current_alert_status_params, effective_leds_enabled_this_loop)

            # --- NEW: Draw Toast if active ---
            if gui_mgr:
                gui_mgr.draw_toast_if_active(current_time_ms)

            # --- j. Yield control ---
            time.sleep_ms(10) # Slightly shorter sleep potentially
            loop_count += 1

            # Optional: Periodic garbage collection & Debug Print
            if loop_count % 500 == 0: # Approx every 5 seconds
                gc.collect()
                # Debug print now shows smoothed RMS
                active_alert_state = alert_mgr.is_alert_active() if alert_mgr else False
                print(f"Loop {loop_count}, Page: {current_page}, Mem: {gc.mem_free()}, RMS(Smoothed): {current_noise_rms:.1f}, Alert: {active_alert_state}")

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
