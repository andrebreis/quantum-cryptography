import os

from configobj import ConfigObj
from validate import Validator

FILENAME = 'qkd.conf'
SPEC_FILENAME = 'qkd.spec'


class Config(object):
    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        if not os.path.exists(os.path.join(dir_path, FILENAME)):
            print(os.path.join(dir_path, SPEC_FILENAME))
            self.config = ConfigObj(configspec=os.path.join(dir_path, SPEC_FILENAME))
        else:
            self.config = ConfigObj(os.path.join(dir_path, FILENAME), configspec=os.path.join(dir_path, SPEC_FILENAME))

        validator = Validator()
        self.config.validate(validator)
        self.write()

    def write(self):
        """
        Write the configuration to the config file in the state dir as specified in the config.
        """
        self.config.filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), FILENAME)
        self.config.write()

    def get_correctness_param(self):
        return self.config['params']['correctness']

    def get_security_param(self):
        return self.config['params']['security']
