# comprehensive_i2s_test_cn.py
# Tests various I2S configurations potentially supported by INMP441 on ESP32.

import time
from machine import Pin, I2S
import struct
import gc

# --- Test Control Parameters ---
# Duration for EACH configuration test (seconds)
TEST_DURATION_PER_CONFIG_S = 10
# Print status interval within each test (seconds)
PRINT_INTERVAL_S = 5
# Max detailed analyses per config (keep low to avoid excessive output)
MAX_DETAILED_ANALYSIS_PER_CONFIG = 2

# --- I2S Pin Configuration ---
I2S_ID = 0
I2S_BCLK_PIN = 17  # Clock line SCK
I2S_WS_PIN = 16    # Word select line WS
I2S_DIN_PIN = 15   # Data line SDIN

# --- Define Test Configurations ---
# Each dict defines a test case: rate (Hz), bits (16/32), format ('MONO'/'STEREO')
test_configs = [
    # --- Baseline & Varying Rate (16-bit MONO) ---
    {'rate': 16000, 'bits': 16, 'format': 'MONO'}, # Baseline (known good)
    {'rate': 8000,  'bits': 16, 'format': 'MONO'},
    {'rate': 32000, 'bits': 16, 'format': 'MONO'},
    {'rate': 44100, 'bits': 16, 'format': 'MONO'},
    {'rate': 48000, 'bits': 16, 'format': 'MONO'},

    # --- 32-bit MONO (Capturing full 24-bit data padded) ---
    {'rate': 16000, 'bits': 32, 'format': 'MONO'},
    {'rate': 48000, 'bits': 32, 'format': 'MONO'},

    # --- STEREO Tests (Requires careful checking of L/R pin on mic) ---
    # Assumes ESP32 reads both slots, one contains mic data, other zeros/noise
    {'rate': 16000, 'bits': 16, 'format': 'STEREO'},
    {'rate': 48000, 'bits': 16, 'format': 'STEREO'},
    {'rate': 16000, 'bits': 32, 'format': 'STEREO'},
    {'rate': 48000, 'bits': 32, 'format': 'STEREO'},
]

# --- Global Variables ---
sck_pin = Pin(I2S_BCLK_PIN)
ws_pin = Pin(I2S_WS_PIN)
sd_pin = Pin(I2S_DIN_PIN)
read_buf = None # Will be allocated based on chunk size

