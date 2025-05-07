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

# --- Module-level BLE State ---
_ble_instance = None
_conn_handle = None
_adv_payload_data = None
_adv_interval_current_us = 100000 # Default, can be overridden during init

# Handles for characteristics
_char_handles = {
    'temp': None, 'humid': None, 'lux': None, 'noise': None,
    'temp_cccd': None, 'humid_cccd': None, 'lux_cccd': None, 'noise_cccd': None,
}

_notify_enabled_flags = {'temp': False, 'humid': False, 'lux': False, 'noise': False}
_indicate_enabled_flags = {'temp': False, 'humid': False, 'lux': False, 'noise': False}
_indicate_in_progress_flags = {'temp': False, 'humid': False, 'lux': False, 'noise': False}

# Cache for sensor values
_cached_sensor_values = {'temp': None, 'humid': None, 'lux': None, 'noise': None}

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

    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle_val, _, addr = data
        _conn_handle = conn_handle_val
        addr_str = ubinascii.hexlify(addr, ':').decode()
        print(f"BLE Manager: Connected: handle={_conn_handle}, addr={addr_str}")
        for key in _notify_enabled_flags: # Reset all flags for the new connection
            _notify_enabled_flags[key] = False
            _indicate_enabled_flags[key] = False
            _indicate_in_progress_flags[key] = False

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
        
        char_key_for_cccd_write = None
        if attr_handle == _char_handles['temp_cccd']: char_key_for_cccd_write = 'temp'
        elif attr_handle == _char_handles['humid_cccd']: char_key_for_cccd_write = 'humid'
        elif attr_handle == _char_handles['lux_cccd']: char_key_for_cccd_write = 'lux'
        elif attr_handle == _char_handles['noise_cccd']: char_key_for_cccd_write = 'noise'

        if char_key_for_cccd_write:
            value_written_bytes = _ble_instance.gatts_read(attr_handle)
            print(f"BLE Manager: Value written to CCCD handle {attr_handle}: {ubinascii.hexlify(value_written_bytes)}")
            
            cccd_value = 0
            if len(value_written_bytes) >= 2: # Ensure at least 2 bytes for unpack
                 cccd_value = struct.unpack('<H', value_written_bytes)[0]
            elif len(value_written_bytes) == 1: # Handle if only one byte is written (less common for CCCD)
                 cccd_value = value_written_bytes[0]


            notify_enabled = (cccd_value & 0x0001) != 0
            indicate_enabled = (cccd_value & 0x0002) != 0

            _notify_enabled_flags[char_key_for_cccd_write] = notify_enabled
            _indicate_enabled_flags[char_key_for_cccd_write] = indicate_enabled
            
            # If disabling, ensure in-progress is also false
            if not indicate_enabled:
                _indicate_in_progress_flags[char_key_for_cccd_write] = False

            print(f"BLE Manager: {char_key_for_cccd_write.capitalize()} Notify: {'Enabled' if notify_enabled else 'Disabled'}, Indicate: {'Enabled' if indicate_enabled else 'Disabled'} (CCCD Write)")
            print(f"BLE Manager: Notification states updated: Notify={_notify_enabled_flags}, Indicate={_indicate_enabled_flags}")
            
            if _conn_handle is not None and (notify_enabled or indicate_enabled):
                # Send initial value if a subscription was enabled
                _send_initial_value(char_key_for_cccd_write)
        else:
            print(f"BLE Manager: GATTS_WRITE to non-CCCD handle: {attr_handle}")
            # Potentially handle writes to characteristic values themselves if they are writable

    elif event == _IRQ_GATTS_READ_REQUEST:
        conn_handle_val, attr_handle = data
        print(f"BLE Manager: Read Request: handle={conn_handle_val}, attr={attr_handle}")
        if attr_handle == _char_handles['temp']:
            _ble_instance.gatts_write(_char_handles['temp'], _pack_sint16_scaled(_cached_sensor_values['temp'], 100))
        elif attr_handle == _char_handles['humid']:
            _ble_instance.gatts_write(_char_handles['humid'], _pack_uint16_scaled(_cached_sensor_values['humid'], 100))
        elif attr_handle == _char_handles['lux']:
            _ble_instance.gatts_write(_char_handles['lux'], _pack_uint24_scaled(_cached_sensor_values['lux'], 100))
        elif attr_handle == _char_handles['noise']:
            _ble_instance.gatts_write(_char_handles['noise'], _pack_sint16_scaled(_cached_sensor_values['noise'], 10))

    elif event == _IRQ_GATTS_INDICATE_DONE:
        conn_handle_val, value_handle, status = data
        print(f"BLE Manager: Indicate DONE: conn_handle={conn_handle_val}, value_handle={value_handle}, status={status}")
        
        char_key_indicated = None
        if value_handle == _char_handles['temp']: char_key_indicated = 'temp'
        elif value_handle == _char_handles['humid']: char_key_indicated = 'humid'
        elif value_handle == _char_handles['lux']: char_key_indicated = 'lux'
        elif value_handle == _char_handles['noise']: char_key_indicated = 'noise'
        
        if char_key_indicated:
            _indicate_in_progress_flags[char_key_indicated] = False
            print(f"BLE Manager: Indication in progress for {char_key_indicated.capitalize()} CLEARED.")
            # Optionally, try to send next data if new data is available and indication is still enabled
            # For simplicity, next periodic update will handle this.

