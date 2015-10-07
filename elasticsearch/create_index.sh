curl -XPUT https://search-team19awshack-moysia77rywudaydpowzulzagy.us-east-1.es.amazonaws.com//user_locations -d '
{
    "mappings": {
        "user": {
            "properties": {
                "phone": {"type": "string"},
                "location": {"type": "geo_point"}
            }
        }
    }
}
'
