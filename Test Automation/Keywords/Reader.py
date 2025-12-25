import configparser
import os

CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "Configurations", "configurations.ini")
)

def get_value(section, key):
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)

    print("INI Loaded From:", CONFIG_PATH)
    print("Sections Found:", config.sections())

    return config[section][key]