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

def normalize_location(loc_string):
    print GOOGLE_REQUEST % (loc_string, GOOGLE_API_KEY)
    res = requests.get(GOOGLE_REQUEST % (loc_string, GOOGLE_API_KEY))
    return res.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    values = request.form.get("values")

    loc = normalize_location(request.form.get("text"))

    if not loc['status'] == "OK":
        return Response(json.dumps({ "status" : "fail", "location" : False }), mimetype="application/json")

    data = {
        "values" : values,
        "lat" : str(loc['results'][0]['geometry']['location']['lat']),
        "lon" : str(loc['results'][0]['geometry']['location']['lng']),
        "english" : loc['results'][0]['formatted_address']
    }

    d_data = data.copy()
    d_data['phone'] = request.form.get("phone")
    d_data['time'] = int(time.time())
    request_table.put_item(data=d_data)

    data['status'] = "success"
    return Response(json.dumps(data), mimetype="application/json")

if __name__ == "__main__":
    app.debug = True
    app.run()
