#!/usr/bin/env python
"""Server for handling interaction between clients and bot."""

import sys
import os
from inspect import getmembers, ismethod

try:
    import zmq
except ImportError:
    sys.stderr.write("ERROR: Failed to import zmq. Is it installed?")
    raise

new_path = [os.path.join(os.path.abspath(os.path.dirname(__file__)), "..")]
sys.path = new_path + sys.path

import lib.lib as lib


class Server(object):

    """Listen for client commands and make them happen on the bot."""

    handler_prefix = "handle_"

    def __init__(self):
        """Build all main bot objects, set ZMQ to listen."""
        # Load configuration and logger
        self.config = lib.load_config()
        self.logger = lib.get_logger()

        # Create cmd -> handler methods mapping (dict)
        self.handlers = dict()
        for name, method in getmembers(self, ismethod):
            if name.startswith(self.handler_prefix):
                cmd = name.replace(self.handler_prefix, "", 1)
                self.handlers[cmd] = method
        self.logger.info("{} handlers registered".format(len(self.handlers)))

    def on_message(self, msg):
        """Confirm message format and take appropriate action.

        :param msg: Message received by ZMQ socket.
        :type msg: dict
        :returns: A dict with reply from a handler or error message.

        """
        try:
            cmd = msg["cmd"]
            assert type(cmd) is str
        except ValueError:
            return self.build_reply("Error",
                                    msg="Unable to convert message to dict")
        except KeyError:
            return self.build_reply("Error", msg="No 'cmd' key given")
        except AssertionError:
            return self.build_reply("Error", msg="Key 'cmd' is not a string")

        if "opts" in msg.keys():
            opts = msg["opts"]
            try:
                assert type(opts) is dict
            except AssertionError:
                return self.build_reply("Error", msg="Key 'opts' not a dict")
        else:
            opts = None

        # Use cmd -> handlers mapping for better performance
        try:
            return self.handlers[cmd](opts)
        except KeyError as e:
            error_msg = "Unknown cmd: {}".format(cmd)
            return self.build_reply("Error", msg=error_msg)

    def build_reply(self, status, result=None, msg=None):
        """Helper function for building standard replies.

        :param status: Exit status code ("Error"/"Success").
        :param result: Optional details of result (eg current speed).
        :param msg: Optional message (eg "Not implemented").
        :returns: A dict with status, result and msg.

        """
        if status != "Success" and status != "Error":
            self.logger.warn("Status is typically 'Success' or 'Error'")

        reply_msg = {}
        reply_msg["status"] = status
        if result is not None:
            reply_msg["result"] = result
        if msg is not None:
            reply_msg["msg"] = msg
        return reply_msg
