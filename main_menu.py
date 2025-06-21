import ctypes
import os
import json
import sys
import tkinter as tk
import tkinter.messagebox

import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress INFO and WARNING messages
import tensorflow as tf
import pickle
from tkinter import ttk
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam
from PIL import Image, ImageTk
from config import BACKGROUND_IMAGE_PATH, CUSTOM_BOARDS_FOLDER, PREVIEW_WIDTH, PREVIEW_HEIGHT, GAME_REPLAY_STORAGE, \
    SCORED_GAMES, AI, REWARD_CONFIG, FONT_PATH
from enviornment import Board
from pygame_gui import RiskGameGUI


# ----------------------------------------------------------------
# MainMenu
# ----------------------------------------------------------------
class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Risk AI Main Menu")
        self.set_window_icon()
        self.geometry("1200x736")
        self.minsize(1200, 736)

        # Ensure AI folder exists
        os.makedirs(AI, exist_ok=True)

        self.style = ttk.Style(self)
        self._configure_style()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create Tabs
        self.play_tab = ttk.Frame(self.notebook)
        self.scoring_tab = ttk.Frame(self.notebook)
        self.training_tab = ttk.Frame(self.notebook)
        self.ai_management_tab = ttk.Frame(self.notebook)  # NEW TAB

        # Add Tabs to Notebook
        self.notebook.add(self.play_tab, text="Play")
        self.notebook.add(self.scoring_tab, text="Scoring")
        self.notebook.add(self.training_tab, text="Training")
        self.notebook.add(self.ai_management_tab, text="AI Management")  # Add AI tab

        # Build Tabs
        self.build_play_tab()
        self.build_scoring_tab()
        self.build_training_tab()
        self.build_ai_management_tab()  # Build AI Management UI


    def _configure_style(self):
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#eaeaea")
        self.style.configure("TLabel", background="#eaeaea", font=(FONT_PATH, 12))
        self.style.configure("TButton", font=(FONT_PATH, 12), padding=6)
        self.style.configure("TCombobox", font=(FONT_PATH, 12), fieldbackground="white", foreground="black")
        self.style.configure("Switch.TCheckbutton", indicatoron=False, relief="ridge", padding=6)

    def build_scoring_tab(self):
        """Creates the Scoring tab UI."""
        container = ttk.Frame(self.scoring_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # -------------------------------
        # Top: List of Game Replays (Multi-Select)
        # -------------------------------
        replay_frame = ttk.LabelFrame(container, text="Select Game Replays to Score")
        replay_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.replay_listbox = tk.Listbox(replay_frame, selectmode=tk.MULTIPLE, height=10)
        self.replay_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.load_replay_files()

        # -------------------------------
        # Middle: Editable Scoring Parameters
        # -------------------------------
        scoring_frame = ttk.LabelFrame(container, text="Scoring Parameters")
        scoring_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.scoring_entries = {}

        # **Categorize scoring parameters dynamically**
        category_frames = {
            "Deploy": ttk.LabelFrame(scoring_frame, text="Deploy"),
            "Attack": ttk.LabelFrame(scoring_frame, text="Attack"),
            "Fortify": ttk.LabelFrame(scoring_frame, text="Fortify"),
            "Game": ttk.LabelFrame(scoring_frame, text="Game"),
        }

        for frame in category_frames.values():
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        for key, value in REWARD_CONFIG.items():
            category = key.split("_")[0]  # Extract category (e.g., "DEPLOY_BONUS" → "DEPLOY")
            category = category.capitalize()  # Ensure correct capitalization
            if category in category_frames:
                frame = category_frames[category]

                # Create Label
                label = ttk.Label(frame, text=key.replace("_", " "))  # Make it more readable
                label.pack(anchor="w", padx=5, pady=2)

                # Create Entry Field with Default Value
                entry_var = tk.StringVar()
                entry_var.set(str(value))  # Ensure default values are set
                entry = ttk.Entry(frame, textvariable=entry_var, width=8)
                entry.pack(anchor="w", padx=5, pady=2)

                self.scoring_entries[key] = entry_var  # Store reference

        # -------------------------------
        # Bottom: Score Button
        # -------------------------------
        score_button = ttk.Button(container, text="Score Selected Games", command=self.score_selected_games)
        score_button.pack(pady=10)

    def build_training_tab(self):
        """Creates the Training tab UI."""
        container = ttk.Frame(self.training_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # -------------------------------
        # Top: List of Scored Games (Multi-Select)
        # -------------------------------
        scored_games_frame = ttk.LabelFrame(container, text="Select Scored Games for Training")
        scored_games_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.scored_games_listbox = tk.Listbox(scored_games_frame, selectmode=tk.MULTIPLE, height=10)
        self.scored_games_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.load_scored_games()

        # -------------------------------
        # Middle: AI Selection (New or Existing)
        # -------------------------------
        ai_selection_frame = ttk.LabelFrame(container, text="AI Model Selection")
        ai_selection_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Dropdown for existing AIs
        self.selected_ai_var = tk.StringVar()
        self.ai_dropdown = ttk.Combobox(ai_selection_frame, textvariable=self.selected_ai_var, state="readonly")
        self.ai_dropdown.pack(fill=tk.X, padx=5, pady=5)
        self.load_trained_ai_models()

        # Entry for naming a new AI model
        self.new_ai_name_var = tk.StringVar()
        new_ai_entry = ttk.Entry(ai_selection_frame, textvariable=self.new_ai_name_var)
        new_ai_entry.pack(fill=tk.X, padx=5, pady=5)
        new_ai_entry.insert(0, "NewAIModel")

        # -------------------------------
        # Bottom: Train Button
        # -------------------------------
        self.train_button = ttk.Button(container, text="Train AI", command=self.train_ai)
        self.train_button.pack(pady=10)

    def load_replay_files(self):
        """Loads available replays from GAME_REPLAY_STORAGE."""
        self.replay_listbox.delete(0, tk.END)
        if os.path.exists(GAME_REPLAY_STORAGE):
            replays = sorted(os.listdir(GAME_REPLAY_STORAGE), reverse=True)
            for replay in replays:
                self.replay_listbox.insert(tk.END, replay)

    def load_scored_games(self):
        """Loads available scored games from SCORED_GAMES."""
        self.scored_games_listbox.delete(0, tk.END)
        if os.path.exists(SCORED_GAMES):
            scored_games = sorted(os.listdir(SCORED_GAMES), reverse=True)
            for game in scored_games:
                self.scored_games_listbox.insert(tk.END, game)

    def load_trained_ai_models(self):
        """Loads available trained AI models from TRAINED_AI."""
        if not os.path.exists(AI):
            os.makedirs(AI, exist_ok=True)
        trained_models = sorted(os.listdir(AI))
        self.ai_dropdown["values"] = trained_models

    def score_selected_games(self):
        """Scores selected game replays and saves them to SCORED_GAMES."""
        selected_indices = self.replay_listbox.curselection()
        selected_files = [self.replay_listbox.get(i) for i in selected_indices]

        if not selected_files:
            tk.messagebox.showwarning("No Selection", "Please select at least one game replay to score.")
            return

        updated_scoring = {key: float(entry.get()) for key, entry in self.scoring_entries.items()}

        for replay_file in selected_files:
            replay_path = os.path.join(GAME_REPLAY_STORAGE, replay_file)
            scored_path = os.path.join(SCORED_GAMES, replay_file)

            with open(replay_path, "r") as f:
                game_data = json.load(f)

            scored_data = self.apply_scoring(game_data, updated_scoring)

            with open(scored_path, "w") as f:
                json.dump(scored_data, f, indent=4)

        tk.messagebox.showinfo("Scoring Complete", "Selected games have been scored and saved.")

    def apply_scoring(self, game_data, scoring_config):
        """Applies scoring based on the given configuration."""
        for move in game_data["moves"]:
            phase = move["phase"]
            action = move["action"]
            key = f"{phase.upper()}_{action.upper()}"

            if key in scoring_config:
                move["reward"] = scoring_config[key]
            else:
                move["reward"] = 0

        return game_data

    def build_play_tab(self):
        container = ttk.Frame(self.play_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # "All same AI" Checkbox
        self.all_same_ai_var = tk.BooleanVar(value=True)  # Defaults to enabled
        all_same_ai_check = ttk.Checkbutton(
            container, text="All same AI", variable=self.all_same_ai_var, command=self.toggle_ai_lock
        )
        all_same_ai_check.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Player selection
        self.player_combos = []
        self.ai_combos = []
        self.ai_file_paths = [None] * 4  # Store selected AI paths per player

        for i in range(4):
            # Player type selection
            lbl = ttk.Label(container, text=f"Player {i + 1}")
            lbl.grid(row=i + 1, column=0, sticky="w", padx=5, pady=2)

            player_combo = ttk.Combobox(container, state="readonly", values=["User", "AI"])
            player_combo.set("User")
            player_combo.grid(row=i + 1, column=1, sticky="ew", padx=5, pady=2)
            player_combo.bind("<<ComboboxSelected>>", lambda event, p=i: self.update_ai_selection(p))
            self.player_combos.append(player_combo)

            # AI selection dropdown
            ai_lbl = ttk.Label(container, text="AI:")
            ai_lbl.grid(row=i + 1, column=2, sticky="e", padx=(5, 2), pady=2)  # Right-align label

            ai_combo = ttk.Combobox(container, state="readonly", values=self.get_ai_list())
            ai_combo.grid(row=i + 1, column=3, columnspan=2, sticky="ew", padx=(2, 5), pady=2)  # Expand dropdown
            ai_combo.bind("<<ComboboxSelected>>", lambda event, p=i: self.set_ai_for_player(p, ai_combo))
            self.ai_combos.append(ai_combo)

        # Use Custom Board switch
        self.use_custom_board_var = tk.BooleanVar()
        custom_board_switch = ttk.Checkbutton(
            container, text="Use Custom Board", variable=self.use_custom_board_var,
            style="Switch.TCheckbutton", command=self.toggle_custom_board
        )
        custom_board_switch.grid(row=5, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Mini Board Preview
        self.custom_board_frame = ttk.Frame(container)
        self.custom_board_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        self.custom_board_frame.grid_remove()

        self.custom_board = None

        # Board name input
        lbl_board_name = ttk.Label(container, text="Board Name:")
        lbl_board_name.grid(row=7, column=0, sticky="w", padx=5, pady=5)

        self.board_name_var = tk.StringVar()
        board_name_entry = ttk.Entry(container, textvariable=self.board_name_var)
        board_name_entry.grid(row=7, column=1, sticky="ew", padx=5, pady=5)

        save_btn = ttk.Button(container, text="Save", command=self.save_board)
        save_btn.grid(row=7, column=2, sticky="w", padx=5, pady=5)

        load_btn = ttk.Button(container, text="Load", command=self.load_board)
        load_btn.grid(row=8, column=2, sticky="w", padx=5, pady=5)

        container.columnconfigure(1, weight=1)

        # Saved Board dropdown
        lbl_saved_board = ttk.Label(container, text="Saved Board:")
        lbl_saved_board.grid(row=8, column=0, sticky="w", padx=5, pady=5)

        self.saved_board_var = tk.StringVar(value="None")
        self.saved_board_combo = ttk.Combobox(container, textvariable=self.saved_board_var,
                                              values=self.get_saved_boards_list(), state="readonly")
        self.saved_board_combo.grid(row=8, column=1, sticky="ew", padx=5, pady=5)

        # Start Game Button
        start_button = ttk.Button(container, text="Start Game", command=self.start_game)
        start_button.grid(row=10, column=2, sticky="e", padx=5, pady=10)

        self.toggle_ai_lock()  # Ensure AI dropdowns are initially locked

    # --------------------------
    # AI SELECTION HELPERS
    # --------------------------
    def toggle_ai_lock(self):
        """Locks AI selection if 'All same AI' is checked, keeping all AI players the same."""
        lock = self.all_same_ai_var.get()

        for i in range(4):
            if lock:
                self.ai_combos[i].config(state="disabled" if i > 0 else "readonly")
                if i > 0 and self.ai_combos[0].get():
                    self.ai_combos[i].set(self.ai_combos[0].get())  # Sync AI selections
            else:
                self.ai_combos[i].config(state="readonly")

    def update_ai_selection(self, player_index):
        """Enables or disables AI selection based on player type."""
        if self.player_combos[player_index].get() == "AI":
            self.ai_combos[player_index].config(state="readonly")
        else:
            self.ai_combos[player_index].config(state="disabled")
            self.ai_combos[player_index].set("")  # Clear AI selection

    def set_ai_for_player(self, player_index, ai_combo):
        """Updates the stored AI file path for a player."""
        selected_ai = ai_combo.get()
        if selected_ai:
            self.ai_file_paths[player_index] = os.path.join(AI, selected_ai)
            if self.all_same_ai_var.get():
                for i in range(4):
                    self.ai_combos[i].set(selected_ai)
                    self.ai_file_paths[i] = self.ai_file_paths[player_index]

    def get_ai_list(self):
        """Retrieves a list of AI models stored in the AI folder."""
        if not os.path.exists(AI):
            os.makedirs(AI, exist_ok=True)
        return [f for f in os.listdir(AI) if f.endswith(".pkl")]

    def toggle_custom_board(self):
        """Handles enabling/disabling the custom board preview."""
        if self.use_custom_board_var.get():
            self.custom_board_frame.grid()

            # Remove existing preview if it exists
            for child in self.custom_board_frame.winfo_children():
                child.destroy()

            self.custom_board = Board()
            self.custom_board.generate_random_board()
            self.custom_board_preview = MiniBoardPreview(self.custom_board_frame, self.custom_board)
            self.custom_board_preview.pack()
        else:
            self.custom_board_frame.grid_remove()
            self.custom_board = None
            self.custom_board_preview = None  # Ensure it's cleared

    def set_window_icon(self):
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                img = Image.open(BACKGROUND_IMAGE_PATH).resize((32, 32), Image.Resampling.LANCZOS)
                self.iconphoto(False, ImageTk.PhotoImage(img))
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    def save_board(self):
        """Passes save request to MiniBoardPreview and updates the dropdown list."""
        board_name = self.board_name_var.get().strip()
        if not board_name:
            tk.messagebox.showerror("Error", "Please enter a board name")
            return

        # Call the save method in MiniBoardPreview
        if self.custom_board_preview:
            self.custom_board_preview.save_board(board_name)

        # Update dropdown list after saving
        self.saved_board_combo["values"] = self.get_saved_boards_list()
        self.saved_board_var.set(board_name)

    def load_board(self):
        """Passes the board loading task to MiniBoardPreview."""
        chosen_board = self.saved_board_var.get().strip()

        if not chosen_board or chosen_board == "None":
            tk.messagebox.showwarning("No Board Selected", "Please select a board from the dropdown.")
            return

        # Ensure we are not adding .json twice
        if not chosen_board.endswith(".json"):
            chosen_board += ".json"

        # Just call the MiniBoardPreview load method
        if self.custom_board_preview:
            self.custom_board_preview.load_board(chosen_board)
        else:
            tk.messagebox.showerror("Error", "MiniBoardPreview is not initialized.")

    def refresh_saved_boards(self):
        """Refreshes the list of saved boards in the dropdown."""
        saved_boards = self.get_saved_boards_list()
        self.saved_board_combo["values"] = saved_boards  # Update dropdown values
        if saved_boards:
            self.saved_board_var.set(saved_boards[0])  # Select first available board

    def get_saved_boards_list(self):
        """Retrieves a list of saved board files."""
        if not os.path.isdir(CUSTOM_BOARDS_FOLDER):
            os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
        return [f.replace(".json", "") for f in os.listdir(CUSTOM_BOARDS_FOLDER) if f.endswith(".json")]

    def get_saved_boards_list(self):
        """Retrieves a list of saved board files."""
        if not os.path.isdir(CUSTOM_BOARDS_FOLDER):
            os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
        return [f for f in os.listdir(CUSTOM_BOARDS_FOLDER) if f.endswith(".json")]

    def start_game(self):
        """Starts the game using the selected player types and board selection."""
        player_types = [combo.get() for combo in self.player_combos]
        ai_file_paths = [combo.get() if combo.get() != "None" else None for combo in self.ai_combos]

        # Use the selected custom board if enabled, otherwise generate a new one
        if self.use_custom_board_var.get() and self.custom_board is not None:
            board = self.custom_board  # Use preloaded custom board
            board.ai_file_paths = ai_file_paths  # Set AI paths for players
        else:
            board = Board(ai_file_paths=ai_file_paths)  # Generate a new random board
            board.generate_random_board()

        # Initialize RiskGameGUI with the chosen board and player settings
        game_gui = RiskGameGUI(board, player_types)
        game_gui.run()

    def train_ai(self):
        """Trains an AI model using selected scored games."""
        selected_indices = self.scored_games_listbox.curselection()
        selected_files = [self.scored_games_listbox.get(i) for i in selected_indices]

        if not selected_files:
            tk.messagebox.showwarning("No Selection", "Please select at least one scored game to train with.")
            return

        ai_name = self.new_ai_name_var.get().strip()
        if not ai_name and not self.selected_ai_var.get():
            tk.messagebox.showerror("Error", "Please enter a new AI name or select an existing AI model.")
            return

        # Determine AI Model Path
        if ai_name:
            ai_path = os.path.join(AI, f"{ai_name}.h5")
        else:
            ai_path = os.path.join(AI, f"{self.selected_ai_var.get()}.h5")

        # Check for GPU availability
        self.device = "/GPU:0" if tf.config.list_physical_devices('GPU') else "/CPU:0"
        print(f"Training on: {self.device}")

        # Load or Create AI Model
        if os.path.exists(ai_path):
            model = tf.keras.models.load_model(ai_path)
        else:
            model = self.build_dqn_model()

        # Disable Train Button During Training
        self.train_button.config(state=tk.DISABLED)

        training_data = []
        for file in selected_files:
            path = os.path.join(SCORED_GAMES, file)
            with open(path, "r") as f:
                game_data = json.load(f)
                training_data.extend(game_data["moves"])  # Extract moves

        # Convert to numpy arrays
        states, actions, rewards, next_states = self.process_training_data(training_data)

        # Train Model
        with tf.device(self.device):
            self.perform_training(model, states, actions, rewards, next_states)

        # Save Trained Model
        model.save(ai_path)

        # Re-enable Train Button
        self.train_button.config(state=tk.NORMAL)
        tk.messagebox.showinfo("Training Complete", f"AI model '{ai_name}' has been trained and saved.")

    def build_dqn_model(self):
        """Builds a new DQN model."""
        model = Sequential([
            Input(shape=(810,)),  # 405 current + 405 previous
            Dense(512, activation='relu'),
            Dense(512, activation='relu'),
            Dense(256, activation='relu'),
            Dense(256, activation='relu'),
            Dense(256, activation='relu'),
            Dense(178)  # Output layer: 178 actions, last 1 being a boolean of whether to cash out the cards in hand into troops.
        ])
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        return model

    def process_training_data(self, training_data):
        """Processes the training data into NumPy arrays."""
        states, actions, rewards, next_states = [], [], [], []

        for move in training_data:
            states.append(move["state"])
            actions.append(move["action"])
            rewards.append(move["reward"])
            next_states.append(move["next_state"])

        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
        )

    def perform_training(self, model, states, actions, rewards, next_states, batch_size=64, gamma=0.99):
        """Trains the model using the DQN update rule, now supporting 178 output nodes."""
        if len(states) < batch_size:
            return

        indices = np.random.choice(len(states), batch_size, replace=False)
        batch_states = states[indices]
        batch_actions = actions[indices]
        batch_rewards = rewards[indices]
        batch_next_states = next_states[indices]

        q_values = model.predict(batch_states, verbose=0)
        next_q_values = model.predict(batch_next_states, verbose=0)

        for i in range(batch_size):
            action = batch_actions[i]
            reward = batch_rewards[i]
            future_q = np.max(next_q_values[i])
            target_q = reward + gamma * future_q

            # Handle special "cash out" output at index 177
            if 0 <= action < 178:
                q_values[i][action] = target_q

        model.fit(batch_states, q_values, epochs=1, verbose=0, batch_size=batch_size)

    # -----------------------------------------
    # AI MANAGEMENT TAB
    # -----------------------------------------
    def build_ai_management_tab(self):
        container = ttk.Frame(self.ai_management_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Input AI Name
        lbl_ai_name = ttk.Label(container, text="AI Name:")
        lbl_ai_name.pack(anchor="w", padx=5, pady=5)

        self.ai_name_var = tk.StringVar()
        ai_name_entry = ttk.Entry(container, textvariable=self.ai_name_var)
        ai_name_entry.pack(fill=tk.X, padx=5, pady=5)

        # Create AI Button
        create_ai_button = ttk.Button(container, text="Create AI", command=self.create_ai)
        create_ai_button.pack(pady=5)

        # AI List
        lbl_ai_list = ttk.Label(container, text="Existing AI Models:")
        lbl_ai_list.pack(anchor="w", padx=5, pady=5)

        self.ai_listbox = tk.Listbox(container, height=10)
        self.ai_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.load_ai_list()

        # Delete AI Button
        delete_ai_button = ttk.Button(container, text="Delete AI", command=self.delete_ai)
        delete_ai_button.pack(pady=5)

    def create_ai(self):
        """Creates a new AI model file and saves it."""
        ai_name = self.ai_name_var.get().strip()
        if not ai_name:
            tk.messagebox.showerror("Error", "Please enter an AI name.")
            return

        ai_path = os.path.join(AI, f"{ai_name}.pkl")
        if os.path.exists(ai_path):
            tk.messagebox.showerror("Error", "AI name already exists.")
            return

        # Save an empty AI model as a placeholder
        with open(ai_path, "wb") as f:
            pickle.dump({}, f)

        self.load_ai_list()
        tk.messagebox.showinfo("Success", f"AI '{ai_name}' created.")

    def delete_ai(self):
        """Deletes the selected AI file."""
        selected_index = self.ai_listbox.curselection()
        if not selected_index:
            tk.messagebox.showerror("Error", "No AI selected.")
            return

        ai_name = self.ai_listbox.get(selected_index[0])
        ai_path = os.path.join(AI, ai_name)

        if os.path.exists(ai_path):
            os.remove(ai_path)
            self.load_ai_list()
            tk.messagebox.showinfo("Success", f"AI '{ai_name}' deleted.")

    def load_ai_list(self):
        """Loads the list of AI models."""
        self.ai_listbox.delete(0, tk.END)
        if os.path.exists(AI):
            ai_files = sorted(os.listdir(AI))
            for ai in ai_files:
                self.ai_listbox.insert(tk.END, ai)

    def get_ai_list(self):
        """Retrieves available AI models."""
        if not os.path.exists(AI):
            os.makedirs(AI, exist_ok=True)
        return [f for f in os.listdir(AI) if f.endswith(".pkl")]

# ----------------------------------------------------------------
# MiniBoardPreview
# ----------------------------------------------------------------
class MiniBoardPreview(tk.Frame):
    """
    A small frame inside Tkinter that displays a scaled-down Risk map
    plus tinted territory silhouettes. Clicking a territory cycles ownership.
    The board object is updated in real-time.
    """
    def __init__(self, parent, board, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT):
        super().__init__(parent)
        self.board = board
        self.width = width
        self.height = height
        self.parent = parent  # Reference to MainMenu

        self.bg_image = None
        self.territory_images = {}  # name -> PIL territory image
        self.preview_image = None
        self.tk_preview = None

        self.load_background()
        self.load_territories()

        self.label = tk.Label(self)
        self.label.pack()
        self.label.bind("<Button-1>", self.on_click)

        self.update_preview()

    def load_background(self):
        """Loads the game board background image."""
        if os.path.exists(BACKGROUND_IMAGE_PATH):
            pil_bg = Image.open(BACKGROUND_IMAGE_PATH).convert("RGBA")
            pil_bg = pil_bg.resize((self.width, self.height), Image.Resampling.LANCZOS)
            self.bg_image = pil_bg
        else:
            self.bg_image = Image.new("RGBA", (self.width, self.height), (255, 255, 255, 255))

    def load_territories(self):
        """Loads and scales individual territory images."""
        for name, territory in self.board.territories.items():
            image_path = territory.get_image_path()
            if os.path.exists(image_path):
                try:
                    pil_img = Image.open(image_path).convert("RGBA")
                    pil_img = pil_img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                    self.territory_images[name] = pil_img
                except Exception as e:
                    print(f"Could not load territory {name}: {e}")

    def update_preview(self):
        """
        Updates the preview image based on the current board state.
        Applies coloring based on ownership.
        """
        base = self.bg_image.copy() if self.bg_image else Image.new("RGBA", (self.width, self.height), (255, 255, 255, 255))

        for name, territory in self.board.territories.items():
            if name not in self.territory_images:
                continue

            t_img = self.territory_images[name].copy()
            color = self.get_color_for_owner(territory.get_owner())
            px = t_img.load()
            w, h = t_img.size

            for x in range(w):
                for y in range(h):
                    r, g, b, a = px[x, y]
                    if a > 0 and (r > 230 and g > 230 and b > 230):  # Replace very white pixels
                        px[x, y] = (color[0], color[1], color[2], a)

            base.alpha_composite(t_img)

        self.preview_image = base
        self.tk_preview = ImageTk.PhotoImage(base)
        self.label.config(image=self.tk_preview)
        self.label.image = self.tk_preview  # Keep reference

    def on_click(self, event):
        """Handles user clicking on a territory in the preview and updates board object."""
        x, y = event.x, event.y

        for name in reversed(list(self.territory_images.keys())):
            img = self.territory_images[name]
            if 0 <= x < self.width and 0 <= y < self.height:
                r, g, b, a = img.getpixel((x, y))
                if a > 0:
                    # User clicked inside this territory
                    current_owner = self.board.territories[name].get_owner()
                    new_owner = self.next_owner(current_owner)
                    self.board.territories[name].set_owner(new_owner)  # Update actual board object

                    # Tell MainMenu that the board has changed
                    if hasattr(self.parent, "custom_board"):
                        self.parent.custom_board = self.board  # Sync with MainMenu

                    self.update_preview()
                    break

    def next_owner(self, current):
        """Cycles the owner of a clicked territory."""
        if current is None:
            return 1
        elif current == 4:
            return None
        else:
            return current + 1

    def get_color_for_owner(self, owner_id):
        """Returns the RGB color corresponding to an owner."""
        color_map = {
            1: (255, 0, 0),
            2: (0, 255, 0),
            3: (0, 0, 255),
            4: (255, 255, 0),
            None: (255, 255, 255),
        }
        return color_map.get(owner_id, (255, 255, 255))

    def save_board(self, board_name):
        """Saves the currently edited board inside MiniBoardPreview."""
        if not board_name:
            tk.messagebox.showerror("Error", "Please enter a board name")
            return

        if self.board is None:
            tk.messagebox.showerror("Error", "No board to save!")
            return

        os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)

        # Ensure filename is correct
        if not board_name.endswith(".json"):
            board_name += ".json"

        file_path = os.path.join(CUSTOM_BOARDS_FOLDER, board_name)

        # Extract the CURRENT edited state from MiniBoardPreview
        board_state = {name: {"owner": terr.get_owner(), "troops": terr.troop_count}
                       for name, terr in self.board.territories.items()}

        try:
            with open(file_path, "w") as f:
                json.dump(board_state, f, indent=4)

            tk.messagebox.showinfo("Success", f"Board saved as {board_name}")

        except Exception as e:
            tk.messagebox.showerror("Save Error", f"Failed to save board:\n{str(e)}")

    def load_board(self, board_name):
        """Loads a saved board into the existing board object, updating its state."""
        file_path = os.path.join(CUSTOM_BOARDS_FOLDER, board_name)

        if not os.path.exists(file_path):
            tk.messagebox.showerror("Error", f"File not found: {file_path}")
            return

        try:
            with open(file_path, "r") as f:
                board_data = json.load(f)

            # MODIFY THE EXISTING BOARD (don't create a new one)
            for name, info in board_data.items():
                if name in self.board.territories:  # Ensure the territory exists
                    self.board.territories[name].set_owner(info["owner"])  # Update ownership
                    self.board.territories[name].troop_count = info["troops"]  # Update troop count

            self.update_preview()  # Reflect the new board state in the UI
            tk.messagebox.showinfo("Success", f"Loaded board: {board_name}")

        except Exception as e:
            tk.messagebox.showerror("Load Error", f"Failed to load board:\n{str(e)}")


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
    app = MainMenu()
    app.mainloop()
    print("Control Panel closed.")
