from timestamp import get_iso_timestamp
from log_helper import LogHandler, LogFormatter


class PrintHistory:
    """
    A class that stores recent log messages.
    """

    def __init__(self, max_size=20):
        self.history = []  # List to store the log messages
        self.max_size = max_size  # Maximum size of the history

    def add(self, message):
        """
        Add a message to the history, keeping the size within the max_size.
        """
        if len(self.history) >= self.max_size:
            self.history.pop(0)
        self.history.append((message, get_iso_timestamp()))

    def get_history(self):
        return self.history


class PrintHistoryLogHandler(LogHandler):
    """
    Custom logging handler that adds log messages to PrintHistory.
    """

    def __init__(self, print_history_instance):
        super().__init__(LogFormatter("{level}: [{name}] {message}"))
        self.print_history_instance = print_history_instance

    def emit(self, record):
        # Format the log message
        log_entry = self.formatter.format(record)
        # Add the formatted log message to the PrintHistory instance
        self.print_history_instance.add(log_entry)
