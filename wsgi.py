import sys
import logging.config
import yaml

sys.path.insert(0,'/var/www/HZ2')
from hz2 import app as application

# Putting the logging stuff here
logger = logging.getLogger("hz2Main")

with open("log.conf", 'rt') as f:
    config = yaml.safe_load(f.read())

logging.config.dictConfig(config)
