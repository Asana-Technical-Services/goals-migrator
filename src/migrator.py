""" migrator.py file to handle the main execution and migration of CSV to Asana goals."""
# pylint: disable=wrong-import-position
import os
import sys
sys.path.append('.')
sys.path.append('./utils')
# pylint: enable=wrong-import-position
import argparse
import numpy as np
import pandas as pd
import parsers
import mappings
from goal import Goal
from logger import log_info


processed_goals = {}


def get_goal_row_from_id(goals_df, goal_id):
    """Gets a dataframe row (Series) based on a search value of the ID column"""
    # Squeeze to convert to pandas Series data type
    return goals_df.loc[goals_df['Id'] == goal_id].squeeze()


def link_aligned_goals(goals_df, child_goal):
    """Creates or updates a new 'parent' goal from a child goal's
    aligned to reference and links the child goal to the parent goal.
    """
    # If this goal is aligned (sub-goal) of another goal, get it
    goal_id = parsers.parse_goal_id(child_goal.data['aligned_to'])
    aligned_goal_data_row = get_goal_row_from_id(goals_df, goal_id)
    goal_has_parent = aligned_goal_data_row['Aligned To (weight, Objective ID)']

    # If this goal is aligned to another, create/update and link it
    if not aligned_goal_data_row.empty:
        aligned_goal = Goal(aligned_goal_data_row)
        already_processed = aligned_goal.data['id'] in processed_goals
        # Skip creating/updating the aligned goal since we've already created it
        if already_processed:
            # Get and set the gid to be used in link child goals below
            aligned_goal.gid = processed_goals[aligned_goal.data['id']]
        else:
            aligned_goal.create_or_update_goal()
            processed_goals[aligned_goal.data['id']] = aligned_goal.gid
        aligned_goal.link_child_goal(child_goal, goal_has_parent)


def create_or_read_output_csv(file_path):
    """Create or reads an existing output CSV file for the processed
    goal data.
    """
    headers = ['goal_index', 'goal_id', 'asana_goal_gid']
    df = None
    if not os.path.isfile(file_path):
        df = pd.DataFrame(columns=headers)
        df.to_csv(file_path, index=False)
    else:
        df = pd.read_csv(file_path, dtype=str)
    return df


def preprocess_df(df):
    """Formats the input dataframe to handle blank values and convert them to None types"""
    # Convert and handle NaN values to None
    df = df.replace({np.nan: None})
    df = df.astype(str)
    df = df.replace({'None': None})

    # Remove duplicate rows
    df = df.drop_duplicates()
    return df

# A flag to indicate if we should skip updating the goals
# for processed goal IDs found in the output CSV


def main(skip_processed=True):
    """Main function for the migrator script to process goals from a CSV
    and create Goal class objects to create goals in Asana
    """
    log_info('Beginning main execution of goals migrator.')
    log_info(f'skip_processed flag set to: {skip_processed}')
    if skip_processed:
        log_info(
            'Ignoring previously processed goals. See goals_processed.csv for more information.'
        )
    else:
        log_info(
            'Processing all goals and ingore previously procssed goals.'
        )

    # Import and read the goals data CSV
    # TODO: For now hard-code column names to handle blank column names that hold
    # additional check-in notes in rows
    column_names = mappings.CSV_COLUMN_NAMES

    goals_df = pd.read_csv('./goals.csv',  names=column_names)
    goals_df = preprocess_df(goals_df)
    log_info(f'Imported <{len(goals_df)}> goals.')

    # If it doesn't already exist, create the csv file to keep track of processed goals
    processed_file_path = './goals_processed.csv'
    processed_df = create_or_read_output_csv(processed_file_path)

    for index, row in goals_df.iterrows():
        if index == 0:  # skip processing the column row
            continue

        # Skip any goals that have already been processed and found in the output csv
        if skip_processed and not processed_df.empty:
            goal_id = row['Id']
            if goal_id in processed_df['goal_id'].values:
                log_info(f'Skipping goal ID: {goal_id}')
                continue

        log_info(f'Processing goal index: {index}')
        goal = Goal(row)
        goal.create_or_update_goal()
        processed_goals[goal.data['id']] = goal.gid
        link_aligned_goals(goals_df, goal)

        # Write the processed goal data to the ouput CSV
        if os.path.exists(processed_file_path):
            data_df = pd.DataFrame([{
                'goal_index': index,
                'goal_id': goal.data['id'],
                'asana_goal_gid': goal.gid,
            }],)
            data_df.to_csv(processed_file_path, mode='a',
                           index=False, header=False)

    log_info('COMPLETE: Finished main execution of goals migrator.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--all", action="store_true")
    args = parser.parse_args()
    skip_arg = not args.all
    main(skip_arg)
