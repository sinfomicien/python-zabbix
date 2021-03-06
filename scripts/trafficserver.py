#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' Copyright (c) 2013 Jean Baptiste Favre.
    Sample script for Zabbix integration with Apache TrafficServer.
'''
import sys,os
import optparse
import socket
import urllib2
import simplejson
import protobix

class TrafficServer():

    __version__ = '0.0.8'
    ZBX_CONN_ERR = 'ERR - unable to send data to Zabbix [%s]'

    ITEM_BL = [
        'proxy.process.version.server.build_date',
        'proxy.process.version.server.build_machine',
        'proxy.process.version.server.build_number',
        'proxy.process.version.server.build_person',
        'proxy.process.version.server.build_time',
        'proxy.process.version.server.long',
        'proxy.process.version.server.short'
    ]

    ATS_BOOLEAN_MAPPING = { "False": 0,
                            "True": 1 }
    ATS_STATE_MAPPING = { "green": 0,
                          "yellow": 1,
                          "red": 2 }

    ATS_CONN_ERR = "ERR - unable to get data from ATS [%s]"

    def _parse_args(self):
        ''' Parse the script arguments
        '''
        parser = optparse.OptionParser(description="Get TrafficServer statistics, "
                                        "format them and send the result to Zabbix")

        parser.add_option("-d", "--dry", action="store_true",
                                   help="Performs TrafficServer API calls but do not "
                                        "send anything to the Zabbix server. Can be "
                                        "used for both Update & Discovery mode")
        parser.add_option("-D", "--debug", action="store_true",
                                   help="Enable debug mode. This will prevent bulk "
                                        "send operations and force sending items one "
                                        "after the other, displaying result for each "
                                        "one")
        parser.add_option("-v", "--verbose", action="store_true",
                                   help="When used with debug option, will force value "
                                        "display for each items managed. Beware that it "
                                        "can be pretty much verbose, specialy for LLD")

        general_options = optparse.OptionGroup(parser, "Apache TrafficServer cluster "
                                                       "configuration options")
        general_options.add_option("-H", "--host", metavar="HOST", default="localhost",
                                   help="Apache TrafficServer hostname")
        general_options.add_option("-p", "--port", default=80,
                                   help="Apache TrafficServer port"
                                        "Default is 80")

        parser.add_option_group(general_options)

        zabbix_options = optparse.OptionGroup(parser, "Zabbix configuration")
        zabbix_options.add_option("--zabbix-server", metavar="HOST", default="localhost",
                                   help="The hostname of Zabbix server or "
                                        "proxy, default is localhost.")
        zabbix_options.add_option("--zabbix-port", metavar="PORT", default=10051,
                                   help="The port on which the Zabbix server or "
                                        "proxy is running, default is 10051.")
        parser.add_option_group(zabbix_options)

        (options, args) = parser.parse_args()

        return (options, args)

    def _get_metrics(self):
        try:
            '''request = urllib2.Request( ("http://%s:%d/_stats" % (options.host, int(options.port))), timeout=0.5 )'''
            request = urllib2.Request( ("http://%s:%d/_stats" % (self.options.host, int(self.options.port))))
            opener  = urllib2.build_opener()
            rawjson = opener.open(request, None, 1)
        except urllib2.URLError as e:
            if self.options.debug:
                print self.ATS_CONN_ERR % e.reason
            raise Exception(self.ATS_CONN_ERR % e.reason)
        json = None
        if (rawjson):
            json = simplejson.load(rawjson)
        return json

    def _init_container(self):
        zbx_container = protobix.DataContainer(
            data_type = 'items',
            zbx_host  = self.options.zabbix_server,
            zbx_port  = int(self.options.zabbix_port),
            debug     = self.options.debug,
            dryrun    = self.options.dry
        )
        zbx_container.data_type = 'items'
        return zbx_container

    def run(self):
        (self.options, args) = self._parse_args()
        data = {}
        rawjson = ""
        zbxret = 0

        if self.options.host == 'localhost':
            hostname = socket.getfqdn()
        else:
            hostname = self.options.host

        # Step 1: init container
        try:
            zbx_container = self._init_container()
        except:
            return 1

        # Step 2: get data
        try:
            json = self._get_metrics()
        except:
            return 2

        # Step 3: format & load data into container
        try:
            for item in json['global']:
                if item not in self.ITEM_BL:
                    zbx_container.add_item(
                        hostname,
                        ("ats.%s" % item),
                        json['global'][item]
                    )
            zbx_container.add_item(hostname, "ats.zbx_version", self.__version__)
        except:
            return 3

        # Step 4: send container data to Zabbix server
        try:
            zbx_container.send(zbx_container)
        except protobix.SenderException as zbx_e:
            if self.options.debug:
                print self.ZBX_CONN_ERR % zbx_e.err_text
            return 4
        # Everything went fine. Let's return 0 and exit
        return 0


if __name__ == '__main__':
    ret = TrafficServer().run()
    print ret
    sys.exit(ret)