import struct

import bluetooth
import ubinascii
from micropython import const

# --- BLE Constants ---
# BLE IRQ Events
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_GATTS_INDICATE_DONE = const(6) # Added for Indication confirmation

# Flags for characteristics
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

# Environmental Sensing Service UUID (Standard)
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# Standard Characteristic UUIDs
_TEMP_CHAR_UUID = bluetooth.UUID(0x2A6E) # Temperature
_HUMID_CHAR_UUID = bluetooth.UUID(0x2A6F) # Humidity
_LUX_CHAR_UUID = bluetooth.UUID(0x2AFB)   # Illuminance (Standard)
# Custom UUID for Noise Level
_NOISE_CHAR_UUID = bluetooth.UUID("8eb6184d-bec0-41b0-8eba-e350662524ff")
_CCCD_UUID = bluetooth.UUID(0x2902) # Standard CCCD UUID

# --- NEW: Device Control Service and Characteristics UUIDs ---
_DEVICE_CONTROL_SERVICE_UUID = bluetooth.UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef") # Example custom UUID

_LED_STATE_CHAR_UUID = bluetooth.UUID("a1b2c3d4-0001-0000-0000-567890abcdef")      # Characteristic for LED On/Off
_BUZZER_ALERT_LOGIC_CHAR_UUID = bluetooth.UUID("a1b2c3d4-0002-0000-0000-567890abcdef") # Characteristic for Buzzer Alert Logic On/Off
_SCREEN_STATE_CHAR_UUID = bluetooth.UUID("a1b2c3d4-0003-0000-0000-567890abcdef")    # Characteristic for Screen On/Off
_SCREEN_BRIGHTNESS_CHAR_UUID = bluetooth.UUID("a1b2c3d4-0004-0000-0000-567890abcdef") # Characteristic for Screen Brightness (0-255)
# --- NEW UUIDs for Alert Control ---
_ALERT_SYSTEM_ENABLED_CHAR_UUID = bluetooth.UUID("a1b2c3d4-0005-0000-0000-567890abcdef") # New
_ALERT_MODE_SELECT_CHAR_UUID = bluetooth.UUID("a1b2c3d4-0006-0000-0000-567890abcdef")    # New


# Define the structure of our Environmental Sensing Service
# All characteristics now support NOTIFY and INDICATE
_ENV_SENSE_SERVICE_DEF = (
    _ENV_SENSE_UUID,
    (
        (_TEMP_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE, ((_CCCD_UUID, _FLAG_READ | _FLAG_WRITE),)),
        (_HUMID_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE, ((_CCCD_UUID, _FLAG_READ | _FLAG_WRITE),)),
        (_LUX_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE, ((_CCCD_UUID, _FLAG_READ | _FLAG_WRITE),)),
        (_NOISE_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE, ((_CCCD_UUID, _FLAG_READ | _FLAG_WRITE),)),
    ),
)

# --- NEW: Device Control Service Definition ---
_DEVICE_CONTROL_SERVICE_DEF = (
    _DEVICE_CONTROL_SERVICE_UUID,
    (
        # Characteristic: LED State (Read/Write/Notify/Indicate, 1 byte: 0=Off, 1=On)
        (_LED_STATE_CHAR_UUID, _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY | _FLAG_INDICATE, ((_CCCD_UUID, _FLAG_READ | _FLAG_WRITE),)),
        # Characteristic: Buzzer Alert Logic (Read/Write, 1 byte: 0=Disabled, 1=Enabled)
        (_BUZZER_ALERT_LOGIC_CHAR_UUID, _FLAG_READ | _FLAG_WRITE, ),
        # Characteristic: Screen State (Read/Write, 1 byte: 0=Off, 1=On)
        (_SCREEN_STATE_CHAR_UUID, _FLAG_READ | _FLAG_WRITE, ),
        # Characteristic: Screen Brightness (Read/Write/Notify/Indicate, 1 byte: 0-255)
        (_SCREEN_BRIGHTNESS_CHAR_UUID, _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY | _FLAG_INDICATE, ((_CCCD_UUID, _FLAG_READ | _FLAG_WRITE),)),
        # --- NEW Alert Control Characteristics ---
        # Characteristic: Alert System Enabled (Read/Write, 1 byte: 0=Disabled, 1=Enabled)
        (_ALERT_SYSTEM_ENABLED_CHAR_UUID, _FLAG_READ | _FLAG_WRITE),
        # Characteristic: Alert Mode Select (Read/Write/Notify/Indicate, 1 byte: 0=Diff, 1=Abs)
        (_ALERT_MODE_SELECT_CHAR_UUID, _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY | _FLAG_INDICATE, ((_CCCD_UUID, _FLAG_READ | _FLAG_WRITE),)),
    ),
)

