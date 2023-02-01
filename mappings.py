"""mappings.py to hold constant variables for goal mappings, team mappings,
and hard-coded CSV column names
"""
# Mappings to map the csv columns to specific goal data keys used throughout the scripts
GOAL_MAPPINGS = {
  'aligned_to': 'Aligned To (weight, Objective ID)',
  'current_number_value': 'Progress %',
  'due_on': 'End Date',
  'id': 'Id',
  'initial_number_value': 'Start',
  'last_status_update': 'Last Check-in Note',
  'last_status_timestamp': 'Last Check-in',
  'name': 'Title',
  'notes': 'Description',
  'owner': 'Creator',
  'goal_type': 'OKR type',
  'period': 'Period',
  'start_on': 'Start Date',
  'status': 'Status',
  'status_updates': 'Array::Checkins',
  'target_number_value': 'Target',
}

TEAM_MAPPINGS = {

}

# Required to handle blank column names that hold additional check-in notes in rows
# that expand based on the max number of entries/columns for checkin data
CSV_COLUMN_NAMES = [
  'Id',
  'Title',
  'Tag',
  'OKR type',
  'Type name',
  'Creator',
  'Owner',
  'Period',
  'Start Date',
  'End Date',
  'Description',
  'Aligned To (weight, Objective ID)',
  'Metric Name',
  'Target',
  'Object Type',
  'Goal Type',
  'Start',
  'Created At',
  'Last Check-in',
  'Progress %',
  'Status',
  'Last Check-in Note',
  'Score',
  'Checkins',
  'Blank 1',
  'Blank 2',
  'Blank 3',
  'Blank 4',
  'Blank 5',
  'Blank 6',
  'Blank 7',
  'Blank 8',
  'Blank 9',
  'Blank 10',
  'Blank 11',
  'Blank 12',
  'Blank 13',
]
