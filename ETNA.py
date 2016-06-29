#!/usr/bin/env python2

import urllib2
import json
import time
import sys
import os

"""
We will start with a crappy version since I am pretty noob at python OOP
Then I may rewrite some code to make a much cleaner version
"""

# wrap this object later on
config = {
    "baseUrl":"https://prepintra.etna-alternance.net/",
    # correspond to the IDs we need to fetch to get user list
    # we have 2 specialization so we have 2 IDs per promotion
    # the URL used is this one:
    # https://prepintra.etna-alternance.net/#/trombi?id=92
    "trombiIds":[92, 93, 109, 110],
    }

# simple wrapper to urllip for get requests
def get(url):
    global config

    for x in config["trombiIds"]:
        print x

if __name__ == "__main__":
    # getting list of users to fetch notes from
    # we need login + ids at least
    get("test")
    # need to make destination directory for notes if it does'nt exist also
