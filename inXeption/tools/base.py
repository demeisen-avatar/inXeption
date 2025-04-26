from abc import ABCMeta, abstractmethod

from inXeption.utils.yaml_utils import load_str


class BaseTool(metaclass=ABCMeta):
    '''
    Base class for all tools with standardized result structure

    Tools maintain state across invocations within an interaction but
    return fresh result dictionaries for each invocation.
    '''

    # Each tool should define its YAML schema as a class variable
    yaml = None

    def __init__(self):
        self.name = load_str(self.yaml)['name']

    @abstractmethod
    async def __call__(self, **kwargs):
        '''
        Tools implement this to execute and return a result dictionary

        Returns:
            dict: Result dictionary with rendering information
        '''

    @abstractmethod
    async def cleanup(self):
        '''
        Clean up any resources used by the tool
        '''


class ToolError(Exception):
    '''
    Exception for expected tool errors
    '''

    def __init__(self, message):
        self.message = message
