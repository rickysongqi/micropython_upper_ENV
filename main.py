# main.py
# Application to manage Wi-Fi, BLE, Keypad, LCD (ST7789),
# I2C Sensors (SI7021, BH1750), and I2S Microphone Input.

import gc  # Garbage collector
# --- 1. Import necessary modules ---
import time

import network

# WARNING: The help('bluetooth') output showed 'bluetooth' was a string.
# This means the module name was likely overwritten. Ensure this is fixed
# (e.g., via hard reset, checking boot.py) before running this script.
try:
    import bluetooth
except ImportError:
    print("CRITICAL: Failed to import 'bluetooth' module. Check firmware and name conflicts.")
    bluetooth = None # Prevent further errors if import failed

from machine import Pin, SPI, I2C, I2S, SoftSPI

# --- Attempt to import required external driver libraries ---
# --- These .py files MUST be present on the device's filesystem ---
try:
    import st7789
except ImportError:
    print("Error: ST7789 driver (st7789.py) not found. Display functions disabled.")
    st7789 = None
try:
    import si7021
except ImportError:
    print("Error: SI7021 driver (si7021.py) not found. Temp/Hum sensor disabled.")
    si7021 = None
try:
    import bh1750
except ImportError:
    print("Error: BH1750 driver (bh1750.py) not found. Light sensor disabled.")
    bh1750 = None

import struct # 确保 struct 已导入
import math

# --- Import ST7789 driver and converted TrueType font ---
try:
    import ubuntu_24 as default_font  # Replace with your actual font module name
except ImportError:
    print("Error: Converted TrueType font module ('my_ttf_font.py') not found.")
    print("Please use a tool to convert TTF font and upload the .py file.")
    default_font = None

# --- 2. Define constants and configuration ---
# --- Add a global debug flag for I2S ---
I2S_DEBUG_VERBOSE = True # 设置为 True 来启用详细日志, 设置为 False 关闭

# WiFi Configuration
#WIFI_SSID = "501_2.4G"
WIFI_SSID = "Redmi_1D4E"
WIFI_PASSWORD = "12340000" # Ensure this is correct

# Bluetooth Configuration
BLE_DEVICE_NAME = "ESP32S3_Sensor" # 或者更短的名字

# Keypad Pins
KEY_UP_PIN = 2
KEY_DOWN_PIN = 41
KEY_LEFT_PIN = 40
KEY_RIGHT_PIN = 1
KEY_ENTER_PIN = 42

# LCD SPI Pins & Config (Assuming SPI controller 2)
LCD_SPI_ID = 2
LCD_SCLK_PIN = 12
LCD_MOSI_PIN = 11
LCD_MISO_PIN = -1 # Usually not needed for LCD write-only
LCD_CS_PIN = 3
LCD_DC_PIN = 46
LCD_RST_PIN = 9
LCD_BL_PIN = 8 # Backlight control
LCD_WIDTH = 240
LCD_HEIGHT = 320
LCD_ROTATION = 2 # 180 degrees (0=0, 1=90, 2=180, 3=270)
LCD_SPI_BAUDRATE = 40000000 # 尝试降低波特率
#LCD_SPI_BAUDRATE = 20000000 # 先试试 20MHz
#LCD_SPI_BAUDRATE = 10000000 # 如果 20MHz 仍有问题，再试试 10MHz

# I2C Pins & Config (Assuming I2C controller 0)
I2C_ID = 0
I2C_SCL_PIN = 39
I2C_SDA_PIN = 38
I2C_FREQ = 400000 # 400 kHz
SI7021_ADDR = 0x40
BH1750_ADDR = 0x23

