# -*- coding: utf-8 -*-
# 适用于 MicroPython 的 ST7789 TFT 显示屏驱动程序
# (修改版：仅支持转换后的 TrueType 字体)

import struct  # 用于数据打包
# 导入必要的模块
from time import sleep_ms  # 用于延时

from micropython import const

print("--- Loading ST7789 Driver: VERSION XYZ (Verbose Debug) ---")

# ST7789 命令定义
_ST7789_SWRESET = b"\x01"  # 软件复位
_ST7789_SLPIN = b"\x10"   # 进入睡眠模式
_ST7789_SLPOUT = b"\x11"  # 退出睡眠模式
_ST7789_NORON = b"\x13"   # 正常显示模式开
_ST7789_INVOFF = b"\x20"  # 显示反相关
_ST7789_INVON = b"\x21"   # 显示反相开
_ST7789_DISPOFF = b"\x28" # 显示关
_ST7789_DISPON = b"\x29"  # 显示开
_ST7789_CASET = b"\x2a"   # 列地址设置
_ST7789_RASET = b"\x2b"   # 行地址设置
_ST7789_RAMWR = b"\x2c"   # 内存写入
_ST7789_VSCRDEF = b"\x33" # 垂直滚动定义
_ST7789_COLMOD = b"\x3a"  # 接口像素格式
_ST7789_MADCTL = b"\x36"  # 内存访问控制
_ST7789_VSCSAD = b"\x37"  # 垂直滚动起始地址

# MADCTL (内存访问控制) 命令的位定义
_ST7789_MADCTL_MY = const(0x80)  # 行地址顺序
_ST7789_MADCTL_MX = const(0x40)  # 列地址顺序
_ST7789_MADCTL_MV = const(0x20)  # 行/列交换
_ST7789_MADCTL_ML = const(0x10)  # 垂直刷新顺序
_ST7789_MADCTL_BGR = const(0x08) # 颜色顺序 (1=BGR, 0=RGB)
_ST7789_MADCTL_MH = const(0x04)  # 水平刷新顺序
_ST7789_MADCTL_RGB = const(0x00) # 颜色顺序 RGB

# 颜色顺序常量
RGB = const(0x00)
BGR = const(0x08)

# 颜色模式常量 (固定使用 16bit RGB565)
_COLOR_MODE_16BIT = const(0x05)

# 预定义颜色常量 (RGB565 格式)
BLACK = const(0x0000)
BLUE = const(0x001F)
RED = const(0xF800)
GREEN = const(0x07E0)
CYAN = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW = const(0xFFE0)
WHITE = const(0xFFFF)

# 数据打包格式
_ENCODE_PIXEL = const(">H") # 16位像素，大端格式
_ENCODE_POS = const(">HH")  # 两个16位坐标，大端格式

# fmt: off
# 禁用代码格式化，保持表格对齐

# 不同屏幕尺寸的旋转参数表
_DISPLAY_240x320 = ( (0x00, 240, 320,  0,  0, False), (0x60, 320, 240,  0,  0, False), (0xc0, 240, 320,  0,  0, False), (0xa0, 320, 240,  0,  0, False) )
_DISPLAY_240x240 = ( (0x00, 240, 240,  0,  0, False), (0x60, 240, 240,  0,  0, False), (0xc0, 240, 240,  0, 80, False), (0xa0, 240, 240, 80,  0, False) )
_DISPLAY_135x240 = ( (0x00, 135, 240, 52, 40, False), (0x60, 240, 135, 40, 53, False), (0xc0, 135, 240, 53, 40, False), (0xa0, 240, 135, 40, 52, False) )
_DISPLAY_128x128 = ( (0x00, 128, 128,  2,  1, False), (0x60, 128, 128,  1,  2, False), (0xc0, 128, 128,  2,  1, False), (0xa0, 128, 128,  1,  2, False) )

# 旋转表元组的索引常量
_WIDTH = const(1)
_HEIGHT = const(2)
_XSTART = const(3)
_YSTART = const(4)

# 支持的显示列表 (物理宽度, 物理高度, 对应的旋转表)
_SUPPORTED_DISPLAYS = ( (240, 320, _DISPLAY_240x320), (240, 240, _DISPLAY_240x240), (135, 240, _DISPLAY_135x240), (128, 128, _DISPLAY_128x128) )

