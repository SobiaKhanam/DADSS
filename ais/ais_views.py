import pycountry
from django.utils.dateparse import parse_date

from .models import *
from django.http import JsonResponse
from django.db.models import Q, F, ExpressionWrapper, DurationField, Case, When, CharField, Min, Max, Count
from datetime import datetime, timedelta
import pandas as pd
from pytz import timezone
from rest_framework.decorators import api_view
from django.db import transaction
from itertools import groupby
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from collections import Counter

@api_view(http_method_names=['GET'])
def trip_count(request):
    """
    Returns a distribution like:
    [
        {"trip_count": 1, "ship_count": 5},
        {"trip_count": 2, "ship_count": 12},
        ...
    ]
    Supports optional date filters: ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
    """
    # 1. Parse date filters
    date_from_raw = request.GET.get('date_from')
    date_to_raw = request.GET.get('date_to')
    start_date = parse_date(date_from_raw) if date_from_raw else None
    end_date = parse_date(date_to_raw) if date_to_raw else None

    # 2. Build trip date filter
    trip_filter = Q()
    if start_date:
        trip_filter &= Q(trips__mt_first_observed_at__gte=start_date)
    if end_date:
        trip_filter &= Q(trips__mt_first_observed_at__lte=end_date)

    # 3. Annotate vessels with filtered trip counts
    vessels_with_trip_counts = Merchant_Vessel.objects.annotate(
        trip_count=Count('trips', filter=trip_filter)
    )

    # 4. Count how many vessels have each trip_count
    counter = Counter()
    for vessel in vessels_with_trip_counts:
        counter[vessel.trip_count] += 1

    # 5. Format and return sorted distribution
    distribution = [
        {'trip_count': k, 'ship_count': v}
        for k, v in sorted(counter.items())
    ]

    return JsonResponse(distribution, safe=False)

@api_view(['GET'])
def vessel_trip_counts(request):
    """
    Returns vessels and their trip counts with optional filters:
    - start_date: only count trips after this date (inclusive)
    - end_date: only count trips before this date (inclusive)
    - min_trips: only include vessels with >= this number of trips
    - max_trips: only include vessels with <= this number of trips
    """

    # Get filter parameters from query params
    date_from_raw = request.GET.get('date_from')
    date_to_raw = request.GET.get('date_to')

    start_date = parse_date(date_from_raw) if date_from_raw else None
    end_date = parse_date(date_to_raw) if date_to_raw else None
    min_trips = request.GET.get('min_trips')
    max_trips = request.GET.get('max_trips')
    search = request.GET.get('search', '').strip()

    # Step 1: Filter trips by date using Q object
    trip_filter = Q()
    if start_date:
        trip_filter &= Q(trips__mt_first_observed_at__gte=start_date)
    if end_date:
        trip_filter &= Q(trips__mt_first_observed_at__lte=end_date)

    # Step 2: Annotate each vessel with its trip count (filtered)
    vessels = Merchant_Vessel.objects.annotate(
        trip_count=Count('trips', filter=trip_filter)
    )

    # ✅ Exclude vessels with 0 trips
    if start_date or end_date or search:
        vessels = vessels.filter(trip_count__gt=0)

    # 4. Filter by name search
    if search:
        vessels = vessels.filter(mv_ship_name__icontains=search)

    # Step 5: Filter by trip count range
    if min_trips:
        vessels = vessels.filter(trip_count__gte=int(min_trips))
    if max_trips:
        vessels = vessels.filter(trip_count__lte=int(max_trips))

    # Step 6: Return selected fields
    results = vessels.values('mv_key', 'mv_ship_name', 'trip_count').order_by('-trip_count')

    return JsonResponse(list(results), safe=False)


@api_view(http_method_names=['GET'])
def stay_count(request):
    start_date_str = request.GET.get('date_from')
    end_date_str = request.GET.get('date_to')
    port = request.GET.get('port')

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    ship_data = Full_Data.objects.filter(timestamp__range=[start_date, end_date]).values(
        'ship_id', 'current_port','timestamp').order_by('timestamp')

    if not ship_data:
        return JsonResponse({})

    ship_df = pd.DataFrame.from_records(ship_data)

    # Combine "KARACHI" and "KARACHI ANCH" into a single category "KARACHI" and same for PORT QASIM AND PORT QASIM ANCH
    ship_df['current_port'] = ship_df['current_port'].replace(
        {'KARACHI ANCH': 'KARACHI', 'PORT QASIM ANCH': 'PORT QASIM'})

    # Filter data for provided port only
    karachi_data = ship_df[ship_df['current_port'] == port]

    # Group data by ship_id
    grouped_data = karachi_data.groupby('ship_id')

    # Calculate the duration for each group (first and last timestamp)
    port_durations = grouped_data.agg({'timestamp': ['first', 'last']})

    # Calculate the duration in days
    port_durations['duration'] = (port_durations['timestamp']['last'] - port_durations['timestamp']['first']).dt.days

    port_durations = port_durations[port_durations['duration'] > 0]

    # Calculate the number of days each ship stayed in Karachi
    days_counts = port_durations['duration'].value_counts().sort_index()

    # Create a dictionary for the JSON response
    response_data = {f"{days} day{'s' if days > 1 else ''}": count for days, count in days_counts.items()}

    return JsonResponse(response_data)