def _send_initial_value(char_key):
    """Helper to send initial notification or indication upon subscription."""
    global _conn_handle, _ble_instance, _char_handles, _cached_sensor_values
    global _notify_enabled_flags, _indicate_enabled_flags, _indicate_in_progress_flags
    
    packed_val = None
    value_to_send = _cached_sensor_values[char_key]

    try:
        if char_key == 'temp':
            packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
        elif char_key == 'humid':
            packed_val = _pack_uint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
        elif char_key == 'lux':
            packed_val = _pack_uint24_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
        elif char_key == 'noise':
            packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send >= 0 else None, 10)

        if packed_val is None:
            print(f"BLE Manager: No valid cached value to send for initial {char_key.capitalize()}")
            return

        # Prefer Indication if enabled and not in progress
        if _indicate_enabled_flags[char_key] and not _indicate_in_progress_flags[char_key]:
            print(f"BLE Manager: Attempting initial INDICATION for {char_key}: conn_h={_conn_handle}, val_h={_char_handles[char_key]}, data={ubinascii.hexlify(packed_val)}")
            _ble_instance.gatts_indicate(_conn_handle, _char_handles[char_key], packed_val)
            _indicate_in_progress_flags[char_key] = True
            print(f"BLE Manager: Sent initial {char_key.capitalize()} Indication value: {value_to_send}")
        elif _notify_enabled_flags[char_key]:
            print(f"BLE Manager: Attempting initial NOTIFY for {char_key}: conn_h={_conn_handle}, val_h={_char_handles[char_key]}, data={ubinascii.hexlify(packed_val)}")
            _ble_instance.gatts_notify(_conn_handle, _char_handles[char_key], packed_val)
            print(f"BLE Manager: Sent initial {char_key.capitalize()} Notify value: {value_to_send}")

    except OSError as e:
        print(f"BLE Manager: Error sending initial {char_key.capitalize()} value: {e}")
        if e.args[0] == 104: _conn_handle = None # Handle disconnect
    except Exception as e:
        print(f"BLE Manager: Unexpected error sending initial {char_key.capitalize()} value: {e}")


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
        handles_tuple_outer = _ble_instance.gatts_register_services((_ENV_SENSE_SERVICE_DEF,))
        service_handles = handles_tuple_outer[0]

        _char_handles['temp'] = service_handles[0]; _char_handles['temp_cccd'] = service_handles[1]
        _char_handles['humid'] = service_handles[2]; _char_handles['humid_cccd'] = service_handles[3]
        _char_handles['lux'] = service_handles[4]; _char_handles['lux_cccd'] = service_handles[5]
        _char_handles['noise'] = service_handles[6]; _char_handles['noise_cccd'] = service_handles[7]
        
        print("BLE Manager: GATT Service Registered.")
        print(f"  Temp Handle Value: {_char_handles['temp']}, CCCD: {_char_handles['temp_cccd']}")
        print(f"  Humid Handle Value: {_char_handles['humid']}, CCCD: {_char_handles['humid_cccd']}")
        print(f"  Lux Handle Value: {_char_handles['lux']}, CCCD: {_char_handles['lux_cccd']}")
        print(f"  Noise Handle Value: {_char_handles['noise']}, CCCD: {_char_handles['noise_cccd']}")
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

    for char_key in ['temp', 'humid', 'lux', 'noise']:
        packed_val = None
        value_to_send = _cached_sensor_values[char_key]
        
        try:
            if char_key == 'temp':
                packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
            elif char_key == 'humid':
                packed_val = _pack_uint16_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
            elif char_key == 'lux':
                packed_val = _pack_uint24_scaled(value_to_send if value_to_send is not None and value_to_send > -990 else None, 100)
            elif char_key == 'noise':
                packed_val = _pack_sint16_scaled(value_to_send if value_to_send is not None and value_to_send >= 0 else None, 10)

            if packed_val is None: continue # Skip if no valid data to pack

            # Prefer Indication if enabled and not already in progress for this characteristic
            if _indicate_enabled_flags[char_key] and not _indicate_in_progress_flags[char_key]:
                print(f"BLE Manager: Attempting INDICATION for {char_key}: conn_h={_conn_handle}, val_h={_char_handles[char_key]}, data={ubinascii.hexlify(packed_val)}")
                _ble_instance.gatts_indicate(_conn_handle, _char_handles[char_key], packed_val)
                _indicate_in_progress_flags[char_key] = True # Mark as in progress
            # Else, if notification is enabled, send notification
            elif _notify_enabled_flags[char_key]:
                print(f"BLE Manager: Attempting NOTIFY for {char_key}: conn_h={_conn_handle}, val_h={_char_handles[char_key]}, data={ubinascii.hexlify(packed_val)}")
                _ble_instance.gatts_notify(_conn_handle, _char_handles[char_key], packed_val)
                
        except OSError as e:
            print(f"BLE Manager: Error sending data for {char_key.capitalize()}: {e}")
            if e.args[0] == 104: # ECONNRESET
                _conn_handle = None
                print("BLE Manager: Connection reset during send, handle cleared.")
                # Reset all flags as connection is lost
                for key_in_loop in _notify_enabled_flags:
                    _notify_enabled_flags[key_in_loop] = False
                    _indicate_enabled_flags[key_in_loop] = False
                    _indicate_in_progress_flags[key_in_loop] = False
                break # Exit loop as connection is gone
        except Exception as e:
            print(f"BLE Manager: Unexpected error sending data for {char_key.capitalize()}: {e}")


def is_connected():
    global _conn_handle
    return _conn_handle is not None

def is_active():
    global _ble_instance
    return _ble_instance is not None and _ble_instance.active()

def deinitialize():
    global _ble_instance, _conn_handle
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
        except Exception as e:
            print(f"BLE Manager: Error deinitializing BLE: {e}")
