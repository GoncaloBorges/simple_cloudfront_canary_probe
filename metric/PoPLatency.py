#!/usr/bin/env python3

import boto3
import json
from botocore.config import Config
import pycurl
from io import BytesIO
import sys, getopt

my_config = Config(
    region_name = 'us-east-1',
    signature_version = 'v4',
    retries = {
        'max_attempts': 10,
        'mode': 'standard'
    }
)

cf = sys.argv[1]
url = []
url.append(str('https://' + cf + sys.argv[2]))
url.append(str('https://' + cf + sys.argv[3]))

def cw_put_metric_data(d,m,p,v):
    
    # Based on  https://stackify.com/custom-metrics-aws-lambda/
    cloudwatch = boto3.client('cloudwatch', config=my_config)

    # cw_response is a dictionary of the form
    #  {'ResponseMetadata': 
    #    {'RequestId': '140a3339-9d77-499e-b7ea-920c431883c1', 'HTTPStatusCode': 200, 
    #     'HTTPHeaders': {'x-amzn-requestid': '140a3339-9d77-499e-b7ea-920c431883c1', 'content-type': 'text/xml', 
    #     'content-length': '212', 'date': 'Thu, 12 May 2022 05:45:05 GMT'}, 'RetryAttempts': 0}}
    cw_response = cloudwatch.put_metric_data(
        MetricData = [
            {
                'MetricName': m,
                'Dimensions': [
                    {
                        'Name': 'Distribution',
                        'Value': d
                    },
                    {
                        'Name': 'PoP',
                        'Value': p
                    },
                ],
                'Unit': 'Milliseconds',
                'Value': v
            },
        ],
        Namespace = 'PoC / CloudFront Canary'
    )
    
    if cw_response['ResponseMetadata']['HTTPStatusCode'] > 200:
       raise HTTPError("Failed sending request", status_code=cw_response['ResponseMetadata']['HTTPStatusCode'])
    # else:
    #   print("Metric successfully published to CloudWatch")

    return




def get_response(u):
    r = []

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL,u)
    #c.setopt(c.WRITEDATA, buffer)
    #c.setopt(c.HEADER, 1)
    c.setopt(c.NOBODY, 1) # header only, no body
    c.setopt(c.HEADERFUNCTION, buffer.write)
    c.perform()

    headers = buffer.getvalue()
    # print(headers.decode('iso-8859-1'))
    response = headers.decode('iso-8859-1').split("\r\n")
    # print(response)

    # r[0] : PoP
    r.append([x for x in response if x.startswith('x-amz-cf-pop')][0].split(":")[1])

    # r[1]: pycurl NAMELOOKUP_TIME
    # print('NAMELOOKUP_TIME: %f' % c.getinfo(c.NAMELOOKUP_TIME))
    r.append(int(c.getinfo(c.NAMELOOKUP_TIME)*1000))

    # r[2]: pycurl CONNECT_TIME
    # print('CONNECT_TIME: %f' % c.getinfo(c.CONNECT_TIME))
    r.append(int(c.getinfo(c.CONNECT_TIME)*1000))

    # r[3]: pycurl PRETRANSFER_TIME
    # print('PRETRANSFER_TIME: %f' % c.getinfo(c.PRETRANSFER_TIME))
    r.append(int(c.getinfo(c.PRETRANSFER_TIME)*1000))

    # r[4]: pycurl STARTTRANSFER
    # print('STARTTRANSFER_TIME: %f' % c.getinfo(c.STARTTRANSFER_TIME))
    r.append(int(c.getinfo(c.STARTTRANSFER_TIME)*1000))

    # r[5]: pycurl TOTAL_TIM
    # print('TOTAL_TIME: %f' % c.getinfo(c.TOTAL_TIME))
    r.append(int(c.getinfo(c.TOTAL_TIME)*1000))

    servertiming = ([x for x in response if x.startswith('server-timing')][0].split(": ")[1]).split(",")
    # print(servertiming)

    # r[6]: cdn-cache-hit/cdn-cache-miss  
    r.append([x for x in servertiming if x.startswith('cdn-cache-')][0])
    if 'cdn-cache-miss' in r[-1]:
        # r[7] : cdn-upstream-dns
        r.append(int([x for x in servertiming if x.startswith('cdn-upstream-dns')][0].split("=")[1]))

        # r[8]: cdn-upstream-connect
        r.append(int([x for x in servertiming if x.startswith('cdn-upstream-connect')][0].split("=")[1]))

        # r[9]: cdn-upstream-fbl
        r.append(int([x for x in servertiming if x.startswith('cdn-upstream-fbl')][0].split("=")[1]))
    # print(r)
    c.close()

    return r



def main():

    for ur in url:
        res = []
        res = get_response(ur)
        #print(res)

        print('Corrently not pushing CW metrics. Comment the continue!')
        continue

        cw_put_metric_data(cf,'pycurl-dns',res[0],res[1])
        cw_put_metric_data(cf,'pycurl-connect',res[0],res[2])

        if res[6] == 'cdn-cache-hit':
            cw_put_metric_data(cf,'hit-pycurl-pretransfer',res[0],res[3])
            cw_put_metric_data(cf,'hit-pycurl-fbl',res[0],res[4])
            cw_put_metric_data(cf,'hit-pycurl-totaltime',res[0],res[5])
        else:
            cw_put_metric_data(cf,'miss-pycurl-pretransfer',res[0],res[3])
            cw_put_metric_data(cf,'miss-pycurl-fbl',res[0],res[4])
            cw_put_metric_data(cf,'miss-pycurl-totaltime',res[0],res[5])  
            cw_put_metric_data(cf,'miss-cdn-upstream-dns',res[0],res[7])
            cw_put_metric_data(cf,'miss-cdn-upstream-connect',res[0],res[8])
            cw_put_metric_data(cf,'miss-cdn-upstream-fbl',res[0],res[9])

    return



if __name__ == "__main__":
    main()

