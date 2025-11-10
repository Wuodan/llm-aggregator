import threading
import time
from collections import deque

import psutil

stats_history = deque(maxlen=60)  # 60 samples = 1 sample/sec for a minute

def stats_collector():
    while True:
        stats_history.append(psutil.virtual_memory().percent)
        time.sleep(5)

threading.Thread(target=stats_collector, daemon=True).start()
