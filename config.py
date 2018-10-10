"""
Stores common configuration information.
"""
import appdirs
import os


APPLICATION_NAME = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
"""
The application name.
"""

USER_DATA_PATH = appdirs.user_data_dir(APPLICATION_NAME)
"""
The Available folder to store user data information.
"""

# Ensure the USER_DATA_PATH is available
if not os.path.exists(USER_DATA_PATH):
    os.makedirs(USER_DATA_PATH, exist_ok=True)
elif not os.path.isdir(USER_DATA_PATH):
    os.remove(USER_DATA_PATH)
    os.makedirs(USER_DATA_PATH, exist_ok=True)
