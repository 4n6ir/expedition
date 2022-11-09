import boto3
import json

def actions(item, sort, table, time):
    
    parse = item[0]['eventSource'].split('.')
    name = parse[0]+':'+item[1]['eventName']
    action = {}
    action['pk'] = 'ACTION'
    action['sk'] = 'AWS#'+sort+'#'+name+'#'+item[4]['sourceIPAddress']
    action['action'] = name
    action['account'] = item[2]['recipientAccountId']
    action['region'] = item[3]['awsRegion']
    action['address'] = item[4]['sourceIPAddress']
    action['count'] = item[5]['apiCount']
    action['time'] = time
    
    dynamodb = boto3.resource('dynamodb')
    database = dynamodb.Table(table)
    
    database.put_item(
        Item = action
    )

def handler(event, context):

    data = event['event']['Data']
    query = event['event']['Query']
    sort = event['event']['Sort']
    state = event['event']['State']
    step = event['event']['Step']
    table = event['event']['Table']
    time = event['event']['Time']
    transitions = event['event']['Transitions']
    
    limit = 'NO'

    cloudtrail_client = boto3.client('cloudtrail')

    if state == 'START':
        result = cloudtrail_client.get_query_results(
            EventDataStore = data,
            QueryId = query
        )
        for item in result['QueryResultRows']:
            if table == 'ActionIndex' or table == 'ErrorIndex':
                actions(item, sort, table, time)
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
            if table == 'ActionIndex' or table == 'ErrorIndex':
                actions(item, sort, table, time)
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
    event['Query'] = query
    event['Sort'] = sort
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