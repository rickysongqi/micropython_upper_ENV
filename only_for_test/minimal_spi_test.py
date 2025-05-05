# minimal_spi_test.py
from machine import Pin, SPI
import time

# --- 配置 (与 main.py 一致) ---
LCD_SPI_ID = 2
LCD_SCLK_PIN = 12
LCD_MOSI_PIN = 11
LCD_MISO_PIN = -1
LCD_CS_PIN = 3  # 如果用到 CS
LCD_DC_PIN = 46
LCD_SPI_BAUDRATE = 40000000 # 或尝试降低的值

# --- 初始化 ---
print("Initializing Pins...")
pin_dc = Pin(LCD_DC_PIN, Pin.OUT)
pin_cs = Pin(LCD_CS_PIN, Pin.OUT) if LCD_CS_PIN is not None else None
if pin_cs: pin_cs.value(1) # Deactivate CS

print("Initializing SPI...")
spi = None
try:
    spi = SPI(LCD_SPI_ID, baudrate=LCD_SPI_BAUDRATE,
              sck=Pin(LCD_SCLK_PIN), mosi=Pin(LCD_MOSI_PIN),
              miso=Pin(LCD_MISO_PIN) if LCD_MISO_PIN != -1 else None)
    print("SPI Initialized OK.")
except Exception as e:
    print(f"SPI Init Failed: {e}")
    # sys.exit() # 在 MicroPython 中可能需要其他退出方式

# --- 模拟 _write(command=b'\x11', data=b'') ---
if spi:
    command = b'\x11'
    data = b'' # 或者 None
    data_len = len(data) if data is not None else 0

    print(f"\nAttempting problematic sequence: cmd={command.hex()}, data_len={data_len}")

    # 1. 发送命令
    print("Sending command...")
    if pin_cs: pin_cs.value(0)
    pin_dc.value(0) # Command mode
    try:
        spi.write(command)
        print("Command sent.")
    except Exception as e:
        print(f"EXCEPTION sending command: {e}")
    finally:
         # 通常 DC 在命令后、数据前切换，或者在 CS 拉高前
         # pin_dc.value(1)
         # if pin_cs: pin_cs.value(1) # 命令后不立即拉高 CS，因为可能有数据
         pass

    # 2. 尝试（或跳过）发送数据
    print(f"Checking condition to send data: data is not None? {data is not None}, data_len > 0? {data_len > 0}")
    if data is not None and data_len > 0:
         print("Condition PASSED - Attempting to send data...")
         pin_dc.value(1) # Data mode
         try:
              spi.write(data) # 这行不应该被执行
              print("Data sent (should not happen for len=0).")
         except Exception as e:
              print(f"EXCEPTION sending data: {e}") # 预期不会到这里，除非判断错误
         finally:
              if pin_cs: pin_cs.value(1) # 完成操作后拉高 CS
    else:
         print("Condition FAILED - Skipping data send.")
         # 即使跳过了数据发送，也要确保 CS 线最终被拉高
         if pin_cs: pin_cs.value(1)

    print("\nSequence finished.")

    # 尝试反初始化
    try:
        print("Deinitializing SPI...")
        spi.deinit()
        print("SPI Deinitialized.")
    except Exception as e:
        print(f"Error deinitializing SPI: {e}")

else:
    print("SPI not initialized, cannot run test sequence.")

print("Minimal test complete.")