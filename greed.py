import time
import select
import sys

class Greed:
    def __init__(self):
        self.blinking = True
        self.last_time = time.time()
        self.blink_interval = 0.5  # Change this to set blinking speed

    def blink(self):
        while self.blinking:
            current_time = time.time()
            if current_time - self.last_time >= self.blink_interval:
                self.last_time = current_time
                print("Blink")  # Replace with actual blinking code

    def non_blocking_input(self):
        inputs = [sys.stdin]
        timeout = 1  # Set timeout for select
        while True:
            readable, _, _ = select.select(inputs, [], [], timeout)
            for s in readable:
                user_input = s.read(1)
                if user_input:
                    print(f'Input received: {user_input}')
                    return
            self.blink()  # Call the blink method

if __name__ == '__main__':
    greed = Greed()
    greed.non_blocking_input()