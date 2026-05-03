import random
import os
import sys
import time
import copy # For deep copying board for undo functionality
import json # For saving/loading high score
import threading # For blinking effect

# Attempt to import platform-specific input modules
try:
    import termios  # For Unix-like systems
    import tty      # For Unix-like systems
except ImportError:
    termios = None
    tty = None

try:
    import msvcrt   # For Windows systems
except ImportError:
    msvcrt = None


# Game configuration
WIDTH = 80
HEIGHT = 40
EMPTY_CELL = ""
SNAKE_CHAR = '@' # Changed snake character for better visibility
GAME_DELAY_SEC = 0.1 # Small delay for game loop
HIGHSCORE_FILE = "greed_highscore.json" # File to store the high score
BLINK_INTERVAL = 0.7 # Seconds between snake blinks - increased for more noticeable blink

# ANSI Color Codes for numbers 1-9 and empty cell
COLORS = {
    1: "\033[37m", # RED
    2: "\033[32m", # Green
    3: "\033[33m", # Yellow
    4: "\033[34m", # Blue
    5: "\033[35m", # Magenta
    6: "\033[36m", # Cyan
    7: "\033[91m", # Light Red
    8: "\033[92m", # Light Green
    9: "\033[93m", # Light Yellow
    EMPTY_CELL: "\033[90m", # Dark Gray for empty
    'SNAKE': "\033[47m\033[30m\033[1m", # White Background, Black Foreground, Bold for snake
    'SNAKE_BLINK': "\033[91m\033[1m" # Bright Red, Bold for blinking effect (this color is not actively used for blinking display)
}
RESET_COLOR = "\033[0m"

# Global flag for blinking effect
_blink_state = True
_blink_timer = None

def start_blinking():
    """Start the blinking animation in a separate thread."""
    global _blink_state, _blink_timer
    
    def blink_loop():
        global _blink_state
        while True:
            time.sleep(BLINK_INTERVAL)
            _blink_state = not _blink_state
    
    _blink_timer = threading.Thread(target=blink_loop, daemon=True)
    _blink_timer.start()

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_char_unix():
    """Reads a single character input on Unix-like systems without pressing Enter."""
    if not termios or not tty:
        raise ImportError("termios or tty module not available.")
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        # Check for escape sequences common for arrow keys
        if ch == '\x1b': # ESC
            ch += sys.stdin.read(1) # Read '['
            if ch.endswith('['):
                ch += sys.stdin.read(1) # Read A, B, C, D for arrow keys
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def get_char_windows():
    """Reads a single character input on Windows without pressing Enter."""
    if not msvcrt:
        raise ImportError("msvcrt module not available.")
    ch = msvcrt.getch()
    # Check for arrow keys (usually two bytes on Windows)
    if ch == b'\xe0': # Special key indicator
        ch += msvcrt.getch() # Read the second byte
    return ch.decode('utf-8', errors='ignore')

def get_input_char():
    """Abstracts getting a single character input based on OS."""
    if os.name == 'nt':
        return get_char_windows()
    else:
        return get_char_unix()

def load_highscore():
    """Loads the high score from a file."""
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('highscore', 0)
        except json.JSONDecodeError:
            return 0 # File corrupted
    return 0

def save_highscore(score):
    """Saves the high score to a file."""
    with open(HIGHSCORE_FILE, 'w') as f:
        json.dump({'highscore': score}, f)

def generate_board(width, height):
    """Generates a board filled with random numbers from 1-9."""
    board = []
    for _ in range(height):
        row = [random.randint(1, 9) for _ in range(width)]
        board.append(row)
    return board

def display_board(board, snake_pos, score, highscore, menu_active=False, history_length=0):
    """Displays the game board, snake, score, and high score.
    If menu_active is True, it also displays the game over menu below the board.
    """
    print(f"SCORE: {score}\n")
    print(f"HIGH SCORE: {highscore}\n")
    
    if menu_active:
        print("GAME OVER! Select an option:\n")
    else:
        print("Use ARROW keys for cardinal movement. T Y B N for diagonal. 'u' to undo, 'x' to show menu.\n")
    
    # Determine snake character/display based on blink state
    display_snake_char = f"{COLORS['SNAKE']}{SNAKE_CHAR} {RESET_COLOR}" # Default white '@' + space
    # Blinking logic is now handled by the global _blink_state, no need for `blinking` param
    if not _blink_state: # If _blink_state is False, it's the "off" part of the blink cycle
        # When blinking, show a blank space instead of the snake character
        # Two spaces to match the width of the character and the added space
        display_snake_char = "  "
    
    for r_idx, row in enumerate(board):
        display_row = []
        for c_idx, cell_value in enumerate(row):
            if (r_idx, c_idx) == snake_pos:
                display_row.append(display_snake_char)
            else:
                color = COLORS.get(cell_value, RESET_COLOR)
                # Display 0 as a space or dash for better visibility
                display_char = str(cell_value) if cell_value != EMPTY_CELL else ' '
                display_row.append(f"{color}{display_char} {RESET_COLOR}") # Added space after display char
        print("".join(display_row))

    # Display game over menu if active
    if menu_active:
        print("\n" + "=" * 50)
        print("What would you like to do?")
        print("=" * 50)
        print("1. Start New Game")
        if history_length > 1:
            print("2. Undo Last Move (Continue from previous state)")
        print("3. Quit Game")
        print("\nEnter 1, 2, or 3...")

