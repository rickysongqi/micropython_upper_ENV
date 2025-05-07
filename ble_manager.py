import struct

import bluetooth
import ubinascii
from micropython import const

# --- BLE Constants ---
# BLE IRQ Events
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4) # Custom definition might be needed

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

# Define the structure of our Environmental Sensing Service
_ENV_SENSE_SERVICE_DEF = (
    _ENV_SENSE_UUID,
    (
        (_TEMP_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,),
        (_HUMID_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,),
        (_LUX_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,),
        (_NOISE_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY,),
    ),
)

# --- Module-level BLE State ---
_ble_instance = None
_conn_handle = None
_adv_payload_data = None
_adv_interval_current_us = 100000 # Default, can be overridden during init

# Handles for characteristics
_char_handles = {
    'temp': None,
    'humid': None,
    'lux': None,
    'noise': None,
}

_notify_enabled_flags = {
    'temp': False,
    'humid': False,
    'lux': False,
    'noise': False,
}

# Cache for sensor values for IRQ use (especially for initial notify and read requests)
_cached_sensor_values = {
    'temp': None,
    'humid': None,
    'lux': None,
    'noise': None,
}

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
    global _ble_instance, _conn_handle, _notify_enabled_flags, _char_handles
    global _cached_sensor_values, _adv_payload_data, _adv_interval_current_us

    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle_val, _, addr = data
        _conn_handle = conn_handle_val
        addr_str = ubinascii.hexlify(addr, ':').decode()
        print(f"BLE Manager: Connected: handle={_conn_handle}, addr={addr_str}")
        for key in _notify_enabled_flags:
            _notify_enabled_flags[key] = False

    elif event == _IRQ_CENTRAL_DISCONNECT:
        conn_handle_val, _, _ = data
        if conn_handle_val == _conn_handle:
            print(f"BLE Manager: Disconnected: handle={conn_handle_val}")
            _conn_handle = None
            if _ble_instance is not None and _ble_instance.active() and _adv_payload_data is not None:
                print("BLE Manager: Restarting advertising...")
                try:
                    _ble_instance.gap_advertise(_adv_interval_current_us, adv_data=_adv_payload_data)
                except Exception as e:
                    print(f"BLE Manager: Error restarting advertising: {e}")

    elif event == _IRQ_GATTS_WRITE:
        conn_handle_val, attr_handle = data
        value_written = _ble_instance.gatts_read(attr_handle)
        notify_state = value_written[0] == 1

        char_map = {
            _char_handles['temp'] + 1: 'temp',
            _char_handles['humid'] + 1: 'humid',
            _char_handles['lux'] + 1: 'lux',
            _char_handles['noise'] + 1: 'noise',
        }
        
        char_key = char_map.get(attr_handle)
        if char_key:
            _notify_enabled_flags[char_key] = notify_state
            print(f"BLE Manager: {char_key.capitalize()} Notify: {'Enabled' if notify_state else 'Disabled'}")
            if notify_state and _conn_handle is not None:
                try:
                    if char_key == 'temp':
                        packed_val = _pack_sint16_scaled(_cached_sensor_values['temp'] if _cached_sensor_values['temp'] is not None and _cached_sensor_values['temp'] > -990 else None, 100)
                        _ble_instance.gatts_notify(_conn_handle, _char_handles['temp'], packed_val)
                    elif char_key == 'humid':
                        packed_val = _pack_uint16_scaled(_cached_sensor_values['humid'] if _cached_sensor_values['humid'] is not None and _cached_sensor_values['humid'] > -990 else None, 100)
                        _ble_instance.gatts_notify(_conn_handle, _char_handles['humid'], packed_val)
                    elif char_key == 'lux':
                        packed_val = _pack_uint24_scaled(_cached_sensor_values['lux'] if _cached_sensor_values['lux'] is not None and _cached_sensor_values['lux'] > -990 else None, 100)
                        _ble_instance.gatts_notify(_conn_handle, _char_handles['lux'], packed_val)
                    elif char_key == 'noise':
                        packed_val = _pack_sint16_scaled(_cached_sensor_values['noise'] if _cached_sensor_values['noise'] is not None and _cached_sensor_values['noise'] >= 0 else None, 10)
                        _ble_instance.gatts_notify(_conn_handle, _char_handles['noise'], packed_val)
                    print(f"BLE Manager: Sent initial {char_key.capitalize()} Notify value: {_cached_sensor_values[char_key]}")
                except OSError as e:
                    print(f"BLE Manager: Error sending initial {char_key.capitalize()} Notify: {e}")
                    if e.args[0] == 104: _conn_handle = None # Handle disconnect
                except Exception as e:
                    print(f"BLE Manager: Unexpected error sending initial {char_key.capitalize()} Notify: {e}")

    elif event == _IRQ_GATTS_READ_REQUEST:
        conn_handle_val, attr_handle = data
        print(f"BLE Manager: Read Request: handle={conn_handle_val}, attr={attr_handle}")
        if attr_handle == _char_handles['temp']:
            _ble_instance.gatts_write(_char_handles['temp'], _pack_sint16_scaled(_cached_sensor_values['temp'] if _cached_sensor_values['temp'] is not None and _cached_sensor_values['temp'] > -990 else None, 100))
        elif attr_handle == _char_handles['humid']:
            _ble_instance.gatts_write(_char_handles['humid'], _pack_uint16_scaled(_cached_sensor_values['humid'] if _cached_sensor_values['humid'] is not None and _cached_sensor_values['humid'] > -990 else None, 100))
        elif attr_handle == _char_handles['lux']:
            _ble_instance.gatts_write(_char_handles['lux'], _pack_uint24_scaled(_cached_sensor_values['lux'] if _cached_sensor_values['lux'] is not None and _cached_sensor_values['lux'] > -990 else None, 100))
        elif attr_handle == _char_handles['noise']:
            _ble_instance.gatts_write(_char_handles['noise'], _pack_sint16_scaled(_cached_sensor_values['noise'] if _cached_sensor_values['noise'] is not None and _cached_sensor_values['noise'] >= 0 else None, 10))

