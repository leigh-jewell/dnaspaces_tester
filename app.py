from flask import Flask, request, render_template
import json
from math import sqrt
from datetime import datetime as dt
from activate import process_activation
import requests
import statistics
import re
from PIL import Image
import base64
import io
from io import BytesIO

SVG_WIDTH = 1200
SVG_HEIGHT = 400
MAX_EVENTS = 500
app = Flask(__name__)

# Client template
client_template = {
    "search_mode": True,
    "mac": "",
    "x": 0.0,
    "y": 0.0,
    "ssid": "",
    "rssi": "",
    "unit": "feet",
    "test_time": 10,
    "start_time": None,
    "number_updates": 0,
    "location_updates": [],
    "filename": "",
    "location": "",
    "tracking": False,
    "number_events": 0,
    "total_events": 0,
    "map_id": "none",
    "map_width": 0.0,
    "map_height": 0.0
}


def calc_distance(x1, y1, x2, y2, real_location, predicted_location):
    if real_location == "":
        print(f"calc_distance(): Location id not provided. Using first location_id {predicted_location}")
        real_location = predicted_location
    if real_location == predicted_location:
        distance = sqrt((x1 - x2)**2 + (y1 - y2)**2)
    else:
        distance = -1.0
    return round(distance, 1)


def client_update(client, data):
    distance_error = calc_distance(client['x'], client['y'], data['x'], data['y'], client['location_id'],
                                   data['location_id'])
    time_delta = abs(round((data['record_timestamp'] - client['start_time']).total_seconds(), 1))
    print(f"client_update(): Distance error {distance_error} "
          f"time secs {time_delta} {client['start_time']} {data['record_timestamp']}")
    location_updates = {'timestamp': data['record_timestamp'],
                        'mac': data['mac'],
                        'username': data['username'],
                        'x': data['x'],
                        'y': data['y'],
                        'ssid': data['ssid'],
                        'rssi': data['rssi'],
                        'error': distance_error,
                        'seconds': time_delta,
                        'location': data['location'],
                        'location_id': data['location_id'],
                        'confidence_factor': data['confidence_factor'],
                        'map_id': data['map_id'],
                        'last_seen': data['last_seen']
                        }

    return location_updates


def feet_to_mts(distance_feet):
    try:
        return round(distance_feet * 0.3048, 1)
    except TypeError:
        print("feet_to_mts(): Error not a number. Returning 0.0")
        return 0.0


@app.route('/activate', methods=['POST'])
def activate_app():
    if request.method == 'GET':
        return render_template('activate.html')
    else:
        # Check to see if we got activation token
        if request.form['token']:
            token = request.form['token']
            print(f"activate_app(): Got activation token:{token}")
            api_key = process_activation(token)
        else:
            print("activate_app(): Form didn't provide api_key or token.")
        return render_template('index.html', api_key=api_key, client=client_template,
                               img_data="", img_width=0.0, img_height=0.0, dim_width=0.0,
                               dim_length=0.0
                               )


def get_location(event):
    location = "UNKNOWN"
    try:
        location = ">".join(
            (event['deviceLocationUpdate']['location']['parent']['parent']['name'],
             event['deviceLocationUpdate']['location']['parent']['name'],
             event['deviceLocationUpdate']['location']['name']))
    except KeyError as e:
        print(f"get_location(): ERROR: KeyError {e} when trying to extract location from {event}.")
    return location


def check_interesting_event(event, client):
    interesting_event = False
    print(f"check_interesting_event(): client {client}")
    print(f"check_interesting_event(): {event['eventType']} {event['deviceLocationUpdate']['device']['macAddress']} {event['deviceLocationUpdate']['location']['locationId']} {client['location']}")
    if event['eventType'] == "DEVICE_LOCATION_UPDATE":
        # Only interested in device location updates
        if event['deviceLocationUpdate']['device']['macAddress'] == client['mac']:
            # Mac matches
            if event['deviceLocationUpdate']['location']['locationId'] == client['location_id']:
                # Mac and provided client location_id matches, interesting.
                interesting_event = True
            elif not client['location_id']:
                # Mac matches but client location_id is empty
                if get_location(event) == client['location']:
                    # Mac matches and location matches
                    interesting_event = True
                elif not client['location']:
                    # Mac matches and client location id or location empty (not provided), interesting
                    interesting_event = True
        elif not client['mac']:
            # Mac is empty (not provided). See if location_id or location matches (search mode).
            if event['deviceLocationUpdate']['location']['locationId'] == client['location_id']:
                # Client location_id provided and matches, interesting
                interesting_event = True
            elif not client['location_id']:
                # Client location_id not provided, check location name
                    if client['location'] in get_location(event):
                        # Client location provided matches
                        interesting_event = True
                    elif not client['location']:
                        # Client location not provided, everything is interesting
                        interesting_event = True

    print(f"check_interesting_event(): interesting_event? {interesting_event}")
    return interesting_event


