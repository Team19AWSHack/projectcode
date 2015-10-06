import time
from decimal import Decimal
import json
import os

import boto
from flask import Flask, request, abort, render_template, Response
import requests

app = Flask(__name__)

from boto.dynamodb2.table import Table

request_table = Table("VaccineRequest")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_REQUEST = "https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s"

RAPIDPRO_API_KEY = os.environ.get("RAPIDPRO_API_KEY")
GIVER_FLOW_UUID = "ff270149-ee71-4aa8-99c4-4fe13d748a43"

def normalize_location(loc_string):
    print GOOGLE_REQUEST % (loc_string, GOOGLE_API_KEY)
    res = requests.get(GOOGLE_REQUEST % (loc_string, GOOGLE_API_KEY))
    return res.json()

@app.route("/location", methods=["POST"])
def location():
    values = request.form.get("values")

    loc = normalize_location(request.form.get("text"))

    if not loc['status'] == "OK":
        return Response(json.dumps({ "status" : "fail", "location" : False }), mimetype="application/json")

    data = {
        "location" : {
            "lat" : str(loc['results'][0]['geometry']['location']['lat']),
            "lon" : str(loc['results'][0]['geometry']['location']['lng']),
        },
        "english" : loc['results'][0]['formatted_address']
    }

    d_data = data.copy()
    d_data['phone'] = request.form.get("phone")
    d_data['time'] = int(time.time())
    request_table.put_item(data=d_data, overwrite=True)

    data['status'] = "success"
    return Response(json.dumps(data), mimetype="application/json")

def get_rapidpro_contact_info(phone):
    res = requests.get("https://api.rapidpro.io/api/v1/contacts.json?phone=%2B12482198946", headers={
        "Authorization" : "Token %s" % RAPIDPRO_API_KEY
    })
    return res.json()['results'][0]

@app.route("/receiver", methods=["POST"])
def receiver():
    phone = request.form.get("phone")
    receiver = request_table.get_item(phone=phone)
    receiver['type'] = "receiver"
    reciever['vaccine_type'] = request.form.get("vaccine_type")
    reciever['number_of_vaccines'] = request.form.get("number_of_vaccines")
    receiver.save()
    loc = normalize_location("%s, %s" % (receiver['location']['lat'], receiver['location']['lon']))
    #TODO: Query for closest locations
    payload = {
        "flow_uuid": GIVER_FLOW_UUID,
        "phone": [
            "+7173327758"
        ],
        "extra": {
            "location": receiver['location'],
            "location_english" : loc['results'][0]['formatted_address'],
            "receiver_phone" : phone,
            "units" : reciever['number_of_vaccines'],
            "vaccine_type" : reciever['vaccine_type']
        }
    }
    res = requests.post("https://api.rapidpro.io/api/v1/runs.json", headers={
        "Authorization" : "Token %s" % RAPIDPRO_API_KEY
    }, data=payload)
    return Response(json.dumps({"status" : "success"}))

@app.route("/giver", methods=["POST"])
def giver():
    phone = request.form.get("phone")
    giver = request_table.get_item(phone=phone)
    giver['type'] = "giver"
    return Response(json.dumps(request.form), mimetype="application/json")

if __name__ == "__main__":
    app.debug = True
    app.run()
