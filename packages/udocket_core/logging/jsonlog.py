import json, sys, datetime

def log(event: str, **kwargs):
    payload = {"ts": datetime.datetime.utcnow().isoformat()+"Z", "event": event}
    payload.update(kwargs)
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()