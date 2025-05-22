# alert_manager.py
# 告警管理器模块
import time # 导入时间模块

# --- 告警配置 ---
# 基于差值的告警触发阈值（可以从main.py移过来或设为可配置）
DEFAULT_TEMP_THRESHOLD_DIFF = 3.0 # 默认温度差值阈值
DEFAULT_HUMI_THRESHOLD_DIFF = 15.0 # 默认湿度差值阈值
DEFAULT_LUX_THRESHOLD_DIFF = 500.0 # 默认光照差值阈值
DEFAULT_RMS_THRESHOLD_DIFF = 500.0 # 默认RMS差值阈值 # 原始RMS差值

# 告警闪烁参数（可以从main.py移过来或设为可配置）
ALERT_FLASH_ON_MS = 150 # 告警闪烁亮的时长（毫秒）
ALERT_FLASH_OFF_MS = 100 # 告警闪烁灭的时长（毫秒）
ALERT_TOTAL_FLASHES = 2 # 告警总共闪烁的次数（一个周期亮灭各一次）

# 告警模式
ALERT_MODE_DIFFERENCE = 0 # 差值模式
ALERT_MODE_THRESHOLD_ABSOLUTE = 1 # 绝对阈值模式

class AlertManager: # 告警管理器类
    def __init__(self, temp_diff_thresh=DEFAULT_TEMP_THRESHOLD_DIFF, # 构造函数，初始化告警管理器
                 humi_diff_thresh=DEFAULT_HUMI_THRESHOLD_DIFF, # 湿度差值阈值参数
                 lux_diff_thresh=DEFAULT_LUX_THRESHOLD_DIFF, # 光照差值阈值参数
                 rms_diff_thresh=DEFAULT_RMS_THRESHOLD_DIFF): # RMS差值阈值参数
        print("Initializing AlertManager...") # 打印初始化信息
        # 当前告警状态
        self.alert_active = False # 告警是否激活标志
        self.alert_flash_step = 0 # 告警闪烁步骤计数
        self.alert_next_action_time = 0 # 下一个闪烁动作的时间（毫秒）

        # 告警模式和阈值
        self.current_alert_mode = ALERT_MODE_DIFFERENCE # 当前告警模式（默认为差值模式）
        self.needs_prev_value_rebaseline = False # 新增：标志，表示需要重新基准化上一次的传感器值

        # 差值模式的阈值
        self.temp_threshold_diff = temp_diff_thresh # 温度差值阈值
        self.humi_threshold_diff = humi_diff_thresh # 湿度差值阈值
        self.lux_threshold_diff = lux_diff_thresh # 光照差值阈值
        self.rms_threshold_diff = rms_diff_thresh # RMS差值阈值

        # 用于差值模式比较的上一次传感器值
        self.prev_temperature_val = -999.0 # 上一次的温度值（初始化为无效值）
        self.prev_humidity_val = -999.0 # 上一次的湿度值（初始化为无效值）
        self.prev_lux_val = -999.0 # 上一次的光照值（初始化为无效值）
        self.prev_rms_val = 0.0 # 上一次的原始RMS值（初始化为0） # 存储上一次的原始RMS值

        # --- 绝对阈值模式的阈值（占位符，待实现更多） ---
        self.abs_temp_high_thresh = 35.0 # 绝对温度高阈值
        self.abs_temp_low_thresh = 5.0 # 绝对温度低阈值
        self.abs_humi_high_thresh = 70.0 # 绝对湿度高阈值
        self.abs_humi_low_thresh = 20.0 # 绝对湿度低阈值
        self.abs_lux_high_thresh = 1500.0 # 新增：绝对光照高阈值
        self.abs_lux_low_thresh = 20.0 # 新增：绝对光照低阈值
        self.abs_rms_high_thresh = 8000.0 # 新增：绝对RMS高阈值（从12000.0改为8000.0）
        # ... 为光照、噪声dB等添加更多阈值（如果需要）

        print(f"AlertManager initialized. Mode: {self.current_alert_mode}, Diff Thresholds: T={self.temp_threshold_diff}, H={self.humi_threshold_diff}, L={self.lux_threshold_diff}, RMS={self.rms_threshold_diff}") # 打印初始化完成信息

    def reset_alert(self): # 重置告警状态
        """重置当前的激活告警状态。"""
        print("AlertManager: Resetting alert state.") # 打印重置告警状态信息
        self.alert_active = False # 设置告警为非激活
        self.alert_flash_step = 0 # 重置闪烁步骤
        self.alert_next_action_time = 0 # 重置下次动作时间
        # 注意：上一次的传感器值不会在这里重置，它们会持续更新。

    def is_alert_active(self): # 检查告警是否激活
        """返回True如果当前有告警处于激活状态"""
        return self.alert_active # 返回告警激活标志

    def get_alert_flash_parameters(self): # 获取告警闪烁参数
        """返回LED/蜂鸣器处理程序所需的闪烁参数"""
        if self.alert_active: # 如果告警激活
            return { # 返回一个字典包含闪烁参数
                "flash_step": self.alert_flash_step, # 当前闪烁步骤
                "next_action_time": self.alert_next_action_time, # 下一个闪烁动作时间
                "on_ms": ALERT_FLASH_ON_MS, # 亮的时长
                "off_ms": ALERT_FLASH_OFF_MS, # 灭的时长
                "total_flashes": ALERT_TOTAL_FLASHES # 总共闪烁次数
            }
        return None # 如果告警未激活，返回None

    def update_alert_flash_state(self, current_time_ms, flash_step, next_action_time): # 更新告警闪烁状态
        """由主循环的LED处理程序调用，更新告警激活时的闪烁状态"""
        self.alert_flash_step = flash_step # 更新闪烁步骤
        self.alert_next_action_time = next_action_time # 更新下次动作时间
        if self.alert_flash_step >= ALERT_TOTAL_FLASHES * 2: # 如果闪烁步骤达到总闪烁次数的两倍（亮灭算一步）
            self.reset_alert() # 告警周期完成，重置告警状态

    def check_sensor_triggers(self, current_time_ms, temp, humi, lux, raw_rms): # 检查传感器是否触发告警
        """
        检查传感器值是否符合当前告警模式和阈值。
        如果条件满足且当前没有激活告警，则激活告警。
        'raw_rms'应为用于差值检查的原始RMS值（未平滑）。
        如果触发了新的告警，返回True，否则返回False。
        """
        if self.alert_active: # 如果告警已经激活
            return False # 不重复触发，直接返回False

        # 如果需要重新基准化处理（例如，模式切换后）
        if self.needs_prev_value_rebaseline: # 如果需要重新基准化标志为True
            print("AlertManager: Rebaselining previous sensor values for next cycle.") # 打印重新基准化信息
            if temp is not None and temp > -990: self.prev_temperature_val = temp # 如果温度有效，更新上一次温度值
            else: self.prev_temperature_val = -999.0 # 否则设为无效值
            
            if humi is not None and humi > -990: self.prev_humidity_val = humi # 如果湿度有效，更新上一次湿度值
            else: self.prev_humidity_val = -999.0 # 否则设为无效值
            
            if lux is not None and lux > -990: self.prev_lux_val = lux # 如果光照有效，更新上一次光照值
            else: self.prev_lux_val = -999.0 # 否则设为无效值
            
            if raw_rms is not None and raw_rms >=0: self.prev_rms_val = raw_rms # 如果原始RMS有效，更新上一次原始RMS值
            else: self.prev_rms_val = 0.0 # 否则设为0
            
            self.needs_prev_value_rebaseline = False # 重置重新基准化标志
            print(f"AlertManager: Prev values for *next* check set to: T={self.prev_temperature_val:.1f}, H={self.prev_humidity_val:.1f}, L={self.prev_lux_val:.1f}, RMS={self.prev_rms_val:.1f}") # 打印下次检查使用的上一次值
            return False # 跳过本次告警检查，等待下次使用新的基准值

        triggered_by = None # 触发告警的原因（初始化为None）

        if self.current_alert_mode == ALERT_MODE_DIFFERENCE: # 如果当前模式是差值模式
            temp_diff = -999.0 # 温度差值（初始化为无效值）
            if temp > -990 and self.prev_temperature_val > -990: # 如果当前和上一次温度都有效
                temp_diff = temp - self.prev_temperature_val # 计算温度差值
            
            humi_diff = -999.0 # 湿度差值（初始化为无效值）
            if humi > -990 and self.prev_humidity_val > -990: # 如果当前和上一次湿度都有效
                humi_diff = humi - self.prev_humidity_val # 计算湿度差值

            lux_diff = -999.0 # 光照差值（初始化为无效值）
            if lux > -990 and self.prev_lux_val > -990: # 如果当前和上一次光照都有效
                lux_diff = lux - self.prev_lux_val # 计算光照差值
            
            rms_diff = -999.0 # RMS差值（初始化为无效值）
            if raw_rms >= 0 and self.prev_rms_val >= 0: # 如果当前和上一次原始RMS都有效，确保上一次RMS也有效用于比较
                rms_diff = raw_rms - self.prev_rms_val # 计算RMS差值

            temp_trig = (temp_diff != -999.0 and abs(temp_diff) >= self.temp_threshold_diff) # 温度触发条件：差值有效且绝对值大于等于阈值（考虑双向变化）
            humi_trig = (humi_diff != -999.0 and humi_diff >= self.humi_threshold_diff) # 湿度触发条件：差值有效且大于等于阈值（通常湿度升高更关键）
            lux_trig = (lux_diff != -999.0 and abs(lux_diff) >= self.lux_threshold_diff) # 光照触发条件：差值有效且绝对值大于等于阈值（光照可增可减）
            rms_trig = (rms_diff != -999.0 and rms_diff >= self.rms_threshold_diff) # RMS触发条件：差值有效且大于等于阈值（噪声通常是增加）

            if temp_trig: triggered_by = f"TempDiff ({temp_diff:.1f})" # 如果温度触发，记录原因
            elif humi_trig: triggered_by = f"HumiDiff ({humi_diff:.1f})" # 如果湿度触发，记录原因
            elif lux_trig: triggered_by = f"LuxDiff ({lux_diff:.1f})" # 如果光照触发，记录原因
            elif rms_trig: triggered_by = f"RMSDiff ({rms_diff:.1f}, RawRMS: {raw_rms:.1f})" # 如果RMS触发，记录原因（包含原始RMS）
        
        elif self.current_alert_mode == ALERT_MODE_THRESHOLD_ABSOLUTE: # 如果当前模式是绝对阈值模式
            if temp is not None and temp > -990 and temp >= self.abs_temp_high_thresh: # 如果温度有效且高于高阈值
                triggered_by = f"TempHigh ({temp:.1f} >= {self.abs_temp_high_thresh:.1f})" # 记录高温触发原因
            elif temp is not None and temp > -990 and temp <= self.abs_temp_low_thresh: # 如果温度有效且低于低阈值
                 triggered_by = f"TempLow ({temp:.1f} <= {self.abs_temp_low_thresh:.1f})" # 记录低温触发原因
            elif humi is not None and humi > -990 and humi >= self.abs_humi_high_thresh: # 如果湿度有效且高于高阈值
               triggered_by = f"HumiHigh ({humi:.1f} >= {self.abs_humi_high_thresh:.1f})" # 记录高湿触发原因
            elif humi is not None and humi > -990 and humi <= self.abs_humi_low_thresh: # 如果湿度有效且低于低阈值
               triggered_by = f"HumiLow ({humi:.1f} <= {self.abs_humi_low_thresh:.1f})" # 记录低湿触发原因
            elif lux is not None and lux > -990 and lux >= self.abs_lux_high_thresh: # 如果光照有效且高于高阈值（新增光照高阈值检查）
                triggered_by = f"LuxHigh ({lux:.1f} >= {self.abs_lux_high_thresh:.1f})" # 记录高光照触发原因
            elif lux is not None and lux > -990 and lux <= self.abs_lux_low_thresh: # 如果光照有效且低于低阈值（新增光照低阈值检查）
                triggered_by = f"LuxLow ({lux:.1f} <= {self.abs_lux_low_thresh:.1f})" # 记录低光照触发原因
            elif raw_rms is not None and raw_rms >= 0 and raw_rms >= self.abs_rms_high_thresh: # 如果原始RMS有效且高于高阈值（新增RMS高阈值检查）
                triggered_by = f"RMSHigh ({raw_rms:.1f} >= {self.abs_rms_high_thresh:.1f})" # 记录高RMS触发原因
            # 为光照、噪声dB等添加更多绝对模式检查（如果需要）

        # 在完成当前周期的检查后更新上一次的值，供下一次周期比较使用
        # 这会在没有因为重新基准化或告警激活而提前返回的情况下执行。
        if temp is not None and temp > -990: self.prev_temperature_val = temp # 如果温度有效，更新上一次温度值
        if humi is not None and humi > -990: self.prev_humidity_val = humi # 如果湿度有效，更新上一次湿度值
        if lux is not None and lux > -990: self.prev_lux_val = lux # 如果光照有效，更新上一次光照值
        if raw_rms is not None and raw_rms >=0: self.prev_rms_val = raw_rms # 如果原始RMS有效，更新上一次原始RMS值

        if triggered_by: # 如果有触发原因（即发生了告警）
            print(f"AlertManager: ALERT TRIGGERED by: {triggered_by}") # 打印告警触发信息
            self.alert_active = True # 激活告警
            self.alert_flash_step = 0 # 重置闪烁步骤
            self.alert_next_action_time = current_time_ms # 设置下次动作时间为当前时间，立即开始闪烁
            return True # 返回True表示触发了新的告警
            
        return False # 如果没有触发告警，返回False

    def set_alert_mode(self, mode): # 设置告警模式
        """设置告警模式。"""
        if mode in [ALERT_MODE_DIFFERENCE, ALERT_MODE_THRESHOLD_ABSOLUTE]: # 如果模式是有效的（差值或绝对阈值）
            if self.current_alert_mode != mode: # 如果当前模式与要设置的模式不同
                self.current_alert_mode = mode # 更新当前告警模式
                print(f"AlertManager: Alert mode changed to {'Difference' if mode == ALERT_MODE_DIFFERENCE else 'Absolute Threshold'}.") # 打印模式切换信息
                self.reset_alert() # 切换模式时重置任何激活的告警
                # 标记需要在下一次check_sensor_triggers调用时重新基准化上一次的值
                self.needs_prev_value_rebaseline = True # 设置重新基准化标志为True
                print("AlertManager: Flagged for prev_value rebaseline on next sensor check.") # 打印需要重新基准化标志信息
            return True # 返回True表示模式设置成功
        return False # 返回False表示模式设置失败（模式无效）

    def get_current_alert_mode(self): # 获取当前告警模式
        return self.current_alert_mode # 返回当前告警模式

    # --- 更新阈值的方法（待扩展更多） ---
    def set_difference_thresholds(self, temp_d=None, humi_d=None, lux_d=None, rms_d=None): # 设置差值模式阈值
        if temp_d is not None: self.temp_threshold_diff = float(temp_d) # 如果温度差值阈值不为None，更新温度差值阈值
        if humi_d is not None: self.humi_threshold_diff = float(humi_d) # 如果湿度差值阈值不为None，更新湿度差值阈值
        if lux_d is not None: self.lux_threshold_diff = float(lux_d) # 如果光照差值阈值不为None，更新光照差值阈值
        if rms_d is not None: self.rms_threshold_diff = float(rms_d) # 如果RMS差值阈值不为None，更新RMS差值阈值
        print(f"AlertManager: Difference thresholds updated: T={self.temp_threshold_diff}, H={self.humi_threshold_diff}, L={self.lux_threshold_diff}, RMS={self.rms_threshold_diff}") # 打印更新后的差值阈值信息

    def set_absolute_thresholds(self, config_dict): # 设置绝对阈值模式阈值
        """
        从字典设置绝对阈值。
        示例：{'temp_high': 30, 'temp_low': 0, 'humi_high': 80}
        """
        if 'temp_high' in config_dict: self.abs_temp_high_thresh = float(config_dict['temp_high']) # 如果字典包含temp_high，更新绝对温度高阈值
        if 'temp_low' in config_dict: self.abs_temp_low_thresh = float(config_dict['temp_low']) # 如果字典包含temp_low，更新绝对温度低阈值
        if 'humi_high' in config_dict: self.abs_humi_high_thresh = float(config_dict['humi_high']) # 如果字典包含humi_high，更新绝对湿度高阈值
        if 'humi_low' in config_dict: self.abs_humi_low_thresh = float(config_dict['humi_low']) # 如果字典包含humi_low，更新绝对湿度低阈值
        if 'lux_high' in config_dict: self.abs_lux_high_thresh = float(config_dict['lux_high']) # 新增
        if 'lux_low' in config_dict: self.abs_lux_low_thresh = float(config_dict['lux_low']) # 新增
        if 'rms_high' in config_dict: self.abs_rms_high_thresh = float(config_dict['rms_high']) # 新增
        # ... 对其他绝对阈值也进行类似处理
        print(f"AlertManager: Absolute thresholds updated. Example: TempHigh={self.abs_temp_high_thresh}, TempLow={self.abs_temp_low_thresh}, HumiHigh={self.abs_humi_high_thresh}, LuxHigh={self.abs_lux_high_thresh}, RMSHigh={self.abs_rms_high_thresh}") # 打印更新后的绝对阈值信息
        # 如果当前模式是绝对模式且阈值发生了显著变化，可能需要重置告警
        if self.current_alert_mode == ALERT_MODE_THRESHOLD_ABSOLUTE: # 如果当前模式是绝对阈值模式
            self.reset_alert() # 重置告警（如果在绝对模式下改变了阈值）

    def get_thresholds_info(self): # 获取阈值信息
        """返回一个字典，包含当前的阈值设置。"""
        return { # 返回包含所有当前阈值的字典
            "mode": self.current_alert_mode, # 当前模式
            "diff_temp": self.temp_threshold_diff, # 温度差值阈值
            "diff_humi": self.humi_threshold_diff, # 湿度差值阈值
            "diff_lux": self.lux_threshold_diff, # 光照差值阈值
            "diff_rms": self.rms_threshold_diff, # RMS差值阈值
            "abs_temp_high": self.abs_temp_high_thresh, # 绝对温度高阈值
            "abs_temp_low": self.abs_temp_low_thresh, # 绝对温度低阈值
            "abs_humi_high": self.abs_humi_high_thresh, # 绝对湿度高阈值
            "abs_humi_low": self.abs_humi_low_thresh, # 绝对湿度低阈值（已添加）
            "abs_lux_high": self.abs_lux_high_thresh, # 绝对光照高阈值（新增）
            "abs_lux_low": self.abs_lux_low_thresh, # 绝对光照低阈值（新增）
            "abs_rms_high": self.abs_rms_high_thresh, # 绝对RMS高阈值（新增）
            # ... 添加其他阈值
        } 