from rest_framework.generics import get_object_or_404

from common.childMixin import ChildRelationMixin
from common.fields import SmartRelatedField, SmartM2MRelatedField
from common.mixin import WeatherMixin
from common.views import WeatherSerializer
from dadss_server.global_permissions import CustomDjangoModelPermission
from dadss_server.parent import *
from .mer_vessel import MerVesselSerializer, MerchantVesselMinimalSerializer
from .models import *


class MSRgoodSerializer(serializers.ModelSerializer):
    msrg_key = serializers.IntegerField(required=False)

    class Meta:
        model = MerSrgoods
        exclude = ['msrg_msr_key']


class MSRTripSerializer(serializers.ModelSerializer):
    msr2_lpoc = SmartRelatedField(model=Port)
    msr2_npoc = SmartRelatedField(model=Port)

    class Meta:
        model = MerSreports2
        exclude = ['msr_key']


class MerSpecialReportListSerializer(serializers.ModelSerializer):
    mv_ship_name = serializers.CharField(source='msr_mv_key.mv_ship_name', read_only=True)
    msr_position = PositionField()
    msr_patroltype = SmartM2MRelatedField(model=PatrolType)
    msr_action = SmartRelatedField(model=ActionType)

    class Meta:
        model = MerSreports
        fields = ['msr_key', 'msr_dtg', 'msr_position', 'mv_ship_name', 'msr_patroltype', 'msr_action', 'msr_pf_id']


class MerSpecialReportSerializer(MerSpecialReportListSerializer, WeatherMixin, ChildRelationMixin):
    trip_source = 'merchant_trip'
    child = MerSreports2
    tripDetails = MSRTripSerializer(many=False, source=trip_source)
    goodDetails = MSRgoodSerializer(many=True, source='msreport_goods')

    mer_vessel = MerchantVesselMinimalSerializer(source='msr_mv_key', read_only=True)

    weather = WeatherSerializer(source='msr_w_key', allow_null=True)
    msr_w_key = serializers.PrimaryKeyRelatedField(
        queryset=Weather.objects.all(),
        required=False,
        write_only=True  # ✅ this hides it from the output
    )

    CHILD_MODELS = [
        ('msreport_goods', MerSrgoods, 'msrg_msr_key', 'msrg_key', {}, []),
        ('msr_patroltypes', MSReportPatroltype, 'msreport', 'msp_key', {}, [], True),
    ]

    class Meta:
        model = MerSreports
        fields = '__all__'
        read_only_fields = ['msr_key', 'msr_rdt']

    def create(self, validated_data):
        patroltypes = validated_data.pop("msr_patroltype", [])
        trip = validated_data.pop(self.trip_source, None)
        goods = validated_data.pop('msreport_goods', [])
        weather_data = validated_data.pop('msr_w_key', None)
        msr_position = validated_data.get('msr_position')
        msr_dtg = validated_data.get('msr_dtg')

        special_report = MerSreports.objects.create(**validated_data)
        self.process_weather(special_report, 'msr_w_key', weather_data,
                             msr_position, msr_dtg, 'MSreport')
        special_report.save()

        self.child.objects.create(**trip, msr_key=special_report)

        self._handle_children(special_report, msr_patroltypes=patroltypes, msreport_goods=goods)

        return special_report

    def update(self, instance, validated_data):
        try:
            patroltypes = validated_data.pop("msr_patroltype", instance.msr_patroltype)
            trip_data = validated_data.pop('merchant_trip', None)
            if trip_data:
                trip_instance = instance.merchant_trip
                for attr, value in trip_data.items():
                    setattr(trip_instance, attr, value)
                trip_instance.save()
            goods = validated_data.pop('msreport_goods', [])

            weather_data = validated_data.pop('msr_w_key', None)
            msr_position = validated_data.get('msr_position', instance.msr_position)
            msr_dtg = validated_data.get('msr_dtg', instance.msr_dtg)

            self.process_weather(instance, 'msr_w_key', weather_data,
                                 msr_position, msr_dtg, 'MSreport')

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            self._handle_children(instance, msr_patroltypes=patroltypes, msreport_goods=goods)
            return instance

        except Exception as e:
            print(e)
            return instance


class MerSpecialReportViewSet(CustomViewSet):
    queryset = (MerSreports.objects.select_related('msr_action', 'msr_mv_key',
                                                  #  'merchant_trip',
                                                  # 'msr_w_key'
                                                   )
                .prefetch_related('msr_patroltype')
                .all())
    serializer_class = MerSpecialReportSerializer
    list_serializer_class = MerSpecialReportListSerializer
    permission_classes = [CustomDjangoModelPermission]
    filterset_fields = '__all__'
    ordering = ['-msr_key']

    @action(methods=['get'], detail=False, url_path='mv_key/(?P<msr_mv_key>[^/.]+)')
    def mv_key(self, request, pk=None, msr_mv_key=None):
        """
            Redirect to Merchant Vessel object if special report is empty.
        """
        tripDetails = 'tripDetails'
        goodDetails = 'goodDetails'

        mvessel_object = get_object_or_404(Merchant_Vessel, mv_key=msr_mv_key)
        mvessel = MerVesselSerializer(mvessel_object, many=False, context={'request': request}).data

        filter_query = self.queryset.filter(msr_mv_key=msr_mv_key).last()
        if filter_query is None:
            mervessel_updated = {
                'mv_key': mvessel['mv_key'],
                "mer_vessel": mvessel
            }
            return Response(mervessel_updated)
        else:
            sreport = MerSpecialReportSerializer(filter_query, many=False).data
            sreport_updated = {'msr_key': sreport['msr_key'], 'msr_mv_key': sreport['msr_mv_key'],
                               'msr_movement': sreport['msr_movement'], goodDetails: sreport[goodDetails],
                               tripDetails: sreport[tripDetails], 'mer_vessel': mvessel}
            return Response(sreport_updated)
