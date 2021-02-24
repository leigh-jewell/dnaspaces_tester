# Cisco DNA Spraces Accuracy and Latency Tester
Cisco DNA Spaces accuracy and latency tester

A small python script to test out  [Cisco DNA Spaces](https://dnaspaces.io). The script creates a web server
using Flask to receive DNA Spaces location update notifications. It can then calculate the error distance and latency
as a device is moved to a specific location on the map.

## Getting Started
* Have a look at the Cisco DNA Spaces API over at [DevNet](https://developer.cisco.com/docs/dna-spaces/#!dna-spaces-location-cloud-api).
To get familar with the APIs available.
* Clone this repository into a directory to get the helper scripts:
```
git clone https://github.com/leigh-jewell/dnaspaces_tester.git
```
### Prerequisites

* Install [Python 3.9+](https://www.python.org/downloads/) with the appropriate distribution for your OS.
* Install [Pipenv](https://pipenv-fork.readthedocs.io/en/latest/) using pip which should have been installed with Python3:
```
pip install pipenv
```
Or if you are using [Homebrew](https://brew.sh/) simply run:
```
brew install pipenv
```

* For your script to authenticate with [Cisco DNA Spaces](https://dnaspaces.io) you need to create a token in your account.
Instructions are shown on [DevNet](https://developer.cisco.com/docs/dna-spaces/#!getting-started). Otherwise, simply follow these steps: 
1. Browse to [Detect and Locate](https://dnaspaces.io/locate/) 
2. Click on the menu bar and select "Notifications"
3. Click on "Web hooks"
4. Add a "Location Update"
5. Send the notification to the server /notification URI

### Installing

Create the virtual environment using Pipflie.lock. This will ensure the dependencies are installed

```
pipenv install --ignore-pipfile
```

## Running the scrips

The script will use the environment variable 'TOKEN' to authenticate to DNA Spaces. You will need to set this according
to your OS.

OSX:
```
export TOKEN="abcdefghijkl"
```
Windows10:
```
set TOKEN "abcdefghijkl"
```

Use the Pipenv shell to ensure you access the virtual environment created:
```
pipenv shell
```

 You can now run the scripts:

```
python app.py
```
This will run a local Flask web server on http://127.0.0.1:5000 which is helpful for testing.

