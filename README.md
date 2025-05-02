# Risk AI Trainer & Game Framework

A Python-based game engine and training platform for Risk, featuring a full GUI, modular AI support (currently Deep Q-Learning), and tools for building, training, and testing AI agents. Users can create custom boards, play manually, or pit AI against each other to generate data and improve strategies.

## Overview

- Full GUI-based Risk game  
- Assign different AI models to each of the 4 players  
- Allows imitation learning by allowing human players to build training data by playing games  
- Supports scoring and training with reward configuration  
- Will have a genetic algorithm for the reward configurations and types of rewards  
- Automatically logs replays to disk in readable format  
- Built-in training for DQN models using scored data  
- GUI tools for managing boards and AI models  
- Modular architecture designed for easy AI swapping (would need manual integration)

## Features

- Replay logging for every turn and phase  
- Adjustable reward config used during scoring (soon to include genetic algorithm)  
- Save/load boards and games from the GUI  
- Scoring tab to assign rewards to past games to generate trainable data  
- Training tab to build DQN models from scored files  
- AI Management tab to create/delete AI models  
- Control panel and AI animation system in GUI  
- Recolorable territory-based troop map with troop display  

## AI System Design

AI decisions are handled via a modular AI handler. The game framework always queries an AI model, even for human players, and stores the overwritten output for analysis or training.  
Human moves override AI predictions when needed, but the AI’s original outputs are preserved in replay logs for future supervised learning.

## AI Training Workflow

1. Play games (either in GUI or headless simulation)  
2. Replays are saved automatically to `game_replay_storage/`  
3. Use the **Scoring** tab to apply reward values to past games  
4. Train AI models on scored replays in the **Training** tab  
5. Assign trained models to players in the **Play** tab  

## Future Plans

- Card system support  
- Genetic algorithm to evolve training parameters  
- Additional AI strategies (MCTS, PPO, Rule-Based)  
- Plugin architecture for new AI types  
- Replay visualizer  
- Use this framework to train any type of model from replay logs  

## Project Structure

main_menu.py – GUI menu and mode control  
enviornment.py – Board logic and input generation  
risk_game.py – Core Risk game rules and flow  
pygame_gui.py – Visual GUI game interface  
game_manager.py – Game controller (AI/GUI bridge)  
game_storage.py – Logging game replays  
scoring.py – Scoring system for replays  
config.py – Paths, colors, dimensions, constants  
AI/ – Folder of saved models (.h5)  
game_replay_storage/ – JSON files of saved games  

## Run the Program

```bash
python main_menu.py
```

> Requires Python 3.10+  
> Install dependencies:  
> `pip install -r requirements.txt`

## License

This project is licensed under the **Unlicense**, making it completely public domain. You can use, modify, and distribute it freely.

## Credits

**Author:** Eian  
Started as a school project with friends. Completely rebuilt.
