# pip import zeroconf.
from collections import defaultdict
from time import sleep
from zeroconf import Zeroconf, ServiceBrowser, ZeroconfServiceTypes
from json import dumps

verbose = False


def note(op, svctype, name):
    if verbose:
        print("{} {} ({})".format(op, svctype, name))


class Listener(object):

    def __init__(self):
        self.zeroconf = Zeroconf()
        self.services = defaultdict(dict)
        self.servers  = {}


    def add_service(self, zeroconf, svctype, name):
        svcinfo = self.zeroconf.get_service_info(svctype, name)
        self.services[svctype][name] = svcinfo
        self.servers[name] = svctype
        note("+", svctype, name)


    def remove_service(self, zeroconf, svctype, name):
        self.services[svctype][name] = None
        note("-", svctype, name)


if __name__ == '__main__':

    zc = Zeroconf()
    listener = Listener()

    print("Detecting services...")
    services = ZeroconfServiceTypes.find(zc)
    print("{}: {}".format(len(services), ', '.join(services)))

    print("Detecting hosts...")
    for service in services:
        browser = ServiceBrowser(zc, service, listener)
    sleep(3)
    print("Found {}".format(len(listener.servers)))

    print()

    def escape(s):
        return s.decode().encode('unicode_escape').decode()

    with open("services.csv", "w") as fh:
        for service in services:
            fh.write(service + "\n")
            servers = listener.services[service]
            print("-- {} {} services".format(len(servers), service))
            for server, info in servers.items():
                props = info.properties
                if isinstance(props, dict):
                    props = dumps({escape(k): escape(v) if isinstance(v, bytes) else v for k, v in props.items()})
                else:
                    props = escape(props)
                print(" | {name} :{port} {serv}".format(
                        name=info.get_name(),
                        port=info.port,
                        serv=info.server,
                ))
                fh.write("{name},{port},\"{serv}\",\"{text}\"\n".format(
                        name=info.get_name(),
                        port=info.port,
                        serv=info.server,
                        text=escape(info.text)
                ))

