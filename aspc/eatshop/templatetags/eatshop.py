from django import template
import datetime
import itertools
from django.core.cache import cache
import pickle
from aspc.eatshop.models import Hours

register = template.Library()

@register.inclusion_tag("eatshop/hours_fragment.html")
def format_hours(business):
    """
    Return business hours information with early morning hours
    presented as people would expect (i.e. Mon 4pm-1am instead of
    Mon 4pm-11:59pm + Tues 12am-1am)
    """

    # First, do we have this cached?
    cache_key = Hours.CACHE_KEY_TEMPLATE.format(id=business.id)
    hours_data = cache.get(cache_key)
    if hours_data:
        hours = pickle.loads(hours_data)
        return {
            "grouped_hours": hours['grouped_hours'],
            'hours_available': hours['hours_available']
        }

    # If it's not cached, we'll have to recompute the hours info...
    almost_midnight = datetime.time(23,59) # end of the day
    midnight = datetime.time(0,0) # beginning of the day

    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    combined = {}

    # Gather 'normal' hour ranges (not beginning at midnight)

    for day in weekdays:
        q = {day: True, 'begin__gt': midnight,}
        if business.hours.filter(**q).count():
            dayranges = combined.get(day, []) # get list of ranges to
                                              # append to

            raw_ranges = business.hours.filter(**q).values_list('begin', 'end')

            for b, e in raw_ranges:
                if e >= almost_midnight: # Clean midnight for display
                    dayranges.append((b, midnight))
                else:
                    dayranges.append((b,e))
            combined[day] = dayranges

    for day_idx, day in enumerate(weekdays):
        q = {day: True, 'begin': midnight,}

        # If there's no period starting at midnight for this day, skip it
        if not business.hours.filter(**q).count(): continue

        # Otherwise, take end of said period and replace midnight end time
        # of previous day (if it exists)

        midnight_period = business.hours.filter(**q)[0]
        old_pd = combined[weekdays[day_idx - 1]][-1] # Last pd yesterday
        if old_pd[1] == midnight:
            new_pd = (old_pd[0], midnight_period.end)
            combined[weekdays[day_idx - 1]][-1] = new_pd # Swap in new pd

    hours_as_list = [(a, combined.get(a, [])) for a in weekdays]
    total_times = sum([len(ranges) for day, ranges in hours_as_list])

    sorted_as_list = sorted(hours_as_list, key=lambda day: day[1])  # Sort by hours

    abbreviations = {
        'monday': 'Mon',
        'tuesday': 'Tues',
        'wednesday': 'Wed',
        'thursday': 'Thurs',
        'friday': 'Fri',
        'saturday': 'Sat',
        'sunday': 'Sun'
    }
    day_indices = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']

    #  Groups the sorted hour list into an array of groups where each group has equivalent hours
    grouped_list = []
    for hours, day_group in itertools.groupby(sorted_as_list, lambda day: day[1]):
        data = [hours, []]  # Array in format [(begin, end), [days]]
        for day in day_group:
            data[1].append(abbreviations[list(day)[0]])  # Converts iterator to a list, and then looks up the appropriate day abbreivation

        grouped_list.append(data)

    # Function for sorting groups by their respective earliest day
    def group_comparator_function(group):
        index = 6  # Assume Sunday
        for day in group[1]:
            if day_indices.index(day) < index:
                index = day_indices.index(day)  # If the day is earlier than the existing earliest, update the index

        return index  # Return the index of the earliest day in the group

    grouped_list = sorted(grouped_list, key=group_comparator_function)  # Sorts groups to ensure the group with Mon is always first, etc.

    # Function that checks if a list of days is in a sequence; i.e. [Mon, Tues, Wed] would return True
    def is_sequence(days):
        for i, day in enumerate(days):
            if day_indices.index(days[i]) + 1 != day_indices.index(days[(i + 1) % len(days)]):  # Checks if the next day follows the current one
                return False
            if i == len(days) - 2:  # No need to compare the last day to anything, so at this point assume True
                return True

    # Formats the string representation of each groups days
    for group in grouped_list:
        if is_sequence(group[1]):  # Checks if the days are in a sequence
            group[1] = group[1][0] + ' - ' + group[1][len(group[1]) - 1]  # If they are, format the days with a hyphen
        else:
            group[1] = ', '.join(group[1])  # If they aren't, format the days as a comma separated list

    context = {"grouped_hours": grouped_list, 'hours_available': total_times > 0}

    # Cache this so we don't have to hit the db again for a long time
    # (timeout=None means until the cache is flushed or a new value replaces it)
    cache.set(cache_key, pickle.dumps(context), None)
    return context
