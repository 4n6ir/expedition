import boto3
import datetime
import json
import os
import time

def authorization(mgmtacct):
    session = boto3.session.Session()
    client = session.client(
        service_name = 'secretsmanager'
    )
    get_secret = client.get_secret_value(
        SecretId = 'arn:aws:secretsmanager:'+os.environ['REGION']+':'+mgmtacct+':secret:expedition'
    )
    return get_secret['SecretString']

def handler(event, context):

    ### TEMP ###
    
    event = {}
    event['query'] = "SELECT eventSource, eventName, COUNT(*) AS apiCount FROM <DATA> WHERE eventTime >= '<START>' AND eventTime < '<END>' GROUP BY eventSource, eventName"
    
    ### ORGANIZATION ###
    
    organizations_client = boto3.client('organizations')
    organization = organizations_client.describe_organization()

    ### SECRET ###

    authorized = authorization(organization['Organization']['MasterAccountId'])
    authorize = json.loads(authorized)

    ### ASSUME ###

    sts_client = boto3.client('sts')

    assumed_role = sts_client.assume_role(
        RoleArn = authorize['role'],
        RoleSessionName = 'expedition',
        DurationSeconds = 1800,
        ExternalId = authorize['extid']
    )

    cloudtrail_client = boto3.client(
        'cloudtrail',
        aws_access_key_id = assumed_role['Credentials']['AccessKeyId'],
        aws_secret_access_key = assumed_role['Credentials']['SecretAccessKey'],
        aws_session_token = assumed_role['Credentials']['SessionToken'],
    )

    ### DATASTORE ###
    
    expedition = 'EMPTY'

    datastores = cloudtrail_client.list_event_data_stores()
    
    for datastore in datastores['EventDataStores']:
        tags = cloudtrail_client.list_tags(
            ResourceIdList = [
                datastore['EventDataStoreArn']
            ]
        )
        for tag in tags['ResourceTagList']:
            for lists in tag['TagsList']:
                if lists['Key'] == 'expedition':
                    parse = tag['ResourceId'].split('/')
                    expedition = parse[1]

    if expedition != 'EMPTY':

        ### DATETIME ###
        
        now = datetime.datetime.now()
        final = now - datetime.timedelta(hours=1)
        start = final.strftime('%Y-%m-%d %H:00:00')
        end = now.strftime("%Y-%m-%d %H:00:00")

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
            print('COMPLETED!!')

    return {
        'statusCode': 200,
        'body': json.dumps('Start Expedition Query')
    }