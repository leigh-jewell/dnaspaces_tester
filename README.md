# Cisco DNA Spraces Accuracy and Latency Tester
Cisco DNA Spaces accuracy and latency tester

A small python script to test out  [Cisco DNA Spaces](https://dnaspaces.io). The script creates a web server
using Flask and connects to DNA Spaces Firehose API to receive location updates. It can then calculate the error distance and latency
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

### Partners Appliction Creation

For your script to receive Firehose API events you need to create an application in [Cisco DNA Spaces Partners](https://partners.dnaspaces.io).  
The steps for creating an application are: 
1. Browse to [Cisco DNA Spaces Partners](https://partners.dnaspaces.io) 
2. Create new app
3. For app type select on prem
4. App Center > Complete APP Name, APP Tag line, APP Description, Primary Industry, App Icon
5. App Tile > Complete APP Tile and App Tile Tag line
6. Events > Check the event Device Location Update  
7. Create
8. Select App Activation Sandbox > App Center > Select your new App, click Activate button
9. Sign up and continue
10. Accept Permissions
11. Choose locations that you wish to test
12. Generate App Activation token and copy token
13. Paste this token into the local http://127.0.0.1/ once you start python app.py

### Installing

Create the virtual environment using Pipflie.lock. This will ensure the dependencies are installed

```
pipenv install --ignore-pipfile
```

## Running the scrips

The script will use the environment variable 'TOKEN' to authenticate to DNA Spaces. You will need to set this according
to your OS.

Use the Pipenv shell to ensure you access the virtual environment created:
```
pipenv shell
```

You can now run the scripts:

```
python app.py
```
This will run a local Flask web server on http://127.0.0.1:5000 which is helpful for testing.

## Vagrant
Some utility files are provided if you want to use vagrant to test with or if you want to provision this to a real server.
