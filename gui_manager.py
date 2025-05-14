import st7789 # Assuming st7789 might be needed for color definitions directly
import time # Needed for time.ticks_ms() in set_toast if used there, or pass current_time_ms
try:
    import ubuntu_24 as default_font # Keep font import for FONT_HEIGHT
except ImportError:
    print("Error: Converted font module ('ubuntu_24.py') not found in gui_manager.")
    default_font = None

# --- UI Layout and Style Constants ---
COLOR_BG = st7789.BLACK if st7789 else 0x0000
COLOR_FG = st7789.WHITE if st7789 else 0xFFFF
COLOR_LABEL = st7789.CYAN if st7789 else 0x07FF
COLOR_VALUE = st7789.WHITE if st7789 else 0xFFFF
COLOR_SEPARATOR = st7789.BLUE if st7789 else 0x001F
COLOR_STATUS_OK = st7789.GREEN if st7789 else 0x07E0
COLOR_STATUS_WARN = st7789.YELLOW if st7789 else 0xFFE0
COLOR_STATUS_BAD = st7789.RED if st7789 else 0xF800
COLOR_MEM = st7789.GREEN if st7789 else 0x07E0
COLOR_TITLE = st7789.YELLOW if st7789 else 0xFFE0
COLOR_PAGE_INDICATOR = st7789.MAGENTA if st7789 else 0xF81F
COLOR_SHADOW = st7789.DARKGREY if hasattr(st7789, 'DARKGREY') else 0x4208 # Define shadow color

# --- NEW: Toast Colors ---
COLOR_TOAST_BG = st7789.DARKGREY if hasattr(st7789, 'DARKGREY') else 0x4208
COLOR_TOAST_FG = st7789.WHITE if st7789 else 0xFFFF

PADDING = 5
FONT_HEIGHT = default_font.HEIGHT if default_font else 24
SHADOW_OFFSET_X = 2
SHADOW_OFFSET_Y = 2
STATUS_BAR_HEIGHT = FONT_HEIGHT + PADDING

# Page Indicator Position (Common to all pages)
# LCD_WIDTH will be passed or accessed via display object
# X_PAGE_INDICATOR = LCD_WIDTH - 45
# Y_PAGE_INDICATOR = PADDING

# -- Layout Page 0: Main Sensors --
Y_STATUS_LINE_P0 = PADDING
X_WIFI_STATUS_P0 = PADDING
X_BLE_STATUS_P0 = 80 # Adjusted to give more space if needed, e.g. 80 or 90
# IP Label removed from status bar, moved to Page 1
Y_SEPARATOR_1_P0 = Y_STATUS_LINE_P0 + STATUS_BAR_HEIGHT + SHADOW_OFFSET_Y + PADDING # Adjusted for shadow and status bar height

# NEW: Layout for sensor data on PAGE_MAIN - one item per row for clarity
X_LABEL_P0 = PADDING + 5
X_VALUE_P0 = X_LABEL_P0 + 75 # Increased space for longer labels like "Noise:"

ROW_SPACING_P0 = FONT_HEIGHT + PADDING + 15 # Generous spacing between rows (24 + 5 + 15 = 44)
ITEM_ROW_SPACING_P1 = FONT_HEIGHT + PADDING + 15 # Spacing for items on Page 1, similar to P0

Y_TEMP_ROW_P0 = Y_SEPARATOR_1_P0 + PADDING + 10
Y_HUMI_ROW_P0 = Y_TEMP_ROW_P0 + ROW_SPACING_P0
Y_LUX_ROW_P0 = Y_HUMI_ROW_P0 + ROW_SPACING_P0
Y_NOISE_RMS_ROW_P0 = Y_LUX_ROW_P0 + ROW_SPACING_P0
Y_NOISE_DB_ROW_P0 = Y_NOISE_RMS_ROW_P0 + ROW_SPACING_P0

