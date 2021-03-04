import requests
import json
import random
from datetime import datetime
import time

move_payload = """
{
    "notifications": [
        {
            "maxDetectedRssi": {
                "rssi": -62,
                "apMacAddress": "2c:57:41:58:ee:e0",
                "lastHeardInSeconds": 0,
                "antennaIndex": 0,
                "band": "IEEE_802_11_B",
                "slot": 0
            },
            "floorUuid": "5298f7b4159a4213a64db1de3c85d178",
            "notificationType": "locationupdate",
            "source": "COMPUTE",
            "deviceId": "00:00:2f:2f:7c:c2",
            "ssid": "cisco",
            "manufacturer": "Microsoft Corporation",
            "floorId": "720582563218976008",
            "rawLocation": {
                "unit": "FEET",
                "rawY": 112.76798,
                "rawX": 126.9718
            },
            "band": "IEEE_802_11_B",
            "staticDevice": "false",
            "timestamp": 1608156624468,
            "eventId": 1608156624492,
            "locComputeType": "RSSI",
            "ipAddress": [
                "10.3.99.211"
            ],
            "userName": "test@cisco.com",
            "lastSeen": "2020-12-16 22:10:24.468+0000",
            "apMacAddress": "2c:57:41:58:e0:00",
            "subscriptionName": "Test",
            "locationMapHierarchy": "D Building-> Level 2",
            "associated": true,
            "tenantId": "13214",
            "locationCoordinate": {
                "unit": "FEET",
                "x": 128.7,
                "y": 111.3,
                "z": 0
            },
            "confidenceFactor": 88,
            "subscriptionId": "89ffe913-f609-4985-97b0-f62a8d70c682",
            "entity": "WIRELESS_CLIENTS"
        }
    ]
}
"""


def send_move_notifications(mac, start_x, start_y, finish_x, finish_y, iterations):
    host = "127.0.0.1:5000"
    good = 0
    url_post = "http://{}/".format(host)
    payload = {'submit': 'Start', 'mac_address': mac, 'x_coordinates': finish_x, 'y_coordinates': finish_y}
    try:
        print(f"Sending POST for mac {mac} x {finish_x} y {finish_y}")
        r = requests.post(url_post, data=payload)
    except requests.exceptions.RequestException as e:
        print(f"Error: Got exception {e} error from requests.")
        raise SystemExit(e)
    if r.status_code == 200:
        print(f"Tracking of mac {mac} successfully set. Sending {iterations} test data.")
        payload_json = json.loads(move_payload)
        url = "http://{}/notification".format(host)
        step_x = round((finish_x - start_x) / iterations, 2)
        step_y = round((finish_y - start_y) / iterations, 2)
        print(f"step_x {step_x} step_y {step_y}")
        for i in range(iterations):
            payload_json['notifications'][0]['deviceId'] = mac
            now = datetime.now()
            payload_json['notifications'][0]['timestamp'] = round(now.timestamp() * 1000)
            payload_json['notifications'][0]['locationCoordinate']['x'] = start_x + round(random.random(), 1)
            payload_json['notifications'][0]['locationCoordinate']['y'] = start_y + round(random.random(), 1)
            try:
                r = requests.post(url, json=payload_json)
                if r.status_code == 200:
                    good += 1
            except:
                print("Failed to send request for client", mac)
            start_x += step_x
            start_y += step_y
            time.sleep(random.random())
        print('Finished move notifications - ', good)
        payload = {'submit': 'Stop'}
        try:
            print(f"Sending POST STOP tracking")
            r = requests.post(url_post, data=payload)
        except requests.exceptions.RequestException as e:
            print(f"Error: Got exception {e} error from requests.")
            raise SystemExit(e)
    else:
        print(f"Got status code {r.status_code} from POST to set tracking.")

    return


send_move_notifications('00:00:2f:2f:7c:c2', 5.0, 6.0, 10.5, 12.0, 10)