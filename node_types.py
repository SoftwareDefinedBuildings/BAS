abbreviations = {
    'DIS' : 'Discharge',
    'AIR' : 'Air',
    'TMP' : 'Temperature',
    'SEN' : 'Sensor',
    'SPD' : 'Speed',
    'CMD' : 'Point of Actuation',
    'RET' : 'Return',
    'MIX' : 'Mixed',
    'ZON' : 'Zone',
    'SPT' : 'Setpoint',
    'OUT' : 'Outside',
    'DMP' : 'Damper',
    'HUM' : 'Humidity',
    'PRS' : 'Pressure',
    'FLW' : 'Flow',
    'POW' : 'Power',
    'CO2' : 'Carbon Dioxide',
    'EXH' : 'Exhaust',
    'FAN' : 'Fan',
    'COO' : 'Cooling',
    'VLV' : 'Valve',
    'AHU' : 'Air Handler',
    'CCV' : 'Cooling Coil',
    'CWL' : 'Cold Water Loop',
    'HWL' : 'Hot Water Loop',
    'REL' : 'Relay',
    'HI'  : 'High',
    'LO'  : 'Low',
    'LIG' : 'Light',
    }

def get_interface(s):
  """ Get the interface for a given string, e.g. 'AHU' """
  import driver_types
  return getattr(driver_types, 'D' + s)

def list_interfaces():
  """ Returns a list of all supported interfaces identified in type_dict """
  import driver_types
  return [ getattr(driver_types, k) for k in driver_types.__dict__.keys() if k.isupper() and k.startswith('D') ]

def list_classes():
  import classes
  import node
  return [v for v in classes.__dict__.values() if type(v) == type and issubclass(v, node.Obj)]

def list_drivers():
  import bacnet_drivers
  import node
  return [v for v in bacnet_drivers.__dict__.values() if type(v) == type and issubclass(v, node.Device)]

def list_tags(targ=''):
  """ Returns a list of all tags"""
  tags = set()
  for cls in list_classes():
    if targ and not cls.type() == targ:
        continue
    tags |= set(cls.required_devices)
  for driver in list_drivers():
    if targ and not driver.type() == targ:
        continue
    tags |= set(driver.required_points)
  return list(tags)

def list_types():
  """ Returns a list of all types"""
  types = []
  types.extend(x.type() for x in list_classes())
  types.extend(x.type() for x in list_drivers())
  return types

def get_tag_name(tag):
  """ convert something like DIS_AIR_TMP_SEN to Discharge Air Temp Sensor """
  #convert tag to a list 
  tag = tag.split("_") if "_" in tag else [tag]
  classification = [abbreviations[prefix] for prefix in tag if prefix in abbreviations ]
  return " ".join(classification)

def get_required_setpoints(s):
  """ Return list of required setpoints for a given string e.g. 'AH' """
  import classes, bacnet_drivers
  if s in classes.__dict__:
    return getattr(classes, s).required_setpoints
  else:
    return getattr(bacnet_drivers, s).required_setpoints

def get_required_points(s):
  """ Return list of required points for a given string e.g. 'AH' """
  import classes, bacnet_drivers
  if s in classes.__dict__:
      return getattr(classes, s).required_drivers
  else:
    return getattr(bacnet_drivers, s).required_points