# OLD constants for Page 0 that are being replaced or removed:
# X_TEMP_LABEL_P0 = PADDING
# X_TEMP_VALUE_P0 = 45
# X_HUM_LABEL_P0 = 120
# X_HUM_VALUE_P0 = 165
# Y_SENSOR_ROW_1_P0 = Y_SEPARATOR_1_P0 + PADDING + 5
# Y_SENSOR_ROW_2_P0 = Y_SENSOR_ROW_1_P0 + FONT_HEIGHT + PADDING + 10
# X_LUX_LABEL_P0 = PADDING
# X_LUX_VALUE_P0 = 60
# X_NOISE_LABEL_P0 = 120
# X_NOISE_VALUE_P0 = 190
# Y_SEPARATOR_2_P0 = Y_SENSOR_ROW_2_P0 + FONT_HEIGHT + PADDING + 5
# Y_BOTTOM_ROW_1_P0 = Y_SEPARATOR_2_P0 + PADDING + 5
# X_KEYS_LABEL_P0 = PADDING (Keys display removed to make space)
# X_KEYS_VALUE_P0 = 70
# Y_BOTTOM_ROW_2_P0 = Y_BOTTOM_ROW_1_P0 + FONT_HEIGHT + PADDING (Memory display removed)
# X_MEM_LABEL_P0 = PADDING
# X_MEM_VALUE_P0 = 70
# Y_BOTTOM_ROW_3_P0 = Y_BOTTOM_ROW_2_P0 + FONT_HEIGHT + PADDING (dB display moved)
# X_DB_LABEL_P0 = PADDING
# X_DB_VALUE_P0 = 70


# -- Layout Page 1: Network Details --
Y_TITLE_P1 = PADDING + 5
X_TITLE_P1 = PADDING
Y_WIFI_ICON_P1 = Y_TITLE_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing
X_WIFI_ICON_P1 = PADDING
X_SSID_LABEL_P1 = X_WIFI_ICON_P1 + 30 # Keep X offset for label relative to icon
Y_SSID_P1 = Y_WIFI_ICON_P1 # SSID shares Y with icon
X_SSID_VALUE_P1 = X_SSID_LABEL_P1 + 70

Y_IP_P1 = Y_SSID_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing
X_IP_LABEL_P1 = PADDING
X_IP_VALUE_P1 = X_IP_LABEL_P1 + 40

Y_MASK_P1 = Y_IP_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing
X_MASK_LABEL_P1 = X_IP_LABEL_P1
X_MASK_VALUE_P1 = X_IP_VALUE_P1

Y_GW_P1 = Y_MASK_P1 + ITEM_ROW_SPACING_P1 # Adjusted spacing
X_GW_LABEL_P1 = X_IP_LABEL_P1
X_GW_VALUE_P1 = X_IP_VALUE_P1

# --- UI Page Configuration (can be referenced from main) ---
NUM_PAGES = 2 # Assuming this might be needed by GUIManager or main
PAGE_MAIN = 0
PAGE_NETWORK = 1

