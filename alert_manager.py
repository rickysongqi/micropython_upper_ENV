# alert_manager.py
import time

# --- Alert Configuration ---
# Thresholds for DIFFERENCE-BASED alert triggering (can be moved from main.py or made configurable)
DEFAULT_TEMP_THRESHOLD_DIFF = 3.0
DEFAULT_HUMI_THRESHOLD_DIFF = 15.0
DEFAULT_LUX_THRESHOLD_DIFF = 500.0
DEFAULT_RMS_THRESHOLD_DIFF = 1500.0 # Raw RMS difference

# Alert flashing parameters (can be moved from main.py or made configurable)
ALERT_FLASH_ON_MS = 150
ALERT_FLASH_OFF_MS = 100
ALERT_TOTAL_FLASHES = 2

# Alert Modes
ALERT_MODE_DIFFERENCE = 0
ALERT_MODE_THRESHOLD_ABSOLUTE = 1

class AlertManager:
    def __init__(self, temp_diff_thresh=DEFAULT_TEMP_THRESHOLD_DIFF,
                 humi_diff_thresh=DEFAULT_HUMI_THRESHOLD_DIFF,
                 lux_diff_thresh=DEFAULT_LUX_THRESHOLD_DIFF,
                 rms_diff_thresh=DEFAULT_RMS_THRESHOLD_DIFF):
        print("Initializing AlertManager...")
        # Current alert status
        self.alert_active = False
        self.alert_flash_step = 0
        self.alert_next_action_time = 0

        # Alert mode and thresholds
        self.current_alert_mode = ALERT_MODE_DIFFERENCE # Default mode

        # Thresholds for DIFFERENCE mode
        self.temp_threshold_diff = temp_diff_thresh
        self.humi_threshold_diff = humi_diff_thresh
        self.lux_threshold_diff = lux_diff_thresh
        self.rms_threshold_diff = rms_diff_thresh

        # Previous sensor values for DIFFERENCE mode comparison
        self.prev_temperature_val = -999.0
        self.prev_humidity_val = -999.0
        self.prev_lux_val = -999.0
        self.prev_rms_val = 0.0 # Stores the *previous raw* RMS value

        # --- Thresholds for ABSOLUTE mode (placeholders, to be implemented) ---
        self.abs_temp_high_thresh = 35.0
        self.abs_temp_low_thresh = 5.0
        self.abs_humi_high_thresh = 70.0
        self.abs_humi_low_thresh = 20.0
        # ... add more for lux, noise_rms_db etc.

        print(f"AlertManager initialized. Mode: {self.current_alert_mode}, Diff Thresholds: T={self.temp_threshold_diff}, H={self.humi_threshold_diff}, L={self.lux_threshold_diff}, RMS={self.rms_threshold_diff}")

    def reset_alert(self):
        """Resets the active alert state."""
        print("AlertManager: Resetting alert state.")
        self.alert_active = False
        self.alert_flash_step = 0
        self.alert_next_action_time = 0
        # Note: Previous sensor values are not reset here, they continue to update.

    def is_alert_active(self):
        """Returns True if an alert is currently active."""
        return self.alert_active

    def get_alert_flash_parameters(self):
        """Returns parameters needed by the LED/Buzzer handler for flashing."""
        if self.alert_active:
            return {
                "flash_step": self.alert_flash_step,
                "next_action_time": self.alert_next_action_time,
                "on_ms": ALERT_FLASH_ON_MS,
                "off_ms": ALERT_FLASH_OFF_MS,
                "total_flashes": ALERT_TOTAL_FLASHES
            }
        return None

    def update_alert_flash_state(self, current_time_ms, flash_step, next_action_time):
        """Called by the main loop's LED handler to update flash state if alert is active."""
        self.alert_flash_step = flash_step
        self.alert_next_action_time = next_action_time
        if self.alert_flash_step >= ALERT_TOTAL_FLASHES * 2:
            self.reset_alert() # Alert cycle finished

    def check_sensor_triggers(self, current_time_ms, temp, humi, lux, raw_rms):
        """
        Checks sensor values against current alert mode and thresholds.
        Activates alert if conditions are met and no alert is currently active.
        'raw_rms' should be the non-smoothed RMS value for difference checking.
        Returns True if a new alert was triggered, False otherwise.
        """
        if self.alert_active:
            return False # Don't re-trigger if already active

        triggered_by = None

        if self.current_alert_mode == ALERT_MODE_DIFFERENCE:
            temp_diff = -999.0
            if temp > -990 and self.prev_temperature_val > -990:
                temp_diff = temp - self.prev_temperature_val
            
            humi_diff = -999.0
            if humi > -990 and self.prev_humidity_val > -990:
                humi_diff = humi - self.prev_humidity_val

            lux_diff = -999.0
            if lux > -990 and self.prev_lux_val > -990:
                lux_diff = lux - self.prev_lux_val
            
            rms_diff = -999.0
            if raw_rms >= 0 and self.prev_rms_val >= 0:
                rms_diff = raw_rms - self.prev_rms_val

            temp_trig = (temp_diff != -999.0 and temp_diff >= self.temp_threshold_diff)
            humi_trig = (humi_diff != -999.0 and humi_diff >= self.humi_threshold_diff)
            lux_trig = (lux_diff != -999.0 and lux_diff >= self.lux_threshold_diff)
            rms_trig = (rms_diff != -999.0 and rms_diff >= self.rms_threshold_diff)

            if temp_trig: triggered_by = f"TempDiff ({temp_diff:.1f})"
            elif humi_trig: triggered_by = f"HumiDiff ({humi_diff:.1f})"
            elif lux_trig: triggered_by = f"LuxDiff ({lux_diff:.1f})"
            elif rms_trig: triggered_by = f"RMSDiff ({rms_diff:.1f}, RawRMS: {raw_rms:.1f})"
        
        elif self.current_alert_mode == ALERT_MODE_THRESHOLD_ABSOLUTE:
            # --- Placeholder for absolute threshold checking ---
            if temp is not None and temp > -990 and temp >= self.abs_temp_high_thresh:
                triggered_by = f"TempHigh ({temp:.1f} >= {self.abs_temp_high_thresh:.1f})"
            # Add more checks for low temp, high/low humi, etc.
            # Example:
            # elif humi is not None and humi > -990 and humi >= self.abs_humi_high_thresh:
            #    triggered_by = f"HumiHigh ({humi:.1f} >= {self.abs_humi_high_thresh:.1f})"
            pass # Implement fully later

        # Update previous values AFTER checking, regardless of trigger
        if temp is not None and temp > -990: self.prev_temperature_val = temp
        if humi is not None and humi > -990: self.prev_humidity_val = humi
        if lux is not None and lux > -990: self.prev_lux_val = lux
        if raw_rms is not None and raw_rms >=0: self.prev_rms_val = raw_rms


        if triggered_by:
            print(f"AlertManager: ALERT TRIGGERED by: {triggered_by}")
            self.alert_active = True
            self.alert_flash_step = 0
            self.alert_next_action_time = current_time_ms # Start flashing immediately
            return True
            
        return False

    def set_alert_mode(self, mode):
        """Sets the alert mode."""
        if mode in [ALERT_MODE_DIFFERENCE, ALERT_MODE_THRESHOLD_ABSOLUTE]:
            if self.current_alert_mode != mode:
                self.current_alert_mode = mode
                print(f"AlertManager: Alert mode changed to {'Difference' if mode == ALERT_MODE_DIFFERENCE else 'Absolute Threshold'}.")
                self.reset_alert() # Reset any active alert when mode changes
                # Resetting previous values might be good too, or let them naturally update
                self.prev_temperature_val = -999.0 
                self.prev_humidity_val = -999.0
                self.prev_lux_val = -999.0
                self.prev_rms_val = 0.0
            return True
        return False

    def get_current_alert_mode(self):
        return self.current_alert_mode

    # --- Methods to update thresholds (to be expanded) ---
    def set_difference_thresholds(self, temp_d=None, humi_d=None, lux_d=None, rms_d=None):
        if temp_d is not None: self.temp_threshold_diff = float(temp_d)
        if humi_d is not None: self.humi_threshold_diff = float(humi_d)
        if lux_d is not None: self.lux_threshold_diff = float(lux_d)
        if rms_d is not None: self.rms_threshold_diff = float(rms_d)
        print(f"AlertManager: Difference thresholds updated: T={self.temp_threshold_diff}, H={self.humi_threshold_diff}, L={self.lux_threshold_diff}, RMS={self.rms_threshold_diff}")

    def set_absolute_thresholds(self, config_dict):
        """
        Sets absolute thresholds from a dictionary.
        Example: {'temp_high': 30, 'temp_low': 0, 'humi_high': 80}
        """
        if 'temp_high' in config_dict: self.abs_temp_high_thresh = float(config_dict['temp_high'])
        if 'temp_low' in config_dict: self.abs_temp_low_thresh = float(config_dict['temp_low'])
        if 'humi_high' in config_dict: self.abs_humi_high_thresh = float(config_dict['humi_high'])
        # ... and so on for other absolute thresholds
        print(f"AlertManager: Absolute thresholds updated. Example: TempHigh={self.abs_temp_high_thresh}")
        # Potentially reset alert if mode is absolute and thresholds change significantly
        if self.current_alert_mode == ALERT_MODE_THRESHOLD_ABSOLUTE:
            self.reset_alert()

    def get_thresholds_info(self):
        """Returns a dictionary with current threshold settings."""
        return {
            "mode": self.current_alert_mode,
            "diff_temp": self.temp_threshold_diff,
            "diff_humi": self.humi_threshold_diff,
            "diff_lux": self.lux_threshold_diff,
            "diff_rms": self.rms_threshold_diff,
            "abs_temp_high": self.abs_temp_high_thresh,
            "abs_temp_low": self.abs_temp_low_thresh,
            "abs_humi_high": self.abs_humi_high_thresh,
            # ... add others
        } 