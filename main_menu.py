import ctypes
import os
import json
import sys
import tkinter as tk
import tkinter.messagebox
import subprocess
import signal
import psutil
import numpy as np
import threading
import time
import socket

from game_manager import GameManager

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress INFO and WARNING messages
import tensorflow as tf
import pickle
from tkinter import ttk
from PIL import Image, ImageTk
from config import BACKGROUND_IMAGE_PATH, AI
from enviornment import Board


# ----------------------------------------------------------------
# Simplified MainMenu - Just Start/Stop Server
# ----------------------------------------------------------------
class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Risk AI Server Control")
        self.set_window_icon()
        self.geometry("400x300")
        self.minsize(400, 300)

        # Ensure AI folder exists
        os.makedirs(AI, exist_ok=True)

        # Server process tracking
        self.game_manager = None
        self.server_thread = None
        self.server_running = False

        self.style = ttk.Style(self)
        self._configure_style()
        self.build_simple_ui()

    # ----------------------------------------------------------------
    # UI SETUP AND CONFIGURATION
    # ----------------------------------------------------------------
    def _configure_style(self):
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#eaeaea")
        self.style.configure("TLabel", background="#eaeaea", font=("Arial", 12))
        self.style.configure("TButton", font=("Arial", 12), padding=10)

    def build_simple_ui(self):
        """Creates a simple UI with just start/stop buttons and info."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(main_frame, text="Risk AI Game Server",
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Info text
        info_text = """Current Configuration:
• 4 Players (All Human Users)
• Random board generation
• Server runs on localhost:9999

