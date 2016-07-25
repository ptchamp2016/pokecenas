import os
import re
import sys
import json
import time
import struct
import requests
import logging
import threading
import math
import calendar

from threading import Thread

from pgoapi import PGoApi
from pgoapi.utilities import f2i, h2f
from pgoapi import utilities as util

from google.protobuf.internal import encoder
from geopy.geocoders import GoogleV3
from s2sphere import Cell, CellId, LatLng
from datetime import datetime

API = None
FETCHING_DATA = False
CANCEL_FETCH = False
Pokemons = []
Pokestops = []
POKEMON_DATA = None
lat_gap_meters = 150
lng_gap_meters = 86.6

meters_per_degree = 111111
lat_gap_degrees = float(lat_gap_meters) / meters_per_degree
pokeSemaphore = threading.BoundedSemaphore()
stopSemaphore = threading.BoundedSemaphore()
fetchSemaphore = threading.BoundedSemaphore()

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

def print_gmaps_dbug(coords):
    url_string = 'http://maps.googleapis.com/maps/api/staticmap?size=400x400&path='
    for coord in coords:
        url_string += '{},{}|'.format(coord[0], coord[1])
    print(url_string[:-1])

def init():
    global POKEMON_DATA
    POKEMON_DATA = json.load(open('api/pokemon.json'))

    # log format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.WARNING)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.WARNING)

def getLocationByName(locationName):
    geolocator = GoogleV3()
    loc = geolocator.geocode(locationName)

    log.info('[!] Your given location: {}'.format(loc.address.encode('utf-8')))

    return (loc.latitude, loc.longitude, loc.altitude)

def get_cellid(lat, long):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, long)).parent(15)
    walk = [origin.id()]

    next = origin.next()
    prev = origin.prev()
    for i in range(10):
        walk.append(prev.id())
        walk.append(next.id())
        next = next.next()
        prev = prev.prev()
    return sorted(walk)

def calculate_lng_degrees(lat):
    return float(lng_gap_meters) / (meters_per_degree * math.cos(math.radians(lat)))

# def generate_location_steps(lat, lng, num_steps):
#     pos, x, y, dx, dy = 1, 0, 0, 0, -1

#     while -num_steps / 2 < x <= num_steps / 2 and -num_steps / 2 < y <= num_steps / 2:
#         yield (x * 0.00125 + lat, y * 0.00175 + lng, 0)

#         if x == y or (x < 0 and x == -y) or (x > 0 and x == 1 - y):
#             dx, dy = -dy, dx

#         x, y = x + dx, y + dy

def generate_location_steps(lat, lng, num_steps):
    ring = 1 #Which ring are we on, 0 = center
    lat_location = lat
    lng_location = lng

    yield (lat,lng, 0) #Middle circle

    while ring < num_steps:
        #Move the location diagonally to top left spot, then start the circle which will end up back here for the next ring 
        #Move Lat north first
        lat_location += lat_gap_degrees
        lng_location -= calculate_lng_degrees(lat_location)

        for direction in range(6):
            for i in range(ring):
                if direction == 0: #Right
                    lng_location += calculate_lng_degrees(lat_location) * 2

                if direction == 1: #Right Down
                    lat_location -= lat_gap_degrees
                    lng_location += calculate_lng_degrees(lat_location)

                if direction == 2: #Left Down
                    lat_location -= lat_gap_degrees
                    lng_location -= calculate_lng_degrees(lat_location)

                if direction == 3: #Left
                    lng_location -= calculate_lng_degrees(lat_location) * 2

                if direction == 4: #Left Up
                    lat_location += lat_gap_degrees
                    lng_location -= calculate_lng_degrees(lat_location)

                if direction == 5: #Right Up
                    lat_location += lat_gap_degrees
                    lng_location += calculate_lng_degrees(lat_location)

                yield (lat_location, lng_location, 0) #Middle circle

        ring += 1

def get_key_from_pokemon(pokemon):
    return '{}-{}'.format(pokemon['spawnpoint_id'], pokemon['encounter_id'])

def send_map_request(api, position):
    cell_ids = get_cellid(position[0], position[1])
    timestamps = [0,] * len(cell_ids)
    try:
        api.set_position(*position)
        api.get_map_objects(latitude=f2i(position[0]),
                            longitude=f2i(position[1]),
                            since_timestamp_ms = timestamps,
                            cell_id = cell_ids)
        return api.call()
    except Exception as e:
        log.warn("Uncaught exception when downloading map " + str(e))
        return False