@api_view(http_method_names=['GET'])
def ship_counts(request):
    start_date_str = request.GET.get('date_from')
    end_date_str = request.GET.get('date_to')

    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7 * 7)

    # Filter the data based on the specified time period
    filtered_data = Full_Data.objects.filter(Q(timestamp__range=(start_date, end_date))). \
        values('ship_id', 'current_port').distinct()

    # Create a dictionary to count the ports
    port_counts = {
        "KARACHI": 0,
        "PORT QASIM": 0,
        "GWADAR": 0,
        "CROSSING": 0,
    }

    for item in filtered_data:
        current_port = item['current_port']
        if current_port in ['KARACHI', 'KARACHI ANCH']:
            port_counts['KARACHI'] += 1
        elif current_port in ['PORT QASIM', 'PORT QASIM ANCH']:
            port_counts['PORT QASIM'] += 1
        elif current_port == 'GWADAR':
            port_counts['GWADAR'] += 1
        elif current_port == '':
            port_counts['CROSSING'] += 1

    # Create a JSON response
    return JsonResponse(port_counts)


@api_view(http_method_names=['GET'])
def ship_counts_week(request):
    # Get the start and end dates from the request
    start_date_str = request.GET.get('date_from')
    end_date_str = request.GET.get('date_to')

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Calculate the number of weeks between start and end dates
    total_weeks = (end_date - start_date).days // 7 + 1

    # Create a list of dictionaries to store counts for each week
    weekly_counts = []

    # Iterate through each week and calculate counts
    for week in range(total_weeks):
        week_start = start_date + timedelta(weeks=week)
        week_end = week_start + timedelta(days=6)

        # Filter the data for the current week
        filtered_data = Full_Data.objects.filter(
            Q(timestamp__range=(week_start, week_end))
        ).values('ship_id', 'current_port').distinct()

        # Create a dictionary to count the ports
        port_counts = {
            "KARACHI": 0,
            "PORT QASIM": 0,
            "GWADAR": 0,
            "CROSSING": 0,
        }

        for item in filtered_data:
            current_port = item['current_port']
            if current_port in ['KARACHI', 'KARACHI ANCH']:
                port_counts['KARACHI'] += 1
            elif current_port in ['PORT QASIM', 'PORT QASIM ANCH']:
                port_counts['PORT QASIM'] += 1
            elif current_port == 'GWADAR':
                port_counts['GWADAR'] += 1
            elif current_port == '':
                port_counts['CROSSING'] += 1

        # Create a dictionary for the current week's counts
        weekly_count = {
            "Week Start": week_start.strftime('%Y-%m-%d'),
            "Week End": week_end.strftime('%Y-%m-%d'),
            "Counts": port_counts,
        }

        # Append the weekly counts to the list
        weekly_counts.append(weekly_count)

    # Create a JSON response with weekly counts
    return JsonResponse(weekly_counts, safe=False)


@api_view(http_method_names=['GET'])
def vessel_position(request):
    ship_id = request.GET.get('ship_id')

    if ship_id:
        ship_positions = Full_Data.objects.filter(ship_id=ship_id).order_by('-timestamp').values(
            'timestamp',
            'latitude',
            'longitude'
        )

        response_data = [
            {
                'timestamp': position['timestamp'].astimezone(timezone('Asia/Karachi')).strftime(
                    '%Y-%m-%d %H:%M:%S.%f %z'),
                'latitude': position['latitude'],
                'longitude': position['longitude']
            }
            for position in ship_positions
        ]
    else:
        latest_positions = Full_Data.objects.order_by('ship_id', '-timestamp').distinct('ship_id').values(
            'ship_id',
            'latitude',
            'longitude',
            'timestamp'
        )

        response_data = [
            {
                'ship_id': position['ship_id'],
                'latitude': position['latitude'],
                'longitude': position['longitude'],
                'timestamp': position['timestamp'].astimezone(timezone('Asia/Karachi')).strftime(
                    '%Y-%m-%d %H:%M:%S.%f %z')
            }
            for position in latest_positions
        ]

    return JsonResponse(response_data, safe=False)


@api_view(http_method_names=['POST'])
def populate_data(request):
    full_data_records = Full_Data.objects.all().order_by('timestamp')

    for row in full_data_records:
        Merchant_Vessel.objects.get_or_create(
            mv_imo=row.imo,
            mv_ship_id=row.ship_id,
            defaults={
                'mv_mmsi': row.mmsi,
                'mv_ship_name': row.ship_name,
                'mv_ship_type': row.ship_type,
                'mv_flag': row.flag,
                'mv_length': row.length,
                'mv_width': row.width,
                'mv_grt': row.grt,
                'mv_dwt': row.dwt,
                'mv_year_built': row.year_built,
                'mv_type_name': row.type_name,
                'mv_ais_type_summary': row.ais_type_summary,
                'mv_data_source': 'ais'
            }
        )
    return JsonResponse(
        {"message": "All unique ships from Full_Data has been successfully uploaded in merchant_vessel."}, status=200)


