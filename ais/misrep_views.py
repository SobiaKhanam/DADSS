from rest_framework import serializers

from common.fields import SmartRelatedField
from common.models import FishingType, Port, MerchantType
from .models import MissionReport, MRDetails, Merchant_Vessel, MRFDensity, MRFishing
from dadss_server.parent import CustomViewSet, PositionField
from dadss_server.global_permissions import CustomDjangoModelPermission


class MRDetailsSerializer(serializers.ModelSerializer):
    mrd_position = PositionField()
    mrd_key = serializers.IntegerField(required=False)
    mrd_npoc = SmartRelatedField(model=Port, required=False, allow_null=True)
    mrd_lpoc = SmartRelatedField(model=Port, required=False, allow_null=True)
    mrd_vessel_type = SmartRelatedField(model=MerchantType, required=False, allow_null=True)

    class Meta:
        model = MRDetails
        fields = '__all__'
        read_only_fields = ['mrd_mr_key', 'mrd_mv_key']

class MRFDensitySerializer(serializers.ModelSerializer):
    mrfd_position = PositionField()
    mrfd_key = serializers.IntegerField(required=False)
    mrfd_type = SmartRelatedField(model=FishingType)

    class Meta:
        model = MRFDensity
        fields = '__all__'
        read_only_fields = ['mrfd_mr_key']

class MRFishingSerializer(serializers.ModelSerializer):
    mrf_position = PositionField()
    mrf_key = serializers.IntegerField(required=False)
    mrf_type = SmartRelatedField(model=FishingType)

    class Meta:
        model = MRFishing
        fields = '__all__'
        read_only_fields = ['mrf_mr_key']


class MreportSerializer(serializers.ModelSerializer):
    misrepdetails = MRDetailsSerializer(many=True, source='mrdetails')
    misrepfishing = MRFishingSerializer(many=True, source='mrfishing')
    misrepfdensity = MRFDensitySerializer(many=True, source='mrfdensity')

    class Meta:
        model = MissionReport
        fields = '__all__'
        read_only_fields = ['mr_key', 'mr_rdt']

    # Should not register new merchant vessels from here

    def create(self, validated_data):
        misrepdetails = validated_data.pop('mrdetails')
        misrepfishing = validated_data.pop('mrfishing')
        misrepfdensity = validated_data.pop('mrfdensity')
        mreport = MissionReport.objects.create(**validated_data)

        for fishing in misrepfishing:
            MRFishing.objects.create(**fishing, mrf_mr_key=mreport)
        for density in misrepfdensity:
            MRFDensity.objects.create(**density, mrfd_mr_key=mreport)

        for mrdetails in misrepdetails:
            mrd_mmsi = mrdetails.get('mrd_mmsi')
            # mrd_vessel_type = mrdetails.get('mrd_vessel_type')
            # mrd_vessel_name = mrdetails.get('mrd_vessel_name')
            merchant_vessel = Merchant_Vessel.objects.filter(mv_mmsi=mrd_mmsi).first()

            # if not merchant_vessel:
            #     merchant_vessel = Merchant_Vessel.objects.create(
            #         mv_mmsi=mrd_mmsi,
            #         mv_ship_name=mrd_vessel_name,
            #         mv_type_name=mrd_vessel_type.mt_name,
            #         mv_ship_type=mrd_vessel_type,
            #         mv_data_source="misrep"
            #     )
            MRDetails.objects.create(mrd_mr_key=mreport, mrd_mv_key=merchant_vessel, **mrdetails)

        return mreport

    def update(self, instance, validated_data):
        try:
            mrdetails_data = validated_data.pop('mrdetails', [])
            mrfishing_data = validated_data.pop('mrfishing', [])
            mrfdensity_data = validated_data.pop('mrfdensity', [])

            # --- Update MRDetails ---
            existing_detail_keys = [item.get('mrd_key') for item in mrdetails_data if item.get('mrd_key')]
            instance.mrdetails.exclude(mrd_key__in=existing_detail_keys).delete()

            for data in mrdetails_data:
                mrd_mmsi = data.get('mrd_mmsi')
                merchant_vessel = None
                if mrd_mmsi:
                    # mrd_vessel_type = data.get('mrd_vessel_type')
                    # mrd_vessel_name = data.get('mrd_vessel_name')
                    merchant_vessel = Merchant_Vessel.objects.filter(mv_mmsi=mrd_mmsi).first()
                    # if not merchant_vessel:
                    #     merchant_vessel = Merchant_Vessel.objects.create(
                    #         mv_mmsi=mrd_mmsi,
                    #         mv_ship_name=mrd_vessel_name,
                    #         mv_type_name=mrd_vessel_type.mt_name,
                    #         mv_ship_type=mrd_vessel_type,
                    #         mv_data_source="misrep"
                    #     )
                mrd_key = data.get('mrd_key')
                if mrd_key is None:
                    MRDetails.objects.create(mrd_mr_key=instance, mrd_mv_key=merchant_vessel, **data)
                    # MRDetails.objects.create(mrd_mr_key=instance, **data)
                else:
                    obj = MRDetails.objects.get(mrd_key=mrd_key, mrd_mr_key=instance)
                    if mrd_mmsi:
                        obj.mrd_mv_key = merchant_vessel
                    for attr, value in data.items():
                        setattr(obj, attr, value)
                    obj.save()

            # --- Update MRFishing ---
            existing_fishing_keys = [item.get('mrf_key') for item in mrfishing_data if item.get('mrf_key')]
            instance.mrfishing.exclude(mrf_key__in=existing_fishing_keys).delete()

            for data in mrfishing_data:
                mrf_key = data.get('mrf_key')
                if mrf_key is None:
                    MRFishing.objects.create(mrf_mr_key=instance, **data)
                else:
                    obj = MRFishing.objects.get(mrf_key=mrf_key, mrf_mr_key=instance)
                    for attr, value in data.items():
                        setattr(obj, attr, value)
                    obj.save()

            # --- Update MRFDensity ---
            existing_density_keys = [item.get('mrfd_key') for item in mrfdensity_data if item.get('mrfd_key')]
            instance.mrfdensity.exclude(mrfd_key__in=existing_density_keys).delete()

            for data in mrfdensity_data:
                mrfd_key = data.get('mrfd_key')
                if mrfd_key is None:
                    MRFDensity.objects.create(mrfd_mr_key=instance, **data)
                else:
                    obj = MRFDensity.objects.get(mrfd_key=mrfd_key, mrfd_mr_key=instance)
                    for attr, value in data.items():
                        setattr(obj, attr, value)
                    obj.save()

            # Update base MissionReport fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            return instance

        except Exception as e:
            print("Update failed:", e)
            return instance


class MreportViewSet(CustomViewSet):
    queryset = MissionReport.objects.all()
    serializer_class = MreportSerializer
    # permission_classes = [CustomDjangoModelPermission]

    filterset_fields = {
        'mr_key': ['exact', 'gte', 'lte'],
        'mr_pf_id': ['exact'],
        'mr_rdt': ['exact', 'gte', 'lte', 'gt', 'lt'],
        'mr_dtg': ['exact', 'gte', 'lte', 'gt', 'lt'],
    }
    search_fields = ['mr_pf_id']
    ordering_fields = ['mr_key', 'mr_rdt', 'mr_dtg']
    ordering = ['-mr_key']
