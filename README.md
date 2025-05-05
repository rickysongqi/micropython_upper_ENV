# ESP32-S3 Multi-Sensor Hub with LCD, BLE, WiFi, and Alerts

This MicroPython project transforms an ESP32-S3 board into a versatile sensor hub featuring:

*   **LCD Display (ST7789):** A multi-page user interface showing real-time sensor data, network status, and system information.
*   **Wireless Connectivity:**
    *   **WiFi:** Connects to a local network, enables WebREPL for remote debugging, and runs a simple TCP server.
    *   **Bluetooth Low Energy (BLE):** Advertises sensor data using the standard Environmental Sensing Service (ESS) profile, allowing connection from mobile apps or other BLE clients.
*   **Sensors:**
    *   **SI7021:** Temperature and Humidity sensor (via I2C).
    *   **BH1750:** Ambient Light sensor (via I2C).
    *   **I2S Microphone:** Measures ambient noise level (RMS).
*   **User Input:** 5-button keypad (Up, Down, Left, Right, Enter) for navigating the UI and controlling features.
*   **Visual/Audible Feedback:**
    *   **WS2812 RGB LEDs (Neopixel):** Displays status with a breathing effect and flashes red during alerts.
    *   **Passive Buzzer:** Provides audible alerts synchronized with LED flashing.
*   **Alert System:** Triggers LED flashing and buzzer sound when sensor readings exceed configurable thresholds (Temperature, Humidity, Light, Noise).
*   **TCP Server:** Listens on port 8888 for incoming connections and responds to a `GET_CURRENT` command with current sensor data in JSON format.

## Features

*   **Multi-Page UI:**
    *   **Page 0 (Main):** Displays WiFi/BLE status, Temperature, Humidity, Lux, Noise Level (smoothed RMS), and Free Memory.
    *   **Page 1 (Network):** Shows Network connection status, SSID, IP Address, Subnet Mask, and Gateway.
*   **BLE Environmental Sensing Service:**
    *   Exposes standard characteristics for Temperature (`0x2A6E`), Humidity (`0x2A6F`), and Illuminance (`0x2AFB`).
    *   Exposes a custom characteristic for Noise Level (`8eb6184d-bec0-41b0-8eba-e350662524ff`).
    *   Supports notifications for all sensor characteristics.
*   **LED Control:**
    *   Smooth breathing effect with configurable color, speed, minimum brightness, and phase shift between LEDs.
    *   Gamma correction for more visually linear brightness changes.
    *   Red flashing alert state triggered by sensor thresholds.
    *   Right key press toggles the LED effect on/off.
*   **Buzzer Alert:** Activates concurrently with the red LED flash during sensor alerts.
*   **Keypad Control:**
    *   Up/Down: Navigate between UI pages (with debounce).
    *   Right: Toggle WS2812 LED effect on/off (with debounce).
    *   Left/Enter: Currently read but no specific action assigned (displayed on Page 0).
*   **Noise Measurement:** Reads audio data from I2S microphone, calculates RMS value, and applies a smoothing filter for display. Raw RMS values are used for triggering alerts.
*   **WebREPL:** Enabled if WiFi connects successfully, allowing remote access to the MicroPython REPL.
*   **Configuration:** Key parameters like WiFi credentials, BLE name, pin assignments, sensor thresholds, UI colors, and LED effects are defined as constants at the beginning of `main.py`.

## Hardware Requirements (Based on `main.py` constants)

*   **Microcontroller:** ESP32-S3 based board.
*   **Display:** ST7789 SPI LCD (240x320).
    *   SPI ID: 2
    *   Pins: SCLK(12), MOSI(11), CS(3), DC(46), RST(9), BL(8)
*   **Keypad:** 5 momentary buttons connected to GPIOs with pull-up resistors.
    *   Pins: UP(2), DOWN(41), LEFT(40), RIGHT(1), ENTER(42)
*   **Sensors:**
    *   SI7021 Temp/Hum Sensor (I2C Addr: 0x40)
    *   BH1750 Light Sensor (I2C Addr: 0x23)
    *   I2C Bus: ID 0, SCL(39), SDA(38)
    *   I2S Microphone (e.g., INMP441 or similar)
    *   I2S Pins: BCLK(17), WS(16), DIN(15)
*   **LEDs:** WS2812 RGB LEDs (Neopixel compatible).
    *   Pin: 18
    *   Number of LEDs: 4
*   **Buzzer:** Passive Buzzer.
    *   Pin: 4

## Software Dependencies