def get_data_from_json(json_event, client):
    number_location_updates = 0
    result = []
    username = ""
    data = {}
    try:
        if check_interesting_event(json_event, client):
            number_location_updates += 1
            data['record_timestamp'] = dt.fromtimestamp(json_event['recordTimestamp'] / 1000)
            data['mac'] = json_event['deviceLocationUpdate']['device']['macAddress']
            data['username'] = json_event['deviceLocationUpdate']['rawUserId']
            data['x'] = feet_to_mts(json_event['deviceLocationUpdate']['xPos'])
            data['y'] = feet_to_mts(json_event['deviceLocationUpdate']['yPos'])
            data['location'] = get_location(json_event)
            data['location_id'] = json_event['deviceLocationUpdate']['location']['locationId']
            data['confidence_factor'] = feet_to_mts(json_event['deviceLocationUpdate']['confidenceFactor'])
            data['map_id'] = json_event['deviceLocationUpdate']['mapId']
            data['ssid'] = json_event['deviceLocationUpdate']['ssid']
            data['rssi'] = json_event['deviceLocationUpdate']['maxDetectedRssi']
            data['last_seen'] = dt.fromtimestamp(json_event['deviceLocationUpdate']['lastSeen'] / 1000)
            result = client_update(client, data)
        else:
            print(f"get_data_from_json(): Not a device location update {json_event['eventType']}")
    except KeyError as e:
        print(f"get_data_from_json(): Unable to extract all data from json. Error: {e}")

    return result


def post_process_results(location_updates):
    first_update = True
    processed = []
    stats = {'average_accuracy':0.0,
             'median_accuracy':0.0,
             'precision_20':0.0,
             'precision_15':0.0,
             'precision_10':0.0,
             'precision_5':0.0,
             'average_latency':0.0,
             'median_latency':0.0
             }
    total_error = 0
    number_updates = 0
    total_precision_20 = 0.0
    total_precision_15 = 0.0
    total_precision_10 = 0.0
    total_precision_5 = 0.0
    total_latency = 0.0
    latency_list = []
    accuracy_list = []
    location_changed = 0
    if len(location_updates) <= 0:
        print("post_process_results(): Nothing to process.")
    else:
        for update in location_updates:
            number_updates += 1
            timestamp = update['timestamp']
            mac = update['mac']
            username = update['username']
            x = update['x']
            y = update['y']
            ssid = update['ssid']
            rssi = update['rssi']
            error = update['error']
            location = update['location']
            location_id = update['location_id']
            confidence_factor = update['confidence_factor']
            map_id = update['map_id']
            last_seen = update['last_seen']
            if first_update:
                prev_timestamp = timestamp
                first_update = False
            time_delta = round((timestamp - prev_timestamp).total_seconds(), 1)
            prev_timestamp = timestamp
            timestamp_formatted = timestamp.astimezone().isoformat()
            if error < 0.0:
                print(f"post_process_results(): Change floor event. Ignoring error {error}")
                location_changed += 1
            else:
                total_error += error
                total_latency += time_delta
                latency_list.append(time_delta)
                accuracy_list.append(error)
                if error <= 20.0:
                    total_precision_20 += 1
                if error <= 15.0:
                    total_precision_15 += 1
                if error <= 10.0:
                    total_precision_10 += 1
                if error <= 5.0:
                    total_precision_5 += 1
            processed.append({'timestamp': timestamp_formatted,
                              'mac': mac,
                              'username': username,
                              'x': x,
                              'y': y,
                              'ssid': ssid,
                              'rssi': rssi,
                              'error': error,
                              'seconds': time_delta,
                              'location': location,
                              'location_id': location_id,
                              'confidence_factor': confidence_factor,
                              'map_id': map_id,
                              'last_seen': last_seen})
        if total_error > 0 and number_updates > 0:
            stats['average_accuracy'] = round(total_error/number_updates, 1)
            stats['median_accuracy'] = round(statistics.median(accuracy_list), 1)
            stats['precision_20'] = get_percentage(total_precision_20, number_updates)
            stats['precision_15'] = get_percentage(total_precision_15, number_updates)
            stats['precision_10'] = get_percentage(total_precision_10, number_updates)
            stats['precision_5'] = get_percentage(total_precision_5, number_updates)
            stats['average_latency'] = round(total_latency/number_updates, 1)
            stats['median_latency'] = round(statistics.median(latency_list), 1)
        stats['floor_change'] = location_changed
        print(f"post_process_results(): {stats}")

    return processed, stats


