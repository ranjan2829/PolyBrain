import time
from typing import Callable, Optional
from threading import Thread


class HourlyScheduler:
    def __init__(self, task: Callable, interval_seconds: int = 3600):
        self.task = task
        self.interval = interval_seconds
        self.running = False
        self.thread: Optional[Thread] = None
    
    def _run(self):
        while self.running:
            try:
                self.task()
            except Exception as e:
                print(f"Scheduler task error: {e}")
            
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def start(self):
        if self.running:
            return
        
        self.running = True
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