# I2S Pins & Config (Assuming I2S controller 0)
I2S_ID = 0
I2S_BCLK_PIN = 17
I2S_WS_PIN = 16
I2S_DIN_PIN = 15
I2S_SAMPLE_RATE = 16000
I2S_BITS = 16
I2S_FORMAT = I2S.MONO
I2S_BUFFER_LEN_IN_BYTES = 4096
I2S_READ_CHUNK_SIZE = 512
# <<<--- 新增：明确指定字节序 ---
I2S_ENDIANNESS = '<'  # '<' 小端，'>' 大端，根据麦克风实际情况设置

# --- 3. Initialization Functions ---

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
    """
    初始化 SPI 总线和 ST7789 LCD。
    (最终版本：移除诊断性测试代码，依赖驱动内部防护)
    """
    global spi # 假设 spi 是全局变量，或根据实际情况调整
    display_dev = None
    print("--- Starting Display Initialization ---")

    # 1. 尝试初始化控制引脚
    pin_rst = None
    pin_dc = None
    pin_cs = None
    pin_bl = None
    try:
        print(f"Attempting to init RST pin: {LCD_RST_PIN}")
        pin_rst = Pin(LCD_RST_PIN, Pin.OUT) if LCD_RST_PIN is not None else None
        print("  RST pin OK.")
        print(f"Attempting to init DC pin: {LCD_DC_PIN}")
        pin_dc = Pin(LCD_DC_PIN, Pin.OUT)
        print("  DC pin OK.")
        print(f"Attempting to init CS pin: {LCD_CS_PIN}")
        pin_cs = Pin(LCD_CS_PIN, Pin.OUT) if LCD_CS_PIN is not None else None
        print("  CS pin OK.")
        print(f"Attempting to init BL pin: {LCD_BL_PIN}")
        pin_bl = Pin(LCD_BL_PIN, Pin.OUT) if LCD_BL_PIN is not None else None
        print("  BL pin OK.")
        if pin_bl: pin_bl.value(1)
    except Exception as e:
        print(f"FATAL: Error initializing CONTROL PINS: {e}")
        return None

    # 2. 尝试初始化硬件 SPI (使用配置的波特率)
    spi = None
    spi_ids_to_try = [2, 3] # 或者根据您的硬件只尝试一个确定的 ID
    print(f"Attempting Hardware SPI initialization for IDs: {spi_ids_to_try}")
    for current_spi_id in spi_ids_to_try:
        try:
            print(f"--> Attempting to init Hardware SPI ID: {current_spi_id}")
            # 使用在常量区定义的 LCD_SPI_BAUDRATE (可能是 40MHz 或已降低的值)
            print(f"    SCLK={LCD_SCLK_PIN}, MOSI={LCD_MOSI_PIN}, MISO={LCD_MISO_PIN}, BAUD={LCD_SPI_BAUDRATE}")
            spi = SPI(current_spi_id, baudrate=LCD_SPI_BAUDRATE,
                      sck=Pin(LCD_SCLK_PIN), mosi=Pin(LCD_MOSI_PIN),
                      miso=Pin(LCD_MISO_PIN) if LCD_MISO_PIN != -1 else None)
            print(f"  SUCCESS: Hardware SPI ID {current_spi_id} initialized OK.")
            break # 初始化成功，跳出循环
        except Exception as e_hw_spi:
            print(f"  ERROR: Failed to initialize Hardware SPI ID {current_spi_id}: {e_hw_spi}")
            spi = None # 确保 spi 为 None 以便尝试下一个或回退

    # 检查硬件 SPI 是否成功，否则尝试 SoftSPI
    if spi is None:
        print("All attempted Hardware SPI IDs failed.")
        try:
            print("Attempting to init Software SPI as fallback...")
            print(f"  SCLK={LCD_SCLK_PIN}, MOSI={LCD_MOSI_PIN}, MISO={LCD_MISO_PIN}")
            spi = SoftSPI(baudrate=10000000, # SoftSPI 通常较慢
                          sck=Pin(LCD_SCLK_PIN), mosi=Pin(LCD_MOSI_PIN),
                          miso=Pin(LCD_MISO_PIN) if LCD_MISO_PIN != -1 else None)
            print("  Software SPI initialized OK (NOTE: Performance will be much lower!).")
        except Exception as e_sw_spi:
            print(f"FATAL: Failed to initialize Software SPI as well: {e_sw_spi}")
            return None

    # --- 底层 SPI 测试 (可选，保持简洁可注释掉) ---
    # 这些基础测试有助于确认 SPI 基本通信正常，如果稳定可移除
    print("--- Performing Pre-Driver SPI Tests ---")
    test_ok = True
    if spi is None:
        print("ERROR: No valid SPI object available for testing.")
        test_ok = False
    else:
        try:
            # 测试 1: struct.pack
            print("Testing struct.pack...")
            test_pixel_data = struct.pack(">H", 0xF800)
            test_pos_data = struct.pack(">HH", 10, 20)
            print(f"  struct.pack test OK. Pixel={test_pixel_data.hex()}, Pos={test_pos_data.hex()}")

            # 测试 2: 发送命令
            print("Testing SPI write (Command - SLPOUT b'\\x11')...")
            cmd_to_send = b"\x11"
            if pin_cs: pin_cs.value(0)
            pin_dc.value(0)
            spi.write(cmd_to_send)
            # pin_dc.value(1) # 根据设备手册决定何时拉高DC
            if pin_cs: pin_cs.value(1)
            print("  SPI write command seemed OK (no exception).")

            # 测试 3: 发送数据
            print("Testing SPI write (Data - 1 pixel b'\\x00\\x00')...")
            data_to_send = struct.pack(">H", 0x0000)
            if pin_cs: pin_cs.value(0)
            pin_dc.value(1) # 数据模式
            spi.write(data_to_send)
            if pin_cs: pin_cs.value(1)
            print("  SPI write data seemed OK (no exception).")

        except Exception as e_test:
            print(f"FATAL: Error during Pre-Driver SPI Tests: {e_test}")
            test_ok = False
            if spi: spi.deinit()
            spi = None

    if not test_ok:
        print("--- Pre-Driver SPI Tests Failed ---")
        return None
    print("--- Pre-Driver SPI Tests Passed ---")

    # --- !!! 不再进行 spi.write(b'') 的直接测试 !!! ---
    # --- 注释掉相关代码块 ---
    # if spi:
    #     print("--- Skipping Additional Test: spi.write(b'') ---")
        # try:
        #     # spi.write(b'') # 不再执行
        #     print("  Skipped.")
        # except Exception as e_empty_write:
        #     print(f"  FATAL: spi.write(b'') FAILED with exception: {e_empty_write}")
        #     if spi: spi.deinit()
        #     return None
        # print("--- Additional Test Skipped ---")


    # 3. 尝试初始化 ST7789 驱动实例
    if spi is None:
        print("FATAL: SPI object is None before driver init, cannot proceed.")
        return None

    # 检查 st7789 模块是否已加载
    if st7789 is None:
        print("FATAL: st7789 driver module not loaded, cannot instantiate.")
        if spi: spi.deinit() # 清理 SPI
        return None

    try:
        print("Initializing ST7789 driver instance...")
        # 现在依赖 st7789 驱动内部的 _write 方法来避免调用 spi.write(b'')
        display_dev = st7789.ST7789(
            spi, LCD_WIDTH, LCD_HEIGHT,
            reset=pin_rst, dc=pin_dc, cs=pin_cs, backlight=pin_bl,
            rotation=LCD_ROTATION, color_order=st7789.BGR # 或根据屏幕调整 RGB/BGR
        )
        print("Display driver instance created successfully.")
        print("--- Display Initialization Finished ---")

    except Exception as e_driver:
        print(f"FATAL: Error initializing ST7789 DRIVER INSTANCE: {e_driver}")
        # 如果错误仍然是 "buffer too short"，并且确认驱动防护无误，则强烈建议更新固件
        if spi: spi.deinit() # 清理 SPI
        display_dev = None

    return display_dev