def get_percentage(total, n):
    percent = (total/n)*100
    return round(percent, 1)


def get_updates(client, key):
    updates = []
    stats = {}
    number_events = 0
    number_location_updates = 0
    headers = {'X-API-Key': key}
    # Connect to API    
    stream_api = requests.get('https://partners.dnaspaces.io/api/partners/v1/firehose/events',
                              stream=True, headers=headers)
    print(f"post_process_results(): Got status code {stream_api.status_code} from partners.dnaspaces.io.")
    # Remember time we started.
    start_time = dt.now()
    if stream_api.status_code == 200:
        # Read in an update from Firehose API
        for line in stream_api.iter_lines():
            number_events += 1
            # Extract the data from the event
            data = json.loads(line)
            result = get_data_from_json(data, client)
            # Check if any interesting events are returned.
            if len(result) > 0:
                updates.append(result)
                number_location_updates += 1
            # Check how long we have been reading the events for and stop if its longer than the test time
            process_time_secs = round((dt.now() - start_time).total_seconds(), 0)
            print(f"post_process_results(): Progress {round((process_time_secs/client['test_time'])*100,1)}% complete."
                  f"post_process_results(): Total events {number_events} "
                  f"Interesting events {number_location_updates}")
            if process_time_secs > client['test_time'] or number_location_updates > MAX_EVENTS:
                print(f"post_process_results(): Complete, time taken {process_time_secs}sec "
                      f"Number of events {number_location_updates}")
                break
    updates_processed, stats = post_process_results(updates)

    return updates_processed, number_location_updates, number_events, stats


def get_location_id(list_updates):
    map_id = ""
    location_id = ""
    print(f"get_location_id(): List of updates {list_updates}")
    for update in list_updates:
        if "location_id" in update:
            print(f"get_location_id(): Location id {update['location_id']}")
            location_id = update['location_id']
            break

    return location_id


def get_number_locations(list_updates):
    number_location_id = 0
    prev_location_id = ""
    for update in list_updates:
        if prev_location_id != update['location_id']:
            prev_location_id = update['location_id']
            number_location_id += 1
    print(f"get_number_locations(): Found {number_location_id} in the updates.")
    return number_location_id


@app.route('/', methods=['POST'])
def track_client():
    stats = {}
    processing_error = False
    client = client_template.copy()
    # Start tracking a client on the firehose API
    print(request.form)
    try:
        api_key = request.form['api_key']
    except KeyError:
        print("track_client(): Error: missing api_key")
        api_key = "Unknown"
    print(f"track_client(): Track client with {api_key}")
    try:
        client['mac'] = request.form['mac_address']
        if len(client['mac']) > 0 and re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", client['mac'].lower()):
            print("track_client(): Got valid mac address.")
            client['search_mode'] = False
        else:
            print(f"track_client(): No MAC address provided. Search mode activated.")
            client['mac'] = ""
            client['search_mode'] = True
    except KeyError:
        print(f"track_client(): Error: No mac address.")
        processing_error = True
    try:
        client['x'] = float(request.form['x_coordinates'])
    except KeyError:
        print(f"track_client(): Error: No x value.")
        client['x'] = 0.0
    except ValueError:
        print("track_client(): Error: Unable to convert x to float.")
        client['x'] = 0.0
    try:
        client['y'] = float(request.form['y_coordinates'])
    except KeyError:
        print(f"track_client(): Error: No y value.")
        client['y'] = 0.0
    except ValueError:
        print("track_client(): Error: Unable to convert y to float.")
        client['y'] = 0.0
    try:
        if request.form['measurement'] == "feet":
            client['x'] = feet_to_mts(client['x'])
            client['y'] = feet_to_mts(client['y'])
            client['unit'] = "feet"
            print(f"track_client(): Converted real x,y to metres {client['x']} {client['y']}")
        else:
            client['unit'] = "metre"
    except ValueError as e:
        print("track_client(): Error: measurement input missing. Assuming metres.")
    try:
        client['location_id'] = request.form['location_id']
        client['location'] = request.form['location']
    except KeyError as e:
        print(f"track_client(): Error: Unable to get location or location_id {e}")
        client['location_id'] = ""
        client['location'] = ""
    try:
        client['test_time'] = int(request.form['test_time'])
    except KeyError:
        print("track_client(): Error: Unable to get test_time.")
        client['test_time'] = 10
    except ValueError:
        print("track_client(): Error: Unable to test_time to int.")
        processing_error = True
    client['start_time'] = dt.now()
    client['number_updates'] = 0
    if not processing_error:
        client['location_updates'], client['number_updates'], client['total_events'], stats = get_updates(client, api_key)
        client['tracking'] = True
        print(f"track_client(): Finished tracking {client['mac']}, got following number of events {client['number_updates'] }")
        if get_number_locations(client['location_updates']) == 1:
            # We only found a single location so we can retrieve the map to display.
            display_map = True
            if client['location_id'] == "":
                # Location_id wasn't provided in the user input so we need to find it.
                location_id = get_location_id(client['location_updates'])
            else:
                location_id = client['location_id']
            map_img, map_width, map_height, dim_width, dim_length = get_map(location_id, api_key)
        else:
            # We got more than one location, so don't display the map.
            display_map = False
            map_width = 0
            map_height = 0
            dim_width = 0
            dim_length = 0
            map_img = ""

    if client['unit'] == "feet":
        print("track_client(): Converting real location back to feet.")
        client['x'] = round(client['x'] * 3.3, 1)
        client['y'] = round(client['y'] * 3.3, 1)
    print(f"track_client(): Display map {display_map}")
    return render_template('index.html', api_key=api_key, client=client, stats=stats,
                           img_data=map_img, img_width=map_width, img_height=map_height, dim_width=dim_width,
                           dim_length=dim_length, display_map=display_map)


