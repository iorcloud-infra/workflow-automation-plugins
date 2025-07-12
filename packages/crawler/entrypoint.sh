#!/bin/bash

uv run alembic upgrade head
uv run fastapi run --host 0.0.0.0 --port $PORT main.py