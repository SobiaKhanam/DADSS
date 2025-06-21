from rest_framework import serializers
from .models import PersonImages, Person, Boats


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ['id', 'name', 'cnic_no', 'cell_no']


class BoatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Boats
        fields = ['id', 'reg_no', 'boat_name', 'boat_type', 'boat_location']


class PersonImagesSerializer(serializers.ModelSerializer):
    person_id = PersonSerializer(read_only=True)
    boat_id = BoatSerializer(read_only=True)

    class Meta:
        model = PersonImages
        fields = ['id', 'photo', 'created_at', 'person_id', 'boat_id']
