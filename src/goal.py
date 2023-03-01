"""goal.py file for class and operations on goal CSV data to Asana Goals API."""
# pylint: disable=maybe-no-member
import os
import parsers
import mappings
from logger import log_info, log_error
from users import get_all_users, MEMBERS_MAPPINGS
from auth import client as asana_client


WORKSPACE_GID = os.getenv('WORKSPACE_GID')
SUPER_ADMIN_GID = os.getenv('SUPER_ADMIN_GID')
ASANA_BASE_URL = asana_client.DEFAULT_OPTIONS['base_url']
WORKSPACE_USERS = get_all_users()


def get_all_time_periods(start_on='', end_on=''):
    """Gets all time periods existing in the workspace
    API Reference: https://developers.asana.com/reference/gettimeperiods
    """
    offset = None
    params = {'workspace': WORKSPACE_GID}
    if start_on:
        params['start_on'] = start_on
    if end_on:
        params['end_on'] = end_on
    data = []
    while True:
        result = asana_client.time_periods.get_time_periods(
            params, offset=offset, full_payload=True, limit=100, iterator_type=None, opt_pretty=True)
        data += result['data']
        if 'next_page' in result and result['next_page'] is not None:
            offset = result['next_page']['offset']
        else:
            break
    return data


def get_all_goals():
    """Gets all the goals existing in the workspace
    API Reference: https://developers.asana.com/reference/getgoals
    """
    offset = None
    params = {
        'workspace': WORKSPACE_GID,
        'opt_fields': 'notes'
    }
    data = []
    while True:
        result = asana_client.goals.get_goals(
            params, offset=offset, full_payload=True, limit=100, iterator_type=None, opt_pretty=True)
        data += result['data']
        if 'next_page' in result and result['next_page'] is not None:
            offset = result['next_page']['offset']
        else:
            break
    return data


# Store the relevant workspace data once to not make multiple API calls
TIME_PERIODS = get_all_time_periods()
workspace_goals = get_all_goals()


if not WORKSPACE_GID:
    MSG = '''
    Missing WORKSPACE_GID. Please add the GID for the workspace to the environment variables.
    > Example: "export WORKSPACE_GID=1001234567890000"
    '''
    log_error(MSG)
    raise ValueError(MSG)

if not SUPER_ADMIN_GID:
    MSG = '''
    Missing SUPER_ADMIN_GID. Please add the GID for the super admin or service account to the environment variables.
    > Example: "export SUPER_ADMIN_GID=1001234567890000"
     '''
    log_error(MSG)
    raise ValueError(MSG)


