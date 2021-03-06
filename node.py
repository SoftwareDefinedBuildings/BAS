import uuid
import itertools
import networkx as nx
import zope.interface
import gis
import redis

geocache = redis.StrictRedis(host='localhost', port=6379, db=0)
# clean out old keys
for k in geocache.keys():
  geocache.delete(k)

def uniquify(l):
    c = itertools.count(start=1)
    if isinstance(item, Node):
        return [item.set_name(item.node_name+" "+str(c.next())) for item in l]
    else:
        raise Exception("we got here?!")
        return [item+" "+str(c.next()) for item in l]

class Node(object):
  """
  Inherited class for nodes and objects (below)
  Uses uuid as a unique identifier, has optional name
  Supports methods add_child, add_parent
  """

  class NodeList(list):
    def add_child(self, child):
      for item in self:
        item.add_child(child)

    def add_parent(self, parent):
      for item in self:
        item.add_parent(parent)

    @property
    def areas(self):
      return gis.Area.objects.filter(nodes__in=[x.link for x in self])

  def __init__(self, name, external_parents=[], external_childs=[], metadata={}, uid=None):
    """
    obj_type: string that conforms to the list of recognized object types
    container: Obj or Relational of which this object is a part
    name: string name of this object
    """
    self.node_name = name
    self.external_parents = external_parents
    self.external_childs = external_childs
    self.uid = uuid.uuid4() if not uid else uid
    if isinstance(self.uid, str):
      self.uid = uuid.UUID(self.uid)
    self.metadata = metadata
    self.tags = []

    self.link, _ = gis.NodeLink.objects.get_or_create(uuid=self.uid)

    #self.container.add_nodes(self)

  def get_name(self):
    return self.node_name

  def __str__(self):
    return self.node_name

  def __cmp__(self, other):
    # use self.uuid to compare to other objects
    if isinstance(other, Node):
      if isinstance(self.uid, uuid.UUID):
        return self.uid.__cmp__(other.uid)
      return -1
    else:
      return -1

  def __hash__(self):
    #hack to get graph copy working
    if hasattr(self,'uid'):
      return hash(self.uid)
    return object.__hash__(self)

  def set_name(self, name):
    self.name = name
    return self

  def validate(self):
    pass

  def _apply_to_multiple(fxn):
    """
    DECORATOR
    if we are applying add_child or add_parent to a list of points, then we apply the fxn to each
    of those points in turn
    """
    def apply_multiple(self, *args):
      if isinstance(args[0],list):
        for rel in args[0]:
          return fxn(self, rel)
      else: return fxn(self, *args)
    return apply_multiple

  @_apply_to_multiple
  def add_child(self, child):
    """
    Give this node a child w/n the context of it's container graph
    child: Device or Obj (which ever this object's type is)
    if the target child is part of an external container, then this
    node makes note of that
    """
    children = [child] if not isinstance(child,list) else child
    for child in children:
      if child.container != self.container:
        self.external_childs.append(child.container)
        child.external_parents.append(self.container)
        self.container.external_childs.append(child.container)
        child.container.external_parents.append(self.container)
      self.container.add_node_child(self, child)

  @_apply_to_multiple
  def add_parent(self, parent):
    """
    Give this node a parent w/n the context of it's container graph
    parent: Device or Obj (which ever this object's type is)
    if the target parent is part of an external container, then this
    node makes note of that
    """
    parents = list(parent) if not isinstance(parent,list) else parent
    for parent in parents:
      if parent.container != self.container:
        self.external_parents.append(parent.container)
        parent.external_childs.append(self.container)
        self.container.external_parents.append(parent.container)
        parent.container.external_childs.append(self.container)
      self.container.add_node_parent(self, parent)

  @classmethod
  def type(cls):
    for interface in zope.interface.implementedBy(cls):
      if interface.getName().startswith('D') or interface.getName().startswith('I'):
        return interface.getName()[1:]
    return cls.__name__

  @property
  def areas(self):
    return self.container.areas if hasattr(self.container,'areas') and not self.link.areas.all() else self.link.areas

  def __emittable__(self):
    """Returns a dictionary representation of the object (passed to Web API)"""
    import node_types
    #TODO: do caching here?
    return {
      'name': self.node_name,
      'type': self.type(),
      'uuid': str(self.uid),
      'methods': node_types.get_methods(self),
      }