# --- Helper Function to Run One Test Configuration ---
def run_test_config(config):
    global read_buf

    print("\n" + "="*60)
    print(f"--- Testing Config: Rate={config['rate']}Hz, Bits={config['bits']}, Format={config['format']} ---")
    print("="*60)

    # --- Derive parameters from config ---
    I2S_SAMPLE_RATE = config['rate']
    I2S_BITS = config['bits']
    I2S_FORMAT_STR = config['format']

    if I2S_FORMAT_STR == 'MONO':
        try:
            I2S_FORMAT_ENUM = I2S.MONO
        except AttributeError:
            print("提示：固件中未定义 I2S.MONO，使用 0 代替。")
            I2S_FORMAT_ENUM = 0
    elif I2S_FORMAT_STR == 'STEREO':
        try:
            I2S_FORMAT_ENUM = I2S.STEREO
        except AttributeError:
            print("提示：固件中未定义 I2S.STEREO，使用 1 代替 (可能需要根据你的固件调整为 2)。")
            I2S_FORMAT_ENUM = 1 # Common value, might need to be 2 for some firmware
    else:
        print(f"错误: 未知的格式 '{I2S_FORMAT_STR}'")
        return False

    if I2S_BITS == 16:
        BYTES_PER_SAMPLE = 2
        UNPACK_CODE = 'h' # signed short
    elif I2S_BITS == 32:
        BYTES_PER_SAMPLE = 4
        UNPACK_CODE = 'i' # signed int
    else:
        print(f"错误: 不支持的位深 {I2S_BITS}")
        return False

    UNPACK_FORMAT_LE = '<' + UNPACK_CODE
    UNPACK_FORMAT_BE = '>' + UNPACK_CODE

    # Adjust buffer size if needed, keep it reasonable
    # Let's stick to 512 bytes read chunk for simplicity across tests
    I2S_READ_CHUNK_SIZE = 512
    # Allocate read buffer if not already done or if size changes (though it doesn't here)
    if read_buf is None or len(read_buf) != I2S_READ_CHUNK_SIZE:
        read_buf = bytearray(I2S_READ_CHUNK_SIZE)

    # Calculate expected samples based on receiver format
    if I2S_FORMAT_STR == 'MONO':
        EXPECTED_SAMPLES_PER_CHUNK = I2S_READ_CHUNK_SIZE // BYTES_PER_SAMPLE
        SAMPLES_PER_FRAME = 1
    else: # STEREO
        # Chunk contains interleaved L/R samples
        EXPECTED_SAMPLES_PER_CHUNK = I2S_READ_CHUNK_SIZE // BYTES_PER_SAMPLE
        if EXPECTED_SAMPLES_PER_CHUNK % 2 != 0:
             print(f"警告: 读取块大小 {I2S_READ_CHUNK_SIZE} 不能被立体声样本大小 {BYTES_PER_SAMPLE*2} 整除!")
        SAMPLES_PER_FRAME = 2


    # --- Statistics for this config ---
    start_time_ms = 0
    last_print_time_ms = 0
    total_loops = 0
    successful_reads = 0
    non_zero_buffers_found = 0
    detailed_analysis_count = 0
    # Reset stats for each config
    unpack_success_stats = {
        'first_le': 0, 'first_be': 0, 'first_pair_le': 0, 'first_pair_be': 0,
        'near_end_le': 0, 'near_end_be': 0,
        'small_chunk_le': 0, 'small_chunk_be': 0, 'small_chunk_stereo_le': 0, 'small_chunk_stereo_be': 0,
        'full_le': 0, 'full_be': 0, 'full_stereo_le': 0, 'full_stereo_be': 0
    }
    unpack_error_stats = {'total': 0, 'bad_typecode': 0, 'other': 0}

    i2s_dev = None
    init_success = False
    try:
        # --- Initialize I2S ---
        print(f"正在初始化 I2S (Rate={I2S_SAMPLE_RATE}, Bits={I2S_BITS}, Format={I2S_FORMAT_STR})...")
        # Set reasonable buffer size, e.g., 4096. Adjust if memory constrained.
        internal_buffer_size = 4096
        i2s_dev = I2S(I2S_ID,
                      sck=sck_pin, ws=ws_pin, sd=sd_pin,
                      mode=I2S.RX,
                      bits=I2S_BITS,
                      format=I2S_FORMAT_ENUM,
                      rate=I2S_SAMPLE_RATE,
                      ibuf=internal_buffer_size)
        print(f"I2S 初始化成功: {i2s_dev}")
        init_success = True

        # --- Test Loop for this config ---
        print(f"\n开始测试循环，持续 {TEST_DURATION_PER_CONFIG_S} 秒...")
        start_time_ms = time.ticks_ms()
        last_print_time_ms = start_time_ms

        while time.ticks_diff(time.ticks_ms(), start_time_ms) < TEST_DURATION_PER_CONFIG_S * 1000:
            total_loops += 1
            bytes_read = -1
            try:
                bytes_read = i2s_dev.readinto(read_buf)

                if bytes_read == I2S_READ_CHUNK_SIZE:
                    successful_reads += 1
                    # Check if buffer is all zeros BEFORE detailed analysis
                    is_all_zeros = all(b == 0 for b in read_buf[:bytes_read])

                    if not is_all_zeros:
                        non_zero_buffers_found += 1

                        # --- Detailed Analysis (Limited Times) ---
                        if detailed_analysis_count < MAX_DETAILED_ANALYSIS_PER_CONFIG:
                            detailed_analysis_count += 1
                            print(f"\n--- 第 {detailed_analysis_count} 次发现非零数据 (循环 {total_loops}) ---")
                            print("原始数据片段 (Hex):")
                            print(f"  开头 (0-31):   {read_buf[:min(32, bytes_read)].hex()}")
                            mid_start = max(0, bytes_read // 2 - 16)
                            print(f"  中间 ({mid_start}-{mid_start+31}): {read_buf[mid_start:min(bytes_read, mid_start + 32)].hex()}")
                            print(f"  结尾 ({max(0, bytes_read-32)}-{bytes_read-1}): {read_buf[max(0, bytes_read-32):bytes_read].hex()}")

                            print("解包测试:")
                            # --- MONO Unpacking ---
                            if I2S_FORMAT_STR == 'MONO':
                                # -- First sample --
                                try:
                                    val = struct.unpack(UNPACK_FORMAT_LE, read_buf[0:BYTES_PER_SAMPLE])[0]
                                    print(f"  - First ({UNPACK_FORMAT_LE}): OK, Val={val}", end=" | ")
                                    unpack_success_stats['first_le'] += 1
                                except Exception as e: print(f"  - First ({UNPACK_FORMAT_LE}): FAIL ({e})", end=" | ")
                                try:
                                    val = struct.unpack(UNPACK_FORMAT_BE, read_buf[0:BYTES_PER_SAMPLE])[0]
                                    print(f"First ({UNPACK_FORMAT_BE}): OK, Val={val}")
                                    unpack_success_stats['first_be'] += 1
                                except Exception as e: print(f"First ({UNPACK_FORMAT_BE}): FAIL ({e})")

                                # -- Near start samples -- (Indices 28, 30)
                                # ... (Can add this back if needed, similar logic to original script)

                                # -- Small chunk --
                                chunk_len = 20
                                num_samples_in_chunk = chunk_len // BYTES_PER_SAMPLE
                                chunk_fmt_le = '<' + UNPACK_CODE * num_samples_in_chunk
                                chunk_fmt_be = '>' + UNPACK_CODE * num_samples_in_chunk
                                if bytes_read >= chunk_len:
                                    try:
                                        vals = struct.unpack(chunk_fmt_le, read_buf[0:chunk_len])
                                        print(f"  - Chunk ({chunk_len}B, {UNPACK_FORMAT_LE}): OK", end=" | ")
                                        unpack_success_stats['small_chunk_le'] += 1
                                    except Exception as e: print(f"  - Chunk ({chunk_len}B, {UNPACK_FORMAT_LE}): FAIL ({e})", end=" | ")
                                    try:
                                        vals = struct.unpack(chunk_fmt_be, read_buf[0:chunk_len])
                                        print(f"Chunk ({chunk_len}B, {UNPACK_FORMAT_BE}): OK")
                                        unpack_success_stats['small_chunk_be'] += 1
                                    except Exception as e: print(f"Chunk ({chunk_len}B, {UNPACK_FORMAT_BE}): FAIL ({e})")
                                else: print("  - (Skip Chunk Test: Not enough bytes)")

                                # -- Full buffer --
                                full_fmt_le = '<' + UNPACK_CODE * EXPECTED_SAMPLES_PER_CHUNK
                                full_fmt_be = '>' + UNPACK_CODE * EXPECTED_SAMPLES_PER_CHUNK
                                try:
                                    vals = struct.unpack(full_fmt_le, read_buf[:bytes_read])
                                    print(f"  - Full ({UNPACK_FORMAT_LE}*N): OK!")
                                    unpack_success_stats['full_le'] += 1
                                except Exception as e:
                                    print(f"  - Full ({UNPACK_FORMAT_LE}*N): FAIL! ({e})")
                                    unpack_error_stats['total'] += 1
                                    if 'bad typecode' in str(e): unpack_error_stats['bad_typecode'] += 1
                                    else: unpack_error_stats['other'] += 1
                                try:
                                    vals = struct.unpack(full_fmt_be, read_buf[:bytes_read])
                                    print(f"  - Full ({UNPACK_FORMAT_BE}*N): OK!")
                                    unpack_success_stats['full_be'] += 1
                                except Exception as e:
                                    print(f"  - Full ({UNPACK_FORMAT_BE}*N): FAIL! ({e})")
                                    unpack_error_stats['total'] += 1
                                    if 'bad typecode' in str(e): unpack_error_stats['bad_typecode'] += 1
                                    else: unpack_error_stats['other'] += 1

                            # --- STEREO Unpacking (Simplified) ---
                            elif I2S_FORMAT_STR == 'STEREO':
                                pair_bytes = BYTES_PER_SAMPLE * 2
                                # -- First L/R pair --
                                if bytes_read >= pair_bytes:
                                    pair_fmt_le = '<' + UNPACK_CODE * 2
                                    pair_fmt_be = '>' + UNPACK_CODE * 2
                                    try:
                                        l_val, r_val = struct.unpack(pair_fmt_le, read_buf[0:pair_bytes])
                                        print(f"  - First Pair ({pair_fmt_le}): OK, L={l_val}, R={r_val}", end=" | ")
                                        unpack_success_stats['first_pair_le'] += 1
                                    except Exception as e: print(f"  - First Pair ({pair_fmt_le}): FAIL ({e})", end=" | ")
                                    try:
                                        l_val, r_val = struct.unpack(pair_fmt_be, read_buf[0:pair_bytes])
                                        print(f"First Pair ({pair_fmt_be}): OK, L={l_val}, R={r_val}")
                                        unpack_success_stats['first_pair_be'] += 1
                                    except Exception as e: print(f"First Pair ({pair_fmt_be}): FAIL ({e})")
                                else: print("  - (Skip First Pair Test: Not enough bytes)")

                                # -- Small chunk (Interleaved) --
                                chunk_len = 20 # Must be multiple of pair_bytes
                                if chunk_len % pair_bytes != 0: chunk_len -= (chunk_len % pair_bytes)
                                num_pairs_in_chunk = chunk_len // pair_bytes
                                chunk_fmt_stereo_le = '<' + (UNPACK_CODE * 2) * num_pairs_in_chunk
                                chunk_fmt_stereo_be = '>' + (UNPACK_CODE * 2) * num_pairs_in_chunk
                                if bytes_read >= chunk_len and chunk_len > 0:
                                     try:
                                        vals = struct.unpack(chunk_fmt_stereo_le, read_buf[0:chunk_len])
                                        print(f"  - Chunk ({chunk_len}B, Stereo {UNPACK_FORMAT_LE}): OK", end=" | ")
                                        unpack_success_stats['small_chunk_stereo_le'] += 1
                                     except Exception as e: print(f"  - Chunk ({chunk_len}B, Stereo {UNPACK_FORMAT_LE}): FAIL ({e})", end=" | ")
                                     try:
                                        vals = struct.unpack(chunk_fmt_stereo_be, read_buf[0:chunk_len])
                                        print(f"Chunk ({chunk_len}B, Stereo {UNPACK_FORMAT_BE}): OK")
                                        unpack_success_stats['small_chunk_stereo_be'] += 1
                                     except Exception as e: print(f"Chunk ({chunk_len}B, Stereo {UNPACK_FORMAT_BE}): FAIL ({e})")
                                else: print(f"  - (Skip Stereo Chunk Test: Not enough bytes or invalid chunk_len {chunk_len})")


                                # -- Full buffer (Interleaved) --
                                num_pairs_in_buffer = EXPECTED_SAMPLES_PER_CHUNK // 2
                                full_fmt_stereo_le = '<' + (UNPACK_CODE * 2) * num_pairs_in_buffer
                                full_fmt_stereo_be = '>' + (UNPACK_CODE * 2) * num_pairs_in_buffer
                                try:
                                    vals = struct.unpack(full_fmt_stereo_le, read_buf[:bytes_read])
                                    print(f"  - Full (Stereo {UNPACK_FORMAT_LE}*N): OK!")
                                    unpack_success_stats['full_stereo_le'] += 1
                                    # Optional: Analyze vals to check if one channel is mostly zero
                                    # left_channel = vals[0::2]
                                    # right_channel = vals[1::2]
                                    # print(f"    L Avg: {sum(left_channel)/len(left_channel):.1f}, R Avg: {sum(right_channel)/len(right_channel):.1f}")
                                except Exception as e:
                                    print(f"  - Full (Stereo {UNPACK_FORMAT_LE}*N): FAIL! ({e})")
                                    unpack_error_stats['total'] += 1
                                    if 'bad typecode' in str(e): unpack_error_stats['bad_typecode'] += 1
                                    else: unpack_error_stats['other'] += 1
                                try:
                                    vals = struct.unpack(full_fmt_stereo_be, read_buf[:bytes_read])
                                    print(f"  - Full (Stereo {UNPACK_FORMAT_BE}*N): OK!")
                                    unpack_success_stats['full_stereo_be'] += 1
                                except Exception as e:
                                    print(f"  - Full (Stereo {UNPACK_FORMAT_BE}*N): FAIL! ({e})")
                                    unpack_error_stats['total'] += 1
                                    if 'bad typecode' in str(e): unpack_error_stats['bad_typecode'] += 1
                                    else: unpack_error_stats['other'] += 1

                elif bytes_read == 0:
                    pass # Ignore zero-byte reads for now
                elif 0 < bytes_read < I2S_READ_CHUNK_SIZE:
                    print(f"警告: 循环 {total_loops} 读取到部分数据 ({bytes_read} 字节)")
                else: # bytes_read < 0
                    print(f"错误: 循环 {total_loops} readinto 返回: {bytes_read}")
                    break # Exit loop for this config on error

            except Exception as e_read:
                print(f"严重错误: 循环 {total_loops} 读取/处理时发生异常: {e_read}")
                import sys
                sys.print_exception(e_read)
                break # Exit loop for this config

            # --- Periodic Status Print ---
            current_time_ms = time.ticks_ms()
            if time.ticks_diff(current_time_ms, last_print_time_ms) >= PRINT_INTERVAL_S * 1000:
                elapsed_s = time.ticks_diff(current_time_ms, start_time_ms) / 1000
                print(f"--- 状态 @ {elapsed_s:.1f}s ---")
                print(f"  循环: {total_loops}, 成功读取: {successful_reads}, 非零缓冲: {non_zero_buffers_found}")
                print(f"  解包总错误: {unpack_error_stats['total']} ('bad typecode': {unpack_error_stats['bad_typecode']}, 其他: {unpack_error_stats['other']})")
                print(f"  内存剩余: {gc.mem_free()} bytes")
                last_print_time_ms = current_time_ms
                gc.collect()

            # time.sleep_ms(1) # Optional short delay

    except Exception as e_main:
        print(f"\n--- 配置测试期间发生严重错误 ---")
        import sys
        sys.print_exception(e_main)
        if "ESP_ERR_NO_MEM" in str(e_main):
             print(">>> 内存不足错误！尝试减小 ibuf 或固件问题。")
        elif "ESP_ERR_INVALID_ARG" in str(e_main):
             print(">>> 无效参数错误！此配置可能不被硬件/固件支持。")

    finally:
        # --- Deinitialize I2S ---
        if i2s_dev:
            print("\n正在反初始化 I2S...")
            try:
                i2s_dev.deinit()
                print("I2S 已反初始化。")
            except Exception as deinit_e:
                print(f"反初始化 I2S 时出错: {deinit_e}")
        gc.collect()

        # --- Print Stats for this Config ---
        print("\n--- 当前配置的最终统计 ---")
        print(f"配置: Rate={config['rate']}Hz, Bits={config['bits']}, Format={config['format']}")
        print(f"测试时长: ~{TEST_DURATION_PER_CONFIG_S} 秒")
        print(f"总循环: {total_loops}, 成功读取: {successful_reads}, 非零缓冲: {non_zero_buffers_found}")
        print(f"详细分析的非零缓冲数量: {detailed_analysis_count}")

        print("解包成功统计 (基于详细分析):")
        if config['format'] == 'MONO':
            print(f"  - First ({UNPACK_FORMAT_LE}/{UNPACK_FORMAT_BE}): {unpack_success_stats['first_le']} / {unpack_success_stats['first_be']}")
            print(f"  - Chunk ({UNPACK_FORMAT_LE}/{UNPACK_FORMAT_BE}): {unpack_success_stats['small_chunk_le']} / {unpack_success_stats['small_chunk_be']}")
            print(f"  - Full ({UNPACK_FORMAT_LE}/{UNPACK_FORMAT_BE}):  {unpack_success_stats['full_le']} / {unpack_success_stats['full_be']}")
        else: # STEREO
            print(f"  - First Pair ({UNPACK_FORMAT_LE}/{UNPACK_FORMAT_BE}): {unpack_success_stats['first_pair_le']} / {unpack_success_stats['first_pair_be']}")
            print(f"  - Chunk ({UNPACK_FORMAT_LE}/{UNPACK_FORMAT_BE}): {unpack_success_stats['small_chunk_stereo_le']} / {unpack_success_stats['small_chunk_stereo_be']}")
            print(f"  - Full ({UNPACK_FORMAT_LE}/{UNPACK_FORMAT_BE}):  {unpack_success_stats['full_stereo_le']} / {unpack_success_stats['full_stereo_be']}")

        print("解包失败统计 (整个缓冲):")
        print(f"  - 总失败次数: {unpack_error_stats['total']}")
        print(f"  - 'bad typecode' 错误: {unpack_error_stats['bad_typecode']}")
        print(f"  - 其他错误: {unpack_error_stats['other']}")

        # Simple conclusion for this config
        if not init_success:
            print("结论: I2S 初始化失败。此配置可能不受支持。")
        elif successful_reads == 0 and total_loops > 0:
             print("结论: 未能成功读取任何数据。")
        elif non_zero_buffers_found == 0 and successful_reads > 0:
             print("结论: 成功读取数据，但所有缓冲区均为零。检查麦克风连接或活动。")
        elif unpack_error_stats['total'] > 0:
             print("结论: 读取到非零数据，但解包时遇到错误。检查数据格式或固件解包功能。")
        elif (config['format'] == 'MONO' and (unpack_success_stats['full_le'] > 0 or unpack_success_stats['full_be'] > 0)) or \
             (config['format'] == 'STEREO' and (unpack_success_stats['full_stereo_le'] > 0 or unpack_success_stats['full_stereo_be'] > 0)):
             print("结论: 成功读取并解包了非零数据！此配置似乎有效。")
        else:
             print("结论: 读取到非零数据，但未能成功解包整个缓冲区（在详细分析样本中）。")

        return init_success and successful_reads > 0 # Indicate basic success

# --- Main Execution ---
print("--- I2S 全面配置测试脚本 ---")
print(f"引脚: BCLK={I2S_BCLK_PIN}, WS={I2S_WS_PIN}, DIN={I2S_DIN_PIN}")
print(f"将测试 {len(test_configs)} 种配置, 每种持续约 {TEST_DURATION_PER_CONFIG_S} 秒...")

successful_configs = []
failed_configs = []

for i, cfg in enumerate(test_configs):
    print(f"\n>>> 开始测试配置 {i+1} / {len(test_configs)}")
    if run_test_config(cfg):
        successful_configs.append(cfg)
    else:
        failed_configs.append(cfg)
    time.sleep(2) # Pause briefly between tests

print("\n" + "#"*60)
print("--- 所有测试完成 ---")
print("#"*60)

print(f"\n成功完成基本读写的配置 ({len(successful_configs)}):")
for cfg in successful_configs:
    print(f"  - Rate={cfg['rate']}, Bits={cfg['bits']}, Format={cfg['format']}")

print(f"\n未能初始化或读取数据的配置 ({len(failed_configs)}):")
for cfg in failed_configs:
    print(f"  - Rate={cfg['rate']}, Bits={cfg['bits']}, Format={cfg['format']}")

print("\n请仔细检查上面每个配置的详细日志和结论。")
print("脚本结束。")