class Goal():
    """Goal class to process CSV data into Asana goal data for API requests."""

    def __init__(self, df_row) -> None:
        self.df_row = df_row
        self.data = self.map_data(df_row)
        self.params = self.get_goal_params()
        self.gid = None

    def map_data(self, df_row):
        """Takes in an input dataframe row (Series object) and maps the column values
        for the specified row based on the fields specified in mappings.py.
        """
        data = {}
        goal_mappings = mappings.GOAL_MAPPINGS
        for key, value in goal_mappings.items():
            # Special handling: If this is an array of columns to capture
            if 'Array::' in value:
                capture_string = parsers.regex_parse(
                    value, 'Array::(.*)')
                data[key] = list(df_row.values[list(df_row.index).index(
                    capture_string):][::-1])  # reverse to sort
            else:
                data[key] = df_row[value]
        return data

    def create_or_update_goal(self):
        """Creates or updates a goal in Asana using the Asana API.
        Uses the mapped data in self.data to publish data into the Asana goal.
        """
        # If the goal doesn't yet exist, create it
        # else update it
        goal = self.check_if_goal_exists()
        created_goal_gid = None
        if not goal['exists']:
            created_goal_gid = self.create_goal()
            workspace_goals.append({
                "gid": created_goal_gid,
                "notes": self.params['notes'],
            })
        else:
            created_goal_gid = self.update_goal(goal['gid'])
        self.gid = created_goal_gid

        # We need to call this after the goal is created or updated
        # in order to grant goal edit/delete permissions to both
        # the super admin and the actual goal owner
        if self.data['owner']:
            self.update_goal_owner()

        # Create/update the goal progress metric
        if self.data['current_number_value']:
            is_parent_goal = self.data['aligned_to'] is None
            self.create_goal_metric(is_parent_goal)

            if not goal['exists']:
                # If no historical status updates or last checkins but there is a status, set it
                # Note, this requires a goal metric to have been created
                status_updates = self.data['status_updates']
                last_status_update = self.data['last_status_update']
                is_invalid_list = all(item is None for item in status_updates)
                if is_invalid_list and last_status_update is None and self.data['status']:
                    self.set_status()
        return self.gid

    def check_if_goal_exists(self):
        """Checks if the Asana goal exists already in the workspace based on
        any reference ID previously published in the goal's description"""
        does_exist = False
        goal_gid = None
        # Loop through all goal data and check against
        # the id in the goal description (notes)
        for item in workspace_goals:
            goal_reference_id = self.get_reference_id(item['notes'])
            if self.data['id'] == goal_reference_id:
                does_exist = True
                goal_gid = item['gid']
                break
        return {'exists': does_exist, 'gid': goal_gid}

    def create_goal(self):
        """Creates a goal in Asana using the Asana API.
        Uses the mapped data in self.data to publish data into the Asana goal.
        API Reference: https://developers.asana.com/reference/creategoal
        """
        result = asana_client.goals.create_goal(self.params, opt_pretty=True)
        log_info(f'Received create goal result as: {result}')
        # Create and fill in the historical status updates
        if result:
            self.create_historical_status_updates(result['gid'])
        return result['gid'] if result else None

    def update_goal(self, goal_gid):
        """Updates an existing goal in Asana using the Asana API.
        Uses the mapped data in self.data to publish data into the Asana goal.
        API Reference: https://developers.asana.com/reference/updategoal
        """
        self.params = self.get_goal_params(True)
        result = asana_client.goals.update_goal(
            goal_gid, self.params, opt_pretty=True)
        log_info(f'Received update goal result as: {result}')
        return result['gid'] if result else None

    def link_child_goal(self, child_goal, parent_goal_has_parent=False):
        """Link a child goal to the parent goal in Asana using the Asana API.
        This method updates the parent goals existing goal metric to manual
        if it itself has it's own parent (since new subgoals can't be set to automatic progress)
        API Reference: https://developers.asana.com/reference/addsupportingrelationship
        """
        parent_goal_gid = self.gid
        child_goal_gid = child_goal.gid
        log_info(
            f'Linking child goal <{child_goal_gid}> to parent goal <{parent_goal_gid}>'
        )
        params = {
            'supporting_resource': child_goal_gid,
            'contribution_weight': 1  # Subgoals should always contribute to parent goal for this
        }

        # If the parent goal we're about to link to also has it's own parent goal
        # convert the linking parent's metric to automatic progress
        # This is handled in the Asana API by creating a new metric which overwrites
        # the old one
        if parent_goal_has_parent:
            self.create_goal_metric(True)

        result = asana_client.goal_relationships.add_supporting_relationship(
            parent_goal_gid,
            params
        )
        log_info(f'Received link goals result as: {result}')

    def get_goal_params(self, is_update=False):
        """Gets and formats the data object into parameters for various API calls."""
        # Set the Ally reference id to be used to check for existing goals
        # Append any existing notes if this is called to update a goal
        goal_id = self.data['id']
        notes_text = f'[Ref: Ally Id: {goal_id}]\n\n'
        if is_update and 'notes' in self.data:
            existing_notes = self.data['notes']
            notes_text += f'{existing_notes}'

        # Set the goal to the workspace level only if its type is
        # "Organization", any other value or empty should be a private/team goal
        goal_type = self.data['goal_type']
        workspace_level = False
        if goal_type == 'Organization':
            workspace_level = True

        params = {
            'due_on': self.data['due_on'],
            'is_workspace_level': workspace_level,
            'name': self.data['name'],
            'notes': notes_text,
            # Initially set admin account as owner and update to goal owner later
            # in order for super admin to have permissions to edit/delete
            'owner': SUPER_ADMIN_GID,
            'start_on': self.data['start_on'],
            'workspace': WORKSPACE_GID
        }

        # Check for and set available time periods into the params
        time_period_gid = self.get_time_period()
        if time_period_gid:
            params['time_period'] = time_period_gid
        return params

    def get_reference_id(self, input_string):
        """A helper method to get the reference ID from the CSV cell value"""
        return parsers.regex_parse(input_string, r'Ref: Ally Id:\s(\d+)')

    def get_time_period(self):
        """Gets the corresponding time period from the possible time periods in the workspace
        based on either a start and end date for the time period or the fallback to the string
        name of the time period.
        """
        # First attempt to get the time period based off the start and end dates
        start_date = self.data['start_on']
        end_date = self.data['due_on']
        # Necessary because it gets used as a generator object
        time_periods_initial = TIME_PERIODS
        # Necessary because it gets used as a generator object
        time_periods_retry = TIME_PERIODS
        time_period = next((period for period in time_periods_initial
                            if period['start_on'] == start_date
                            and period['end_on'] == end_date), None)

        # If we failed to get a time period from those dates, search and retrieve
        # using the period string
        if not time_period:
            log_info('Couldnt find time period. Checking against period string.')
            period = self.data['period']
            year_text = parsers.regex_parse(period, r'.*\s(\d+)')
            quarter_text = parsers.regex_parse(period, r'(Q\d)\s\d+')

            # Convert the period data to QX FYXX format
            display_value = ''
            if year_text and 'Annual' in period:
                # Get the last two characters of year string
                display_value = f'FY{year_text[-2:]}'
            elif quarter_text and year_text:
                display_value = f'{quarter_text} FY{year_text[-2:]}'

            time_period = next((item for item in time_periods_retry
                                if item['display_name'] == display_value), None)
        return time_period['gid'] if time_period else None

    def create_historical_status_updates(self, goal_gid):
        """Creates all the Asana status update objects on the goal (sorted by timestamp)
        for every checkin cell value found in the CSV.
        """
        status_updates = self.data['status_updates']
        for item in status_updates:
            if item is not None:
                self.create_historical_status_update(goal_gid, item)

        # If the historical status updates were empty, check for an existing last checkin
        is_invalid_list = all(item is None for item in status_updates)
        last_status_update = self.data['last_status_update']
        if is_invalid_list and last_status_update is not None:
            self.create_checkin_status_update(goal_gid)
        return

    def create_historical_status_update(self, goal_gid, status_update_data):
        """Creates Asana status update objects on the goal."""
        # Parse the status value and map to the correct status type
        status_value = parsers.parse_checkin_status(status_update_data)
        # Parse the timestamp for record keeping
        timestamp = parsers.parse_checkin_timestamp(status_update_data)
        # Parse the notes text for the update
        notes = parsers.parse_checkin_notes(status_update_data)
        return self.create_status_update(goal_gid, status_value, timestamp, notes)

    def create_checkin_status_update(self, goal_gid):
        """Creates a status update for the specified goal based on its self.data."""
        status_value = self.data['status']
        timestamp = self.data['last_status_timestamp']
        notes = self.data['last_status_update']
        return self.create_status_update(goal_gid, status_value, timestamp, notes)

    def create_status_update(self, goal_gid, status_value, timestamp, notes):
        """Creates a status update in Asana using the Asana API.
        API Reference: https://developers.asana.com/reference/createstatusforobject
        """
        status_type = ''
        if status_value == 'On Track':
            status_type = 'on_track'
        elif status_value == 'At Risk':
            status_type = 'at_risk'
        elif status_value == 'Behind':
            status_type = 'off_track'
        elif status_value == 'Closed':
            status_type = 'achieved'
        else:
            return  # if there isn't a status update, return

        title = f'Status Update: {status_value} - {timestamp}'
        notes_text = f'[Ref: Ally Checkin Timestamp: {timestamp}]\n\n'
        notes_text += str(notes)
        params = {
            'parent': goal_gid,
            'status_type': status_type,
            'text': notes_text,
            'title': title,
        }
        result = asana_client.status_updates.create_status_for_object(
            params, opt_pretty=True)
        return result['gid'] if result else None

    def set_status(self):
        """Helper method to update the goal's status using the Asana API.
        API Reference: https://developers.asana.com/reference/updategoal
        """
        status_value = self.data['status']
        status_type = ''
        if status_value == 'On Track':
            status_type = 'green'
        elif status_value == 'At Risk':
            status_type = 'yellow'
        elif status_value == 'Behind':
            status_type = 'red'
        elif status_value == 'Closed':
            status_type = 'achieved'
        else:
            return  # if there isn't a status update, return
        params = {'status': status_type}
        result = asana_client.goals.update_goal(
            self.gid, params, opt_pretty=True)
        return result['gid'] if result else None

    def update_goal_owner(self):
        """Helper method to update the goal's owner using the Asana API.
        API Reference: https://developers.asana.com/reference/updategoal
        """
        owner = self.data['owner']
        owner_gid = self.find_mapped_owner_gid(owner)
        if not owner_gid:
            return
        params = {'owner': owner_gid}
        result = asana_client.goals.update_goal(
            self.gid, params, opt_pretty=True)
        return result['gid'] if result else None

    def find_mapped_owner_gid(self, owner):
        """Searches for and return the goal owner's GID based on first and last name,
        the email, and the member mappings in the members.csv"""
        # TODO: Implement performance improvement of pre-mapping these during initial script run
        # First check if the owner is in the user mappings
        valid_email = next(
            (email for email, name in MEMBERS_MAPPINGS.items() if owner == name), None)
        if valid_email:
            # Then use the associated email and check if a user in the workspace
            found_user = next(
                (user for user in WORKSPACE_USERS if user['email'] == valid_email), None)
            if found_user:
                return found_user['gid']
        # Since we didn't find the goal owner in the mappings, set the owner to the user admin
        log_error(
            f'Could not find owner <{owner}> in members.csv for goal {self.data}. \
            Setting default owner to super admin.'
        )
        return

    def create_goal_metric(self, is_parent_goal=False):
        """Creates a goal metric in Asana using the Asana API.
        Uses the mapped data in self.data to publish data into the Asana goal.
        Takes an input parameter to denote if this is a parent goal and should have
        "subgoal_progress" (automatic) metric tracking or not.
        API Reference: https://developers.asana.com/reference/creategoalmetric
        """
        progress_source = 'subgoal_progress' if is_parent_goal else 'manual'
        params = {
            'progress_source': progress_source,
            'precision': 1,
            'unit': 'percentage'
        }

        # The API expects number values if calculating manually
        if not is_parent_goal:
            initial_number_value = float(
                self.data['initial_number_value']) / 100
            current_progress_value = float(
                self.data['current_number_value']) / 100
            target_number_value = float(self.data['target_number_value']) / 100
            params['initial_number_value'] = initial_number_value
            params['current_number_value'] = current_progress_value,
            params['target_number_value'] = target_number_value

        result = asana_client.goals.create_goal_metric(
            self.gid, params, opt_pretty=True)
        log_info(f'Received create goal metric result as: {result}')
        return result['gid'] if result else None