To play: Start server, then connect Godot client"""

        info_label = ttk.Label(main_frame, text=info_text,
                               font=("Arial", 10),
                               justify=tk.LEFT)
        info_label.pack(pady=(0, 30))

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        # Start Server Button
        self.start_button = ttk.Button(button_frame, text="Start Server",
                                       command=self.start_server,
                                       style="TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

        # Stop Server Button
        self.stop_button = ttk.Button(button_frame, text="Stop Server",
                                      command=self.stop_server,
                                      style="TButton")
        self.stop_button.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.X, expand=True)
        self.stop_button.config(state=tk.DISABLED)  # Initially disabled

        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(20, 0))

        self.status_label = ttk.Label(status_frame, text="Server Status: Stopped",
                                      font=("Arial", 10, "italic"))
        self.status_label.pack()

    def set_window_icon(self):
        """Sets window icon if background image exists."""
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                img = Image.open(BACKGROUND_IMAGE_PATH).resize((32, 32), Image.Resampling.LANCZOS)
                self.iconphoto(False, ImageTk.PhotoImage(img))
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    def _reset_button_states(self):
        """Resets button states (called on main thread)."""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Server Status: Stopped")

    # ----------------------------------------------------------------
    # SERVER START/STOP CONTROLS
    # ----------------------------------------------------------------
    def start_server(self):
        """Starts the Risk game server in a separate thread."""
        if self.server_running:
            tk.messagebox.showwarning("Server Running", "A server is already running. Stop it first.")
            return

        try:
            # Hardcoded configuration for simplicity
            # TODO: Make this configurable in future versions
            player_types = ["User", "User", "User", "User"]  # 4 human players
            ai_file_paths = [None, None, None, None]  # No AI files needed for human players

            # Create board with random generation
            board = Board(ai_file_paths=ai_file_paths)
            board.generate_random_board()

            # Debug: Confirm board is populated
            print("🎲 Generated board with territories:")
            for name, t in board.territories.items():
                print(f"  {name}: owner={t.owner}, troops={t.troop_count}")

            # Create GameManager instance
            self.game_manager = GameManager(board=board, player_types=player_types)

            # Start server in separate thread
            self.server_thread = threading.Thread(target=self._run_server_thread, daemon=True)
            self.server_running = True
            self.server_thread.start()

            # Update UI states
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="Server Status: Running")

            print("🚀 Game server started in background thread")
            tk.messagebox.showinfo("Server Started",
                                   "Risk server is now running on localhost:9999!\n\n"
                                   "Connect with your Godot client to play.")

        except Exception as e:
            self.server_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Server Status: Error")
            tk.messagebox.showerror("Error", f"Failed to start server:\n{str(e)}")
            print(f"❌ Error starting server: {e}")

    def stop_server(self):
        """Stops the Risk server and all related processes."""
        print("🛑 Stopping Risk server and related processes...")

        try:
            # First, set the running flag to False
            self.server_running = False

            # FORCIBLY close socket connections to unblock the thread
            self._force_close_connections()

            # Close the server if it exists
            self._close_game_manager_server()

            # Kill any remaining processes
            killed_count = self._cleanup_processes()

            # Enhanced thread monitoring with background checker
            self._monitor_thread_shutdown()

            # Reset variables
            self.game_manager = None
            self.server_thread = None

            # Update button states
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Server Status: Stopped")

            tk.messagebox.showinfo("Server Stopped",
                                   f"Server stopped successfully!\n"
                                   f"{'Cleaned up ' + str(killed_count) + ' processes.' if killed_count > 0 else 'No additional cleanup needed.'}")

        except Exception as e:
            # Even if there's an error, still reset the button states
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Server Status: Error")
            self.server_running = False
            self.game_manager = None
            self.server_thread = None

            tk.messagebox.showerror("Error", f"Error stopping server:\n{str(e)}")
            print(f"❌ Error in stop_server: {e}")

    # ----------------------------------------------------------------
    # SERVER THREAD MANAGEMENT
    # ----------------------------------------------------------------
    def _run_server_thread(self):
        """Runs the game server in a separate thread with connection monitoring."""
        thread_id = threading.get_ident()
        print(f"🔧 Server thread {thread_id} started")

        try:
            # Instead of calling game_manager.start_game(), implement our own loop
            # that can be stopped when server_running becomes False
            self._run_monitored_game_loop()
        except Exception as e:
            print(f"❌ Server thread {thread_id} error: {e}")
            # Check if it's a connection error (client disconnect)
            if "forcibly closed" in str(e) or "disconnected" in str(e).lower():
                print("🔌 Client disconnected, stopping server gracefully")
            else:
                print(f"❌ Unexpected server error: {e}")
        finally:
            # Reset states when server stops
            self.server_running = False
            print(f"✅ Server thread {thread_id} finished executing - work complete")
            print("🔄 Server thread finished, resetting button states")
            # Schedule UI updates on the main thread
            self.after(0, self._reset_button_states)

    def _run_monitored_game_loop(self):
        """Runs the game loop with proper connection and stop monitoring."""
        try:
            # Initialize the server
            from risk_server import RiskServer
            self.game_manager.server = RiskServer(self.game_manager.player_types, self.game_manager.board)
            print("RiskServer initialized. Starting Risk game...")

            # IMPORTANT: Store references for forced socket closing
            self.server_connection = self.game_manager.server.conn
            self.server_socket = self.game_manager.server.server_socket

            # Set socket timeout to make it interruptible
            self.server_connection.settimeout(1.0)  # 1 second timeout

            # Don't regenerate board - use the one we already created
            print("📤 Using pre-generated board...")

            # Send initial board state to Godot
            self.game_manager.server.send_full_board_state()
            print("📤 Initial board state sent to Godot")

            # Game state
            self.game_manager.current_player = 1
            self.game_manager.phases = ["deploy", "attack", "fortify"]

            # Main game loop WITH monitoring
            while (not self.game_manager.check_game_over() and
                   self.server_running):  # ← KEY: Check our stop flag!

                print(f"\n=== Player {self.game_manager.current_player}'s turn ===")

                # Early exit check
                if not self.server_running:
                    print("🛑 Server stop requested, ending game loop")
                    break

                # Determine if current player is user or AI
                player_type = self.game_manager.player_types[self.game_manager.current_player - 1]
                is_user = (player_type == "User")

                print(f"🎮 Player {self.game_manager.current_player} is: {player_type}")

                # Notify Godot about the new turn (with error handling)
                try:
                    self.game_manager.server.send_turn_update(self.game_manager.current_player)
                except Exception as e:
                    print(f"❌ Failed to send turn update: {e}")
                    print("🔌 Client likely disconnected, stopping game")
                    break

                # Go through all phases for this player
                for phase in self.game_manager.phases:
                    # Check stop flag before each phase
                    if not self.server_running:
                        print("🛑 Server stop requested during phase, ending game loop")
                        return

                    print(f"📍 Phase: {phase} for Player {self.game_manager.current_player} ({player_type})")

                    # Send phase update with error handling
                    try:
                        self.game_manager.server.send_phase_update(self.game_manager.current_player, phase,
                                                                   is_user=is_user)
                    except Exception as e:
                        print(f"❌ Failed to send phase update: {e}")
                        print("🔌 Client likely disconnected, stopping game")
                        return

                    if is_user:
                        # User turn - wait for Godot with timeout checking
                        print(
                            f"⏳ Waiting for User Player {self.game_manager.current_player} to complete {phase} phase...")
                        success = self._handle_user_phase_with_timeout(phase)
                        if not success:
                            print("❌ User phase failed (client disconnected or stop requested), ending game")
                            return  # ← KEY: Exit the entire loop on disconnection!
                    else:
                        # AI turn - simulate AI actions WITH stop checking
                        print(f"🤖 AI Player {self.game_manager.current_player} executing {phase} phase...")
                        success = self._handle_ai_phase_with_stop_check(phase)
                        if not success:
                            print("🛑 AI phase stopped due to stop request")
                            return

                    print(f"✅ Player {self.game_manager.current_player} completed {phase} phase")

                # End of turn - move to next player
                self.game_manager.current_player = (self.game_manager.current_player % len(
                    self.game_manager.player_types)) + 1

            print("🏁 Game ending...")

            # Don't call end_game() as it will try to close connections again
            print("\n🎮 GAME OVER!")
            print("📊 Final board state:")
            self._print_final_stats()

        except Exception as e:
            print(f"❌ Error in monitored game loop: {e}")
            # If it's a connection error, exit gracefully
            if "forcibly closed" in str(e) or "disconnected" in str(e).lower():
                print("🔌 Connection error detected, stopping game gracefully")
                return
            raise  # Re-raise other exceptions
        finally:
            # Ensure server is closed (but only once)
            if hasattr(self.game_manager, 'server') and self.game_manager.server:
                try:
                    print("🔌 Closing server connection...")
                    self.game_manager.server.close()
                    print("✅ Server connection closed")
                except Exception as e:
                    print(f"⚠️ Error closing server: {e}")

    # ----------------------------------------------------------------
    # PHASE HANDLING (USER AND AI)
    # ----------------------------------------------------------------
    def _handle_user_phase_with_timeout(self, phase):
        """Handles user phase with timeout checking for stop requests."""
        try:
            # Keep checking for commands with timeout
            while self.server_running:
                try:
                    # This will now timeout every 1 second thanks to settimeout()
                    cmd = self.game_manager.server.wait_for_command("end_phase")

                    if cmd is None:  # Client disconnected
                        print("❌ Client disconnected during user phase")
                        return False

                    # Command received successfully
                    return True

                except socket.timeout:
                    # Socket timeout - check if we should stop
                    if not self.server_running:
                        print("🛑 Stop requested during user phase")
                        return False
                    # Continue waiting if server still running
                    continue

        except Exception as e:
            print(f"❌ Error in user phase: {e}")
            return False

    def _handle_ai_phase_with_stop_check(self, phase):
        """Handles AI phase with periodic stop checking."""
        try:
            # Simulate AI thinking time with stop checking
            print(f"🤖 AI Player {self.game_manager.current_player} thinking...")

            # Instead of time.sleep(1), check every 0.1 seconds for 1 second total
            for i in range(10):  # 10 * 0.1 = 1 second
                if not self.server_running:
                    print("🛑 Stop requested during AI thinking")
                    return False
                time.sleep(0.1)  # Short sleep with frequent checking

            if phase == "deploy":
                return self._simulate_ai_deploy_with_stop_check()
            elif phase == "attack":
                return self._simulate_ai_attack_with_stop_check()
            elif phase == "fortify":
                return self._simulate_ai_fortify_with_stop_check()

            return True

        except Exception as e:
            print(f"❌ Error in AI phase: {e}")
            return False

    # ----------------------------------------------------------------
    # AI SIMULATION WITH STOP CHECKING
    # ----------------------------------------------------------------
    def _simulate_ai_deploy_with_stop_check(self):
        """Simulates AI deploy actions with stop checking."""
        print(f"🪖 AI Player {self.game_manager.current_player} deploying troops...")

        # Check if we should stop before starting
        if not self.server_running:
            return False

        # Get AI's territories
        ai_territories = [name for name, territory in self.game_manager.board.territories.items()
                          if territory.owner == self.game_manager.current_player]

        if ai_territories:
            # Calculate troops to deploy
            troops_to_deploy = self.game_manager.board.calculate_troops(self.game_manager.current_player)
            print(f"💰 AI gets {troops_to_deploy} troops to deploy")

            # Randomly distribute troops among AI's territories
            import random
            while troops_to_deploy > 0 and self.server_running:  # ← Check stop flag
                territory_name = random.choice(ai_territories)
                deploy_amount = min(random.randint(1, 3), troops_to_deploy)

                # Deploy troops
                success = self.game_manager.board.deploy_troops(self.game_manager.current_player, territory_name,
                                                                deploy_amount)
                if success:
                    troops_to_deploy -= deploy_amount
                    print(f"🎯 AI deployed {deploy_amount} troops to {territory_name}")

                    # Send update to Godot (if still running)
                    if self.server_running:
                        try:
                            territory = self.game_manager.board.get_territory(territory_name)
                            self.game_manager.server.send_territory_update(territory_name, territory.owner,
                                                                           territory.troop_count)
                        except Exception as e:
                            print(f"⚠️ Error sending AI deploy update: {e}")
                            return False

        return self.server_running  # Return True only if we're still running

    def _simulate_ai_attack_with_stop_check(self):
        """Simulates AI attack actions with stop checking."""
        print(f"⚔️ AI Player {self.game_manager.current_player} considering attacks...")

        # Check stop flag before processing
        if not self.server_running:
            return False

        # For now, AI skips attack phase
        print("🤖 AI skips attack phase")
        return True

    def _simulate_ai_fortify_with_stop_check(self):
        """Simulates AI fortify actions with stop checking."""
        print(f"🏰 AI Player {self.game_manager.current_player} considering fortification...")

        # Check stop flag before processing
        if not self.server_running:
            return False

        # For now, AI skips fortify phase
        print("🤖 AI skips fortify phase")
        return True

    # ----------------------------------------------------------------
    # PROCESS CLEANUP AND MONITORING
    # ----------------------------------------------------------------
    def _force_close_connections(self):
        """Forcibly closes socket connections to unblock threads."""
        if hasattr(self, 'server_connection') and self.server_connection:
            try:
                print("🔌 Force closing client connection...")
                self.server_connection.close()
                print("✅ Force closed client connection")
            except Exception as e:
                print(f"⚠️ Error force closing client connection: {e}")

        if hasattr(self, 'server_socket') and self.server_socket:
            try:
                print("🔌 Force closing server socket...")
                self.server_socket.close()
                print("✅ Force closed server socket")
            except Exception as e:
                print(f"⚠️ Error force closing server socket: {e}")

    def _close_game_manager_server(self):
        """Closes the game manager server connection."""
        if self.game_manager and hasattr(self.game_manager, 'server'):
            try:
                print("🔌 Closing game manager server connection...")
                self.game_manager.server.close()
                print("✅ Closed game manager server connection")
            except Exception as e:
                print(f"⚠️ Error closing game manager server: {e}")

    def _cleanup_processes(self):
        """Kills any remaining Risk-related processes."""
        killed_count = 0

        # Method 1: Kill processes using port 9999
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.pid == os.getpid():  # Skip current process
                        continue

                    # Use net_connections() instead of deprecated connections()
                    try:
                        connections = proc.net_connections()
                        for conn in connections:
                            if hasattr(conn, 'laddr') and hasattr(conn.laddr, 'port') and conn.laddr.port == 9999:
                                print(f"🔄 Killing process {proc.pid} ({proc.info['name']}) using port 9999")
                                proc.terminate()
                                proc.wait(timeout=3)
                                killed_count += 1
                                break
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        continue

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue
        except Exception as e:
            print(f"⚠️ Error checking connections: {e}")

        # Method 2: Kill Python processes running Risk scripts
        risk_script_names = ['risk_server.py', 'game_manager.py']
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid == os.getpid():  # Skip current process
                    continue

                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = ' '.join(cmdline)
                        # Only kill if it's running risk_server.py or game_manager.py (not main_menu.py)
                        if any(script in cmdline_str for script in risk_script_names):
                            print(f"🔄 Killing Python process {proc.pid} running {cmdline_str}")
                            proc.terminate()
                            proc.wait(timeout=3)
                            killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue

        # Method 3: System-level port checking
        self._cleanup_port_9999()

        return killed_count

    def _cleanup_port_9999(self):
        """Uses system tools to clean up port 9999."""
        try:
            # Try to bind to port 9999 to see if it's free
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            result = test_socket.connect_ex(('127.0.0.1', 9999))
            if result == 0:
                print("⚠️ Port 9999 still in use, attempting force close...")
                # Port is still in use, try more aggressive cleanup
                try:
                    # On Windows, use netstat to find the process
                    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=5)
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if ':9999' in line and 'LISTENING' in line:
                            parts = line.split()
                            if len(parts) > 4:
                                pid = parts[-1]
                                try:
                                    pid = int(pid)
                                    if pid != os.getpid():
                                        proc = psutil.Process(pid)
                                        proc.terminate()
                                        proc.wait(timeout=3)
                                        print(f"🔄 Force killed process {pid} on port 9999")
                                except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                except Exception as e:
                    print(f"⚠️ Error in force cleanup: {e}")
            else:
                print("✅ Port 9999 is now free")
            test_socket.close()
        except Exception as e:
            print(f"⚠️ Error checking port status: {e}")

    def _monitor_thread_shutdown(self):
        """Monitors thread shutdown with enhanced tracking."""
        if self.server_thread and self.server_thread.is_alive():
            print("⏳ Waiting for server thread to finish...")
            self.server_thread.join(timeout=2)  # Wait 2 seconds initially

            if self.server_thread.is_alive():
                print("⚠️ Thread still showing as alive, starting background monitor...")
                # Start background thread monitor
                self._start_thread_monitor()
            else:
                print("✅ Server thread finished and cleaned up successfully")

    def _start_thread_monitor(self):
        """Starts a background monitor to track when the thread actually finishes."""
        if hasattr(self, 'server_thread') and self.server_thread:
            monitor_thread = threading.Thread(
                target=self._monitor_thread_cleanup,
                args=(self.server_thread,),
                daemon=True
            )
            monitor_thread.start()

    def _monitor_thread_cleanup(self, thread_to_monitor):
        """Monitors a thread until it's actually cleaned up."""
        thread_id = getattr(thread_to_monitor, 'ident', 'unknown')
        start_time = time.time()
        check_count = 0

        print(f"🔍 Starting thread monitor for thread {thread_id}")

        while thread_to_monitor.is_alive() and check_count < 300:  # Monitor for max 5 minutes (300 seconds)
            time.sleep(1)  # Check every second
            check_count += 1
            elapsed = int(time.time() - start_time)

            # Print status every 10 seconds to avoid spam
            if check_count % 10 == 0:
                print(f"🕐 Thread {thread_id} still in registry after {elapsed} seconds")

        if thread_to_monitor.is_alive():
            print(f"⚠️ Thread {thread_id} still alive after 5 minutes - giving up monitoring")
            print("   This is likely a Python threading quirk and can be safely ignored")
        else:
            elapsed = int(time.time() - start_time)
            print(f"🎉 Thread {thread_id} successfully cleaned up after {elapsed} seconds")
            print("✅ Thread fully removed from Python's thread registry")

    # ----------------------------------------------------------------
    # UTILITY FUNCTIONS
    # ----------------------------------------------------------------
    def _print_final_stats(self):
        """Prints final game statistics."""
        player_stats = {1: {"territories": 0, "troops": 0},
                        2: {"territories": 0, "troops": 0},
                        3: {"territories": 0, "troops": 0},
                        4: {"territories": 0, "troops": 0}}

        for territory in self.game_manager.board.territories.values():
            if territory.owner in player_stats:
                player_stats[territory.owner]["territories"] += 1
                player_stats[territory.owner]["troops"] += territory.troop_count

        for player_id in range(1, len(self.game_manager.player_types) + 1):
            stats = player_stats[player_id]
            player_type = self.game_manager.player_types[player_id - 1]
            print(
                f"   Player {player_id} ({player_type}): {stats['territories']} territories, {stats['troops']} troops")


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------
if __name__ == "__main__":
    app = MainMenu()
    app.mainloop()
    print("Risk AI Server Control closed.")