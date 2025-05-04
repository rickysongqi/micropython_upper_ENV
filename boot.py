# boot.py
# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import webrepl
# 启动 WebREPL 服务，可以通过 http://micropython.org/webrepl/ 访问
# 连接 WiFi 后，可以通过设备的 IP 地址访问
webrepl.start()
# 如果需要挂载 SD 卡或其他文件系统，也可以在这里进行