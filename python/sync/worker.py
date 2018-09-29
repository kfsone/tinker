from argparse import Namespace
from multiprocessing import Queue
from threading import Thread
from typing import Any, Callable, List, Union


class Worker(Thread):
    """
    Assembly-line threaded worker.

    Provides for the creation of a singly-linked list of worker threads that can take
    input at any point along the chain and potentially result in output from the
    final node in the chain.

    E.g you might pass URLs into a first worker that checks if the URL has already
    been processed. URLs that are unprocessed are forwarded to a second worker which
    fetches the urls and forwards the content to a final worker. The final worker
    scans the content for a keyword and puts some information into the final
    or 'out' queue for the owner to retrieve.
    """

    TERMINATOR = "terminal"
    """ Used internally to notify a worker that it's being shut down. """

    Callback = Callable[[Namespace, Any, Any, Queue], None]


    def __init__(
            self,
            args:       Namespace,
            callback:   Callback,
            client:     Any,
            next_queue: Queue,
            logger
            ):
        super(Worker, self).__init__()
        #if use_sftp:
        #    self._client = SFTPSession(args.host, args.username, args.password, initial_path=args.remote, logger=logger)
        #else:
        #    self._client = SSHSession(args.host, args.username, args.password, logger=logger)

        self._queue    = Queue()
        self._args     = args
        self._callback = callback
        self._client   = client
        self._next     = next_queue
        self._logger   = logger


    def put(self, thing: Any):
        return self._queue.put(thing)


    def get(self, thing: Any) -> Any:
        if self._next is not None:
            raise RuntimeError("Cannot 'get' from any worker but the last in a chain")
        return self._queue.get(thing)


    def run(self):
        qget   = self._queue.get
        oper   = self._callback
        nextq  = self._next
        client = self._client

        terminator = self.TERMINATOR

        try:
            while True:
                data = qget()
                if data == terminator:
                    break
                oper(self._args, client, data, nextq)
        finally:

            # Terminator received; forward.
            if nextq:
                nextq.put(terminator)

            if client:
                client.close()   


    def close(self):
        self._queue.put(self.TERMINATOR)
        self.join()