def init_i2s():
    """Initializes I2S peripheral for audio input with verbose logging."""
    i2s_dev = None
    read_buf = None
    print("[I2S INIT] Initializing I2S for microphone...")
    print(f"[I2S INIT] Config: ID={I2S_ID}, BCLK={I2S_BCLK_PIN}, WS={I2S_WS_PIN}, DIN={I2S_DIN_PIN}")
    print(f"[I2S INIT] Config: Rate={I2S_SAMPLE_RATE}, Bits={I2S_BITS}, Format={I2S_FORMAT}, Internal Buf={I2S_BUFFER_LEN_IN_BYTES} bytes")
    try:
        sck_pin = Pin(I2S_BCLK_PIN)
        ws_pin = Pin(I2S_WS_PIN)
        sd_pin = Pin(I2S_DIN_PIN)
        print("[I2S INIT] GPIO Pins initialized.")

        i2s_dev = I2S(I2S_ID,
                      sck=sck_pin, ws=ws_pin, sd=sd_pin,
                      mode=I2S.RX,
                      bits=I2S_BITS,
                      format=I2S_FORMAT,
                      rate=I2S_SAMPLE_RATE,
                      ibuf=I2S_BUFFER_LEN_IN_BYTES)
        print(f"[I2S INIT] I2S object created: {i2s_dev}")

        read_buf = bytearray(I2S_READ_CHUNK_SIZE)
        print(f"[I2S INIT] Read buffer created: {len(read_buf)} bytes")
        print("[I2S INIT] I2S Initialized successfully.")

    except Exception as e:
        print(f"[I2S INIT] FATAL: Error initializing I2S: {e}")
        print(f"[I2S INIT] Exception type: {type(e)}")
        if i2s_dev:
            try:
                i2s_dev.deinit()
                print("[I2S INIT] Attempted I2S deinit after error.")
            except Exception as deinit_e:
                print(f"[I2S INIT] Error during deinit after init failure: {deinit_e}")
        i2s_dev = None
        read_buf = None

    print(f"[I2S INIT] Returning: i2s_dev={type(i2s_dev)}, read_buf exists={read_buf is not None}")
    return i2s_dev, read_buf

