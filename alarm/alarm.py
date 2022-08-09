import boto3
import json
import os

def handler(event, context):

    print(event['Records'][0]['dynamodb']['NewImage'])
    print(event['Records'][0]['dynamodb']['NewImage']['action']['S'])
    
    #client = boto3.client('sns')

    #response = client.publish(
    #    TopicArn = os.environ['SNS_TOPIC'],
    #    Subject = 'Expedition Alarm',
    #    Message = str(gzipdata)
    #)

    return {
        'statusCode': 200,
        'body': json.dumps('Expedition Alarm')
    }