import st7789 # 导入ST7789驱动库，用于颜色定义等
import time # 导入时间模块，用于时间相关的计算，例如Toast显示
try: # 尝试导入自定义字体模块
    import ubuntu_24 as default_font # 导入转换后的Ubuntu字体模块作为默认字体 # Keep font import for FONT_HEIGHT # 保留字体导入以获取字体高度
except ImportError: # 如果导入失败
    print("Error: Converted font module ('ubuntu_24.py') not found in gui_manager.") # 打印错误信息
    default_font = None # 字体设为None

# --- UI Layout and Style Constants ---
# --- UI布局和样式常量 ---
COLOR_BG = st7789.BLACK if st7789 else 0x0000 # 背景颜色（如果导入了st7789则使用其黑色，否则使用默认黑色）
COLOR_FG = st7789.WHITE if st7789 else 0xFFFF # 前景颜色（如果导入了st7789则使用其白色，否则使用默认白色）
COLOR_LABEL = st7789.CYAN if st7789 else 0x07FF # 标签文本颜色（青色）
COLOR_VALUE = st7789.WHITE if st7789 else 0xFFFF # 值文本颜色（白色）
COLOR_SEPARATOR = st7789.BLUE if st7789 else 0x001F # 分隔线颜色（蓝色）
COLOR_STATUS_OK = st7789.GREEN if st7789 else 0x07E0 # 状态正常颜色（绿色）
COLOR_STATUS_WARN = st7789.YELLOW if st7789 else 0xFFE0 # 状态警告颜色（黄色）
COLOR_STATUS_BAD = st7789.RED if st7789 else 0xF800 # 状态不良颜色（红色）
COLOR_MEM = st7789.GREEN if st7789 else 0x07E0 # 内存显示颜色（绿色）
COLOR_TITLE = st7789.YELLOW if st7789 else 0xFFE0 # 标题颜色（黄色）
COLOR_PAGE_INDICATOR = st7789.MAGENTA if st7789 else 0xF81F # 页面指示器颜色（洋红色）
COLOR_SHADOW = st7789.DARKGREY if hasattr(st7789, 'DARKGREY') else 0x4208 # Define shadow color # 阴影颜色（如果st7789有定义则使用，否则使用默认深灰色）

# --- NEW: Toast Colors ---
# --- 新增：Toast提示框颜色 ---
COLOR_TOAST_BG = st7789.DARKGREY if hasattr(st7789, 'DARKGREY') else 0x4208 # Toast背景颜色
COLOR_TOAST_FG = st7789.WHITE if st7789 else 0xFFFF # Toast前景文本颜色

PADDING = 5 # 元素内边距
FONT_HEIGHT = default_font.HEIGHT if default_font else 24 # 字体高度（如果字体导入成功则使用字体自身高度，否则默认24）
SHADOW_OFFSET_X = 2 # 阴影X轴偏移
SHADOW_OFFSET_Y = 2 # 阴影Y轴偏移
STATUS_BAR_HEIGHT = FONT_HEIGHT + PADDING # 状态栏高度 = 字体高度 + 内边距

# Page Indicator Position (Common to all pages)
# 页面指示器位置（所有页面通用）
# LCD_WIDTH will be passed or accessed via display object
# LCD_WIDTH将通过display对象传递或访问
# X_PAGE_INDICATOR = LCD_WIDTH - 45 # 页面指示器X坐标 (示例)
# Y_PAGE_INDICATOR = PADDING # 页面指示器Y坐标 (示例)

# -- Layout Page 0: Main Sensors --
# -- 页面0布局：主要传感器数据 --
Y_STATUS_LINE_P0 = PADDING # 页面0状态栏Y坐标
X_WIFI_STATUS_P0 = PADDING # 页面0 WiFi状态X坐标
X_BLE_STATUS_P0 = 80 # Adjusted to give more space if needed, e.g. 80 or 90 # 页面0 BLE状态X坐标（调整以留出更多空间，例如80或90）
# IP Label removed from status bar, moved to Page 1
# IP标签从状态栏移除，移至页面1
Y_SEPARATOR_1_P0 = Y_STATUS_LINE_P0 + STATUS_BAR_HEIGHT + SHADOW_OFFSET_Y + PADDING # Adjusted for shadow and status bar height # 页面0第一个分隔线Y坐标（根据阴影和状态栏高度调整）