class GUIManager:
    def __init__(self, display, font):
        self.display = display
        self.font = font
        self.lcd_width = display.width
        self.lcd_height = display.height

        # Page Indicator Position (Common to all pages)
        self.x_page_indicator = self.lcd_width - 45
        self.y_page_indicator = PADDING
        
        # Previous UI string states
        self.prev_wifi_status_str_p0 = None
        self.prev_ble_status_str_p0 = None
        self.prev_temperature_str = None
        self.prev_humidity_str = None
        self.prev_lux_str = None
        self.prev_noise_level_str = None
        # self.prev_pressed_key_names = None # This is directly calculated in main loop, not a text field typically
        self.prev_decibel_str = None
        
        self.prev_wifi_icon_str_p1 = None
        self.prev_ssid_str_p1 = None
        self.prev_ip_str_p1 = None
        self.prev_mask_str_p1 = None
        self.prev_gw_str_p1 = None
        
        self.prev_page_indicator_str = None

        # --- NEW: Toast specific variables ---
        self.toast_text = None
        self.toast_start_time_ms = 0
        self.toast_duration_ms = 0
        self.toast_active = False
        self._toast_last_rect = None # Stores (x,y,w,h) of the last toast to clear it

    def update_text_field(self, x, y, new_text, prev_text_attr_name, fg_color, bg_color):
        """Updates a text field only if the text has changed.
        prev_text_attr_name is the name of the attribute holding the previous text (e.g., 'prev_temperature_str').
        """
        if not self.display or not self.font:
            return getattr(self, prev_text_attr_name)
            
        prev_text = getattr(self, prev_text_attr_name)

        if new_text != prev_text:
            if prev_text is not None and prev_text != "":
                try:
                    if hasattr(self.display, 'write_width'):
                        prev_width = self.display.write_width(self.font, prev_text)
                    else:
                        prev_width = len(prev_text) * (self.font.MAX_WIDTH if hasattr(self.font, 'MAX_WIDTH') else 15)
                    self.display.fill_rect(x, y, prev_width + 2, FONT_HEIGHT, bg_color) # Clear slightly wider
                except Exception as e:
                    print(f"Err clear '{prev_text}': {e}")
            try:
                self.display.write(self.font, new_text, x, y, fg_color, bg_color)
            except Exception as e:
                print(f"Err write '{new_text}': {e}")
                return prev_text # Return old text if write failed
            
            setattr(self, prev_text_attr_name, new_text) # Update the stored previous text
            return new_text
        return prev_text

    def reset_prev_ui_strings(self):
        """Resets all previous UI string states to force redraw on page switch."""
        print("Resetting previous UI strings for page switch.")
        # Page 0
        self.prev_wifi_status_str_p0 = None
        self.prev_ble_status_str_p0 = None
        self.prev_temperature_str = None
        self.prev_humidity_str = None
        self.prev_lux_str = None
        self.prev_noise_level_str = None
        self.prev_decibel_str = None
        # Page 1
        self.prev_wifi_icon_str_p1 = None
        self.prev_ssid_str_p1 = None
        self.prev_ip_str_p1 = None
        self.prev_mask_str_p1 = None
        self.prev_gw_str_p1 = None
        # Common
        self.prev_page_indicator_str = None

    def draw_page_layout(self, page_index):
        """Draws the static layout elements for the given page."""
        if not self.display or not self.font:
            return
        print(f"Drawing layout for Page {page_index}...")
        self.display.fill(COLOR_BG)

        # Draw Page Indicator (Common to all pages)
        page_text = f"{page_index + 1}/{NUM_PAGES}"
        self.display.write(self.font, page_text, self.x_page_indicator, self.y_page_indicator, COLOR_PAGE_INDICATOR, COLOR_BG)

        if page_index == PAGE_MAIN:
            # Simplified shadow handling: Removed complex fill_rect calls for shadow.
            # Y_SEPARATOR_1_P0 now serves as the primary visual division below the status bar.
            
            # Actual static labels and separators for Page 0
            self.display.hline(0, Y_SEPARATOR_1_P0, self.lcd_width, COLOR_SEPARATOR)
            
            self.display.write(self.font, "Temp:", X_LABEL_P0, Y_TEMP_ROW_P0, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "Humi:", X_LABEL_P0, Y_HUMI_ROW_P0, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "Lux:", X_LABEL_P0, Y_LUX_ROW_P0, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "Noise:", X_LABEL_P0, Y_NOISE_RMS_ROW_P0, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "dB:", X_LABEL_P0, Y_NOISE_DB_ROW_P0, COLOR_LABEL, COLOR_BG)

        elif page_index == PAGE_NETWORK:
            self.display.write(self.font, "Network Info", X_TITLE_P1, Y_TITLE_P1, COLOR_TITLE, COLOR_BG)
            self.display.write(self.font, "NET", X_WIFI_ICON_P1, Y_WIFI_ICON_P1, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "SSID:", X_SSID_LABEL_P1, Y_SSID_P1, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "IP:", X_IP_LABEL_P1, Y_IP_P1, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "Mask:", X_MASK_LABEL_P1, Y_MASK_P1, COLOR_LABEL, COLOR_BG)
            self.display.write(self.font, "GW:", X_GW_LABEL_P1, Y_GW_P1, COLOR_LABEL, COLOR_BG)
        
        # Removed the stray 'if page_index == PAGE_MAIN:' block that was previously after the elif.
        # The 'pass' for shadow simplification is also removed as the logic above is now cleaner.

        print(f"Layout drawn for Page {page_index}.") 

    # --- NEW: Toast Methods ---
    def set_toast(self, text, current_time_ms, duration_ms=2000):
        """Activates a toast message."""
        if not self.display or not self.font:
            return

        # If a toast was active, clear its last position first
        if self.toast_active and self._toast_last_rect:
            try:
                self.display.fill_rect(
                    self._toast_last_rect[0], self._toast_last_rect[1],
                    self._toast_last_rect[2], self._toast_last_rect[3],
                    COLOR_BG # Fill with main background color
                )
            except Exception as e:
                print(f"Error clearing previous toast area: {e}")
        
        self.toast_text = text
        self.toast_start_time_ms = current_time_ms
        self.toast_duration_ms = duration_ms
        self.toast_active = True
        self._toast_last_rect = None # Reset, will be set when drawn
        # The actual drawing will happen in draw_toast_if_active
        print(f"Toast set: '{text}' for {duration_ms}ms")

    def draw_toast_if_active(self, current_time_ms):
        """Draws the toast message if active, or clears it if expired."""
        if not self.display or not self.font:
            self.toast_active = False # Cannot display
            return

        if self.toast_active:
            if time.ticks_diff(current_time_ms, self.toast_start_time_ms) > self.toast_duration_ms:
                # Toast expired
                self.toast_active = False
                if self._toast_last_rect:
                    try:
                        # Clear the area where the toast was
                        self.display.fill_rect(
                            self._toast_last_rect[0], self._toast_last_rect[1],
                            self._toast_last_rect[2], self._toast_last_rect[3],
                            COLOR_BG # Fill with main background color
                        )
                        # print(f"Toast cleared: '{self.toast_text}'")
                    except Exception as e:
                        print(f"Error clearing expired toast area: {e}")
                    self._toast_last_rect = None
                self.toast_text = None
            else:
                # Toast is active and needs to be drawn
                toast_padding = 5
                try:
                    if hasattr(self.display, 'write_width'):
                        text_width = self.display.write_width(self.font, self.toast_text)
                    else: # Basic estimation
                        text_width = len(self.toast_text) * (self.font.MAX_WIDTH if hasattr(self.font, 'MAX_WIDTH') else 15)
                except Exception: # Fallback if font is not fully loaded or missing attributes
                    text_width = len(self.toast_text) * 12 # Estimate

                toast_height = FONT_HEIGHT + 2 * toast_padding
                toast_width = text_width + 2 * toast_padding

                # Position: Centered horizontally, near the bottom
                toast_x = (self.lcd_width - toast_width) // 2
                toast_y = self.lcd_height - toast_height - 10 # 10px from bottom

                # Ensure toast is within screen bounds (simple check)
                if toast_x < 0: toast_x = 0
                if toast_y < 0: toast_y = 0
                if toast_x + toast_width > self.lcd_width:
                    toast_width = self.lcd_width - toast_x
                if toast_y + toast_height > self.lcd_height:
                    toast_height = self.lcd_height - toast_y
                
                # Store rect for clearing
                self._toast_last_rect = (toast_x, toast_y, toast_width, toast_height)

                # Draw toast background
                self.display.fill_rect(toast_x, toast_y, toast_width, toast_height, COLOR_TOAST_BG)
                # Draw toast text
                text_x_pos = toast_x + toast_padding
                text_y_pos = toast_y + toast_padding
                self.display.write(self.font, self.toast_text, text_x_pos, text_y_pos, COLOR_TOAST_FG, COLOR_TOAST_BG)
                # print(f"Toast drawn: '{self.toast_text}' at ({toast_x},{toast_y})") 