# bh1750.py
# MicroPython driver for the BH1750 Ambient Light Sensor

from machine import I2C
from time import sleep_ms

# I2C 地址
BH1750_DEFAULT_ADDRESS = 0x23
BH1750_SECONDARY_ADDRESS = 0x5C

# 操作码 (Commands/Opcodes)
_CMD_POWER_DOWN = 0x00
_CMD_POWER_ON = 0x01
_CMD_RESET = 0x07
_CMD_CONT_HIGH_RES_MODE = 0x10  # 连续高分辨率模式 1 (1lx, 120ms)
_CMD_CONT_HIGH_RES_MODE_2 = 0x11 # 连续高分辨率模式 2 (0.5lx, 120ms)
_CMD_CONT_LOW_RES_MODE = 0x13   # 连续低分辨率模式 (4lx, 16ms)
_CMD_ONCE_HIGH_RES_MODE = 0x20   # 单次高分辨率模式 1
_CMD_ONCE_HIGH_RES_MODE_2 = 0x21  # 单次高分辨率模式 2
_CMD_ONCE_LOW_RES_MODE = 0x23    # 单次低分辨率模式

# 转换因子 (根据数据手册)
_CONVERSION_FACTOR = 1.2

class BH1750:
    """
    用于 BH1750 光照传感器的 MicroPython 驱动类。
    """
    def __init__(self, i2c, address=BH1750_DEFAULT_ADDRESS):
        """
        初始化传感器。
        参数:
            i2c (I2C): 已初始化的 machine.I2C 对象。
            address (int): 传感器的 I2C 地址 (0x23 或 0x5C)。
        """
        if not isinstance(i2c, I2C):
             raise TypeError("I2C object required.")
        self._i2c = i2c
        self._address = address
        self._buffer = bytearray(2) # 用于读取数据
        # 初始化时确保传感器上电并重置
        self.power_on()
        self.reset()
        # 可以选择设置一个默认模式，或者让用户在读取时指定
        # self.set_mode(_CMD_CONT_HIGH_RES_MODE)

    def _write_cmd(self, command):
        """发送命令 (私有方法)"""
        try:
            self._i2c.writeto(self._address, bytes([command]))
            sleep_ms(10) # 短暂延时确保命令被接收
            return True
        except OSError as e:
            # print(f"BH1750 I2C Error writing command {command:#x}: {e}")
            return False

    def power_on(self):
        """给传感器上电"""
        return self._write_cmd(_CMD_POWER_ON)

    def power_off(self):
        """关闭传感器电源"""
        return self._write_cmd(_CMD_POWER_DOWN)

    def reset(self):
        """重置传感器 (会清除测量寄存器，需要重新设置模式)"""
        self.power_on() # 重置前需要先上电
        return self._write_cmd(_CMD_RESET)

    def set_mode(self, mode):
         """
         设置测量模式。
         参数:
             mode (int): 操作码，例如 _CMD_CONT_HIGH_RES_MODE。
         """
         return self._write_cmd(mode)

    def read(self, mode=_CMD_ONCE_HIGH_RES_MODE):
        """
        执行一次测量并读取光照强度 (勒克斯, lx)。
        默认使用单次高分辨率模式 1。
        参数:
            mode (int): 使用的测量模式的操作码。
                       对于单次模式，函数会发送命令并等待转换完成。
                       对于连续模式，假设模式已预先设置，函数只负责读取。
        返回:
            float: 光照强度 (lx)，如果读取失败则返回 None。
        """
        # 发送模式命令 (如果是单次模式)
        if mode in [_CMD_ONCE_HIGH_RES_MODE, _CMD_ONCE_HIGH_RES_MODE_2, _CMD_ONCE_LOW_RES_MODE]:
            if not self.set_mode(mode):
                 return None # 发送命令失败

            # 等待转换完成 (根据模式选择延时)
            if mode == _CMD_ONCE_LOW_RES_MODE:
                sleep_ms(24) # 低分辨率大约 16ms，加一点余量
            else:
                sleep_ms(180) # 高分辨率大约 120ms，加一点余量
        # else: # 如果是连续模式，假设已经调用 set_mode 设置好了，这里直接读取
             # sleep_ms(10) # 连续模式也需要短暂延时确保数据更新?

        # 从传感器读取 2 字节数据
        try:
            self._i2c.readfrom_into(self._address, self._buffer)
        except OSError as e:
            # print(f"BH1750 I2C Error reading data: {e}")
            return None

        # 转换数据
        raw_value = int.from_bytes(self._buffer, 'big') # 大端格式
        lux = raw_value / _CONVERSION_FACTOR

        # 根据模式调整 (模式2 分辨率更高，需要除以 2 吗？手册似乎没说需要额外调整)
        # if mode in [_CMD_CONT_HIGH_RES_MODE_2, _CMD_ONCE_HIGH_RES_MODE_2]:
        #     lux /= 2.0

        return lux

    # 为常用模式提供便捷方法 (可选)
    def luminance(self, mode=_CMD_ONCE_HIGH_RES_MODE):
        """测量并返回光照强度 (lx)，是 read() 的别名。"""
        return self.read(mode)