@api_view(http_method_names=['GET'])
def flag_counts(request):
    start_date_str = request.GET.get('date_from')
    end_date_str = request.GET.get('date_to')
    port = request.GET.get('port')

    date_from = datetime.strptime(start_date_str, '%Y-%m-%d')
    date_to = datetime.strptime(end_date_str, '%Y-%m-%d')

    all_ships = Full_Data.objects.filter(timestamp__range=(date_from, date_to))
    ship_data = list(all_ships.values())
    ship_df = pd.DataFrame.from_records(ship_data)
    ship_df['current_port'] = ship_df['current_port'].replace(
        {'KARACHI ANCH': 'KARACHI', 'PORT QASIM ANCH': 'PORT QASIM'})
    if port:
        ship_df = ship_df[ship_df['current_port'] == port]

    unique_ships = {}
    for ship in ship_df.itertuples():
        unique_ships[ship.ship_id] = ship.flag

    flag_count = {}
    for flag in unique_ships.values():
        flag_count[flag] = flag_count.get(flag, 0) + 1

    return JsonResponse(flag_count)


@api_view(http_method_names=['GET'])
def type_counts(request):
    start_date_str = request.GET.get('date_from')
    end_date_str = request.GET.get('date_to')
    port = request.GET.get('port')

    date_from = datetime.strptime(start_date_str, '%Y-%m-%d')
    date_to = datetime.strptime(end_date_str, '%Y-%m-%d')

    all_ships = Full_Data.objects.filter(timestamp__range=(date_from, date_to))
    if port:
        all_ships = all_ships.filter(current_port=port)

    ship_data = list(all_ships.values())
    ship_df = pd.DataFrame.from_records(ship_data)
    ship_df['current_port'] = ship_df['current_port'].replace(
        {'KARACHI ANCH': 'KARACHI', 'PORT QASIM ANCH': 'PORT QASIM'})
    unique_ships = ship_df.drop_duplicates(subset='ship_id')
    type_count = unique_ships.groupby('ais_type_summary')['ship_id'].count().to_dict()

    return JsonResponse(type_count)


@transaction.atomic
def register_trip(request):
    data_records = Full_Data.objects.all().order_by('imo', 'mmsi', 'timestamp')
    # Group records by IMO or MMSI based on the condition
    records_by_identifier = {}
    for is_imo_zero, group in groupby(data_records, key=lambda x: x.imo == '0'):
        identifier = 'mmsi' if is_imo_zero else 'imo'
        records_by_identifier[identifier] = list(group)

    for identifier, records in records_by_identifier.items():
        # Initialize a dictionary to keep track of ongoing trips for each vessel
        ongoing_trips = {}
        previous_timestamp = None

        for row in records:
            # Determine the identifier value (either MMSI or IMO)
            identifier_value = row.mmsi if identifier == 'mmsi' else row.imo
            # Register vessel data if not already registered
            vessel, created = Merchant_Vessel.objects.get_or_create(
                mv_imo=row.imo,
                mv_ship_id=row.ship_id,
                defaults={
                    'mv_mmsi': row.mmsi,
                    'mv_ship_name': row.ship_name,
                    'mv_ship_type': row.ship_type,
                    'mv_call_sign': row.call_sign,
                    'mv_flag': row.flag,
                    'mv_length': row.length,
                    'mv_width': row.width,
                    'mv_grt': row.grt,
                    'mv_dwt': row.dwt,
                    'mv_year_built': row.year_built,
                    'mv_type_name': row.type_name,
                    'mv_ais_type_summary': row.ais_type_summary
                }
            )
            timestamp = row.timestamp
            if identifier_value in ongoing_trips:
                trip = ongoing_trips[identifier_value]
                if row.destination != trip.mt_destination and row.eta != trip.mt_eta:
                    trip.mt_last_observed_at = previous_timestamp
                    trip.mt_observed_duration = (previous_timestamp - trip.mt_first_observed_at).days
                    trip.mt_trip_status = 'Completed'
                    trip.save()
                    trip = Merchant_Trip.objects.create(
                        mt_mv_key=vessel,
                        mt_dsrc=row.dsrc,
                        mt_destination=row.destination,
                        mt_eta=row.eta,
                        mt_first_observed_at=timestamp,
                        mt_trip_status='Ongoing'
                    )
                    ongoing_trips[identifier_value] = trip
                # Create or update TripDetail for ongoing trip
                Trip_Details.objects.create(
                    mtd_mt_key=trip,
                    mtd_longitude=row.longitude,
                    mtd_latitude=row.latitude,
                    mtd_speed=row.speed,
                    mtd_heading=row.heading,
                    mtd_status=row.status,
                    mtd_course=row.course,
                    mtd_timestamp=timestamp,
                    mtd_utc_seconds=row.utc_seconds,
                    mtd_draught=row.draught,
                    mtd_rot=row.rot,
                    mtd_current_port=row.current_port,
                    mtd_last_port=row.last_port,
                    mtd_last_port_time=row.last_port_time,
                    mtd_current_port_id=row.current_port_id,
                    mtd_current_port_unlocode=row.current_port_unlocode,
                    mtd_current_port_country=row.current_port_country,
                    mtd_last_port_id=row.last_port_id,
                    mtd_last_port_unlocode=row.last_port_unlocode,
                    mtd_last_port_country=row.last_port_country,
                    mtd_next_port_id=row.next_port_id,
                    mtd_next_port_unlocode=row.next_port_unlocode,
                    mtd_next_port_name=row.next_port_name,
                    mtd_next_port_country=row.next_port_country,
                    mtd_eta_calc=row.eta_calc,
                    mtd_eta_updated=row.eta_updated,
                    mtd_distance_to_go=row.distance_to_go,
                    mtd_distance_travelled=row.distance_travelled,
                    mtd_awg_speed=row.awg_speed,
                    mtd_max_speed=row.max_speed
                )
            else:
                # Create a new trip and TripDetail
                trip = Merchant_Trip.objects.create(
                    mt_mv_key=vessel,
                    mt_dsrc=row.dsrc,
                    mt_destination=row.destination,
                    mt_eta=row.eta,
                    mt_first_observed_at=timestamp,
                    mt_trip_status='Ongoing'
                )
                ongoing_trips[identifier_value] = trip

                Trip_Details.objects.create(
                    mtd_mt_key=trip,
                    mtd_longitude=row.longitude,
                    mtd_latitude=row.latitude,
                    mtd_speed=row.speed,
                    mtd_heading=row.heading,
                    mtd_status=row.status,
                    mtd_course=row.course,
                    mtd_timestamp=timestamp,
                    mtd_utc_seconds=row.utc_seconds,
                    mtd_draught=row.draught,
                    mtd_rot=row.rot,
                    mtd_current_port=row.current_port,
                    mtd_last_port=row.last_port,
                    mtd_last_port_time=row.last_port_time,
                    mtd_current_port_id=row.current_port_id,
                    mtd_current_port_unlocode=row.current_port_unlocode,
                    mtd_current_port_country=row.current_port_country,
                    mtd_last_port_id=row.last_port_id,
                    mtd_last_port_unlocode=row.last_port_unlocode,
                    mtd_last_port_country=row.last_port_country,
                    mtd_next_port_id=row.next_port_id,
                    mtd_next_port_unlocode=row.next_port_unlocode,
                    mtd_next_port_name=row.next_port_name,
                    mtd_next_port_country=row.next_port_country,
                    mtd_eta_calc=row.eta_calc,
                    mtd_eta_updated=row.eta_updated,
                    mtd_distance_to_go=row.distance_to_go,
                    mtd_distance_travelled=row.distance_travelled,
                    mtd_awg_speed=row.awg_speed,
                    mtd_max_speed=row.max_speed
                )
            previous_timestamp = timestamp

    return JsonResponse({"message": "Data registration complete"}, status=200)


