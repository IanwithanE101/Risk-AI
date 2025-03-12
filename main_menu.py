import os
import json
import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
from PIL import Image, ImageTk

from config import BACKGROUND_IMAGE_PATH, CUSTOM_BOARDS_FOLDER, territory_positions, PREVIEW_WIDTH, PREVIEW_HEIGHT
from enviornment import Board
from play_game import RiskGameGUI
from risk_game import RiskGame


# ----------------------------------------------------------------
# MainMenu
# ----------------------------------------------------------------
class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Risk AI Main Menu")
        self.geometry("641x736")
        self.minsize(641, 736)

        self.set_window_icon()

        self.style = ttk.Style(self)
        self._configure_style()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.ai_training_tab = ttk.Frame(self.notebook)
        self.play_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.ai_training_tab, text="AI Training")
        self.notebook.add(self.play_tab, text="Play")

        self.build_ai_training_tab()
        self.build_play_tab()

    def _configure_style(self):
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#eaeaea")
        self.style.configure("TLabel", background="#eaeaea", font=("Arial", 12))
        self.style.configure("TButton", font=("Arial", 12), padding=6)
        self.style.configure("TCombobox", font=("Arial", 12), fieldbackground="white", foreground="black")
        self.style.configure("Switch.TCheckbutton", indicatoron=False, relief="ridge", padding=6)

    def build_ai_training_tab(self):
        lbl = ttk.Label(self.ai_training_tab, text="AI Training not implemented yet.", font=("Arial", 16))
        lbl.pack(pady=20)

    def build_play_tab(self):
        container = ttk.Frame(self.play_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Player selection from directory
        self.player_combos = []
        for i in range(4):
            lbl = ttk.Label(container, text=f"Player {i+1}")
            lbl.grid(row=i, column=0, sticky="w", padx=5, pady=2)

            combo = ttk.Combobox(container, state="readonly", values=["User", "AI"])
            combo.set("User")
            combo.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            self.player_combos.append(combo)

        # Use Custom Board switch
        self.use_custom_board_var = tk.BooleanVar()
        custom_board_switch = ttk.Checkbutton(
            container, text="Use Custom Board", variable=self.use_custom_board_var,
            style="Switch.TCheckbutton", command=self.toggle_custom_board
        )
        custom_board_switch.grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Mini Board Preview Frame
        self.custom_board_frame = ttk.Frame(container)
        self.custom_board_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        self.custom_board_frame.grid_remove()

        self.custom_board = None

        # Board name input
        lbl_board_name = ttk.Label(container, text="Board Name:")
        lbl_board_name.grid(row=6, column=0, sticky="w", padx=5, pady=5)

        self.board_name_var = tk.StringVar()
        board_name_entry = ttk.Entry(container, textvariable=self.board_name_var)
        board_name_entry.grid(row=6, column=1, sticky="ew", padx=5, pady=5)

        save_btn = ttk.Button(container, text="Save", command=self.save_board)
        save_btn.grid(row=6, column=2, sticky="w", padx=5, pady=5)

        load_btn = ttk.Button(container, text="Load", command=self.load_board)
        load_btn.grid(row=7, column=2, sticky="w", padx=5, pady=5)

        container.columnconfigure(1, weight=1)

        # Dropdown for selecting saved boards
        lbl_saved_board = ttk.Label(container, text="Saved Board:")
        lbl_saved_board.grid(row=7, column=0, sticky="w", padx=5, pady=5)

        self.saved_board_var = tk.StringVar(value="None")
        self.saved_board_combo = ttk.Combobox(container, textvariable=self.saved_board_var,
                                              values=self.get_saved_boards_list(), state="readonly")
        self.saved_board_combo.grid(row=7, column=1, sticky="ew", padx=5, pady=5)

        # Start Game Button (Layer 10, far right)
        start_button = ttk.Button(container, text="Start Game", command=self.start_game)
        start_button.grid(row=10, column=2, sticky="e", padx=5, pady=10)

    def toggle_custom_board(self):
        if self.use_custom_board_var.get():
            self.custom_board_frame.grid()
            for child in self.custom_board_frame.winfo_children():
                child.destroy()

            self.custom_board = Board(num_players=4)
            self.custom_board.generate_random_board()

            preview = MiniBoardPreview(self.custom_board_frame, self.custom_board)
            preview.pack()
        else:
            self.custom_board_frame.grid_remove()
            self.custom_board = None

    def save_board(self):
        """Saves the current custom board as a JSON file and updates the dropdown list."""
        board_name = self.board_name_var.get().strip()
        if not board_name:
            tk.messagebox.showerror("Error", "Please enter a board name")
            return

        if self.custom_board is None:
            tk.messagebox.showerror("Error", "No custom board to save!")
            return

        os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
        file_path = os.path.join(CUSTOM_BOARDS_FOLDER, f"{board_name}.json")

        # Extract state manually instead of calling get_game_state()
        board_state = {name: {"owner": terr.get_owner(), "troops": terr.troop_count}
                       for name, terr in self.custom_board.territories.items()}

        try:
            with open(file_path, "w") as f:
                json.dump(board_state, f, indent=4)

            # Update dropdown list so that it can be immediately loaded if wanted
            saved_boards = self.get_saved_boards_list()
            self.saved_board_combo["values"] = saved_boards  # Update dropdown
            self.saved_board_var.set(board_name)  # Set new saved board as selected

            tk.messagebox.showinfo("Success", f"Board saved as {board_name}")

        except Exception as e:
            tk.messagebox.showerror("Save Error", f"Failed to save board:\n{str(e)}")

    def load_board(self):
        """Loads a saved board from JSON and updates the custom board."""
        chosen_board = self.saved_board_var.get()
        if chosen_board == "None":
            tk.messagebox.showwarning("No Board Selected", "Please select a board from the dropdown.")
            return

        file_path = os.path.join(CUSTOM_BOARDS_FOLDER, chosen_board)
        if not os.path.exists(file_path):
            tk.messagebox.showerror("Error", f"File not found: {file_path}")
            return

        try:
            with open(file_path, "r") as f:
                board_data = json.load(f)

            self.custom_board = Board(num_players=4)

            # Set territories from the loaded data
            for name, info in board_data.items():
                if name in self.custom_board.territories:
                    self.custom_board.territories[name].set_owner(info["owner"])
                    self.custom_board.territories[name].troop_count = info["troops"]

            self.use_custom_board_var.set(True)
            self.toggle_custom_board()
            tk.messagebox.showinfo("Success", f"Loaded board: {chosen_board}")

        except Exception as e:
            tk.messagebox.showerror("Load Error", f"Failed to load board:\n{str(e)}")
    def set_window_icon(self):
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                img = Image.open(BACKGROUND_IMAGE_PATH).resize((32, 32), Image.Resampling.LANCZOS)
                self.iconphoto(False, ImageTk.PhotoImage(img))
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    def get_saved_boards_list(self):
        """Retrieves a list of saved board files."""
        if not os.path.isdir(CUSTOM_BOARDS_FOLDER):
            os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
        return [f for f in os.listdir(CUSTOM_BOARDS_FOLDER) if f.endswith(".json")]

    def start_game(self):
        """Starts the game using the selected player types and board selection."""
        player_types = [combo.get() for combo in self.player_combos]

        # Use the selected custom board if enabled, otherwise generate a new one
        if self.use_custom_board_var.get() and self.custom_board is not None:
            board = self.custom_board  # Use preloaded custom board
        else:
            board = Board(num_players=4)  # Generate a new random board
            board.generate_random_board()

        # Initialize RiskGameGUI with the chosen board and player settings
        game_gui = RiskGameGUI(board, player_types)
        game_gui.run()


# ----------------------------------------------------------------
# MiniBoardPreview
# ----------------------------------------------------------------
class MiniBoardPreview(tk.Frame):
    """
    A small frame inside Tkinter that displays a scaled-down Risk map
    plus tinted territory silhouettes. Clicking a territory cycles ownership.
    """
    def __init__(self, parent, board, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT):
        super().__init__(parent)
        self.board = board
        self.width = width
        self.height = height

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
                    if a > 0 and (r, g, b) == (255, 255, 255):
                        px[x, y] = (color[0], color[1], color[2], a)

            base.alpha_composite(t_img)

        self.preview_image = base
        self.tk_preview = ImageTk.PhotoImage(base)
        self.label.config(image=self.tk_preview)
        self.label.image = self.tk_preview  # keep reference

    def on_click(self, event):
        """Handles user clicking on a territory in the preview."""
        x, y = event.x, event.y

        for name in reversed(list(self.territory_images.keys())):
            img = self.territory_images[name]
            if 0 <= x < self.width and 0 <= y < self.height:
                r, g, b, a = img.getpixel((x, y))
                if a > 0:
                    # User clicked inside this territory
                    current_owner = self.board.territories[name].get_owner()
                    new_owner = self.next_owner(current_owner)
                    self.board.territories[name].set_owner(new_owner)
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

# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
    app = MainMenu()
    app.mainloop()
    print("Control Panel closed.")
