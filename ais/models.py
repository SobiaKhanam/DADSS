from django.db import models
from django.utils import timezone

from common.models import Port, ActionType, PatrolType, MerchantType, FishingType, Weather


class Full_Data(models.Model):
    id = models.BigAutoField(primary_key=True)
    mmsi = models.CharField(max_length=100, blank=True,
                            null=True)  # maritime mobile service identity identifies vessel's transmitter station
    imo = models.CharField(max_length=100, blank=True,
                           null=True)  # international maritime organisation number uniquely identifies vessels
    ship_id = models.CharField(max_length=100, blank=True,
                               null=True)  # id assigned by marine traffic for the subject vessel
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    speed = models.FloatField(blank=True, null=True)
    heading = models.FloatField(blank=True, null=True)  # vessel bow position (vessel orientation)
    status = models.CharField(max_length=100, blank=True,
                              null=True)  # navigational status input by vessel's crew (value range from 0-15)
    course = models.FloatField(blank=True, null=True)  # vessel navigation or movement in water
    timestamp = models.DateTimeField(blank=True, null=True)  # time position/event recorded by marine traffic
    dsrc = models.CharField(max_length=100, blank=True, null=True)  # data source: terrestrial or satellite
    utc_seconds = models.FloatField(blank=True, null=True)  # time taken by vessel to transmit information
    ship_name = models.CharField(max_length=100, blank=True, null=True)
    ship_type = models.CharField(max_length=100, blank=True, null=True)
    call_sign = models.CharField(max_length=100, blank=True,
                                 null=True)  # uniquely designated identifier for the vessel's transmitter station
    flag = models.CharField(max_length=100, blank=True, null=True)
    length = models.FloatField(blank=True, null=True)  # in meters
    width = models.FloatField(blank=True, null=True)  # in meters
    grt = models.FloatField(blank=True,
                            null=True)  # gross tonnage: internal volume of ship (assess size and capacity of ship)
    dwt = models.FloatField(blank=True,
                            null=True)  # Deadweight (in metric tons): weight a vessel can safely carry (excluding its own)
    draught = models.FloatField(blank=True,
                                null=True)  # critical measurement for determining a ship's immersion in the water
    year_built = models.IntegerField(blank=True, null=True)
    rot = models.FloatField(blank=True,
                            null=True)  # rate of turn indicates how quickly a vessel is changing its direction of movement.
    type_name = models.CharField(max_length=100, blank=True, null=True)
    ais_type_summary = models.CharField(max_length=100, blank=True, null=True)  # Further explanation of the SHIPTYPE ID
    destination = models.CharField(max_length=100, blank=True, null=True)
    eta = models.DateTimeField(blank=True, null=True)  # Estimated Time of Arrival to Destination
    current_port = models.CharField(max_length=100, blank=True, null=True)
    last_port = models.CharField(max_length=100, blank=True, null=True)
    last_port_time = models.DateTimeField(blank=True, null=True)
    current_port_id = models.CharField(max_length=100, blank=True, null=True)
    current_port_unlocode = models.CharField(max_length=100, blank=True, null=True)
    current_port_country = models.CharField(max_length=100, blank=True, null=True)
    last_port_id = models.CharField(max_length=100, blank=True, null=True)
    last_port_unlocode = models.CharField(max_length=100, blank=True, null=True)
    last_port_country = models.CharField(max_length=100, blank=True, null=True)
    next_port_id = models.CharField(max_length=100, blank=True, null=True)
    next_port_unlocode = models.CharField(max_length=100, blank=True, null=True)
    next_port_name = models.CharField(max_length=100, blank=True, null=True)
    next_port_country = models.CharField(max_length=100, blank=True, null=True)
    eta_calc = models.DateTimeField(blank=True, null=True)
    eta_updated = models.DateTimeField(blank=True, null=True)
    distance_to_go = models.FloatField(blank=True, null=True)
    distance_travelled = models.FloatField(blank=True, null=True)
    awg_speed = models.FloatField(blank=True, null=True)
    max_speed = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fulldata'


