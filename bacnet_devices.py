import node
import device_types
import requests
import json
from zope.interface import implements

ROOT='http://127.0.0.1:8080/data/WattStopper'

def read_point(point, root=ROOT):
  time, reading = requests.get(root + point).json['Readings'][-1]
  return reading

def write_point(point, value, type=None, root=ROOT):
    if type:
        write_multiple_points({point: {'type': type, 'value': value}})
    else:
        write_multiple_points({point: {'value': value}})

def write_multiple_points(data, root=ROOT):
    requests.post(root+'/write', json.dumps(data))


class BACnetFAN(node.Device):
  implements(device_types.DFAN)

  # required_setpoints = ['SPD']
  # required_points = ['POW']
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetCCV(node.Device):
  implements(device_types.DCCV)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetDMP(node.Device):
  implements(device_types.DDMP)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetSEN(node.Device):
  implements(device_types.DSEN)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetCHR(node.Device):
  implements(device_types.DCHR)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetPMP(node.Device):
  implements(device_types.DPMP)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetTOW(node.Device):
  implements(device_types.DTOW)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetVLV(node.Device):
  implements(device_types.DVLV)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

class BACnetHX(node.Device):
  implements(device_types.DHX)
  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point


class BACnetREL(node.Device):
  implements(device_types.DREL)

  def __init__(self, name, point):
      node.Device.__init__(self, name)
      self.point = point

  def set_brightness(self, value):
    write_point(self.point, value, type='enumerated')

  def get_brightness(self):
    return read_point(self.point)