from flask import Flask, request, render_template, send_file, make_response
import json
from math import sqrt
from datetime import datetime as dt
from activate import process_activation
import requests
import statistics
import re
import pprint
from PIL import Image
import base64
import io
from io import BytesIO

IMAGE_SCALE = 0.5

app = Flask(__name__)

# Client template
client_template = {
    "search_mode": True,
    "mac": "",
    "x": 0.0,
    "y": 0.0,
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
        print(f"Location id not provided. Using first location_id {predicted_location}")
        real_location = predicted_location
    if real_location == predicted_location:
        distance = sqrt((x1 - x2)**2 + (y1 - y2)**2)
    else:
        distance = -1.0
    return round(distance, 1)


def client_update(client, record_timestamp, x, y, location, location_id, confidence_factor, map_id, mac, username):
    distance_error = calc_distance(client['x'], client['y'], x, y, client['location_id'], location_id)
    time_delta = abs(round((record_timestamp - client['start_time']).total_seconds(), 1))
    print(f"Distance error {distance_error} time secs {time_delta} {client['start_time']} {record_timestamp}")
    location_updates = {'timestamp': record_timestamp,
                        'mac': mac,
                        'username': username,
                        'x': x,
                        'y': y,
                        'error': distance_error,
                        'seconds': time_delta,
                        'location': location,
                        'location_id': location_id,
                        'confidence_factor': confidence_factor,
                        'map_id': map_id
                        }
    print(location_updates)

    return location_updates


def feet_to_mts(distance_feet):
    try:
        return round(distance_feet * 0.3048, 1)
    except TypeError:
        print("Error not a number")
        return 0.0


@app.route('/activate', methods=['POST'])
def activate_app():
    if request.method == 'GET':
        return render_template('activate.html')
    else:
        # Check to see if we got activation token
        if request.form['token']:
            token = request.form['token']
            print(f"Got activation token:{token}")
            api_key = process_activation(token)
        else:
            print("Form didn't provide api_key or token.")
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


def get_data_from_json(json_event, client):
    number_location_updates = 0
    result = []
    username = ""
    print(f"Device location update {json_event}")
    try:
        print(json_event['deviceLocationUpdate']['location'])
        if json_event['eventType'] == "DEVICE_LOCATION_UPDATE" \
                and (client['search_mode'] or
                     json_event['deviceLocationUpdate']['device']['macAddress'] == client['mac']):
            number_location_updates += 1
            time_stamp_datetime = dt.fromtimestamp(json_event['recordTimestamp'] / 1000)
            mac = json_event['deviceLocationUpdate']['device']['macAddress']
            username = json_event['deviceLocationUpdate']['rawUserId']
            x = feet_to_mts(json_event['deviceLocationUpdate']['xPos'])
            y = feet_to_mts(json_event['deviceLocationUpdate']['yPos'])
            location = get_location(json_event)
            location_id = json_event['deviceLocationUpdate']['location']['locationId']
            confidence_factor = feet_to_mts(json_event['deviceLocationUpdate']['confidenceFactor'])
            map_id = json_event['deviceLocationUpdate']['mapId']
            result = client_update(client, time_stamp_datetime, x, y, location, location_id, confidence_factor,
                                   map_id, mac, username)
            print(f"Device location update {json_event['eventType']} {username}")
        else:
            print(f"Not a device location update {json_event['eventType']}")
    except KeyError as e:
        print(f"Unable to extract all data from json. Error: {e}")

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
        print("INFO: Nothing to process.")
    else:
        for update in location_updates:
            number_updates += 1
            timestamp = update['timestamp']
            mac = update['mac']
            username = update['username']
            x = update['x']
            y = update['y']
            error = update['error']
            location = update['location']
            location_id = update['location_id']
            confidence_factor = update['confidence_factor']
            map_id = update['map_id']
            if first_update:
                prev_timestamp = timestamp
                first_update = False
            time_delta = round((timestamp - prev_timestamp).total_seconds(), 1)
            prev_timestamp = timestamp
            timestamp_formatted = timestamp.astimezone().isoformat()
            if error < 0.0:
                print(f"INFO: Change floor event. Ignoring error {error}")
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
                              'error': error,
                              'seconds': time_delta,
                              'location': location,
                              'location_id': location_id,
                              'confidence_factor': confidence_factor,
                              'map_id': map_id})
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
        print(f"Stats: {stats}")

    return processed, stats


