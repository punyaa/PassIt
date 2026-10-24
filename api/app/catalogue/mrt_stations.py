"""MRT stations with approximate coordinates and the URA planning area they sit in.

A curated subset spread across Singapore, enough for nearest-station filtering in the
prototype. B3 can replace it with the full LTA station dataset without changing callers.
Coordinates are approximate (station centroid, about 100 m accuracy).
"""

from math import asin, cos, radians, sin, sqrt
from typing import NamedTuple


class Station(NamedTuple):
    name: str
    latitude: float
    longitude: float
    planning_area: str


STATIONS: tuple[Station, ...] = (
    Station("Admiralty", 1.4406, 103.8009, "Woodlands"),
    Station("Aljunied", 1.3164, 103.8829, "Geylang"),
    Station("Ang Mo Kio", 1.3700, 103.8496, "Ang Mo Kio"),
    Station("Beauty World", 1.3412, 103.7758, "Bukit Timah"),
    Station("Bedok", 1.3240, 103.9300, "Bedok"),
    Station("Bishan", 1.3510, 103.8484, "Bishan"),
    Station("Boon Keng", 1.3195, 103.8618, "Kallang"),
    Station("Boon Lay", 1.3386, 103.7060, "Jurong West"),
    Station("Botanic Gardens", 1.3224, 103.8153, "Tanglin"),
    Station("Braddell", 1.3404, 103.8470, "Toa Payoh"),
    Station("Buangkok", 1.3829, 103.8930, "Sengkang"),
    Station("Bugis", 1.3008, 103.8559, "Downtown Core"),
    Station("Bukit Batok", 1.3490, 103.7496, "Bukit Batok"),
    Station("Bukit Gombak", 1.3587, 103.7518, "Bukit Batok"),
    Station("Bukit Panjang", 1.3784, 103.7623, "Bukit Panjang"),
    Station("Buona Vista", 1.3073, 103.7903, "Queenstown"),
    Station("Caldecott", 1.3375, 103.8395, "Toa Payoh"),
    Station("Changi Airport", 1.3574, 103.9886, "Changi"),
    Station("Chinatown", 1.2844, 103.8439, "Outram"),
    Station("Chinese Garden", 1.3423, 103.7326, "Jurong East"),
    Station("Choa Chu Kang", 1.3854, 103.7443, "Choa Chu Kang"),
    Station("City Hall", 1.2931, 103.8520, "Downtown Core"),
    Station("Clementi", 1.3151, 103.7652, "Clementi"),
    Station("Commonwealth", 1.3025, 103.7983, "Queenstown"),
    Station("Dhoby Ghaut", 1.2990, 103.8456, "Museum"),
    Station("Eunos", 1.3197, 103.9030, "Bedok"),
    Station("HarbourFront", 1.2653, 103.8220, "Bukit Merah"),
    Station("Hillview", 1.3627, 103.7675, "Bukit Batok"),
    Station("Hougang", 1.3713, 103.8924, "Hougang"),
    Station("Joo Koon", 1.3277, 103.6783, "Boon Lay"),
    Station("Jurong East", 1.3331, 103.7422, "Jurong East"),
    Station("Kallang", 1.3114, 103.8714, "Kallang"),
    Station("Kembangan", 1.3210, 103.9129, "Bedok"),
    Station("Kent Ridge", 1.2935, 103.7845, "Queenstown"),
    Station("Khatib", 1.4174, 103.8329, "Yishun"),
    Station("Kovan", 1.3602, 103.8853, "Hougang"),
    Station("Kranji", 1.4251, 103.7619, "Sungei Kadut"),
    Station("Lakeside", 1.3442, 103.7210, "Jurong West"),
    Station("Lavender", 1.3073, 103.8631, "Kallang"),
    Station("Little India", 1.3066, 103.8496, "Rochor"),
    Station("Lorong Chuan", 1.3517, 103.8642, "Serangoon"),
    Station("MacPherson", 1.3268, 103.8900, "Geylang"),
    Station("Marina Bay", 1.2763, 103.8546, "Downtown Core"),
    Station("Marymount", 1.3487, 103.8393, "Bishan"),
    Station("Newton", 1.3127, 103.8380, "Newton"),
    Station("Novena", 1.3204, 103.8438, "Novena"),
    Station("one-north", 1.2995, 103.7874, "Queenstown"),
    Station("Orchard", 1.3043, 103.8320, "Orchard"),
    Station("Outram Park", 1.2803, 103.8395, "Outram"),
    Station("Pasir Ris", 1.3731, 103.9493, "Pasir Ris"),
    Station("Paya Lebar", 1.3177, 103.8926, "Geylang"),
    Station("Pioneer", 1.3376, 103.6973, "Jurong West"),
    Station("Potong Pasir", 1.3313, 103.8690, "Toa Payoh"),
    Station("Punggol", 1.4052, 103.9024, "Punggol"),
    Station("Queenstown", 1.2945, 103.8060, "Queenstown"),
    Station("Raffles Place", 1.2840, 103.8514, "Downtown Core"),
    Station("Redhill", 1.2896, 103.8168, "Bukit Merah"),
    Station("Sembawang", 1.4491, 103.8201, "Sembawang"),
    Station("Sengkang", 1.3917, 103.8954, "Sengkang"),
    Station("Serangoon", 1.3498, 103.8737, "Serangoon"),
    Station("Simei", 1.3433, 103.9533, "Tampines"),
    Station("Somerset", 1.3006, 103.8389, "Orchard"),
    Station("Stevens", 1.3200, 103.8259, "Tanglin"),
    Station("Tai Seng", 1.3359, 103.8879, "Hougang"),
    Station("Tampines", 1.3533, 103.9452, "Tampines"),
    Station("Tanah Merah", 1.3272, 103.9465, "Bedok"),
    Station("Tanjong Pagar", 1.2765, 103.8458, "Downtown Core"),
    Station("Tiong Bahru", 1.2862, 103.8270, "Bukit Merah"),
    Station("Toa Payoh", 1.3327, 103.8474, "Toa Payoh"),
    Station("Upper Thomson", 1.3541, 103.8325, "Bishan"),
    Station("Woodlands", 1.4370, 103.7865, "Woodlands"),
    Station("Yew Tee", 1.3973, 103.7475, "Choa Chu Kang"),
    Station("Yio Chu Kang", 1.3818, 103.8449, "Ang Mo Kio"),
    Station("Yishun", 1.4295, 103.8350, "Yishun"),
)

STATIONS_BY_NAME = {station.name.lower(): station for station in STATIONS}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def nearest_station(latitude: float, longitude: float) -> Station:
    return min(STATIONS, key=lambda s: haversine_km(latitude, longitude, s.latitude, s.longitude))