@postpone
def getPoiData(lat, lng):
    global API
    global FETCHING_DATA
    global CANCEL_FETCH
    global Pokemons
    global Pokestops

    while FETCHING_DATA and CANCEL_FETCH:
        log.info("[!] Waiting previous loop to end")
        time.sleep(0.20)
    CANCEL_FETCH = False

    if(FETCHING_DATA is False):
        try:
            fetchSemaphore.acquire()
            FETCHING_DATA = True
        finally:
            fetchSemaphore.release()
        
        log.info('[+] getting Data')
        Pokemons = []
        Pokestops = []
        poi = {'pokemons': {}, 'forts': {}}
        num_steps = 8
        total_steps = (3 * (num_steps**2)) - (3 * num_steps) + 1
        origin = LatLng.from_degrees(lat, lng)

        coords = []

        for step, step_location in enumerate(generate_location_steps(lat, lng, num_steps), 1):
            if(CANCEL_FETCH is not True):
                response_dict = {}
                failed_consecutive = 0
                while not response_dict and not CANCEL_FETCH:
                    coords.append(step_location)
                    response_dict = send_map_request(API, step_location)
                    if response_dict:
                        try:
                            if 'status' in response_dict['responses']['GET_MAP_OBJECTS']:
                                if response_dict['responses']['GET_MAP_OBJECTS']['status'] == 1:
                                    for map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:
                                        if 'wild_pokemons' in map_cell:
                                            for pokemon in map_cell['wild_pokemons']:
                                                pokekey = get_key_from_pokemon(pokemon)
                                                pos = LatLng.from_degrees(pokemon['latitude'], pokemon['longitude'])
                                                d_t = datetime.utcfromtimestamp((pokemon['last_modified_timestamp_ms'] + pokemon['time_till_hidden_ms']) / 1000.0)
                                                if(pokekey not in poi['pokemons']):
                                                    try:
                                                        pokeSemaphore.acquire()
                                                        Pokemons.append({
                                                            "key": pokekey,
                                                            "id": pokemon['pokemon_data']['pokemon_id'],
                                                            "name": POKEMON_DATA[pokemon['pokemon_data']['pokemon_id'] - 1]['Name'],
                                                            "latitude": pokemon['latitude'],
                                                            "longitude": pokemon['longitude'],
                                                            "time_left": pokemon['time_till_hidden_ms'],
                                                            "hides_at": pokemon['last_modified_timestamp_ms'] + pokemon['time_till_hidden_ms'],
                                                            "distance": int(origin.get_distance(pos).radians * 6366468.241830914)
                                                        })
                                                    finally:
                                                        pokeSemaphore.release()
                                                poi['pokemons'][pokekey] = pokemon
                                        if 'forts' in map_cell:
                                            for pokestop in map_cell['forts']:
                                                if pokestop.get('type') == 1 and 'lure_info' in pokestop:  # Pokestops with lure
                                                    active_pokemon_id = pokestop['lure_info']['active_pokemon_id']
                                                    if(pokestop['id'] not in poi['forts']):
                                                        try:
                                                            stopSemaphore.acquire()
                                                            Pokestops.append({
                                                                "key": pokestop['id'],
                                                                "pokemon_name": POKEMON_DATA[active_pokemon_id - 1]['Name'],
                                                                "latitude": pokestop['latitude'],
                                                                "longitude": pokestop['longitude'],
                                                                "last_modified": pokestop['last_modified_timestamp_ms']
                                                            })
                                                        finally:
                                                            stopSemaphore.release()
                                                    poi['forts'][pokestop['id']] = pokestop
                        except KeyError:
                            log.error('Scan step {:d} failed. Response dictionary key error.'.format(step))
                            failed_consecutive += 1
                            if(failed_consecutive >= 5):
                                log.error('Servers Down. Waiting before trying again')
                                time.sleep(20)
                                failed_consecutive = 0
                    else:
                        log.warn('Fetch poi data failed. Going again')
                log.info('Completed {:5.2f}% of scan.'.format(float(step) / total_steps*100))
                # log.info('Completed {:5.2f}% of scan.'.format(float(step) / num_steps**2*100))
            else:
                log.info('Canceling Scan to start another')
                Pokemons = []
                break
        print_gmaps_dbug(coords)
        try:
            fetchSemaphore.acquire()
            FETCHING_DATA = False
        finally:
            fetchSemaphore.release()

def login(location=None):
    global API
    global CANCEL_FETCH
    init()
    try:
        API = PGoApi()
        CANCEL_FETCH = True

        position = getLocationByName(location)
        API.set_position(*position)

        goog_username = os.environ.get('GOOG_USERNAME', "Invalid")
        goog_password = os.environ.get('GOOG_PASSWORD', "Invalid")

        login_type = "google"

        log.info('[+] Authentication with Google...')
        if not API.login(login_type, goog_username, goog_password):
            log.warn('[-] Trouble logging in via Google')
            log.info('[+] Authentication with PTC...')
            ptc_username = os.environ.get('PTC_USERNAME', "Invalid")
            ptc_password = os.environ.get('PTC_PASSWORD', "Invalid")
            login_type = "ptc"
            if not API.login(login_type, ptc_username, ptc_password):
                log.error("[-] Trouble logging in via PTC. Stopping")
                return False
        
        API.get_player()
        response_dict = API.call()
        
        getPoiData(position[0], position[1])
        return True
    except Exception as e:
        log.error("Error login" + str(e));
        return false

def getPokemons():
    global Pokemons
    global FETCHING_DATA
    stop = False
    try:
        pokeSemaphore.acquire()
        data = Pokemons
        log.info("Getting Pokemon: %s", len(data))
        Pokemons = []
        fetchSemaphore.acquire()
        if not data and FETCHING_DATA is not True:
            stop = True
    finally:
        pokeSemaphore.release()
        fetchSemaphore.release()
    
    if stop:
        return True
    else:
        return data

def getLuredStops():
    global Pokestops
    try:
        stopSemaphore.acquire()
        data = Pokestops
        log.info("Getting Pokestops: %s", len(data))
        Pokestops = []
    finally:
        stopSemaphore.release()
    
    return data

def rescan(location=None):
    log.info("Rescaning")
    try:
        global CANCEL_FETCH
        CANCEL_FETCH = True
        position = getLocationByName(location)
        getPoiData(position[0], position[1])
    except Exception as e:
        log.error("Error rescaning" + str(e));
        return login(location)

    return True

    
if __name__ == '__main__':
    main()