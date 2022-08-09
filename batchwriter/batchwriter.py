import boto3
import json

def actions(item, sort, table, time):
    
    parse = item[0]['eventSource'].split('.')
    name = parse[0]+':'+item[1]['eventName']
    action = {}
    action['pk'] = 'ACTION'
    action['sk'] = 'AWS#'+sort+'#'+name
    action['action'] = name
    action['account'] = item[2]['recipientAccountId']
    action['region'] = item[3]['awsRegion']
    action['count'] = item[4]['apiCount']
    action['time'] = time
    
    dynamodb = boto3.resource('dynamodb')
    database = dynamodb.Table(table)
    
    database.put_item(
        Item = action
    )

def handler(event, context):

    data = event['event']['Data']
    extid = event['event']['ExtId']
    query = event['event']['Query']
    role = event['event']['Role']
    sort = event['event']['Sort']
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
    event['ExtId'] = extid
    event['Query'] = query
    event['Role'] = role
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