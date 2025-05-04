# audio_capture_for_analysis_cn.py
# Captures audio snippets for selected configurations and detects clipping.

import time
from machine import Pin, I2S
import struct
import gc
import os

# --- Configuration ---
# Pin definition
I2S_ID = 0
I2S_BCLK_PIN = 17
I2S_WS_PIN = 16
I2S_DIN_PIN = 15

# Configurations to capture (based on your selection)
# Format is MONO for all selected configurations
TARGET_CONFIGS = [
    {'name': '16k_16bM', 'rate': 16000, 'bits': 16, 'format': I2S.MONO}, # 最佳平衡
    {'name': '48k_32bM', 'rate': 48000, 'bits': 32, 'format': I2S.MONO}, # 最高质量
    {'name': '48k_16bM', 'rate': 48000, 'bits': 16, 'format': I2S.MONO}, # 次高质量
    {'name': '32k_16bM', 'rate': 32000, 'bits': 16, 'format': I2S.MONO}, # 次佳平衡 1
    {'name': '44k1_16bM','rate': 44100, 'bits': 16, 'format': I2S.MONO}, # 次佳平衡 2
]

# Capture duration per config (seconds)
CAPTURE_DURATION_S = 5 # Adjust as needed (5 seconds is a good start)

# I2S Read buffer size (bytes)
I2S_READ_CHUNK_SIZE = 1024 # Increased chunk size for efficiency

# Internal buffer size (ibuf) for I2S
INTERNAL_BUFFER_SIZE = 4096 * 2 # Maybe increase if sample rate is high

# Output directory (if using SD card, prefix with /sd/)
OUTPUT_DIR = "/" # Root directory of the filesystem

# --- Global Variables ---
sck_pin = Pin(I2S_BCLK_PIN)
ws_pin = Pin(I2S_WS_PIN)
sd_pin = Pin(I2S_DIN_PIN)
read_buf = bytearray(I2S_READ_CHUNK_SIZE)

# --- Main Loop ---
print("--- 音频采集与削波检测脚本 ---")
if OUTPUT_DIR != "/" and OUTPUT_DIR.endswith('/'):
     OUTPUT_DIR = OUTPUT_DIR[:-1]
if OUTPUT_DIR != "/" and OUTPUT_DIR != "":
    try:
        os.mkdir(OUTPUT_DIR)
        print(f"创建目录: {OUTPUT_DIR}")
    except OSError as e:
        if e.errno != 17: # 17 = EEXIST (File exists)
             print(f"无法创建目录 {OUTPUT_DIR}: {e}")
             # Decide whether to continue or stop
             # raise e # Uncomment to stop script if dir creation fails