# ST7789 标准初始化命令序列
_ST7789_INIT_CMDS = (
    ( b'\x11', b'', 120),                # 退出睡眠模式 (SLPOUT)
    ( b'\x3a', b'\x55', 10),             # 设置像素格式 (COLMOD): 0x55 -> 16 bits/pixel (RGB565)
    ( b'\x36', b'\x00', 0),               # 设置内存访问控制 (MADCTL): 默认值 (后面根据旋转更新)
    ( b'\xb2', b'\x0c\x0c\x00\x33\x33', 0), # Porch 控制
    ( b'\xb7', b'\x35', 0),               # Gate 控制
    ( b'\xbb', b'\x19', 0),               # VCOMS 设置 (可调整)
    ( b'\xc0', b'\x2c', 0),               # Power 控制 1
    ( b'\xc2', b'\x01', 0),               # Power 控制 2
    ( b'\xc3', b'\x12', 0),               # Power 控制 3
    ( b'\xc4', b'\x20', 0),               # Power 控制 4
    ( b'\xc6', b'\x0f', 0),               # VCOM 控制 1
    ( b'\xd0', b'\xa4\xa1', 0),           # Power 控制 A
    ( b'\xe0', b'\xd0\x00\x05\x0e\x15\x0d\x37\x43\x47\x09\x15\x12\x16\x19', 0), # Gamma 设置 (+)
    ( b'\xe1', b'\xd0\x00\x05\x0d\x0c\x06\x2d\x44\x45\x0b\x16\x14\x17\x1b', 0), # Gamma 设置 (-)
    # ( b'\x21', b'', 10),                  # 可选：打开显示反相 (INVON)
    ( b'\x29', b'', 120)                 # 打开显示 (DISPON)
)
# fmt: on
# 重新启用代码格式化

def color565(r, g, b):
    """将 RGB(0-255) 转换为 16位 RGB565 颜色值"""
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3

