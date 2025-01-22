THERMAL_SCANNER_ENABLED = False

def get_temperature():
    # No need to check for the flag here anymore as it is
    # handled in the routes where this function is called.
    return None

def is_thermal_scanner_enabled():
    return THERMAL_SCANNER_ENABLED

def toggle_thermal_scanner():
    # This function can remain to allow toggling the flag,
    # but it won't have any practical effect when the hardware 
    # interaction code is removed.
    global THERMAL_SCANNER_ENABLED
    THERMAL_SCANNER_ENABLED = not THERMAL_SCANNER_ENABLED