@api_view(http_method_names=['GET'])
def mer_trip_duration(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    data = Full_Data.objects.filter(timestamp__range=[date_from, date_to])

    # Step 2: Handle the case where IMO is 0 by using MMSI
    data = data.annotate(unique_id=F('imo')).annotate(unique_id=Case(When(unique_id='0', then=F('mmsi')),
                                                                     default=F('unique_id'), output_field=CharField()))
    # Step 3: Calculate the duration each ship has spent at sea
    data = data.values('unique_id').annotate(
        min_timestamp=Min('timestamp'),
        max_timestamp=Max('timestamp')
    ).annotate(duration=ExpressionWrapper(F('max_timestamp') - F('min_timestamp'), output_field=DurationField()))

    # Step 4: Categorize these durations
    less_than_15_days = data.filter(duration__lt=timedelta(days=15)).count()
    between_15_and_30_days = data.filter(duration__gte=timedelta(days=15), duration__lte=timedelta(days=30)).count()
    greater_than_30_days = data.filter(duration__gt=timedelta(days=30)).count()

    # Step 5: Return the counts
    response_data = {
        "less than 15 days": less_than_15_days,
        "between 15 and 30 days": between_15_and_30_days,
        "greater than 30 days": greater_than_30_days
    }

    return JsonResponse(response_data)


@api_view(['GET'])
def mer_trip_count(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    date_from = datetime.strptime(date_from, '%Y-%m-%d')
    date_to = datetime.strptime(date_to, '%Y-%m-%d')

    response = []
    num_days = (date_to - date_from).days + 1
    if num_days > 90:
        grouping_level = 'month'
    else:
        grouping_level = 'day'

    if grouping_level == 'month':
        increment = relativedelta(months=1)
    else:
        increment = timedelta(days=1)

    trips = Full_Data.objects.filter(timestamp__range=(date_from, date_to))
    current_date = date_from
    while current_date <= date_to:
        year = current_date.year
        month = current_date.month
        day = current_date.day

        item = {'Year': year, 'Month': datetime.strftime(current_date, '%B')}
        if grouping_level == 'day':
            item['Date'] = day

        if grouping_level == 'month':
            filtered_trips = trips.filter(timestamp__year=year, timestamp__month=month)
        else:
            filtered_trips = trips.filter(timestamp__date=current_date)

        # Annotate and count based on unique ship identification
        counts = (filtered_trips
                  .annotate(unique_ship=Case(
            When(imo=0, then=F('mmsi')),
            default=F('imo'),
            output_field=CharField()))
                  .values('current_port', 'unique_ship')
                  .distinct()
                  .values('current_port')
                  .annotate(count=Count('unique_ship'))
                  .order_by('current_port'))

        for count in counts:
            item[count['current_port']] = count['count']

        all_possible_locations = Full_Data.objects.values_list('current_port', flat=True).distinct()
        for location in all_possible_locations:
            if location not in item:
                item[location] = 0

        response.append(item)
        current_date += increment

    return JsonResponse(response, safe=False)


@api_view(['GET'])
def mer_leave_enter(request):
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    boat_location = request.GET.get('boat_location')

    # Parse date strings to datetime objects
    date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
    date_to = datetime.strptime(date_to_str, "%Y-%m-%d")

    # Calculate the duration between date_from and date_to
    duration = (date_to - date_from).days

    # Set the initial date
    current_date = date_from

    data = []

    # Initialize date labels and counters
    while current_date <= date_to:
        if duration < 90:
            next_date = current_date + timedelta(days=1)
            date_range_label = current_date.strftime("%d-%B-%Y")
        else:
            next_date = current_date.replace(month=current_date.month % 12 + 1,
                                             day=1) if current_date.month < 12 else current_date.replace(
                year=current_date.year + 1, month=1, day=1)
            date_range_label = current_date.strftime("%B %Y")

        # Filter for the specific date range
        date_filter = Q(timestamp__gte=current_date) & Q(timestamp__lt=next_date)

        # Filter records for the date range and optionally by boat location
        if boat_location:
            arrivals = Full_Data.objects.filter(date_filter, current_port=boat_location).distinct('imo')
            departures = Full_Data.objects.filter(date_filter, last_port=boat_location).distinct('imo')
            data.append({
                "date": date_range_label,
                "arrivals": arrivals.count(),
                "departures": -1 * departures.count()
            })

            total_arrivals = Full_Data.objects.filter(date_filter).aggregate(
                total=Count('imo', distinct=True, filter=Q(current_port__isnull=False) & ~Q(current_port=''))
            )['total'] or 0

            total_departures = Full_Data.objects.filter(date_filter).aggregate(
                total=Count('imo', distinct=True, filter=Q(last_port__isnull=False) & ~Q(last_port=''))
            )['total'] or 0

            data.append({
                "date": date_range_label,
                "arrivals": total_arrivals,
                "departures": -1 * total_departures
            })

        current_date = next_date

    return JsonResponse(data, safe=False)


@api_view(['GET'])
def mer_mv_leave_enter(request):
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    boat_location = request.GET.get('boat_location')

    # Parse date strings to datetime objects
    date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
    date_to = datetime.strptime(date_to_str, "%Y-%m-%d")

    # Calculate the duration between date_from and date_to
    duration = (date_to - date_from).days

    # Set the initial date
    current_date = date_from

    data = []

    # Get a distinct list of ports based on current_port
    port_list = list(
        Full_Data.objects.exclude(current_port__isnull=True).exclude(current_port='').values_list('current_port',
                                                                                                  flat=True).distinct())

    # Initialize date labels and counters
    while current_date <= date_to:
        if duration < 90:
            next_date = current_date + timedelta(days=1)
            date_range_label = current_date.strftime("%d-%B-%Y")
        else:
            next_date = current_date.replace(month=current_date.month % 12 + 1,
                                             day=1) if current_date.month < 12 else current_date.replace(
                year=current_date.year + 1, month=1, day=1)
            date_range_label = current_date.strftime("%B %Y")

        # Filter for the specific date range
        date_filter = Q(timestamp__gte=current_date) & Q(timestamp__lt=next_date)
        ports_data = {port: {"arrivals": 0, "departures": 0} for port in port_list}

        # Filter records for the date range and optionally by boat location
        if boat_location:
            arrivals = Full_Data.objects.filter(date_filter, current_port=boat_location).values(
                'current_port').annotate(
                imo_count=Count('imo', distinct=True))
            departures = Full_Data.objects.filter(date_filter, last_port=boat_location).values('last_port').annotate(
                imo_count=Count('imo', distinct=True))

        else:
            # Query arrivals and departures
            arrivals = Full_Data.objects.filter(date_filter).values('current_port').annotate(
                imo_count=Count('imo', distinct=True))
            departures = Full_Data.objects.filter(date_filter).values('last_port').annotate(
                imo_count=Count('imo', distinct=True))

        # Fill in arrivals and departures counts
        for arrival in arrivals:
            port = arrival['current_port']
            if port in ports_data:
                ports_data[port]['arrivals'] = arrival['imo_count']

        for departure in departures:
            port = departure['last_port']
            if port in ports_data:
                ports_data[port]['departures'] = departure['imo_count']

        data.append({
            "date": date_range_label,
            **ports_data
        })

        current_date = next_date

    return JsonResponse(data, safe=False)


@api_view(http_method_names=['GET'])
def mer_fv_con(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Filter data based on date range
    if date_from and date_to:
        data_query = Full_Data.objects.filter(timestamp__gte=date_from, timestamp__lte=date_to)
    else:
        data_query = Full_Data.objects.all()

    # Get the latest entry for each unique IMO
    latest_entries = data_query.values('imo').annotate(max_id=Max('id'))
    latest_data = Full_Data.objects.filter(id__in=[entry['max_id'] for entry in latest_entries])

    # Extract coordinates for the heatmap
    coordinates = [(data.latitude, data.longitude) for data in latest_data if
                   data.latitude is not None and data.longitude is not None]

    # Calculate density using a grid approach
    grid_size = 0.1  # Adjust grid size for resolution
    density_map = defaultdict(int)

    for lat, lon in coordinates:
        lat_grid = round(lat / grid_size) * grid_size
        lon_grid = round(lon / grid_size) * grid_size
        density_map[(lat_grid, lon_grid)] += 1

    # Convert to the specified JSON format
    heatmap_data = []
    for (lat, lon), density in density_map.items():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]  # Note that GeoJSON format uses [longitude, latitude]
            },
            "properties": {
                "intensity": density
            }
        }
        heatmap_data.append(feature)

    # Return the JSON response
    return JsonResponse(heatmap_data, safe=False)