# --- Module-level BLE State ---
_ble_instance = None
_conn_handle = None
_adv_payload_data = None
_adv_interval_current_us = 100000 # Default, can be overridden during init

# Handles for characteristics
_char_handles = {
    'temp': None, 'humid': None, 'lux': None, 'noise': None,
    'temp_cccd': None, 'humid_cccd': None, 'lux_cccd': None, 'noise_cccd': None,
    'led_state': None, 'led_state_cccd': None,
    'buzzer_logic': None,
    'screen_state': None,
    'screen_brightness': None, 'screen_brightness_cccd': None,
    'alert_system_enabled': None,
    'alert_mode_select': None, 'alert_mode_select_cccd': None,
}

_notify_enabled_flags = {'temp': False, 'humid': False, 'lux': False, 'noise': False, 'led_state': False, 'screen_brightness': False, 'alert_mode_select': False}
_indicate_enabled_flags = {'temp': False, 'humid': False, 'lux': False, 'noise': False, 'led_state': False, 'screen_brightness': False, 'alert_mode_select': False}
_indicate_in_progress_flags = {'temp': False, 'humid': False, 'lux': False, 'noise': False, 'led_state': False, 'screen_brightness': False, 'alert_mode_select': False}

# Cache for sensor values
_cached_sensor_values = {'temp': None, 'humid': None, 'lux': None, 'noise': None}

# --- NEW: Module-level state for BLE control settings (with defaults) ---
_led_control_state_ble = True  # True = On, False = Off
_buzzer_alert_logic_enabled_ble = True # True = Enabled, False = Disabled
_screen_state_ble = True # True = On, False = Off
_screen_brightness_ble = 255 # 0-255
# --- NEW: Module-level state for Alert control settings ---
_alert_system_enabled_ble = True # Default to enabled
_alert_mode_ble = 0 # Default to 0 (e.g., ALERT_MODE_DIFFERENCE)

# --- Helper functions to pack sensor data ---
def _pack_sint16_scaled(value, scale_factor=1, default_val=0x8000):
    if value is None:
        return struct.pack('<h', default_val)
    try:
        scaled_val = int(float(value) * scale_factor)
        scaled_val = max(-32768, min(32767, scaled_val))
        return struct.pack('<h', scaled_val)
    except Exception:
        return struct.pack('<h', default_val)

def _pack_uint16_scaled(value, scale_factor=1, default_val=0xFFFF):
    if value is None:
        return struct.pack('<H', default_val)
    try:
        scaled_val = int(float(value) * scale_factor)
        scaled_val = max(0, min(65535, scaled_val))
        return struct.pack('<H', scaled_val)
    except Exception:
        return struct.pack('<H', default_val)

def _pack_uint24_scaled(value, scale_factor=1, default_val=0xFFFFFF):
    if value is None:
        return default_val.to_bytes(3, 'little')
    try:
        scaled_val = int(float(value) * scale_factor)
        scaled_val = max(0, min(16777215, scaled_val))
        return scaled_val.to_bytes(3, 'little')
    except Exception:
         return default_val.to_bytes(3, 'little')

