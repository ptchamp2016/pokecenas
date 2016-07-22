import os
import re
import sys
import json
import time
import struct
import random
import requests
import pprint
import logging

from threading import Thread

from pgoapi import PGoApi
from pgoapi.utilities import f2i, h2f
from pgoapi import utilities as util

from google.protobuf.internal import encoder
from geopy.geocoders import GoogleV3
from s2sphere import Cell, CellId, LatLng

DEBUG = True
API = None
FETCHING_DATA = False
Pokemons = []

log = logging.getLogger(__name__)

def postpone(function):
    def decorator(*args, **kwargs):
        t = Thread(target = function, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
    return decorator

def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)

def startLogger():
    # log format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

def getLocationByName(locationName):
    geolocator = GoogleV3()
    loc = geolocator.geocode(locationName)

    print('[!] Your given location: {}'.format(loc.address.encode('utf-8')))
    print('[!] lat/long: {} {}'.format(loc.latitude, loc.longitude))

    return (loc.latitude, loc.longitude, loc.altitude)

def get_cell_ids(lat, long, radius = 10):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, long)).parent(15)
    walk = [origin.id()]
    right = origin.next()
    left = origin.prev()

    # Search around provided radius
    for i in range(radius):
        walk.append(right.id())
        walk.append(left.id())
        right = right.next()
        left = left.prev()

    # Return everything
    return sorted(walk)

def get_key_from_pokemon(pokemon):
    return '{}-{}'.format(pokemon['spawnpoint_id'], pokemon['pokemon_data']['pokemon_id'])

def generate_spiral(starting_lat, starting_lng, step_size, step_limit):
    coords = [{'lat': starting_lat, 'lng': starting_lng}]
    steps,x,y,d,m = 1, 0, 0, 1, 1
    rlow = 0.0
    rhigh = 0.0005

    while steps < step_limit:
        while 2 * x * d < m and steps < step_limit:
            x = x + d
            steps += 1
            lat = x * step_size + starting_lat + random.uniform(rlow, rhigh)
            lng = y * step_size + starting_lng + random.uniform(rlow, rhigh)
            coords.append({'lat': lat, 'lng': lng})
        while 2 * y * d < m and steps < step_limit:
            y = y + d
            steps += 1
            lat = x * step_size + starting_lat + random.uniform(rlow, rhigh)
            lng = y * step_size + starting_lng + random.uniform(rlow, rhigh)
            coords.append({'lat': lat, 'lng': lng})

        d = -1 * d
        m = m + 1
    return coords

@postpone
def getSpiralData(lat, lng):
    global API
    global FETCHING_DATA
    global Pokemons
    if(FETCHING_DATA is False):
        FETCHING_DATA = True
        print('[+] getting Spiral Data')
        Pokemons = []
        poi = {'pokemons': {}, 'forts': []}
        step_size = 0.0015
        step_limit = 49
        coords = generate_spiral(lat, lng, step_size, step_limit)
        first = True
        for coord in coords:
            if(first is False):
                time.sleep(1)
            else:
                first = False

            lat = coord['lat']
            lng = coord['lng']
            API.set_position(lat, lng, 0)

            cell_ids = get_cell_ids(lat, lng)
            timestamps = [0,] * len(cell_ids)
            API.get_map_objects(latitude = util.f2i(lat), longitude = util.f2i(lng), since_timestamp_ms = timestamps, cell_id = cell_ids)
            response_dict = API.call()
            if 'status' in response_dict['responses']['GET_MAP_OBJECTS']:
                if response_dict['responses']['GET_MAP_OBJECTS']['status'] == 1:
                    for map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:
                        if 'wild_pokemons' in map_cell:
                            for pokemon in map_cell['wild_pokemons']:
                                pokekey = get_key_from_pokemon(pokemon)
                                pokemon['hides_at'] = time.time() + pokemon['time_till_hidden_ms']/1000
                                pokemon['poke_key'] = pokekey
                                if(pokekey not in poi['pokemons']):
                                    Pokemons.append(pokemon)
                                poi['pokemons'][pokekey] = pokemon

        FETCHING_DATA = False
        if(DEBUG):
            # print('POI dictionary: \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(poi)))
            print('POI dictionary: \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(Pokemons)))

def login(location=None):
    global API
    startLogger()
    API = PGoApi()

    position = getLocationByName(location)
    API.set_position(*position)
    ptc_username = os.environ.get('PTC_USERNAME', "Invalid")
    ptc_password = os.environ.get('PTC_PASSWORD', "Invalid")
    login_type = "ptc"

    print('[+] Authentication with ptc...')
    if not API.login(login_type, ptc_username, ptc_password):
        print('[-] Trouble logging in via PTC')
        print('[+] Authentication with Google...')
        goog_username = os.environ.get('GOOG_USERNAME', "Invalid")
        goog_password = os.environ.get('GOOG_PASSWORD', "Invalid")
        login_type = "google"
        if not API.login(login_type, goog_username, goog_password):
            log.error("[-] Trouble logging in via Google. Stopping")
            return False
    
    API.get_player()
    response_dict = API.call()
    if(DEBUG):
        print('Response dictionary: \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))
    
    getSpiralData(position[0], position[1])
    return True

def getPokemons():
    global FETCHING_DATA
    global Pokemons
    if(FETCHING_DATA is False):
        return Pokemons
    else:
        return {}

if __name__ == '__main__':
    main()