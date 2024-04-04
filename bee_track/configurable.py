import multiprocessing.sharedctypes


class Configurable:
    """
    A configurable worker that runs in a separate process.

    # TODO rename Worker
    """

    def __init__(self, message_queue: Queue):
        self.config_queue = multiprocessing.Queue()
        self.config_thread = threading.Thread(target=self.config_worker).start()
        self.message_queue = message_queue

    def worker(self):
        # Implement the worker code
        # TODO rename Worker.__call__() or Worker.run()
        raise NotImplementedError

    def config_worker(self):
        """
        this method is a worker that waits for the config queue
        """
        # TODO what is happening here?
        # TODO refactor into separate set, get, put commands
        while True:
            command = self.config_queue.get()

            if command[0] == 'get':
                if len(command) != 2:
                    self.message_queue.put("Wrong number of items in get call")
                    continue
            if command[0] == 'set':
                if len(command) != 3:
                    self.message_queue.put("Wrong number of items in set call")
                    continue
            if (command[0] != 'get') and (command[0] != 'set'):
                self.message_queue.put("Use set or get")
                continue
            if not hasattr(self, command[1]):
                print(self.index)
                self.message_queue.put("%s not available in this class." % command[1])
                continue

            att = getattr(self, command[1])
            if isinstance(att, multiprocessing.sharedctypes.Synchronized):
                v = att.value
            else:
                v = att
            if command[0] == 'get':
                self.message_queue.put("Value of %s is %s" % (command[1], v))
                continue
            if command[0] == 'set':
                try:
                    if isinstance(att, sharedctypes.Synchronized):
                        getattr(self, command[1]).value = type(v)(command[2])
                    else:
                        setattr(self, command[1], type(v)(command[2]))

                    self.message_queue.put("Set %s to %s" % (command[1], command[2]))

                except Exception as e:
                    self.message_queue.put("Failed to set:" + str(e))
