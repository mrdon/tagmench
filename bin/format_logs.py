#!/bin/python3
# Copied from https://bitbucket.org/mrdon/tb/src/master/plugins/devloop/util.py
from __future__ import print_function

import io
import json
import re
import sys
from contextlib import contextmanager
from contextlib import redirect_stdout
from datetime import datetime
from functools import partial

import dateutil.parser
from blessings import Terminal

HAS_JSON = re.compile(r'^(.*?)(\{.*"@?time(?:stamp)?".*\})')
LOCAL_LINE = re.compile(r"(.*) (DEBUG|INFO|WARN|ERROR|FATAL)\s+\[(.*)\] (.*)")

colors = Terminal()


@contextmanager
def redirected_stdout():
    f = io.StringIO()
    stdout = sys.stdout
    f.write = partial(print_local_line, stdout=stdout)
    with redirect_stdout(f):
        yield


def print_local_line(line, stdout=sys.stdout):
    line = line.strip()

    # Looks for json inside a docker_compose line
    m = HAS_JSON.match(line)
    if m:
        prefix = m.group(1)
        line = m.group(2)
        print(prefix, end="", file=stdout)
        print_json_lines([line], stdout=stdout)
        return

    m = LOCAL_LINE.search(line)
    if m:
        c = level_to_color(m.group(2))
        ansi_line = "{} {} [{}] {}".format(
            m.group(1), c(m.group(2)), c(m.group(3)), c(m.group(4))
        )
        print(ansi_line, file=stdout)
    else:
        print("{}".format(line), file=stdout)


def print_json_line(ts, data, min_level="debug", stdout=sys.stdout):
    trace_id = data.get("traceId", data.get("request_id", data.get("dd.trace_id", "")))
    msg = data.get("message", "")
    if isinstance(msg, dict):
        msg = json.dumps(msg)
    else:
        msg = msg  # .encode('utf8')
    level = data.get("level", "INFO")
    min_level = min_level.upper()
    if min_level == "ERROR" and level in ("DEBUG", "INFO", "WARN"):
        return
    elif min_level == "WARN" and level in ("DEBUG", "INFO"):
        return
    elif min_level == "INFO" and level == "DEBUG":
        return

    role = data.get("m", {}).get("g", "?")
    container = data.get("container", "?")
    color = None
    if msg.startswith("=====> New request"):
        color = colors.blue
    if msg.startswith("=====> Request complete"):
        color = colors.blue
    if color is None:
        color = level_to_color(level)
    try:
        ansi_line = format_line(
            role="{}:{}".format(role, container),
            instance=data.get("ec2", {}).get("id", "?"),
            time=ts,
            level=color(colors.bold(level)),
            msg=color(msg),
            trace=trace_id,
            color=color,
            stacktrace=data.get("stack_trace", data.get("exc_info", "")),
        )
        print(ansi_line, file=stdout)
    except Exception as e:
        print("err: {}".format(e), file=stdout)
        print(data, file=stdout)


def print_json_lines(line_iterator, tag=None, min_level="debug", stdout=sys.stdout):
    for line in line_iterator:
        data = line_to_json(line, stdout=stdout)
        if not data:
            continue

        if tag and data.get("m", {}).get("t", "") != tag:
            continue

        print_json_line(
            data.get("timestamp", data.get("@timestamp", data.get("time"))),
            data,
            min_level=min_level,
            stdout=stdout,
        )


def line_to_json(line, stdout=sys.stdout):
    line = line.strip()
    if not line:
        return

    try:
        return json.loads(line)
    except Exception:
        print(line, file=stdout)


def format_line(role, instance, time, level, msg, trace, color, stacktrace):
    if time is not None:
        if not isinstance(time, datetime):
            time = dateutil.parser.parse(time)
        time = time.strftime("%H:%M:%S.%f")[:-3]
    return "{time} {t.magenta}[{role}:{instance}] ({trace}) {level} {msg}{stacktrace}".format(
        t=colors,
        instance=instance,
        role=role,
        time=colors.green(time),
        level=color(colors.bold(level)),
        msg=color(msg),
        trace=trace,
        color=color,
        stacktrace="" if not stacktrace else "\n{}".format(colors.bold_red(stacktrace)),
    )


def level_to_color(level):
    if level == "DEBUG":
        color = colors.dim_white_on_black
    elif level == "INFO":
        color = _add_colors
    elif level == "WARN" or "WARNING":
        color = colors.yellow_on_black
    elif level == "ERROR":
        color = colors.red
    elif level == "FATAL":
        color = colors.white_on_red
    else:
        color = _add_colors
    return color


def _add_colors(c):
    return colors.normal + c + colors.normal


if __name__ == "__main__":
    try:
        for line in sys.stdin:
            print_local_line(line)
    except KeyboardInterrupt:
        pass
