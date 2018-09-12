#!/usr/bin/env python

# TODO
# 1) make this work with more than two apache servers
# 2) use urllib to check site before fipping sites - what if pingdom erroneous?
# 3) reboot server if ssh exception occurs using idrac

__author__ = 'quackmaster@protonmail.com'

import pingdomlib
import fabric
from paramiko import ssh_exception
import urllib
import sys
import time
from invoke import UnexpectedExit
from slackclient import SlackClient

# slack creds
st1 = "st1"
st2 = "st2"
st = st1 + st2
sc = SlackClient(st)

# pingdom creds
api = pingdomlib.Pingdom('user',
                         'key', 'secret')
# servers runnning apache
hosta = 'a.example.com'
hostb = 'b.example.com'

# virtual ip
ip = 'ip'

# ssh user for fabric.Connection
user = 'user'

# site we're monitoring via pingdom
site = 'https://site.example.com'

# defining site using its pindgom id
apache = api.getCheck(id)

# how often in seconds to run functions in this script
run_every = 120

# mins to wait when in outage before taking action
fm = 10

_outer_loop_ = True

while _outer_loop_:
    time.sleep(run_every)

    def ssh():

        # below used in find_hosts()
        global hosta_r
        global hostb_r
        global ip

        c = '/usr/sbin/ip addr show dev '
        iface = 'em1:1'
        grep = " | grep 'inet ' | cut -d ' ' -f 6  | cut -f 1 -d '/' | grep "
        command = c + iface + grep + ip
        hosta_c = fabric.Connection(hosta, user=user, connect_timeout=5)
        hostb_c = fabric.Connection(hostb, user=user, connect_timeout=5)

        # must define None as ssh() will exit with Exception when host lacks IP
        _inner_a_ = True

        while _inner_a_:
            try:
                hosta_r = hosta_c.run(command, hide=True)
                sys.stdout.write(hosta + ' has ' + ip + '\n')
                sys.stdout.flush()
                hosta_c.close()
            except UnexpectedExit:
                sys.stdout.write(hosta + ' does not have ' + ip + '\n')
                sys.stdout.flush()
                hosta_r = None
                hosta_c.close()
                pass
                break
            except ssh_exception.NoValidConnectionsError:
                sys.stdout.write(hosta + ' connection failed - exiting... \n')
                sys.stdout.flush()
                raise
                sys.exit()
            except KeyError:
                sys.stdout.write(hosta + ' server-side account error \n')
                sys.stdout.write.flush()
                hosta_c.close()
                continue
            else:
                break

        _inner_b_ = True

        while _inner_b_:
            try:
                hostb_r = hostb_c.run(command, hide=True)
                sys.stdout.write(hostb + ' has ' + ip + '\n')
                sys.stdout.flush()
                hostb_c.close()
            except UnexpectedExit:
                sys.stdout.write(hostb + ' does not have ' + ip + '\n')
                sys.stdout.flush()
                hostb_r = None
                hostb_c.close()
                pass
                break
            except ssh_exception.NoValidConnectionsError:
                sys.stdout.write(hostb + ' connection failed - exiting... \n')
                sys.stdout.flush()
                raise
                sys.exit()
            except KeyError:
                sys.stdout.write(hostb + ' server-side account error \n')
                sys.stdout.flush()
                hostb_c.close()
                continue
            else:
                break

    ssh()

    # find out if services are down
    def check_outage():

        global d
        global ldt
        global ldt_int

        # outages() prints all recent outages - only want last one
        # so putting all in new list which will be used in flip_hosts()
        d = []

        if apache.status != 'up':

            # define ldt and others here
            for outage in apache.outages():

                # append outages to new list
                d.append("%d" % ((outage['timeto'] - outage['timefrom']) / 60))
        else:
            d.append('up')

        # needed for flip_hosts()
        ldt = d[-1]

    check_outage()

    # this function builds list of defined apache servers
    # as well as the result of ssh()
    # which will tell us what server's currently active
    # at the time out outage
    # and which new server should take its place
    def find_hosts():

        # used in flip_hosts() as well
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

    # function that flips to other apache server
    # run from mgmt host which has ssh key access
    # for user defined at top of script
    # you will also need to configure sudo access
    def flip_hosts():

        global n200

        # using fh, nh, astatus for messages only
        # ran into line length issue with message lines
        fh = fliphost
        nh = newhost
        astatus = apache.status

        # need below far for 'e' message only
        # given if statement in check_outage()
        dt = ldt

        # need string not int in below error error message 'e'
        fm_str = str(fm)

        # slack messages being sent
        # e = error mesage sent when downtime exists
        # oe = message sent when other error found
        # np = message sent when downtime exists though lt threshold (fm_str)
        # not200 = message sent when site not returning HTTP 200
        e = fh + ' ' + astatus + ' ' + dt + ' >= ' + fm_str + ' ' + nh + ' up'
        oe = 'neither apache host defined as ' + nh + ' serious problem'
        np = fh + ' ' + astatus + ' <= ' + fm_str + ' please check services'
        n200 = e + ' though does not return 200 so urgently investigate'

        # apache / network commands to be executed
        ifup = 'sudo ifup em1:1 && sleep 2'
        ifdown = 'sudo ifdown em1:1 && sleep 2'
        rapache = 'sudo /usr/sbin/apachectl graceful'

        if astatus == 'up':
            pass
            sys.stdout.write(site + ' up via pingdom check' + '\n')
            sys.stdout.flush()
        else:
            ldt_int = int(ldt)
            if ldt_int >= fm:
                if fliphost is hosta:
                    fabric.Connection(hosta, user=user).run(ifdown)
                    fabric.Connection(hostb, user=user).run(ifup)
                    fabric.Connection(hostb, user=user).run(rapache)
                elif fliphost is hostb:
                    fabric.Connection(hostb, user=user).run(ifdown)
                    fabric.Connection(hosta, user=user).run(ifup)
                    fabric.Connection(hosta, user=user).run(rapache)
                else:
                    sc.api_call("chat.postMessage", channel="#pingdom",
                                text=oe)
                    sys.exit()
            else:
                sc.api_call("chat.postMessage", channel="#pingdom", text=np)

    flip_hosts()

    # urllib get http status code
    # then send message if site back
    def check_site():

        code = urllib.urlopen(site).getcode()
        if code != 200:
                sc.api_call("chat.postMessage", channel="#pingdom", text=n200)
        else:
            sys.stdout.write(site + ' up via urllib check' + '\n')
            sys.stdout.flush()
            pass
    check_site()
