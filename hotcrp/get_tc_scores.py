#!/usr/bin/env python3

import util
from config import *
from pprint import pprint

data = util.download_csv("https://docs.google.com/spreadsheets/d/e/2PACX-1vR5yF6tYHTChP7lJrztd1kiJtC6mEdk5ml5xq_JBcA0M2xB0gvMUq_ivWrd4uo8MY98c9VYsbRSefJp/pub?gid=1941059672&single=true&output=csv")


try:
    email_aliases = dict([(ea['alias'].lower(),ea['email'].lower()) for ea in util.read_csv(HOTCRP_EMAIL_ALIASES_CSV)])
except Exception as e:
    print(f"failed to read email alias file [{HOTCRP_EMAIL_ALIASES_CSV}]")
    print(e)
    email_aliases = {}


def email(e):
    return email_aliases.get(e,e)

out = [{
    'paper':d['Paper'].strip(),
    'reviewer':email(d[f"Email {i}"].strip()),
    'score':d[f"Score {i}"].strip()
    } for d in data for i in "12345"]

util.write_csv(TC_SCORES_CSV,out)

