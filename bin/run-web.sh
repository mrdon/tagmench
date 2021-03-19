#!/usr/bin/env sh

hypercorn tagmench.web:app -c file:/app/hypercorn_config.py