# --- BLE IRQ Handler ---
def _irq_handler(event, data):
    global _ble_instance, _conn_handle
    global _notify_enabled_flags, _indicate_enabled_flags, _indicate_in_progress_flags
    global _char_handles, _cached_sensor_values, _adv_payload_data, _adv_interval_current_us
    # --- NEW: Access to control state variables ---
    global _led_control_state_ble, _buzzer_alert_logic_enabled_ble
    global _screen_state_ble, _screen_brightness_ble
    # --- NEW: Access to alert control state variables ---
    global _alert_system_enabled_ble, _alert_mode_ble

    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle_val, _, addr = data
        _conn_handle = conn_handle_val
        addr_str = ubinascii.hexlify(addr, ':').decode()
        print(f"BLE Manager: Connected: handle={_conn_handle}, addr={addr_str}")
        for key in _notify_enabled_flags: # Reset all flags for the new connection
            _notify_enabled_flags[key] = False
            _indicate_enabled_flags[key] = False
            _indicate_in_progress_flags[key] = False
        # Ensure led_state flags are also reset if not covered by the loop above (they are if dicts updated)
        # _notify_enabled_flags['led_state'] = False # Covered by loop
        # _indicate_enabled_flags['led_state'] = False # Covered by loop
        # _indicate_in_progress_flags['led_state'] = False # Covered by loop
        
        # --- MODIFIED: Control states now persist across reconnections ---
        # _led_control_state_ble = True # No longer reset to default
        # _buzzer_alert_logic_enabled_ble = True # No longer reset to default
        # _screen_state_ble = True # No longer reset to default
        # _screen_brightness_ble = 255 # No longer reset to default
        # _alert_system_enabled_ble = True # No longer reset to default
        # _alert_mode_ble = 0 # No longer reset to default
        print("BLE Manager: Device states persist across reconnections. Client CCCD flags reset.")

    elif event == _IRQ_CENTRAL_DISCONNECT:
        conn_handle_val, _, _ = data
        if conn_handle_val == _conn_handle:
            print(f"BLE Manager: Disconnected: handle={conn_handle_val}")
            _conn_handle = None
            # Reset flags as connection is lost
            for key in _notify_enabled_flags:
                _notify_enabled_flags[key] = False
                _indicate_enabled_flags[key] = False
                _indicate_in_progress_flags[key] = False
            if _ble_instance is not None and _ble_instance.active() and _adv_payload_data is not None:
                print("BLE Manager: Restarting advertising...")
                try:
                    _ble_instance.gap_advertise(_adv_interval_current_us, adv_data=_adv_payload_data)
                except Exception as e:
                    print(f"BLE Manager: Error restarting advertising: {e}")

    elif event == _IRQ_GATTS_WRITE:
        conn_handle_val, attr_handle = data
        print(f"BLE Manager: GATTS_WRITE Event: conn_handle={conn_handle_val}, attr_handle={attr_handle}")
        
        # --- Refactored CCCD write handling ---
        char_key_for_cccd_write = None
        for key, handle_value in _char_handles.items():
            if key.endswith("_cccd") and handle_value == attr_handle:
                char_key_for_cccd_write = key[:-5] # Remove "_cccd" suffix
                break

        if char_key_for_cccd_write:
            value_written_bytes = _ble_instance.gatts_read(attr_handle)
            print(f"BLE Manager: Value written to CCCD handle {attr_handle} for '{char_key_for_cccd_write}': {ubinascii.hexlify(value_written_bytes)}")
            
            cccd_value = 0
            if len(value_written_bytes) >= 2:
                 cccd_value = struct.unpack('<H', value_written_bytes)[0]
            elif len(value_written_bytes) == 1:
                 cccd_value = value_written_bytes[0]

            notify_enabled = (cccd_value & 0x0001) != 0
            indicate_enabled = (cccd_value & 0x0002) != 0

            _notify_enabled_flags[char_key_for_cccd_write] = notify_enabled
            _indicate_enabled_flags[char_key_for_cccd_write] = indicate_enabled
            
            if not indicate_enabled: # If disabling indication, ensure in-progress is also false
                _indicate_in_progress_flags[char_key_for_cccd_write] = False

            print(f"BLE Manager: {char_key_for_cccd_write} Notify: {'Enabled' if notify_enabled else 'Disabled'}, Indicate: {'Enabled' if indicate_enabled else 'Disabled'} (CCCD Write)")
            print(f"BLE Manager: Notification states updated: Notify={_notify_enabled_flags}, Indicate={_indicate_enabled_flags}")
            
            if _conn_handle is not None and (notify_enabled or indicate_enabled):
                _send_initial_value(char_key_for_cccd_write) # Send initial value upon subscription
        else:
            # Handle writes to characteristic values
            value_written_bytes = _ble_instance.gatts_read(attr_handle)
            if not value_written_bytes:
                print(f"BLE Manager: GATTS_WRITE to handle {attr_handle}, but no data read.")
                return

            if attr_handle == _char_handles.get('led_state'):
                new_val_from_client = bool(value_written_bytes[0])
                if new_val_from_client != _led_control_state_ble:
                    _led_control_state_ble = new_val_from_client
                    print(f"BLE Manager: LED effective state set by CLIENT to: {'On' if _led_control_state_ble else 'Off'}")
                    _send_ble_notification_if_enabled('led_state', struct.pack('B', int(_led_control_state_ble)))
            elif attr_handle == _char_handles.get('buzzer_logic'):
                _buzzer_alert_logic_enabled_ble = bool(value_written_bytes[0])
                print(f"BLE Manager: Buzzer alert logic set to: {'Enabled' if _buzzer_alert_logic_enabled_ble else 'Disabled'}")
            elif attr_handle == _char_handles.get('screen_state'):
                _screen_state_ble = bool(value_written_bytes[0])
                print(f"BLE Manager: Screen state set to: {'On' if _screen_state_ble else 'Off'}")
            elif attr_handle == _char_handles.get('screen_brightness'):
                _screen_brightness_ble = int(value_written_bytes[0])
                _screen_brightness_ble = max(0, min(255, _screen_brightness_ble))
                print(f"BLE Manager: Screen brightness set to: {_screen_brightness_ble}")
                _send_ble_notification_if_enabled('screen_brightness', struct.pack('B', _screen_brightness_ble))
            # --- NEW: Handle writes to alert control characteristics ---
            elif attr_handle == _char_handles.get('alert_system_enabled'):
                _alert_system_enabled_ble = bool(value_written_bytes[0])
                print(f"BLE Manager: Alert system set to: {'Enabled' if _alert_system_enabled_ble else 'Disabled'}")
            elif attr_handle == _char_handles.get('alert_mode_select'):
                new_mode = int(value_written_bytes[0])
                new_mode = max(0, min(1, new_mode)) # Assuming 0 or 1 for modes
                if new_mode != _alert_mode_ble:
                    _alert_mode_ble = new_mode
                    print(f"BLE Manager: Alert mode set by CLIENT to: {_alert_mode_ble}")
                    _send_ble_notification_if_enabled('alert_mode_select', struct.pack('B', _alert_mode_ble))
            else:
                print(f"BLE Manager: GATTS_WRITE to unhandled characteristic value handle: {attr_handle}")

    elif event == _IRQ_GATTS_READ_REQUEST:
        conn_handle_val, attr_handle = data
        # print(f"BLE Manager: Read Request: handle={conn_handle_val}, attr={attr_handle}") # Can be verbose
        if attr_handle == _char_handles.get('temp'):
            _ble_instance.gatts_write(_char_handles['temp'], _pack_sint16_scaled(_cached_sensor_values['temp'], 100))
        elif attr_handle == _char_handles.get('humid'):
            _ble_instance.gatts_write(_char_handles['humid'], _pack_uint16_scaled(_cached_sensor_values['humid'], 100))
        elif attr_handle == _char_handles.get('lux'):
            _ble_instance.gatts_write(_char_handles['lux'], _pack_uint24_scaled(_cached_sensor_values['lux'], 100))
        elif attr_handle == _char_handles.get('noise'):
            _ble_instance.gatts_write(_char_handles['noise'], _pack_sint16_scaled(_cached_sensor_values['noise'], 10))
        elif attr_handle == _char_handles.get('led_state'):
            _ble_instance.gatts_write(_char_handles['led_state'], struct.pack('?', _led_control_state_ble))
        elif attr_handle == _char_handles.get('buzzer_logic'):
            _ble_instance.gatts_write(_char_handles['buzzer_logic'], struct.pack('?', _buzzer_alert_logic_enabled_ble))
        elif attr_handle == _char_handles.get('screen_state'):
            _ble_instance.gatts_write(_char_handles['screen_state'], struct.pack('?', _screen_state_ble))
        elif attr_handle == _char_handles.get('screen_brightness'):
            _ble_instance.gatts_write(_char_handles['screen_brightness'], struct.pack('B', _screen_brightness_ble))
        # --- NEW: Handle reads for alert control characteristics ---
        elif attr_handle == _char_handles.get('alert_system_enabled'):
            _ble_instance.gatts_write(_char_handles['alert_system_enabled'], struct.pack('?', _alert_system_enabled_ble))
        elif attr_handle == _char_handles.get('alert_mode_select'):
            _ble_instance.gatts_write(_char_handles['alert_mode_select'], struct.pack('B', _alert_mode_ble))

    elif event == _IRQ_GATTS_INDICATE_DONE:
        conn_handle_val, value_handle, status = data
        # print(f"BLE Manager: Indicate DONE: conn_handle={conn_handle_val}, value_handle={value_handle}, status={status}")
        
        char_key_indicated = None
        # Find which characteristic this indication was for
        for key, handle_val in _char_handles.items():
            if not key.endswith("_cccd") and handle_val == value_handle: # Check non-CCCD handles
                char_key_indicated = key
                break
        
        if char_key_indicated and char_key_indicated in _indicate_in_progress_flags:
            _indicate_in_progress_flags[char_key_indicated] = False
            # print(f"BLE Manager: Indication in progress for {char_key_indicated} CLEARED.")
        # else: # Should not happen if mapping is correct
            # print(f"BLE Manager: Indicate DONE for unmapped handle {value_handle} or char_key {char_key_indicated} not in progress flags.")


