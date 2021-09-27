import json
import requests
from datetime import datetime
from math import sqrt
from argparse import ArgumentParser


def calc_distance(x1, y1, x2, y2):
    distance = sqrt((x1 - x2)**2 + (y1 - y2)**2)
    return round(distance, 1)


def feet_to_metres(in_feet):
    if in_feet > 0.0:
        in_metres = in_feet * 0.3048
    else:
        in_metres = 0.0
    return round(in_metres, 1)


def stream_data(key, mac_track, x, y, start_time):
    headers = {'X-API-Key': key}
    request = requests.get('https://partners.dnaspaces.io/api/partners/v1/firehose/events', stream=True, headers=headers)
    print("Status code", request.status_code)
    num_updates = 0
    for line in request.iter_lines():
        data = json.loads(line)
        event_type = data['eventType']
        if event_type == 'DEVICE_LOCATION_UPDATE' and False:
            mac_update = data['deviceLocationUpdate']['device']['macAddress']
            if mac_update == mac_track:
                num_updates += 1
                zone_name_update = data['deviceLocationUpdate']['location']['name']
                x_update = feet_to_metres(data['deviceLocationUpdate']['xPos'])
                y_update = feet_to_metres(data['deviceLocationUpdate']['yPos'])
                time_received = datetime.now()
                distance_error = calc_distance(x, y, x_update, y_update)
                time_delta = round((time_received - start_time).total_seconds(), 1)
                print(f"Notification {num_updates} received for mac {mac_update} zone {zone_name_update} "
                      f"x {x_update} y {y_update} error {distance_error} time {time_delta}")
        elif event_type == 'IOT_TELEMETRY':
            mac_update = data['iotTelemetry']['deviceInfo']['deviceMacAddress']
            if mac_update == mac_track:
                num_updates += 1
                zone_name_update = data['iotTelemetry']['location']['name']
                x_update = feet_to_metres(data['iotTelemetry']['detectedPosition']['xPos'])
                y_update = feet_to_metres(data['iotTelemetry']['detectedPosition']['yPos'])
                time_received = datetime.now()
                distance_error = calc_distance(x, y, x_update, y_update)
                time_delta = round((time_received - start_time).total_seconds(), 1)
                print(f"Telemetry {num_updates} received for mac {mac_update} zone {zone_name_update} "
                      f"x {x_update} y {y_update} error {distance_error} time {time_delta}")

    return True


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-k", dest="key")
    parser.add_argument("-m", dest="mac")
    parser.add_argument("-x",  dest="x", type=float)
    parser.add_argument("-y",  dest="y", type=float)
    args = parser.parse_args()
    stream_data(args.key, args.mac, args.x, args.y, datetime.now())