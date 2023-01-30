import json
import csv
import urllib3
from io import StringIO
import re
from pprint import pprint
from math import ceil
from random import shuffle


def shuffled(lst):
    newlst = list(lst)
    shuffle(newlst)
    return newlst

_HTTP = None


def curl_csv(url,delimiter=','):

    text = download_txt(url)

    reader = csv.DictReader(StringIO(text),delimiter=delimiter)

    return list(reader)

download_csv = curl_csv

def read_csv(filename,delimiter=','):
    with open(filename,"r") as f:
        reader = csv.DictReader(f,delimiter=delimiter)
        return list(reader)
    
    
def write_csv(filename,data):

    with open(filename, 'w', newline='') as csvfile:
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for r in data:
            writer.writerow(r)
            
def read_json(filename):
    with open(filename,"r") as jf:
        return json.load(jf)

def write_json(filename,data):
    with open(filename,"w") as jf:
        return json.dump(data,jf,indent=4)

def download_txt(url):
    data = download(url)

    text = data.decode()

    return text

def download(url,detailed=False):
    global _HTTP

    if not _HTTP:
        _HTTP = urllib3.PoolManager()

    response = _HTTP.request('GET', url)

    if not response.status in [200,201]:
        raise(FileNotFoundError(url))

    if not detailed:
        return response.data

    return (response.data,response.headers)


def bounded(f,a,b):
    if f < a:
        return a
    if f > b:
        return b
    return f
