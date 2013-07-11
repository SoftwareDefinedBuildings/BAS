from django.contrib.gis.db import models
from django.conf import settings
from serialization import Serializable
from django.core.files.storage import FileSystemStorage
import os

# Create your models here.

class Building(models.Model, Serializable):
    name = models.CharField(max_length=50, unique=True)
    polygon = models.PolygonField()
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

class Floor(models.Model, Serializable):
    name = models.CharField(max_length=50, unique=True)
    polygon = models.PolygonField(default="POLYGON((-12.12890625 58.768200159239576, 1.1865234375 58.49369382056807, 5.537109375 50.2612538275847, -12.9638671875 49.18170338770662, -12.12890625 58.768200159239576))")
    building = models.ForeignKey(Building, related_name='floors')
    floorplan = models.ImageField(upload_to='uploads')
    objects = models.GeoManager()

    def image_tag(self):
        print self.floorplan
        return u'<img src="/media/{0}" />'.format(self.floorplan)
    image_tag.short_description = 'Image'
    image_tag.allow_tags = True

    # on save, set the floor area to the same coordinates as the building
    def save(self):
        if self.pk is None:
            self.polygon = self.building.polygon
        super(Floor, self).save()

    def __unicode__(self):
        return self.name

class Area(models.Model, Serializable):
    name = models.CharField(max_length=50, unique=True)
    polygon = models.PolygonField()
    floor = models.ForeignKey(Floor, related_name='areas')
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

class Node(models.Model, Serializable):
    smap_uuid = models.CharField(max_length=100, unique=True) # should I use a UUID field here?
    point = models.PointField()
    area = models.ForeignKey(Area, related_name='nodes')
    objects = models.GeoManager()

    def __unicode__(self):
        return self.smap_uuid