@api_view(http_method_names=['GET'])
def mer_visual_act_trend(request):
    date_from = datetime.strptime(request.GET.get('date_from'), '%Y-%m-%d').date()
    date_to = datetime.strptime(request.GET.get('date_to'), '%Y-%m-%d').date()

    filter = request.GET.get('filter')  # 'harbor and type', 'harbor' or 'type'
    harbor = request.GET.get('harbor')
    type = request.GET.get('type')
    grouping_level = request.GET.get('group_by')

    if type:
        type_list = type.split(',')

    all_possible_types = Full_Data.objects.exclude(ais_type_summary='').values_list('ais_type_summary',
                                                                                    flat=True).distinct()
    all_possible_locations = ['KARACHI', 'PORT QASIM', 'GWADAR']
    response_data = []

    current_date = date_from
    while current_date <= date_to:
        year = current_date.year
        month = current_date.strftime('%B')
        filter_start = current_date
        week_end = current_date + timedelta(days=6)

        if grouping_level == 'day':
            item = {'Year': year, 'Month': month, 'Date': current_date.day}
            filter_end = current_date
        elif grouping_level == 'week':
            if week_end > date_to:
                week_end = date_to
            item = {
                'Year': year,
                'Week_Start': current_date.strftime('%d-%m-%Y'),
                'Week_End': week_end.strftime('%d-%m-%Y')
            }
            filter_end = week_end
            if filter_end > date_to:
                filter_end = date_to

        else:  # month
            start_of_next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            if start_of_next_month > date_to:
                filter_end = date_to
            else:
                filter_end = start_of_next_month - timedelta(days=1)
            item = {'Year': year, 'Month': month}

        filtered_trips = Full_Data.objects.filter(timestamp__date__range=(filter_start, filter_end))

        if filter == 'harbor and type':

            count = (filtered_trips.values('imo', 'ship_id', 'current_port', 'ais_type_summary').distinct())
            if harbor:
                count = count.filter(current_port=harbor)
                all_possible_locations = [harbor]

            if type:
                count = count.filter(ais_type_summary__in=type_list)
                all_possible_types = type_list

            for location in all_possible_locations:
                if location not in item:
                    item[location] = {}
                    for t in all_possible_types:
                        item[location][t] = 0

                # Count distinct entries and update the item
            for counts in count:
                port = counts['current_port']
                ais_type = counts['ais_type_summary']
                if port in item and ais_type in item[port]:
                    item[port][ais_type] += 1  # Increment the count for the port and type

                # Ensure all possible locations and types are included in item
            for location in all_possible_locations:
                if location not in item:
                    item[location] = {}
                    for t in all_possible_types:
                        item[location][t] = 0

        elif filter == 'harbor':

            count = (filtered_trips.values('imo', 'ship_id', 'current_port').distinct())
            if harbor:
                count = count.filter(current_port=harbor)
                all_possible_locations = [harbor]

            port_counts = {location: 0 for location in all_possible_locations}

            for count_item in count:
                port = count_item['current_port']
                if port in port_counts:
                    port_counts[port] += 1
            item.update(port_counts)

            for location in all_possible_locations:
                if location not in item:
                    item[location] = 0

        elif filter == 'type':
            count = (
                filtered_trips.filter(current_port__in=all_possible_locations).values('imo', 'ship_id', 'current_port',
                                                                                      'ais_type_summary').distinct())
            if type:
                count = count.filter(ais_type_summary__in=type_list)
                all_possible_types = type_list

            type_counts = {types: 0 for types in all_possible_types}
            for count_item in count:
                port = count_item['ais_type_summary']
                if port in type_counts:
                    type_counts[port] += 1
            item.update(type_counts)

            for types in all_possible_types:
                if types not in item:
                    item[types] = 0

        elif filter == 'all':
            count = (
                filtered_trips.filter(current_port__in=all_possible_locations).values('imo', 'ship_id', 'current_port').distinct())
            total_count = 0
            for count_item in count:
                port = count_item['current_port']
                if port in all_possible_locations:
                    total_count += 1
            item['total_count'] = total_count
        response_data.append(item)
        current_date = filter_end + timedelta(days=1)

    return JsonResponse(response_data, safe=False)


