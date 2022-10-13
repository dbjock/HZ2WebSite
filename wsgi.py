import sys
import logging.config
import yaml

sys.path.insert(0,'/var/www/HZ2')
from hz2 import app as application

# Putting the logging stuff here
logger = logging.getLogger("hz2Main")
basedir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(basedir,'log.conf' ), 'rt') as f:
    config = yaml.safe_load(f.read())

logging.config.dictConfig(config)
