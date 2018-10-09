"""
This module implements validation and single run of specifications files
"""
import collections
import json
import jsonschema
import pathlib
import re
import subprocess
from functools import reduce


_SCHEMA = json.loads(pathlib.Path('./schema/schema.json').read_text(encoding='utf-8'))
"""
The specifications schema file loaded as a python object.
"""


class Specification:

    def __init__(self, spec):
        self.spec = spec if isinstance(spec, dict) else json.loads(spec)
        self._validate_spec()
        self.name = self.spec['name']
        self.interval = self.spec['interval']
        self.extract = self.spec['extract']
        self.command_function = self._build_command_function()
        self.filter_function = self._build_filter_function()
        self.extract_function = self._build_extract_function()

    def _validate_spec(self):
        try:
            jsonschema.validate(self.spec, _SCHEMA)
        except jsonschema.ValidationError as e:
            raise Exception(f'VALIDATION FAIL. message: {e.message}; cause: {e.cause}')

    def _build_command_function(self):
        command = self.spec['command']

        def run_command():
            result = subprocess.CompletedProcess = subprocess.run(command, capture_output=True)
            if result.returncode != 0:
                raise Exception(f'RUN FAIL. command return code is not 0: {result.returncode}')
            return result.stdout.decode('utf-8')

        return run_command

    def _build_filter_function(self):
        filter_ = self.spec['filter']
        if 'all' in filter_:
            return lambda text: {0: text}
        elif 'lines' in filter_:
            lines = set(filter_['lines'])
            return lambda text: {index: line for line in text.splitlines() if line in lines}
        elif 'match' in filter_:
            pattern = filter_['match']
            matcher = re.compile(pattern)
            return lambda text: {index: match.group() for index, match in enumerate(matcher.finditer(text))}

    def _build_extract_function(self):
        rules = self.spec['extract']
        extractors = []
        for rule in rules:
            key = rule['key']
            if isinstance(key, list):
                def key_comparer(index): return index in key
            elif isinstance(key, dict):
                def key_comparer(index): return index >= key['from'] and index <= key['to']

            data = rule['data']
            matcher = re.compile(data)

            def data_extractor(line):
                match = matcher.search(line)
                if match == None:
                    return None
                return {
                    **{0: match.group(0)},
                    **{index + 1: match for index, match in enumerate(match.groups())},
                    **match.groupdict(),
                }

            extractors.append({'key_comparer': key_comparer, 'data_extractor': data_extractor})

        def extract_function(lines):
            extracted_data = {}
            for index, line in lines.items():
                matching_extractors = [extractor for extractor in extractors if extractor['key_comparer'](index)]
                if len(matching_extractors) == 0:
                    continue
                extractor = matching_extractors[-1]
                extracted_data[index] = extractor['data_extractor'](line)
            return extracted_data

        return extract_function

    def single_run(self):
        text = self.command_function()
        lines = self.filter_function(text)
        extracted_data = self.extract_function(lines)
        return extracted_data


def test():
    print(Specification(pathlib.Path('./specs/disk.json').read_text()).single_run())


if __name__ == '__main__':
    test()