def get_percentage(total, n):
    percent = (total/n)*100
    return round(percent, 1)


def get_samples(key):
    number_events = 0
    number_location_updates = 0
    headers = {'X-API-Key': key}
    # Connect to API
    stream_api = requests.get('https://partners.dnaspaces.io/api/partners/v1/firehose/events',
                              stream=True, headers=headers)
    print(f"Got status code {stream_api.status_code} from partners.dnaspaces.io.")
    # Remember time we started.
    start_time = dt.now()
    if stream_api.status_code == 200:
        # Read in an update from Firehose API
        for line in stream_api.iter_lines():
            number_events += 1

    return render_template('index.html', api_key=api_key, client=client, stats=stats,
                           img_data=map_img, img_width=map_width, img_height=map_height, dim_width=dim_width,
                           dim_length=dim_length)


def get_updates(client, key):
    updates = []
    stats = {}
    number_events = 0
    number_location_updates = 0
    headers = {'X-API-Key': key}
    # Connect to API
    stream_api = requests.get('https://partners.dnaspaces.io/api/partners/v1/firehose/events',
                              stream=True, headers=headers)
    print(f"Got status code {stream_api.status_code} from partners.dnaspaces.io.")
    # Remember time we started.
    start_time = dt.now()
    if stream_api.status_code == 200:
        # Read in an update from Firehose API
        for line in stream_api.iter_lines():
            number_events += 1
            # Extract the data from the event
            data = json.loads(line)
#            pprint.pprint(data)
            result = get_data_from_json(data, client)
            # Check if any interesting events are returned.
            if len(result) > 0:
                updates.append(result)
                number_location_updates += 1
            # Check how long we have been reading the events for and stop if its longer than the test time
            process_time_secs = round((dt.now() - start_time).total_seconds(), 0)
            print(f"Progress - {round((process_time_secs/client['test_time'])*100,1)}% complete. "
                  f"Total events {number_events} interesting events {number_location_updates}")
            if process_time_secs > client['test_time']:
                print('Complete. Time taken', process_time_secs)
                break
    updates_processed, stats = post_process_results(updates)

    return updates_processed, number_location_updates, number_events, stats


def get_location_id(list_updates):
    map_id = ""
    location_id = ""
    print(f"List of updates {list_updates}")
    for update in list_updates:
        if "location_id" in update:
            print(f"Location id {update['location_id']}")
            location_id = update['location_id']
            break

    return location_id


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
        print("Error: missing api_key")
        api_key = "Unknown"
    print(f"Track client with {api_key}")
    try:
        client['mac'] = request.form['mac_address']
        if len(client['mac']) > 0 and re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", client['mac'].lower()):
            print("Got valid mac address.")
            client['search_mode'] = False
        else:
            print(f"No MAC address provided. Search mode activated.")
            client['mac'] = ""
            client['search_mode'] = True
    except KeyError:
        print(f"Error: No mac address.")
        processing_error = True
    try:
        client['x'] = float(request.form['x_coordinates'])
    except KeyError:
        print(f"Error: No x value.")
        processing_error = True
    except ValueError:
        print("Error: Unable to convert x to float.")
        processing_error = True
    try:
        client['y'] = float(request.form['y_coordinates'])
    except KeyError:
        print(f"Error: No y value.")
        processing_error = True
    except ValueError:
        print("Error: Unable to convert y to float.")
        processing_error = True
    try:
        if request.form['measurement'] == "feet":
            client['x'] = feet_to_mts(client['x'])
            client['y'] = feet_to_mts(client['y'])
            client['unit'] = "feet"
            print(f"Converted real x,y to metres {client['x']} {client['y']}")
        else:
            client['unit'] = "metre"
    except ValueError as e:
        print("Error: measurement input missing. Assuming metres.")
    try:
        client['location_id'] = request.form['location_id']
    except KeyError:
        print("Error: Unable to get location_id.")
        client['location_id'] = ""
    try:
        client['test_time'] = int(request.form['test_time'])
    except KeyError:
        print("Error: Unable to get test_time.")
        client['test_time'] = 10
    except ValueError:
        print("Error: Unable to test_time to int.")
        processing_error = True
    client['start_time'] = dt.now()
    client['number_updates'] = 0
    if not processing_error:
        client['location_updates'], client['number_updates'], client['total_events'], stats = get_updates(client, api_key)
        client['tracking'] = True
        print(f"Finished tracking {client['mac']}, got following events {client['number_updates'] }")
        if client['location_id'] == "":
            location_id = get_location_id(client['location_updates'])
            client['location_id'] = location_id
        map_img, map_width, map_height, dim_width, dim_length = get_map(client['location_id'], api_key)

    if client['unit'] == "feet":
        print("Converting real location back to feet.")
        client['x'] = round(client['x'] * 3.3, 1)
        client['y'] = round(client['y'] * 3.3, 1)

    return render_template('index.html', api_key=api_key, client=client, stats=stats,
                           img_data=map_img, img_width=map_width, img_height=map_height, dim_width=dim_width,
                           dim_length=dim_length)


