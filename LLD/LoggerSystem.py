import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import os
import concurrent.futures

"""
==============================================================================================
LOGGING FRAMEWORK LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Requirements:
1. Support Log Levels (DEBUG, INFO, WARNING, ERROR, FATAL).
2. Log Format: Timestamp + Level + Message.
3. Multiple Destinations: Console, File, Database (Simulated).
4. Configuration: Set minimum log level and add destinations.
5. Thread Safety: Handles concurrent logging via locks and concurrent.futures.
6. Extensibility: Interface-based appenders.

Design Patterns:
1. Singleton: For the central 'Logger' instance.
2. Observer / Strategy: 'LogAppender' interface for multiple output destinations.
3. Chain of Responsibility: (Optional) Can be used for level-based filtering, 
   but here handled via configuration.
"""

# ==========================================
# Enums & Models
# ==========================================

class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    FATAL = 5

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

class LogMessage:
    """Encapsulates the data for a single log entry."""
    def __init__(self, level: LogLevel, content: str):
        self.level = level
        self.content = content
        self.timestamp = datetime.now()

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [{self.level.name}] {self.content}"

# ==========================================
# Appenders (Observer / Strategy)
# ==========================================

class LogAppender(ABC):
    """Abstract base class for all log output destinations."""
    @abstractmethod
    def append(self, message: LogMessage):
        pass

class ConsoleAppender(LogAppender):
    """Appender for standard console output."""
    def append(self, message: LogMessage):
        print(f"CONSOLE: {message}")

class FileAppender(LogAppender):
    """Thread-safe appender for writing logs to a file."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = threading.Lock()

    def append(self, message: LogMessage):
        with self._lock:
            try:
                with open(self.file_path, "a") as f:
                    f.write(str(message) + "\n")
            except IOError as e:
                print(f"Failed to write to log file: {e}")

class DatabaseAppender(LogAppender):
    """Simulated appender for database logging."""
    def __init__(self, db_url: str):
        self.db_url = db_url

    def append(self, message: LogMessage):
        # Simulated DB Insertion
        print(f"DB ({self.db_url}): INSERT INTO logs VALUES ('{message.level.name}', '{message.content}')")

# ==========================================
# Configuration
# ==========================================

class LoggerConfig:
    """Holds the configuration state for the logger."""
    def __init__(self):
        self.min_level = LogLevel.INFO
        self.appenders: List[LogAppender] = []
        self._lock = threading.Lock()

    def set_level(self, level: LogLevel):
        with self._lock:
            self.min_level = level

    def add_appender(self, appender: LogAppender):
        with self._lock:
            self.appenders.append(appender)

# ==========================================
# Logger (Singleton)
# ==========================================

class CustomLogger:
    """Central access point for logging (Singleton)."""
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(CustomLogger, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.config = LoggerConfig()
        self._initialized = True

    @classmethod
    def get_instance(cls):
        return cls()

    def log(self, level: LogLevel, message_text: str):
        """Dispatches log message to all configured appenders if level meets requirement."""
        if level >= self.config.min_level:
            log_data = LogMessage(level, message_text)
            # Parallel execution of appenders or simple iteration?
            # Thread-safety is key within appenders.
            for appender in self.config.appenders:
                appender.append(log_data)

    # Convenience methods
    def debug(self, msg: str): self.log(LogLevel.DEBUG, msg)
    def info(self, msg: str): self.log(LogLevel.INFO, msg)
    def warning(self, msg: str): self.log(LogLevel.WARNING, msg)
    def error(self, msg: str): self.log(LogLevel.ERROR, msg)
    def fatal(self, msg: str): self.log(LogLevel.FATAL, msg)

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Custom Logging Framework Demo ---")

    logger = CustomLogger.get_instance()

    # 1. Configuration
    logger.config.set_level(LogLevel.DEBUG)
    logger.config.add_appender(ConsoleAppender())
    
    log_file = "app_logs.txt"
    if os.path.exists(log_file):
        os.remove(log_file)
    logger.config.add_appender(FileAppender(log_file))

    # 2. Simple Logging
    logger.info("Application starting...")
    logger.debug("Debugging mode active.")

    # 3. Dynamic Config Change
    logger.config.set_level(LogLevel.WARNING)
    logger.info("This info message should NOT be printed or logged.")
    logger.error("A simulated database error occurred.")

    # 4. Multi-threaded Logging Simulation
    print("\n--- Starting Concurrent Logging Demo ---")
    
    def worker(thread_name: str):
        for i in range(3):
            logger.warning(f"Message {i} from {thread_name}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        threads = [f"Thread-{j}" for j in range(5)]
        executor.map(worker, threads)

    # 5. Verify File Content
    print("\n--- Verifying File Logs ---")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            print(f.read())
