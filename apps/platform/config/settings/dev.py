from .base import *  # noqa

DEBUG = True

# Inherit CELERY_TASK_ALWAYS_EAGER from env/base (default False).
# Set CELERY_TASK_ALWAYS_EAGER=1 locally only when you are not running Redis/worker.
