import os
import time


class CliBlock:
    os.system("")
    move_cursor_left = '\r'
    move_cursor_up = '\033[A'
    clear_line = '\033[K'

    def __init__(self, exit_delay=0):
        self.lines_printed = 0
        self.last_enter = False
        self.exit_delay = exit_delay

    def __enter__(self):
        return self

    def __exit__(self, *args):
        time.sleep(self.exit_delay)

        if not self.last_enter:
            print(f'{self.move_cursor_left}{self.clear_line}', end='', flush=True)

        for _ in range(self.lines_printed):
            print(f'{self.move_cursor_up}{self.clear_line}', end='', flush=True)

    def print(self, *args: str, **kwargs):
        message = kwargs.get('sep', ' ').join(args)
        self.lines_printed += message.count('\n')
        print(message, flush=True, **kwargs)

        if 'end' not in kwargs or kwargs['end'] == '\n':
            self.lines_printed += 1
            self.last_enter = True

    def input(self, prompt: str) -> str:
        self.lines_printed += prompt.count('\n')
        ans = input(prompt)
        self.lines_printed += 1
        self.last_enter = True
        return ans