class Container(nx.DiGraph):
  """
  Inheritable class for handling basic graph operations beyond what networkx provides
  """

  def __init__(self, contents):
    nx.DiGraph.__init__(self)
    self.parents = []
    self.children = []
    # TODO: can we get rid of the obj stuff?
    # if contents: for c in contents, self.add_node(c)
    if contents:
      for obj in contents:
        obj.container = self
        self.add_node(obj)

  def search(self, fn, retfn=lambda x: x):
    """
    searches dfs preorder for nodes for which the function [fn] evaluates to true
    It appends all True values to a results list, and applies [retfn] to them
    """
    if not self.nodes():
      return []
    results = []
    for nd in nx.dfs_preorder_nodes(self):
      if fn(nd):
        results.append(retfn(nd))
      #if the node is itself a container, we search it too!
      if isinstance(nd, Container):
        results.extend(nd.search(fn,retfn))
    return results

  def add_node_child(self, node, child):
    if child not in self:
      self.add_node(child)
    if not self.__contains__(node):
      self.add_edge(node,child)
    elif not self.has_edge(node,child):
      self.add_edge(node,child)

  def add_node_parent(self, node, parent):
    if parent not in self:
      self.add_node(parent)
    if not self.__contains__(node):
      self.add_edge(parent,node)
    elif not self.has_edge(parent, node):
      self.add_edge(parent,node)


class Device(Node):
  """
  Internal components of a larger object
  """
  required_setpoints = []
  required_points = []

  def __init__(self, name, uid=None):
    self.attributes = {}
    Node.__init__(self,name,uid=uid)

    self.validate()
    #print "Device",self.name, self.uid

  def validate(self):
    req = set(self.required_points)
    for k in self.attributes.keys():
        k = k.split(' ')[0]
        req.discard(k)

    if req:
        raise NotImplementedError("Required points %s are not provided for %s" %
                                  (str(list(req)), self.name))

  def set_attribute(self, att, value):
    self.attributes[att] = value

  def get_attribute(self, att):
    return self.attributes[att]

  def del_attribute(self, att):
    del self.attributes[att]

  def __getitem__(self, att):
    return self.get_attribute(att)

  def __setitem__(self, att, value):
    self.set_attribute(att, value)

  def __delitem__(self, att):
    self.del_attribute(att)

class Obj(Node, Container):
  required_setpoints = []
  required_devices = []

  def __init__(self, container, name, devices=None, uid=None):
    self.container = container
    if devices is None:
      self.devices = {}
    else:
      self.devices = dict(itertools.chain(*[zip(uniquify([k] * len(v)), uniquify(v)) if isinstance(v, list) else ((k, v),) for k, v in devices.items()]))
    for d in self.devices:
      self.devices[d].tags = d.replace(' ','_').split('_')

    Node.__init__(self, name,uid=uid)
    Container.__init__(self, self.devices.values())
    self.container.add_node(self)
    self.tags.append(self.type())

    self.validate()
    #print ">>>Object",self.name, self.uid

  def search(self, fn, retfn=lambda x: x):
    if not self.nodes():
      return []
    res = []
    for dev in self.nodes():
      if fn(dev):
        res.append(retfn(dev))
    return res

  def validate(self):
    req = set(self.required_devices)
    for k in self.devices.keys():
        k = k.split(' ')[0]
        req.discard(k)

    if req:
        raise NotImplementedError("Required devices %s are not provided for %s" %
                                  (str(list(req)), self.name))

  def add_area(self, area):
    geocache.set(str(self.uid), area)
    self.areas.add(area)

  def __getitem__(self, key):
    if key in self.devices:
      return Node.NodeList(self.devices[key]) if isinstance(self.devices[key],list) else self.devices[key]
    else:
      return Node.NodeList(filter(lambda x: x, [self.devices[k] if key in k else None for k in self.devices]))

class Relational(Container):

  def __init__(self, name, objects=[]):
    self.domain_name = name
    self.uid = uuid.uuid4()
    Container.__init__(self, objects)

  def get_name(self):
    return self.domain_name

#place holder...?
class Domain(Relational):
  pass
