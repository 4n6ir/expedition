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
    table = dynamodb.Table('errorindex')

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


    print(responsedata)
    

    return {
        'statusCode': 200,
        'body': json.dumps('Expedition Report')
    }