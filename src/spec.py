"""
This module implements serialization, validation and execution of specification files.
"""
import json
import jsonschema
import os
import pathlib
import re
import requests
import subprocess

import config


_SCHEMA = json.loads(pathlib.Path('./schema/schema.json').read_text(encoding='utf-8'))
"""
The specifications schema file loaded as a python object.
"""


class Specification:
    """
    This class validates, verifies and executes the specification files.
    """

    def __init__(self, spec):
        """
        Loads the received specification.
            :param spec: str | dict - The specification string to load from the user data or the dict to create a new
            specification.
        """
        if isinstance(spec, str):
            self._deserialize(spec)
        elif isinstance(spec, dict):
            self.spec = spec
            self._validate_spec()
            self._serialize()
        else:
            raise TypeError('spec, expected: str | dict')

    def _validate_spec(self):
        """
        Validates the current specification against the json schema.
        """
        jsonschema.validate(self.spec, _SCHEMA)

    def _serialize(self):
        """
        Serializes the specification 
        """
        name = self.spec['name']
        icon = self.spec['tray']['icon']
        icon_url = requests.utils.urlparse(icon)
        if icon_url.scheme == '' and re.match(r'^(\w:)?(\\|\/).*', icon_url.path) or icon_url.scheme == 'file':
            path = pathlib.Path(icon_url.path)
            if not path.exists():
                raise FileNotFoundError('icon file not found')
            icon_content = path.read_bytes()
        else:
            response = requests.get(icon)
            if response.status_code != 200:
                raise ConnectionError('icon fetch fail')
            icon_content = response.content
        spec_path = os.path.join(config.USER_DATA_PATH, f'{name}.json')
        icon_path = os.path.join(config.USER_DATA_PATH, f'{name}.png')
        self.spec['tray']['icon'] = icon_path
        pathlib.Path(spec_path).write_text(json.dumps(self.spec))
        pathlib.Path(icon_path).write_bytes(icon_content)

    def _deserialize(self, name):
        """
        Deserializes the specification file from its name in the user data path.
        """
        spec_path = os.path.join(config.USER_DATA_PATH, f'{name}.json')
        icon_path = os.path.join(config.USER_DATA_PATH, f'{name}.png')
        if not os.path.exists(spec_path) or not os.path.exists(icon_path):
            raise FileNotFoundError('spec or icon file not found')
        self.spec = json.loads(pathlib.Path(spec_path).read_text())

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

    def _build_tray_data_function(self):
        tray = self.spec['tray']
        icon = tray['icon']
        icon = tray['info']
        # TODO

    def single_run(self):
        text = self.command_function()
        lines = self.filter_function(text)
        extracted_data = self.extract_function(lines)
        return extracted_data


def test():
    # creation from new spec
    new_spec = Specification(json.loads(pathlib.Path('./specs/disk.json').read_text()))
    
    # creation from stored spec
    stored_spec = Specification('disk')
    
    # rewrite first created specification
    new_spec = Specification(json.loads(pathlib.Path('./specs/disk.json').read_text()))


if __name__ == '__main__':
    test()
