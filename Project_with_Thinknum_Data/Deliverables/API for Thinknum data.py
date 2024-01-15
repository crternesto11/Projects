# -*- coding: utf-8 -*-
"""
Created on Sun Oct 22 23:22:50 2023

@author: 47086
"""
import json
import requests
import time
import pandas


api_host = 'https://data.thinknum.com'
api_version = '20151130'
api_client_id = '18dd3d368615308bef1a'
api_client_secret = '06e2c1f559b79dc9cab559e877ab6f38b91590fb'  # THIS KEY SHOULD NEVER BE PUBLICALLY ACCESSIBLE
dataset_id = 'job_listings'
""" job_category=[["Consultant","consultant"],["Engineer","engineer"],["Manager","manager"],["Scientist","scientist"],
              ["Specialist","specialist"],["Analyst","analyst"],["Lead","lead","Leader","leader","Head","head"],
              ["Intern","intern"],["Advisor","advisor"],["Developer", "developer", "Architect","architect"],
              ["Support","support"],["Product","product"],["Operation","operation"],["Customer","customer","Service","service"],
              ["Sale","sale"],["Information","information"],["Technical","technical"],["Marketing","marketing"],
              ["Software","software"],["Business","business"],["Hardware","hardware"]
              ] """


# ### STEP 1: Authorization
# Setup and send request to get an authorization token

payload = {
    'version': api_version,
    'client_id': api_client_id,
    'client_secret': api_client_secret
}
request_url = api_host + '/api/authorize'
r = requests.post(request_url, data=payload)

if r.status_code != 200:
    raise Exception('Failed to authorize: ' + r.text)

token_data = json.loads(r.text)


# ### STEP 2: Get the authorization and post qurey
api_auth_token = token_data['auth_token']
api_auth_expires = token_data['auth_expires']
api_auth_headers = {
    "X-API-Version": api_version,
    "Authorization": f"token {api_auth_token}"
}
print('Authorization Token', api_auth_token)

# ###dataframe for all data
df=pandas.DataFrame({'company ticker':[],'Posted year':[],'Posted week':[],'count':[]})


# ###form loop for every company
## get query id for every query
def get_query_id(con_name):
    while True :
        response = requests.post(
            url='https://data.thinknum.com/datasets/job_listings/query/', 
            headers={
                'Authorization': f"token {api_auth_token}", 
                'X-API-Version': api_version, 
                'Accept': 'application/json'
            }, 
            data=json.dumps({
                "tickers": [
                    con_name
                ],
                "filters": [
                    {
                        "match": "all",
                        "conditions": [
                            {
                              "column": "as_of_date",
                              "type": "[]",
                              "value": [
                                "2019-01-01",
                                "2023-12-20"
                              ]
                            },
                            {
                                "column": "title",
                                "type": "(...)",
                                "value": [
                                    "Information",
                                    "information"
                                ]
                            }
                          ]
                        }
                      ],
                      "groups": [
                        {
                          "column": "as_of_date",
                          "partition": "yearweek"
                        },
                        {
                        "column": "dataset__entity__entity_ticker__ticker__market_industry"
                        }
                      ],
                      "aggregations": [
                        {
                          "column": "dataset__entity__entity_ticker__ticker__ticker",
                          "type": "count"
                        }
                      ]
                
            })
        )
        results = json.loads(response.text)

        if results['state'] == "running":
            time.sleep(3)
        else:
            break
    return results['id']


def get_company(com_name):
    # for each kind of job 
    query_id=get_query_id(com_name)
    
    ### STEP 3: CHECK THE STATUS OF PROGRESS
    response = requests.head(
        url='https://data.thinknum.com/datasets/job_listings/query/'+query_id, 
        headers={
            'Authorization': f"token {api_auth_token}" , 
            'X-API-Version': api_version, 
            'Accept': 'application/vnd.thinknum.table+json'
        }
    )
        
    ## check the result of query
    try:
        results = dict(response.headers)
    except:
        print('having trouble get the data for',com_name)
        return 0
    
    # ### STEP 4: Get the data
    response = requests.get(
        url='https://data.thinknum.com/datasets/job_listings/query/'+query_id, 
        headers={
            'Authorization': f"token {api_auth_token}", 
            'X-API-Version': api_version, 
            'Accept': 'application/vnd.thinknum.table+json'
        }
    )
    results = json.loads(response.text)

    print(com_name, " has an amount of ", len(results['rows']),"weeks")
    
    ##write all results in df
    for job in results['rows']:
        data={
            'company ticker': com_name,
            'Posted year': job[0][:4],
            'Posted week': job[0][5:],
            'count': job[2]
            }
        
        df.loc[len(df.index)] = data


# # # #### STEP 5: start getting data
c_df=pandas.read_excel('F:/revenue.xlsx', sheet_name='Sheet1')
col=pandas.Series(c_df.columns[::2]).apply(lambda x:x.split(' ')[0])

for c in col:
    get_company(c)

df.to_excel('F:/by_week_add.xlsx',index=False) 
