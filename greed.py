import sys
import select
import time

# Constants for display refresh timing
REFRESH_INTERVAL = 0.1  # 100 ms refresh interval for Alpine Linux compatibility
BLINK_INTERVAL = 0.5  # 500 ms blink interval

# Function to implement time-based blinking logic
def blink_display():
    while True:
        print("\033[1;32mBlink!\033[0m")  # Print blink text in green
        time.sleep(BLINK_INTERVAL)
        print("\033[0m ")  # Clear the display
        time.sleep(BLINK_INTERVAL)

# Non-blocking input handling
def non_blocking_input():
    print("Press any key to stop blinking...")
    while True:
        # Check if input is available
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            input()  # Read the input
            break  # Exit the loop on input
        time.sleep(REFRESH_INTERVAL)

if __name__ == '__main__':
    try:
        # Run blinking display in a separate logic flow
        blink_display()
    except KeyboardInterrupt:
        print("Blinking stopped.")
        sys.exit(0)