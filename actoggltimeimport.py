#!/usr/bin/env python

import pyac
from datetime import datetime, timedelta
import json
import logging
import sys
import argparse
import re
import requests
import os.path
import ConfigParser

parser = argparse.ArgumentParser(description="Sends Toggl time entries to Active Collab as long as the project slug (the name of the project as rendered in its URL) matches a project in Active Collab. If the task begins with #N (where N is the task number within that project), the time will be attached to that specific task.")
parser.add_argument("-d", "--days", dest="days", default=15, type=int, choices=xrange(1,364),
                    help="how many days of time entries to pull; remember, already-synced entries will be skipped automatically. Default value is 15.", metavar="N")
args = parser.parse_args()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

# Console logging
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
LOG.addHandler(ch)

config = ConfigParser.RawConfigParser()
try:
    config.read(os.path.expanduser('~/.togglrc'))
    toggl_api_token = config.get('toggl', 'token')
except:
    LOG.error('Please create a ~/.togglrc file with your token. View README for setup instructions.')


def human_duration(ms):
    seconds = int(ms) / 1000
    minutes, seconds = divmod(seconds, 60)

    # Round minutes up; Active Collab doesn't support seconds
    if (seconds > 30):
        minutes += 1
    hours, minutes = divmod(minutes, 60)
    return (format(hours, "02") + ":" + format(minutes, "02"))


def milliseconds_to_hours(ms):
    return "%.2f" % (int(ms) / (60*60*1000.00))


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".

    See http://stackoverflow.com/a/3041990
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

def toggl_query(url, params={}, method="GET", report=False, payload=None):
    if report:
       api_url = 'https://www.toggl.com/reports/api/v2' + url
    else:
        api_url = 'https://www.toggl.com/api/v8' + url

    auth = (toggl_api_token, 'api_token')
    headers = {'content-type': 'application/json'}
    params['user_agent'] = 'actoggltimeimport'

    if method == "POST":
        response = requests.post(api_url, auth=auth, headers=headers, params=params, data=payload)
    elif method == "PUT":
        response = requests.put(api_url, auth=auth, headers=headers, params=params)
    elif method == "GET":
        response = requests.get(api_url, auth=auth, headers=headers, params=params)
    else:
        raise UserWarning('GET, POST and PUT are the only supported request methods.')

    # If the response errored, raise for that.
    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    return response.json()


def get_workspaces():
    return toggl_query('/workspaces')


def get_workspace_projects():
    return toggl_query('/workspaces/' + workspace_id + '/projects', {}, 'GET')


def get_timeslips_query(**kwargs):
    params = {
        'grouping': 'users',
        'subgrouping': 'projects',
        'order_field': 'date',
        }

    for key in kwargs:
        if not params.get(key):
            params[key] = kwargs.get(key)

    response = toggl_query('/details', params, 'GET', True)

    return response


def get_timeslips(**kwargs):
    timeslips = []
    response = get_timeslips_query(**kwargs)
    data = response['data']
    per_page = response['per_page']
    total_count = response['total_count']

    if data:
        for row in data:
            timeslips.append(row)

    if total_count > per_page:
        # There are more records than can be returned in one go-round.
        total_pages = total_count / per_page
        if total_count % per_page:
            total_pages += 1

        for current_page in range(total_pages):
            page = current_page + 1
            if page > 1:
                response = get_timeslips_query(page=page, **kwargs)
                data = response['data']
                if data:
                    for row in data:
                        timeslips.append(row)

    return timeslips

workspaces = get_workspaces()
workspace_id = str(workspaces[0]['id'])

# Hopefully the user is running this script more frequently than every 14 days!
# The limit is 365 days (or maybe 364)
daysago = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

records_file_path = os.path.join(os.path.expanduser('~'),'.actoggltimeimport_records.txt')

try:
    records_file = open(records_file_path, "r")
    toggl_entries = json.load(records_file)
    records_file.close()
except:
    toggl_entries = {}
    LOG.info("No data found")
    if query_yes_no("Warning: no sync history found! Choose Yes to start fresh (may cause dupes if you have previous imported).", "no") is False:
        LOG.info("Aborting.")
        exit()

timeslips = get_timeslips(workspace_id=workspace_id, since=daysago)

# We only want to send "new" entries to Active Collab
new_items = {}
for item in timeslips:
    if str(item['id']) not in toggl_entries:
        end_date = item['end'].split('T')[0]
        new_items[item['id']] = [item['project'], item['description'], end_date, human_duration(item['dur'])]

LOG.info("Found %d new time entries" % len(new_items))
if len(new_items) > 0:
    if query_yes_no("If this sounds right, choose Yes to continue", "yes") is False:
        LOG.info("Aborting.")
        exit()
else:
    exit()

class PyACLocal(pyac.activeCollab):
    def add_time_to_project(self, project_id, value, user_id, record_date,
                            job_type_id, billable_status, summary):
        """ Adds a new time record to the time log in a defined project. """
        params = {
            'time_record[value]': value,
            'time_record[user_id]': user_id,
            'time_record[record_date]': record_date,
            'time_record[job_type_id]': job_type_id,
            'time_record[billable_status]': billable_status,
            'time_record[summary]': summary,
            'submitted': 'submitted',
            }
        return self.call_api('projects/%s/tracking/time/add' %
                             project_id, params)

ac = PyACLocal()

# To avoid multiple API calls, we'll just get everything we might need right away
projects = ac.get_projects()
project_list = []
for project in projects:
    project_list.append(project["slug"])

for entry, props in new_items.iteritems():
    #props values are 0:project, 1:description, 2:end date, 3:duration
    if props[0] in project_list:
        task_num_text = re.match('^#(\d+)(.*)', props[1])
        if task_num_text:
            task_num = int(task_num_text.group(1))
            task_text = task_num_text.group(2).lstrip(': -')
            try:
                result = ac.add_time_to_task(props[0], task_num, props[3], ac.user_id, props[2], 1, 1, task_text)
                LOG.info("Added {3}h to #{0} in {1} - {2}".format(task_num, props[0], task_text, props[3]))
                toggl_entries[entry] = props
            except:
                LOG.error("Could not add {3}h to #{0} in {1} - {2}".format(task_num, props[0], task_text, props[3]))
                if query_yes_no("Try again later?", "yes") is False:
                    # Add this to the records file so it doesn't get processed again
                    toggl_entries[entry] = props
        else:
            try:
                result = ac.add_time_to_project(props[0], props[3], ac.user_id, props[2], 1, 1, props[1])
                LOG.info("Added {2}h to {0} - {1}".format(props[0], props[1], props[3]))
                toggl_entries[entry] = props
            except:
                LOG.error("Could not add {2}h to {0} - {1}".format(props[0], props[1], props[3]))
                if query_yes_no("Try again later?", "yes") is False:
                    # Add this to the records file so it doesn't get processed again
                    toggl_entries[entry] = props
    else:
        LOG.error("Could not find project {0} for {1}".format(props[0], props[1]))
        if query_yes_no("Try again later?", "yes") is False:
            # Add this to the records file so it doesn't get processed again
            toggl_entries[entry] = props

# Write the successful entries to the records file
records_file = open(records_file_path, "w")
json.dump(toggl_entries, records_file)
records_file.close()
