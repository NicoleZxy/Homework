from datetime import date
import dateutil.relativedelta as rd
import re
from dateutil import rrule


monthes = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
month_to_int = {month: i + 1 for i, month in enumerate(monthes)}

def get_date(date_str):
    """
    Returns a datetime object from a string in the format "YYYY-MM-DD"
    """
    match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', date_str)
    if match:
        year, month, day = match.groups()
        start = date(int(year), int(month), int(day))
        end = start
        return start, end
    match = re.match(r'^(\d{4})([A-Z][a-z]{1,2})$', date_str)
    if match:
        year, month = match.groups()
        start = date(int(year), month_to_int[month], 1)
        end = start + rd.relativedelta(months=1) - rd.relativedelta(days=1)
        return start, end
    match = re.match(r'^(\d{4})Q(\d)$', date_str)
    if match:
        year, quarter = match.groups()
        start = date(int(year), int(quarter) * 3 - 2, 1)
        end = start + rd.relativedelta(months=3) - rd.relativedelta(days=1)
        return start, end
    match = re.match(r'^(\d{4})A$', date_str)
    if match:
        year, = match.groups()
        start = date(int(year), 1, 1)
        end = start + rd.relativedelta(years=1) - rd.relativedelta(days=1)
        return start, end
    raise ValueError("Invalid date string: {}".format(date_str))


def get_holidays(start, end):
    """
    Returns the holidays for the given period
    """

    syear = start.year
    eyear = end.year
    holidays = set()
    for year in range(syear, eyear+1):
        # New Year's Day
        if year > 1870:
            if date(year, 1, 1).weekday() == 6:  # Sunday
                holidays.add(date(year, 1, 2))
            else:
                holidays.add(date(year, 1, 1))
        # Memorial Day
        if year > 1970:
            holidays.add(date(year, 5, 31) + rd.relativedelta(weekday=rd.MO(-1)))
        elif year >= 1888:
            holidays.add(date(year, 5, 30))
        # Independence Day
        if year > 1870:
            if date(year, 7, 4).weekday() == 6:  # Sunday
                holidays.add(date(year, 7, 5))
            else:
                holidays.add(date(year, 7, 4))
        # Labor Day
        if year >= 1894:
            holidays.add(date(year, 9, 1) + rd.relativedelta(weekday=rd.MO))
        # Thanksgiving
        if year > 1870:
            holidays.add(date(year, 11, 1) + rd.relativedelta(weekday=rd.TH(+4)))
        # Christmas Day
        if year > 1870:
            if date(year, 12, 25).weekday() == 6:  # Sunday
                holidays.add(date(year, 12, 26))
            else:
                holidays.add(date(year, 12, 25))

    # Filter the holidays that are in the time range
    holidays = set(holiday for holiday in holidays if start <= holiday <= end)
    return holidays


def get_daylight_adjust(start, end):
    """
    Returns the daylight saving time adjustment for the time range.
    """

    syear = start.year
    eyear = end.year
    daylight_adjust = 0
    for year in range(syear, eyear+1):
        start_time = date(year, 3, 1) + rd.relativedelta(weekday=rd.SU(+2))
        end_time = date(year, 11, 1) + rd.relativedelta(weekday=rd.SU(+1))
        if start <= start_time <= end:
            daylight_adjust -= 1
        if start <= end_time <= end:
            daylight_adjust += 1

    return daylight_adjust


ISO_Regions_map = {
    "PJM": "eastern",
    "MISO": "eastern",
    "ERCOT": "eastern",
    "SPP": "eastern",
    "NYISO": "eastern",
    "WECC": "western",
    "CAISO": "western",
}

def get_hours(iso, ptype, period):
    """
    Returns the hours for the given period

    Parameters:
    iso: character, the ISO region, one of PJM/MISO/ERCOT/SPP/NYISO/WECC/CAISO
    ptype: character, the type of period, one of onpeak/offpeak/flat/2x16H/7x8
    period: character, one of the following:“2018-2-3” as a daily,“2018Mar” as a monthly,
         “2018Q2” as a quarterly, “2018A” as an annually.

    Returns:
    The number of hours
    """

    start, end = get_date(period)

    if ISO_Regions_map[iso] == "eastern":
        weekdays = range(5)
    else:
        weekdays = range(6)

    if iso == "MISO":
        daylight_adjust = 0
    else:
        daylight_adjust = get_daylight_adjust(start, end)

    holidays = get_holidays(start, end)
    all_day = set(map(lambda i: i.date(), rrule.rrule(dtstart=start, until=end, freq=rrule.DAILY)))
    all_weekdays = set(map(lambda i: i.date(), rrule.rrule(dtstart=start, until=end, freq=rrule.DAILY, byweekday=weekdays)))
    if ptype == "onpeak":
        days = len(all_weekdays - holidays)
        hours = days * 16
        return hours
    elif ptype == 'offpeak':
        days = len(all_weekdays - holidays)
        hours = days * 16
        hours = len(all_day) * 24 - hours
        hours += daylight_adjust
        return hours
    elif ptype == '2x16H':
        days = len((all_day - all_weekdays).union(holidays))
        hours = days * 16
        return hours
    elif ptype == '7x8':
        days = len(all_day)
        hours = days * 8
        hours += daylight_adjust
        return hours
    elif ptype == 'flat':
        hours = len(all_day) * 24
        hours += daylight_adjust
        return hours
    else:
        raise ValueError("Invalid peak type: {}".format(ptype))
