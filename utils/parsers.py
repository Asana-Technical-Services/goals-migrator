"""parsers.py file for utility helper methods to parse information from strings."""
import re


def parse_goal_id(input_string):
    """ A helper method to parse the goal ID from a string."""
    return regex_parse(input_string, r'Id:\s(\d+)')


def parse_goal_weight(input_string):
    """ A helper method to parse the goal weight from a string."""
    return regex_parse(input_string, r'weight:\s(\d+)')


def parse_checkin_timestamp(input_string):
    """ A helper method to parse the checkin timestamp from a string."""
    return regex_parse(input_string, r'(\[.*UTC.*\]).*')


def parse_checkin_status(input_string):
    """ A helper method to parse the checkin status from a string."""
    return regex_parse(input_string, r'Status:\s(.*)')


def parse_checkin_notes(input_string):
    """ A helper method to parse the checkin notes from a string."""
    return regex_parse(input_string, r'Note:\s(.*[\s\S]+)Metric Name:')


def regex_parse(input_string, regex):
    """A base method to search for a capturing group match
    based on a given input string and a corresponding regex."""
    invalid_input = (
        not input_string
        or not regex
        or len(input_string) <= 0
        or len(regex) <= 0
    )
    if invalid_input:
        return None
    result = re.search(regex, input_string)
    return result.group(1) if result else None
