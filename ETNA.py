#!/usr/bin/env python2

import requests
import json
import time
import sys
import os

"""
API endpoints:
/trombi/id : information about promotions
/terms/promoID/students/student/marks: grades
/students/session/student: information about UV
/promo: user promotion informations
/walls: wall you can access to
/identity: user identity
"""

def load_config():
    with open("config", "r") as f:
        return json.loads(f.read())

def save_config():
    global config

    with open("config", "w") as f:
        f.write(json.dumps(config, sort_keys=True, indent=4))

def fetch_marks():
    global users
    global config

    for u in users:
        ref = json.loads(get(config["baseURL"] + "terms/" + str(users[u]) + "/students/" + u + "/marks"))
        with open("notes/" + u, "w") as f:
            if config["env"] == "debug":
                f.write(json.dumps(ref, sort_keys=True, indent=4))
            else:
                f.write(json.dumps(ref))

def get_diff(prev, cur):
    for x in range(0, len(cur)):
        if cur[x]["activity_id"] != prev[x]["activity_id"]:
            print "activity"


def write_on_slack(msg):
    global config

    # don't spam slack if we are debugging
    if config["debug"] == "debug":
        print msg

# simple wrapper for requests
def get(url):
    global config

    if config["env"] == "debug":
        print url
    cookie = dict(authenticator=config["cookie"])
    r = requests.get(url, cookies=cookie)
    if r.status_code != 200:
        # TODO: handle error on slack with timeout etc...
        print "Error: " + str(r.status_code)
    return r.text

if __name__ == "__main__":
    # switch to the good directory, useful for crontab
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    if not os.path.isdir("notes"):
        os.mkdir("notes")

    config = load_config()

    # fetching users with ids of trombi
    users = dict()
    for x in config["trombiIds"]:
        data = json.loads(get(config["baseURL"] + "trombi/" + str(x)))
        for a in data["students"]:
            users[a["login"]] = set()
            users[a["login"]] = x

    # on first execution, we need to fetch all data
    if not os.path.isfile("notes/" + config["refUSER"]):
        fetch_marks()
        exit()

    # we will make our diff from here
    with open("notes/" + config["refUSER"], "r") as f:
        prev = json.loads(f.read())
    ref = json.loads(get(config["baseURL"] + "terms/" + str(config["refPROM"]) + "/students/" + config["refUSER"] + "/marks"))

    diff = get_diff(prev, ref)

