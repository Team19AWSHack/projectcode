//NPM modules
var express = require('express');
var bodyParser = require('body-parser');
var aws = require('aws-sdk');

var aws_key = process.env.AWS_KEY;
var aws_secret = process.env.AWS_SECRET;
aws.config.update({accessKeyId: aws_key, secretAccessKey: aws_secret});
aws.config.update({region: 'us-east-1'});
var dynamodb = new aws.DynamoDB({apiVersion: '2012-08-10'});
var app = express();
app.use('/', express.static(__dirname + '/public'));
var tableName = 'VaccineRequest';

app.get('/stats/requests/overdue', function(request, response) {
	//Get all items with timestamp > 24 hours from current and status == open
	
	var expiredDate = Date.now() - (24*3600);
	
	var params = {
		TableName: tableName,
		ScanFilter: {
			TimestampEpoch: {
				ComparisonOperator: 'LT',
				AttributeValueList: [{'N':expiredDate.toString()}]
			},
			Status: {
				ComparisonOperator: 'NE',
				AttributeValueList: [{'S':'Fulfilled'}]
			}
		}
	};
	
	dynamodb.scan(params, function (err, data) {
	if (err) { console.log(err); return; }
	
	response.send(data);
	});
	
});

//Get a count of requests by status for last 24 hours
app.get('/stats/requests/summary', function(request, response) {
		var requestedCount, assignedCount, fulfilledCount = 0;
		
		//Get Open Count
		var requestedParams = {
			TableName: tableName,
			ScanFilter: {
				Status: {
					ComparisonOperator: 'EQ',
					AttributeValueList: [{'S':'Requested'}]
				}
			},
			Select: 'COUNT'
		}
		
		var assignedParams = {
			TableName: tableName,
			ScanFilter: {
				Status: {
					ComparisonOperator: 'EQ',
					AttributeValueList: [{'S':'Assigned'}]
				}
			},
			Select: 'COUNT'
		}
		
		var fulfilledParams = {
			TableName: tableName,
			ScanFilter: {
				Status: {
					ComparisonOperator: 'EQ',
					AttributeValueList: [{'S':'Fulfilled'}]
				}
			},
			Select: 'COUNT'	
		}
		
		dynamodb.scan(requestedParams, function (err, data) {
		
			if (err) { console.log(err); return; }
				requestedCount = data.Count;
				
				dynamodb.scan(assignedParams, function (err, data) {
					if (err) { console.log(err); return; }
					assignedCount = data.Count;
					
					dynamodb.scan(fulfilledParams, function (err, data) {
						if (err) { console.log(err); return; }
						
						fulfilledCount = data.Count;
						
						var result = { 'RequestedCount' : requestedCount,
							'AssignedCount' : assignedCount,
							'FulfilledCount' : fulfilledCount,
							'TotalCount' : (requestedCount + assignedCount + fulfilledCount)
						};
						
						response.send(result);
						
						
					});
				});
		});
});

//Returns all open requests
app.get('/stats/requests/open', function(request, response) {
	//Get all open requests
	var params = {
			TableName: tableName,
			ScanFilter: {
				Status: {
					ComparisonOperator: 'EQ',
					AttributeValueList: [{'S':'Requested'}]
				}
			}
		}
		
	dynamodb.scan(params, function (err, data) {
		if (err) { console.log(err); return; }
		
		response.send(data);
	});
});

//Returns all closed requests
app.get('/stats/requests/closed', function(request, response) {
	var params = {
			TableName: tableName,
			ScanFilter: {
				Status: {
					ComparisonOperator: 'EQ',
					AttributeValueList: [{'S':'Fulfilled'}]
				}
			}
		}
		
	dynamodb.scan(params, function (err, data) {
		if (err) { console.log(err); return; }
		
		response.send(data);
	});
});

//Returns all requests regardless of status (Used for Geo and list)
app.get('/stats/requests/all', function(request, response) {
	var params = {
			TableName: tableName
		}
		
	dynamodb.scan(params, function (err, data) {
		if (err) { console.log(err); return; }
		
		response.send(data);
	});
});

app.get('/stats/requests/last10', function(request, response) {
	var params = {
			TableName: tableName,
			Limit: 10
		}
		
	dynamodb.scan(params, function (err, data) {
		if (err) { console.log(err); return; }
		
		response.send(data);
	});
});

app.get('/stats/requests/lasthour', function(request, response) {
	var params = {
		TableName: tableName,
		ScanFilter: {
			time: {
				ComparisonOperator: 'LT',
				AttributeValueList: [{'N': (Date.now() - 3600).toString()}]
			}
		},
		Select: 'COUNT'
	}
	
	dynamodb.scan(params, function (err, data) {
		if (err) { console.log(err); return; }
		
		response.send(data);
	});
});



app.listen(8000, function(error) {  
  if(error) {
    throw error;
  }
  console.log('Listening on 127.0.0.1:8000');
});