def calculate_rms(audio_buffer, bytes_read):
    """
    Calculates the Root Mean Square (RMS) of the audio samples, 支持 16/32 位采样和不同字节序。
    """
    if I2S_DEBUG_VERBOSE:
        print(f"[RMS CALC] Received buffer (len={len(audio_buffer)}), bytes_read={bytes_read}, I2S_BITS={I2S_BITS}")

    if bytes_read == 0:
        if I2S_DEBUG_VERBOSE: print("[RMS CALC] bytes_read is 0, returning 0.0")
        return 0.0

    # 根据 I2S_BITS 确定样本大小和解包代码
    if I2S_BITS == 16:
        bytes_per_sample = 2
        unpack_code = 'h'
    elif I2S_BITS == 32:
        bytes_per_sample = 4
        unpack_code = 'i'
    else:
        print(f"[RMS CALC] ERROR: Unsupported I2S_BITS value: {I2S_BITS}")
        return -1.0

    if bytes_read % bytes_per_sample != 0:
        print(f"[RMS CALC] WARNING: bytes_read ({bytes_read}) not multiple of bytes_per_sample ({bytes_per_sample})!")
        num_samples = bytes_read // bytes_per_sample
        bytes_to_process = num_samples * bytes_per_sample
        if I2S_DEBUG_VERBOSE: print(f"[RMS CALC] Adjusted bytes_to_process: {bytes_to_process}")
    else:
        num_samples = bytes_read // bytes_per_sample
        bytes_to_process = bytes_read

    if I2S_DEBUG_VERBOSE: print(f"[RMS CALC] Calculated bytes_per_sample: {bytes_per_sample}, num_samples: {num_samples}")

    if num_samples == 0:
        if I2S_DEBUG_VERBOSE: print("[RMS CALC] num_samples is 0, returning 0.0")
        return 0.0

    if I2S_DEBUG_VERBOSE:
        sample_bytes_hex = ' '.join(f'{b:02x}' for b in audio_buffer[:min(16, bytes_to_process)])
        print(f"[RMS CALC] Raw buffer start (hex): {sample_bytes_hex}")

    try:
        format_string = I2S_ENDIANNESS + unpack_code * num_samples
        if I2S_DEBUG_VERBOSE: print(f"[RMS CALC] Unpack format string: '{format_string}'")
        samples = struct.unpack(format_string, audio_buffer[:bytes_to_process])
        if I2S_DEBUG_VERBOSE:
            sample_values_str = ', '.join(map(str, samples[:min(10, num_samples)]))
            print(f"[RMS CALC] Unpacked samples start: {sample_values_str}")
            if samples:
                min_sample = min(samples)
                max_sample = max(samples)
                print(f"[RMS CALC] Sample range: min={min_sample}, max={max_sample}")
            else:
                print("[RMS CALC] No samples unpacked.")
    except Exception as e:
        print(f"[RMS CALC] ERROR during unpack/print: {e}")
        if "unpack" in str(e).lower():
            print(f"[RMS CALC] Unpack ERROR details: bytes_to_process={bytes_to_process}, format='{format_string}'")
        return -1.0

    sum_sq = 0.0
    for sample in samples:
        sum_sq += float(sample) * float(sample)
    if I2S_DEBUG_VERBOSE: print(f"[RMS CALC] Sum of squares: {sum_sq}")

    mean_sq = sum_sq / num_samples
    if I2S_DEBUG_VERBOSE: print(f"[RMS CALC] Mean square: {mean_sq}")

    try:
        if mean_sq < 0:
            print(f"[RMS CALC] ERROR: Mean square is negative ({mean_sq}), cannot calculate sqrt.")
            return -1.0
        rms = math.sqrt(mean_sq)
        if I2S_DEBUG_VERBOSE: print(f"[RMS CALC] Calculated RMS: {rms}")
        return rms
    except ValueError as e:
        print(f"[RMS CALC] ERROR calculating sqrt: {e}, mean_sq={mean_sq}")
        return -1.0


