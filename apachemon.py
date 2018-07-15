#!/usr/bin/env python

# TODO
# 1) solve 'else' with hostb in ssh() as no exception occurs yet clause ran
# 2) make this run as a daemon with something like supervisord
# 3) make this work with more than two apache servers

__author__ = 'quackmaster@protonmail.com'

import pingdomlib
import fabric
import urllib
import sys
from invoke import UnexpectedExit
from slackclient import SlackClient

# slack creds - broken up due to length
st1 = "token1"
st2 = "token2"
st = st1 + st2
sc = SlackClient(st)

# pingdom creds
api = pingdomlib.Pingdom('login',
                         'cred', 'cred')

# ssh user for fabric.Connection
user = 'root'

# site we're monitoring via pingdom
site = 'https://web.example.com'

# defining site using its pindgom id
apache = api.getCheck(id)

# ssh() finds which apache server currently has the virtual ip


def ssh():

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
    grep = " | grep 'inet ' | cut -d ' ' -f 6  | cut -f 1 -d '/' | grep "
    ip = 'ip'

    command = c + iface + grep + ip
    hosta_c = fabric.Connection(hosta, user=user)
    hostb_c = fabric.Connection(hostb, user=user)

    # slack message sent if another exception occurs
    # which will result in sys.exit()
    # hosta_emsg = "error with ssh() to " + hosta
    # hostb_emsg = "error with ssh() to " + hostb

    # we must define None as ssh() will exit with Exception when host lacks IP
    try:
        hosta_r = hosta_c.run(command, hide=True)
    except UnexpectedExit:
        hosta_r = None
        pass
#   # else:
#   #     sc.api_call("chat.postMessage", channel="#pingdom", text=hosta_emsg)
#   #     raise
#   #     sys.exit()

    try:
        hostb_r = hostb_c.run(command, hide=True)
    except UnexpectedExit:
        hostb_r = None
        pass
    # else:
    #    # print(hostb_r)
    #    sc.api_call("chat.postMessage", channel="#pingdom", text=hostb_emsg)
    #    sys.exit()


ssh()

# find out if services are down


def check_outage():

    global dt

    # outages() prints all recent outages - only want last one
    # so putting all in new list which will be used in flip_hosts()
    dt = []

    if apache.status != 'up':
        for outage in apache.outages():

            # append outages to new list
            dt.append("%d" % ((outage['timeto'] - outage['timefrom']) / 60))


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

    # host[a:b]_r will always exist given exception handling in ssh()
    # though will make sure here as well
    # stdout will not exist if var happens to be None
    # so we are allowing it to pass if that's the case

    try:
        hosta_r
        har = (hosta_r).stdout
        if type(har) is unicode:
            ah.insert(1, str(har).strip('[]').strip('\n'))
        else:
            print('hosta_r error')
            sys.exit()
    except (NameError, AttributeError):
        if hosta_r is None:
            har = hosta_r
            ah.insert(1, har)
            pass
        else:
            print('hosta_r error')
            sys.exit()

    try:
        hostb_r
        hbr = (hostb_r).stdout
        if type(hbr) is unicode:
            ah.insert(3, str(hbr).strip('[]').strip('\n'))
        else:
            print('hostb_r error')
            sys.exit()
    except (NameError, AttributeError):
        if hostb_r is None:
            hbr = hostb_r
            ah.insert(3, hbr)
            pass
        else:
            print('hostb_r error')
            sys.exit()

    # find if hosta or hostb are active host
    # at time of reported outage
    # shown below as 'ah'
    # we want that to be fliphost
    # meaning the host which will lose the ip
    # we also define the opposite as newhost

    # print(isinstance(ah[3], str))

    if ah[0] is hosta and ah[2] is hostb:
        if ah[1] is None and ah[3] == ip:
            fliphost = hostb
            newhost = hosta

        else:
            if ah[1] == ip and ah[3] is None:
                fliphost = hosta
                newhost = hostb
            else:
                print("unknown error")
                sys.exit()


find_hosts()

# run from mgmt host which has ssh key access


def flip_hosts():

    # we want last downtime in dt[]
    ldt = dt[-1]

    # slack messages sent
    global e
    global not200
    e = fliphost + ' ' + apache.status + ' ' + ldt + ' >10 ' + newhost + ' up'
    oe = 'neither apache host defined as ' + fliphost + ' serious problem'
    np = fliphost + ' ' + apache.status + ' <10 ' + ' please investigate'
    not200 = e + ' though does not return 200 so urgently investigate'

    # apache vars
    ifup = 'ifup em1:1 && sleep 2'
    ifdown = 'ifdown em1:1 && sleep 2'
    rapache = '/usr/sbin/apachectl graceful'

    if apache.status == 'up':
        pass

    else:
        if ldt >= 10:
            if fliphost is hosta:
                fabric.Connection(hosta, user=user).run(ifdown)
                fabric.Connection(hostb, user=user).run(ifup)
                fabric.Connection(hostb, user=user).run(rapache)
            elif fliphost is hostb:
                fabric.Connection(hostb, user=user).run(ifdown)
                fabric.Connection(hosta, user=user).run(ifup)
                fabric.Connection(hosta, user=user).run(rapache)
            else:
                sc.api_call("chat.postMessage", channel="#pingdom", text=oe)
                sys.exit()
        else:
            sc.api_call("chat.postMessage", channel="#pingdom", text=np)


flip_hosts()


def check_site():

    # urllib get http status code
    # then send message if site back
    code = urllib.urlopen(site).getcode()

    if code == 200:
            sc.api_call("chat.postMessage", channel="#pingdom", text=e)
    else:
        sc.api_call("chat.postMessage", channel="#pingdom", text=not200)


check_site()
