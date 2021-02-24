from flask import Flask, request, render_template, send_file
import json
import csv
import os.path
from math import sqrt
from datetime import datetime as dt


app = Flask(__name__)
client = {
    "tracking": False,
    "mac": "",
    "x": 0.0,
    "y": 0.0,
    "start_time": "",
    "number_updates": 0,
    "location_updates": [],
    "filename": ""
}


def calc_distance(x1, y1, x2, y2):
    distance = sqrt((x1 - x2)**2 + (y1 - y2)**2)
    return round(distance, 2)


def client_update(mac, x, y, timestamp, notification_time):
    global client
    if client['tracking'] and client['mac'] == mac:
        print(f"Client location update for tracked client {mac} {x}, {y} {notification_time}")
        distance_error = calc_distance(client['x'], client['y'], x, y)
        time_delta = round((timestamp - client['start_time']).total_seconds(), 2)
        print(f"Distance error {distance_error} time secs {time_delta}")
        client['location_updates'].append({'x': x,
                                           'y': y,
                                           'error': distance_error,
                                           'seconds': time_delta})
        with open(client['filename'], "a") as f:
            append_csv_file = csv.writer(f, delimiter=',')
            append_csv_file.writerow([time_delta, distance_error])
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
        x = request.json['notifications'][0]['locationCoordinate']['x']
        y = request.json['notifications'][0]['locationCoordinate']['y']
        if client['tracking']:
            client_update(device_id, x, y, time_stamp_datetime, time_stamp_format)
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
            client['filename'] = "tracking_" + client['mac'] + ".csv"
            try:
                os.remove(client['filename'])
            except IOError:
                print(f"File doesnt exist {client['filename']}")
            with open(client['filename'], "a") as f:
                append_csv_file = csv.writer(f, delimiter=',')
                append_csv_file.writerow(['time_delta', 'distance_error'])
            client['number_updates'] = 0
            if client['tracking']:
                print(f"Tracking {client['mac']} x {client['x']} y {client['y']} Time {client['start_time']}")
        elif request.form['submit'] == "Stop":
            print("POST: Stop")
            client['tracking'] = False
        return render_template('index.html', tracking_status=client['tracking'], client=client)
    else:
        print(f"GET request Tracking Status {client['tracking']} Tracked {client['location_updates']}")
        return render_template('index.html', tracking_status=client['tracking'], client=client)


@app.route('/download', methods=['GET', 'POST'])
def down_load_file():
    path = "./" + client['filename']
    return send_file(path, as_attachment=True)


@app.route('/file/<filename>', methods=['GET', 'POST'])
def get_file(filename):
    path = "./" + filename
    return send_file(path, as_attachment=True)


if __name__ == '__main__':
    app.run()
