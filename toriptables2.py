#! /usr/bin/env python
# Written by rupe
"""
Tor Iptables script is an anonymizer
that sets up iptables and tor to route all services
and traffic including DNS through the tor network.
"""

from __future__ import print_function
from commands import getoutput
from subprocess import call
from os.path import isfile
from os import devnull
from argparse import ArgumentParser

fnull = open(devnull, 'w')


class TorIptables(object):
    def __init__(self):
        self.tor_config_file = '/etc/tor/torrc'
        self.torrc = '''
VirtualAddrNetwork 10.0.0.0/10
AutomapHostsOnResolve 1
TransPort 9040
DNSPort 53
'''
        self.non_tor_net = ["192.168.0.0/16", "172.16.0.0/12"]
        self.non_tor = ["127.0.0.0/9", "127.128.0.0/10", "127.0.0.0/8"]
        self.tor_uid = getoutput("id -ur debian-tor")  # Tor user uid
        self.trans_port = "9040"  # Tor port
        self.load_iptables_rules.__init__(self)

    def flush_iptables_rules(self):
        call(["iptables", "-F"])
        call(["iptables", "-t", "nat", "-F"])

    def load_iptables_rules(self):
        self.flush_iptables_rules()
        self.non_tor.extend(self.non_tor_net)

        call(["iptables", "-t", "nat", "-A", "OUTPUT", "-m", "owner",
              "--uid-owner", "%s" % self.tor_uid, "-j", "RETURN"])
        call(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "udp", "--dport",
              "53", "-j", "REDIRECT", "--to-ports", "53"])

        for self.net in self.non_tor:
            call(["iptables", "-t", "nat", "-A", "OUTPUT", "-d",
                  "%s" % self.net, "-j", "RETURN"])

        call(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "tcp", "--syn",
              "-j", "REDIRECT", "--to-ports", "%s" % self.trans_port])

        call(["iptables", "-A", "OUTPUT", "-m", "state", "--state",
              "ESTABLISHED,RELATED", "-j", "ACCEPT"])

        for self.net in self.non_tor:
            call(["iptables", "-A", "OUTPUT", "-d", "%s" % self.net, "-j",
                  "ACCEPT"])

        call(["iptables", "-A", "OUTPUT", "-m", "owner", "--uid-owner",
              "%s" % self.tor_uid, "-j", "ACCEPT"])
        call(["iptables", "-A", "OUTPUT", "-j", "REJECT"])

        # Restart Tor
        call(["service", "tor", "restart"], stderr=fnull)


if __name__ == '__main__':
    parser = ArgumentParser(
    description='Tor Iptables script for loading and unloading iptables rules')
    parser.add_argument('-l', '--load',
                        action="store_true",
                        help='This option will load tor iptables rules')
    parser.add_argument('-f', '--flush',
                        action='store_true',
                        help='This option flushes the iptables rules to default')
    args = parser.parse_args()

    try:
        load_tables = TorIptables()
        if isfile(load_tables.tor_config_file):
            if not 'VirtualAddrNetwork' in open(
                load_tables.tor_config_file).read():
                with open(load_tables.tor_config_file, 'a+') as torrconf:
                    torrconf.write(load_tables.torrc)

        if args.load:
            load_tables.load_iptables_rules()
        elif args.flush:
            load_tables.flush_iptables_rules()
        else:
            parser.print_help()
    except Exception as err:
        print(err)