class Merchant_Vessel(models.Model):
    mv_key = models.BigAutoField(primary_key=True)
    mv_mmsi = models.CharField(max_length=100, blank=True, null=True)
    mv_imo = models.CharField(max_length=100, blank=True, null=True)
    mv_ship_id = models.CharField(max_length=100, blank=True, null=True)
    mv_ship_name = models.CharField(max_length=100, blank=True, null=True)
    mv_ship_type = models.ForeignKey(MerchantType, on_delete=models.DO_NOTHING,
                                     db_column='mv_ship_type', null=True, blank=True)
    mv_call_sign = models.CharField(max_length=100, blank=True, null=True)
    mv_flag = models.CharField(max_length=100, blank=True, null=True)
    mv_length = models.FloatField(blank=True, null=True)
    mv_width = models.FloatField(blank=True, null=True)
    mv_grt = models.FloatField(blank=True, null=True)
    mv_dwt = models.FloatField(blank=True, null=True)
    mv_year_built = models.IntegerField(blank=True, null=True)
    mv_type_name = models.CharField(max_length=100, blank=True, null=True)
    mv_ais_type_summary = models.CharField(max_length=100, blank=True, null=True)
    mv_data_source = models.CharField(max_length=50, default="ais")
    mv_pf_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mer_vessel'


class MerVesselImage(models.Model):
    vi_key = models.BigAutoField(primary_key=True)
    vi_vessel = models.ForeignKey('Merchant_Vessel', db_column='vi_vessel', related_name='mv_images',
                                  on_delete=models.CASCADE)
    vi_image = models.ImageField(upload_to='vessel_images/merchant/', blank=True, null=True)
    vi_remarks = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mer_vessel_images'


class Merchant_Trip(models.Model):
    mt_key = models.BigAutoField(primary_key=True)
    mt_mv_key = models.ForeignKey(Merchant_Vessel, models.DO_NOTHING, db_column='mt_mv_key', related_name='trips')
    mt_dsrc = models.CharField(max_length=100, blank=True, null=True)
    mt_destination = models.CharField(max_length=100, blank=True, null=True)
    mt_eta = models.DateTimeField(blank=True, null=True)
    mt_first_observed_at = models.DateTimeField(blank=True, null=True)
    mt_last_observed_at = models.DateTimeField(blank=True, null=True)
    mt_observed_duration = models.IntegerField(blank=True, null=True)
    mt_trip_status = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mer_trip'

    # @property
    # def tripdetails(self):
    #     return self.tripdetails.all()


class Trip_Details(models.Model):
    mtd_key = models.BigAutoField(primary_key=True)
    mtd_mt_key = models.ForeignKey(Merchant_Trip, models.DO_NOTHING, db_column='mtd_mt_key', related_name='tripdetails')
    mtd_longitude = models.FloatField(blank=True, null=True)
    mtd_latitude = models.FloatField(blank=True, null=True)
    mtd_speed = models.FloatField(blank=True, null=True)
    mtd_heading = models.FloatField(blank=True, null=True)
    mtd_status = models.CharField(max_length=100, blank=True, null=True)
    mtd_course = models.FloatField(blank=True, null=True)
    mtd_timestamp = models.DateTimeField(blank=True, null=True)
    mtd_utc_seconds = models.FloatField(blank=True, null=True)
    mtd_draught = models.FloatField(blank=True, null=True)
    mtd_rot = models.FloatField(blank=True, null=True)
    mtd_current_port = models.CharField(max_length=100, blank=True, null=True)
    mtd_last_port = models.CharField(max_length=100, blank=True, null=True)
    mtd_last_port_time = models.DateTimeField(blank=True, null=True)
    mtd_current_port_id = models.CharField(max_length=100, blank=True, null=True)
    mtd_current_port_unlocode = models.CharField(max_length=100, blank=True, null=True)
    mtd_current_port_country = models.CharField(max_length=100, blank=True, null=True)
    mtd_last_port_id = models.CharField(max_length=100, blank=True, null=True)
    mtd_last_port_unlocode = models.CharField(max_length=100, blank=True, null=True)
    mtd_last_port_country = models.CharField(max_length=100, blank=True, null=True)
    mtd_next_port_id = models.CharField(max_length=100, blank=True, null=True)
    mtd_next_port_unlocode = models.CharField(max_length=100, blank=True, null=True)
    mtd_next_port_name = models.CharField(max_length=100, blank=True, null=True)
    mtd_next_port_country = models.CharField(max_length=100, blank=True, null=True)
    mtd_eta_calc = models.DateTimeField(blank=True, null=True)
    mtd_eta_updated = models.DateTimeField(blank=True, null=True)
    mtd_distance_to_go = models.FloatField(blank=True, null=True)
    mtd_distance_travelled = models.FloatField(blank=True, null=True)
    mtd_awg_speed = models.FloatField(blank=True, null=True)
    mtd_max_speed = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mer_trip_detail'


