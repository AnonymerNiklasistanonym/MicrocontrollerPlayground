from timestamp import get_iso_timestamp


class LogRecord:
    """
    Represents a single log record.
    """

    def __init__(self, level, message, name):
        self.level = level
        self.message = message
        self.name = name
        self.timestamp = get_iso_timestamp()


class Formatter:
    """
    Formats log records into strings.
    """

    def __init__(self, fmt=None):
        self.fmt = fmt or "{timestamp} - {level} - {name} - {message}"

    def format(self, record):
        return self.fmt.format(
            timestamp=record.timestamp,
            level=record.level,
            name=record.name,
            message=record.message,
        )


class Handler:
    """
    Base class for all handlers.
    """

    def __init__(self, formatter=None):
        self.formatter = formatter or Formatter()

    def setFormatter(self, formatter):
        self.formatter = formatter

    def emit(self, record):
        """
        Processes a log record.
        Should be overridden by subclasses.
        """
        raise NotImplementedError("Handler subclasses must implement 'emit' method")


class ConsoleHandler(Handler):
    """
    A handler that outputs log records to the console.
    """

    def emit(self, record):
        log_entry = self.formatter.format(record)
        print(log_entry)


class Logger:
    """
    A lightweight logger for MicroPython with handler support.
    """

    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    def __init__(self, name, level="INFO"):
        self.name = name
        self.level = self.LEVELS.get(level.upper(), 20)
        self.handlers = []

    def setLevel(self, level):
        """
        Set the logging level.
        """
        self.level = self.LEVELS.get(level.upper(), 20)

    def addHandler(self, handler):
        """
        Add a logging handler.
        """
        self.handlers.append(handler)

    def log(self, level, *args):
        """
        Log a message if it meets the logging level.
        Concatenates all arguments into a single message string.
        """
        if self.LEVELS[level] >= self.level:
            message = " ".join(str(arg) for arg in args)
            record = LogRecord(level, message, self.name)
            for handler in self.handlers:
                handler.emit(record)

    def debug(self, *args):
        self.log("DEBUG", *args)

    def info(self, *args):
        self.log("INFO", *args)

    def warning(self, *args):
        self.log("WARNING", *args)

    def error(self, *args):
        self.log("ERROR", *args)

    def critical(self, *args):
        self.log("CRITICAL", *args)


class PrintHistory:
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
        """
        Get the full history of stored messages.
        """
        return self.history


class PrintHistoryLoggingHandler(Handler):
    """
    Custom logging handler that adds log messages to PrintHistory.
    """

    def __init__(self, print_history_instance):
        super().__init__()
        self.print_history_instance = print_history_instance

    def emit(self, record):
        # Format the log message
        log_entry = self.formatter.format(record)
        # Add the formatted log message to the PrintHistory instance
        self.print_history_instance.add(log_entry)
        # Also print it to the console
        print(log_entry)
