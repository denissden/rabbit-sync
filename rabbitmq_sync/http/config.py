import configparser
import logging

config = configparser.ConfigParser()
config.read('rabbit_sync_http_endpoints.ini')

# example
#
# [main]
# only_with_prefix = false
#
# [consul]
# prefix = /consul
# destination = consul:8500

PREFIX_TO_DESTINATION = dict()
ONLY_WITH_PREFIX = config.getboolean('http', 'only_with_prefix',  fallback=False)
HTTP_TIMEOUT_SECONDS = config.getfloat('http', 'timeout',  fallback=5.)

for section in config.sections():
    if section == 'http':
        continue

    content = config[section]
    prefix = content.get('prefix')
    destination = content.get('destination')

    if all([prefix, destination]):
        PREFIX_TO_DESTINATION[prefix] = destination

logging.info('Http proxy config: %s', PREFIX_TO_DESTINATION)