# NEW: Layout for sensor data on PAGE_MAIN - one item per row for clarity
# 新增：页面0传感器数据布局 - 每行一个项目以提高清晰度
X_LABEL_P0 = PADDING + 5 # 页面0标签文本X坐标
X_VALUE_P0 = X_LABEL_P0 + 75 # Increased space for longer labels like "Noise:" # 页面0值文本X坐标（增加空间以适应更长的标签如"Noise:"）

ROW_SPACING_P0 = FONT_HEIGHT + PADDING + 15 # Generous spacing between rows (24 + 5 + 15 = 44) # 页面0行间距（较宽，24+5+15=44）
ITEM_ROW_SPACING_P1 = FONT_HEIGHT + PADDING + 15 # Spacing for items on Page 1, similar to P0 # 页面1项目行间距，与页面0类似

Y_TEMP_ROW_P0 = Y_SEPARATOR_1_P0 + PADDING + 10 # 页面0温度行Y坐标
Y_HUMI_ROW_P0 = Y_TEMP_ROW_P0 + ROW_SPACING_P0 # 页面0湿度行Y坐标
Y_LUX_ROW_P0 = Y_HUMI_ROW_P0 + ROW_SPACING_P0 # 页面0光照行Y坐标
Y_NOISE_RMS_ROW_P0 = Y_LUX_ROW_P0 + ROW_SPACING_P0 # 页面0噪声RMS行Y坐标
Y_NOISE_DB_ROW_P0 = Y_NOISE_RMS_ROW_P0 + ROW_SPACING_P0 # 页面0噪声dB行Y坐标

# OLD constants for Page 0 that are being replaced or removed:
# 页面0中被替换或移除的旧常量：
# X_TEMP_LABEL_P0 = PADDING # 旧温度标签X坐标
# X_TEMP_VALUE_P0 = 45 # 旧温度值X坐标
# X_HUM_LABEL_P0 = 120 # 旧湿度标签X坐标
# X_HUM_VALUE_P0 = 165 # 旧湿度值X坐标
# Y_SENSOR_ROW_1_P0 = Y_SEPARATOR_1_P0 + PADDING + 5 # 旧第一行传感器Y坐标
# Y_SENSOR_ROW_2_P0 = Y_SENSOR_ROW_1_P0 + FONT_HEIGHT + PADDING + 10 # 旧第二行传感器Y坐标
# X_LUX_LABEL_P0 = PADDING # 旧光照标签X坐标
# X_LUX_VALUE_P0 = 60 # 旧光照值X坐标
# X_NOISE_LABEL_P0 = 120 # 旧噪声标签X坐标
# X_NOISE_VALUE_P0 = 190 # 旧噪声值X坐标
# Y_SEPARATOR_2_P0 = Y_SENSOR_ROW_2_P0 + FONT_HEIGHT + PADDING + 5 # 旧第二个分隔线Y坐标
# Y_BOTTOM_ROW_1_P0 = Y_SEPARATOR_2_P0 + PADDING + 5 # 旧底部第一行Y坐标
# X_KEYS_LABEL_P0 = PADDING (Keys display removed to make space) # 旧按键标签X坐标（按键显示移除以节省空间）
# X_KEYS_VALUE_P0 = 70 # 旧按键值X坐标
# Y_BOTTOM_ROW_2_P0 = Y_BOTTOM_ROW_1_P0 + FONT_HEIGHT + PADDING (Memory display removed) # 旧底部第二行Y坐标（内存显示移除）
# X_MEM_LABEL_P0 = PADDING # 旧内存标签X坐标
# X_MEM_VALUE_P0 = 70 # 旧内存值X坐标
# Y_BOTTOM_ROW_3_P0 = Y_BOTTOM_ROW_2_P0 + FONT_HEIGHT + PADDING (dB display moved) # 旧底部第三行Y坐标（dB显示移动）
# X_DB_LABEL_P0 = PADDING # 旧dB标签X坐标
# X_DB_VALUE_P0 = 70 # 旧dB值X坐标


# -- Layout Page 1: Network Details --
# -- 页面1布局：网络详情 --
Y_TITLE_P1 = PADDING + 5 # 页面1标题Y坐标
X_TITLE_P1 = PADDING # 页面1标题X坐标
Y_WIFI_ICON_P1 = Y_TITLE_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing # 页面1 WiFi图标Y坐标（调整间距）
X_WIFI_ICON_P1 = PADDING # 页面1 WiFi图标X坐标
X_SSID_LABEL_P1 = X_WIFI_ICON_P1 + 30 # Keep X offset for label relative to icon # 页面1 SSID标签X坐标（相对于图标保持X偏移）
Y_SSID_P1 = Y_WIFI_ICON_P1 # SSID与图标共享Y坐标
X_SSID_VALUE_P1 = X_SSID_LABEL_P1 + 70 # 页面1 SSID值X坐标