def _send_initial_value(char_key):
    """Helper to send initial notification or indication upon subscription."""
    global _conn_handle, _ble_instance, _char_handles, _cached_sensor_values
    global _notify_enabled_flags, _indicate_enabled_flags, _indicate_in_progress_flags
    global _led_control_state_ble, _screen_brightness_ble, _alert_mode_ble # Access relevant states
    
    packed_val = None
    value_to_send = None # Will be set based on char_key

    try:
        if char_key == 'temp':
            value_to_send = _cached_sensor_values.get('temp')
            packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
        elif char_key == 'humid':
            value_to_send = _cached_sensor_values.get('humid')
            packed_val = _pack_uint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
        elif char_key == 'lux':
            value_to_send = _cached_sensor_values.get('lux')
            packed_val = _pack_uint24_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
        elif char_key == 'noise':
            value_to_send = _cached_sensor_values.get('noise')
            packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send >= 0 else None, 10)
        elif char_key == 'led_state':
            value_to_send = _led_control_state_ble
            packed_val = struct.pack('B', int(value_to_send))
        elif char_key == 'screen_brightness':
            value_to_send = _screen_brightness_ble
            packed_val = struct.pack('B', int(value_to_send))
        elif char_key == 'alert_mode_select': # New
            value_to_send = _alert_mode_ble
            packed_val = struct.pack('B', int(value_to_send))


        if packed_val is None:
            # print(f"BLE Manager: No valid cached/current value to send for initial {char_key}")
            return

        # Prefer Indication if enabled and not in progress
        if _indicate_enabled_flags.get(char_key) and not _indicate_in_progress_flags.get(char_key):
            # print(f"BLE Manager: Attempting initial INDICATION for {char_key}: conn_h={_conn_handle}, val_h={_char_handles.get(char_key)}, data={ubinascii.hexlify(packed_val)}")
            _ble_instance.gatts_indicate(_conn_handle, _char_handles[char_key], packed_val)
            _indicate_in_progress_flags[char_key] = True
            print(f"BLE Manager: Sent initial {char_key} Indication value: {value_to_send}")
        elif _notify_enabled_flags.get(char_key):
            # print(f"BLE Manager: Attempting initial NOTIFY for {char_key}: conn_h={_conn_handle}, val_h={_char_handles.get(char_key)}, data={ubinascii.hexlify(packed_val)}")
            _ble_instance.gatts_notify(_conn_handle, _char_handles[char_key], packed_val)
            print(f"BLE Manager: Sent initial {char_key} Notify value: {value_to_send}")

    except OSError as e:
        print(f"BLE Manager: Error sending initial {char_key} value: {e}")
        if e.args[0] == 104: _conn_handle = None # Handle disconnect
    except Exception as e:
        print(f"BLE Manager: Unexpected error sending initial {char_key} value: {e}")


