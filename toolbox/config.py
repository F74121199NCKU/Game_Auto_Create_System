from google import genai
from google.genai import types              #type:ignore
import sys
import os
import re

# API Key setup
API_KEY = input("Please enter your Google Gemini API Key: ").strip()
client = genai.Client(api_key=API_KEY)


# Global 
MODEL_SMART         = 'gemini-2.5-pro'
MODEL_NORMAL        = 'gemini-2.5-flash'
EMBEDDING_MODEL     = "models/gemini-embedding-001" 
CHAOS_PAYLOAD = """
# ==========================================
# [CHAOS PAYLOAD INJECTED: SYNCHRONOUS FUZZ TESTER ACTIVE]
# ==========================================
import pygame
import random
import sys
import time
import os

# Force output encoding to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

print("[FUZZER] Synchronous Safe Mode Test Initialized.", flush=True)

TEST_KEYS = [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, 
             pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE, 
             pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]

_original_event_get = pygame.event.get

_FUZZ_START_TIME = time.time()
_FUZZ_DURATION_SEC = 12.0
# Step 1: Define the non-blocking delay period
_CHAOS_DELAY_SEC = 2.0  

def _chaotic_event_get(*args, **kwargs):
    current_time = time.time()
    
    # Step 2: Adjust total time to include the initial delay
    if current_time - _FUZZ_START_TIME > (_FUZZ_DURATION_SEC + _CHAOS_DELAY_SEC):
        print("[FUZZ] SUCCESS: Test Passed cleanly.", flush=True)
        try:
            pygame.quit()
        except:
            pass
        os._exit(0)

    # Always fetch the real events first
    events = _original_event_get(*args, **kwargs)
    
    # Step 3: Non-blocking delay check. 
    # If we are still in the delay period, just return normal events without injecting chaos.
    if current_time - _FUZZ_START_TIME < _CHAOS_DELAY_SEC:
        return events
    
    # --- CHAOS INJECTION START ---
    # Randomly keyboard button test
    if random.random() < 0.2:
        random_key = random.choice(TEST_KEYS)
        events.append(pygame.event.Event(pygame.KEYDOWN, {'key': random_key, 'unicode': '', 'mod': 0, 'scancode': 0}))
        events.append(pygame.event.Event(pygame.KEYUP, {'key': random_key})) 
        
    # Randomly mouse button test
    if random.random() < 0.1:
        try:
            surface = pygame.display.get_surface()
            w, h = surface.get_size() if surface else (800, 600)
            rand_x = random.randint(0, w)
            rand_y = random.randint(0, int(h * 0.85)) 
            
            events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (rand_x, rand_y), 'button': 1, 'touch': False}))
            events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (rand_x, rand_y), 'button': 1, 'touch': False}))
        except:
            pass

    return events

# Override the original pygame function
pygame.event.get = _chaotic_event_get
# ==========================================
"""

GLOBAL_JSON_TEMPLATE = """
{
  "game_metadata": {
    "title": "String (Name of the game)",
    "genre": "String",
    "fps": "int",
    "screen_size": ["int", "int"]
  },
 
  "config_data": {
    "description": "Global variables and tuning parameters (e.g., PLAYER_SPEED, ASSET_PATHS)",
    "parameters": {
      "parameter_name": "Value (Can be int, float, string, or list)"
    }
  },

  "core_systems": [
    {
      "class_name": "String (e.g., ObjectPool, SpatialGrid, AStarPathfinder)",
      "parent_class": "String (or null)",
      "is_singleton": "boolean",
      "description": "String (Low-level architectural or algorithmic systems)",
      "attributes": {
        "attr_name": "Type (e.g., 'dict', 'list', 'int')"
      },
      "methods": [
        {
          "name": "String",
          "params": ["self", "param_name: type"],
          "return_type": "String"
        }
      ]
    }
  ],

  "managers": [
    

      "class_name": "String (e.g., CollisionManager, DungeonManager, UIManager)",
      "parent_class": "String (or null)",
      "is_singleton": "boolean",
      "description": "String (Controllers that manage interactions between systems and entities)",
      "attributes": {
        "attr_name": "Type"
      },
      "methods": [
        {
          "name": "String",
          "params": ["self", "param_name: type"],
          "return_type": "String"
        }
      ]
    }
  ],

  "game_states": [
    {
      "class_name": "String (e.g., MainMenuState, PlayingState, GameOverState)",
      "parent_class": "String (e.g., State)",
      "description": "String (FSM states that control what is updated and drawn)",
      "attributes": {
        "attr_name": "Type"
      },
      "methods": [
        {
          "name": "enter",
          "params": ["self"],
          "return_type": "None"
        },
        {
          "name": "update",
          "params": ["self", "dt: float", "events: list"],
          "return_type": "None"
        },
        {
          "name": "draw",
          "params": ["self", "surface: pygame.Surface"],
          "return_type": "None"
        }
      ]
    }
  ],

  "entities": [
    {
      "class_name": "String (e.g., Player, BossProjectile, Wall, Button, HUD)",
      "parent_class": "String (e.g., GameSprite, pygame.sprite.Sprite)",
      "description": "String (Tangible objects or UI elements rendered on screen)",
      "attributes": {
        "attr_name": "Type"
      },
      "methods": [
        {
          "name": "__init__",
          "params": ["self", "*args", "**kwargs"],
          "return_type": "None"
        },
        {
          "name": "String",
          "params": ["self", "param_name: type"],
          "return_type": "String"
        }
      ]
    }
  ]
}
"""

# Safety Standards
safety_settings = [
    types.SafetySetting(category = "HARM_CATEGORY_HARASSMENT", threshold = "BLOCK_NONE"),
    types.SafetySetting(category = "HARM_CATEGORY_HATE_SPEECH", threshold = "BLOCK_NONE"),
    types.SafetySetting(category = "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold = "BLOCK_NONE"),
    types.SafetySetting(category = "HARM_CATEGORY_DANGEROUS_CONTENT", threshold = "BLOCK_NONE"),
]
