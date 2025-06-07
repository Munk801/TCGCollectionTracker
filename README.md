
## What is it?

This script is a personal script made to simplify the lives of my spouse and myself when selling
TCG cards via TCGPlayer.  It simply updates various information on a google sheet to manage our 
inventory better and understand current market value.

## Getting Started
### Setting up Google Drive API Access

Make sure you create a new project within your google dev console

https://console.cloud.google.com

Create a new project

Once you create a project, make sure you create a new service account.

This service account also needs to be allowed access from whatever spreadsheet or thing you are looking to read/write to. 

From your google service account, you will need to create a new key which will be used for API access. Go to APIs and Services-> Enabled APIs & services -> Find the Google Sheets API -> Credentials and create a new key for a service account.  Save that json config

### Activate the venv environment

On windows, run the following to set up your venv
```
git clone <repo>
cd <repo>

python -m venv venv

```
./venv/Scripts/activate.bat
pip install -r requirements.txt

```

To run the actual script
```
python tcgplayer_tracker.py
```