# --- Public API ---
def initialize(device_name, adv_interval_us=100000):
    global _ble_instance, _adv_payload_data, _adv_interval_current_us, _char_handles

    if bluetooth is None:
        print("BLE Manager: Bluetooth module not available.")
        return False
    
    _ble_instance = bluetooth.BLE()
    if not _ble_instance.active():
        print("BLE Manager: Activating Bluetooth...")
        try:
            _ble_instance.active(True)
        except Exception as e:
            print(f"BLE Manager: Error activating BLE: {e}")
            _ble_instance = None
            return False

    _adv_interval_current_us = adv_interval_us
    print("BLE Manager: Configuring GATT services...")
    try:
        registered_services_tuples = _ble_instance.gatts_register_services(
            (_ENV_SENSE_SERVICE_DEF, _DEVICE_CONTROL_SERVICE_DEF)
        )
        
        env_sense_service_handles = registered_services_tuples[0]
        _char_handles['temp'] = env_sense_service_handles[0]; _char_handles['temp_cccd'] = env_sense_service_handles[1]
        _char_handles['humid'] = env_sense_service_handles[2]; _char_handles['humid_cccd'] = env_sense_service_handles[3]
        _char_handles['lux'] = env_sense_service_handles[4]; _char_handles['lux_cccd'] = env_sense_service_handles[5]
        _char_handles['noise'] = env_sense_service_handles[6]; _char_handles['noise_cccd'] = env_sense_service_handles[7]
        
        print("BLE Manager: Environmental Sensing Service Registered.")
        # print(f"  Temp Handle Value: {_char_handles['temp']}, CCCD: {_char_handles['temp_cccd']}")
        # ... other env sense prints ...

        if len(registered_services_tuples) > 1:
            control_service_handles = registered_services_tuples[1]
            _char_handles['led_state'] = control_service_handles[0]
            _char_handles['led_state_cccd'] = control_service_handles[1]
            _char_handles['buzzer_logic'] = control_service_handles[2]
            _char_handles['screen_state'] = control_service_handles[3]
            _char_handles['screen_brightness'] = control_service_handles[4]
            _char_handles['screen_brightness_cccd'] = control_service_handles[5] # Added
            # --- NEW: Assign handles for alert control ---
            _char_handles['alert_system_enabled'] = control_service_handles[6]
            _char_handles['alert_mode_select'] = control_service_handles[7]
            _char_handles['alert_mode_select_cccd'] = control_service_handles[8]
            
            print("BLE Manager: Device Control Service Registered.")
            print(f"  LED State Handle: {_char_handles['led_state']}, CCCD: {_char_handles['led_state_cccd']}")
            print(f"  Buzzer Logic Handle: {_char_handles['buzzer_logic']}")
            print(f"  Screen State Handle: {_char_handles['screen_state']}")
            print(f"  Screen Brightness Handle: {_char_handles['screen_brightness']}, CCCD: {_char_handles['screen_brightness_cccd']}")
            print(f"  Alert System Enabled Handle: {_char_handles['alert_system_enabled']}")
            print(f"  Alert Mode Select Handle: {_char_handles['alert_mode_select']}, CCCD: {_char_handles['alert_mode_select_cccd']}")
        else:
            print("BLE Manager: WARNING - Device Control Service handles not found after registration.")

    except Exception as e:
        print(f"BLE Manager: Error registering GATT services: {e}")
        _ble_instance.active(False); _ble_instance = None
        return False

    _ble_instance.irq(_irq_handler)
    print("BLE Manager: IRQ handler set.")

    print("BLE Manager: Configuring advertisement...")
    payload = bytearray()
    payload.extend(b'\x02\x01\x06') 
    payload.extend(b'\x03\x03\x1A\x18')
    name_bytes = bytes(device_name, 'utf-8')
    payload.extend(bytes([len(name_bytes) + 1, 0x09]))
    payload.extend(name_bytes)
    _adv_payload_data = payload
    
    try:
        _ble_instance.gap_advertise(_adv_interval_current_us, adv_data=_adv_payload_data)
        print(f"BLE Manager: Advertising started as '{device_name}'.")
        return True
    except Exception as e:
        print(f"BLE Manager: Error starting advertising: {e}")
        try: # Fallback
             payload_fallback = bytearray()
             payload_fallback.extend(b'\x02\x01\x06')
             payload_fallback.extend(bytes([len(name_bytes) + 1, 0x09]))
             payload_fallback.extend(name_bytes)
             _adv_payload_data = payload_fallback
             _ble_instance.gap_advertise(_adv_interval_current_us, adv_data=_adv_payload_data)
             print("BLE Manager: Advertising started (name only).")
             return True
        except Exception as e_fb:
             print(f"BLE Manager: Error starting fallback advertising: {e_fb}")
             _adv_payload_data = None
             if _ble_instance: _ble_instance.active(False); _ble_instance = None
             return False

