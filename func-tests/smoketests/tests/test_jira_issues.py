
from datetime import datetime
from functools import reduce
import json
import logging
import pytest
import requests

CONTENT_JSON = { 'Content-Type': 'application/json' }

def test_valid_index(ctx):
    resp = requests.get(ctx.base_url+'/rest/api/2/issue/KT-1',
                        auth=ctx.admin_auth)
    assert resp.status_code == 200
    issue = resp.json()
    assert issue['fields']['summary'].startswith('Kanban cards represent work items >> Click the "KT-1" link')


def test_create_ticket(ctx):
    issue = {
      'fields': {
        'project': { 'key': "KT" },
        'summary': "New ticket" + str(datetime.now()),
        'issuetype': { 'name': "Task" }
      }
    }

    resp = requests.post(ctx.base_url+'/rest/api/2/issue',
                         auth=ctx.admin_auth,
                         headers=CONTENT_JSON,
                         data=json.dumps(issue))
    logging.error(resp.text)
    assert resp.status_code == 201


def test_jql(ctx):
    resp = requests.get(ctx.base_url+'/rest/api/2/search?jql=assignee=admin',
                        auth=ctx.admin_auth)
    assert resp.status_code == 200
    assert resp.json()['total'] == 16

