# WARNING:

Feel free to use this script, but it's not very polished. I've published it for a few co-workers and myself.

# Requirements:

1. PyAc - https://github.com/kostajh/pyac
1. Requests - http://docs.python-requests.org/en/latest/
1. A working ActiveCollab site and working API key
1. A working Toggl account with a working API token

# Intro:

AciveCollab is a time management system. ActiveCollab has projects, and projects have tasks within them.
You can enter time at the project-level or for a specific task within a project.

Toggl is a web-based time tracking application.

This script will automatically send your Toggl time entries into ActiveCollab.

When you create a project in ActiveCollab it'll get a unique URL.
For example, if I create a project called "Website Beta" it will create a URL
of *https://myactivecollaburl.com/projects/website-beta*. The project slug in this example is "website-beta".
If that slug was already in use when I created this new project, it would have used something else.

When you are storing time entries in Toggl, if you want the time entry to work with this script,
you must set the toggl time entry's project name to a valid ActiveCollab project slug. If you use a project name
that doesn't match an ActiveCollab project slug, the script will prompt you to ignore the entry; this is useful if
you use Toggl to track tasks that are not in ActiveCollab (like personal tasks).

Additionally, if you wish to store your time for a specific task within an ActiveCollab project,
you may start the task description (in Toggl) with a hashtag and the task number within that project.
See the examples below for more information.

When you sync entries from Toggl to ActiveCollab (by running the script) it will automatically store a history
of which time entries have been synced. This information is stored in `~/.actoggltimeimport_records.txt`.

# Initial Setup:

1. Install pyac
    1. `mkdir ~/3rdparty` (or wherever you want to install pyac)
    1. `cd ~/3rdparty`
    1. `git clone https://github.com/kostajh/pyac.git`
    1. `cd ~/3rdparty/pyac`
    1. `sudo python setup.py install`
1. Create `~/.acrc` file:<pre>url=https://myactivecollaburl.com/api.php<br/>key=4-q3qb33XITWyYpdmFCwh9931Bwzk3giTw7yY2kvK7<br/>user_id=4</pre>
    1. Use your own values, of course
1. Create `~/.togglrc` file:<pre>[toggl]<br/>token=e0926359d8c73bbe7ab136d042530d9a</pre>
    1. Use your own token
1. Run `actoggltimeimport.py` as often as you need to. It will only send each time entry to ActiveCollab once.

# Examples:
<pre>
https://myactivecollaburl.com/projects/clean-the-house/tasks/103

                                       \             /       \ /
                                        \           /         |
                                           project       task number

------------------------------------------------------------------------------------

Example 1: Log time at the PROJECT level:

Toggl time entry project:     clean-the-house
Toggl time entry description: My description goes here.

------------------------------------------------------------------------------------

Example 2: Log time at the TASK level (use whichever format you prefer):

Toggl time entry project:     clean-the-house
Toggl time entry description: #58 - This description doesn't have to match task name

Toggl time entry project:     clean-the-house
Toggl time entry description: #58: Here's another format that will work

Toggl time entry project:     clean-the-house
Toggl time entry description: #58 This will work too.

------------------------------------------------------------------------------------
</pre>