def update_sensor_data_and_send(temp_val, humid_val, lux_val, noise_rms_val):
    global _cached_sensor_values, _ble_instance, _conn_handle
    global _notify_enabled_flags, _indicate_enabled_flags, _indicate_in_progress_flags, _char_handles

    _cached_sensor_values['temp'] = temp_val
    _cached_sensor_values['humid'] = humid_val
    _cached_sensor_values['lux'] = lux_val
    _cached_sensor_values['noise'] = noise_rms_val

    if _conn_handle is None or _ble_instance is None:
        return

    # print(f"BLE Manager: update_sensor_data_and_send. Notify: {_notify_enabled_flags}, Indicate: {_indicate_enabled_flags}, InProgress: {_indicate_in_progress_flags}")

    for char_key in ['temp', 'humid', 'lux', 'noise']: # Iterate only sensor keys here
        packed_val = None
        value_to_send = _cached_sensor_values[char_key] # Use .get(char_key) for safety if keys might be missing
        
        try:
            if char_key == 'temp':
                packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
            elif char_key == 'humid':
                packed_val = _pack_uint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
            elif char_key == 'lux':
                packed_val = _pack_uint24_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
            elif char_key == 'noise':
                packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send >= 0 else None, 10)

            if packed_val is None: continue

            # Call generic helper instead of duplicating logic
            _send_ble_notification_if_enabled(char_key, packed_val)
                
        except OSError as e: # This outer try-except might be redundant if _send_ble_notification_if_enabled handles it
            print(f"BLE Manager: Error sending data for {char_key}: {e}")
            if e.args[0] == 104: # ECONNRESET
                _conn_handle = None
                print("BLE Manager: Connection reset during send, handle cleared.")
                for key_in_loop in _notify_enabled_flags: # Reset all flags
                    _notify_enabled_flags[key_in_loop] = False
                    _indicate_enabled_flags[key_in_loop] = False
                    _indicate_in_progress_flags[key_in_loop] = False
                break 
        except Exception as e:
            print(f"BLE Manager: Unexpected error sending data for {char_key}: {e}")


