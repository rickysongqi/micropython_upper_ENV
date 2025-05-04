# si7021.py
# MicroPython driver for the SI7021 Temperature and Humidity Sensor

from machine import I2C
from time import sleep_ms

# I2C 地址 (固定)
_SI7021_DEFAULT_ADDRESS = 0x40

# 命令
_CMD_MEASURE_HUMIDITY_HOLD = 0xE5
_CMD_MEASURE_HUMIDITY_NOHOLD = 0xF5 # 不常用
_CMD_MEASURE_TEMP_HOLD = 0xE3
_CMD_MEASURE_TEMP_NOHOLD = 0xF3 # 不常用
_CMD_READ_TEMP_FROM_PREV_RH = 0xE0 # 读取上次湿度测量时的温度
_CMD_RESET = 0xFE
# _CMD_READ_USER_REG = 0xE7
# _CMD_WRITE_USER_REG = 0xE6
# _CMD_READ_ID_1 = b'\xFA\x0F' # 读取 ID 第一部分
# _CMD_READ_ID_2 = b'\xFC\xC9' # 读取 ID 第二部分

class SI7021:
    """
    用于 SI7021 温湿度传感器的 MicroPython 驱动类。
    """
    def __init__(self, i2c, address=_SI7021_DEFAULT_ADDRESS):
        """
        初始化传感器。
        参数:
            i2c (I2C): 已初始化的 machine.I2C 对象。
            address (int): 传感器的 I2C 地址 (固定为 0x40)。
        """
        if not isinstance(i2c, I2C):
             raise TypeError("I2C object required.")
        self._i2c = i2c
        self._address = address
        self._buffer = bytearray(3) # 用于读取数据 (2字节数据 + 1字节CRC)
        # self.reset() # 可选：初始化时复位

    def _read_data(self, command, delay_ms):
        """
        发送命令并读取数据 (私有方法)。
        返回: 读取到的原始字节串 (通常是 2 字节数据)。
        如果读取失败则返回 None。
        """
        try:
            # 发送测量命令
            self._i2c.writeto(self._address, bytes([command]))
            # 等待测量完成
            sleep_ms(delay_ms)
            # 读取数据 (数据 + CRC)
            self._i2c.readfrom_into(self._address, self._buffer)
            # TODO: 添加 CRC 校验 (可选)
            return self._buffer[0:2] # 只返回数据部分
        except OSError as e:
            # print(f"SI7021 I2C Error reading command {command:#x}: {e}")
            return None

    def humidity(self):
        """
        测量并返回相对湿度 (%)。
        返回: 浮点数类型的湿度值，如果读取失败则返回 None。
        """
        raw_data = self._read_data(_CMD_MEASURE_HUMIDITY_HOLD, 25) # 湿度测量需要较长时间
        if raw_data is None:
            return None

        raw_value = int.from_bytes(raw_data, 'big') # 大端格式
        # 应用转换公式
        humidity = ((125.0 * raw_value) / 65536.0) - 6.0
        # 限制在 0-100 范围内
        return max(0.0, min(100.0, humidity))

    def temperature(self):
        """
        测量并返回温度 (°C)。
        注意：可以直接测量温度，或者读取上次湿度测量时的温度值。
               直接测量温度更准确，但读取上次的值更快。这里采用直接测量。
        返回: 浮点数类型的温度值，如果读取失败则返回 None。
        """
        # --- 方法1: 直接测量温度 ---
        raw_data = self._read_data(_CMD_MEASURE_TEMP_HOLD, 25) # 温度测量也需要时间
        if raw_data is None:
             return None
        raw_value = int.from_bytes(raw_data, 'big')

        # --- 方法2: 读取上次湿度测量时的温度 (更快，但可能不是当前温度) ---
        # try:
        #     self._i2c.writeto(self._address, bytes([_CMD_READ_TEMP_FROM_PREV_RH]))
        #     sleep_ms(10) # 短暂延时
        #     self._i2c.readfrom_into(self._address, self._buffer)
        #     raw_value = int.from_bytes(self._buffer[0:2], 'big')
        # except OSError as e:
        #     print(f"SI7021 I2C Error reading previous temp: {e}")
        #     return None

        # 应用转换公式
        temperature = ((175.72 * raw_value) / 65536.0) - 46.85
        return temperature

    def reset(self):
        """
        复位传感器。
        """
        try:
            self._i2c.writeto(self._address, bytes([_CMD_RESET]))
            sleep_ms(20) # 等待复位完成
            print("SI7021 reset.")
            return True
        except OSError as e:
            # print(f"SI7021 I2C Error resetting: {e}")
            return False

    # def read_id(self):
    #     """读取设备ID (可选)"""
    #     try:
    #         # 读取第一部分
    #         self._i2c.writeto(self._address, _CMD_READ_ID_1)
    #         sleep_ms(10)
    #         id1_data = bytearray(8) # 4 ID bytes + 4 CRC bytes?
    #         self._i2c.readfrom_into(self._address, id1_data)
    #         # 读取第二部分
    #         self._i2c.writeto(self._address, _CMD_READ_ID_2)
    #         sleep_ms(10)
    #         id2_data = bytearray(6) # 2 ID bytes + 4 CRC bytes?
    #         self._i2c.readfrom_into(self._address, id2_data)
    #         # TODO: 验证 CRC 并组合 ID
    #         print("ID1:", id1_data.hex())
    #         print("ID2:", id2_data.hex())
    #         # 简单的返回 SNA + SNB 部分 (前 4 + 前 2?)
    #         return id1_data[0:4] + id2_data[0:2]
    #     except OSError as e:
    #         print(f"SI7021 I2C Error reading ID: {e}")
    #         return None