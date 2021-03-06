# Copyright (C) 2017 Oliver "kfsone" Smith <oliver@kfs.org>
# Provided under The MIT License -- see LICENSE.

from __future__ import absolute_import
from __future__ import with_statement
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import requests

from utilities import join_uri_paths


"""
A simple wrapper for a RESTful api, which returns the parsed json response
as an object.

Example:

  # Request the post with id #1 and the comments for it at
  # jsonplaceholder.typicode.com

  api = RESTful("jsonplaceholder.typicode.com", protocol="https")

  # Get a list of posts as dictionaries ( [{...},...] )
  posts = api.query("/posts")

  # Get post id #1 as a dictionary of properties ( {'body':..., ...})
  post = api.query("/posts/1")

  # Get the comments on post #1 as a list of dictionaries.
  cmts = api.query("/posts/1/comments")  # => ditto

  # Simulate posting our own post.
  post = api.query("/posts", body={"userId":123, "title":"Test Post",
          "body":"This is a test, just a test."})

For some interfaces you will need to use 'put' rather than 'post', in which
case there is an "update" rather than "query" member:

  post = api.update("/posts", body={"userId":123, "title":"Test Post"})


You can use "prefix" to create API-zoned objects:

  class PostsAPI(RESTful):
    DEFAULT_PROTOCOL = "https"
    DEFAULT_PREFIX   = "/posts"

  posts = PostsAPI("jsonplaceholder.typicode.com")
  posts.query()  # Returns list of posts
  posts.query("1")  # Returns /posts/1  =>  dictionary of post 1 properties
"""

###############################################################################
#
class RESTful(object):

    DEFAULT_PREFIX   = "/"
    DEFAULT_PROTOCOL = "http"

    FETCH  = requests.get
    CREATE = requests.post
    UPDATE = requests.put


    ###########################################################################
    # Constructor.
    #
    def __init__(self, address, protocol=None, prefix=None):
        """
            Construct a restful API instance to the given address,
            assuming the API base is "http://{address}/" by default.

            \param   address    The name or IP of the service,
            \param   protocol   [optional] Protocol to speak (default=http),
            \param   prefix     [optional] Top-level of the API (default=/),
        """

        if protocol is None:
            protocol = self.DEFAULT_PROTOCOL
        if prefix is None:
            prefix = self.DEFAULT_PREFIX

        self._base_url = "%s://%s" % (protocol, address)
        self._prefix   = prefix


    ###########################################################################
    # Helper to translate sub-paths into complete paths with a protocol.
    #
    def _get_request_path(self, query_path):
        """
        Internal helper than translates a query path into a request path.

        \param   query_path       The path the user is providing,
        \return                   The complete path to request.
        """

        if not query_path:
            request_path = self._prefix

        elif not self._prefix or query_path.startswith(self._prefix):
            # When there's no prefix or the incoming path included it,
            # just use the query path.
            request_path = query_path

        elif query_path.startswith("./"):
            # If prefix="/api/" and you want "/api/api/foo", use "./api/foo"
            # or "/api/api/foo".
            request_path = join_uri_paths(self._prefix, query_path[2:])

        else:
            # Otherwise, we inject the prefix.
            request_path = join_uri_paths(self._prefix, query_path)

        # Introduce the protocol and address.
        return join_uri_paths(self._base_url, request_path)


    ###########################################################################
    # Make an actual query.
    #
    def query(self, query_path=None, body=None):
        """
        Send a query within the API using GET or, if the optional body is
        provided, via POST. The body can either be a list or dictionary to be
        sent as JSON, anything else will be sent as-is as the 'data' field of
        the post.

        If you are using an API which requests you to use "PUT" you should use
        the 'update' method instead.

        `prefix` is automatically added unless the query_path includes it,
        e.g., given r = RESTful("host", prefix="/api/")
            r.query("/foo")
            r.query("/api/foo")
        are equivalent. Use "./" to avoid this, e.g.
            r.query("./api/foo") => /api/api/foo

        \param   query_path     The prefix-relative path to the query,
        \param   body           a: dict{ parameters },
                                b: string representation of data to be sent,
        \return                 JSON representation of the response,
        """

        # Translate the query path to a request
        request = self._get_request_path(query_path)

        # If body is None, just use get:
        if body is None:
            response = self.FETCH(request)

        # If we're given a dictionary or list, automatically convert it to a
        # JSON representation.
        elif isinstance(body, (dict, list, tuple)):
            response = self.CREATE(request, json=body)

        else:
            response = self.CREATE(request, data=body)

        return response.json()


    ###########################################################################
    # Perform a "put" operation to update existing data.
    #
    def update(self, query_path=None, body=None):
        """
        Like 'query' but uses 'put' as the transport method.
        """

        request = self._get_request_path(query_path)

        if not body or isinstance(body, (dict, list, tuple)):
            response = self.UPDATE(request, json=body)
        else:
            response = self.UPDATE(request, data=body)

        return response.json()
