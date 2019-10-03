# -*- encoding: utf-8 -*-

spotlights_networks = {
    "CS:GO": 50,
    "LoL (pro)": 51,
    "LoL (amateur)": 51,
    "osu!": 52,
    "Hearthstone": 53,
    "Fortnite": 54,
    "libre": 55
}

spotlights_name = {
    "CS:GO": "csgo",
    "LoL (pro)": "lol-pro",
    "LoL (amateur)": "lol-amat",
    "osu!": "osu",
    "Hearthstone": "hs",
    "Fortnite": "fortnite",
    "libre": "libre"
}

def _parse_server_response(json_data):
    return  Definition(
        ip=json_data['ip'],
        lease_time=7200,
        subnet=json_data['spotlight'],
        serial=json_data['isBanned'],
        #hostname="%s.%s.%d.%d.ua"%(json_data['name'], spotlights_name.get(json_data['spotlight']), json_data['switchPort'], json_data['switchId']),
        hostname=None,
        gateways="172.16.%d.254"%spotlights_networks.get(json_data['spotlight']),
        subnet_mask="255.255.255.0",
        broadcast_address="172.16.%d.255"%spotlights_networks.get(json_data['spotlight']),
        domain_name="ua",
        domain_name_servers=["172.16.%d.254"%spotlights_networks.get(json_data['spotlight'])],
        ntp_servers=None,
        extra=None,
    )


import json
import logging
import urllib
import urllib2
import requests

from staticdhcpdlib.databases.generic import (Definition, Database, CachingDatabase)

_logger = logging.getLogger("extension.ua-app")

#This class implements your lookup method; to customise this module for your
#site, all you should need to do is edit this section.
class _HTTPLogic(object):
    def __init__(self):
        from staticdhcpdlib import config

        try:
            self._uri = config.X_HTTPDB_URI
        except AttributeError:
            raise AttributeError("X_HTTPDB_URI must be specified in conf.py")
        self._headers = getattr(config, 'X_HTTPDB_HEADERS', {})
        self._parameters = getattr(config, 'X_HTTPDB_PARAMETERS', {})
        self._parameter_key_mac = getattr(config, 'X_HTTPDB_PARAMETER_KEY_MAC', 'mac')
        self._post = getattr(config, 'X_HTTPDB_POST', True)
        self._default_name_servers = getattr(config, 'X_HTTPDB_DEFAULT_NAME_SERVERS', '')
        self._default_lease_time = getattr(config, 'X_HTTPDB_DEFAULT_LEASE_TIME', 0)
        self._default_serial = getattr(config, 'X_HTTPDB_DEFAULT_SERIAL', 0)

    def _lookupMAC(self, mac):

        global _parse_server_response

        try:
            r = requests.get("%s/%s" % (self._uri, str(mac)))

            _logger.debug("Sending request to '%(uri)s' for '%(params)s'..." % {
                'uri': self._uri,
                'params': mac,
            })

            code = r.status_code

            _logger.debug("MAC response received from '%(uri)s' for '%(mac)s'" % {
                'uri': self._uri,
                'mac': str(mac),
            })
        except Exception, e:
            _logger.error("Failed to lookup '%(mac)s' on '%(uri)s': %(error)s" % {
                'uri': self._uri,
                'mac': str(mac),
                'error': str(e),
            })
            raise
        else:
            if code == 404:
                _logger.debug("Unknown MAC response from '%(uri)s' for '%(mac)s': %(results)r" % {
                    'uri': self._uri,
                    'mac': str(mac),
                    'results': None,
                })
                return None
            elif code == 407:
                _logger.debug("Unauthorized for '%(mac)s': %(results)r" % {
                    'uri': self._uri,
                    'mac': str(mac),
                    'results': None,
                })
                return None
            elif code == 200:
                results = r.json()

                _logger.debug("Known MAC response from '%(uri)s' for '%(mac)s': %(results)r" % {
                    'uri': self._uri,
                    'mac': str(mac),
                    'results': results,
                })

                rep = None
                if isinstance(results, list): #Multi-definition response
                    rep = [_parse_server_response(self._set_defaults(result)) for result in results]
                rep = _parse_server_response(self._set_defaults(results))
                print rep.hostname

                if rep.serial == True:
                    _logger.debug("Banned user for '%(mac)s': %(results)r" % {
                        'uri': self._uri,
                        'mac': str(mac),
                        'results': results,
                    })
                    return None
                rep.serial = 0
                return rep
            else: #The server sent back 'null' or an empty object
                _logger.debug("Unknown MAC response from '%(uri)s' for '%(mac)s': %(results)r" % {
                    'uri': self._uri,
                    'mac': str(mac),
                    'results': None,
                })
                return None

    def _set_defaults(self, json_data):
        """
        Set the default values on a server response if they do not
         already have usable values

        :param dictionary json_data: Dictionary containing response data
        :return dictionary: The modified dictionary with defaults
        """
        if not json_data.get('serial'):
            json_data['serial'] = self._default_serial
        if not json_data.get('domain_name_servers'):
            json_data['domain_name_servers'] = self._default_name_servers
        if not json_data.get('lease_time'):
            json_data['lease_time'] = self._default_lease_time
        return json_data

class HTTPDatabase(Database, _HTTPLogic):
    def __init__(self):
        _HTTPLogic.__init__(self)

    def lookupMAC(self, mac):
        return self._lookupMAC(mac)

class HTTPCachingDatabase(CachingDatabase, _HTTPLogic):
    def __init__(self):
        from staticdhcpdlib import config
        if hasattr(config, 'X_HTTPDB_CONCURRENCY_LIMIT'):
            CachingDatabase.__init__(self, concurrency_limit=config.X_HTTPDB_CONCURRENCY_LIMIT)
        else:
            CachingDatabase.__init__(self)
        _HTTPLogic.__init__(self)
