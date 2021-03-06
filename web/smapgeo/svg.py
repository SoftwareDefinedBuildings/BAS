#!/usr/bin/env python
from django.conf import settings
from inkscape.inkex import NSS, addNS, etree
from inkscape import simplepath, simpletransform, cubicsuperpath, cspsubdiv
from inkscape import geoutil
from models import Building, Floor, Area, View, AreaMetadata, NodeLink, find_or_create
import StringIO
from PIL import Image
import os

def formatTransform(mat):
    return ("matrix(%.25g,%.25g,%.25g,%.25g,%.25g,%.25g)" % (mat[0][0], mat[1][0], mat[0][1], mat[1][1], mat[0][2], mat[1][2]))

NSS[u'geo'] = 'http://local.cs.berkeley.edu/geodata-schema'
flatness = 1.5


def regions_to_path(regions):
    ret = []
    for region in regions:
        if region == []:
            continue
        cur = []
        for pt in region:
            if cur == []:
                cur.append(['M', [pt[0], pt[1]]])
            else:
                cur.append(['L', [pt[0], pt[1]]])
        cur.append(['Z', []])

        ret.extend(cur)

    return ret


def building_to_svg(building, use_style=True, root_path="", floor_names=None, types=None, all_floors=True):
    d = etree.fromstring("""
<svg
  xmlns="http://www.w3.org/2000/svg"
  xmlns:svg="http://www.w3.org/2000/svg"
  xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
  xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
  xmlns:geo="{}">
  sodipodi:docname="{}">
</svg>
""".format(str(NSS[u'geo']), building.name)
        )
    title = d.makeelement(addNS('title', 'svg'))
    d.append(title)
    title.text = building.name

    if use_style:
        s = d.makeelement(addNS('style', 'svg'))
        d.append(s)
        s.set('type', 'text/css')
        s.text = """
          .area {
            fill: #0000ff;
            fill-opacity: 0.3;
            stroke-width: 2.0;
            stroke: #000000;
          }
        """

    max_width = 0
    max_height = 0

    if floor_names:
        floors = building.floors.filter(name__in=floor_names)
    else:
        floors = building.floors.all()
    for floor in floors:
        floor_id = floor.name.replace(' ', '_')
        f = d.makeelement(addNS('g', 'svg'))
        d.append(f)

        f.set('id', floor_id)
        f.set(addNS('groupmode', 'inkscape'), 'layer')
        f.set('class', 'floor')
        f.set(addNS('label', 'inkscape'), floor.name)

        views = floor.views.filter(name='floorplan')
        if len(views) == 0 or views[0].image is None:
            continue
        view = views[0]
        width, height = view.dimensions
        max_width = max(max_width, width)
        max_height = max(max_height, height)

        i = d.makeelement(addNS('image', 'svg'))
        f.append(i)
        i.set('x', str(0))
        i.set('y', str(0))
        i.set(addNS('href', 'xlink'),  root_path + '/smapgeo/' + view.image)

        try:
            img = Image.open(os.path.join(settings.SMAPGEO_DATA_DIR, view.image))
            width, height = img.size
            i.set('width', str(width))
            i.set('height', str(height))
        except:
            pass

        keep_floor = all_floors
        for area in floor.areas.all():
            type_entry = AreaMetadata.objects.filter(area=area, tagname='Type')
            if type_entry:
                area_type = type_entry[0].tagval
            else:
                area_type = None
            if types and area_type not in types:
                continue

            keep_floor = True

            area_id = area.name.replace(' ', '_')
            a = f.makeelement(addNS('path', 'svg'))
            f.append(a)

            a.set('id', floor_id + '__' + area_id)
            title = a.makeelement(addNS('title', 'svg'))
            a.append(title)
            title.text = area.name

            desc = a.makeelement(addNS('desc', 'svg'))
            a.append(desc)
            desc.text = "\n".join([stream.uuid for stream in area.streams.all()] +
                                  ['{}={}'.format(m.tagname, m.tagval) for m in area.metadata.all()])
            if area_type:
                a.set('class', 'area area_' + area_type)
            else:
                a.set('class', 'area')

            path = cubicsuperpath.CubicSuperPath(regions_to_path(area.get_regions()))
            simpletransform.applyTransformToPath(geoutil.inverse(view.mtx), path)
            a.set('d', cubicsuperpath.formatPath(path))

        if not keep_floor:
            d.remove(f)


    d.set('width', str(max_width))
    d.set('height', str(max_height))
    d.set('viewBox', "0 0 {} {}".format(max_width, max_height))

    output = StringIO.StringIO()
    d.getroottree().write(output)
    contents = output.getvalue()
    output.close()
    return contents