*   MicroPython firmware for ESP32-S3.
*   `st7789.py`: Driver for the ST7789 LCD.
*   `si7021.py`: Driver for the SI7021 sensor.
*   `bh1750.py`: Driver for the BH1750 sensor.
*   `neopixel.py`: Library for controlling WS2812 LEDs.
*   `ubuntu_24.py`: Font file (converted using a font-to-py tool).
*   `webrepl.py` (Optional, standard in many MicroPython builds).
*   `bluetooth`: Standard MicroPython BLE module.

## Setup

1.  **Hardware:** Connect all components according to the pin definitions in `main.py`.
2.  **Software:**
    *   Flash MicroPython firmware onto your ESP32-S3 board.
    *   Upload `main.py` and all required driver/font files (`st7789.py`, `si7021.py`, `bh1750.py`, `neopixel.py`, `ubuntu_24.py`) to the root directory of the device's filesystem.
3.  **Configuration:** Modify the constants at the beginning of `main.py`, especially:
    *   `WIFI_SSID` and `WIFI_PASSWORD`.
    *   `BLE_DEVICE_NAME`.
    *   Pin assignments if your hardware differs.
    *   Sensor thresholds (`TEMP_THRESHOLD_DIFF`, `HUMI_THRESHOLD_DIFF`, etc.).
    *   LED effect parameters (`BREATH_COLOR_BASE`, `BREATH_SPEED`, etc.).

## Usage

1.  Power on the ESP32-S3 board.
2.  The application will attempt to connect to WiFi.
3.  The LCD will display the main sensor page (Page 0).
4.  Use the **Up** and **Down** keys to switch between Page 0 (Sensors) and Page 1 (Network).
5.  Use the **Right** key to toggle the WS2812 LED breathing effect on or off.
6.  If sensor readings exceed the defined thresholds, the LEDs will flash red, and the buzzer will sound intermittently.
7.  Connect to the device via BLE using a BLE scanner app (like nRF Connect) to view the Environmental Sensing Service and read/subscribe to sensor characteristics.
8.  If WiFi is connected, you can connect to the WebREPL (usually `ws://<device_ip>:8266/`).
9.  If WiFi is connected, you can connect to the TCP server on port 8888. Send the command `GET_CURRENT\n` to receive a JSON object with the latest sensor readings.

---

# ESP32-S3 多传感器中心 (LCD, BLE, WiFi, 警报) - 中文说明

这个 MicroPython 项目将 ESP32-S3 开发板转变为一个多功能传感器中心，具有以下特点：

*   **LCD 显示屏 (ST7789):** 多页面用户界面，显示实时传感器数据、网络状态和系统信息。
*   **无线连接:**
    *   **WiFi:** 连接到本地网络，启用 WebREPL 进行远程调试，并运行一个简单的 TCP 服务器。
    *   **低功耗蓝牙 (BLE):** 使用标准环境传感服务 (ESS) 配置文件广播传感器数据，允许移动应用程序或其他 BLE 客户端连接。
*   **传感器:**
    *   **SI7021:** 温度和湿度传感器 (通过 I2C)。
    *   **BH1750:** 环境光传感器 (通过 I2C)。
    *   **I2S 麦克风:** 测量环境噪音水平 (RMS)。
*   **用户输入:** 5 键键盘 (上、下、左、右、确认) 用于导航 UI 和控制功能。
*   **视觉/听觉反馈:**
    *   **WS2812 RGB LED (Neopixel):** 以呼吸效果显示状态，并在警报期间闪烁红灯。
    *   **无源蜂鸣器:** 提供与 LED 闪烁同步的声音警报。
*   **警报系统:** 当传感器读数超过可配置的阈值 (温度、湿度、光线、噪音) 时，触发 LED 闪烁和蜂鸣器鸣叫。
*   **TCP 服务器:** 在端口 8888 上侦听传入连接，并响应 `GET_CURRENT` 命令，以 JSON 格式返回当前的传感器数据。

## 功能特性

*   **多页面 UI:**
    *   **页面 0 (主页):** 显示 WiFi/BLE 状态、温度、湿度、光照强度 (勒克斯)、噪音水平 (平滑后的 RMS 值) 和可用内存。
    *   **页面 1 (网络):** 显示网络连接状态、SSID、IP 地址、子网掩码和网关。
*   **BLE 环境传感服务:**
    *   公开温度 (`0x2A6E`)、湿度 (`0x2A6F`) 和照度 (`0x2AFB`) 的标准特征。
    *   公开噪音水平的自定义特征 (`8eb6184d-bec0-41b0-8eba-e350662524ff`)。
    *   支持所有传感器特征的通知 (Notify)。
*   **LED 控制:**
    *   平滑的呼吸效果，具有可配置的颜色、速度、最低亮度和 LED 之间的相位差。
    *   伽马校正，使亮度变化在视觉上更线性。
    *   由传感器阈值触发的红色闪烁警报状态。
    *   按下右键可切换 LED 效果的开关状态。
