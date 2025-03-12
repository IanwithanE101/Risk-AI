import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam
import random
import pickle

# Import configuration settings
from config import REPLAY_BUFFER_FOLDER

# Ensure replay buffer folder exists
os.makedirs(REPLAY_BUFFER_FOLDER, exist_ok=True)


class DQNAgent:
    """
    Deep Q-Network (DQN) Agent for training and inference.
    """
    def __init__(self, learning_rate=0.001, gamma=0.99, capacity=10000):
        self.learning_rate = learning_rate
        self.gamma = gamma  # Discount factor for future rewards
        self.model = self.build_model()
        self.replay_buffer = ReplayBuffer(capacity)

    def build_model(self):
        """Creates the DQN model based on our architecture."""
        model = Sequential([
            Input(shape=(444,)),  # Input layer: 444 features
            Dense(512, activation='relu'),
            Dense(512, activation='relu'),
            Dense(256, activation='relu'),
            Dense(256, activation='relu'),
            Dense(256, activation='relu'),
            Dense(177)  # Output layer: 177 actions (no activation)
        ])
        model.compile(optimizer=Adam(learning_rate=self.learning_rate), loss='mse')
        return model

    def train(self, batch_size=64):
        """Trains the DQN using past experiences from the replay buffer."""
        if len(self.replay_buffer.buffer) < batch_size:
            return  # Not enough data to train

        batch = self.replay_buffer.sample(batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = np.array(states)
        next_states = np.array(next_states)
        rewards = np.array(rewards)
        dones = np.array(dones, dtype=np.float32)

        # Predict Q-values for current and next states
        q_values = self.model.predict(states, verbose=0)
        next_q_values = self.model.predict(next_states, verbose=0)

        # Update Q-values using Bellman equation
        for i in range(batch_size):
            action = actions[i]
            target_q = rewards[i] + (self.gamma * np.max(next_q_values[i]) * (1 - dones[i]))  # Gamma=0.99
            q_values[i][action] = target_q  # Update only the taken action

        # Train the model
        self.model.fit(states, q_values, epochs=1, verbose=0, batch_size=batch_size)

    def save(self, model_filename="dqn_model.h5", buffer_filename="replay_buffer.pkl"):
        """Saves the trained model and replay buffer."""
        self.model.save(model_filename)
        self.replay_buffer.save_to_file(buffer_filename)

    def load(self, model_filename="dqn_model.h5", buffer_filename="replay_buffer.pkl"):
        """Loads the trained model and replay buffer."""
        if os.path.exists(model_filename):
            self.model = tf.keras.models.load_model(model_filename)
        else:
            print(f"Model file not found: {model_filename}")

        self.replay_buffer.load_from_file(buffer_filename)


class ReplayBuffer:
    """
    Stores (state, action, reward, next_state, done) tuples for training.
    """
    def __init__(self, capacity=10000):
        self.buffer = []
        self.capacity = capacity

    def store(self, state, action, reward, next_state, done):
        """Stores a single move in the replay buffer."""
        self.buffer.append((state, action, reward, next_state, done))
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)  # Remove oldest data

    def save_to_file(self, filename):
        """Saves the replay buffer to a file."""
        filename = os.path.join(REPLAY_BUFFER_FOLDER, filename)
        with open(filename, "wb") as f:
            pickle.dump(self.buffer, f)

    def load_from_file(self, filename):
        """Loads a replay buffer from a file."""
        filename = os.path.join(REPLAY_BUFFER_FOLDER, filename)
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                self.buffer = pickle.load(f)
        else:
            print(f"Replay buffer file not found: {filename}")

    def sample(self, batch_size):
        """Returns a batch of past moves for training."""
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
