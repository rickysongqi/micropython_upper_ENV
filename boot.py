# boot.py
# This file is executed on every boot (including wake-boot from deepsleep)
import network
import time
#import esp
#esp.osdebug(None)
# import webrepl # <<< 移除或注释掉

# # 尝试检查WiFi是否已连接，如果已连接则启动WebREPL # <<< 移除或注释掉
# # 这依赖于之前的状态，或者main.py会再次尝试连接 # <<< 移除或注释掉
# sta_if = network.WLAN(network.STA_IF) # <<< 移除或注释掉 (如果不再需要)
# if sta_if.isconnected(): # <<< 移除或注释掉
#     print("WiFi is already connected. Starting WebREPL...") # <<< 移除或注释掉
#     try: # <<< 移除或注释掉
#         webrepl.start() # <<< 移除或注释掉
#         print("WebREPL started successfully.") # <<< 移除或注释掉
#     except Exception as e: # <<< 移除或注释掉
#         print(f"Error starting WebREPL: {e}") # <<< 移除或注释掉
# else: # <<< 移除或注释掉
#     print("WiFi not connected in boot.py. WebREPL not started here.") # <<< 移除或注释掉
# # main.py 应该会尝试连接WiFi # <<< 移除或注释掉

# 如果需要挂载 SD 卡或其他文件系统，也可以在这里进行
# (保留 network 和 time 可能仍有用，例如需要检查时间)
# 如果确定 boot.py 不再需要 network/time，也可以移除它们
print("boot.py executed.") # 可以加一句打印确认boot.py执行了