def is_connected():
    global _conn_handle
    return _conn_handle is not None

def is_active():
    global _ble_instance
    return _ble_instance is not None and _ble_instance.active()

def deinitialize():
    global _ble_instance, _conn_handle
    # --- NEW: Reset control states to default on deinitialization ---
    global _led_control_state_ble, _buzzer_alert_logic_enabled_ble
    global _screen_state_ble, _screen_brightness_ble
    # --- NEW: Reset alert control states ---
    global _alert_system_enabled_ble, _alert_mode_ble


    if _ble_instance is not None:
        try:
            if _conn_handle is not None:
                _ble_instance.gap_disconnect(_conn_handle)
                print("BLE Manager: Disconnected from client.")
                _conn_handle = None
            if _ble_instance.active():
                _ble_instance.gap_advertise(None) # Stop advertising
                _ble_instance.active(False)
                print("BLE Manager: Bluetooth deactivated.")
            _ble_instance = None
            # Reset states only if explicitly designed for full deinitialization,
            # otherwise they should reflect the last known state.
            # For this change, we assume deinitialize() means a full stop and reset.
            _led_control_state_ble = True
            _buzzer_alert_logic_enabled_ble = True
            _screen_state_ble = True
            _screen_brightness_ble = 255
            _alert_system_enabled_ble = True
            _alert_mode_ble = 0
            print("BLE Manager: All control and alert states reset to default during deinitialization.")
        except Exception as e:
            print(f"BLE Manager: Error deinitializing BLE: {e}")

# --- NEW: Public Getter Functions for Control States ---
def get_led_control_state_ble():
    global _led_control_state_ble
    return _led_control_state_ble

def get_buzzer_alert_logic_enabled_ble():
    global _buzzer_alert_logic_enabled_ble
    return _buzzer_alert_logic_enabled_ble

def get_screen_state_ble():
    global _screen_state_ble
    return _screen_state_ble

def get_screen_brightness_ble():
    global _screen_brightness_ble
    return _screen_brightness_ble

# --- NEW: Public Getter Functions for Alert Control States ---
def get_alert_system_enabled_ble():
    global _alert_system_enabled_ble
    return _alert_system_enabled_ble

def get_alert_mode_ble():
    global _alert_mode_ble
    return _alert_mode_ble

