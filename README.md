Apachemon
===============

In this repository you will find a script that will manage uptime for a given site behind which two Apache servers will operate.

For this to work the servers should be using a Virtual IP with network script already in place.

You will get notifications sent via Slack when the script detects an outage and then brings up the other web server.

Requirements
------------

You must be using Python 2.7

**ifup** should work properly.

**Apache** 2.4 should be present on both servers.

You must have an account with [Pingdom](https://pypi.org/project/PingdomLib/)

[Fabric](https://github.com/fabric/fabric)

[Slackclient](https://pypi.org/project/slackclient/)

[Supervisor](http://supervisord.org/)

Ansible Role
------------

This repository also contains a skeleton Ansible role which deploys a service account on a local ***mgmt host*** as well as remote Apache servers.

In this instance mgmt host would be a server that runs the apachemon service managed by Supervisor.

The role's designed to be ran against Apache servers whereas some tasks run on localhost.  So the server from which you run Ansible should be considered the mgmt host.

TODO
------------
Add step which detects Apache state rather than simply running graceful restart.  Would be also useful to add step which attempts another restart if HTTP 200 isn't found by urllib.

Make this work with more than two Apache servers.

Reboot server out of band using iDRAC if exception occurs.

