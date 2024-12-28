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


class LogFormatter:
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


class LogHandler:
    """
    Base class for all log handlers.
    """

    def __init__(self, formatter=None):
        self.formatter = formatter or LogFormatter()

    def setFormatter(self, formatter):
        self.formatter = formatter

    def emit(self, record):
        """
        Processes a log record.
        Should be overridden by subclasses.
        """
        raise NotImplementedError("LogHandler subclasses must implement 'emit' method")


class LogHandlerConsole(LogHandler):
    """
    A log handler that outputs log records to the console.
    """

    def emit(self, record):
        log_entry = self.formatter.format(record)
        print(log_entry)


class LogHandlerFile(LogHandler):
    """
    A log handler that writes log records to a specified log file.
    """

    def __init__(self, log_file, formatter=None):
        super().__init__(formatter)
        self.log_file = log_file

    def emit(self, record):
        log_entry = self.formatter.format(record)
        try:
            with open(self.log_file, 'a') as file:
                file.write(log_entry + '\n')
        except Exception as e:
            print(f"Failed to write log to {self.log_file}: {e}")


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
        self.level = self.LEVELS.get(level.upper(), 20)

    def addHandler(self, handler):
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