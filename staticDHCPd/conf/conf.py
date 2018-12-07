# Whether to daemonise on startup (you don't want this during initial setup)
DAEMON = False
UID = 1000
GID = 1000
DHCP_SERVER_IP = '10.0.70.1'

import ua_app
X_HTTPDB_URI = 'https://api-dev-ua.apps.uttnetgroup.fr/api/v1/networks'
#X_HTTPDB_URI = 'http://bins.apps.uttnetgroup.fr/1bys9kq1'
DATABASE_ENGINE = ua_app.HTTPDatabase

import sys
import os
sys.path.append(os.path.abspath("/etc/staticDHCPd/extensions"))

import dynamism
import logging
import requests

_logger = logging.getLogger('dhcp')
global _dynamic_pool
_dynamic_pool = dynamism.DynamicPool("Joueurs_poubelle", 0, 1800, "joueurs-poubelle", subnet_mask="255.255.254.0", gateway="172.16.99.254",
                                     broadcast_address="172.16.99.255", domain_name_servers=['172.16.99.254'])
_dynamic_pool.add_ips(['172.16.98.' + str(i) for i in range(10, 255)])
_dynamic_pool.add_ips(['172.16.99.' + str(i) for i in range(1, 250)])


def handleUnknownMAC(packet, method, mac, client_ip, relay_ip, port):
    bail = _dynamic_pool.handle(method, packet, mac, client_ip)
    payload = {
        "mac": mac._mac_string,
        "ip": bail.ip._ip_string
    }
    r = requests.post("https://api-dev-ua.apps.uttnetgroup.fr/api/v1/networks", json=payload)
    _logger.info("%s - %s - API : %d"%(mac, bail.ip, r.status_code))
    return bail