def svg_to_building(s):
    svg = etree.fromstring(s)

    name = svg.get(addNS('docname', 'sodipodi'), 'Untitled building')
    for group in svg:
        if group.tag == addNS('title', 'svg'):
            name = group.text
        elif group.tag == addNS('metadata', 'svg'):
            for metadata_node in group.iterchildren():
                if metadata_node.tag == addNS('title', 'dc'):
                    name = group.text
    name = name.strip('\n\t')

    b = find_or_create(Building, save=True, name=name)
    for group in svg:
        if group.tag == addNS('title', 'svg'):
            b.name = group.text
        elif group.tag == addNS('metadata', 'svg'):
            for metadata_node in group.iterchildren():
                if metadata_node.tag == addNS('title', 'dc'):
                    b.name = group.text
        elif group.tag == addNS('g', 'svg'):
            parse_floor(b, group)
    b.save()
    return b

def parse_floor(b, group):
    if group.get(addNS('groupmode', 'inkscape')) != 'layer':
        return
    f = find_or_create(Floor, save=True, name=group.get(addNS('label', 'inkscape'), 'Floor'), building=b)

    image = ""
    for node in group:
        if node.tag == addNS('image', 'svg'):
            image = node.get(addNS('href', 'xlink'))
            break
    else:
        return

    try:
        v = View.objects.filter(floor=f, name='floorplan')[0]
    except IndexError:
        return
    v.image = 'floor_plans/' + image.split('/')[-1]
    v.save()

    for node in group:
        if node.tag == addNS('path', 'svg'):
            parse_path(f, node)

def parse_path(f, node):
    name = "Untitled Area"
    streams = []
    tags = {}
    for subnode in node:
        if subnode.tag == addNS('title', 'svg'):
            name = subnode.text
        elif subnode.tag == addNS('desc', 'svg') and subnode.text is not None:
            for x in subnode.text.split('\n'):
                if x.strip() == '':
                    continue
                elif '=' in x:
                    tag, value = x.split('=', 1)
                    tags[tag] = value
                else:
                    streams.append(x)

    d = node.get('d')
    if d is None or d.strip()=="":
        return

    regions = []
    p = cubicsuperpath.parsePath(d)
    t = node.get('transform')
    if t is not None:
        simpletransform.applyTransformToPath(simpletransform.parseTransform(t), p)

    view = f.views.filter(name='floorplan')[0]
    simpletransform.applyTransformToPath(view.mtx, p)
    cspsubdiv.cspsubdiv(p, flatness)
    for sp in p:
        region = []
        for pt in sp:
            region.append([pt[1][0], pt[1][1]])
        while len(region) > 1 and region[0] == region[-1]:
            region.pop() #Remove repeated last coordinate
        region.append(region[0])
        regions.append(region)
    a = find_or_create(Area, save=False, floor=f, name=name)
    a.set_regions(regions)
    a.save()
    
    a.streams.clear()
    for uuid in streams:
        try:
            stream = NodeLink.objects.get(uuid=uuid)
            a.streams.add(stream)
        except:
            print "sMAP stream {} not found".format(uuid)
    for tag, value in tags.items():
        m = find_or_create(AreaMetadata, save=False, area=a, tagname=tag)
        m.tagval = value
        m.save()
    a.name = name
    a.view = f.views.filter(name='floorplan')[0]
    a.save()