class MerSreports(models.Model):
    msr_key = models.AutoField(primary_key=True)
    msr_pf_id = models.CharField(max_length=100)
    msr_dtg = models.DateTimeField(blank=True, null=True)
    msr_position = models.TextField(blank=True, null=True)
    msr_mv_key = models.ForeignKey(Merchant_Vessel, on_delete=models.DO_NOTHING, db_column='msr_mv_key')
    msr_movement = models.CharField(max_length=100, blank=True, null=True)
    msr_action = models.ForeignKey(ActionType, on_delete=models.DO_NOTHING, db_column='msr_action')
    msr_info = models.CharField(max_length=100, blank=True, null=True)
    msr_rdt = models.DateTimeField(default=timezone.now)
    msr_fuelrem = models.IntegerField(blank=True, null=True)
    msr_patroltype = models.ManyToManyField(PatrolType, through='MsreportPatroltype', related_name='msr_patroltype')
    msr_coi = models.BooleanField(blank=True, null=True, default=False)
    msr_freshwater = models.IntegerField(blank=True, null=True)
    msr_w_key = models.ForeignKey(Weather, on_delete=models.DO_NOTHING, db_column='msr_w_key',
                                  blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mersreports'


class MerSrgoods(models.Model):
    msrg_key = models.AutoField(primary_key=True)
    msrg_msr_key = models.ForeignKey(MerSreports, models.DO_NOTHING, db_column='msrg_msr_key',
                                     related_name='msreport_goods')
    msrg_item = models.CharField(max_length=100, blank=True, null=True)
    msrg_qty = models.FloatField(blank=True, null=True)
    msrg_denomination = models.CharField(max_length=100, blank=True, null=True)
    msrg_category = models.CharField(max_length=100, blank=True, null=True)
    msrg_subcategory = models.CharField(max_length=100, blank=True, null=True)
    msrg_value = models.FloatField(blank=True, null=True)
    msrg_source = models.CharField(max_length=100, blank=True, null=True)
    msrg_confiscated = models.BooleanField(blank=True, null=True)
    msrg_remarks = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mersrgoods'


class MerSrgoodsImage(models.Model):
    msrgi_key = models.BigAutoField(primary_key=True)
    msrgi_good = models.ForeignKey('MerSrgoods', db_column='msrgi_good', related_name='msrg_images',
                                   on_delete=models.CASCADE)
    msrgi_image = models.ImageField(upload_to='goods_images/merchant/', blank=True, null=True)
    msrgi_remarks = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mersrgoods_images'


class MerSreports2(models.Model):
    msr2_key = models.OneToOneField(MerSreports, models.DO_NOTHING, db_column='msr2_key', primary_key=True,
                                    related_name='merchant_trip')
    msr2_lpoc = models.ForeignKey(Port, on_delete=models.DO_NOTHING, db_column='msr2_lpoc', related_name='msr2_lpoc')
    msr2_lpocdtg = models.DateField(blank=True, null=True)
    msr2_npoc = models.ForeignKey(Port, on_delete=models.DO_NOTHING, db_column='msr2_npoc', related_name='msr2_npoc')
    msr2_npoceta = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mersreports2'


class MSReportPatroltype(models.Model):
    msp_key = models.AutoField(primary_key=True)
    msreport = models.ForeignKey(MerSreports, models.DO_NOTHING, db_column='msreport', related_name='msr_patroltypes')
    patroltype = models.ForeignKey(PatrolType, models.DO_NOTHING, db_column='patroltype')

    class Meta:
        managed = False
        db_table = 'msreport_patroltype'


class MissionReport(models.Model):
    mr_key = models.BigAutoField(primary_key=True)
    mr_pf_id = models.CharField(max_length=100)
    mr_dtg = models.DateTimeField(blank=True, null=True)
    mr_rdt = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'misrep'

    @property
    def detail(self):
        return self.mrdetails.all()

    @property
    def fdensity(self):
        return self.mrfdensity.all()

    @property
    def fishing(self):
        return self.mrfishing.all()


class MRFDensity(models.Model):
    mrfd_key = models.AutoField(primary_key=True)
    mrfd_mr_key = models.ForeignKey(MissionReport, models.DO_NOTHING, db_column='mrfd_mr_key',
                                    related_name='mrfdensity')
    mrfd_position = models.TextField()  # This field type is a guess.
    mrfd_qty = models.SmallIntegerField()
    mrfd_type = models.ForeignKey(FishingType, on_delete=models.DO_NOTHING,
                                  db_column='mrfd_type', blank=True, null=True)
    mrfd_movement = models.CharField()

    class Meta:
        managed = False
        db_table = 'misrep_fdensity'


class MRDetails(models.Model):
    mrd_key = models.BigAutoField(primary_key=True)
    mrd_mmsi = models.CharField(max_length=100, blank=True, null=True)
    mrd_vessel_type = models.ForeignKey(MerchantType, on_delete=models.DO_NOTHING,
                                        db_column='mrd_vessel_type', blank=True, null=True)
    mrd_vessel_name = models.CharField(max_length=100, blank=True, null=True)
    mrd_position = models.TextField(blank=True, null=True)  # This field type is a guess.
    mrd_course = models.FloatField(blank=True, null=True)
    mrd_speed = models.FloatField(blank=True, null=True)
    mrd_npoc = models.ForeignKey(Port, on_delete=models.DO_NOTHING, related_name='mrd_npoc',
                                 db_column='mrd_npoc', blank=True, null=True)
    mrd_lpoc = models.ForeignKey(Port, on_delete=models.DO_NOTHING, related_name='mrd_lpoc',
                                 db_column='mrd_lpoc', blank=True, null=True)
    mrd_act_desc = models.CharField(max_length=500, blank=True, null=True)
    mrd_dtg = models.DateTimeField(blank=True, null=True)
    mrd_ais_status = models.CharField(max_length=100, blank=True, null=True)
    mrd_call_details = models.CharField(max_length=100, blank=True, null=True)
    mrd_response = models.CharField(max_length=100, blank=True, null=True)
    mrd_remarks = models.CharField(max_length=100, blank=True, null=True)
    mrd_mr_key = models.ForeignKey(MissionReport, models.DO_NOTHING, db_column='mrd_mr_key', related_name='mrdetails')
    mrd_mv_key = models.ForeignKey(Merchant_Vessel, on_delete=models.CASCADE,
                                   db_column='mrd_mv_key', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'misrep_details'


class MRFishing(models.Model):
    mrf_key = models.AutoField(primary_key=True)
    mrf_mr_key = models.ForeignKey(MissionReport, models.DO_NOTHING, db_column='mrf_mr_key', related_name='mrfishing')
    mrf_position = models.TextField()  # This field type is a guess.
    mrf_name = models.CharField()
    mrf_type = models.ForeignKey(FishingType, on_delete=models.DO_NOTHING,
                                 db_column='mrf_type', blank=True, null=True)
    mrf_movement = models.CharField()

    class Meta:
        managed = False
        db_table = 'misrep_fishing'

