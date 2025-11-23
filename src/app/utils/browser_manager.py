"""Browser Manager for SeleniumBase instances"""
from typing import Optional
from seleniumbase import SB


class BrowserManager:
    """Manages multiple SeleniumBase browser instances for parallel processing"""

    def __init__(self):
        self.browsers = []

    def create_browser(self, **kwargs):
        """Create a new browser instance and return its index"""
        sb_context = SB(**kwargs)
        sb = sb_context.__enter__()  # Manually enter the context
        self.browsers.append((sb_context, sb))
        return len(self.browsers) - 1

    def get(self, index: int):
        """Get browser by index"""
        return self.browsers[index][1]  # Return the actual SB instance

    def create_multiple(self, count: int, **kwargs):
        """Create multiple browsers at once"""
        indices = []
        for _ in range(count):
            indices.append(self.create_browser(**kwargs))
        return indices

    def close_all(self):
        """Close all browser instances"""
        for sb_context, sb in self.browsers:
            try:
                sb_context.__exit__(None, None, None)  # Properly exit the context
            except Exception as e:
                print(f"Error closing browser: {e}")
        self.browsers.clear()

    def __len__(self):
        """Return the number of browsers"""
        return len(self.browsers)
