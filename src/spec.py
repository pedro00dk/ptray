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

    @staticmethod
    def load_user_specifications():
        """
        Get all specifications in the user data folder.

        :return: list[Specification] - the user specifications
        """
        specs_data = [path for path in pathlib.Path(config.USER_DATA_PATH).glob('*.json')]
        return [Specification(spec_data.name[:spec_data.name.rfind('.')]) for spec_data in specs_data]

    def __init__(self, spec_data):
        """
        Loads the received specification.

        :param spec_data: str | dict - The specification string to load from the user data or the dict to create a new
            specification.
        """
        if isinstance(spec_data, str):
            self._deserialize(spec_data)
        elif isinstance(spec_data, dict):
            self.spec = spec_data
            self._validate_spec()
            self._serialize()
        else:
            raise TypeError('spec, expected: str | dict')

        self.execution_pipeline = self._build_execution_pipeline()

    def _validate_spec(self):
        """
        Validates the current specification against the json schema.

        :throws: jsonschema.ValidationError - if fails to validate the schema
        """
        jsonschema.validate(self.spec, _SCHEMA)

    def _serialize(self):
        """
        Serializes the specification.

        :throws: FileNotFoundError - if not find the icon as a local file
        :throws: ConnectionError - if fails to fetch the icon from the internet
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

        :throws: FileNotFoundError - if not find spec or icon file
        """
        spec_path = os.path.join(config.USER_DATA_PATH, f'{name}.json')
        icon_path = os.path.join(config.USER_DATA_PATH, f'{name}.png')
        if not os.path.exists(spec_path) or not os.path.exists(icon_path):
            raise FileNotFoundError('spec or icon file not found')
        self.spec = json.loads(pathlib.Path(spec_path).read_text())

    def _build_execution_pipeline(self):
        """
        Creates a function for running the specification pipeliene
        """
        def execution_pipeline():
            output = self._run_command()
            filtered = self._filter(output['result'])
            extracted = self._extract(filtered)
            return extracted

        return execution_pipeline

    def _run_command(self):
        """
        Runs the specification command and returns it's output as string.

        :return: dict - the command status code, result and error
        """
        command = self.spec['command']
        result = subprocess.run(command, capture_output=True)
        return {
            'code': result.returncode,
            'result': result.stdout.decode('utf-8'),
            'error': result.stderr.decode('utf-8')
        }

    def _filter(self, output):
        """
        Filters the command output, returns the filtered data in a dict.

        :param output: str - The output of the specification command
        :return: dict[int -> str] if 'all' was specified, returns a single key 0 and the entire output, if lines was
            specified, returns the line numbers as keys and the text lines as value, if a match pattern was specified,
            returns the match order as keys and the matches as values
        """
        filter_ = self.spec['filter']
        if 'all' in filter_:
            return {0: output}
        elif 'lines' in filter_:
            return {index: line for line in output.splitlines() if line in set(filter_['lines'])}
        elif 'match' in filter_:
            return {index: match.group() for index, match in enumerate(re.finditer(filter_['match'], output))}

    def _extract(self, filtered):
        """
        Extract the information from filtered data, filtering the remaining matched strings in data groups. Keys that
        matches more than one extractor will be processed by the last matching.

        :param filtered: dict[int -> str] - the filtered command output
        :return: dict[int -> dict[str -> str]] - the extracted data from the filtered output
        """
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

        extracted_data = {}
        for index, line in filtered.items():
            matching_extractors = [extractor for extractor in extractors if extractor['key_comparer'](index)]
            if len(matching_extractors) == 0:
                continue
            extractor = matching_extractors[-1]
            extracted_data[index] = extractor['data_extractor'](line)
        return extracted_data

    def _build_tray_data_function(self):
        tray = self.spec['tray']
        icon = tray['icon']
        icon = tray['info']
        # TODO


def test():
    # creation from new spec
    new_spec = Specification(json.loads(pathlib.Path('./specs/disk.json').read_text()))
    print(new_spec.execution_pipeline())

    # creation from stored spec
    stored_spec = Specification('disk')
    print(stored_spec.execution_pipeline())

    # rewrite first created specification
    new_spec = Specification(json.loads(pathlib.Path('./specs/disk.json').read_text()))
    print(new_spec.execution_pipeline())

    # user specifications
    specifications = Specification.load_user_specifications()
    print(specifications)


if __name__ == '__main__':
    test()
