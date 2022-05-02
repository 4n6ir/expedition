import boto3
import json

def handler(event, context):

    data = event['event']['Data']
    extid = event['event']['ExtId']
    query = event['event']['Query']
    role = event['event']['Role']
    state = event['event']['State']
    step = event['event']['Step']
    table = event['event']['Table']
    time = event['event']['Time']
    transitions = event['event']['Transitions']
    
    limit = 'NO'

    sts_client = boto3.client('sts')

    assumed_role = sts_client.assume_role(
        RoleArn = role,
        RoleSessionName = 'expedition',
        DurationSeconds = 900,
        ExternalId = extid
    )

    cloudtrail_client = boto3.client(
        'cloudtrail',
        aws_access_key_id = assumed_role['Credentials']['AccessKeyId'],
        aws_secret_access_key = assumed_role['Credentials']['SecretAccessKey'],
        aws_session_token = assumed_role['Credentials']['SessionToken']
    )

    dynamodb = boto3.resource('dynamodb')
    database = dynamodb.Table(table)

    if state == 'START':
        result = cloudtrail_client.get_query_results(
            EventDataStore = data,
            QueryId = query
        )

        for item in result['QueryResultRows']:
            if table == 'ActionIndex': 
                parse = item['eventSource'].split('.')
                pk = parse[0]+':'+item['eventName']
                action = {}
                action['pk'] = pk
                action['sk'] = time
                action['account'] = item['recipientAccountId']
                action['region'] = item['awsRegion']
                action['count'] = item['apiCount']
                database.put_item(
                    Item = json.dumps(action)
                )

        try:
            state = result['NextToken']
            status = 'CONTINUE'
        except:
            state = ''
            status = 'SUCCEEDED'
            pass
    else:
        result = cloudtrail_client.get_query_results(
            EventDataStore = data,
            QueryId = query,
            NextToken = state
        )

        for item in result['QueryResultRows']:
            if table == 'ActionIndex': 
                parse = item['eventSource'].split('.')
                pk = parse[0]+':'+item['eventName']
                action = {}
                action['pk'] = pk
                action['sk'] = str(time)
                action['account'] = item['recipientAccountId']
                action['region'] = item['awsRegion']
                action['count'] = item['apiCount']
                database.put_item(
                    Item = json.dumps(action)
                )

        try:
            state = result['NextToken']
            status = 'CONTINUE'
        except:
            state = ''
            status = 'SUCCEEDED'
            pass

    transitions += 1
    
    if transitions == 2500:
        
        limit = 'YES'
        transitions = 0
    
    event = {}
    event['Data'] = data
    event['ExtId'] = extid
    event['Query'] = query
    event['Role'] = role
    event['State'] = state
    event['Step'] = step
    event['Table'] = table
    event['Time'] = time
    event['Transitions'] = transitions

    if limit == 'YES':

        sfn_client = boto3.client('stepfunctions')

        sfn_client.start_execution(
            stateMachineArn = step,
            input = json.dumps(event)
        )

        status = 'SUCCEEDED'
    
    return {
        'event': event,
        'status': status,
    }