*   **蜂鸣器警报:** 在传感器警报期间与红色 LED 闪烁同时激活。
*   **键盘控制:**
    *   上/下: 在 UI 页面之间导航 (带防抖)。
    *   右: 切换 WS2812 LED 效果的开关状态 (带防抖)。
    *   左/确认: 当前会读取按键状态，但未分配特定操作 (状态显示在页面 0)。
*   **噪音测量:** 从 I2S 麦克风读取音频数据，计算 RMS 值，并应用平滑滤波器进行显示。原始 RMS 值用于触发警报。
*   **WebREPL:** 如果 WiFi 连接成功则启用，允许远程访问 MicroPython REPL。
*   **配置:** 关键参数，如 WiFi 凭据、BLE 名称、引脚分配、传感器阈值、UI 颜色和 LED 效果，都在 `main.py` 开头定义为常量。

## 硬件要求 (基于 `main.py` 中的常量定义)

*   **微控制器:** 基于 ESP32-S3 的开发板。
*   **显示屏:** ST7789 SPI LCD (240x320)。
    *   SPI ID: 2
    *   引脚: SCLK(12), MOSI(11), CS(3), DC(46), RST(9), BL(8)
*   **键盘:** 5 个瞬时按钮，连接到 GPIO 并使用上拉电阻。
    *   引脚: UP(2), DOWN(41), LEFT(40), RIGHT(1), ENTER(42)
*   **传感器:**
    *   SI7021 温湿度传感器 (I2C 地址: 0x40)
    *   BH1750 光照传感器 (I2C 地址: 0x23)
    *   I2C 总线: ID 0, SCL(39), SDA(38)
    *   I2S 麦克风 (例如 INMP441 或类似型号)
    *   I2S 引脚: BCLK(17), WS(16), DIN(15)
*   **LED:** WS2812 RGB LED (兼容 Neopixel)。
    *   引脚: 18
    *   LED 数量: 4
*   **蜂鸣器:** 无源蜂鸣器。
    *   引脚: 4

## 软件依赖

*   适用于 ESP32-S3 的 MicroPython 固件。
*   `st7789.py`: ST7789 LCD 驱动。
*   `si7021.py`: SI7021 传感器驱动。
*   `bh1750.py`: BH1750 传感器驱动。
*   `neopixel.py`: 控制 WS2812 LED 的库。
*   `ubuntu_24.py`: 字体文件 (使用字体转 py 工具转换)。
*   `webrepl.py` (可选, 许多 MicroPython 构建版本中自带)。
*   `bluetooth`: 标准 MicroPython BLE 模块。

## 设置步骤

1.  **硬件:** 根据 `main.py` 中的引脚定义连接所有组件。
2.  **软件:**
    *   将 MicroPython 固件烧录到您的 ESP32-S3 开发板。
    *   将 `main.py` 以及所有必需的驱动/字体文件 (`st7789.py`, `si7021.py`, `bh1750.py`, `neopixel.py`, `ubuntu_24.py`) 上传到设备文件系统的根目录。
3.  **配置:** 修改 `main.py` 开头的常量，特别是：
    *   `WIFI_SSID` 和 `WIFI_PASSWORD`。
    *   `BLE_DEVICE_NAME`。
    *   如果您的硬件不同，请修改引脚分配。
    *   传感器阈值 (`TEMP_THRESHOLD_DIFF`, `HUMI_THRESHOLD_DIFF` 等)。
    *   LED 效果参数 (`BREATH_COLOR_BASE`, `BREATH_SPEED` 等)。

## 使用说明

1.  给 ESP32-S3 开发板上电。
2.  应用程序将尝试连接到 WiFi。
3.  LCD 将显示主传感器页面 (页面 0)。
4.  使用 **上** 和 **下** 键在页面 0 (传感器) 和页面 1 (网络) 之间切换。
5.  使用 **右** 键切换 WS2812 LED 呼吸效果的开关状态。
6.  如果传感器读数超过定义的阈值，LED 将闪烁红灯，并且蜂鸣器将间歇鸣叫。
7.  使用 BLE 扫描器应用程序 (如 nRF Connect) 通过 BLE 连接到设备，以查看环境传感服务并读取/订阅传感器特征。
8.  如果 WiFi 已连接，您可以通过 WebREPL 连接 (通常地址为 `ws://<设备IP>:8266/`)。
9.  如果 WiFi 已连接，您可以连接到端口 8888 上的 TCP 服务器。发送命令 `GET_CURRENT\n` 以接收包含最新传感器读数的 JSON 对象。
