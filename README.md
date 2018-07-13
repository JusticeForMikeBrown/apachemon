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

TODO
------------
Make this work with more than two Apache servers.
