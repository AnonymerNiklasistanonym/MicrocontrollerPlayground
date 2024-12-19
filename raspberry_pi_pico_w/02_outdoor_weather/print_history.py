from timestamp import get_iso_timestamp


class PrintHistory:
    def __init__(self, max_size=20):
        self.history = []  # List to store the print statements
        self.max_size = max_size  # Maximum size of the history

    def add(self, message):
        if len(self.history) >= self.max_size:
            self.history.pop(0)
        self.history.append((message, get_iso_timestamp()))

    def get_history(self):
        return self.history
