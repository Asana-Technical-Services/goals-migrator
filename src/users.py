""" users.py file to handle getting Asana users for a the given workspace."""
# pylint: disable=maybe-no-member
import os
import pandas as pd
from auth import client as asana_client

WORKSPACE_GID = os.getenv('WORKSPACE_GID')


def get_members_data():
    """Read an Asana organization USERS CSV export and reads it into
    a pandas dataframe for processing."""
    name_key = 'Name'
    email_key = 'Email Address'
    members_df = pd.read_csv('./members.csv', usecols=[name_key, email_key])
    members_data = members_df.to_dict(orient='records')
    formatted_members_data = {}
    for data in members_data:
        formatted_members_data[data[email_key]] = data[name_key]
    return formatted_members_data


def get_all_users():
    """A helper method to get all users for the given workspace.
    Note this is utilizes the Asana API's pagination scheme and makes multiple
    calls to get all users in the workspace.
    API Reference: https://developers.asana.com/reference/getusers"""
    offset = None
    params = {
        'opt_fields': 'gid,email,name',
        'workspace': WORKSPACE_GID,
    }
    data = []
    while True:
        result = asana_client.users.get_users(
            params, offset=offset, full_payload=True, limit=100, iterator_type=None, opt_pretty=True)
        data += result['data']
        if 'next_page' in result and result['next_page'] is not None:
            offset = result['next_page']['offset']
        else:
            break
    return data


# Constant variables to export and use throughout
MEMBERS_MAPPINGS = get_members_data()