@api_view(http_method_names=['GET'])
def mer_visual_harbour(request):
    date_from = datetime.strptime(request.GET.get('date_from'), '%Y-%m-%d').date()
    date_to = datetime.strptime(request.GET.get('date_to'), '%Y-%m-%d').date()

    filter = request.GET.get('filter')  # 'harbor and type', 'harbor' or 'type'
    harbor = request.GET.get('harbor')
    type = request.GET.get('type')
    grouping_level = request.GET.get('group_by')

    if type:
        type_list = type.split(',')

    all_possible_types = Full_Data.objects.exclude(ais_type_summary='').values_list('ais_type_summary', flat=True).\
        distinct()
    all_possible_locations = ['KARACHI', 'PORT QASIM', 'GWADAR']

    response_data = []

    # Sets to keep track of unique ships counted for arrival and departure
    unique_arrival_ships = set()
    unique_departure_ships = set()

    current_date = date_from
    while current_date <= date_to:
        year = current_date.year
        month = current_date.strftime('%B')
        filter_start = current_date
        week_end = current_date + timedelta(days=6)

        if grouping_level == 'day':
            item = {'Year': year, 'Month': month, 'Date': current_date.day}
            filter_end = current_date
        elif grouping_level == 'week':
            if week_end > date_to:
                week_end = date_to
            item = {
                'Year': year,
                'Week_Start': current_date.strftime('%d-%m-%Y'),
                'Week_End': week_end.strftime('%d-%m-%Y')
            }
            filter_end = week_end
            if filter_end > date_to:
                filter_end = date_to

        else:  # month
            start_of_next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            if start_of_next_month > date_to:
                filter_end = date_to
            else:
                filter_end = start_of_next_month - timedelta(days=1)
            item = {'Year': year, 'Month': month}

        filtered_trips = Full_Data.objects.filter(timestamp__date__range=(filter_start, filter_end))

        if filter == 'harbor and type':
            arrival = (filtered_trips.filter(current_port__in=all_possible_locations).
                       values('imo', 'ship_id', 'current_port', 'last_port', 'ais_type_summary').distinct())
            if harbor:
                arrival = arrival.filter(current_port=harbor)
                all_possible_locations = [harbor]

            if type:
                arrival = arrival.filter(ais_type_summary__in=type_list)
                all_possible_types = type_list

            for location in all_possible_locations:
                if location not in item:
                    item[location] = {}
                    for t in all_possible_types:
                        item[location][t] = {'arrival': 0, 'departure': 0}

            for counts in arrival:
                ship_id = (counts['imo'], counts['ship_id'], counts['current_port'])
                if ship_id not in unique_arrival_ships:
                    unique_arrival_ships.add(ship_id)
                    port = counts['current_port']
                    ais_type = counts['ais_type_summary']
                    if port in item and ais_type in item[port]:
                        item[port][ais_type]['arrival'] += 1  # Increment the count for the port and type

            for arrival_ship in unique_arrival_ships:
                imo, ship_id, arrival_port = arrival_ship
                ship_trips = filtered_trips.filter(imo=imo, ship_id=ship_id).order_by('timestamp')
                previous_port = arrival_port

                for trip in ship_trips:
                    current_port = trip.current_port
                    last_port = trip.last_port
                    next_port = trip.next_port_name
                    ais_type = trip.ais_type_summary

                    if current_port != previous_port:
                        if last_port != previous_port and (next_port != previous_port or next_port is None):
                            if previous_port in item and ais_type in item[port] and arrival_ship not in unique_departure_ships:
                                item[previous_port][ais_type]['departure'] -= 1
                                unique_departure_ships.add(arrival_ship)
                            break
                    previous_port = current_port

        elif filter == 'harbor':
            arrival = (filtered_trips.filter(current_port__in=all_possible_locations).
                       values('imo', 'ship_id', 'current_port', 'last_port').distinct())
            if harbor:
                arrival = arrival.filter(current_port=harbor)
                all_possible_locations = [harbor]

            port_counts = {location: {'arrival': 0, 'departure': 0} for location in all_possible_locations}

            for count_item in arrival:
                ship_id = (count_item['imo'], count_item['ship_id'], count_item['current_port'])
                if ship_id not in unique_arrival_ships:
                    unique_arrival_ships.add(ship_id)
                    port = count_item['current_port']
                    if port in port_counts:
                        port_counts[port]['arrival'] += 1

            for arrival_ship in unique_arrival_ships:
                imo, ship_id, arrival_port = arrival_ship
                ship_trips = filtered_trips.filter(imo=imo, ship_id=ship_id).order_by('timestamp')
                previous_port = arrival_port

                for trip in ship_trips:
                    current_port = trip.current_port
                    last_port = trip.last_port
                    next_port = trip.next_port_name

                    if current_port != previous_port:
                        if last_port != previous_port and (next_port != previous_port or next_port is None):
                            if previous_port in port_counts and arrival_ship not in unique_departure_ships:
                                port_counts[previous_port]['departure'] -= 1
                                unique_departure_ships.add(arrival_ship)
                            break
                    previous_port = current_port
            item.update(port_counts)

            for location in all_possible_locations:
                if location not in item:
                    item[location] = 0

        elif filter == 'type':
            arrival = (filtered_trips.filter(current_port__in=all_possible_locations).
                values('imo', 'ship_id', 'current_port', 'last_port', 'ais_type_summary').distinct())

            if type:
                arrival = arrival.filter(ais_type_summary__in=type_list)
                all_possible_types = type_list

            type_counts = {types: {'arrival': 0, 'departure': 0} for types in all_possible_types}

            for count_item in arrival:
                ship_id = (count_item['imo'], count_item['ship_id'], count_item['current_port'])
                if ship_id not in unique_arrival_ships:
                    unique_arrival_ships.add(ship_id)
                    port = count_item['ais_type_summary']
                    if port in type_counts:
                        type_counts[port]['arrival'] += 1

            for arrival_ship in unique_arrival_ships:
                imo, ship_id, arrival_port = arrival_ship
                ship_trips = filtered_trips.filter(imo=imo, ship_id=ship_id).order_by('timestamp')
                previous_port = arrival_port

                for trip in ship_trips:
                    current_port = trip.current_port
                    last_port = trip.last_port
                    next_port = trip.next_port_name
                    ais_type = trip.ais_type_summary

                    if current_port != previous_port:
                        if last_port != previous_port and (next_port != previous_port or next_port is None):
                            if previous_port in all_possible_locations and ais_type in type_counts and arrival_ship not in unique_departure_ships:
                                type_counts[ais_type]['departure'] -= 1
                                unique_departure_ships.add(arrival_ship)
                            break
                    previous_port = current_port
            item.update(type_counts)

            for types in all_possible_types:
                if types not in item:
                    item[types] = 0

        elif filter == 'all':
            arrival = (filtered_trips.filter(current_port__in=all_possible_locations).
                       values('imo', 'ship_id', 'current_port', 'last_port').distinct())

            total_arrival = 0
            total_departure = 0

            for count_item in arrival:
                ship_id = (count_item['imo'], count_item['ship_id'], count_item['current_port'])
                if ship_id not in unique_arrival_ships:
                    unique_arrival_ships.add(ship_id)
                    port = count_item['current_port']
                    if port in all_possible_locations:
                        total_arrival += 1

            for arrival_ship in unique_arrival_ships:
                imo, ship_id, arrival_port = arrival_ship
                ship_trips = filtered_trips.filter(imo=imo, ship_id=ship_id).order_by('timestamp')
                previous_port = arrival_port

                for trip in ship_trips:
                    current_port = trip.current_port
                    last_port = trip.last_port
                    next_port = trip.next_port_name

                    if current_port != previous_port:
                        if last_port != previous_port and (next_port != previous_port or next_port is None):
                            if previous_port in all_possible_locations and arrival_ship not in unique_departure_ships:
                                total_departure -= 1
                                unique_departure_ships.add(arrival_ship)
                            break
                    previous_port = current_port

            item['arrival'] = total_arrival
            item['departure'] = total_departure

        response_data.append(item)
        current_date = filter_end + timedelta(days=1)

    return JsonResponse(response_data, safe=False)


