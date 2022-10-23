import boto3
import datetime
import json
import os
from boto3.dynamodb.conditions import Key

def handler(event, context):
    
    ### DATETIME ###
        
    now = datetime.datetime.now()
    final = now - datetime.timedelta(hours=1)
    sort = final.strftime("%Y#%m#%d#%H")

    ### DYNAMODB QUERY ###

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(event['table'])

    response = table.query(
        KeyConditionExpression = Key('pk').eq('ACTION') & Key('sk').begins_with('AWS#'+sort+'#')
    )
    
    responsedata = response['Items']
    
    while 'LastEvaluatedKey' in response:
        
        response = table.query(
            KeyConditionExpression=Key('pk').eq('ACTION') & Key('sk').begins_with('AWS#'+sort+'#'),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        
        responsedata.extend(response['Items'])

    f = open('/tmp/expedition.html', 'w')
    
    f.write('<HTML>')
    f.write('<BODY>')
    f.write('<TABLE>')
    f.write('<TR><TH>Time</TH><TH>Action</TH><TH>Count</TH><TH>Account</TH><TH>Region</TH><TH>Address</TH></TR>')
    
    for item in responsedata:

        f.write('<TR><TD>'+str(item['time'])+'</TD><TD>'+str(item['action'])+'</TD><TD>'+str(item['count'])+'</TD><TD>'+str(item['account'])+'</TD><TD>'+str(item['region'])+'</TD><TD>'+str(item['address'])+'</TD></TR>')

    f.write('</TABLE>')
    f.write('</BODY>')
    f.write('</HTML>')
    
    f.close()

    s3_client = boto3.client('s3')

    s3_client.upload_file('/tmp/expedition.html', os.environ['BUCKET'], event['folder']+'/expedition.html')

    return {
        'statusCode': 200,
        'body': json.dumps('Expedition Report')
    }