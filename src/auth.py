""" auth.py file authenticating into the Asana API."""
import os
import asana
from logger import log_info, log_error

ASANA_TOKEN = os.getenv('ASANA_TOKEN')

if not ASANA_TOKEN:
    MSG = '''
    Missing ASANA_TOKEN. Please add the token for the super admin or service account to the environment variables.
    > Example: "export ASANA_TOKEN=1/1000000000000001:e123abc456def789ghi1011jklmn01"
    '''
    log_error(MSG)
    raise ValueError(MSG)

# Authenticate and get the Asana client
client = asana.Client.access_token(ASANA_TOKEN)
log_info('Authenticated Asana client.')

# TODO: Handle Asana request options for max_retries
