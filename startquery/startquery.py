import boto3
import datetime
import json
import os
import time

def handler(event, context):

    ### DATASTORE ###
    
    expedition = 'EMPTY'

    cloudtrail_client = boto3.client('cloudtrail')

    datastores = cloudtrail_client.list_event_data_stores()
    
    for datastore in datastores['EventDataStores']:
        tags = cloudtrail_client.list_tags(
            ResourceIdList = [
                datastore['EventDataStoreArn']
            ]
        )
        for tag in tags['ResourceTagList']:
            for lists in tag['TagsList']:
                if lists['Key'] == 'Expedition':
                    parse = tag['ResourceId'].split('/')
                    expedition = parse[1]

    if expedition != 'EMPTY':

        ### DATETIME ###
        
        now = datetime.datetime.now()
        final = now - datetime.timedelta(hours=1)
        start = final.strftime('%Y-%m-%d %H:00:00')
        end = now.strftime("%Y-%m-%d %H:00:00")
        sort = final.strftime("%Y#%m#%d#%H")

        ### BUILDING ###
        
        query = str(event['query'])
        query = query.replace('<DATA>', expedition)
        query = query.replace('<START>', start)
        query = query.replace('<END>', end)

        ### QUERY ###
        
        queryid = cloudtrail_client.start_query(
            QueryStatement = query
        )

        ### MONITOR ###

        status = 'STARTED'
        
        while status == 'STARTED' or status == 'QUEUED' or status == 'RUNNING':
            time.sleep(30)
            result = cloudtrail_client.get_query_results(
                EventDataStore = expedition,
                QueryId = queryid['QueryId'],
                MaxQueryResults = 1
            )
            status = result['QueryStatus']
        
        ### LOGGING ###
        
        result['Query'] = query
        print(result)

        if result['QueryStatus'] == 'FINISHED':

            ssm_client = boto3.client('ssm')
            
            response = ssm_client.get_parameter(
                Name = os.environ['STATE']
            )
            step = response['Parameter']['Value']
    
            batch = {}
            batch['Data'] = expedition
            batch['Query'] = queryid['QueryId']
            batch['Sort'] = sort
            batch['State'] = 'START'
            batch['Step'] = step
            batch['Table'] = event['table']
            batch['Time'] = start
            batch['Transitions'] = 0

            sfn_client = boto3.client('stepfunctions')

            sfn_client.start_execution(
                stateMachineArn = step,
                input = json.dumps(batch)
            )

    return {
        'statusCode': 200,
        'body': json.dumps('Start Expedition Query')
    }