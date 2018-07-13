#!/usr/bin/env python

__author__ = 'quackmaster@protonmail.com'

#TODO
#1) make this run as a daemon with something like supervisord
#2) make this work with more than two apache servers

import pingdomlib
import fabric
import sys
import urllib
from slackclient import SlackClient

# slack creds
st = "oauthtoken"
sc = SlackClient(st)

# pingdom creds
api = pingdomlib.Pingdom('user', 
    'creds', 'creds')

# checking for site using its pindgom id
apache = api.getCheck(pingdom_check)

# find which apache server currently has the virtual ip
def ssh():

    # fabric keeps printing to stdout
    # which is annoying so we're 
    # disabling it entirely
    class NullDevice():
        def write(self, s):
            pass

    fabric.stdout = NullDevice()

    # below used in find_hosts()
    global hosta
    global hostb
    global hosta_r
    global hostb_r
    global ip

    hosta = 'servera.example.com'
    hostb = 'serverb.example.com'
    
    c = '/usr/sbin/ip addr show dev ' 
    iface = 'em1:1'
    grep =  " | grep 'inet ' | cut -d ' ' -f 6  | cut -f 1 -d '/' | grep " 
    ip = '140.251.30.43'

    command = c + iface + grep + ip
   
    hosta_c = fabric.Connection(hosta)
    hostb_c = fabric.Connection(hostb)

    # make the ssh connections to both hosts
    # if host does not have virtual ip
    # then the variable below will not exist
    # thus the need to pass exception
    # if the ip does exist then a message
    # will be printed to stdout so we have
    # made that a NullDevice as shown above
    try:
        hosta_r = hosta_c.run(command, hide=True)
    except:
       pass
  
    try:
        hostb_r = hostb_c.run(command, hide=True)
    except:
       pass

ssh()

# find out if services are down
def check_outage():
    
    global downtime

    #outages() prints all recent outages - only want last one
    downtime = []
    
    if apache.status != 'up':
        for outage in apache.outages():
        
            # append outages to new list
            downtime.append("%d" % ((outage['timeto'] - outage['timefrom']) / 60))
        
check_outage()

# this function builds list of defined apache servers
# as well as the result of ssh()
# which will tell us what server's currently active
# at the time out outage
# and which new server should take its place
def find_hosts():

    global fliphost
    global newhost

    # hosts which lack ip will have None added to the right
    ah = [hosta, hostb]

    # we must insert None as we passed exceptionin ssh()
    # therefore, if hosta did not have the virtual ip
    # then the variable hosta_r won't actually have anything
    # so we populate it as None in the list
    try:
        har = (hosta_r).stdout
        ah.insert(1, har)
    except:
        ah.insert(1, None)
        pass

    try:
        hbr = (hostb_r).stdout
        ah.insert(3, hbr)
    except:
        ah.insert(3, None)
        pass

    # find if hosta or hostb are active host
    # at time of reported outage
    # shown below as 'ah'
    # we want that to be fliphost
    # meaning the host which will lose the ip
    # we also define the opposite as newhost

    if ah[0] is hosta:
        if ah[1] is None:
            if ah[2] is hostb:
                if ah[3] == hbr:
                    fliphost = hostb
                    newhost = hosta
        else:
            if ah[2] is hostb:
                if ah[1] == har:
                    if ah[3] is None:
                        fliphost = hosta
                        newhost = hostb

find_hosts()

# run from mgmt host which has ssh key access
def flip_hosts():

    dt = downtime[-1]

    # slack messages sent 
    global emsg
    global not200
    emsg = fliphost + ' ' + apache.status + ' gt 10 m - dt ' + dt + ' - ' + newhost + ' active'
    npmsg = fliphost + ' ' + apache.status + ' lt 10 m' + ' please investigate or wait longer'
    not200 = emsg + ' though does not return 200 so urgently investigate'
    
    # variables
    ifup = 'ifup em1:1 && sleep 2'
    ifdown = 'ifdown em1:1 && sleep 2'
    rapache = '/usr/sbin/apachectl graceful'
    user = 'root'

    if apache.status == 'up':
        pass

    else:
        if downtime[-1] >= 10:
            if fliphost is hosta: 
                fabric.Connection(hosta, user=user).run(ifdown)
                fabric.Connection(hostb, user=user).run(ifup)
                fabric.Connection(hostb, user=user).run(rapache)
            if fliphost is hostb: 
                fabric.Connection(hostb, user=user).run(ifdown)
                fabric.Connection(hosta, user=user).run(ifup)
                fabric.Connection(hosta, user=user).run(rapache)
        else:
            sc.api_call(
             "chat.postMessage",
              channel="#pingdom",
              text=npmsg
             )
flip_hosts()

def check_site():

    # urllib get http status code
    # then send message if site back
    site = 'https://site.you.want.to.monitor'
    code = urllib.urlopen(site).getcode()

    if code == 200:
            sc.api_call(
             "chat.postMessage",
              channel="#pingdom",
              text=emsg
             )
    else: 
        sc.api_call(
         "chat.postMessage",
          channel="#pingdom",
          text=not200
         )

check_site()

