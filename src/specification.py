"""
This module implements validation and single run of specifications files
"""
import collections
import jsonschema
import re
import subprocess
from functools import reduce


"""
Specification schema
"""
_SCHEMA = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'interval': {'type': 'number'},
        'command': {
            'type': 'array',
            'items': {'type': 'string'}
        },
        'filter': {
            'type': 'object',
            'properties': {
                'pattern': {'type': 'string'},
                'flags': {
                    'type': 'object',
                    'properties': {
                        'multiline': {'type': 'boolean'},
                        'dotall': {'type': 'boolean'},
                        'intensive': {'type': 'boolean'},
                        'extended': {'type': 'boolean'},
                        'ascii': {'type': 'boolean'}
                    }
                }
            }
        },
        'split': {
            'type': 'object',
            'properties': {
                'key': {'type': 'string'}
            }
        },
        'apply': {
            'type': 'object'
        }
    }
}


def _build_filter_function(specification):
    """
    Builds the specification filter function fot the specification, the result function expects the specification
    command output and returns a list of matches found in the command output using the provided pattern.
    """
    flags_dict = {
        'multiline': re.RegexFlag.MULTILINE,
        'dotall': re.RegexFlag.DOTALL,
        'intensive': re.RegexFlag.IGNORECASE,
        'extended': re.RegexFlag.VERBOSE,
        'ascii': re.RegexFlag.ASCII
    }
    pattern = specification['filter']['pattern']
    flags = reduce(
        lambda options, option: options | option,
        (flags_dict[option] for option, value in specification['filter']['flags'].items() if value),
        re.RegexFlag.UNICODE
    )
    filter_matcher = re.compile(pattern, flags)
    groups_dict = {index - 1: group for group, index in filter_matcher.groupindex.items()}

    def filter_function(text):
        matches_elements = filter_matcher.findall(text)
        matches_tuples = [groups if isinstance(groups, tuple) else (groups,) for groups in matches_elements]
        matches = [{groups_dict[index]: value for index, value in enumerate(match)} for match in matches_tuples]
        return matches

    return filter_function


def _build_split_function(specification):
    """
    Builds the split function, takes the output from the filter function and creates pools of matches with the same key
    provided in the specification.
    """
    key = specification['split']['key']

    def split_function(matches):
        if len(matches) == 0:
            return {}
        if key not in matches[0]:
            raise Exception(f'Key not found in match: key: {key}, colleted groups:{matches_dicts[0].keys()}')
        pools = {}
        [pools[match[key]].append(match) if match[key] in pools else pools.update({match[key]: [match]})
         for match in matches]
        pools = {
            key: {group: [match[group] for match in pool] for group in pool[0].keys()}
            for key, pool in pools.items()
        }
        return pools

    return split_function


def _build_apply_function(specification):
    """
    Builds the apply function, this function receives the pools from the filter function and apply a function for each
    pattern group specified.
    """
    functions_dict = {group: eval(function) for group, function in specification['apply'].items()}

    def apply_function(pools):
        return {
            key: {group: functions_dict[group](values) for group, values in pool.items() if group in functions_dict}
            for key, pool in pools.items()
        }

    return apply_function


def validate_specification(specification):
    """
    Validates the schema, if it fails, throw an exception.
    """
    jsonschema.validate(specification, _SCHEMA)


def run_specification(specification):
    """
    Validates and runs the specification a single time for testing purposes.
    """
    validate_specification(specification)

    name = specification['name']
    interval = specification['interval']

    # command
    command: str = specification['command']
    completed_process: subprocess.CompletedProcess = subprocess.run(command, capture_output=True)
    if completed_process.returncode != 0:
        raise Exception(f'return code: {completed_process.returncode}; error: {completed_process.stderr}')
    output: str = completed_process.stdout.decode('utf-8')

    # functions
    filter_function = _build_filter_function(specification)
    split_function = _build_split_function(specification)
    apply_function = _build_apply_function(specification)

    result = apply_function(split_function(filter_function(output)))
    return {'name': name, 'interval': interval, 'result': result}


def test():
    import jsonc
    with open('./specs/disk.jsonc') as specification_file:
        print(run_specification(jsonc.loads(specification_file.read())))


if __name__ == '__main__':
    test()
