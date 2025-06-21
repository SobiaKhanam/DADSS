from django.db import models
from django.utils import timezone


class Boats(models.Model):
    id = models.BigAutoField(primary_key=True)
    reg_no = models.CharField(max_length=100, blank=True, null=True)
    boat_name = models.CharField(max_length=100, blank=True, null=True)
    boat_type = models.CharField(max_length=100, blank=True, null=True)
    boat_location = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'boats'


class Person(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    cnic_no = models.CharField(max_length=100, blank=True, null=True)
    cell_no = models.CharField(max_length=100, blank=True, null=True)
    boat_id = models.ForeignKey('Boats', on_delete=models.CASCADE, db_column='boat_id')

    class Meta:
        managed = False
        db_table = 'person'


class PersonImages(models.Model):
    id = models.BigAutoField(primary_key=True)
    boat_id = models.ForeignKey('Boats', on_delete=models.CASCADE, db_column='boat_id')
    person_id = models.ForeignKey('Person', on_delete=models.CASCADE, db_column='person_id')
    photo = models.ImageField(upload_to='person_images/', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, default=timezone.now)

    class Meta:
        managed = False
        db_table = 'person_images'