# --- 4. Main Application Logic ---
if __name__ == "__main__":
    print("--- Starting Main Application ---")
    gc.collect()

    # --- Initialize all peripherals ---
    wifi = init_wifi(WIFI_SSID, WIFI_PASSWORD)
    ble = init_ble(BLE_DEVICE_NAME)
    keys = init_keypad()
    i2c, temp_hum_sensor, light_sensor = init_i2c_sensors()
    display = init_display()
    # --- 调用带有详细日志的 I2S 初始化 ---
    i2s, i2s_buffer = init_i2s()

    # --- Variables for main loop ---
    last_sensor_read_ms = 0
    sensor_read_interval_ms = 5000 # Read sensors every 5 seconds

    last_display_update_ms = 0
    display_update_interval_ms = 200 # Update display every 200ms
    noise_update_interval_ms = 100 # 更新噪声显示字符串的频率
    noise_calc_interval_ms = 50   # 计算 RMS 的频率 (可以比显示更频繁)
    last_noise_calc_ms = 0
    last_noise_update_ms = 0  # <<<--- 修复：定义 last_noise_update_ms


    temperature_str = "N/A"
    humidity_str = "N/A"
    lux_str = "N/A"
    pressed_key_names = "--"
    noise_level_str = "N/A"
    loop_count = 0
    i2s_read_success_count = 0 # <<<--- 新增：统计成功读取次数
    i2s_read_zero_count = 0    # <<<--- 新增：统计读取到0字节次数

    current_noise_rms = 0.0

    gc.collect()
    print(f"Initial free memory: {gc.mem_free()} bytes")
    print(f"[MAIN] I2S object after init: {i2s}")
    print(f"[MAIN] I2S buffer object after init: {'Exists' if i2s_buffer else 'None'}")

    # --- Main Loop ---
    try:
        while True:
            current_time_ms = time.ticks_ms()

            # --- a. Read Keypad Input ---
            pressed_list = []
            for name, pin in keys.items():
                if not pin.value(): # Active low (pressed when value is 0)
                    pressed_list.append(name.upper())
            pressed_key_names = ",".join(pressed_list) if pressed_list else "--"

            # --- b. Read I2C Sensors (Timed) ---
            if time.ticks_diff(current_time_ms, last_sensor_read_ms) >= sensor_read_interval_ms:
                last_sensor_read_ms = current_time_ms
                # Read Temperature/Humidity
                if temp_hum_sensor:
                    try:
                        t = temp_hum_sensor.temperature()
                        h = temp_hum_sensor.humidity()
                        temperature_str = f"{t:.1f}"
                        humidity_str = f"{h:.1f}"
                    except Exception as e:
                        print(f"Warn: Failed reading SI7021: {e}")
                        temperature_str = "Err"
                        humidity_str = "Err"
                # Read Light Sensor
                if light_sensor:
                    try:
                        l = light_sensor.read()
                        lux_str = f"{l:.1f}"
                    except Exception as e:
                        print(f"Warn: Failed reading BH1750: {e}")
                        lux_str = "Err"

            # --- c. Read I2S Audio Input & Calculate Noise ---
            # <<<--- 修改：加入详细日志和定时计算 ---
            if i2s and i2s_buffer:
                # --- 尝试读取 I2S 数据 ---
                bytes_read = 0 # 重置 bytes_read
                try:
                    if I2S_DEBUG_VERBOSE:
                        print(f"[I2S READ @{current_time_ms}] Attempting i2s.readinto(buffer)...")

                    # --- 核心读取操作 ---
                    bytes_read = i2s.readinto(i2s_buffer)
                    # --- END 核心读取操作 ---

                    if I2S_DEBUG_VERBOSE:
                        print(f"[I2S READ @{current_time_ms}] i2s.readinto returned: {bytes_read} bytes")

                    if bytes_read > 0:
                        i2s_read_success_count += 1
                        # --- 定时计算 RMS ---
                        if time.ticks_diff(current_time_ms, last_noise_calc_ms) >= noise_calc_interval_ms:
                           last_noise_calc_ms = current_time_ms
                           if I2S_DEBUG_VERBOSE: print(f"[RMS PROC @{current_time_ms}] Processing {bytes_read} bytes...")
                           current_noise_rms = calculate_rms(i2s_buffer, bytes_read)
                           # 注意：calculate_rms 内部已有日志

                    elif bytes_read == 0:
                        i2s_read_zero_count += 1
                        if I2S_DEBUG_VERBOSE and loop_count % 50 == 0 : # 不要过于频繁地打印0字节读取
                             print(f"[I2S READ @{current_time_ms}] Warning: read 0 bytes.")
                        # 0字节读取可能表示缓冲区暂时为空，通常不是错误，不清空 current_noise_rms
                    else:
                        # readinto 返回负值通常表示错误
                        print(f"[I2S READ @{current_time_ms}] ERROR: i2s.readinto returned negative value: {bytes_read}")
                        current_noise_rms = -1.0 # 标记错误

                except Exception as e:
                    print(f"[I2S READ @{current_time_ms}] CRITICAL ERROR during i2s.readinto or processing: {e}")
                    print(f"[I2S READ @{current_time_ms}] Exception type: {type(e)}")
                    current_noise_rms = -1.0 # Indicate error
                    # 可选：尝试反初始化并重新初始化 I2S？或者直接停止？
                    # try:
                    #     print("[I2S READ] Attempting I2S deinit due to read error...")
                    #     i2s.deinit()
                    #     i2s = None
                    #     # Consider adding a cooldown before trying re-init
                    # except Exception as deinit_e:
                    #      print(f"[I2S READ] Error during deinit after read error: {deinit_e}")

            elif not i2s:
                 if loop_count % 200 == 0: # Don't spam if I2S init failed
                     print("[MAIN] Warning: I2S peripheral object is None. Skipping read.")


            # --- d. Update Display Data String (Timed) ---
            if time.ticks_diff(current_time_ms, last_noise_update_ms) >= noise_update_interval_ms:
                last_noise_update_ms = current_time_ms
                if current_noise_rms >= 0:
                    noise_level_str = f"{current_noise_rms:.1f}"
                else:
                    noise_level_str = "Err"

            # --- e. Update LCD Display (Timed) ---
            # <<<--- 修改：添加噪声显示 ---
            if display and time.ticks_diff(current_time_ms, last_display_update_ms) >= display_update_interval_ms:
                last_display_update_ms = current_time_ms
                try:
                    display.fill(st7789.BLACK)
                    if default_font:
                        fg_color = st7789.WHITE
                        bg_color = st7789.BLACK
                        wifi_status = "W+" if wifi and wifi.isconnected() else "W-"
                        ble_status = "B+" if ble and ble.active() else "B-"
                        status_line = f"{wifi_status} {ble_status} Loop:{loop_count}"
                        display.write(default_font, status_line, 0, 0, fg_color, bg_color)
                        display.write(default_font, f"Temp: {temperature_str} C", 0, 20, fg_color, bg_color)
                        display.write(default_font, f"Humi: {humidity_str} %", 0, 40, fg_color, bg_color)
                        display.write(default_font, f"Lux:  {lux_str} lx", 0, 60, fg_color, bg_color)
                        display.write(default_font, f"Keys: {pressed_key_names}", 0, 80, fg_color, bg_color)
                        display.write(default_font, f"Mem: {gc.mem_free()}", 0, 100, st7789.GREEN, bg_color)
                        # --- 添加噪声显示行 ---
                        display.write(default_font, f"Noise:{noise_level_str} RMS", 0, 120, st7789.WHITE, st7789.BLACK)
                        # --- End of added line ---
                    else:
                        display.fill_rect(10, 10, display.width - 20, 20, st7789.RED)
                except Exception as e:
                    print(f"Warn: Error updating display: {e}")

            # --- f. Handle BLE Connections/Events ---
            # This part requires more specific logic based on your BLE application

            # --- g. Handle WiFi Reconnection ---
            # Simple check, could be more robust (e.g., exponential backoff)

            # --- h. Yield control ---
            # <<<--- 修改：稍微调整延时，确保 I2S 有机会填充缓冲区 ---
            # time.sleep_ms(20)
            # 短暂延时，具体值可能需要根据系统负载和 I2S 速率调整
            # 如果噪声更新频率很高，这里的延时可以短一些
            time.sleep_ms(10)
            loop_count += 1

            # Optional: Periodic garbage collection
            if loop_count % 100 == 0:
                print(f"Loop {loop_count}, Mem free: {gc.mem_free()}, Noise RMS: {current_noise_rms:.2f}") # 添加内存和噪声打印
                gc.collect()

    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
    finally:
        # --- Cleanup resources ---
        print("Cleaning up resources...")
        if i2s:
            print("Deinitializing I2S...")
            i2s.deinit()
        if display:
             try:
                  bl_pin = Pin(LCD_BL_PIN, Pin.OUT)
                  bl_pin.value(0)
                  print("Display backlight off.")
             except Exception as e:
                  print(f"Warn: Could not turn off backlight: {e}")
        if wifi and wifi.active():
            print("Deactivating WiFi...")
            wifi.active(False)
        if ble and ble.active():
            print("Deactivating Bluetooth...")
            ble.active(False)
        if i2c:
             print("I2C bus closing.")
             pass

        print("Cleanup complete. Application finished.")