#!/usr/bin/env python2

import requests.packages.urllib3
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
    try:
        with open("config", "r") as f:
            return json.loads(f.read())
    except:
        print "Error while loading configuration"
        exit()


def save_config():
    global config

    try:
        with open("config", "w") as f:
            f.write(json.dumps(config, sort_keys=True, indent=4))
    except:
        print "Error while saving configuration"
        exit()


def get_activity_in_list(activity, json_list):
    for x in json_list:
        if x["activity_id"] == activity:
            return x
    return None


def get_data_from_diff(diff):
    global users

    msg = ""
    for i in range(0, len(diff)):
        msg += diff[i]["msg"]
        notes = []
        average = 0
        count = 0
        if diff[i]["note"]:
            for u in users:
                with open("notes/" + u, "r") as f:
                    data = json.loads(f.read())
                try:
                    index = next(a for (a, d) in enumerate(data) if d["activity_id"] == diff[i]["activity_id"])
                    try:
                        if "Non" in data[index]["validation"]:
                            validation = "Non valide"
                        elif "Valid" in data[index]["validation"]:
                            validation = "Valide"
                        else:
                            validation = ""
                    except:
                        validation = "Introuvable"
                    notes.append(dict(user=u, note=data[index]["student_mark"], validation=validation))
                    average += data[index]["student_mark"]
                    count += 1
                except:
                    notes.append(dict(user=u, note=None, validation=None))
            notes = sorted(notes, key=lambda k : k["note"], reverse=True)
            for n in notes:
                if n["note"] != None:
                    msg += "%10s => %0.1f - %s\n" % (n["user"], n["note"], n["validation"])
                else:
                    msg += "%10s => No note\n" % (n["user"])
            if count > 0:
                msg += "Average => %.2f\n" % (average / count)
    return msg


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


def fetch_users():
    global users

    for x in config["trombiIds"]:
        data = json.loads(get(config["baseURL"] + "trombi/" + str(x)))
        for a in data["students"]:
            users[a["login"]] = set()
            users[a["login"]] = x


def get_diff(prev, cur):
    ret = []
    for e in cur:
        msg = ""
        prev_elem = get_activity_in_list(e["activity_id"], prev)
        if prev_elem == None:
            msg += "Nouvel intitule detecte `%s/%s`\n" % (e["uv_long_name"], e["activity_name"])
            if e["student_mark"] != None:
                msg += "Nouvelle note detectee `%s/%s`\n" % (e["uv_long_name"], e["activity_name"])
            if e["validation"] != None:
                msg += "Validation de `%s/%s`\n" % (e["uv_long_name"], e["activity_name"])
            if len(msg) > 0:
                ret.append(dict(activity_id=e["activity_id"], msg=msg, note=e["student_mark"]))
        else:
            if e["student_mark"] != prev_elem["student_mark"]:
                msg += "Nouvelle note detectee `%s/%s`\n" % (e["uv_long_name"], e["activity_name"])
            if e["validation"] != prev_elem["validation"]:
                msg += "Validation de `%s/%s`\n" % (e["uv_long_name"], e["activity_name"])
            if len(msg) > 0:
                ret.append(dict(activity_id=e["activity_id"], msg=msg, note=e["student_mark"]))
    return ret


def write_on_slack(msg):
    global config

    if len(msg) == 0 or msg == config["lastMessage"]:
        return
    # don't spam slack if we are debugging
    if config["env"] == "debug":
        print msg
        return
    msg = msg.rstrip()
    data = json.dumps(dict(channel=config["slackChan"], text=msg))
    r = requests.post(config["slackHook"], data=dict(payload=data))
    if r.status_code != 200:
        print "Slackpost failed"
        # TODO: handle error


# simple wrapper for requests
def get(url):
    global config

    if config["env"] == "debug":
        print url
    cookie = dict(authenticator=config["cookie"])
    try:
        r = requests.get(url, cookies=cookie)
    except requests.exceptions.RequestException as e:
        try:
            print "1: " + e.message.reason.message[e.message.reason]
            print "2: " + e.message.reason.message[e.message.reason.message]
            print "3: " + e.message.reason
            print "4: " + e.meassage.reason.message
            msg = e.message.reason.message[e.message.reason.message.find("["):]
        except:
            msg = "unknown error"
        if config["timeout"] == 0:
            msg = "Intranet: " + msg
            write_on_slack(msg)
        config["timeout"] += 2 # 2 is the number of minutes between each crontab execution
        save_config()
        exit()
    if r.status_code == 401:
        # reauthenticate (apparently that should never happen, sessions are never destroyed...)
        print "Authentication needed"
    if r.status_code != 200:
        if config["timeout"] == 0:
            msg = "Intranet returned: " + str(r.status_code)
            write_on_slack(msg)
        config["timeout"] += 2 # 2 is the number of minutes between each crontab execution
        save_config()
        exit()
    if config["timeout"] > 0:
        write_on_slack("Intranet is back online after %d minutes of timeout" % config["timeout"])
        config["timeout"] = 0
        save_config()
    return r.text


if __name__ == "__main__":
    # disable SSL warning for deprecated python versions
    requests.packages.urllib3.disable_warnings()
    # switch to the good directory, useful for crontab
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    if not os.path.isdir("notes"):
        os.mkdir("notes")

    config = load_config()

    users = dict()

    # on first execution, we need to fetch all data
    if not os.path.isfile("notes/" + config["refUSER"]):
        fetch_users()
        fetch_marks()
        exit()

    # we will make our diff from here
    if config["env"] == "debug":
        with open("test", "r") as f:
            prev = json.loads(f.read())
    else:
        with open("notes/" + config["refUSER"], "r") as f:
            prev = json.loads(f.read())

    cur = json.loads(get(config["baseURL"] + "terms/" + str(config["refPROM"]) + "/students/" + config["refUSER"] + "/marks"))

    diff = get_diff(prev, cur)
    if len(diff) == 0:
        if config["env"] == "debug":
            print "No diff detected"
        exit()

    fetch_users()
    if config["env"] != "debug":
        fetch_marks()
    msg = get_data_from_diff(diff)
    write_on_slack(msg)
