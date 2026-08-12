live_logs = []


def add_live_log(message):

    live_logs.append(message)

    if len(live_logs) > 1000:
        live_logs.pop(0)