@app.route('/', methods=['GET'])
def get_home_page():
    print(client_template)
    return render_template('index.html', api_key="", client=client_template, stats={},
                           img_data="", img_width=0.0, img_height=0.0, dim_width=0.0,
                           dim_length=0.0
                           )


@app.route('/download', methods=['POST'])
def down_load_file():
    csv = "seconds, error\n"
    print(f"Returned {request.form['client']}")
    client = {'seconds': 1, 'error': 2}
    for row in client['location_updates']:
        print(row)
        csv += f"{row['seconds']},{row['error']}\n"
    response = make_response(csv)
    cd = 'attachment; filename=location.csv'
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/csv'

    return response


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
        print(f"Got status code {request_location_info.status_code} from partners.dnaspaces.io.")
    except requests.exceptions.RequestException as e:
        print(f"Error: getting map information to partners.dnaspaces.io {e}")
        error = True
    if not error and request_location_info.status_code == 200:
        print("Successfully got map info.")
        error = False
        location_info = request_location_info.json()
        try:
            map_info = location_info['locationDetails']['mapDetails']
        except ValueError as e:
            print(f"Error: Tried to extract mapDetails from location but got an error {e}")
        print(f"Map info mapId {map_info['mapId']} width {map_info['imageWidth']} height {map_info['imageHeight']}")
        try:
            map_id = map_info['mapId']
            img_width = float(map_info['imageWidth']) * IMAGE_SCALE
            img_height = float(map_info['imageHeight']) * IMAGE_SCALE
            dimension_width = feet_to_mts(float(map_info['dimension']['width']))
            dimension_length = feet_to_mts(float(map_info['dimension']['length']))
            print(f"Image width {img_width} image height {img_height} floor width (mtrs) {dimension_width} floor length (mtrs) {dimension_length}")
        except ValueError:
            print("Image width and height not returned.")
            error = True
        try:
            r = requests.get(f"https://partners.dnaspaces.io/api/partners/v1/maps/{map_id}/image", headers=headers)
            print(f"Got status code {r.status_code} from partners.dnaspaces.io.")
        except requests.exceptions.RequestException as e:
            print(f"Error: getting map from partners.dnaspaces.io {e}")
            error = True
        if not error and r.status_code == 200:
            print("Successfully got map image. Converting image.")
            im = Image.open(BytesIO(r.content))
            data = io.BytesIO()
            im.save(data, "JPEG")
            encoded_img_data = base64.b64encode(data.getvalue())
            decode_img_data = encoded_img_data.decode('utf-8')

    return decode_img_data, img_width, img_height, dimension_width, dimension_length


if __name__ == '__main__':
    app.run()
