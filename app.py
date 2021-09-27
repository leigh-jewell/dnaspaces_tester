from flask import Flask, request, render_template, send_file, make_response
import json
import csv
import os.path
from math import sqrt
from datetime import datetime as dt
import tempfile
from activate import process_activation
import requests
import ast

app = Flask(__name__)

# Client template
client_template = {
    "mac": "aa:bb:cc:dd:ee:ff",
    "x": 0.0,
    "y": 0.0,
    "test_time": 10,
    "start_time": None,
    "number_updates": 0,
    "location_updates": [],
    "filename": "",
    "location": "",
    "tracking": False,
    "number_events": 0,
    "total_events": 0
}


def calc_distance(x1, y1, x2, y2):
    distance = sqrt((x1 - x2)**2 + (y1 - y2)**2)
    return round(distance, 1)


def client_update(client, record_timestamp, x, y, location):
    distance_error = calc_distance(client['x'], client['y'], x, y)
    time_delta = round((record_timestamp - client['start_time']).total_seconds(), 1)
    print(f"Distance error {distance_error} time secs {time_delta}")
    location_updates = {'x': x,
                         'y': y,
                         'error': distance_error,
                         'seconds': time_delta,
                         'location': location}
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
        return render_template('index.html', api_key=api_key, client=client_template)


def get_data_from_json(json_event, client):
    number_location_updates = 0
    result = []
    try:
        if json_event['eventType'] == "DEVICE_LOCATION_UPDATE" \
                and json_event['deviceLocationUpdate']['device']['macAddress'] == client['mac']:
            number_location_updates += 1
            time_stamp_datetime = dt.fromtimestamp(json_event['recordTimestamp'] / 1000)
#            time_stamp_formatted = time_stamp_datetime.isoformat()
            x = feet_to_mts(json_event['deviceLocationUpdate']['xPos'])
            y = feet_to_mts(json_event['deviceLocationUpdate']['yPos'])
            location = json_event['deviceLocationUpdate']['location']['name']
            result = client_update(client, time_stamp_datetime, x, y, location)
        else:
            print(f"Not a device location update {json_event['eventType']}.")
    except KeyError as e:
        print(f"Unable to extract all data from json. Error: {e}")

    return result


def get_updates(client, key):
    updates = []
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
            print(f"Got data from dnaspaces {data}.")
            result = get_data_from_json(data, client)
            # Check if any interesting events are returned.
            if len(result) > 0:
                updates.append(result)
                number_location_updates += 1
            # Check how long we have been reading the events for and stop if its longer than the test time
            process_time_secs = round((dt.now() - start_time).total_seconds(), 1)
            if process_time_secs > client['test_time']:
                print('Complete. Time taken', process_time_secs)
                break
    return updates, number_location_updates, number_events


@app.route('/track', methods=['POST'])
def track_client():
    client = client_template
    # Start tracking a client on the firehose API
    api_key = request.form['api_key']
    print(f"Track client with {api_key}")
    client['mac'] = request.form['mac_address']
    client['x'] = float(request.form['x_coordinates'])
    client['y'] = float(request.form['y_coordinates'])
    client['test_time'] = int(request.form['test_time'])
    client['start_time'] = dt.now()
    client['number_updates'] = 0
    client['location_updates'], client['number_updates'], client['total_events'] = get_updates(client, api_key)
    client['tracking'] = True
    print(f"Finished tracking {client['mac']}, got following events {client['number_updates'] }")

    return render_template('index.html', api_key=api_key, client=client)


@app.route('/', methods=['GET'])
def get_home_page():
    return render_template('index.html', api_key="API KEY", client=client_template)


@app.route('/download', methods=['POST'])
def down_load_file():
    csv = "seconds, error\n"
    print(f"Returned {request.form['client']}")
#    client = ast.literal_eval(request.form['client'])
    client = {'seconds': 1, 'error': 2}
    for row in client['location_updates']:
        print(row)
        csv += f"{row['seconds']},{row['error']}\n"
    response = make_response(csv)
    cd = 'attachment; filename=location.csv'
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/csv'

    return response


if __name__ == '__main__':
    app.run()
