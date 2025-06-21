from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from dadss_server.parent import *
from .mer_special_report import MerSpecialReportListSerializer
from .mer_vessel import MerchantVesselMinimalSerializer
from .models import *


class TripDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip_Details
        fields = '__all__'
        read_only_fields = ['mtd_key', 'mtd_mt_key']


class MerVesselTripSerializer(serializers.ModelSerializer):
    trip_details = TripDetailsSerializer(source='tripdetails', many=True, required=False)

    class Meta:
        model = Merchant_Trip
        fields = '__all__'
        read_only_fields = ['mt_key', 'mt_mv_key']


class MerchantVesselBundleSerializer(serializers.Serializer):
    merchant_vessel = MerchantVesselMinimalSerializer()
    trips = MerVesselTripSerializer(many=True)
    reports = MerSpecialReportListSerializer(many=True)


class MerchantVesselDataView(DebugTimingMixin, APIView):
    def get(self, mv_key):
        vessel = get_object_or_404(
            Merchant_Vessel.objects.select_related('mv_ship_type')
            .prefetch_related('mv_images'),  # If images exist
            mv_key=mv_key
        )

        trips = (Merchant_Trip.objects.filter(mt_mv_key=vessel))

        reports = (
            MerSreports.objects
            .filter(msr_mv_key=vessel.mv_key)
            .select_related('msr_action', 'msr_mv_key')
            .prefetch_related('msr_patroltype')
        )

        trips_data = MerVesselTripSerializer(trips, many=True).data
        reports_data = MerSpecialReportListSerializer(reports, many=True).data
        vessel = MerchantVesselMinimalSerializer(vessel).data

        return Response({
            "merchant_vessel": vessel,
            "trips": trips_data,
            "reports": reports_data
        })
