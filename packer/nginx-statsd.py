#!/usr/bin/env python3

import sys
import re
import statsd

c = statsd.StatsClient('localhost', 8125)

parts = [
    r'(?P<remote_address>\S+)',         # host %h
    r'\S+',                             # indent %l (unused)
    r'(?P<user>\S+)',                   # user %u
    r'\[(?P<time>.+)\]',                # time %t
    r'"(?P<request>.*)"',               # request "%r"
    r'(?P<status>[0-9]+)',              # status %>s
    r'(?P<size>[0-9.]+|-)',             # size %b (careful, can be '-')
    r'(?P<request_length>[0-9.]+)',     # request size in bytes
    r'(?P<request_latency>[0-9.]+)',    # request latency in seconds (float)
    r'"(?P<referrer>\S+|-)"',           # referrer "%{Referer}i"
    r'"(?P<agent>.*)"',                 # user agent "%{User-agent}i"
]
pattern = re.compile(r'\s+'.join(parts)+r'\s*\Z')

for line in sys.stdin:
    m = pattern.match(line)
    if m:
        method, path, proto = m.groupdict()['request'].split(' ')
        if path != '/':
            path = '/'.join(path.split('?')[0].split('/')[:2])
        c.timing('.'.join(['host', 'nginx', path, method, m.groupdict()['status']]), float(m.groupdict()['request_latency'])*1000)