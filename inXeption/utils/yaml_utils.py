'''
YAML utilities for consistent formatting across the project

CRITICAL: Thread Safety Notes
----------------------------
The ruamel.yaml YAML instance maintains internal state during serialization.
This can lead to race conditions if the same instance is used from multiple
threads simultaneously. We encountered this when:
1. Agent thread was serializing a Matrix response
2. Terminal thread tried to log a trigger event
3. Both used the same global YAML instance
4. This corrupted the emitter's state, leading to DocumentStartEvent/NodeEvent errors

For this reason, dump_str() creates a fresh YAML instance for each dump operation
rather than using a shared instance.
'''

import os
from enum import Enum
from io import StringIO

from ruamel.yaml import YAML


def setup_yaml():
    '''Configure YAML formatter for nice output'''
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.default_flow_style = False

    def my_string_representer(dumper, data):
        is_multiline = '\n' in data
        return dumper.represent_scalar(
            'tag:yaml.org,2002:str',
            data.strip() if is_multiline else data,
            style='|' if is_multiline else None,
        )

    def enum_representer(dumper, data):
        '''Handle Enum values by returning their string value'''
        return dumper.represent_scalar('tag:yaml.org,2002:str', data.value)

    yaml.Representer.add_representer(str, my_string_representer)
    yaml.Representer.add_multi_representer(Enum, enum_representer)
    return yaml


# YAML loading helper (using fresh instance each time for thread safety)
def load_str(data):
    '''Load YAML string with proper formatting'''
    return setup_yaml().load(data)


def dump_str(data):
    '''Dump YAML data to string with proper formatting'''
    yaml = setup_yaml()  # Fresh instance per dump operation
    return (lambda s: yaml.dump(data, s) or s.getvalue())(StringIO())


def from_yaml_file(file_path):
    '''Load YAML data from a file with proper formatting'''
    file_path = os.fspath(file_path)  # Convert Path object to str if necessary
    with open(file_path) as f:
        return setup_yaml().load(f)
