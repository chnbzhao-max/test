"""Postcode-centred radius filters using published Datahub coordinates."""
import math
import re
from functools import lru_cache
from urllib.parse import quote
import requests


def valid_point(point):
    return isinstance(point, dict) and all(type(point.get(k)) in (int, float) and math.isfinite(point[k]) for k in ('lat','lon')) and -90 <= point['lat'] <= 90 and -180 <= point['lon'] <= 180


def distance_km(one, two):
    if not valid_point(one) or not valid_point(two):
        raise ValueError('Invalid coordinates')
    lat1, lat2 = math.radians(one['lat']), math.radians(two['lat'])
    dlat = lat2-lat1
    dlon = math.radians(two['lon']-one['lon'])
    value = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,value))))


@lru_cache(maxsize=128)
def postcode_centre(postcode):
    postcode = re.sub(r'\s+', '', postcode).upper()
    if not re.fullmatch(r'(?:[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}|GIR0AA)', postcode):
        raise ValueError('Enter a complete UK postcode, such as SW1A 1AA')
    response = requests.get('https://api.postcodes.io/postcodes/'+quote(postcode, safe=''), timeout=10)
    if response.status_code == 404:
        raise ValueError('Postcode not found')
    response.raise_for_status()
    result = response.json()['result']
    point = {'lat': result['latitude'], 'lon': result['longitude']}
    if not valid_point(point):
        raise ValueError('Postcode provider returned invalid coordinates')
    return point
