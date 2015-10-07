import time
from decimal import Decimal
import json
import os

from flask import Flask, request, abort, render_template, Response
import requests

app = Flask(__name__)

from boto.dynamodb2.table import Table
from boto.dynamodb2.items import Item
from boto.dynamodb2.exceptions import ItemNotFound

request_table = Table("VaccineRequest")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_REQUEST = "https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s"

RAPIDPRO_API_KEY = os.environ.get("RAPIDPRO_API_KEY")
GIVER_FLOW_UUID = "ff270149-ee71-4aa8-99c4-4fe13d748a43"
REQUESTOR_CONNECT = "d081b452-7663-40a0-bde8-a2930887f690"
GIVER_CONNECT = "d647f9ef-aab3-4dca-84bc-f9a20fe09d91"

ELASTISEARCH_SEARCH_URL = "https://search-team19awshack-moysia77rywudaydpowzulzagy.us-east-1.es.amazonaws.com/user_locations/_search?pretty=true"
ELASTISEARCH_QUERY = {
  "sort" : [
      {
          "_geo_distance" : {
              "order" : "asc",
              "unit" : "km"
          }
      }
  ],
  "query" : {
    "filtered" : {
        "query" : {
            "match_all" : {}
        },
        "filter" : {
            "geo_distance" : {
                "distance" : "50000km",
            }
        }
    }
}}

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

def closest_locations(location):
    payload = ELASTISEARCH_QUERY
    payload['sort'][0]["_geo_distance"]['location'] = location
    payload['query']['filtered']['filter']['geo_distance']['location'] = location

    res = requests.get(ELASTISEARCH_SEARCH_URL, data=json.dumps(payload))
    ret = []
    for hit in res.json()['hits']['hits'][:4]:
        ret.append(hit['_source']['phone'])
    return ret

@app.route("/receiver", methods=["POST"])
def receiver():
    phone = request.form.get("phone")
    try:
        receiver = request_table.get_item(phone=phone)
    except ItemNotFound:
        receiver = Item(request_table, data={"phone" : phone })
    values = json.loads(request.form['values'])
    receiver['vaccine_type'] = values[0]['value']
    receiver['number_of_vaccines'] = values[1]['value']
    reciever['Status'] = "Requested"
    receiver.save()
    loc = normalize_location("%s, %s" % (receiver['location']['lat'], receiver['location']['lon']))

    closest = closest_locations(receiver['location'])
    if not len(closest):
        closest = [ "+17173327758" ]
        # return Response(json.dumps({"status" : "success", "results" : "None"}))
    try:
        closest.remove(phone)
    except:
        pass

    extra = {
        "lat" : receiver['location']['lat'],
        "lon" : receiver['location']['lon'],
        "location_english" : loc['results'][0]['formatted_address'],
        "receiver_phone" : phone,
        "number_of_vaccines" : receiver['number_of_vaccines'],
        "vaccine_type" : receiver['vaccine_type']
    }

    payload = {
        "flow_uuid": GIVER_FLOW_UUID,
        "phone": closest,
        "extra": extra
    }
    res = requests.post("https://api.rapidpro.io/api/v1/runs.json", headers={
        "Authorization" : "Token %s" % RAPIDPRO_API_KEY,
        'content-type': 'application/json'
    }, data=json.dumps(payload))
    return Response(json.dumps({ "status" : "success", "response" : res.json(), "closest" : closest }), mimetype="application/json")

# @app.route("/has", methods=["POST"])
# def has():
#     phone = request.form.get("phone")
#     giver = request_table.get_item(phone=phone)
#     giver["available"] = giver.get("available", []) + [{ request.form.get("vaccine_type") : request.form.get("number_of_vaccines") }]
#     giver.save()
#     return Response(json.dumps({"status" : "success"}))

@app.route("/giver", methods=["POST"])
def giver():
    print request.form
    values = json.loads(request.form['values'])
    vac_req = request_table.get_item(phone=values[0]['receiver_phone'])
    time_to_response = float(request.form['text'])
    if time_to_response < vac_req['time_to_response']:
        vac_req['time_to_response'] = time_to_response
        vac_req['responder'] = request.form['phone']
        vac_req.save()
    return Response(json.dumps(request.form), mimetype="application/json")

@app.route("/connect")
def connect():
    for req in request_table.scan():
        if not req['received_time']:
            payload = {
                "flow_uuid": GIVER_CONNECT,
                "phone": req['responder'],
                "extra": {
                    "time_to_response" : str(req['time_to_response']),
                    "requester" : req['phone']
                }
            }
            res = requests.post("https://api.rapidpro.io/api/v1/runs.json", headers={
                "Authorization" : "Token %s" % RAPIDPRO_API_KEY,
                'content-type': 'application/json'
            }, data=json.dumps(payload))

            payload = {
                "flow_uuid": REQUESTOR_CONNECT,
                "phone": req['phone'],
                "extra": {
                    "time_to_response" : str(req['time_to_response']),
                    "giver" : req['responder']
                }
            }
            res = requests.post("https://api.rapidpro.io/api/v1/runs.json", headers={
                "Authorization" : "Token %s" % RAPIDPRO_API_KEY,
                'content-type': 'application/json'
            }, data=json.dumps(payload))

            req['Status'] = "Assigned"
            req.save()

            return Response(json.dumps({"status" : "success" }))


@app.route("/received")
def received():
    req = request_table.get_item(request.form['phone'])
    req['received_time'] = int(time.time())
    req['Status'] = "Fulfilled"
    req.save()
    return Response(json.dumps({ "status" : "success" }))

if __name__ == "__main__":
    app.debug = True
    app.run()