def check_for_any_valid_moves(board, snake_pos, width, height):
    """Checks if there's at least one valid move from the current snake position."""
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue # Skip no-move

            first_target_r, first_target_c = snake_pos[0] + dr, snake_pos[1] + dc
            
            # Check if the first step is valid (within bounds and not an empty cell)
            if not is_valid_position(first_target_r, first_target_c, width, height):
                continue
            
            num_steps = board[first_target_r][first_target_c]
            if num_steps == EMPTY_CELL:
                continue

            # Check if the entire sequence of steps is valid
            current_sequence_valid = True
            for i in range(1, num_steps + 1):
                next_r, next_c = snake_pos[0] + dr * i, snake_pos[1] + dc * i
                if not is_valid_position(next_r, next_c, width, height) or board[next_r][next_c] == EMPTY_CELL:
                    current_sequence_valid = False
                    break
            
            if current_sequence_valid:
                return True # Found at least one valid move
    return False # No valid moves found

def get_move_delta(key):
    """Maps input keys (including arrow key sequences) to (dr, dc) for 8 directions."""
    # (dr, dc) mapping: (row_change, col_change)

    # Check for arrow keys first (these are specific multi-character sequences)
    # Unix-like arrow keys
    if key == '\x1b[A': return (-1, 0)  # Up Arrow
    if key == '\x1b[B': return (1, 0)   # Down Arrow
    if key == '\x1b[C': return (0, 1)   # Right Arrow
    if key == '\x1b[D': return (0, -1)  # Left Arrow
    # Windows arrow keys
    if key == '\xe0H': return (-1, 0)  # Up Arrow
    if key == '\xe0P': return (1, 0)   # Down Arrow
    if key == '\xe0M': return (0, 1)   # Right Arrow
    if key == '\xe0K': return (0, -1)  # Left Arrow

    # If not an arrow key, treat it as a single character and convert to lowercase
    key_lower = key.lower()
    # New diagonal keys
    if key_lower == 't': return (-1, -1)  # Top-Left
    if key_lower == 'y': return (-1, 1)   # Top-Right
    if key_lower == 'b': return (1, -1)   # Down-Left
    if key_lower == 'n': return (1, 1)    # Down-Right
    return None # Invalid key

def is_valid_position(r, c, width, height):
    """Checks if coordinates are within board bounds."""
    return 0 <= r < height and 0 <= c < width


