r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Dies Irae"

TELNET_PORTS = [4201]  # Change 4000 to your desired telnet port
WEBSERVER_PORTS = [(4200, 4005)]  # Change 8000 to your desired webserver port
WEBSOCKET_CLIENT_PORT = 4202

SERVERNAME = "beta.diesiraemu.com"
TELNET_INTERFACES = ['0.0.0.0']
WEBSERVER_INTERFACES = ['0.0.0.0']

ALLOWED_HOSTS = ['beta.diesiraemu.com', 'localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = ['https://beta.diesiraemu.com', 'http://beta.diesiraemu.com']

INSTALLED_APPS += ["world.wod20th"]  # Add your app to the list of installed apps
BASE_ROOM_TYPECLASS = "typeclasses.rooms.RoomParent"
  # Change 8001 to your desired websocket port
######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