# --- Public API ---
def initialize(device_name, adv_interval_us=100000):
    global _ble_instance, _adv_payload_data, _adv_interval_current_us
    global _char_handles

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
        handles_tuple = _ble_instance.gatts_register_services((_ENV_SENSE_SERVICE_DEF,))
        _char_handles['temp'] = handles_tuple[0][0]
        _char_handles['humid'] = handles_tuple[0][1]
        _char_handles['lux'] = handles_tuple[0][2]
        _char_handles['noise'] = handles_tuple[0][3]
        print("BLE Manager: GATT Service Registered.")
        print(f"  Temp Handle: {_char_handles['temp']}")
        print(f"  Humid Handle: {_char_handles['humid']}")
        print(f"  Lux Handle: {_char_handles['lux']}")
        print(f"  Noise Handle: {_char_handles['noise']}")
    except Exception as e:
        print(f"BLE Manager: Error registering GATT services: {e}")
        _ble_instance.active(False)
        _ble_instance = None
        return False

    _ble_instance.irq(_irq_handler)
    print("BLE Manager: IRQ handler set.")

    print("BLE Manager: Configuring advertisement...")
    payload = bytearray()
    payload.extend(b'\x02\x01\x06') # Flags: LE General Discoverable Mode
    payload.extend(b'\x03\x03\x1A\x18') # Service UUID List: _ENV_SENSE_UUID (0x181A)
    name_bytes = bytes(device_name, 'utf-8')
    payload.extend(bytes([len(name_bytes) + 1, 0x09])) # Type: Complete Local Name
    payload.extend(name_bytes)
    _adv_payload_data = payload
    
    try:
        _ble_instance.gap_advertise(_adv_interval_current_us, adv_data=_adv_payload_data)
        print(f"BLE Manager: Advertising started as '{device_name}'.")
        return True
    except Exception as e:
        print(f"BLE Manager: Error starting advertising: {e}")
        # Fallback might be needed
        try:
             print("BLE Manager: Advertising fallback: name only")
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
             _ble_instance.active(False)
             _ble_instance = None
             return False

def update_sensor_data_and_notify(temp_val, humid_val, lux_val, noise_rms_val):
    global _cached_sensor_values, _ble_instance, _conn_handle, _notify_enabled_flags, _char_handles

    _cached_sensor_values['temp'] = temp_val
    _cached_sensor_values['humid'] = humid_val
    _cached_sensor_values['lux'] = lux_val
    _cached_sensor_values['noise'] = noise_rms_val

    if _conn_handle is None or _ble_instance is None:
        return

    try:
        if _notify_enabled_flags['temp']:
            packed_temp = _pack_sint16_scaled(temp_val if temp_val is not None and temp_val > -990 else None, 100)
            _ble_instance.gatts_notify(_conn_handle, _char_handles['temp'], packed_temp)
        
        if _notify_enabled_flags['humid']:
            packed_hum = _pack_uint16_scaled(humid_val if humid_val is not None and humid_val > -990 else None, 100)
            _ble_instance.gatts_notify(_conn_handle, _char_handles['humid'], packed_hum)
        
        if _notify_enabled_flags['lux']:
            packed_lux = _pack_uint24_scaled(lux_val if lux_val is not None and lux_val > -990 else None, 100)
            _ble_instance.gatts_notify(_conn_handle, _char_handles['lux'], packed_lux)

        if _notify_enabled_flags['noise']:
            packed_noise = _pack_sint16_scaled(noise_rms_val if noise_rms_val is not None and noise_rms_val >= 0 else None, 10) # Scale by 10
            _ble_instance.gatts_notify(_conn_handle, _char_handles['noise'], packed_noise)
            
    except OSError as e:
        print(f"BLE Manager: Error sending notifications: {e}")
        if e.args[0] == 104: # ECONNRESET
            _conn_handle = None
            print("BLE Manager: Connection reset during notify, handle cleared.")
    except Exception as e:
        print(f"BLE Manager: Unexpected error sending notifications: {e}")

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
                _ble_instance.active(False)
                print("BLE Manager: Bluetooth deactivated.")
            _ble_instance = None
        except Exception as e:
            print(f"BLE Manager: Error deinitializing BLE: {e}")