Y_IP_P1 = Y_SSID_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing # 页面1 IP地址Y坐标（调整间距）
X_IP_LABEL_P1 = PADDING # 页面1 IP标签X坐标
X_IP_VALUE_P1 = X_IP_LABEL_P1 + 40 # 页面1 IP值X坐标

Y_MASK_P1 = Y_IP_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing # 页面1 子网掩码Y坐标（调整间距）
X_MASK_LABEL_P1 = X_IP_LABEL_P1 # 页面1 子网掩码标签X坐标
X_MASK_VALUE_P1 = X_IP_VALUE_P1 # 页面1 子网掩码值X坐标

Y_GW_P1 = Y_MASK_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing # 页面1 网关Y坐标（调整间距）
X_GW_LABEL_P1 = X_IP_LABEL_P1 # 页面1 网关标签X坐标
X_GW_VALUE_P1 = X_IP_VALUE_P1 # 页面1 网关值X坐标

# --- UI Page Configuration (can be referenced from main) ---
# --- UI页面配置（可在main中引用） ---
NUM_PAGES = 2 # Assuming this might be needed by GUIManager or main # 页面总数（假设GUIManager或main需要）
PAGE_MAIN = 0 # 主页面索引
PAGE_NETWORK = 1 # 网络页面索引