class ST7789:
    """
    ST7789 驱动类 (仅支持 TrueType 转换字体)

    初始化参数:
        spi (SPI): 配置好的 machine.SPI 对象 **(必需)**
        width (int): 显示屏的物理宽度 (像素) **(必需)**
        height (int): 显示屏的物理高度 (像素) **(必需)**
        reset (Pin): 连接到屏幕 RESET 引脚的 machine.Pin 对象 (可选, 推荐)
        dc (Pin): 连接到屏幕 DC (Data/Command) 引脚的 machine.Pin 对象 **(必需)**
        cs (Pin): 连接到屏幕 CS (Chip Select) 引脚的 machine.Pin 对象 (可选)
        backlight (Pin): 连接到屏幕背光控制引脚的 machine.Pin 对象 (可选)
        rotation (int): 屏幕旋转方向 (0=0度, 1=90度, 2=180度, 3=270度, 默认为0)
        color_order (int): 颜色顺序 (ST7789.RGB 或 ST7789.BGR, 默认为 BGR)
        custom_init (tuple): 自定义初始化命令序列 (可选)
        custom_rotations (tuple): 自定义旋转参数表 (可选)
    """
    def __init__(
        self, spi, width, height, reset=None, dc=None, cs=None, backlight=None,
        rotation=0, color_order=BGR, custom_init=None, custom_rotations=None,
    ):
        if dc is None: raise ValueError("dc 引脚是必需的.")
        self.rotations = custom_rotations or self._find_rotations(width, height)
        if not self.rotations:
            supported = ", ".join([f"{w}x{h}" for w, h, _ in _SUPPORTED_DISPLAYS])
            raise ValueError(f"不支持的 {width}x{height} 显示. 支持: {supported}")

        self.physical_width = width
        self.physical_height = height
        self.spi = spi
        self.reset = reset
        self.dc = dc
        self.cs = cs
        self.backlight = backlight
        self.color_order = color_order
        self.init_cmds = custom_init or _ST7789_INIT_CMDS

        self._rotation = rotation % len(self.rotations)
        self.rotation(self._rotation) # 应用初始旋转设置

        self.hard_reset()
        self.init(self.init_cmds)
        self.fill(BLACK)
        if self.backlight is not None: self.backlight.value(1)
        print(f"ST7789 (TTF only) Initialized: {self.width}x{self.height}, Rot: {self._rotation}")

    @staticmethod
    def _find_rotations(width, height):
        """根据物理宽高查找内置的旋转表"""
        for w, h, rot_table in _SUPPORTED_DISPLAYS:
            if w == width and h == height: return rot_table
        return None

    # --- init 方法: 注释掉调试信息 ---
    def init(self, commands):
        """执行初始化命令序列"""
        print("Sending init commands...") # 保留开始信息
        for command, data, delay in commands:
            cmd_hex = command.hex() if command else "None"
            data_hex = data.hex() if data is not None else "None"
            # 注释掉循环内的详细打印
            # print(f"  init loop: Processing cmd={cmd_hex}, data={data_hex}, delay={delay}")
            try:
                self._write(command, data)
            except Exception as e:
                # 保留异常捕获和打印
                print(f"  init loop: *** EXCEPTION CAUGHT WHILE PROCESSING cmd={cmd_hex}, data={data_hex} ***")
                print(f"  init loop: Exception details: {e}")
                raise # 重新抛出以停止初始化

            if delay > 0:
                sleep_ms(delay)
        print("Init complete.") # 保留完成信息

    # --- _write 方法: 注释掉大部分调试信息，保留核心逻辑和错误处理 ---
    def _write(self, command=None, data=None):
        """通过 SPI 写入命令/数据 (底层) - 清理版"""
        # print("--- ENTERING _write (Cleaned Version) ---") # 可选保留，或删除
        cmd_hex = command.hex() if command is not None else "None"
        # data_info = f"type={type(data).__name__}" if data is not None else "data=None" # 已注释
        data_len = -1

        # --- 1. 验证和计算 Data Length ---
        try:
            if data is None:
                data_len = 0
            elif isinstance(data, (bytes, bytearray)):
                data_len = len(data)
            else:
                # 保留意外类型警告
                print(f"    _write: *** WARNING: Unexpected data type: {type(data).__name__} ***")
                data_len = 0
            # 注释掉详细的开始打印
            # print(f"  _write: START - cmd={cmd_hex}, {data_info}, determined_data_len={data_len}")
        except Exception as e:
            # 保留计算长度时的异常
            print(f"    _write: *** EXCEPTION during data validation/len calc: {e} ***")
            data_len = -1

        # --- 2. SPI 操作 ---
        if self.cs:
            try:
                self.cs.value(0)
            except Exception as e:
                 # 保留 CS 控制异常
                print(f"    _write: *** EXCEPTION setting CS low: {e} ***")

        # --- 3. 发送命令 ---
        if command is not None:
            if self.dc:
                try:
                    self.dc.value(0)
                except Exception as e:
                    # 保留 DC 控制异常
                    print(f"    _write: *** EXCEPTION setting DC low: {e} ***")

            # print(f"    _write: Attempting spi.write(command) for {cmd_hex}...") # 已注释
            try:
                self.spi.write(command)
                # print(f"    _write: Command {cmd_hex} sent successfully.") # 已注释
            except Exception as e:
                 # 保留命令发送异常
                print(f"    _write: *** EXCEPTION during spi.write(command): {e} ***")
                if self.cs: self.cs.value(1)
                raise
        # else:
        #     print(f"    _write: No command provided.") # 已注释

        # --- 4. 发送数据 (防护加强) ---
        # print(f"    _write: Evaluating condition to send data: ...") # 已注释
        if data is not None and isinstance(data, (bytes, bytearray)) and data_len > 0:
            # print(f"    _write: CONDITION PASSED. Attempting to send {data_len} bytes of data.") # 已注释
            if self.dc:
                try:
                    self.dc.value(1)
                except Exception as e:
                    # 保留 DC 控制异常
                    print(f"    _write: *** EXCEPTION setting DC high: {e} ***")

            # print(f"    _write: Executing spi.write(data) for {data_len} bytes...") # 已注释
            try:
                self.spi.write(data)
                # print(f"    _write: Data ({data_len} bytes) sent successfully.") # 已注释
            except Exception as e:
                # 保留数据发送异常
                print(f"    _write: *** CRITICAL EXCEPTION during spi.write(data) (len={data_len}): {e} ***")
                if self.cs: self.cs.value(1)
                raise
        # else:
            # print(f"    _write: CONDITION FAILED. Skipping spi.write(data). Determined data_len was {data_len}.") # 已注释

        # --- 5. 结束传输 ---
        if self.cs:
            try:
                self.cs.value(1)
            except Exception as e:
                 # 保留 CS 控制异常
                print(f"    _write: *** EXCEPTION setting CS high: {e} ***")

        # print(f"  _write: END - cmd={cmd_hex}") # 已注释

    def hard_reset(self):
        """执行硬件复位"""
        if self.reset:
            print("Hard reset...")
            if self.cs: self.cs.value(1)
            self.reset.value(1); sleep_ms(10)
            self.reset.value(0); sleep_ms(10)
            self.reset.value(1); sleep_ms(120)
            if self.cs: self.cs.value(1)
            print("Hard reset done.")
        else: self.soft_reset()

    def soft_reset(self):
        """执行软件复位"""
        print("Soft reset...")
        self._write(_ST7789_SWRESET); sleep_ms(150)
        print("Soft reset done.")

    def sleep_mode(self, value):
        """进入/退出睡眠模式"""
        if value: self._write(_ST7789_SLPIN); print("Sleep mode ON.")
        else: self._write(_ST7789_SLPOUT); sleep_ms(120); print("Sleep mode OFF.")

    def inversion_mode(self, value):
        """开启/关闭显示反相"""
        if value: self._write(_ST7789_INVON); print("Inversion ON.")
        else: self._write(_ST7789_INVOFF); print("Inversion OFF.")

    def rotation(self, rotation):
        """设置屏幕旋转方向"""
        num_rotations = len(self.rotations)
        rotation %= num_rotations
        self._rotation = rotation
        madctl_val, self.width, self.height, self.xstart, self.ystart, _ = self.rotations[rotation]
        madctl_cmd = madctl_val | self.color_order
        self._write(_ST7789_MADCTL, bytes([madctl_cmd]))
        print(f"Rotation: {rotation} ({self.width}x{self.height}), MADCTL: {madctl_cmd:#04x}")

    def _set_window(self, x0, y0, x1, y1):
        """设置绘图窗口区域 (私有)"""
        if 0 <= x0 <= x1 < self.width and 0 <= y0 <= y1 < self.height:
            self._write(_ST7789_CASET, struct.pack(_ENCODE_POS, x0 + self.xstart, x1 + self.xstart))
            self._write(_ST7789_RASET, struct.pack(_ENCODE_POS, y0 + self.ystart, y1 + self.ystart))
            self._write(_ST7789_RAMWR)

    def vline(self, x, y, length, color):
        """绘制垂直线"""
        self.fill_rect(x, y, 1, length, color)

    def hline(self, x, y, length, color):
        """绘制水平线"""
        self.fill_rect(x, y, length, 1, color)

    def pixel(self, x, y, color):
        """绘制单个像素"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._set_window(x, y, x, y)
            self._write(None, struct.pack(_ENCODE_PIXEL, color))

    def blit_buffer(self, buffer, x, y, width, height):
        """高效绘制缓冲区图像数据"""
        if x < 0: width += x; x = 0
        if y < 0: height += y; y = 0
        if x + width > self.width: width = self.width - x
        if y + height > self.height: height = self.height - y
        if width <= 0 or height <= 0: return
        self._set_window(x, y, x + width - 1, y + height - 1)
        self._write(None, buffer)

    def rect(self, x, y, width, height, color):
        """绘制矩形边框"""
        self.hline(x, y, width, color)
        self.vline(x, y, height, color)
        self.vline(x + width - 1, y, height, color)
        self.hline(x, y + height - 1, width, color)

    def fill_rect(self, x, y, width, height, color):
        """绘制填充矩形"""
        if x < 0: width += x; x = 0
        if y < 0: height += y; y = 0
        if x + width > self.width: width = self.width - x
        if y + height > self.height: height = self.height - y
        if width <= 0 or height <= 0: return
        self._set_window(x, y, x + width - 1, y + height - 1)
        num_pixels = width * height
        pixel_bytes = struct.pack(_ENCODE_PIXEL, color)
        chunk_size_pixels = 256
        chunk_size_bytes = chunk_size_pixels * 2
        chunk_data = pixel_bytes * chunk_size_pixels
        full_chunks = num_pixels // chunk_size_pixels
        remaining_pixels = num_pixels % chunk_size_pixels
        self.dc.value(1)
        if self.cs: self.cs.value(0)
        for _ in range(full_chunks): self.spi.write(chunk_data)
        if remaining_pixels > 0: self.spi.write(pixel_bytes * remaining_pixels)
        if self.cs: self.cs.value(1)

    def fill(self, color):
        """用指定颜色填充整个屏幕"""
        self.fill_rect(0, 0, self.width, self.height, color)

    def line(self, x0, y0, x1, y1, color):
        """使用 Bresenham 算法绘制直线"""
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep: x0, y0 = y0, x0; x1, y1 = y1, x1
        if x0 > x1: x0, x1 = x1, x0; y0, y1 = y1, y0
        dx = x1 - x0; dy = abs(y1 - y0); err = dx // 2
        ystep = 1 if y0 < y1 else -1
        while x0 <= x1:
            if steep: self.pixel(y0, x0, color)
            else: self.pixel(x0, y0, color)
            err -= dy
            if err < 0: y0 += ystep; err += dx
            x0 += 1

    def vscrdef(self, tfa, vsa, bfa):
        """定义垂直滚动区域"""
        self._write(_ST7789_VSCRDEF, struct.pack(">HHH", tfa, vsa, bfa))

    def vscsad(self, vssa):
        """设置垂直滚动起始地址"""
        self._write(_ST7789_VSCSAD, struct.pack(">H", vssa))

    # --- TrueType 字体支持 ---
    # 注意：需要配合使用 TTF 字体转换工具生成的 .py 字体模块
    # 字体模块需要包含: MAP, OFFSETS, WIDTHS, BITMAPS, HEIGHT, MAX_WIDTH, OFFSET_WIDTH

    def write(self, font, string, x, y, fg=WHITE, bg=BLACK):
        """
        使用转换后的 TrueType 字体在屏幕上书写字符串。
        参数:
            font (module): 包含转换后字体数据的模块
            string (str): 要书写的字符串
            x, y (int): 起始坐标 (左上角)
            fg (int): 前景色 (字符颜色, 默认白色)
            bg (int): 背景色 (默认黑色)
        """
        # 检查字体模块是否有效 (基本检查)
        if not all(hasattr(font, attr) for attr in ['MAP', 'OFFSETS', 'WIDTHS', 'BITMAPS', 'HEIGHT', 'MAX_WIDTH', 'OFFSET_WIDTH']):
             print("错误: 提供的字体模块格式不正确 (缺少必需属性).")
             return

        buffer_len = font.HEIGHT * font.MAX_WIDTH * 2 # 创建足够大的缓冲区
        buffer = bytearray(buffer_len)
        fg_hi = fg >> 8
        fg_lo = fg & 0xFF
        bg_hi = bg >> 8
        bg_lo = bg & 0xFF

        for character in string:
            try:
                # 查找字符在字体 MAP 中的索引
                char_index = font.MAP.index(character)
                # 计算字符位图数据在 BITMAPS 中的起始位偏移
                offset = char_index * font.OFFSET_WIDTH
                bs_bit = font.OFFSETS[offset]
                if font.OFFSET_WIDTH > 1:
                    bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 1]
                if font.OFFSET_WIDTH > 2: # 处理 3 字节偏移
                    bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 2]

                # 获取字符的实际宽度
                char_width = font.WIDTHS[char_index]
                # 计算绘制该字符需要的缓冲区字节数
                buffer_needed = char_width * font.HEIGHT * 2

                # 从字体位图数据 (font.BITMAPS) 中提取像素信息并填充缓冲区
                pixel_byte_index = 0
                for _ in range(buffer_needed // 2): # 遍历字符的每个像素
                    # 检查 BITMAPS 中的对应位是否为 1
                    if font.BITMAPS[bs_bit >> 3] & (1 << (7 - (bs_bit & 7))):
                        # 前景色
                        buffer[pixel_byte_index] = fg_hi
                        buffer[pixel_byte_index + 1] = fg_lo
                    else:
                        # 背景色
                        buffer[pixel_byte_index] = bg_hi
                        buffer[pixel_byte_index + 1] = bg_lo
                    bs_bit += 1 # 移动到位图数据的下一位
                    pixel_byte_index += 2 # 移动到缓冲区的下一个像素位置

                # 计算字符绘制的结束坐标
                to_col = x + char_width - 1
                to_row = y + font.HEIGHT - 1

                # 检查是否超出屏幕边界
                if self.width > to_col and self.height > to_row:
                    # 设置窗口并使用 blit_buffer 绘制字符缓冲区
                    self._set_window(x, y, to_col, to_row)
                    self._write(None, buffer[:buffer_needed]) # 只发送需要的字节

                # 更新下一个字符的起始 x 坐标
                x += char_width

            except ValueError:
                # 如果字符在字体 MAP 中找不到，则忽略该字符
                pass
            except IndexError:
                 # 防止字体数据索引越界
                 print(f"警告: 字体数据索引错误，可能字体文件已损坏或不完整 (字符: {character})")
                 pass # 继续处理下一个字符

    def write_width(self, font, string):
        """
        计算使用指定 TrueType 转换字体书写字符串时的总像素宽度。
        参数:
            font (module): 包含转换后字体数据的模块
            string (str): 要测量的字符串
        返回:
            int: 字符串的总像素宽度
        """
        # 检查字体模块是否有效
        if not all(hasattr(font, attr) for attr in ['MAP', 'WIDTHS']):
             print("错误: 字体模块格式不正确 (缺少 MAP 或 WIDTHS).")
             return 0

        width = 0
        for character in string:
            try:
                # 查找字符索引并累加其宽度
                char_index = font.MAP.index(character)
                width += font.WIDTHS[char_index]
            except ValueError:
                # 忽略找不到的字符
                pass
            except IndexError:
                 print(f"警告: 字体宽度数据索引错误 (字符: {character})")
                 pass
        return width