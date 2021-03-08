from flask import Flask, request, render_template, send_file, make_response
import json
import csv
import os.path
from math import sqrt
from datetime import datetime as dt
import tempfile

app = Flask(__name__)
client = {
    "tracking": False,
    "mac": "",
    "x": 0.0,
    "y": 0.0,
    "start_time": "",
    "number_updates": 0,
    "location_updates": [],
    "filename": "",
    "zone": ""
}


def calc_distance(x1, y1, x2, y2):
    distance = sqrt((x1 - x2)**2 + (y1 - y2)**2)
    return round(distance, 1)


def client_update(mac, x, y, timestamp, notification_time, zone):
    global client
    if client['tracking'] and client['mac'] == mac:
        print(f"Client location update for tracked client {mac} {x}, {y} {notification_time} {zone}")
        distance_error = calc_distance(client['x'], client['y'], x, y)
        time_delta = round((timestamp - client['start_time']).total_seconds(), 1)
        print(f"Distance error {distance_error} time secs {time_delta}")
        client['location_updates'].append({'x': x,
                                           'y': y,
                                           'error': distance_error,
                                           'seconds': time_delta,
                                           'zone': zone})
        print(client['location_updates'])
        client["number_updates"] += 1


@app.route('/notification', methods=['POST'])
def post():
    global client
    data = {}
    try:
        data = json.loads(request.data)
        device_id = request.json['notifications'][0]['deviceId']
        compute_type = request.json['notifications'][0]['locComputeType']
        time_stamp = request.json['notifications'][0]['timestamp']/1000
        time_stamp_datetime = dt.fromtimestamp(time_stamp)
        time_stamp_format = time_stamp_datetime .isoformat()
        location_map_hierarchy = request.json['notifications'][0]['locationMapHierarchy']
        zone = location_map_hierarchy.split("->")[-1]
        x_feet = round(request.json['notifications'][0]['locationCoordinate']['x'], 1)
        y_feet = round(request.json['notifications'][0]['locationCoordinate']['y'], 1)
        if x_feet > 0.0:
            x = round(x_feet * 0.3048, 1)
        else:
            x = 0.0
        if y_feet > 0.0:
            y = round(y_feet * 0.3048, 1)
        else:
            y = 0.0
        if client['tracking']:
            client_update(device_id, x, y, time_stamp_datetime, time_stamp_format, zone)
    except (ValueError, KeyError, TypeError) as e:
        print("Error with POST", e)
    return json.dumps(request.json)


@app.route('/', methods=['GET', 'POST'])
def start_timer():
    global client
    if request.method == 'POST':
        print(f"POST request Tracking Status {client['tracking']} Tracked {client['location_updates']}")
        if request.form['submit'] == "Start" and not client['tracking']:
            print("POST: Start")
            client['tracking'] = True
            client['mac'] = request.form['mac_address']
            client['x'] = float(request.form['x_coordinates'])
            client['y'] = float(request.form['y_coordinates'])
            client['start_time'] = dt.now()
            client['location_updates'] = []
            client['number_updates'] = 0
            if client['tracking']:
                print(f"Tracking {client['mac']} x {client['x']} y {client['y']} Time {client['start_time']}")
        elif request.form['submit'] == "Stop":
            print("POST: Stop")
            client['tracking'] = False
        else:
            print("")
        return render_template('index.html', tracking_status=client['tracking'], client=client)
    else:
        if len(client['location_updates']) > 0:
            have_data = True
        else:
            have_data = False
        print(f"{request.method} request Tracking Status {client['tracking']} Tracked {client['location_updates']}")
        return render_template('index.html', tracking_status=client['tracking'], client=client)


@app.route('/download', methods=['GET', 'POST'])
def down_load_file():
    csv = "seconds, error\n"
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