def main_game_loop():
    # Start blinking animation
    start_blinking()
    
    # Initialize game state
    board = generate_board(WIDTH, HEIGHT)
    snake_pos = (random.randint(0, HEIGHT - 1), random.randint(0, WIDTH - 1))
    score = 0
    game_over_state = False # Initialize game_over_state here
    
    current_highscore = load_highscore()

    # History will store tuples of (board_copy, snake_pos_copy, score_copy)
    history = [(copy.deepcopy(board), snake_pos, score)]

    # Flag to indicate if raw input is available and working
    raw_input_available = True
    if (os.name == 'nt' and not msvcrt) or (os.name != 'nt' and (not termios or not tty)):
        print("Warning: Raw input modules (msvcrt/termios) not found or not fully imported.")
        print("Falling back to traditional input (you will need to press Enter after each key).")
        raw_input_available = False
        time.sleep(2) # Give user time to read warning

    # Main game loop
    while True: # Loop indefinitely until 'quit' is explicitly chosen via menu
        clear_screen()
        # Display the board, and potentially the game over menu at the bottom
        display_board(board, snake_pos, score, current_highscore, menu_active=game_over_state, history_length=len(history))

        char_input = ''
        try:
            if raw_input_available:
                char_input = get_input_char()
            else:
                # Adjust prompt based on game_over_state
                prompt = "Enter move (T Y B N, ARROWS), 'u' for undo, 'x' for menu: "
                if game_over_state:
                    prompt = "Enter 1, 2, or 3 for menu choice: "
                
                char_input = input(prompt).strip()
                if not char_input: # Handle empty input from traditional input
                    continue
        except Exception as e: # Catch any input-related errors during raw input
            if raw_input_available: # Only warn if we were trying raw input
                print(f"\nError reading raw input: {e}. Falling back to traditional input.")
                print("Make sure your terminal supports raw input (e.g., not all IDE consoles).")
                raw_input_available = False # Disable raw input for the rest of the game
                time.sleep(2)
                continue # Try again with traditional input
            else: # If already in traditional input and still error, something else is wrong
                print(f"\nCritical input error: {e}. Exiting.")
                print("Thanks for playing!")
                return # Critical error, truly exit

        # --- Handle input based on game state (game over menu or active play) ---
        if game_over_state:
            # Game Over Menu is active, expect menu choices
            if char_input == '1': # Start New Game
                board = generate_board(WIDTH, HEIGHT)
                snake_pos = (random.randint(0, HEIGHT - 1), random.randint(0, WIDTH - 1))
                score = 0
                history = [(copy.deepcopy(board), snake_pos, score)]
                game_over_state = False # Reset state for new game
                current_highscore = load_highscore() # Reload highscore in case it was updated
                continue
            elif char_input == '2' and len(history) > 1: # Undo Last Move
                prev_board, prev_snake_pos, prev_score = history.pop()
                board = copy.deepcopy(prev_board)
                snake_pos = prev_snake_pos
                score = prev_score
                game_over_state = False # Allow playing again after undo
                continue
            elif char_input == '3': # Quit Game
                print("Thanks for playing!")
                return # Exit main game loop
            else:
                # Invalid menu choice, ignore and wait for valid input
                if raw_input_available:
                    print("Invalid menu option. Please choose 1, 2, or 3.")
                    time.sleep(1)
                continue
        else:
            # Game is active, handle movement and special commands
            if char_input.lower() == 'x': # User explicitly asks for menu
                game_over_state = True # Transition to game over state to show menu
                continue
            elif char_input.lower() == 'u': # Undo during active play
                if len(history) > 1:
                    prev_board, prev_snake_pos, prev_score = history.pop()
                    board = copy.deepcopy(prev_board)
                    snake_pos = prev_snake_pos
                    score = prev_score
                    continue
                else:
                    if raw_input_available:
                        print("No moves to undo!")
                        time.sleep(1)
                    continue

            move_delta = get_move_delta(char_input)

            if move_delta: # It's a valid movement key
                dr, dc = move_delta
                
                # --- Simulate the move to check validity without altering current state yet ---
                first_target_r, first_target_c = snake_pos[0] + dr, snake_pos[1] + dc

                current_move_valid = True
                if not is_valid_position(first_target_r, first_target_c, WIDTH, HEIGHT) or \
                   board[first_target_r][first_target_c] == EMPTY_CELL:
                    current_move_valid = False
                else:
                    num_steps = board[first_target_r][first_target_c]
                    cells_to_eat = []
                    
                    for i in range(1, num_steps + 1):
                        next_r, next_c = snake_pos[0] + dr * i, snake_pos[1] + dc * i
                        
                        if not is_valid_position(next_r, next_c, WIDTH, HEIGHT):
                            current_move_valid = False
                            break
                        
                        if board[next_r][next_c] == EMPTY_CELL:
                            current_move_valid = False
                            break
                        
                        cells_to_eat.append((next_r, next_c))
                
                if not current_move_valid:
                    # Invalid move attempted, but check if other valid moves exist
                    if not check_for_any_valid_moves(board, snake_pos, WIDTH, HEIGHT):
                        # No other valid moves, truly game over
                        game_over_state = True
                        if score > current_highscore: # Check and save high score upon definitive game over
                            save_highscore(score)
                            current_highscore = score # Update current session highscore
                    else:
                        # Other moves possible, just inform the player this move was invalid
                        if raw_input_available:
                            print("Invalid move! Try a different direction.")
                            time.sleep(1) # Give player time to read message
                        continue # Continue to next loop iteration without changing state
                
                if current_move_valid: # If the move is valid, THEN save the current state to history BEFORE applying changes
                    history.append((copy.deepcopy(board), snake_pos, score))

                    # Apply the move
                    for r, c in cells_to_eat:
                        score += board[r][c]
                        board[r][c] = EMPTY_CELL # Cell disappears

                    snake_pos = cells_to_eat[-1] # New snake position is the last cell eaten
                    # Check and save high score after a successful move
                    if score > current_highscore:
                        save_highscore(score)
                        current_highscore = score # Update current session highscore
            else:
                # Invalid key press during active game, ignore.
                continue

        # After a move (or non-move, like invalid key), re-check for game over if not already in menu state
        if not game_over_state and not check_for_any_valid_moves(board, snake_pos, WIDTH, HEIGHT):
            game_over_state = True # Set flag to true to trigger game over menu after loop
            if score > current_highscore: # Check and save high score upon definitive game over
                save_highscore(score)
                current_highscore = score # Update current session highscore


        # Add a small delay only if raw input is available and game is not over
        if raw_input_available and not game_over_state:
            time.sleep(GAME_DELAY_SEC)

# This code should ideally not be reached if the loop manages game_over_state correctly
# If it is, it means the loop exited without 'return'.
if __name__ == "__main__":
    print("Starting Greed game...")
    main_game_loop()