def get_country_name(country_code):
    try:
        return pycountry.countries.get(alpha_2=country_code).name
    except AttributeError:
        return country_code  # Fallback to code if not found


@api_view(['GET'])
def mer_visual_flag_count(request):
    date_from = datetime.strptime(request.GET.get('date_from'), '%Y-%m-%d').date()
    date_to = datetime.strptime(request.GET.get('date_to'), '%Y-%m-%d').date()

    filter = request.GET.get('filter')
    harbor = request.GET.get('harbor')
    type = request.GET.get('type')
    grouping_level = request.GET.get('group_by')

    all_possible_types = Full_Data.objects.exclude(next_port_country='').values_list('next_port_country', flat=True).distinct()
    all_possible_locations = ['KARACHI', 'PORT QASIM', 'GWADAR']

    response_data = []

    current_date = date_from
    while current_date <= date_to:
        year = current_date.year
        month = current_date.strftime('%B')
        filter_start = current_date
        week_end = current_date + timedelta(days=6)

        if grouping_level == 'day':
            item = {'Year': year, 'Month': month, 'Date': current_date.day}
            filter_end = current_date
        elif grouping_level == 'week':
            if week_end > date_to:
                week_end = date_to
            item = {
                'Year': year,
                'Week_Start': current_date.strftime('%d-%m-%Y'),
                'Week_End': week_end.strftime('%d-%m-%Y')
            }
            filter_end = week_end
            if filter_end > date_to:
                filter_end = date_to
        else:  # month
            start_of_next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            if start_of_next_month > date_to:
                filter_end = date_to
            else:
                filter_end = start_of_next_month - timedelta(days=1)
            item = {'Year': year, 'Month': month}

        filtered_trips = Full_Data.objects.filter(timestamp__date__range=(filter_start, filter_end))

        if filter == 'harbor and type':
            count = filtered_trips.values('imo', 'ship_id', 'current_port', 'next_port_country').distinct()
            if harbor:
                count = count.filter(current_port=harbor)
                all_possible_locations = [harbor]

            if type:
                count = count.filter(next_port_country=type)
                all_possible_types = [type]

            for location in all_possible_locations:
                if location not in item:
                    item[location] = {}
                    for t in all_possible_types:
                        full_type_name = get_country_name(t)
                        item[location][full_type_name] = 0

            for counts in count:
                port = counts['current_port']
                ais_type = counts['next_port_country']
                full_type_name = get_country_name(ais_type)
                if port in item and full_type_name in item[port]:
                    item[port][full_type_name] += 1

            for location in all_possible_locations:
                if location not in item:
                    item[location] = {}
                    for t in all_possible_types:
                        full_type_name = get_country_name(t)
                        item[location][full_type_name] = 0

        elif filter == 'type':
            count = filtered_trips.filter(current_port__in=all_possible_locations).values('imo', 'ship_id', 'current_port', 'next_port_country').distinct()
            if type:
                count = count.filter(next_port_country=type)
                all_possible_types = [type]

            type_counts = {get_country_name(types): 0 for types in all_possible_types}
            for count_item in count:
                port = count_item['next_port_country']
                full_type_name = get_country_name(port)
                if full_type_name in type_counts:
                    type_counts[full_type_name] += 1
            item.update(type_counts)

            for types in all_possible_types:
                full_type_name = get_country_name(types)
                if full_type_name not in item:
                    item[full_type_name] = 0

        response_data.append(item)
        current_date = filter_end + timedelta(days=1)

    return JsonResponse(response_data, safe=False)
