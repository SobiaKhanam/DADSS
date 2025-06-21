from rest_framework import status

from common.fields import SmartRelatedField
from dadss_server.parent import *
from .models import *



class MerVesselImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerVesselImage
        fields = '__all__'
        read_only_fields = ['vi_key']


class MerVesselImageViewSet(CustomViewSet):
    queryset = MerVesselImage.objects.all().order_by('-vi_key')
    serializer_class = MerVesselImageSerializer

    def create(self, request, *args, **kwargs):
        vi_vessel = request.data.get('vi_vessel')
        created_instances = []

        # Loop through the indices and create image instances
        index = 0
        while f'vi_image[{index}]' in request.data:
            image_data = {
                'vi_vessel': vi_vessel,
                'vi_image': request.data[f'vi_image[{index}]'],
                'vi_remarks': request.data.get(f'vi_remarks[{index}]', '')
            }
            serializer = self.get_serializer(data=image_data)
            serializer.is_valid(raise_exception=True)
            created_instance = serializer.save()
            created_instances.append(created_instance)
            index += 1

        return Response(self.get_serializer(created_instances, many=True).data, status=status.HTTP_201_CREATED)


class MerchantVesselListSerializer(serializers.ModelSerializer):
    mv_ship_type = SmartRelatedField(model=MerchantType)

    class Meta:
        model = Merchant_Vessel
        # fields = ['mv_key', 'mv_mmsi', 'mv_imo', 'mv_ship_type', 'mv_ship_id', 'mv_ship_name',
        #           'mv_flag', 'mv_ais_type_summary', 'mv_type_name']
        fields = '__all__'


class MerchantVesselMinimalSerializer(MerchantVesselListSerializer):
    mv_images = MerVesselImageSerializer(many=True, required=False)

    class Meta:
        model = Merchant_Vessel
        # fields = MerchantVesselListSerializer.Meta.fields + ['mv_images']
        fields = '__all__'


class MerVesselSerializer(MerchantVesselMinimalSerializer):
    mv_data_source = serializers.HiddenField(default='registered_merchant')

    class Meta:
        model = Merchant_Vessel
        fields = '__all__'
        read_only_fields = ['mv_key']

    def create(self, validated_data):
        mv_imo = validated_data.get('mv_imo')
        existing_vessel = Merchant_Vessel.objects.filter(mv_imo=mv_imo).first()
        if existing_vessel:
            raise serializers.ValidationError({'error': 'IMO is already registered'})
        aisvessel = Merchant_Vessel.objects.create(**validated_data)
        return aisvessel


class MerVesselViewSet(CustomViewSet):
    queryset = Merchant_Vessel.objects.select_related('mv_ship_type').order_by('-mv_key')
    serializer_class = MerVesselSerializer
    list_serializer_class = MerchantVesselListSerializer
    filterset_fields = {
        'mv_key': ['exact'],
        'mv_imo': ['exact'],
        'mv_ship_id': ['exact'],
        'mv_ship_name': ['exact'],
        'mv_type_name': ['exact'],
        'mv_data_source': ['exact'],
    }
    search_fields = ['mv_imo', 'mv_ship_name', 'mv_mmsi', 'mv_type_name']