# --- NEW HELPER: Internal function to send notifications/indications ---
def _send_ble_notification_if_enabled(char_key_name, packed_data):
    global _conn_handle, _ble_instance, _char_handles
    global _notify_enabled_flags, _indicate_enabled_flags, _indicate_in_progress_flags

    if _conn_handle is None or _ble_instance is None:
        return False

    sent = False
    try:
        target_value_handle = _char_handles.get(char_key_name)
        if target_value_handle is None:
            # print(f"BLE Manager: No value handle for char_key '{char_key_name}' in _send_ble_notification_if_enabled.")
            return False

        # Prefer Indication if enabled and not already in progress for this characteristic
        if _indicate_enabled_flags.get(char_key_name, False) and \
           not _indicate_in_progress_flags.get(char_key_name, False):
            
            _ble_instance.gatts_indicate(_conn_handle, target_value_handle, packed_data)
            _indicate_in_progress_flags[char_key_name] = True
            # print(f"BLE Manager: Sent INDICATION for {char_key_name}")
            sent = True
        # Else, if notification is enabled, send notification
        elif _notify_enabled_flags.get(char_key_name, False):
            _ble_instance.gatts_notify(_conn_handle, target_value_handle, packed_data)
            # print(f"BLE Manager: Sent NOTIFY for {char_key_name}")
            sent = True
    except OSError as e:
        # print(f"BLE Manager: OSError sending {char_key_name} notification/indication: {e}")
        if e.args[0] == 104 or e.args[0] == 128: # ECONNRESET / ENOTCONN
            print(f"BLE Manager: Connection error ({e.args[0]}) sending {char_key_name}. Clearing handle.")
            _conn_handle = None 
            # Reset relevant flags for this characteristic as client is gone/unsubscribed implicitly
            if char_key_name in _notify_enabled_flags: _notify_enabled_flags[char_key_name] = False
            if char_key_name in _indicate_enabled_flags: _indicate_enabled_flags[char_key_name] = False
            if char_key_name in _indicate_in_progress_flags: _indicate_in_progress_flags[char_key_name] = False
    except Exception as e:
        print(f"BLE Manager: Unexpected error sending {char_key_name} notification/indication: {e}")
    return sent


# --- NEW/MODIFIED Public API function for main.py to update LED state ---
def update_led_state_and_notify_if_changed(new_effective_led_state):
    global _led_control_state_ble
    new_effective_led_state = bool(new_effective_led_state)
    state_changed = (new_effective_led_state != _led_control_state_ble)
    _led_control_state_ble = new_effective_led_state 

    if state_changed:
        print(f"BLE Manager: LED effective state changed to: {_led_control_state_ble} (by device logic). Notifying if subscribed.")
        packed_val = struct.pack('B', int(_led_control_state_ble))
        _send_ble_notification_if_enabled('led_state', packed_val)

def update_screen_brightness_and_notify_if_changed(new_brightness):
    global _screen_brightness_ble
    new_brightness = max(0, min(255, int(new_brightness)))
    state_changed = (new_brightness != _screen_brightness_ble)
    _screen_brightness_ble = new_brightness

    if state_changed:
        print(f"BLE Manager: Screen brightness changed to: {_screen_brightness_ble} (by device logic). Notifying if subscribed.")
        packed_val = struct.pack('B', _screen_brightness_ble)
        _send_ble_notification_if_enabled('screen_brightness', packed_val)

# --- NEW: Public function for main.py to update alert mode from device ---
def update_alert_mode_ble_and_notify(new_mode):
    """
    Called by main.py (e.g., after a physical key press) to update the alert mode.
    If the state changes and a client is subscribed, it sends a notification/indication.
    """
    global _alert_mode_ble
    new_mode = int(new_mode) # Ensure it's an int (0 or 1)
    state_changed = (new_mode != _alert_mode_ble)
    
    _alert_mode_ble = new_mode # Update the master BLE state

    if state_changed:
        print(f"BLE Manager: Alert mode changed to: {_alert_mode_ble} (by device logic). Notifying if subscribed.")
        packed_val = struct.pack('B', _alert_mode_ble)
        _send_ble_notification_if_enabled('alert_mode_select', packed_val)
    # else:
    #     print(f"BLE Manager: Alert mode remains: {_alert_mode_ble}. No notification needed from this call.")

# Ensure advertising payload is correctly constructed if services change
# For now, the advertised services (UUID 0x181A in payload) remain the same.
# If _DEVICE_CONTROL_SERVICE_UUID were to be advertised, payload would need update.
