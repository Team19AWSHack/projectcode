import json

import boto
from flask import Flask, request, abort, render_template, Response


app = Flask(__name__)

from boto.dynamodb2.table import Table

request_table = Table("VaccineRequest")

def normalize_location(loc_string):
    # string apiKey = "AIzaSyBhfg8yxDEA34U8BrStO1Vbpini8TzQBz0";
    #
    # XmlDocument xResultsDoc = null;
    #
    # xResultsDoc = Util.askGoogle(cleanAddress, apiKey);
    #
    # if (xResultsDoc.SelectSingleNode("//GeocodeResponse/status").InnerText == "OK")
    # {
    #    lat = xResultsDoc.SelectSingleNode("//geometry/location/lat").InnerText;
    #    lng = xResultsDoc.SelectSingleNode("//geometry/location/lng").InnerText;
    # }

    return loc_string

@app.route("/webhook", methods=["POST"])
def webhook():
    values = request.form.get("values")
    data = {
        "values" : values
    }

    return Response(json.dumps(data), mimetype="application/json")