@app.route('/', methods=['GET'])
def get_home_page():
    print(client_template)
    return render_template('index.html', api_key="", client=client_template, stats={},
                           img_data="", img_width=0.0, img_height=0.0, dim_width=0.0,
                           dim_length=0.0
                           )


def get_image_scale_ratio(img_width, img_height, view_width, view_height):
    if img_width > img_height:
        print(f"get_image_scale_ratio(): img_width {img_height} greater than img_height {img_height}")
        ratio = round(view_width/img_width, 2)
    else:
        print(f"get_image_scale_ratio():  img_height {img_height} greater than img_width {img_height}")
        ratio = round(view_height/img_height, 2)
    print(f"get_image_scale_ratio(): image scale ratio {ratio}")
    return ratio


def get_map(location_id, api_key):
    error = False
    encoded_img_data = ""
    decode_img_data = ""
    print(f"get_image(): loction id {location_id}")
    headers = {'X-API-Key': api_key}
    img_width = 0
    img_height = 0
    dimension_width = 0
    dimension_length = 0
    try:
        request_location_info = requests.get(f"https://partners.dnaspaces.io/api/partners/v1/locations/{location_id}",
                                             headers=headers)
        print(f"get_map(): Got status code: {request_location_info.status_code} from partners.dnaspaces.io.")
    except requests.exceptions.RequestException as e:
        print(f"get_map(): Error: getting map information to partners.dnaspaces.io {e}")
        error = True
    if not error and request_location_info.status_code == 200:
        print("get_map(): Successfully got map info.")
        error = False
        location_info = request_location_info.json()
        try:
            map_info = location_info['locationDetails']['mapDetails']
        except ValueError as e:
            print(f"get_map(): Error: Tried to extract mapDetails from location but got an error {e}")
        print(f"get_map(): Map info mapId {map_info['mapId']} width {map_info['imageWidth']} height {map_info['imageHeight']}")
        try:
            map_id = map_info['mapId']
            img_width = float(map_info['imageWidth'])
            img_height = float(map_info['imageHeight'])
            img_scale_ratio = get_image_scale_ratio(img_width, img_height, SVG_WIDTH, SVG_HEIGHT)
            img_width_scaled = img_width * img_scale_ratio
            img_height_scaled = img_height * img_scale_ratio
            dimension_width = feet_to_mts(float(map_info['dimension']['width']))
            dimension_length = feet_to_mts(float(map_info['dimension']['length']))
            print(f"get_map(): Image width {img_width_scaled} image height {img_height_scaled} floor width (mtrs) {dimension_width} floor length (mtrs) {dimension_length}")
        except ValueError:
            print("get_map(): Image width and height not returned.")
            error = True
        try:
            r = requests.get(f"https://partners.dnaspaces.io/api/partners/v1/maps/{map_id}/image", headers=headers)
            print(f"get_map(): Got status code {r.status_code} from partners.dnaspaces.io.")
        except requests.exceptions.RequestException as e:
            print(f"get_map(): Error: getting map from partners.dnaspaces.io {e}")
            error = True
        if not error and r.status_code == 200:
            print("get_map(): Successfully got map image. Converting image.")
            im = Image.open(BytesIO(r.content))
            data = io.BytesIO()
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            im.save(data, "JPEG")
            encoded_img_data = base64.b64encode(data.getvalue())
            decode_img_data = encoded_img_data.decode('utf-8')

    return decode_img_data, img_width_scaled, img_height_scaled, dimension_width, dimension_length


if __name__ == '__main__':
    app.run()
