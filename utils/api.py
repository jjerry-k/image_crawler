import requests

def request_crwling(bytes_data, test=False):
    files = {
            'file': bytes_data,
            }
    payload = {
            'test': True if test else False
        }
    requests.post("http://backend:5000/request/crawl", verify=False, files=files, data=payload)