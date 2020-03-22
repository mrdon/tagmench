#!/usr/bin/env sh

hypercorn tagmench.web:app -c python:/app/hypercorn_config.py