for config in TARGET_CONFIGS:
    config_name = config['name']
    rate = config['rate']
    bits = config['bits']
    format_enum = config['format'] # Assuming MONO for all

    print(f"\n--- 开始处理配置: {config_name} (Rate={rate}, Bits={bits}) ---")

    if bits == 16:
        BYTES_PER_SAMPLE = 2
        UNPACK_CODE = 'h'
        SIGNED_MIN = -32768
        SIGNED_MAX = 32767
    elif bits == 32:
        BYTES_PER_SAMPLE = 4
        UNPACK_CODE = 'i'
        SIGNED_MIN = -2147483648
        SIGNED_MAX = 2147483647
        # Note: For INMP441 (24-bit data in 32-bit frame), actual max/min
        # are closer to +/- (2**23 - 1) << 8, but checking full 32-bit range
        # is a simpler indicator of potential clipping/overload.
    else:
        print(f"错误: 配置 {config_name} 的位深 {bits} 不支持。跳过。")
        continue

    # Ensure chunk size is multiple of sample size
    if I2S_READ_CHUNK_SIZE % BYTES_PER_SAMPLE != 0:
        print(f"错误: 读取块大小 {I2S_READ_CHUNK_SIZE} 不是样本大小 {BYTES_PER_SAMPLE} 的整数倍。跳过。")
        continue

    # Generate filename
    filename = f"{OUTPUT_DIR}/audio_{config_name}.raw"
    print(f"准备写入文件: {filename}")

    i2s_dev = None
    outfile = None
    init_success = False
    capture_success = False
    total_samples_processed = 0
    clipped_samples_count = 0

    try:
        # --- Initialize I2S ---
        print("正在初始化 I2S...")
        i2s_dev = I2S(I2S_ID,
                      sck=sck_pin, ws=ws_pin, sd=sd_pin,
                      mode=I2S.RX,
                      bits=bits,
                      format=format_enum,
                      rate=rate,
                      ibuf=INTERNAL_BUFFER_SIZE)
        print(f"I2S 初始化成功: {i2s_dev}")
        init_success = True

        # --- Open output file ---
        outfile = open(filename, 'wb')
        print(f"文件已打开，开始采集 {CAPTURE_DURATION_S} 秒...")

        start_time_ms = time.ticks_ms()
        total_bytes_written = 0

        # --- Capture Loop ---
        while time.ticks_diff(time.ticks_ms(), start_time_ms) < CAPTURE_DURATION_S * 1000:
            try:
                bytes_read = i2s_dev.readinto(read_buf)

                if bytes_read > 0:
                    # Write raw bytes to file
                    bytes_written = outfile.write(read_buf[:bytes_read])
                    if bytes_written != bytes_read:
                        print(f"警告: 文件写入字节数 ({bytes_written}) 与读取字节数 ({bytes_read}) 不匹配！")
                        # Maybe handle disk full error?
                    total_bytes_written += bytes_written

                    # Unpack data for clipping check
                    num_samples_in_buf = bytes_read // BYTES_PER_SAMPLE
                    # Use '<' for little-endian, adjust if your platform differs
                    format_string = '<' + UNPACK_CODE * num_samples_in_buf
                    try:
                        samples = struct.unpack(format_string, read_buf[:bytes_read])

                        # Check for clipping
                        for sample in samples:
                            if sample <= SIGNED_MIN or sample >= SIGNED_MAX:
                                clipped_samples_count += 1
                        total_samples_processed += num_samples_in_buf

                    except Exception as e_unpack:
                        print(f"解包错误: {e_unpack}")
                        # Continue capturing raw data if unpack fails?

                elif bytes_read < 0:
                    print(f"错误: I2S readinto 返回 {bytes_read}")
                    break # Stop capture for this config

            except Exception as e_read:
                print(f"I2S 读取错误: {e_read}")
                break # Stop capture for this config

        # End of capture loop
        capture_success = True
        print(f"采集完成。总共写入 {total_bytes_written} 字节。")

    except Exception as e_main:
        print(f"处理配置 {config_name} 时发生错误: {e_main}")
        import sys
        sys.print_exception(e_main)

    finally:
        # --- Cleanup ---
        if outfile:
            outfile.close()
            print(f"文件 {filename} 已关闭。")
        if i2s_dev:
            print("正在反初始化 I2S...")
            try:
                i2s_dev.deinit()
                print("I2S 已反初始化。")
            except Exception as deinit_e:
                print(f"反初始化 I2S 时出错: {deinit_e}")
        gc.collect()

        # --- Report Clipping ---
        if capture_success and total_samples_processed > 0:
            clipping_percentage = (clipped_samples_count / total_samples_processed) * 100
            print(f"削波检测: {clipped_samples_count} / {total_samples_processed} 个样本达到极值 ({clipping_percentage:.4f}%)")
            if clipping_percentage > 0.1: # Threshold for warning
                 print("警告: 检测到明显削波 (破音)，可能输入信号过强或增益设置不当！")
        elif init_success and not capture_success:
            print("削波检测: 未能成功完成采集，无法计算。")
        elif not init_success:
             print("削波检测: I2S 初始化失败，无法采集。")

print("\n--- 所有配置处理完毕 ---")
print("请将生成的 .raw 文件从 ESP32 传输到电脑进行进一步分析。")