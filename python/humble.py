# Copyright (C) 2017 Oliver "kfsone" Smith <oliver@kfs.org>
# Provided under The MIT License -- see LICENSE.

from __future__ import absolute_import
from __future__ import with_statement
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from restful import RESTful


class ButtonNotPressedError(Exception):
    """
    Raised when app is not authorized to register because the button
    has not been pressed on the hub.
    """

    pass


class BridgeAPI(RESTful):

    DEFAULT_PREFIX = "/api"

    def __init__(self, device_name, address, protocol=None, prefix=None, username=None):
        """
        Create a BridgeAPI instance.

        \param    device_name     How to identify ourselves to the hub,
        \param    address         DNS name or IP address of the hub,
        \param    protocol        [opt] Which protocol (http or https) to use,
        \param    prefix          [opt] Top-level URL (should be "/api"),
        \param    username        [opt] Authorization saved from previous instance,
        """

        super(BridgeAPI, self).__init__(address, protocol=protocol, prefix=prefix)

        if not device_name:
            raise ValueError("No device_name specified for register (call your app something).")

        self._device_name = device_name
        self._username = username


    def connect(self, username=None):
        """
        Get authorization from the hub to talk to it.
        \param   username    [optional] Credential from a previous session.
        """

        if username:
            self._username = username
            return

        # If we already have a username, do nothing.
        if self._username is not None:
            return

        # Request /api with device_type={device_name}
        result = self.query("", body={"device_type": self._device_name})
        error = result.get("error")
        if error:
            if error["type"] == 101:
                # User has not pressed the button on the hub first, try again.
                raise ButtonNotPressedError(error["description"])
            raise Exception("Error from hub during registration: " + str(error))

        success = result["success"]
        self._username = success["username"]

    # query and update simply fall thru.

