from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import ais_views, mer_vessel, misrep_views, ais_summary, mer_special_report

router = DefaultRouter(trailing_slash=False)
router.register(r'merchant', mer_special_report.MerSpecialReportViewSet, basename="merchant")
router.register(r'aisvessel', mer_vessel.MerVesselViewSet, basename="aisvessel")
router.register(r'aisvessel_image', mer_vessel.MerVesselImageViewSet, basename="aisvessel_image")
router.register(r'misrep', misrep_views.MreportViewSet, basename="misrep")

urlpatterns = [
    path('', include(router.urls)),

    path('mv_trips_count', ais_views.trip_count, name='mv_trips_count'),
    path('mv_trips', ais_views.vessel_trip_counts, name='mv_trips'),
    path('stay_count', ais_views.stay_count, name='stay_count'),
    path('ship_counts', ais_views.ship_counts, name='ship_counts'),
    path('ship_counts_week', ais_views.ship_counts_week, name='ship_counts_week'),
    path('vessel_position', ais_views.vessel_position, name='vessel_position'),
    path('populate_data', ais_views.populate_data, name='populate_data'),
    path('flag_counts', ais_views.flag_counts, name='flag_counts'),
    path('type_counts', ais_views.type_counts, name='type_counts'),
    path('register_trip', ais_views.register_trip, name='register_trip'),
    path('merchant_vessel_view/<int:mv_key>', ais_summary.MerchantVesselDataView.as_view(),
         name='merchant_vessel_view'),
    path("mer_duration_at_sea", ais_views.mer_trip_duration),
    path("mer_activity_trend", ais_views.mer_trip_count),
    path("mer_leave_enter", ais_views.mer_leave_enter),
    path("mer_mv_leave_enter", ais_views.mer_mv_leave_enter),
    path("mer_fv_con", ais_views.mer_fv_con),
    path("mer_visual_act_trend", ais_views.mer_visual_act_trend),
    path("mer_visual_harbor", ais_views.mer_visual_harbour),
    path("mer_visual_flag_count", ais_views.mer_visual_flag_count),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