class GUIManager: # GUI管理器类
    def __init__(self, display, font): # 构造函数，初始化GUI管理器
        self.display = display # 存储显示对象
        self.font = font # 存储字体对象
        self.lcd_width = display.width # 获取LCD宽度
        self.lcd_height = display.height # 获取LCD高度

        # Page Indicator Position (Common to all pages)
        # 页面指示器位置（所有页面通用）
        self.x_page_indicator = self.lcd_width - 45 # 计算页面指示器X坐标
        self.y_page_indicator = PADDING # 计算页面指示器Y坐标
        
        # Previous UI string states
        # 上一次的UI文本状态，用于判断是否需要更新显示
        self.prev_wifi_status_str_p0 = None # 页面0上一次的WiFi状态文本
        self.prev_ble_status_str_p0 = None # 页面0上一次的BLE状态文本
        self.prev_temperature_str = None # 上一次的温度文本
        self.prev_humidity_str = None # 上一次的湿度文本
        self.prev_lux_str = None # 上一次的光照文本
        self.prev_noise_level_str = None # 上一次的噪声水平（RMS）文本
        # self.prev_pressed_key_names = None # This is directly calculated in main loop, not a text field typically # 上一次按下的按键名称（通常在main循环中直接计算，不是UI文本字段）
        self.prev_decibel_str = None # 上一次的噪声分贝文本
        
        self.prev_wifi_icon_str_p1 = None # 页面1上一次的WiFi图标文本
        self.prev_ssid_str_p1 = None # 页面1上一次的SSID文本
        self.prev_ip_str_p1 = None # 页面1上一次的IP地址文本
        self.prev_mask_str_p1 = None # 页面1上一次的子网掩码文本
        self.prev_gw_str_p1 = None # 页面1上一次的网关文本
        
        self.prev_page_indicator_str = None # 上一次的页面指示器文本

        # --- NEW: Toast specific variables ---
        # --- 新增：Toast提示框相关变量 ---
        self.toast_text = None # Toast提示框文本内容
        self.toast_start_time_ms = 0 # Toast显示开始时间（毫秒）
        self.toast_duration_ms = 0 # Toast显示持续时间（毫秒）
        self.toast_active = False # Toast是否激活标志
        self._toast_last_rect = None # Stores (x,y,w,h) of the last toast to clear it # 存储上一次Toast的矩形区域(x,y,宽,高)，用于清除旧的Toast

    def update_text_field(self, x, y, new_text, prev_text_attr_name, fg_color, bg_color): # 更新文本字段
        """Updates a text field only if the text has changed.
        prev_text_attr_name is the name of the attribute holding the previous text (e.g., 'prev_temperature_str').
        """ # 仅在文本内容发生变化时更新文本字段。
        # prev_text_attr_name是存储上一次文本的属性名称（例如，'prev_temperature_str'）。
        if not self.display or not self.font: # 如果显示对象或字体对象不存在
            return getattr(self, prev_text_attr_name) # 返回上一次的文本值，不进行更新
            
        prev_text = getattr(self, prev_text_attr_name) # 获取存储的上一次文本值

        if new_text != prev_text: # 如果新文本与上一次文本不同
            if prev_text is not None and prev_text != "": # 如果上一次文本有效且不为空
                try: # 尝试计算上一次文本的宽度并清除区域
                    if hasattr(self.display, 'write_width'): # 如果display对象有write_width方法（更准确）
                        prev_width = self.display.write_width(self.font, prev_text) # 使用write_width计算宽度
                    else: # 否则使用简陋估算
                        prev_width = len(prev_text) * (self.font.MAX_WIDTH if hasattr(self.font, 'MAX_WIDTH') else 15) # 估算宽度
                    self.display.fill_rect(x, y, prev_width + 2, FONT_HEIGHT, bg_color) # Clear slightly wider # 填充矩形区域清除旧文本（稍宽一点以确保清除干净）
                except Exception as e: # 捕获清除时的异常
                    print(f"Err clear '{prev_text}': {e}") # 打印清除错误信息
            try: # 尝试写入新文本
                self.display.write(self.font, new_text, x, y, fg_color, bg_color) # 写入新文本
            except Exception as e: # 捕获写入时的异常
                print(f"Err write '{new_text}': {e}") # 打印写入错误信息
                return prev_text # Return old text if write failed # 如果写入失败，返回旧文本
            
            setattr(self, prev_text_attr_name, new_text) # Update the stored previous text # 更新存储的上一次文本值为新文本
            return new_text # 返回新文本
        return prev_text # 如果文本没有变化，返回上一次文本

    def reset_prev_ui_strings(self): # 重置所有上一次的UI文本状态
        """Resets all previous UI string states to force redraw on page switch.""" # 重置所有上一次的UI文本状态，以在页面切换时强制重绘所有内容。
        print("Resetting previous UI strings for page switch.") # 打印重置信息
        # Page 0 # 页面0相关状态
        self.prev_wifi_status_str_p0 = None # 重置页面0 WiFi状态文本
        self.prev_ble_status_str_p0 = None # 重置页面0 BLE状态文本
        self.prev_temperature_str = None # 重置温度文本
        self.prev_humidity_str = None # 重置湿度文本
        self.prev_lux_str = None # 重置光照文本
        self.prev_noise_level_str = None # 重置噪声水平文本
        self.prev_decibel_str = None # 重置噪声分贝文本
        # Page 1 # 页面1相关状态
        self.prev_wifi_icon_str_p1 = None # 重置页面1 WiFi图标文本
        self.prev_ssid_str_p1 = None # 重置页面1 SSID文本
        self.prev_ip_str_p1 = None # 重置页面1 IP地址文本
        self.prev_mask_str_p1 = None # 重置页面1 子网掩码文本
        self.prev_gw_str_p1 = None # 重置页面1 网关文本
        # Common # 通用状态
        self.prev_page_indicator_str = None # 重置页面指示器文本

    def draw_page_layout(self, page_index): # 绘制页面布局
        """Draws the static layout elements for the given page.""" # 绘制给定页面的静态布局元素。
        if not self.display or not self.font: # 如果显示对象或字体对象不存在
            return # 不进行绘制
        print(f"Drawing layout for Page {page_index}...") # 打印正在绘制的页面信息
        self.display.fill(COLOR_BG) # 用背景颜色填充整个屏幕

        # Draw Page Indicator (Common to all pages)
        # 绘制页面指示器（所有页面通用）
        page_text = f"{page_index + 1}/{NUM_PAGES}" # 构建页面指示器文本，格式为 "当前页/总页数"
        self.display.write(self.font, page_text, self.x_page_indicator, self.y_page_indicator, COLOR_PAGE_INDICATOR, COLOR_BG) # 绘制页面指示器文本

        if page_index == PAGE_MAIN: # 如果是主页面（页面0）
            # Simplified shadow handling: Removed complex fill_rect calls for shadow.
            # 简化阴影处理：移除了复杂的fill_rect调用来绘制阴影。
            # Y_SEPARATOR_1_P0 now serves as the primary visual division below the status bar.
            # Y_SEPARATOR_1_P0现在作为状态栏下方的主要视觉分隔线。
            
            # Actual static labels and separators for Page 0
            # 页面0的实际静态标签和分隔线
            self.display.hline(0, Y_SEPARATOR_1_P0, self.lcd_width, COLOR_SEPARATOR) # 绘制状态栏下方的水平分隔线
            
            self.display.write(self.font, "Temp:", X_LABEL_P0, Y_TEMP_ROW_P0, COLOR_LABEL, COLOR_BG) # 绘制温度标签
            self.display.write(self.font, "Humi:", X_LABEL_P0, Y_HUMI_ROW_P0, COLOR_LABEL, COLOR_BG) # 绘制湿度标签
            self.display.write(self.font, "Lux:", X_LABEL_P0, Y_LUX_ROW_P0, COLOR_LABEL, COLOR_BG) # 绘制光照标签
            self.display.write(self.font, "Noise:", X_LABEL_P0, Y_NOISE_RMS_ROW_P0, COLOR_LABEL, COLOR_BG) # 绘制噪声标签
            self.display.write(self.font, "dB:", X_LABEL_P0, Y_NOISE_DB_ROW_P0, COLOR_LABEL, COLOR_BG) # 绘制dB标签

        elif page_index == PAGE_NETWORK: # 如果是网络页面（页面1）
            self.display.write(self.font, "Network Info", X_TITLE_P1, Y_TITLE_P1, COLOR_TITLE, COLOR_BG) # 绘制页面标题
            self.display.write(self.font, "NET", X_WIFI_ICON_P1, Y_WIFI_ICON_P1, COLOR_LABEL, COLOR_BG) # 绘制网络状态图标标签
            self.display.write(self.font, "SSID:", X_SSID_LABEL_P1, Y_SSID_P1, COLOR_LABEL, COLOR_BG) # 绘制SSID标签
            self.display.write(self.font, "IP:", X_IP_LABEL_P1, Y_IP_P1, COLOR_LABEL, COLOR_BG) # 绘制IP标签
            self.display.write(self.font, "Mask:", X_MASK_LABEL_P1, Y_MASK_P1, COLOR_LABEL, COLOR_BG) # 绘制子网掩码标签
            self.display.write(self.font, "GW:", X_GW_LABEL_P1, Y_GW_P1, COLOR_LABEL, COLOR_BG) # 绘制网关标签
        
        # Removed the stray 'if page_index == PAGE_MAIN:' block that was previously after the elif.
        # 移除了之前在elif之后的零散的'if page_index == PAGE_MAIN:'代码块。
        # The 'pass' for shadow simplification is also removed as the logic above is now cleaner.
        # 用于阴影简化的'pass'也已移除，因为上面的逻辑现在更清晰了。

        print(f"Layout drawn for Page {page_index}.") # 打印页面布局绘制完成信息

    # --- NEW: Toast Methods ---
    # --- 新增：Toast提示框方法 ---
    def set_toast(self, text, current_time_ms, duration_ms=2000): # 设置Toast提示框内容和持续时间
        """Activates a toast message.""" # 激活一个Toast提示消息。
        if not self.display or not self.font: # 如果显示对象或字体对象不存在
            return # 不设置Toast

        # If a toast was active, clear its last position first
        # 如果之前有Toast处于激活状态，先清除它上一次绘制的位置
        if self.toast_active and self._toast_last_rect: # 如果Toast激活且存储了上一次的矩形区域
            try: # 尝试清除旧的Toast区域
                self.display.fill_rect( # 填充矩形区域
                    self._toast_last_rect[0], self._toast_last_rect[1], # X坐标，Y坐标
                    self._toast_last_rect[2], self._toast_last_rect[3], # 宽度，高度
                    COLOR_BG # Fill with main background color # 使用主背景颜色填充
                ) # 清除旧的Toast区域
            except Exception as e: # 捕获清除时的异常
                print(f"Error clearing previous toast area: {e}") # 打印清除错误信息
        
        self.toast_text = text # 设置Toast文本内容
        self.toast_start_time_ms = current_time_ms # 记录Toast开始显示的时间
        self.toast_duration_ms = duration_ms # 设置Toast持续时间
        self.toast_active = True # 激活Toast标志
        self._toast_last_rect = None # Reset, will be set when drawn # 重置上一次的矩形区域，将在绘制时设置
        # The actual drawing will happen in draw_toast_if_active
        # 实际的绘制将在draw_toast_if_active方法中进行
        print(f"Toast set: '{text}' for {duration_ms}ms") # 打印Toast设置信息

    def draw_toast_if_active(self, current_time_ms): # 如果Toast激活则绘制，或在过期时清除
        """Draws the toast message if active, or clears it if expired.""" # 如果Toast处于激活状态则绘制，或者如果已过期则清除它。
        if not self.display or not self.font: # 如果显示对象或字体对象不存在
            self.toast_active = False # Cannot display # 无法显示，设为非激活
            return # 不进行绘制或清除

        if self.toast_active: # 如果Toast处于激活状态
            if time.ticks_diff(current_time_ms, self.toast_start_time_ms) > self.toast_duration_ms: # 如果当前时间超过了开始时间+持续时间（即Toast已过期）
                # Toast expired # Toast已过期
                self.toast_active = False # 设为非激活
                if self._toast_last_rect: # 如果存储了上一次的矩形区域
                    try: # 尝试清除Toast区域
                        # Clear the area where the toast was
                        # 清除Toast所在的区域
                        self.display.fill_rect( # 填充矩形区域
                            self._toast_last_rect[0], self._toast_last_rect[1],
                            self._toast_last_rect[2], self._toast_last_rect[3],
                            COLOR_BG # Fill with main background color # 使用主背景颜色填充
                        ) # 清除Toast区域
                        # print(f"Toast cleared: '{self.toast_text}'") # 打印Toast清除信息（可选）
                    except Exception as e: # 捕获清除时的异常
                        print(f"Error clearing expired toast area: {e}") # 打印清除错误信息
                    self._toast_last_rect = None # 重置上一次的矩形区域
                self.toast_text = None # 清除Toast文本内容
            else: # Toast仍然处于激活状态
                # Toast is active and needs to be drawn
                # Toast处于激活状态，需要绘制
                toast_padding = 5 # Toast内边距
                try: # 尝试计算文本宽度
                    if hasattr(self.display, 'write_width'): # 如果display对象有write_width方法
                        text_width = self.display.write_width(self.font, self.toast_text) # 使用write_width计算文本宽度
                    else: # 否则使用简陋估算
                        text_width = len(self.toast_text) * (self.font.MAX_WIDTH if hasattr(self.font, 'MAX_WIDTH') else 15) # 估算文本宽度
                except Exception: # 捕获计算宽度时的异常（例如字体未加载完全）
                    text_width = len(self.toast_text) * 12 # Estimate # 估算文本宽度（回退值）

                toast_height = FONT_HEIGHT + 2 * toast_padding # 计算Toast高度 = 字体高度 + 2 * 内边距
                toast_width = text_width + 2 * toast_padding # 计算Toast宽度 = 文本宽度 + 2 * 内边距

                # Position: Centered horizontally, near the bottom
                # 位置：水平居中，靠近底部
                toast_x = (self.lcd_width - toast_width) // 2 # 计算Toast的X坐标使其水平居中
                toast_y = self.lcd_height - toast_height - 10 # 10px from bottom # 计算Toast的Y坐标使其靠近底部（底部留10像素空间）

                # Ensure toast is within screen bounds (simple check)
                # 确保Toast在屏幕范围内（简单检查）
                if toast_x < 0: toast_x = 0 # 如果X坐标小于0，设为0
                if toast_y < 0: toast_y = 0 # 如果Y坐标小于0，设为0
                if toast_x + toast_width > self.lcd_width: # 如果Toast右边界超出屏幕
                    toast_width = self.lcd_width - toast_x # 调整Toast宽度
                if toast_y + toast_height > self.lcd_height: # 如果Toast下边界超出屏幕
                    toast_height = self.lcd_height - toast_y # 调整Toast高度
                
                # Store rect for clearing
                # 存储Toast的矩形区域，用于后续清除
                self._toast_last_rect = (toast_x, toast_y, toast_width, toast_height) # 存储当前Toast的矩形区域

                # Draw toast background
                # 绘制Toast背景
                self.display.fill_rect(toast_x, toast_y, toast_width, toast_height, COLOR_TOAST_BG) # 填充矩形区域绘制背景
                # Draw toast text
                # 绘制Toast文本
                text_x_pos = toast_x + toast_padding # 计算文本X坐标
                text_y_pos = toast_y + toast_padding # 计算文本Y坐标
                self.display.write(self.font, self.toast_text, text_x_pos, text_y_pos, COLOR_TOAST_FG, COLOR_TOAST_BG) # 绘制Toast文本
                # print(f"Toast drawn: '{self.toast_text}' at ({toast_x},{toast_y})") # 打印Toast绘制信息（可选） 