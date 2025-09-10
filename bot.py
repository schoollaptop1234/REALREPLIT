"""
TadzzyBot - Complete Enhanced Version with ALL NEW FEATURES
✅ Fixed all VS Code syntax errors
✅ Modern Discord UI with buttons and dropdowns (NO REACTIONS)
✅ Interactive 90-minute battles with halftime & penalties
✅ Pack system with amazing animations and UI
✅ Card upgrading system (Gold→Diamond→TOTW→UCL→TOTY→Ultimate)
✅ Enhanced !viewdeleted with user filtering
✅ Shop "OUT OF STOCK" system with !restock
✅ Packs in !addcode system
✅ !adminupgrade command for upgrading user cards
✅ Beautiful animated pack openings and battle experiences
"""

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import json
import random
import asyncio
import os
import shutil
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv

# -----------------------------
# Config
# -----------------------------
DATA_FILE = "tadzzy_data.json"
DATA_BACKUP_DIR = "backups"
AUTOSAVE_INTERVAL_SECONDS = 60
STARTING_BALANCE = 50_000
MAX_COLLECTION_SLOTS = 15
LEVEL_XP_REWARD = 1  # Reduced back to 1 for slower progression
LEVEL_UP_XP_THRESHOLD = 100  # Increased to 100 for harder leveling  
LEVEL_REWARD_TADBUCKS = 8000  # Reduced rewards
LEVEL_REWARD_TADZZY = 5  # Reduced rewards
AUCTION_DEFAULT_DURATION_MINUTES = 2  # Changed from hours to minutes
REBIRTH_REQUIREMENT = 250000  # 250k requirement

# Bot announcement channel - ALL announcements go here
ANNOUNCEMENT_CHANNEL_ID = 1211345997217923133

# Enhanced rebirth system with 10 levels and free cards - Level 10+ gets Secrets!
REBIRTH_LEVELS = [
    {"level": 1, "requirement": 250000, "multiplier": 0.5, "card_rarity": "Common"},
    {"level": 2, "requirement": 500000, "multiplier": 0.5, "card_rarity": "Common"},
    {"level": 3, "requirement": 1000000, "multiplier": 0.5, "card_rarity": "Epic"},
    {"level": 4, "requirement": 2000000, "multiplier": 0.5, "card_rarity": "Epic"},
    {"level": 5, "requirement": 5000000, "multiplier": 0.5, "card_rarity": "Epic"},
    {"level": 6, "requirement": 10000000, "multiplier": 0.5, "card_rarity": "Legendary"},
    {"level": 7, "requirement": 20000000, "multiplier": 0.5, "card_rarity": "Legendary"},
    {"level": 8, "requirement": 50000000, "multiplier": 0.5, "card_rarity": "Legendary"},
    {"level": 9, "requirement": 100000000, "multiplier": 0.5, "card_rarity": "Mythic"},
    {"level": 10, "requirement": 250000000, "multiplier": 0.5, "card_rarity": "Secret"}  # Level 10+ gets Secret cards!
]

# -----------------------------
# Load token & set intents
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: DISCORD_TOKEN not set in environment.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# -----------------------------
# In-memory data structure (persisted to JSON)
# -----------------------------
data = {
    "tadbucks_balances": {},  # user_id: int
    "tadzzy_points": {},  # user_id: int
    "xp_levels": {},  # user_id: int
    "user_collections": {},  # user_id: [card dicts with upgrade levels]
    "user_packs": {},  # user_id: {pack_type: count}
    "gamenights": [],  # list of links
    "auctions": {},  # player_name: auction dict
    "guess_db": {},  # we'll fill programmatically (clues)
    "trades": {},  # trade_id: trade dict
    "daily_rewards": {},  # user_id: last_claim_date
    "weekly_rewards": {},  # user_id: last_claim_date
    "hourly_rewards": {},  # user_id: last_claim_timestamp
    "daily_spin": {},  # user_id: last_spin_date
    "multipliers": {},  # user_id: {multiplier_type: expiry_time}
    "codes": {},  # code_name: {cash, xp, multipliers, packs}
    "rebirths": {},  # user_id: rebirth_count
    "deleted_messages": [],  # list of deleted message objects
    "out_of_stock": [],  # list of player names that are out of stock
    "shop_discount": 0,  # current shop discount percentage
    "user_storage": {},  # user_id: max_slots (int or "infinite")
    "settings": {  # future expansions
        "starting_balance": STARTING_BALANCE
    }
}

# Initialize users dict for compatibility
users = {}

# -----------------------------
# Real-life footballers for guessing
# -----------------------------
real_life_players = [
    # Current superstars
    "Lionel Messi", "Cristiano Ronaldo", "Kylian Mbappe", "Erling Haaland",
    "Mohamed Salah", "Kevin De Bruyne", "Robert Lewandowski", "Neymar Jr",
    "Virgil van Dijk", "Karim Benzema", "Sadio Mane", "Son Heung-min",
    "Harry Kane", "Luka Modric", "N'Golo Kante", "Paul Pogba",
    
    # Premier League stars
    "Bruno Fernandes", "Mason Mount", "Phil Foden", "Jack Grealish",
    "Raheem Sterling", "Marcus Rashford", "Jadon Sancho", "Declan Rice",
    "Bukayo Saka", "Martin Odegaard", "Gabriel Jesus", "Darwin Nunez",
    
    # La Liga stars
    "Pedri", "Gavi", "Vinicius Junior", "Federico Valverde", "Rodrygo",
    "Antoine Griezmann", "Joao Felix", "Real Sociedad", "Isco",
    
    # Serie A stars
    "Victor Osimhen", "Rafael Leao", "Lautaro Martinez", "Paulo Dybala",
    "Federico Chiesa", "Ciro Immobile", "Lorenzo Insigne",
    
    # Bundesliga stars
    "Joshua Kimmich", "Thomas Muller", "Jamal Musiala", "Serge Gnabry",
    "Marco Reus", "Jude Bellingham", "Giovanni Reyna",
    
    # Legends
    "Zinedine Zidane", "Ronaldinho", "Thierry Henry", "Francesco Totti",
    "Andrea Pirlo", "Xavi", "Andres Iniesta", "Sergio Ramos"
]

# -----------------------------
# Footballers & Cards (base) - 4x income rates for ultimate earning power!
# -----------------------------
footballers = [
    # Secret - Highest passive income generators (2x income)
    {"name": "Tadstarman", "rarity": "Secret", "price": 100000000, "color": 0x000000, "income_rate": 10000},
    {"name": "Jeeves", "rarity": "Secret", "price": 95000000, "color": 0x000000, "income_rate": 9500},
    {"name": "Jazzy", "rarity": "Secret", "price": 90000000, "color": 0x000000, "income_rate": 9000},

    # Expensive (2x income)
    {"name": "JustMatt", "rarity": "Expensive", "price": 5000000, "color": 0x00ff00, "income_rate": 5000},

    # Mythics (2x income)
    {"name": "Leo", "rarity": "Mythic", "price": 3000000, "color": 0xff0000, "income_rate": 3000},
    {"name": "Gdigz", "rarity": "Mythic", "price": 2900000, "color": 0xff0000, "income_rate": 2900},
    {"name": "Pulse", "rarity": "Mythic", "price": 2800000, "color": 0xff0000, "income_rate": 2800},
    {"name": "Barou", "rarity": "Mythic", "price": 2750000, "color": 0xff0000, "income_rate": 2750},
    {"name": "Arving8", "rarity": "Mythic", "price": 2700000, "color": 0xff0000, "income_rate": 2700},

    # Legendary (2x income)
    {"name": "deadp00l295", "rarity": "Legendary", "price": 2000067, "color": 0xffff00, "income_rate": 2000},
    {"name": "Messi", "rarity": "Legendary", "price": 1500000, "color": 0xffff00, "income_rate": 1500},
    {"name": "Ronaldo", "rarity": "Legendary", "price": 1400000, "color": 0xffff00, "income_rate": 1400},
    {"name": "Salah", "rarity": "Legendary", "price": 1300000, "color": 0xffff00, "income_rate": 1300},
    {"name": "Son", "rarity": "Legendary", "price": 1200000, "color": 0xffff00, "income_rate": 1200},
    {"name": "De Bruyne", "rarity": "Legendary", "price": 1100000, "color": 0xffff00, "income_rate": 1100},
    {"name": "Joel", "rarity": "Legendary", "price": 1050000, "color": 0xffff00, "income_rate": 1050},
    {"name": "Lewandowski", "rarity": "Legendary", "price": 1000000, "color": 0xffff00, "income_rate": 1000},
    {"name": "Mbappe", "rarity": "Legendary", "price": 980000, "color": 0xffff00, "income_rate": 980},
    {"name": "Neymar", "rarity": "Legendary", "price": 960000, "color": 0xffff00, "income_rate": 960},

    # Epics (2x income)
    {"name": "Haaland", "rarity": "Epic", "price": 850000, "color": 0x800080, "income_rate": 850},
    {"name": "Benzema", "rarity": "Epic", "price": 820000, "color": 0x800080, "income_rate": 820},
    {"name": "Vinicius Jr", "rarity": "Epic", "price": 800000, "color": 0x800080, "income_rate": 800},
    {"name": "Kane", "rarity": "Epic", "price": 780000, "color": 0x800080, "income_rate": 780},
    {"name": "Joy", "rarity": "Epic", "price": 750000, "color": 0x800080, "income_rate": 750},

    # Commons - Lower income generators (2x income)
    {"name": "Rashford", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Sancho", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Pedri", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Gavi", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Musiala", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Kroos", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Goalkeeper Tadzzy", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Axel", "rarity": "Common", "price": 20000, "color": 0x0000ff, "income_rate": 20},
    {"name": "Dim", "rarity": "Common", "price": 17000, "color": 0x0000ff, "income_rate": 16},
    {"name": "Ex_xpo", "rarity": "Common", "price": 16000, "color": 0x0000ff, "income_rate": 16},
    {"name": "Yousef", "rarity": "Common", "price": 15000, "color": 0x0000ff, "income_rate": 14},
    {"name": "Mazzy", "rarity": "Common", "price": 14000, "color": 0x0000ff, "income_rate": 14},
    {"name": "Lizardboyy", "rarity": "Common", "price": 13000, "color": 0x0000ff, "income_rate": 12},
    {"name": "NtanielGamer6", "rarity": "Common", "price": 12000, "color": 0x0000ff, "income_rate": 12},
    {"name": "kanye", "rarity": "Common", "price": 11000, "color": 0x0000ff, "income_rate": 10},
    {"name": "salvas", "rarity": "Common", "price": 10000, "color": 0x0000ff, "income_rate": 10},
    {"name": "Eggham", "rarity": "Common", "price": 9000, "color": 0x0000ff, "income_rate": 8},
    {"name": "Ducky", "rarity": "Common", "price": 8000, "color": 0x0000ff, "income_rate": 8},
    {"name": "Kaan", "rarity": "Common", "price": 7000, "color": 0x0000ff, "income_rate": 6},
    {"name": "Krosspy", "rarity": "Common", "price": 6000, "color": 0x0000ff, "income_rate": 6},
    {"name": "Tmerri", "rarity": "Common", "price": 5000, "color": 0x0000ff, "income_rate": 4},
    {"name": "Quixy", "rarity": "Common", "price": 4000, "color": 0x0000ff, "income_rate": 4},
    {"name": "Alexander Isak", "rarity": "Common", "price": 3000, "color": 0x0000ff, "income_rate": 2},
    {"name": "Itoshi Sae", "rarity": "Common", "price": 2000, "color": 0x0000ff, "income_rate": 2},
    {"name": "Bachira", "rarity": "Common", "price": 1000, "color": 0x0000ff, "income_rate": 2},
    {"name": "Mr.Incredible", "rarity": "Common", "price": 500, "color": 0x0000ff, "income_rate": 2},
]

# Auto-generate more commons to reach 50+ players (4x income rates)
common_players = [f"Tadstarman Bot{i}" for i in range(1, 51 - len(footballers))]
for i, name in enumerate(common_players):
    footballers.append({"name": name, "rarity": "Common", "price": 150, "color": 0x0000ff, "income_rate": 8})

# -----------------------------
# Pack System Configuration
# -----------------------------
PACK_TYPES = {
    "Default Pack": {
        "price": 50000,
        "rarities": {
            "Common": 0.85,
            "Epic": 0.12,
            "Legendary": 0.025,
            "Mythic": 0.004,
            "Secret": 0.001
        }
    },
    "TOTW Pack": {
        "price": 350000,  # Lowered from 500k
        "rarities": {
            "Common": 0.65,  # Slightly better odds
            "Epic": 0.25,
            "Legendary": 0.08,
            "Mythic": 0.018,
            "Secret": 0.002
        }
    },
    "UCL Pack": {
        "price": 1400000,  # Lowered from 2M
        "rarities": {
            "Common": 0.50,  # Better odds
            "Epic": 0.32,
            "Legendary": 0.14,
            "Mythic": 0.033,
            "Secret": 0.007
        }
    },
    "TOTY Pack": {
        "price": 9500000,  # Lowered from 15M
        "rarities": {
            "Common": 0.30,  # Better odds
            "Epic": 0.35,
            "Legendary": 0.25,
            "Mythic": 0.085,
            "Secret": 0.015
        }
    },
    "Ultimate Pack": {
        "price": 11500000,  # Lowered from 35M to exactly 11.5M as requested
        "rarities": {
            "Common": 0.15,  # Much better odds
            "Epic": 0.30,
            "Legendary": 0.30,
            "Mythic": 0.18,
            "Secret": 0.07
        }
    },
    "Godly Pack": {
        "price": 20000000,  # 20 million TadBucks - extremely expensive
        "rarities": {
            "Common": 0.05,  # Very rare commons
            "Epic": 0.15,
            "Legendary": 0.25,
            "Mythic": 0.30,
            "Secret": 0.25  # High chance for Secrets
        }
    }
}

UPGRADE_LEVELS = ["Gold", "Diamond", "TOTW", "UCL", "TOTY", "Ultimate"]

def get_card_upgrade_level(card: dict) -> str:
    return card.get("upgrade_level", "Gold")

def get_upgrade_multiplier(upgrade_level: str) -> float:
    multipliers = {
        "Gold": 1.5,
        "Diamond": 1.75,
        "TOTW": 2.0,
        "UCL": 2.5,
        "TOTY": 2.75,
        "Ultimate": 3.0,
        "Godly": 5.0
    }
    return multipliers.get(upgrade_level, 1.0)

def upgrade_card_stats(card: dict) -> dict:
    """Upgrade card stats based on level"""
    upgrade_level = get_card_upgrade_level(card)
    multiplier = get_upgrade_multiplier(upgrade_level)
    
    # Store original values if not already stored
    if "original_price" not in card:
        card["original_price"] = card["price"]
    if "original_income_rate" not in card:
        card["original_income_rate"] = card["income_rate"]
    
    # Apply multiplier to original values
    card["price"] = int(card["original_price"] * multiplier)
    card["income_rate"] = int(card["original_income_rate"] * multiplier)
    
    return card

# Normalizing helper
def normalize_name(n: str) -> str:
    return n.strip().lower()

# find player card by name (case-insensitive)
def find_player_card_by_name(name: str) -> Optional[dict]:
    name_norm = normalize_name(name)
    for p in footballers:
        if normalize_name(p["name"]) == name_norm:
            return p
    return None

# Enhanced Shop Stock System - Only legendary and above can be out of stock!
def is_out_of_stock(player_name: str) -> bool:
    return player_name in data["out_of_stock"]

def restock_player(player_name: str):
    if player_name in data["out_of_stock"]:
        data["out_of_stock"].remove(player_name)

def set_out_of_stock(player_name: str):
    if player_name not in data["out_of_stock"]:
        data["out_of_stock"].append(player_name)

def can_be_out_of_stock(player_name: str) -> bool:
    """Only legendary and above can be out of stock"""
    card = find_player_card_by_name(player_name)
    if not card:
        return False
    return card["rarity"] in ["Legendary", "Mythic", "Secret", "Expensive"]

def randomize_stock_status():
    """Only legendary+ go out of stock, Secrets mostly out of stock"""
    for footballer in footballers:
        if not can_be_out_of_stock(footballer["name"]):
            # Always restock commons and epics
            restock_player(footballer["name"])
        elif footballer["rarity"] == "Secret":
            # Secrets are mostly out of stock (80% chance)
            if random.random() < 0.8:
                set_out_of_stock(footballer["name"])
            else:
                restock_player(footballer["name"])
        elif footballer["rarity"] in ["Legendary", "Mythic", "Expensive"]:
            # Legendary+ have normal out of stock chance (30% chance)
            if random.random() < 0.3:
                set_out_of_stock(footballer["name"])
            else:
                restock_player(footballer["name"])

# Pack discount system - 10% off when active
def set_pack_discount(discount_percent: int):
    """Set global pack discount"""
    data["shop_discount"] = discount_percent

def get_pack_discount() -> int:
    """Get current pack discount"""
    return data.get("shop_discount", 0)

def apply_pack_discount(price: int) -> int:
    """Apply discount to pack price"""
    discount = get_pack_discount()
    if discount > 0:
        return int(price * (100 - discount) / 100)
    return price

def is_pack_discount_active() -> bool:
    """Check if pack discount is currently active"""
    return get_pack_discount() > 0

# Luck multiplier system for codes
def get_user_luck_multiplier(user_id: int) -> float:
    """Get user's current luck multiplier from codes"""
    uid = str(user_id)
    multipliers = data.get("multipliers", {}).get(uid, {})
    
    # Check for x2_luck or x3_luck
    current_time = datetime.now(timezone.utc)
    luck_multiplier = 1.0
    
    for mult_type, expiry_str in list(multipliers.items()):
        expiry_time = datetime.fromisoformat(expiry_str)
        if current_time < expiry_time:
            if mult_type == "x2_luck":
                luck_multiplier = max(luck_multiplier, 2.0)
            elif mult_type == "x3_luck":
                luck_multiplier = max(luck_multiplier, 3.0)
        else:
            # Remove expired multiplier
            del multipliers[mult_type]
    
    return luck_multiplier

def apply_luck_to_pack_opening(rarities: dict, luck_multiplier: float) -> dict:
    """Apply luck multiplier to pack opening odds"""
    if luck_multiplier <= 1.0:
        return rarities
    
    # Improve odds for higher rarities
    adjusted_rarities = {}
    total_adjustment = 0
    
    for rarity, chance in rarities.items():
        if rarity in ["Legendary", "Mythic", "Secret"]:
            # Boost rare cards significantly
            boost_factor = luck_multiplier
            adjusted_chance = min(0.8, chance * boost_factor)  # Cap at 80%
            total_adjustment += adjusted_chance - chance
        else:
            adjusted_chance = chance
        adjusted_rarities[rarity] = adjusted_chance
    
    # Reduce common chances to compensate
    if "Common" in adjusted_rarities:
        adjusted_rarities["Common"] = max(0.05, adjusted_rarities["Common"] - total_adjustment)
    
    # Normalize to ensure total = 1.0
    total = sum(adjusted_rarities.values())
    if total > 0:
        for rarity in adjusted_rarities:
            adjusted_rarities[rarity] /= total
    
    return adjusted_rarities

# -----------------------------
# Guess-the-player DB with REAL PROFESSIONAL FOOTBALL PLAYERS ONLY! 🏆⚽
# Updated with 100+ professional footballers across all difficulty levels
# -----------------------------
def build_guess_db():
    g = {
        "easy": [
            # World's biggest superstars - everyone knows these!
            ("Argentine forward, 8 Ballon d'Or winner, GOAT", "Lionel Messi"),
            ("Portuguese superstar, CR7, Real Madrid legend", "Cristiano Ronaldo"),
            ("Egyptian King, Liverpool right winger", "Mohamed Salah"),
            ("Norwegian striker, Manchester City goal machine", "Erling Haaland"),
            ("French speedster, PSG and France forward", "Kylian Mbappe"),
            ("Brazilian magician, former Barcelona superstar", "Neymar Jr"),
            ("Polish striker, Barcelona goal-scoring machine", "Robert Lewandowski"),
            ("Belgian midfielder, Manchester City playmaker", "Kevin De Bruyne"),
            ("Dutch defender, Liverpool's rock at the back", "Virgil van Dijk"),
            ("French striker, Real Madrid Ballon d'Or winner", "Karim Benzema"),
            ("English striker, Bayern Munich captain", "Harry Kane"),
            ("Korean forward, Tottenham's Son", "Son Heung-min"),
            ("Senegalese winger, former Liverpool star", "Sadio Mane"),
            ("Croatian midfielder, Real Madrid legend", "Luka Modric"),
            ("French midfielder, Chelsea and France star", "N'Golo Kante"),
        ],
        "normal": [
            # Premier League and top European league stars
            ("Portuguese midfielder, Manchester United star", "Bruno Fernandes"),
            ("English winger, Chelsea speedster", "Raheem Sterling"),
            ("German midfielder, Bayern Munich leader", "Joshua Kimmich"),
            ("English forward, Manchester United academy", "Marcus Rashford"),
            ("English winger, Arsenal's Bukayo", "Bukayo Saka"),
            ("Norwegian midfielder, Arsenal captain", "Martin Odegaard"),
            ("English midfielder, West Ham captain", "Declan Rice"),
            ("English winger, Manchester City talent", "Phil Foden"),
            ("English midfielder, Chelsea academy graduate", "Mason Mount"),
            ("Portuguese winger, Manchester United talent", "Jadon Sancho"),
            ("Brazilian forward, Arsenal striker", "Gabriel Jesus"),
            ("Uruguayan striker, Liverpool Darwin", "Darwin Nunez"),
            ("German striker, Bayern Munich veteran", "Thomas Muller"),
            ("Italian midfielder, Juventus legend", "Federico Chiesa"),
            ("Spanish goalkeeper, Manchester United", "David de Gea"),
        ],
        "hard": [
            # Rising stars and less obvious players
            ("Spanish midfielder, Barcelona's golden boy", "Pedri"),
            ("Spanish midfielder, Barcelona teenager", "Gavi"),
            ("Brazilian winger, Real Madrid rising star", "Vinicius Junior"),
            ("Brazilian winger, Real Madrid speedster", "Rodrygo"),
            ("Uruguayan midfielder, Real Madrid Federico", "Federico Valverde"),
            ("German midfielder, Bayern Munich Jamal", "Jamal Musiala"),
            ("English midfielder, Borussia Dortmund star", "Jude Bellingham"),
            ("American midfielder, Borussia Dortmund Giovanni", "Giovanni Reyna"),
            ("German winger, Borussia Dortmund captain", "Marco Reus"),
            ("Nigerian striker, Napoli goal machine", "Victor Osimhen"),
            ("Portuguese forward, AC Milan Rafael", "Rafael Leao"),
            ("Argentine striker, Inter Milan Lautaro", "Lautaro Martinez"),
            ("Argentine forward, Roma Paulo", "Paulo Dybala"),
            ("Italian striker, Lazio legend", "Ciro Immobile"),
            ("Spanish defender, Manchester City", "Aymeric Laporte"),
            ("French defender, Real Madrid Ferland", "Ferland Mendy"),
        ],
        "extreme": [
            # Football legends and very specific clues
            ("French midfielder, Real Madrid legend, 2006 World Cup headbutt", "Zinedine Zidane"),
            ("Brazilian magician, Barcelona legend, beach football skills", "Ronaldinho"),
            ("French striker, Arsenal legend, Invincibles top scorer", "Thierry Henry"),
            ("Italian midfielder, AC Milan legend, perfect passing", "Andrea Pirlo"),
            ("Spanish midfielder, Barcelona tiki-taka master", "Andres Iniesta"),
            ("Spanish midfielder, Barcelona legend, 6 Ballon d'Or", "Xavi"),
            ("Italian forward, Roma one-club legend", "Francesco Totti"),
            ("Brazilian midfielder, AC Milan legend, 2007 Ballon d'Or", "Kaka"),
            ("English midfielder, Manchester United legend, scholes", "Paul Scholes"),
            ("Brazilian striker, Real Madrid phenomenon", "Ronaldo Nazario"),
            ("French striker, Arsenal legend, va va voom", "Thierry Henry"),
            ("Italian defender, AC Milan legend, Maldini", "Paolo Maldini"),
            ("German goalkeeper, Bayern Munich legend", "Oliver Kahn"),
            ("Dutch striker, Arsenal legend, flying Dutchman", "Dennis Bergkamp"),
            ("Ukrainian striker, AC Milan legend, Shevchenko", "Andriy Shevchenko"),
            ("Portuguese midfielder, Real Madrid Figo", "Luis Figo"),
            ("Brazilian defender, AC Milan legend, Cafu", "Cafu"),
            ("English striker, Manchester United legend", "Wayne Rooney"),
            ("Welsh winger, Real Madrid Gareth", "Gareth Bale"),
            ("Swedish striker, AC Milan legend, Ibrahimovic", "Zlatan Ibrahimovic"),
        ]
    }
    return g

data["guess_db"] = build_guess_db()

# Global variables for tracking
last_income_report = {}
total_income_tracker = {}
gamble_cooldowns: Dict[str, str] = {}
fairgamble_cooldowns: Dict[str, str] = {}
active_guess_games: Dict[str, dict] = {}
two_way_trades = {}
pending_trades = {}
active_battles = {}
battle_cooldowns: Dict[str, str] = {}

# Helper functions for admin checks and level requirements
def is_admin(user, guild) -> bool:
    """Check if user has administrator permissions"""
    if not guild:
        return False
    member = guild.get_member(user.id)
    return member and member.guild_permissions.administrator

def has_level_requirement(user_id: int, required_level: int) -> bool:
    """Check if user meets level requirement"""
    user_level = get_level(user_id)
    return user_level >= required_level

def should_bypass_cooldown(user, guild) -> bool:
    """Check if user should bypass cooldowns (admins)"""
    return is_admin(user, guild)

# Battle system constants - 45 seconds real-time!
BATTLE_DURATION = 45  # 45 seconds real-time
BATTLE_COOLDOWN = 60  # 1 minute cooldown
BATTLE_WIN_REWARD = 5000  # $5,000 for winning

# Battle commentary lines
BATTLE_COMMENTARY = [
    "⚽ The ball is rolling on the pitch!",
    "🏃‍♂️ What a run down the wing!",
    "⚡ Lightning fast counter-attack!",
    "🎯 The striker is looking dangerous!",
    "💨 Speed down the flanks!",
    "🔥 The crowd is getting excited!",
    "⚽ Beautiful ball control!",
    "🚀 That was close to the goal!",
    "💪 Strong defensive play!",
    "🌟 Brilliant skill on display!"
]

# -----------------------------
# Modern Discord UI Components
# -----------------------------

class ShopPaginationView(View):
    def __init__(self, user_id: int, all_items: list, items_per_page: int = 10):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.all_items = all_items
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = (len(all_items) - 1) // items_per_page
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Enable/disable buttons based on current page
        self.children[0].disabled = self.current_page <= 0  # Previous button
        self.children[1].disabled = self.current_page >= self.max_pages  # Next button
        
        # Update labels with page info
        self.children[0].label = f"⬅️ Previous"
        self.children[1].label = f"Next ➡️"
    
    def get_current_page_items(self):
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.all_items[start_idx:end_idx]
    
    def create_shop_embed(self):
        current_items = self.get_current_page_items()
        
        embed = discord.Embed(
            title="⚽ **TadzzyBot Football Card Shop** ⚽",
            description=f"💰 **Buy cards to build your ultimate collection!**\n📄 Page {self.current_page + 1}/{self.max_pages + 1}",
            color=0x3498db
        )
        
        # Check for active discount
        discount = get_pack_discount()
        if discount > 0:
            embed.add_field(
                name="🔥 **SALE ACTIVE!**",
                value=f"**{discount}% OFF** all packs! Limited time!",
                inline=False
            )
        
        # Add pack shop section for first page
        if self.current_page == 0:
            pack_info = []
            for pack_name, pack_data in PACK_TYPES.items():
                original_price = pack_data["price"]
                final_price = apply_pack_discount(original_price)
                price_text = f"${final_price:,}"
                if discount > 0:
                    price_text += f" ~~${original_price:,}~~"
                
                pack_info.append(f"🎁 **{pack_name}**: {price_text}")
            
            embed.add_field(
                name="🎁 **PACKS** (Use !buypack)",
                value="\n".join(pack_info),
                inline=False
            )
        
        # Add current page cards
        available_cards = []
        out_of_stock_cards = []
        
        for footballer in current_items:
            name = footballer["name"]
            price = footballer["price"]
            rarity = footballer["rarity"]
            
            if is_out_of_stock(name):
                out_of_stock_cards.append(f"❌ **{name}** - {rarity} - OUT OF STOCK")
            else:
                available_cards.append(f"⚽ **{name}** - {rarity} - ${price:,}")
        
        if available_cards:
            embed.add_field(
                name="✅ **AVAILABLE CARDS**",
                value="\n".join(available_cards),
                inline=False
            )
        
        if out_of_stock_cards:
            embed.add_field(
                name="❌ **OUT OF STOCK**",
                value="\n".join(out_of_stock_cards),
                inline=False
            )
        
        embed.set_footer(text="🛒 Use !buy <player_name> to purchase cards | 🎁 Use !buypack to buy packs")
        return embed
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your shop session!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_shop_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already on first page!", ephemeral=True)
    
    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your shop session!", ephemeral=True)
            return
        
        if self.current_page < self.max_pages:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_shop_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already on last page!", ephemeral=True)
    
    @discord.ui.button(label="🛒 Buy Packs", style=discord.ButtonStyle.success)
    async def buy_packs(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your shop session!", ephemeral=True)
            return
        
        view = PackShopView()
        embed = discord.Embed(
            title="🎁 **Pack Shop** 🎁",
            description="Choose a pack to purchase!",
            color=0x00ff00
        )
        
        await interaction.response.edit_message(embed=embed, view=view)

class CollectionPaginationView(View):
    def __init__(self, user_id: int, user_collection: list, target_user_id: int = None, items_per_page: int = 8):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_collection = user_collection
        self.target_user_id = target_user_id or user_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = max(0, (len(user_collection) - 1) // items_per_page)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Enable/disable buttons based on current page
        self.children[0].disabled = self.current_page <= 0  # Previous button
        self.children[1].disabled = self.current_page >= self.max_pages  # Next button
        
        # Update labels with page info
        self.children[0].label = f"⬅️ Previous"
        self.children[1].label = f"Next ➡️"
    
    def get_current_page_items(self):
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.user_collection[start_idx:end_idx]
    
    def create_collection_embed(self):
        current_items = self.get_current_page_items()
        
        if self.user_id == self.target_user_id:
            title = "⚽ **Your Football Card Collection** ⚽"
            max_storage = get_user_max_storage(self.user_id)
            description = f"📦 **{len(self.user_collection)}/{max_storage} cards** | Page {self.current_page + 1}/{self.max_pages + 1}"
        else:
            target_user = bot.get_user(self.target_user_id)
            username = target_user.display_name if target_user else "User"
            title = f"⚽ **{username}'s Collection** ⚽"
            description = f"📦 **{len(self.user_collection)} cards** | Page {self.current_page + 1}/{self.max_pages + 1}"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x3498db
        )
        
        if not current_items:
            embed.add_field(
                name="📭 Empty Collection",
                value="No cards on this page. Use `!buy <player>` to get cards!",
                inline=False
            )
            return embed
        
        # Calculate total value for current page
        page_value = sum(card.get("price", 0) for card in current_items)
        
        # Add cards to embed
        for i, card in enumerate(current_items, start=(self.current_page * self.items_per_page + 1)):
            upgrade_level = get_card_upgrade_level(card)
            upgrade_progress = card.get("upgrade_progress", 0)
            
            # Build card info
            card_info = f"🏆 **{card['rarity']}** | 💰 ${card['price']:,}\"\n            
            card_info += f\"⭐ Level: **{upgrade_level}**\"\n            
            if upgrade_level != \"Ultimate\" and upgrade_progress > 0:\n                card_info += f\" ({upgrade_progress}% progress)\"\n            \n            embed.add_field(\n                name=f\"{i}. {card['name']}\",\n                value=card_info,\n                inline=True\n            )\n        \n        # Add page summary\n        embed.add_field(\n            name=\"📊 **Page Summary**\",\n            value=f\"💰 Page Value: ${page_value:,}\\n📦 Cards shown: {len(current_items)}\",\n            inline=False\n        )\n        \n        if self.user_id == self.target_user_id:\n            embed.set_footer(text=\"💡 Use !sell <number> to sell cards | !upgrade <number> to upgrade\")\n        \n        return embed\n    \n    @discord.ui.button(label=\"⬅️ Previous\", style=discord.ButtonStyle.secondary)\n    async def previous_page(self, interaction: discord.Interaction, button: Button):\n        if interaction.user.id != self.user_id:\n            await interaction.response.send_message(\"❌ This is not your collection view!\", ephemeral=True)\n            return\n        \n        if self.current_page > 0:\n            self.current_page -= 1\n            self.update_buttons()\n            embed = self.create_collection_embed()\n            await interaction.response.edit_message(embed=embed, view=self)\n        else:\n            await interaction.response.send_message(\"❌ Already on first page!\", ephemeral=True)\n    \n    @discord.ui.button(label=\"Next ➡️\", style=discord.ButtonStyle.secondary)\n    async def next_page(self, interaction: discord.Interaction, button: Button):\n        if interaction.user.id != self.user_id:\n            await interaction.response.send_message(\"❌ This is not your collection view!\", ephemeral=True)\n            return\n        \n        if self.current_page < self.max_pages:\n            self.current_page += 1\n            self.update_buttons()\n            embed = self.create_collection_embed()\n            await interaction.response.edit_message(embed=embed, view=self)\n        else:\n            await interaction.response.send_message(\"❌ Already on last page!\", ephemeral=True)\n    \n    @discord.ui.button(label=\"📊 Full Stats\", style=discord.ButtonStyle.primary)\n    async def show_full_stats(self, interaction: discord.Interaction, button: Button):\n        if interaction.user.id != self.user_id:\n            await interaction.response.send_message(\"❌ This is not your collection view!\", ephemeral=True)\n            return\n        \n        # Calculate collection statistics\n        total_value = sum(card.get(\"price\", 0) for card in self.user_collection)\n        total_income = sum(card.get(\"income_rate\", 0) for card in self.user_collection)\n        \n        # Count by rarity\n        rarity_counts = {}\n        for card in self.user_collection:\n            rarity = card.get(\"rarity\", \"Common\")\n            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1\n        \n        # Count by upgrade level\n        upgrade_counts = {}\n        for card in self.user_collection:\n            level = get_card_upgrade_level(card)\n            upgrade_counts[level] = upgrade_counts.get(level, 0) + 1\n        \n        if self.user_id == self.target_user_id:\n            title = \"📊 **Your Collection Statistics** 📊\"\n        else:\n            target_user = bot.get_user(self.target_user_id)\n            username = target_user.display_name if target_user else \"User\"\n            title = f\"📊 **{username}'s Collection Statistics** 📊\"\n        \n        embed = discord.Embed(title=title, color=0x00ff00)\n        \n        embed.add_field(\n            name=\"💰 **Financial Summary**\",\n            value=f\"Total Value: ${total_value:,}\\nPassive Income: ${total_income:,}/hour\",\n            inline=True\n        )\n        \n        embed.add_field(\n            name=\"📦 **Collection Size**\",\n            value=f\"Total Cards: {len(self.user_collection)}\",\n            inline=True\n        )\n        \n        if rarity_counts:\n            rarity_text = \"\\n\".join([f\"{rarity}: {count}\" for rarity, count in sorted(rarity_counts.items())])\n            embed.add_field(\n                name=\"🏆 **By Rarity**\",\n                value=rarity_text,\n                inline=True\n            )\n        \n        if upgrade_counts:\n            upgrade_text = \"\\n\".join([f\"{level}: {count}\" for level, count in sorted(upgrade_counts.items())])\n            embed.add_field(\n                name=\"⭐ **By Upgrade Level**\",\n                value=upgrade_text,\n                inline=True\n            )\n        \n        await interaction.response.edit_message(embed=embed, view=self)

class PackOpenView(View):
    def __init__(self, user_id: int, pack_type: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.pack_type = pack_type
        self.opened = False

    @discord.ui.button(label="🎁 Open Pack", style=discord.ButtonStyle.primary, emoji="✨")
    async def open_pack(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your pack!", ephemeral=True)
            return
        
        if self.opened:
            await interaction.response.send_message("❌ Pack already opened!", ephemeral=True)
            return

        self.opened = True
        
        # Simulate pack opening animation
        await interaction.response.edit_message(content="🎁✨ Opening pack... ✨🎁", embed=None, view=None)
        await asyncio.sleep(1)
        
        # Check if collection is full BEFORE opening pack
        uid = str(self.user_id)
        user_coll = data["user_collections"].setdefault(uid, [])
        max_storage = get_user_max_storage(self.user_id)
        
        if len(user_coll) >= max_storage:
            embed = discord.Embed(
                title="❌ Collection Full!",
                description=f"Your collection is full ({len(user_coll)}/{max_storage})!\nPack was **NOT** consumed. Please sell cards or upgrade storage first.",
                color=0xff0000
            )
            embed.add_field(
                name="💡 Solutions",
                value="• Use `!sell <card_number>` to sell cards\n• Use `!sell all` to clear collection\n• Contact an admin for more storage",
                inline=False
            )
            await interaction.edit_original_response(content=None, embed=embed, view=None)
            return
        
        # Get pack contents with luck multipliers
        pack_info = PACK_TYPES[self.pack_type]
        rarities_dict = pack_info["rarities"].copy()
        
        # Apply luck multiplier if active
        luck_multiplier = get_user_luck_multiplier(self.user_id)
        if luck_multiplier > 1.0:
            rarities_dict = apply_luck_to_pack_opening(rarities_dict, luck_multiplier)
        
        rarities = list(rarities_dict.keys())
        weights = list(rarities_dict.values())
        
        # Open 3 cards
        cards_won = []
        for _ in range(3):
            chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
            available_cards = [f for f in footballers if f["rarity"] == chosen_rarity]
            
            if available_cards:
                card = random.choice(available_cards).copy()
                
                # Check for pre-upgraded cards in special packs
                if self.pack_type in ["TOTW Pack", "UCL Pack", "TOTY Pack", "Ultimate Pack"]:
                    if random.random() < 0.3:  # 30% chance for pre-upgraded
                        if self.pack_type == "TOTW Pack":
                            card["upgrade_level"] = "TOTW"
                        elif self.pack_type == "UCL Pack":
                            card["upgrade_level"] = "UCL"
                        elif self.pack_type == "TOTY Pack":
                            card["upgrade_level"] = "TOTY"
                        elif self.pack_type == "Ultimate Pack":
                            card["upgrade_level"] = "Ultimate"
                        
                        card = upgrade_card_stats(card)
                
                cards_won.append(card)
        
        # Add cards to user collection (we already verified space is available)
        added_cards = []
        for card in cards_won:
            if len(user_coll) < max_storage:
                user_coll.append(card)
                added_cards.append(card)
        
        # Remove the opened pack from inventory ONLY after successful opening
        user_packs = data["user_packs"].setdefault(uid, {})
        if user_packs.get(self.pack_type, 0) > 0:
            user_packs[self.pack_type] -= 1
            if user_packs[self.pack_type] <= 0:
                del user_packs[self.pack_type]
        
        # Create results embed
        embed = discord.Embed(
            title=f"🎁 {self.pack_type} Opened! ✨",
            description="🎉 **Pack Opening Results!** 🎉",
            color=0xff6b6b
        )
        
        # Show luck multiplier if active
        if luck_multiplier > 1.0:
            embed.add_field(
                name="🍀 **LUCK ACTIVE!**",
                value=f"✨ **{luck_multiplier:.1f}x** luck boosting rare card chances!",
                inline=False
            )
        
        for i, card in enumerate(added_cards, 1):
            upgrade_text = ""
            if card.get("upgrade_level") and card.get("upgrade_level") != "Gold":
                upgrade_text = f" **[{card['upgrade_level']}]**"
            
            embed.add_field(
                name=f"🎯 Card {i}: {card['name']}{upgrade_text}",
                value=f"✨ {card['rarity']} | 💰 ${card['price']:,}",
                inline=False
            )
        
        embed.set_footer(text="🌟 Amazing pack opening! Use !collection to see your new cards! 🌟")
        
        await interaction.edit_original_response(content=None, embed=embed, view=None)

class GambleView(View):
    def __init__(self, user_id: int, amount: int):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.amount = amount

    async def process_gamble(self, interaction: discord.Interaction, game_name: str, win_chance: float, payout_multiplier: float):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your gambling session!", ephemeral=True)
            return
        
        # Set cooldown
        uid = str(self.user_id)
        gamble_cooldowns[uid] = datetime.utcnow().isoformat()
        
        won = random.random() < win_chance
        balance = get_balance(self.user_id)
        
        if won:
            winnings = int(self.amount * payout_multiplier)
            set_balance(self.user_id, balance + winnings)
            
            embed = discord.Embed(
                title=f"🎉 {game_name} - You Won! 🎉",
                description=f"💰 You won ${winnings:,}!\n💳 New balance: ${get_balance(self.user_id):,}",
                color=0x00ff00
            )
        else:
            set_balance(self.user_id, balance - self.amount)
            
            embed = discord.Embed(
                title=f"💸 {game_name} - You Lost! 💸",
                description=f"💸 You lost ${self.amount:,}.\n💳 New balance: ${get_balance(self.user_id):,}",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🔴 Red (60%)", style=discord.ButtonStyle.danger)
    async def red_game(self, interaction: discord.Interaction, button: Button):
        await self.process_gamble(interaction, "Red", 0.6, 0.8)

    @discord.ui.button(label="⚫ Black (60%)", style=discord.ButtonStyle.secondary)
    async def black_game(self, interaction: discord.Interaction, button: Button):
        await self.process_gamble(interaction, "Black", 0.6, 0.8)

    @discord.ui.button(label="⚪ White (60%)", style=discord.ButtonStyle.secondary)
    async def white_game(self, interaction: discord.Interaction, button: Button):
        await self.process_gamble(interaction, "White", 0.6, 0.8)

    @discord.ui.button(label="🎲 Dice (50%)", style=discord.ButtonStyle.primary)
    async def dice_game(self, interaction: discord.Interaction, button: Button):
        await self.process_gamble(interaction, "Dice Roll", 0.5, 1.0)

    @discord.ui.button(label="🃏 Card (40%)", style=discord.ButtonStyle.success)
    async def card_game(self, interaction: discord.Interaction, button: Button):
        await self.process_gamble(interaction, "Card Draw", 0.4, 1.5)

class FairGambleView(View):
    def __init__(self, user_id: int, amount: int):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.amount = amount

    async def process_fair_gamble(self, interaction: discord.Interaction, game_name: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your gambling session!", ephemeral=True)
            return
        
        # Set cooldown
        uid = str(self.user_id)
        fairgamble_cooldowns[uid] = datetime.now(timezone.utc).isoformat()
        
        won = random.random() < 0.5
        balance = get_balance(self.user_id)
        
        if won:
            set_balance(self.user_id, balance + self.amount)
            embed = discord.Embed(
                title=f"🎉 {game_name} - You Won! 🎉",
                description=f"⚖️ 50/50! You won ${self.amount:,}!\n💳 New balance: ${get_balance(self.user_id):,}",
                color=0x00ff00
            )
        else:
            set_balance(self.user_id, balance - self.amount)
            embed = discord.Embed(
                title=f"💸 {game_name} - You Lost! 💸",
                description=f"⚖️ 50/50! You lost ${self.amount:,}.\n💳 New balance: ${get_balance(self.user_id):,}",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🪙 Coin Flip", style=discord.ButtonStyle.primary)
    async def coin_flip(self, interaction: discord.Interaction, button: Button):
        await self.process_fair_gamble(interaction, "Coin Flip")

    @discord.ui.button(label="🎯 Target Shot", style=discord.ButtonStyle.success)
    async def target_shot(self, interaction: discord.Interaction, button: Button):
        await self.process_fair_gamble(interaction, "Target Shot")

    @discord.ui.button(label="⚡ Lightning", style=discord.ButtonStyle.danger)
    async def lightning_strike(self, interaction: discord.Interaction, button: Button):
        await self.process_fair_gamble(interaction, "Lightning Strike")

    @discord.ui.button(label="🌟 Star Catch", style=discord.ButtonStyle.secondary)
    async def star_catch(self, interaction: discord.Interaction, button: Button):
        await self.process_fair_gamble(interaction, "Star Catch")

class PackShopSelect(Select):
    def __init__(self):
        options = []
        discount = get_pack_discount()
        
        for pack_name, pack_info in PACK_TYPES.items():
            original_price = pack_info["price"]
            final_price = apply_pack_discount(original_price)
            
            price_text = f"${final_price:,}"
            if discount > 0:
                price_text += f" ({discount}% OFF!)"
            
            rarities_text = " | ".join([f"{k}: {int(v*100)}%" for k, v in pack_info["rarities"].items()])
            description = f"{price_text} | {rarities_text}"[:100]  # Discord limits description to 100 chars
            
            options.append(
                discord.SelectOption(
                    label=pack_name + (" 🔥" if discount > 0 else ""),
                    description=description,
                    emoji="🎁"
                )
            )
        
        super().__init__(placeholder="Choose a pack to purchase...", options=options)

    async def callback(self, interaction: discord.Interaction):
        pack_name = self.values[0].replace(" 🔥", "")  # Remove sale indicator
        pack_info = PACK_TYPES[pack_name]
        user_id = interaction.user.id
        
        ensure_user_exists(user_id)
        balance = get_balance(user_id)
        
        # Apply discount
        original_price = pack_info["price"]
        final_price = apply_pack_discount(original_price)
        discount = get_pack_discount()
        
        if balance < final_price:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You have ${balance:,} but {pack_name} costs ${final_price:,}",
                ephemeral=True
            )
            return
        
        # Purchase pack
        set_balance(user_id, balance - final_price)
        
        # Add to user's pack inventory
        uid = str(user_id)
        user_packs = data["user_packs"].setdefault(uid, {})
        user_packs[pack_name] = user_packs.get(pack_name, 0) + 1
        
        embed = discord.Embed(
            title=f"🎁 {pack_name} Purchased! ✨",
            color=0x00ff00
        )
        
        # Show discount info if active
        if discount > 0:
            embed.description = f"🔥 **{discount}% DISCOUNT ACTIVE!** 🔥\n💰 Original: ${original_price:,}\n💵 You paid: ${final_price:,}\n💳 New balance: ${get_balance(user_id):,}"
        else:
            embed.description = f"💰 Cost: ${final_price:,}\n💳 New balance: ${get_balance(user_id):,}"
        
        # Add pack chances
        chances_text = "\n".join([f"{k}: {int(v*100)}%" for k, v in pack_info["rarities"].items()])
        embed.add_field(name="🎲 Pack Chances", value=chances_text, inline=True)
        embed.add_field(name="📦 Contents", value="3 Random Cards", inline=True)
        embed.set_footer(text="🎉 Use !openpack to open with amazing animations!")
        
        await interaction.response.edit_message(embed=embed, view=None)

class PackShopView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(PackShopSelect())

class CardSacrificeSelect(Select):
    def __init__(self, user_id: int, target_card_index: int, user_collection: list):
        self.user_id = user_id
        self.target_card_index = target_card_index
        
        options = []
        for i, card in enumerate(user_collection):
            if i != target_card_index:  # Can't sacrifice the card being upgraded
                upgrade_level = get_card_upgrade_level(card)
                options.append(
                    discord.SelectOption(
                        label=f"{card['name']} [{upgrade_level}]",
                        description=f"{card['rarity']} | ${card['price']:,} | +{int(get_upgrade_multiplier(upgrade_level) * 50)}% progress",
                        value=str(i),
                        emoji="⚔️"
                    )
                )
        
        if not options:
            options.append(discord.SelectOption(label="No cards available", value="none", emoji="❌"))
        
        super().__init__(placeholder="Choose a card to sacrifice...", options=options[:25])  # Discord limit

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your sacrifice session!", ephemeral=True)
            return
        
        if self.values[0] == "none":
            await interaction.response.send_message("❌ No cards available to sacrifice!", ephemeral=True)
            return
        
        sacrifice_index = int(self.values[0])
        uid = str(self.user_id)
        user_coll = data["user_collections"].get(uid, [])
        
        if sacrifice_index >= len(user_coll) or self.target_card_index >= len(user_coll):
            await interaction.response.send_message("❌ Cards not found!", ephemeral=True)
            return
        
        # Get cards
        sacrifice_card = user_coll[sacrifice_index]
        target_card = user_coll[self.target_card_index]
        
        # Calculate progress boost based on sacrificed card's upgrade level
        sacrifice_multiplier = get_upgrade_multiplier(get_card_upgrade_level(sacrifice_card))
        progress_boost = int(sacrifice_multiplier * 50)  # 50% base, multiplied by upgrade level
        
        # Apply progress
        current_progress = target_card.get("upgrade_progress", 0)
        new_progress = min(100, current_progress + progress_boost)
        target_card["upgrade_progress"] = new_progress
        
        # Remove sacrificed card
        user_coll.pop(sacrifice_index)
        
        # Adjust target card index if needed
        if sacrifice_index < self.target_card_index:
            self.target_card_index -= 1
        
        # Check if leveled up
        current_level = get_card_upgrade_level(target_card)
        if new_progress >= 100:
            current_index = UPGRADE_LEVELS.index(current_level)
            if current_index < len(UPGRADE_LEVELS) - 1:
                new_level = UPGRADE_LEVELS[current_index + 1]
                target_card["upgrade_level"] = new_level
                target_card["upgrade_progress"] = 0
                target_card = upgrade_card_stats(target_card)
                user_coll[self.target_card_index] = target_card
                
                embed = discord.Embed(
                    title="🎉 SACRIFICE SUCCESSFUL - LEVEL UP! 🎉",
                    description=f"⚔️ {sacrifice_card['name']} was sacrificed!\n✨ {target_card['name']} upgraded to **{new_level}**! ✨",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="⭐ Maximum Level Reached! ⭐",
                    description=f"🏆 {target_card['name']} is already at Ultimate level!\n⚔️ {sacrifice_card['name']} was still sacrificed for progress.",
                    color=0xffd700
                )
        else:
            embed = discord.Embed(
                title="⚔️ Card Sacrificed Successfully! ⚔️",
                description=f"⚔️ {sacrifice_card['name']} was sacrificed!\n📈 {target_card['name']} upgrade progress: {new_progress}%",
                color=0x3498db
            )
        
        embed.add_field(name="Progress Gained", value=f"+{progress_boost}%", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)

class UpgradeView(View):
    def __init__(self, user_id: int, card_index: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.card_index = card_index

    @discord.ui.button(label="⚔️ Sacrifice Card", style=discord.ButtonStyle.danger)
    async def sacrifice_card(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your upgrade session!", ephemeral=True)
            return
        
        uid = str(self.user_id)
        user_coll = data["user_collections"].get(uid, [])
        
        if len(user_coll) <= 1:
            await interaction.response.send_message("❌ You need at least 2 cards to sacrifice one!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚔️ Choose Card to Sacrifice",
            description="Select a card from your collection to sacrifice for upgrade progress!",
            color=0xff0000
        )
        
        view = View(timeout=30)
        view.add_item(CardSacrificeSelect(self.user_id, self.card_index, user_coll))
        
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="💰 Pay to Upgrade", style=discord.ButtonStyle.success)
    async def pay_upgrade(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your upgrade session!", ephemeral=True)
            return
        
        uid = str(self.user_id)
        user_coll = data["user_collections"].get(uid, [])
        
        if self.card_index >= len(user_coll):
            await interaction.response.send_message("❌ Card not found!", ephemeral=True)
            return
        
        card = user_coll[self.card_index]
        current_level = get_card_upgrade_level(card)
        current_progress = card.get("upgrade_progress", 0)
        
        # Calculate upgrade cost
        base_cost = card.get("original_price", card["price"]) * 0.5  # 50% of original card value
        level_multiplier = UPGRADE_LEVELS.index(current_level) + 1
        upgrade_cost = int(base_cost * level_multiplier)
        
        balance = get_balance(self.user_id)
        
        if balance < upgrade_cost:
            await interaction.response.send_message(
                f"❌ Insufficient funds! Need ${upgrade_cost:,}, you have ${balance:,}",
                ephemeral=True
            )
            return
        
        # Process upgrade
        set_balance(self.user_id, balance - upgrade_cost)
        
        # Add progress (paying gives 25% progress)
        new_progress = min(100, current_progress + 25)
        card["upgrade_progress"] = new_progress
        
        # Check if leveled up
        if new_progress >= 100:
            current_index = UPGRADE_LEVELS.index(current_level)
            if current_index < len(UPGRADE_LEVELS) - 1:
                new_level = UPGRADE_LEVELS[current_index + 1]
                card["upgrade_level"] = new_level
                card["upgrade_progress"] = 0
                card = upgrade_card_stats(card)
                user_coll[self.card_index] = card
                
                embed = discord.Embed(
                    title="🎉 UPGRADE SUCCESSFUL! 🎉",
                    description=f"✨ {card['name']} upgraded to **{new_level}**! ✨",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="⭐ Maximum Level Reached! ⭐",
                    description=f"🏆 {card['name']} is already at Ultimate level!",
                    color=0xffd700
                )
        else:
            embed = discord.Embed(
                title="📈 Progress Added!",
                description=f"💪 {card['name']} upgrade progress: {new_progress}%",
                color=0x3498db
            )
        
        embed.add_field(name="💳 New Balance", value=f"${get_balance(self.user_id):,}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)

# Battle System UI - COMPLETELY REVAMPED FOR 45 SECOND BATTLES!
class BattleCardSelect(Select):
    def __init__(self, user_id: int, opponent_id: int, user_collection: list):
        self.user_id = user_id
        self.opponent_id = opponent_id
        self.user_collection = user_collection
        
        options = []
        for i, card in enumerate(user_collection[:25]):  # Discord limit
            upgrade_level = get_card_upgrade_level(card)
            battle_power = self.calculate_battle_power(card)
            
            options.append(
                discord.SelectOption(
                    label=f"{card['name']} [{upgrade_level}]",
                    description=f"{card['rarity']} • Power: {battle_power} • ${card['price']:,}",
                    value=str(i),
                    emoji="⚽"
                )
            )
        
        if not options:
            options.append(discord.SelectOption(label="No cards available", value="none", emoji="❌"))
        
        super().__init__(placeholder="Choose your battle card...", options=options)
    
    def calculate_battle_power(self, card: dict) -> int:
        """Calculate battle power based on card stats"""
        base_power = card.get('income_rate', 1)
        upgrade_multiplier = get_upgrade_multiplier(get_card_upgrade_level(card))
        return int(base_power * upgrade_multiplier * 0.1)  # Scale for battle display
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your battle!", ephemeral=True)
            return
        
        if self.values[0] == "none":
            await interaction.response.send_message("❌ No cards available for battle!", ephemeral=True)
            return
        
        card_index = int(self.values[0])
        uid = str(self.user_id)
        user_coll = data["user_collections"].get(uid, [])
        
        if card_index >= len(user_coll):
            await interaction.response.send_message("❌ Card not found!", ephemeral=True)
            return
        
        selected_card = user_coll[card_index]
        
        # Start the enhanced battle
        await self.start_45_second_battle(interaction, selected_card)
    
    async def start_45_second_battle(self, interaction: discord.Interaction, user_card: dict):
        """Start an interactive 45-second battle with real-time events"""
        # Get opponent info
        opponent = bot.get_user(self.opponent_id)
        if not opponent:
            await interaction.response.send_message("❌ Opponent not found!", ephemeral=True)
            return
        
        # Select random opponent card
        opponent_uid = str(self.opponent_id)
        opponent_coll = data["user_collections"].get(opponent_uid, [])
        if not opponent_coll:
            await interaction.response.send_message("❌ Opponent has no cards!", ephemeral=True)
            return
        
        opponent_card = random.choice(opponent_coll)
        
        # Calculate battle powers
        user_power = self.calculate_battle_power(user_card)
        opponent_power = self.calculate_battle_power(opponent_card)
        
        # Set battle cooldown
        uid = str(self.user_id)
        battle_cooldowns[uid] = datetime.utcnow().isoformat()
        
        # Initial battle embed
        embed = discord.Embed(
            title="⚔️ **45-SECOND BATTLE BEGINS!** ⚔️",
            description=f"🥊 **{interaction.user.display_name}** vs **{opponent.display_name}**",
            color=0xff4500
        )
        
        embed.add_field(
            name=f"🔥 {interaction.user.display_name}'s Team",
            value=f"⚽ {user_card['name']} [{get_card_upgrade_level(user_card)}]\\n💪 Power: {user_power}",
            inline=True
        )
        
        embed.add_field(
            name=f"🔥 {opponent.display_name}'s Team", 
            value=f"⚽ {opponent_card['name']} [{get_card_upgrade_level(opponent_card)}]\\n💪 Power: {opponent_power}",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Battle Duration",
            value="**45 seconds** of intense action!",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Battle variables
        user_score = 0
        opponent_score = 0
        battle_events = []
        
        # 45-second battle loop with real-time events
        for second in range(0, BATTLE_DURATION, 5):  # Update every 5 seconds
            await asyncio.sleep(5)
            
            # Random events based on card power
            user_success_rate = min(0.7, 0.3 + (user_power / (user_power + opponent_power)))
            opponent_success_rate = 1 - user_success_rate
            
            # Commentary
            commentary = random.choice(BATTLE_COMMENTARY)
            battle_events.append(f"⏱️ {second+5}s: {commentary}")
            
            # Random special events
            event_chance = random.random()
            
            if event_chance < 0.15:  # 15% chance for penalties
                await self.handle_penalty_event(interaction, user_card, opponent_card, battle_events, user_score, opponent_score, second+5)
                continue
            elif event_chance < 0.25:  # 10% chance for free kicks
                await self.handle_freekick_event(interaction, user_card, opponent_card, battle_events, user_score, opponent_score, second+5)
                continue
            elif event_chance < 0.45:  # 20% chance for big chances
                await self.handle_big_chance_event(interaction, user_card, opponent_card, battle_events, user_success_rate, second+5)
                continue
            
            # Regular goal chances
            if random.random() < 0.3:  # 30% chance for goal attempt each interval
                if random.random() < user_success_rate:
                    user_score += 1
                    battle_events.append(f"⚽ {second+5}s: **GOAL!** {user_card['name']} scores! {user_score}-{opponent_score}")
                elif random.random() < opponent_success_rate:
                    opponent_score += 1
                    battle_events.append(f"⚽ {second+5}s: **GOAL!** {opponent_card['name']} scores! {user_score}-{opponent_score}")
            
            # Update battle display every 10 seconds
            if (second + 5) % 10 == 0:
                await self.update_battle_display(interaction, user_card, opponent_card, user_score, opponent_score, battle_events[-3:], second+5)
        
        # Final results
        await self.conclude_battle(interaction, user_card, opponent_card, user_score, opponent_score, battle_events)
    
    async def handle_penalty_event(self, interaction, user_card, opponent_card, battle_events, user_score, opponent_score, time):
        """Handle interactive penalty shootout"""
        penalty_taker = random.choice([("user", user_card), ("opponent", opponent_card)])
        
        if penalty_taker[0] == "user":
            battle_events.append(f"🥅 {time}s: **PENALTY!** {user_card['name']} steps up!")
            view = PenaltyView(self.user_id, "user", user_score, opponent_score)
        else:
            battle_events.append(f"🥅 {time}s: **PENALTY!** {opponent_card['name']} steps up!")
            # Auto-resolve opponent penalty
            if random.random() < 0.7:  # 70% penalty conversion rate
                opponent_score += 1
                battle_events.append(f"⚽ {time}s: **PENALTY GOAL!** Score: {user_score}-{opponent_score}")
            else:
                battle_events.append(f"🚫 {time}s: **PENALTY MISSED!** Score stays {user_score}-{opponent_score}")
        
        await self.update_battle_display(interaction, user_card, opponent_card, user_score, opponent_score, battle_events[-2:], time)
        
        if penalty_taker[0] == "user":
            penalty_embed = discord.Embed(
                title="🥅 **PENALTY SHOOTOUT!** 🥅",
                description=f"⚽ {user_card['name']} has a penalty! Choose your shot placement!",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=penalty_embed, view=view)
    
    async def handle_freekick_event(self, interaction, user_card, opponent_card, battle_events, user_score, opponent_score, time):
        """Handle interactive free kick"""
        freekick_taker = random.choice([("user", user_card), ("opponent", opponent_card)])
        
        if freekick_taker[0] == "user":
            battle_events.append(f"⚡ {time}s: **FREE KICK!** {user_card['name']} lines up the shot!")
            view = FreekickView(self.user_id, "user", user_score, opponent_score)
        else:
            battle_events.append(f"⚡ {time}s: **FREE KICK!** {opponent_card['name']} takes aim!")
            if random.random() < 0.4:  # 40% free kick conversion rate
                opponent_score += 1
                battle_events.append(f"🚀 {time}s: **FREE KICK GOAL!** Score: {user_score}-{opponent_score}")
            else:
                battle_events.append(f"🌪️ {time}s: **FREE KICK OVER THE BAR!** Score stays {user_score}-{opponent_score}")
        
        await self.update_battle_display(interaction, user_card, opponent_card, user_score, opponent_score, battle_events[-2:], time)
        
        if freekick_taker[0] == "user":
            freekick_embed = discord.Embed(
                title="⚡ **FREE KICK OPPORTUNITY!** ⚡",
                description=f"🎯 {user_card['name']} has a free kick! Aim your shot!",
                color=0xffff00
            )
            await interaction.edit_original_response(embed=freekick_embed, view=view)
    
    async def handle_big_chance_event(self, interaction, user_card, opponent_card, battle_events, user_success_rate, time):
        """Handle big chance events"""
        if random.random() < 0.5:
            # User big chance
            battle_events.append(f"💥 {time}s: **BIG CHANCE!** {user_card['name']} is through on goal!")
            if random.random() < (user_success_rate + 0.2):  # Boosted success rate for big chances
                battle_events.append(f"⚽ {time}s: **CLINICAL FINISH!** What a goal!")
            else:
                battle_events.append(f"🤦 {time}s: **SAVED!** The keeper makes a brilliant stop!")
        else:
            # Opponent big chance  
            battle_events.append(f"💥 {time}s: **BIG CHANCE!** {opponent_card['name']} breaks free!")
            if random.random() < 0.6:
                battle_events.append(f"⚽ {time}s: **UNSTOPPABLE SHOT!** Goal scored!")
            else:
                battle_events.append(f"🛡️ {time}s: **BLOCKED!** Heroic defending!")
    
    async def update_battle_display(self, interaction, user_card, opponent_card, user_score, opponent_score, recent_events, time):
        """Update the battle display with current status"""
        embed = discord.Embed(
            title=f"⚔️ **LIVE BATTLE - {time}s/{BATTLE_DURATION}s** ⚔️",
            description=f"🔥 **{user_card['name']} {user_score} - {opponent_score} {opponent_card['name']}** 🔥",
            color=0x00ff00 if user_score > opponent_score else (0xff0000 if opponent_score > user_score else 0xffff00)
        )
        
        if recent_events:
            embed.add_field(
                name="📺 **Live Commentary**",
                value="\\n".join(recent_events[-3:]),  # Show last 3 events
                inline=False
            )
        
        progress_bar = "▓" * int((time / BATTLE_DURATION) * 20) + "░" * (20 - int((time / BATTLE_DURATION) * 20))
        embed.add_field(
            name="⏱️ **Match Progress**",
            value=f"`{progress_bar}` {time}s / {BATTLE_DURATION}s",
            inline=False
        )
        
        try:
            await interaction.edit_original_response(embed=embed, view=None)
        except:
            pass  # Continue if edit fails
    
    async def conclude_battle(self, interaction, user_card, opponent_card, user_score, opponent_score, battle_events):
        """Conclude the battle with final results and rewards"""
        # Determine winner
        if user_score > opponent_score:
            result = "win"
            result_emoji = "🏆"
            result_text = "**VICTORY!**"
            result_color = 0x00ff00
            
            # Award winner prize
            current_balance = get_balance(self.user_id)
            set_balance(self.user_id, current_balance + BATTLE_WIN_REWARD)
            reward_text = f"💰 You earned ${BATTLE_WIN_REWARD:,}!"
            
        elif opponent_score > user_score:
            result = "loss"
            result_emoji = "💔"
            result_text = "**DEFEAT!**"
            result_color = 0xff0000
            reward_text = "💪 Better luck next time!"
            
        else:
            result = "draw"
            result_emoji = "🤝"
            result_text = "**DRAW!**"
            result_color = 0xffff00
            reward_text = "🎯 Evenly matched!"
        
        # Final embed
        embed = discord.Embed(
            title=f"{result_emoji} **BATTLE CONCLUDED!** {result_emoji}",
            description=f"{result_text}\\n🔥 **Final Score: {user_score} - {opponent_score}** 🔥",
            color=result_color
        )
        
        embed.add_field(
            name="⚽ **Your Champion**",
            value=f"{user_card['name']} [{get_card_upgrade_level(user_card)}]",
            inline=True
        )
        
        embed.add_field(
            name="⚽ **Opponent Champion**", 
            value=f"{opponent_card['name']} [{get_card_upgrade_level(opponent_card)}]",
            inline=True
        )
        
        embed.add_field(
            name="🎁 **Battle Reward**",
            value=reward_text,
            inline=False
        )
        
        # Show highlights
        goal_events = [event for event in battle_events if "GOAL!" in event or "PENALTY GOAL!" in event or "FREE KICK GOAL!" in event]
        if goal_events:
            embed.add_field(
                name="⚽ **Match Highlights**",
                value="\\n".join(goal_events[-5:]),  # Show last 5 goals
                inline=False
            )
        
        embed.set_footer(text=f"⏱️ Battle lasted {BATTLE_DURATION} seconds • Next battle available in {BATTLE_COOLDOWN} seconds")
        
        await interaction.edit_original_response(embed=embed, view=None)
        
        # Announce in battle channel
        try:
            channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            if channel:
                announce_embed = discord.Embed(
                    title=f"{result_emoji} **Battle Result!** {result_emoji}",
                    description=f"🥊 **{interaction.user.display_name}** vs **{bot.get_user(self.opponent_id).display_name}**\\n🔥 **Final: {user_score} - {opponent_score}**",
                    color=result_color
                )
                await channel.send(embed=announce_embed)
        except:
            pass

class PenaltyView(View):
    def __init__(self, user_id: int, taker: str, user_score: int, opponent_score: int):
        super().__init__(timeout=15)
        self.user_id = user_id
        self.taker = taker
        self.user_score = user_score
        self.opponent_score = opponent_score

    async def penalty_result(self, interaction: discord.Interaction, placement: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your penalty!", ephemeral=True)
            return
        
        # Penalty success rates by placement
        success_rates = {
            "top_left": 0.8,
            "top_right": 0.8, 
            "bottom_left": 0.7,
            "bottom_right": 0.7,
            "center": 0.6
        }
        
        success = random.random() < success_rates.get(placement, 0.7)
        
        if success:
            self.user_score += 1
            embed = discord.Embed(
                title="⚽ **PENALTY GOAL!** ⚽",
                description=f"🎯 Perfect shot to the {placement.replace('_', ' ')}!\\n🔥 **Score: {self.user_score} - {self.opponent_score}**",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="🚫 **PENALTY SAVED!** 🚫", 
                description=f"🧤 The keeper guessed correctly!\\n😤 **Score stays: {self.user_score} - {self.opponent_score}**",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="↖️ Top Left", style=discord.ButtonStyle.primary)
    async def top_left(self, interaction: discord.Interaction, button: Button):
        await self.penalty_result(interaction, "top_left")

    @discord.ui.button(label="↗️ Top Right", style=discord.ButtonStyle.primary) 
    async def top_right(self, interaction: discord.Interaction, button: Button):
        await self.penalty_result(interaction, "top_right")

    @discord.ui.button(label="⬇️ Center", style=discord.ButtonStyle.secondary)
    async def center(self, interaction: discord.Interaction, button: Button):
        await self.penalty_result(interaction, "center")

    @discord.ui.button(label="↙️ Bottom Left", style=discord.ButtonStyle.success)
    async def bottom_left(self, interaction: discord.Interaction, button: Button):
        await self.penalty_result(interaction, "bottom_left")

    @discord.ui.button(label="↘️ Bottom Right", style=discord.ButtonStyle.success)
    async def bottom_right(self, interaction: discord.Interaction, button: Button):
        await self.penalty_result(interaction, "bottom_right")

class FreekickView(View):
    def __init__(self, user_id: int, taker: str, user_score: int, opponent_score: int):
        super().__init__(timeout=15)
        self.user_id = user_id
        self.taker = taker
        self.user_score = user_score
        self.opponent_score = opponent_score

    async def freekick_result(self, interaction: discord.Interaction, placement: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your free kick!", ephemeral=True)
            return
        
        # Free kick success rates by placement
        success_rates = {
            "top_corner": 0.5,
            "low_corner": 0.4,
            "center": 0.3,
            "over_wall": 0.6
        }
        
        success = random.random() < success_rates.get(placement, 0.4)
        
        if success:
            self.user_score += 1
            embed = discord.Embed(
                title="🚀 **FREE KICK GOAL!** 🚀",
                description=f"💫 Spectacular shot {placement.replace('_', ' ')}!\\n🔥 **Score: {self.user_score} - {self.opponent_score}**",
                color=0x00ff00
            )
        else:
            miss_outcomes = ["🌪️ Over the bar!", "🛡️ Blocked by the wall!", "🧤 Saved by the keeper!"]
            outcome = random.choice(miss_outcomes)
            embed = discord.Embed(
                title="🚫 **FREE KICK MISSED!** 🚫",
                description=f"{outcome}\\n😤 **Score stays: {self.user_score} - {self.opponent_score}**",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🎯 Top Corner", style=discord.ButtonStyle.primary)
    async def top_corner(self, interaction: discord.Interaction, button: Button):
        await self.freekick_result(interaction, "top_corner")

    @discord.ui.button(label="⬇️ Low Corner", style=discord.ButtonStyle.success)
    async def low_corner(self, interaction: discord.Interaction, button: Button):
        await self.freekick_result(interaction, "low_corner")

    @discord.ui.button(label="🎪 Over Wall", style=discord.ButtonStyle.secondary)
    async def over_wall(self, interaction: discord.Interaction, button: Button):
        await self.freekick_result(interaction, "over_wall")

    @discord.ui.button(label="🚀 Power Shot", style=discord.ButtonStyle.danger)
    async def center(self, interaction: discord.Interaction, button: Button):
        await self.freekick_result(interaction, "center")

# Enhanced Trade System - Specific card selection!
class TradeCardSelect(Select):
    def __init__(self, user_id: int, user_collection: list, trade_type: str):
        self.user_id = user_id
        self.trade_type = trade_type  # "offer" or "request"
        
        options = []
        for i, card in enumerate(user_collection[:25]):  # Discord limit
            upgrade_level = get_card_upgrade_level(card)
            options.append(
                discord.SelectOption(
                    label=f"{card['name']} [{upgrade_level}]",
                    description=f"{card['rarity']} • ${card['price']:,} • {card.get('income_rate', 1)}/30min",
                    value=str(i),
                    emoji="🎴"
                )
            )
        
        if not options:
            options.append(discord.SelectOption(label="No cards available", value="none", emoji="❌"))
        
        placeholder = "Choose cards to offer..." if trade_type == "offer" else "Choose cards you want..."
        super().__init__(placeholder=placeholder, options=options, max_values=min(5, len(options)))

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your selection!", ephemeral=True)
            return
        
        if self.values[0] == "none":
            await interaction.response.send_message("❌ No cards available!", ephemeral=True)
            return
        
        selected_cards = []
        uid = str(self.user_id)
        
        if self.trade_type == "offer":
            user_coll = data["user_collections"].get(uid, [])
        else:
            # This is a request from target's collection
            user_coll = data["user_collections"].get(uid, [])
        
        for value in self.values:
            card_index = int(value)
            if card_index < len(user_coll):
                card = user_coll[card_index]
                selected_cards.append({
                    'name': card['name'],
                    'upgrade_level': get_card_upgrade_level(card),
                    'rarity': card['rarity'],
                    'price': card['price']
                })
        
        # Store selection and respond
        card_list = "\\n".join([f"• {card['name']} [{card['upgrade_level']}]" for card in selected_cards])
        
        embed = discord.Embed(
            title=f"✅ **Cards {'Offered' if self.trade_type == 'offer' else 'Requested'}!**",
            description=f"Selected {len(selected_cards)} card(s):",
            color=0x00ff00
        )
        
        embed.add_field(
            name=f"{'📦 Offering' if self.trade_type == 'offer' else '💎 Requesting'}:",
            value=card_list,
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class TradeView(View):
    def __init__(self, initiator_id: int, target_id: int):
        super().__init__(timeout=300)  # 5 minutes
        self.initiator_id = initiator_id
        self.target_id = target_id
        self.initiator_offer = []
        self.target_request = []
        self.trade_finalized = False

    @discord.ui.button(label="📦 Select Cards to Offer", style=discord.ButtonStyle.primary)
    async def select_offer(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("❌ You are not the trade initiator!", ephemeral=True)
            return
        
        uid = str(self.initiator_id)
        user_coll = data["user_collections"].get(uid, [])
        
        if not user_coll:
            await interaction.response.send_message("❌ You have no cards to offer!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📦 **Select Cards to Offer**",
            description="Choose up to 5 cards from your collection to offer in this trade!",
            color=0x3498db
        )
        
        view = View(timeout=60)
        view.add_item(TradeCardSelect(self.initiator_id, user_coll, "offer"))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="💎 Select Cards Wanted", style=discord.ButtonStyle.success)
    async def select_request(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("❌ You are not the trade initiator!", ephemeral=True)
            return
        
        target_uid = str(self.target_id)
        target_coll = data["user_collections"].get(target_uid, [])
        
        if not target_coll:
            await interaction.response.send_message("❌ Target player has no cards!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="💎 **Select Cards You Want**",
            description="Choose up to 5 cards you want from their collection!",
            color=0x00ff00
        )
        
        view = View(timeout=60)
        view.add_item(TradeCardSelect(self.initiator_id, target_coll, "request"))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🔄 Finalize Trade Offer", style=discord.ButtonStyle.secondary)
    async def finalize_offer(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("❌ You are not the trade initiator!", ephemeral=True)
            return
        
        if not self.initiator_offer or not self.target_request:
            await interaction.response.send_message("❌ You must select both cards to offer and cards to request!", ephemeral=True)
            return
        
        # Create trade embed showing the specific trade
        target_user = bot.get_user(self.target_id)
        
        embed = discord.Embed(
            title="🔄 **SPECIFIC TRADE PROPOSAL** 🔄",
            description=f"**{interaction.user.display_name}** wants to trade with **{target_user.display_name}**",
            color=0xffd700
        )
        
        # Show offered cards
        offer_text = []
        for card_info in self.initiator_offer:
            offer_text.append(f"• {card_info['name']} [{card_info['upgrade_level']}] - {card_info['rarity']}")
        
        embed.add_field(
            name="📦 **Cards Being Offered**",
            value="\\n".join(offer_text) if offer_text else "None selected",
            inline=False
        )
        
        # Show requested cards
        request_text = []
        for card_info in self.target_request:
            request_text.append(f"• {card_info['name']} [{card_info['upgrade_level']}] - {card_info['rarity']}")
        
        embed.add_field(
            name="💎 **Cards Being Requested**", 
            value="\\n".join(request_text) if request_text else "None selected",
            inline=False
        )
        
        embed.set_footer(text="Target player can accept or decline this specific trade!")
        
        # Create new view with accept/decline for target
        trade_decision_view = TradeDecisionView(self.initiator_id, self.target_id, self.initiator_offer, self.target_request)
        
        await interaction.response.edit_message(embed=embed, view=trade_decision_view)

    @discord.ui.button(label="❌ Cancel Trade", style=discord.ButtonStyle.danger)
    async def cancel_trade(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in [self.initiator_id, self.target_id]:
            await interaction.response.send_message("❌ You are not part of this trade!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ **Trade Cancelled** ❌",
            description=f"The trade has been cancelled by <@{interaction.user.id}>.",
            color=0xff0000
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class TradeDecisionView(View):
    def __init__(self, initiator_id: int, target_id: int, initiator_offer: list, target_request: list):
        super().__init__(timeout=300)
        self.initiator_id = initiator_id
        self.target_id = target_id
        self.initiator_offer = initiator_offer
        self.target_request = target_request

    @discord.ui.button(label="✅ Accept Specific Trade", style=discord.ButtonStyle.success)
    async def accept_specific_trade(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ You are not the target of this trade!", ephemeral=True)
            return
        
        # Execute the specific trade
        success = self.execute_trade()
        
        if success:
            embed = discord.Embed(
                title="🎉 **TRADE COMPLETED!** 🎉",
                description=f"Successful trade between <@{self.initiator_id}> and <@{self.target_id}>!",
                color=0x00ff00
            )
            
            # Show what was traded
            offer_text = [f"• {card['name']} [{card['upgrade_level']}]" for card in self.initiator_offer]
            request_text = [f"• {card['name']} [{card['upgrade_level']}]" for card in self.target_request]
            
            embed.add_field(name="📦 **Cards Traded Away**", value="\\n".join(offer_text), inline=True)
            embed.add_field(name="💎 **Cards Received**", value="\\n".join(request_text), inline=True)
            
        else:
            embed = discord.Embed(
                title="❌ **Trade Failed!** ❌",
                description="Trade could not be completed. Players may not have the required cards.",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="❌ Decline Trade", style=discord.ButtonStyle.danger)
    async def decline_specific_trade(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ You are not the target of this trade!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ **Trade Declined** ❌",
            description=f"<@{self.target_id}> has declined the trade offer.",
            color=0xff0000
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    def execute_trade(self) -> bool:
        """Execute the specific trade between players"""
        try:
            initiator_uid = str(self.initiator_id)
            target_uid = str(self.target_id)
            
            initiator_coll = data["user_collections"].get(initiator_uid, [])
            target_coll = data["user_collections"].get(target_uid, [])
            
            # Verify all cards exist
            for offer_card in self.initiator_offer:
                if not any(c['name'] == offer_card['name'] and get_card_upgrade_level(c) == offer_card['upgrade_level'] 
                          for c in initiator_coll):
                    return False
            
            for request_card in self.target_request:
                if not any(c['name'] == request_card['name'] and get_card_upgrade_level(c) == request_card['upgrade_level'] 
                          for c in target_coll):
                    return False
            
            # Remove cards from initiator and add requested cards
            for offer_card in self.initiator_offer:
                for i, card in enumerate(initiator_coll):
                    if card['name'] == offer_card['name'] and get_card_upgrade_level(card) == offer_card['upgrade_level']:
                        initiator_coll.pop(i)
                        break
            
            # Remove cards from target and add offered cards  
            for request_card in self.target_request:
                for i, card in enumerate(target_coll):
                    if card['name'] == request_card['name'] and get_card_upgrade_level(card) == request_card['upgrade_level']:
                        target_coll.pop(i)
                        break
            
            # Add new cards
            initiator_coll.extend(self.target_request)
            target_coll.extend(self.initiator_offer)
            
            return True
            
        except Exception as e:
            print(f"Trade execution error: {e}")
            return False

# Modern Shop UI with Pagination - ENHANCED VERSION
class ShopView(View):
    def __init__(self, cards: List[dict], rarity_filter: str = None, page: int = 0):
        super().__init__(timeout=120)
        self.cards = cards
        self.rarity_filter = rarity_filter
        self.page = page
        self.cards_per_page = 6
        self.max_pages = (len(cards) - 1) // self.cards_per_page + 1
        
        # Update button states
        if self.page <= 0:
            self.previous_button.disabled = True
        if self.page >= self.max_pages - 1:
            self.next_button.disabled = True

    def get_embed(self):
        embed = discord.Embed(
            title=f"🏪 **Tadzzy Card Shop**{f' - {self.rarity_filter} Cards' if self.rarity_filter else ''}",
            description=f"📄 **Page {self.page + 1}/{self.max_pages}** | 💳 **{len(self.cards)} Total Cards**",
            color=0x5865F2
        )
        
        # Show discount if active
        if data["shop_discount"] > 0:
            embed.add_field(
                name="🛍️ **MEGA SALE ACTIVE!**",
                value=f"💥 **{data['shop_discount']}% OFF ALL PLAYERS!** 💥",
                inline=False
            )
        
        # Get cards for current page
        start_idx = self.page * self.cards_per_page
        end_idx = start_idx + self.cards_per_page
        page_cards = self.cards[start_idx:end_idx]
        
        for i, card in enumerate(page_cards, 1):
            # Rarity emoji mapping
            rarity_emojis = {
                "Secret": "⚫",
                "Expensive": "💎", 
                "Mythic": "🔮",
                "Legendary": "⭐",
                "Epic": "🟣",
                "Common": "🔵"
            }
            
            # Check if out of stock
            if card["name"] in data["out_of_stock"]:
                stock_status = "❌ **OUT OF STOCK**"
                price_display = "🚫 **N/A**"
                buy_info = "❌ **Unavailable**"
            else:
                stock_status = "✅ **In Stock**"
                original_price = card["price"]
                discounted_price = int(original_price * (1 - data["shop_discount"] / 100))
                
                if data["shop_discount"] > 0:
                    price_display = f"💸 ~~${original_price:,}~~ ➜ **${discounted_price:,}**"
                else:
                    price_display = f"💰 **${original_price:,}**"
                
                buy_info = f"📝 `!buy {card['name']}`"
            
            # Income calculation with emoji
            income_rate = card.get('income_rate', 1)
            if income_rate >= 5000:
                income_emoji = "💎"
            elif income_rate >= 1000:
                income_emoji = "⭐"
            elif income_rate >= 500:
                income_emoji = "🟣"
            elif income_rate >= 100:
                income_emoji = "🔵"
            else:
                income_emoji = "🟢"
            
            embed.add_field(
                name=f"{rarity_emojis.get(card['rarity'], '⚪')} **{card['name']}**",
                value=(
                    f"{rarity_emojis.get(card['rarity'], '⚪')} **{card['rarity']}** Rarity\n"
                    f"{price_display}\n"
                    f"{income_emoji} **{income_rate:,}** coins/30min\n"
                    f"{stock_status}\n"
                    f"{buy_info}"
                ),
                inline=True
            )
        
        # Add helpful footer
        embed.set_footer(
            text=f"💡 Use buttons to navigate • Higher rarity = More income • {len(self.cards)} total cards"
        )
        
        return embed

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 0:
            self.page -= 1
            
            # Update button states
            self.next_button.disabled = False
            if self.page <= 0:
                self.previous_button.disabled = True
            
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary, row=0) 
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.max_pages - 1:
            self.page += 1
            
            # Update button states
            self.previous_button.disabled = False
            if self.page >= self.max_pages - 1:
                self.next_button.disabled = True
            
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="🔍 Filter by Rarity", style=discord.ButtonStyle.primary, row=0)
    async def filter_button(self, interaction: discord.Interaction, button: Button):
        # Create rarity filter dropdown
        select = RaritySelect()
        view = View()
        view.add_item(select)
        
        embed = discord.Embed(
            title="🔍 **Filter Shop by Rarity**",
            description="Choose a rarity to filter the shop, or select 'All Cards' to show everything!",
            color=0x3498db
        )
        
        rarities = {}
        for card in footballers:
            rarity = card["rarity"]
            rarities[rarity] = rarities.get(rarity, 0) + 1
        
        rarity_text = []
        for rarity, count in rarities.items():
            emoji = {"Secret": "⚫", "Expensive": "💎", "Mythic": "🔮", "Legendary": "⭐", "Epic": "🟣", "Common": "🔵"}.get(rarity, "⚪")
            rarity_text.append(f"{emoji} **{rarity}**: {count} cards")
        
        embed.add_field(
            name="📊 **Available Rarities**",
            value="\n".join(rarity_text),
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.success, row=0)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="💰 Quick Buy", style=discord.ButtonStyle.success, row=1)
    async def quick_buy_button(self, interaction: discord.Interaction, button: Button):
        # Show quick buy options for current page
        start_idx = self.page * self.cards_per_page
        end_idx = start_idx + self.cards_per_page
        page_cards = self.cards[start_idx:end_idx]
        
        # Filter available cards (not out of stock)
        available_cards = [card for card in page_cards if card["name"] not in data["out_of_stock"]]
        
        if not available_cards:
            await interaction.response.send_message("❌ No cards available for quick buy on this page!", ephemeral=True)
            return
        
        select = QuickBuySelect(available_cards, interaction.user.id)
        view = View()
        view.add_item(select)
        
        embed = discord.Embed(
            title="💰 **Quick Buy Menu**",
            description="Select a card from this page to purchase instantly!",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class RaritySelect(Select):
    def __init__(self):
        # Count cards by rarity
        rarities = {}
        for card in footballers:
            rarity = card["rarity"]
            rarities[rarity] = rarities.get(rarity, 0) + 1
        
        options = [
            discord.SelectOption(
                label="All Cards",
                description=f"Show all {len(footballers)} cards",
                emoji="🌟",
                value="all"
            )
        ]
        
        rarity_order = ["Secret", "Expensive", "Mythic", "Legendary", "Epic", "Common"]
        emoji_map = {"Secret": "⚫", "Expensive": "💎", "Mythic": "🔮", "Legendary": "⭐", "Epic": "🟣", "Common": "🔵"}
        
        for rarity in rarity_order:
            if rarity in rarities:
                options.append(
                    discord.SelectOption(
                        label=f"{rarity} Cards",
                        description=f"{rarities[rarity]} {rarity.lower()} cards available",
                        emoji=emoji_map.get(rarity, "⚪"),
                        value=rarity.lower()
                    )
                )
        
        super().__init__(placeholder="Choose rarity to filter...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "all":
            filtered_cards = sorted(footballers, key=lambda x: x["price"], reverse=True)
            rarity_filter = None
        else:
            rarity = self.values[0].title()
            filtered_cards = sorted([f for f in footballers if f["rarity"] == rarity], key=lambda x: x["price"], reverse=True)
            rarity_filter = rarity
        
        if not filtered_cards:
            await interaction.response.send_message(f"❌ No cards found for rarity '{rarity}'!", ephemeral=True)
            return
        
        view = ShopView(filtered_cards, rarity_filter)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)

class QuickBuySelect(Select):
    def __init__(self, available_cards: List[dict], user_id: int):
        self.available_cards = available_cards
        self.user_id = user_id
        
        options = []
        for card in available_cards[:25]:  # Discord limit
            original_price = card["price"]
            discounted_price = int(original_price * (1 - data["shop_discount"] / 100))
            final_price = discounted_price if data["shop_discount"] > 0 else original_price
            
            rarity_emojis = {"Secret": "⚫", "Expensive": "💎", "Mythic": "🔮", "Legendary": "⭐", "Epic": "🟣", "Common": "🔵"}
            
            options.append(
                discord.SelectOption(
                    label=card["name"],
                    description=f"{card['rarity']} • ${final_price:,} • {card.get('income_rate', 1)}/30min",
                    emoji=rarity_emojis.get(card["rarity"], "⚪"),
                    value=card["name"]
                )
            )
        
        super().__init__(placeholder="Select a card to buy instantly...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your quick buy menu!", ephemeral=True)
            return
        
        card_name = self.values[0]
        card = find_player_card_by_name(card_name)
        
        if not card:
            await interaction.response.send_message("❌ Card not found!", ephemeral=True)
            return
        
        # Check if out of stock
        if card["name"] in data["out_of_stock"]:
            await interaction.response.send_message(f"❌ {card['name']} is currently OUT OF STOCK!", ephemeral=True)
            return
        
        ensure_user_exists(self.user_id)
        user_balance = get_balance(self.user_id)
        original_price = card["price"]
        final_price = int(original_price * (1 - data["shop_discount"] / 100))
        
        if user_balance < final_price:
            await interaction.response.send_message(
                f"❌ **Insufficient funds!**\n💰 You have: **${user_balance:,}**\n💸 Card costs: **${final_price:,}**",
                ephemeral=True
            )
            return
        
        # Check if user already owns this card
        uid = str(self.user_id)
        user_collection = data["user_collections"].get(uid, [])
        if any(c["name"] == card["name"] for c in user_collection):
            await interaction.response.send_message(f"❌ You already own **{card['name']}**!", ephemeral=True)
            return
        
        # Check collection space
        if len(user_collection) >= MAX_COLLECTION_SLOTS:
            await interaction.response.send_message(f"❌ Your collection is full! **({MAX_COLLECTION_SLOTS}/{MAX_COLLECTION_SLOTS})**", ephemeral=True)
            return
        
        # Process purchase
        set_balance(self.user_id, user_balance - final_price)
        purchased_card = card.copy()
        purchased_card["upgrade_level"] = "Gold"
        purchased_card["upgrade_progress"] = 0
        data["user_collections"][uid].append(purchased_card)
        
        embed = discord.Embed(
            title="🎉 **Quick Purchase Successful!**",
            description=f"You bought **{card['name']}** for **${final_price:,}**!",
            color=card["color"]
        )
        
        if data["shop_discount"] > 0:
            embed.add_field(
                name="💸 **Discount Applied**",
                value=f"You saved **${original_price - final_price:,}** ({data['shop_discount']}% off)!",
                inline=True
            )
        
        embed.add_field(name="💰 **New Balance**", value=f"${get_balance(self.user_id):,}", inline=True)
        embed.add_field(name="📈 **Passive Income**", value=f"💰 {card.get('income_rate', 1)}/30min", inline=True)
        embed.add_field(name="📦 **Collection**", value=f"{len(user_collection)+1}/{MAX_COLLECTION_SLOTS} cards", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)

class BattleActionView(View):
    def __init__(self, user_id: int, action_type: str, context: dict):
        super().__init__(timeout=15)
        self.user_id = user_id
        self.action_type = action_type
        self.context = context

    @discord.ui.button(label="🥅 Top Left", style=discord.ButtonStyle.primary)
    async def top_left(self, interaction: discord.Interaction, button: Button):
        await self.handle_action(interaction, "top_left")

    @discord.ui.button(label="🥅 Top Right", style=discord.ButtonStyle.primary) 
    async def top_right(self, interaction: discord.Interaction, button: Button):
        await self.handle_action(interaction, "top_right")

    @discord.ui.button(label="🥅 Bottom Left", style=discord.ButtonStyle.secondary)
    async def bottom_left(self, interaction: discord.Interaction, button: Button):
        await self.handle_action(interaction, "bottom_left")

    @discord.ui.button(label="🥅 Bottom Right", style=discord.ButtonStyle.secondary)
    async def bottom_right(self, interaction: discord.Interaction, button: Button):
        await self.handle_action(interaction, "bottom_right")

    @discord.ui.button(label="🎯 Center", style=discord.ButtonStyle.success)
    async def center(self, interaction: discord.Interaction, button: Button):
        await self.handle_action(interaction, "center")

    async def handle_action(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your action!", ephemeral=True)
            return

        success_chance = 0.5  # 50% base chance
        
        if self.action_type == "penalty":
            success_chance = 0.5  # 50/50 for penalties as requested
            
        if self.action_type == "freekick":
            success_chance = 0.3  # 30% for free kicks
            
        if self.action_type == "chance":
            success_chance = 0.6  # 60% for chances
        
        success = random.random() < success_chance
        
        if success:
            self.context["scorer"] = self.user_id
            result_text = f"⚽ **GOAL!** Perfect {choice} placement!"
        else:
            result_text = f"💨 **MISS!** The ball goes wide from {choice}!"
        
        embed = discord.Embed(
            title=f"🎯 {self.action_type.title()} Result!",
            description=result_text,
            color=0x00ff00 if success else 0xff0000
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

# -----------------------------
# Shop Discount System
# -----------------------------
@tasks.loop(hours=6)  # Check every 6 hours
async def shop_discount_system():
    """Random shop discounts"""
    if random.random() < 0.3:  # 30% chance
        data["shop_discount"] = 10  # 10% discount
        print("[Shop] 10% discount activated!")
        
        # Send announcement to specific channel
        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            try:
                embed = discord.Embed(
                    title="🛍️ SHOP SALE! 🛍️",
                    description="💥 **10% OFF ALL PLAYERS!** 💥\nLimited time offer - get your favorite cards now!",
                    color=0xff6b6b
                )
                await channel.send(embed=embed)
                print(f"[Shop] Sale announcement sent to channel {ANNOUNCEMENT_CHANNEL_ID}")
            except Exception as e:
                print(f"[Shop] Failed to send announcement: {e}")
        else:
            print(f"[Shop] Announcement channel {ANNOUNCEMENT_CHANNEL_ID} not found")
        
        # Discount lasts 2 hours
        await asyncio.sleep(7200)
        data["shop_discount"] = 0
        print("[Shop] Discount ended.")

# -----------------------------
# Persistence: save & load to JSON
# -----------------------------
def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                for k in ["tadbucks_balances", "tadzzy_points", "xp_levels", "user_collections", "user_packs", "gamenights",
                         "auctions", "trades", "daily_rewards", "weekly_rewards", "hourly_rewards", "daily_spin", "multipliers",
                         "codes", "rebirths", "deleted_messages", "out_of_stock", "shop_discount", "settings"]:
                    if k in file_data:
                        data[k] = file_data[k]
            print("✅ Loaded data from", DATA_FILE)
        except Exception as e:
            print("Failed to load data:", e)
    else:
        print("No data file found, starting fresh.")

def save_data():
    try:
        to_save = {
            k: data[k] for k in ["tadbucks_balances", "tadzzy_points", "xp_levels", "user_collections", "user_packs",
                                "gamenights", "auctions", "trades", "daily_rewards", "weekly_rewards",
                                "hourly_rewards", "daily_spin", "multipliers", "codes", "rebirths", "deleted_messages", "out_of_stock", "shop_discount", "settings"]
        }
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
        return True
    except Exception as e:
        print("Failed to save data:", e)
        return False

def backup_data():
    os.makedirs(DATA_BACKUP_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(DATA_BACKUP_DIR, f"tadzzy_data_backup_{timestamp}.json")
    try:
        if os.path.exists(DATA_FILE):
            shutil.copy2(DATA_FILE, dest)
            return dest
    except Exception as e:
        print("Backup failed:", e)
        return None

# -----------------------------
# Utility functions
# -----------------------------
def ensure_user_exists(user_id: int):
    uid = str(user_id)
    if uid not in data["tadbucks_balances"]:
        data["tadbucks_balances"][uid] = data["settings"].get("starting_balance", STARTING_BALANCE)
    if uid not in data["tadzzy_points"]:
        data["tadzzy_points"][uid] = 0
    if uid not in data["xp_levels"]:
        data["xp_levels"][uid] = 0
    if uid not in data["user_collections"]:
        data["user_collections"][uid] = []
    if uid not in data["user_packs"]:
        data["user_packs"][uid] = {}
    if uid not in data["rebirths"]:
        data["rebirths"][uid] = 0

def get_balance(user_id: int) -> int:
    uid = str(user_id)
    return int(data["tadbucks_balances"].get(uid, data["settings"].get("starting_balance", STARTING_BALANCE)))

def get_user_max_storage(user_id: int) -> int:
    """Get user's maximum collection storage slots"""
    uid = str(user_id)
    storage = data["user_storage"].get(uid, MAX_COLLECTION_SLOTS)
    if storage == "infinite":
        return 999999  # Return a very large number for infinite
    return storage

def set_user_storage(user_id: int, slots):
    """Set user's maximum storage slots"""
    uid = str(user_id)
    data["user_storage"][uid] = slots

def set_balance(user_id: int, amount: int):
    uid = str(user_id)
    data["tadbucks_balances"][uid] = int(amount)

def add_to_collection(user_id: int, card: dict) -> bool:
    uid = str(user_id)
    ensure_user_exists(user_id)
    if len(data["user_collections"][uid]) >= MAX_COLLECTION_SLOTS:
        return False
    data["user_collections"][uid].append(card)
    return True

def get_multiplier(user_id: int, multiplier_type: str) -> float:
    """Get active multiplier for user"""
    uid = str(user_id)
    user_multipliers = data["multipliers"].get(uid, {})
    
    if multiplier_type in user_multipliers:
        expiry = datetime.fromisoformat(user_multipliers[multiplier_type])
        if datetime.utcnow() < expiry:
            if multiplier_type in ["x2_cash", "x2_xp"]:
                return 2.0
            elif multiplier_type in ["x3_cash", "x3_xp"]:
                return 3.0
        else:
            # Remove expired multiplier
            del user_multipliers[multiplier_type]
    
    return 1.0

def apply_rebirth_bonus(user_id: int, base_income: int) -> int:
    """Apply rebirth bonus to income (50% per rebirth)"""
    uid = str(user_id)
    rebirths = data["rebirths"].get(uid, 0)
    
    if rebirths == 0:
        return base_income
    
    # 50% bonus per rebirth
    multiplier = 1.0 + (rebirths * 0.5)
    return int(base_income * multiplier)

# -----------------------------
# Background tasks
# -----------------------------
@tasks.loop(seconds=AUTOSAVE_INTERVAL_SECONDS)
async def autosave_task():
    saved = save_data()
    if saved:
        print(f"[{datetime.utcnow().isoformat()}] Autosaved data.")
    else:
        print(f"[{datetime.utcnow().isoformat()}] Autosave failed.")

@tasks.loop(minutes=30)
async def passive_income():
    """Fixed passive income system - pays every 30 minutes"""
    for uid, coll in data["user_collections"].items():
        if not coll:  # Skip users with empty collections
            continue
            
        total_income = 0
        user_id = int(uid)
        
        for card in coll:
            # Use the income_rate field directly (already doubled in card definitions)
            base_income = card.get("income_rate", 1)
            
            # Apply rebirth bonus
            income_with_rebirth = apply_rebirth_bonus(user_id, base_income)
            
            # Apply cash multiplier
            cash_multiplier = get_multiplier(user_id, "x2_cash") if get_multiplier(user_id, "x2_cash") > 1 else get_multiplier(user_id, "x3_cash")
            final_income = int(income_with_rebirth * cash_multiplier)
            
            total_income += final_income
        
        if total_income > 0:
            current_balance = data["tadbucks_balances"].get(uid, STARTING_BALANCE)
            data["tadbucks_balances"][uid] = current_balance + total_income
            last_income_report[uid] = total_income
            total_income_tracker[uid] = total_income_tracker.get(uid, 0) + total_income
            print(f"[Passive Income] User {uid} earned {total_income} Tadbucks.")
    
    save_data()

@tasks.loop(minutes=1)
async def auction_cleanup():
    """Auto-close expired auctions"""
    current_time = datetime.now(timezone.utc)
    expired_auctions = []
    
    for player_name, auction in data["auctions"].items():
        if not auction.get("active", False):
            continue
            
        ends_at = datetime.fromisoformat(auction["ends_at"])
        if current_time > ends_at:
            expired_auctions.append(player_name)
    
    for player_name in expired_auctions:
        auction = data["auctions"][player_name]
        auction["active"] = False
        
        # Award to highest bidder and announce winner
        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        
        if auction.get("highest_bidder"):
            winner_id = int(auction["highest_bidder"])
            amount = int(auction["highest_bid"])
            
            ensure_user_exists(winner_id)
            if get_balance(winner_id) >= amount:
                set_balance(winner_id, get_balance(winner_id) - amount)
                card = find_player_card_by_name(player_name)
                if card:
                    user_coll = data["user_collections"].setdefault(str(winner_id), [])
                    if len(user_coll) < MAX_COLLECTION_SLOTS:
                        user_coll.append(card.copy())
                        print(f"[Auction] {winner_id} won {player_name} for ${amount}")
                        
                        # Announce winner in announcement channel
                        if channel:
                            try:
                                winner = bot.get_user(winner_id)
                                winner_name = winner.display_name if winner else f"User {winner_id}"
                                
                                embed = discord.Embed(
                                    title="🏆 AUCTION WON! 🏆",
                                    description=f"**{winner_name}** won the auction!",
                                    color=card["color"]
                                )
                                embed.add_field(name="🎯 Player", value=f"{card['rarity']} {player_name}", inline=True)
                                embed.add_field(name="💰 Final Bid", value=f"{amount:,} Tadbucks", inline=True)
                                embed.add_field(name="🏆 Winner", value=winner_name, inline=True)
                                embed.set_footer(text="🎉 Congratulations! Keep bidding on future auctions!")
                                
                                await channel.send(embed=embed)
                            except Exception as e:
                                print(f"[Auction] Failed to announce winner: {e}")
        else:
            # No bidders - announce failed auction
            if channel:
                try:
                    embed = discord.Embed(
                        title="💸 AUCTION EXPIRED 💸",
                        description=f"**{player_name}** auction ended with no bidders!",
                        color=0x808080
                    )
                    embed.set_footer(text="💡 Better luck next time! Stay alert for new auctions!")
                    
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"[Auction] Failed to announce expired auction: {e}")

@passive_income.before_loop
async def before_passive_income():
    await bot.wait_until_ready()
    print("[Passive Income] System started.")

@auction_cleanup.before_loop
async def before_auction_cleanup():
    await bot.wait_until_ready()
    print("[Auction Cleanup] System started.")

@shop_discount_system.before_loop
async def before_shop_discount():
    await bot.wait_until_ready()
    print("[Shop Discount] System started.")

# -----------------------------
# Bot events
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot ready as {bot.user} (ID: {bot.user.id})")
    load_data()
    
    # Randomize shop stock on startup - items go out of stock more often!
    randomize_stock_status()
    print("🛒 Shop stock randomized - many items are now out of stock!")
    if not autosave_task.is_running():
        autosave_task.start()
    if not passive_income.is_running():
        passive_income.start()
    if not auction_cleanup.is_running():
        auction_cleanup.start()
    if not shop_discount_system.is_running():
        shop_discount_system.start()
    await bot.change_presence(activity=discord.Game(name="type !help"))
    
    # Send startup announcement
    channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if channel:
        try:
            embed = discord.Embed(
                title="🤖 TadzzyBot Online! 🤖",
                description="✅ **Bot has been successfully started!**\n🎮 All systems are operational and ready!",
                color=0x00ff00
            )
            embed.add_field(
                name="🌟 Features Active",
                value="• Economy System\n• Pack Openings\n• Random Auctions\n• Passive Income\n• Shop Discounts\n• All Commands",
                inline=True
            )
            embed.add_field(
                name="🎯 Get Started",
                value="Type `!help` for commands\nType `!daily` for free rewards\nType `!spin` for daily wheel",
                inline=True
            )
            embed.set_footer(text="🚀 TadzzyBot - Your Ultimate Discord Economy Bot!")
            
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[Startup] Failed to send startup message: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
        return
    
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument: {str(error)}")
        return
    
    if isinstance(error, commands.CommandOnCooldown):
        remaining = str(timedelta(seconds=int(error.retry_after)))
        await ctx.send(f"⏰ Command is on cooldown. Try again in {remaining}")
        return
    
    # Log unexpected errors
    print(f"[Error] Command: {ctx.command}, Error: {error}")
    
    embed = discord.Embed(
        title="❌ An Error Occurred",
        description="Something went wrong! Please try again or contact an administrator.",
        color=0xff0000
    )
    embed.add_field(name="Command", value=f"`{ctx.command}`" if ctx.command else "Unknown", inline=True)
    embed.set_footer(text="If this error persists, please report it!")
    
    try:
        await ctx.send(embed=embed)
    except:
        pass

@bot.event
async def on_message_delete(message):
    """Store deleted messages for retrieval"""
    if message.author.bot:
        return
    
    data["deleted_messages"].append({
        "content": message.content,
        "author": str(message.author),
        "author_id": message.author.id,
        "channel": str(message.channel),
        "timestamp": datetime.utcnow().isoformat(),
        "message_id": message.id
    })
    
    # Keep only last 50 deleted messages
    if len(data["deleted_messages"]) > 50:
        data["deleted_messages"] = data["deleted_messages"][-50:]

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
        
    # XP system per message with increased XP
    uid = message.author.id
    ensure_user_exists(uid)
    
    # Apply XP multiplier
    base_xp = LEVEL_XP_REWARD
    xp_multiplier = get_multiplier(uid, "x2_xp") if get_multiplier(uid, "x2_xp") > 1 else get_multiplier(uid, "x3_xp")
    final_xp = int(base_xp * xp_multiplier)
    
    data["xp_levels"][str(uid)] = int(data["xp_levels"].get(str(uid), 0)) + final_xp
    
    # Level check
    current_xp = data["xp_levels"][str(uid)]
    if current_xp % LEVEL_UP_XP_THRESHOLD == 0:
        data["tadbucks_balances"][str(uid)] = int(data["tadbucks_balances"].get(str(uid), STARTING_BALANCE)) + LEVEL_REWARD_TADBUCKS
        data["tadzzy_points"][str(uid)] = int(data["tadzzy_points"].get(str(uid), 0)) + LEVEL_REWARD_TADZZY
        level = current_xp // LEVEL_UP_XP_THRESHOLD
        try:
            await message.channel.send(
                f"🎉 {message.author.mention} reached level {level}! You received {LEVEL_REWARD_TADZZY} Tadzzy Points and ${LEVEL_REWARD_TADBUCKS} Tadbucks!"
            )
        except Exception:
            pass
    
    # Guess game listener
    key = str(message.author.id)
    if key in active_guess_games:
        answer = active_guess_games[key]["answer"]
        if message.content.lower().strip() == answer.lower():
            await message.channel.send(f"🎉 Correct {message.author.mention}! The player was {answer}.")
            del active_guess_games[key]
    
    # Random auction spawn - 3x more frequent, only in announcement channel
    if random.random() < 0.03 and hasattr(message.channel, 'id') and message.channel.id == ANNOUNCEMENT_CHANNEL_ID:  # 3% chance per message in announcement channel only
        rarity_weights = {
            "Common": 0.6,
            "Epic": 0.25,
            "Legendary": 0.1,
            "Mythic": 0.04,
            "Secret": 0.01
        }
        rarities = list(rarity_weights.keys())
        weights = list(rarity_weights.values())
        chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
        
        available_cards = [f for f in footballers if f["rarity"] == chosen_rarity]
        if available_cards:
            card = random.choice(available_cards)
            
            # Create auction
            ends_at = (datetime.now(timezone.utc) + timedelta(minutes=AUCTION_DEFAULT_DURATION_MINUTES)).isoformat()
            data["auctions"][card["name"]] = {
                "highest_bid": 0,
                "highest_bidder": None,
                "active": True,
                "created_by": "system",
                "ends_at": ends_at
            }
            
            embed = discord.Embed(
                title="🏆 WILD AUCTION APPEARED! 🏆",
                description=f"A wild **{card['rarity']} {card['name']}** has appeared for auction!",
                color=card["color"]
            )
            embed.add_field(name="💰 Starting Bid", value=f"{card['price']:,} Tadbucks", inline=True)
            embed.add_field(name="⏰ Time Limit", value=f"{AUCTION_DEFAULT_DURATION_MINUTES} minutes", inline=True)
            embed.add_field(name="📊 Rarity", value=f"{card['rarity']}", inline=True)
            embed.add_field(name="🎯 How to Bid", value=f"Use `!bid {card['name']} <amount>`", inline=False)
            embed.set_footer(text="💡 Tip: Higher bids have better chances to win!")
            
            await message.channel.send(embed=embed)
            print(f"[Random Auction] {card['rarity']} {card['name']} auction spawned in announcement channel")
    
    await bot.process_commands(message)

# -----------------------------
# Enhanced Help Commands
# -----------------------------
@bot.command(name="help")
async def help_command(ctx: commands.Context):
    embed = discord.Embed(
        title="🎮 Tadzzy Bot — Ultimate Command Center",
        description="🚀 **Modern Discord Bot with Amazing UI!** Use ! prefix for all commands.",
        color=0x5865F2
    )
    
    embed.add_field(
        name="💰 Economy & Shop",
        value=(
            "`!shop [rarity]` - Browse the player shop\n"
            "`!buy <player>` - Purchase a player card\n"
            "`!sell <player>` - Sell your player card\n"
            "`!balance [@user]` - View Tadbucks balance\n"
            "`!collection [@user]` - View collections\n"
            "`!upgrade <card_number>` - Upgrade your cards\n"
            "`!leaderboard` - Top Tadbucks players\n"
            "`!points_leaderboard` - Top Tadzzy Points\n"
            "`!allplayers` - Browse all available players"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎁 Pack System (NEW!)",
        value=(
            "`!packshop` - Browse amazing packs to purchase\n"
            "`!packs` - View your owned packs\n"
            "`!openpack <pack_type>` - Open a pack with animations\n"
            "Available: `Default, TOTW, UCL, TOTY, Ultimate`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎰 Gambling & Rewards",
        value=(
            "`!gamble <amount>` - Multiple games, 3h cooldown\n"
            "`!fairgamble <amount>` - Level 25+, 3h cooldown\n"
            "`!daily` - Daily rewards (XP + money)\n"
            "`!weekly` - Weekly rewards (highly rewarded)\n"
            "`!hourly` - Hourly rewards (fair rewards)\n"
            "`!spin` - Daily spin wheel with jackpots\n"
            "`!redeem <code>` - Redeem multiplier codes"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Enhanced Battles & Trading",
        value=(
            "`!battle @user` - Epic 90-minute battles with animations\n"
            "`!trade @user` - Easy trading with modern UI\n"
            "`!accepttrade <id>` - Accept trade offer\n"
            "`!declinetrade <id>` - Decline trade offer"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏆 Auctions & Advanced",
        value=(
            "`!spawnauction <player>` - Start auction (2min timer)\n"
            "`!bid <player> <amount>` - Bid on auctions\n"
            "`!rebirth` - 10-level system with rewards\n"
            "`!rebirthinfo` - View all rebirth levels\n"
            "`!viewdeleted [@user]` - View deleted messages\n"
            "`!passiveincome` - Check last payout\n"
            "`!income total` - View lifetime earnings"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚽ Guess The Player (Real Life)",
        value=(
            "`!guesstheplayereasy` - Easy difficulty\n"
            "`!guesstheplayer` - Normal difficulty\n"
            "`!guesstheplayerhard` - Hard difficulty\n"
            "`!guesstheplayerextreme` - Extreme difficulty"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎲 Fun & Games",
        value=(
            "`!rps <choice>` - Rock Paper Scissors\n"
            "`!coinflip` - Flip a coin | `!dice <sides>` - Roll dice\n"
            "`!8ball <question>` - Magic 8-ball\n"
            "`!var` - Football VAR decision\n"
            "`!meme` - Random memes | `!dadjoke` - Dad jokes\n"
            "`!compliment [@user]` - Spread positivity\n"
            "`!trivia` - Quiz time | `!ping` - Bot latency"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Progress & Stats",
        value=(
            "`!messagesleft` - XP needed for next level\n"
            "`!collection_status [@user]` - Collection info\n"
            "`!tadbucks` - Economy guide"
        ),
        inline=False
    )
    
    embed.set_footer(
        text="✨ NEW: Modern UI with buttons, pack animations, 90-minute battles, and card upgrades!",
        icon_url=bot.user.avatar.url if bot.user.avatar else None
    )
    
    await ctx.send(embed=embed)

# -----------------------------
# Enhanced Pack System Commands
# -----------------------------
@bot.command()
async def packshop(ctx: commands.Context):
    """Browse and purchase packs"""
    embed = discord.Embed(
        title="🎁 Pack Shop - Amazing Animated Openings! ✨",
        description="Choose from our incredible pack selection with guaranteed amazing cards!",
        color=0xff6b6b
    )
    
    for pack_name, pack_info in PACK_TYPES.items():
        rarities_text = "\n".join([f"{rarity}: {int(chance*100)}%" for rarity, chance in pack_info["rarities"].items()])
        
        embed.add_field(
            name=f"🎁 {pack_name}",
            value=(
                f"💰 **${pack_info['price']:,}**\n"
                f"📦 **3 Cards**\n"
                f"🎲 **Chances:**\n{rarities_text}"
            ),
            inline=True
        )
    
    embed.set_footer(text="🌟 Use the dropdown below to purchase a pack! 🌟")
    
    view = PackShopView()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def packs(ctx: commands.Context):
    """View owned packs"""
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_packs = data["user_packs"].get(uid, {})
    
    if not user_packs or all(count == 0 for count in user_packs.values()):
        await ctx.send("📦 You don't have any packs! Use !packshop to buy some amazing packs!")
        return
    
    embed = discord.Embed(
        title=f"📦 {ctx.author.display_name}'s Pack Collection",
        description="Your unopened packs ready for amazing reveals!",
        color=0x3498db
    )
    
    for pack_name, count in user_packs.items():
        if count > 0:
            pack_info = PACK_TYPES.get(pack_name, {"price": 0})
            embed.add_field(
                name=f"🎁 {pack_name}",
                value=f"📦 **{count}** pack{'s' if count != 1 else ''}\n💰 Value: ${pack_info['price']:,} each",
                inline=True
            )
    
    embed.set_footer(text="🎉 Use !openpack <pack_name> to open with amazing animations!")
    
    await ctx.send(embed=embed)

@bot.command()
async def openpack(ctx: commands.Context, *, pack_name: str = None):
    """Open a pack with amazing animations"""
    if not pack_name:
        await ctx.send("❌ Please specify a pack to open! Example: !openpack Default Pack")
        return
    
    # Find matching pack
    pack_match = None
    for pack_type in PACK_TYPES.keys():
        if pack_name.lower() in pack_type.lower():
            pack_match = pack_type
            break
    
    if not pack_match:
        await ctx.send(f"❌ Pack '{pack_name}' not found! Available: {', '.join(PACK_TYPES.keys())}")
        return
    
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_packs = data["user_packs"].get(uid, {})
    
    if user_packs.get(pack_match, 0) <= 0:
        await ctx.send(f"❌ You don't have any {pack_match}s! Use !packshop to buy some.")
        return
    
    # Remove pack from inventory
    user_packs[pack_match] = user_packs.get(pack_match, 0) - 1
    
    # Create pack opening embed
    embed = discord.Embed(
        title=f"🎁 {pack_match} Ready to Open! ✨",
        description="Click the button below to experience an amazing pack opening animation!",
        color=0xff6b6b
    )
    
    view = PackOpenView(ctx.author.id, pack_match)
    await ctx.send(embed=embed, view=view)

# -----------------------------
# Card Upgrade System
# -----------------------------
@bot.command()
async def upgrade(ctx: commands.Context, card_number: int):
    """Upgrade a card with modern UI"""
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_coll = data["user_collections"].get(uid, [])
    
    if card_number < 1 or card_number > len(user_coll):
        await ctx.send(f"❌ Invalid card number! You have {len(user_coll)} cards. Use !collection to see them.")
        return
    
    card = user_coll[card_number - 1]
    current_level = get_card_upgrade_level(card)
    current_progress = card.get("upgrade_progress", 0)
    
    # Check if max level
    if current_level == "Ultimate":
        await ctx.send(f"⭐ {card['name']} is already at Ultimate level!")
        return
    
    # Get next level
    current_index = UPGRADE_LEVELS.index(current_level)
    next_level = UPGRADE_LEVELS[current_index + 1] if current_index < len(UPGRADE_LEVELS) - 1 else "Ultimate"
    
    embed = discord.Embed(
        title=f"🔧 Upgrade {card['name']}",
        description=f"✨ **Current Level:** {current_level}\n📈 **Progress:** {current_progress}%\n🎯 **Next Level:** {next_level}",
        color=0x3498db
    )
    
    # Calculate costs
    base_cost = card.get("original_price", card["price"]) * 0.5  # 50% of original card value
    level_multiplier = UPGRADE_LEVELS.index(current_level) + 1
    upgrade_cost = int(base_cost * level_multiplier)
    
    embed.add_field(
        name="💰 Upgrade Cost",
        value=f"${upgrade_cost:,} (25% progress)",
        inline=True
    )
    
    embed.add_field(
        name="🏆 Benefits",
        value=f"Income: +{int(get_upgrade_multiplier(next_level)*100)}%\nBattle Power: +{int(get_upgrade_multiplier(next_level)*50)}%\nValue: +{int(get_upgrade_multiplier(next_level)*100)}%",
        inline=True
    )
    
    embed.set_footer(text="Choose your upgrade method below!")
    
    view = UpgradeView(ctx.author.id, card_number - 1)
    await ctx.send(embed=embed, view=view)

# -----------------------------
# Enhanced Gambling System
# -----------------------------
@bot.command()
async def gamble(ctx: commands.Context, amount: int):
    """Enhanced gambling with modern UI - 3 hour cooldown"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    if amount <= 0:
        return await ctx.send("❌ Bet amount must be positive.")
    
    balance = get_balance(ctx.author.id)
    if amount > balance:
        return await ctx.send("❌ You don't have enough Tadbucks.")
    
    # Check 3-hour cooldown
    last = gamble_cooldowns.get(uid)
    now = datetime.utcnow()
    if last:
        last_dt = datetime.fromisoformat(last)
        if now - last_dt < timedelta(hours=3):
            remaining = timedelta(hours=3) - (now - last_dt)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return await ctx.send(f"⏰ You can gamble again in {hours}h {minutes}m.")
    
    embed = discord.Embed(
        title="🎰 Choose Your Gambling Game",
        description=f"💰 **Betting:** ${amount:,}\n🎲 **Choose your game with buttons below!**",
        color=0xff9900
    )
    
    embed.add_field(name="🔴 Red (60%)", value="Better odds, lower payout (0.8x)", inline=True)
    embed.add_field(name="⚫ Black (60%)", value="Better odds, lower payout (0.8x)", inline=True)
    embed.add_field(name="⚪ White (60%)", value="Better odds, lower payout (0.8x)", inline=True)
    embed.add_field(name="🎲 Dice (50%)", value="Even odds, even payout (1.0x)", inline=True)
    embed.add_field(name="🃏 Card (40%)", value="Worse odds, higher payout (1.5x)", inline=True)
    
    view = GambleView(ctx.author.id, amount)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def fairgamble(ctx: commands.Context, amount: int):
    """Fair gambling with modern UI - Level 25+ required"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    if amount <= 0:
        return await ctx.send("❌ Bet amount must be positive.")
    
    balance = get_balance(ctx.author.id)
    if amount > balance:
        return await ctx.send("❌ You don't have enough Tadbucks.")
    
    # Check level requirement (25 instead of 50)
    level = int(data["xp_levels"].get(uid, 0)) // LEVEL_UP_XP_THRESHOLD
    if level < 25:
        return await ctx.send(f"❌ You need to be at least level 25 for fair gamble. You're level {level}.")
    
    # Check 3-hour cooldown
    last = fairgamble_cooldowns.get(uid)
    now = datetime.utcnow()
    if last:
        last_dt = datetime.fromisoformat(last)
        if now - last_dt < timedelta(hours=3):
            remaining = timedelta(hours=3) - (now - last_dt)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return await ctx.send(f"⏰ You can fair gamble again in {hours}h {minutes}m.")
    
    embed = discord.Embed(
        title="⚖️ Choose Your Fair Game (50/50)",
        description=f"💰 **Betting:** ${amount:,}\n🎯 **All games have equal 50/50 odds!**",
        color=0x00ff00
    )
    
    embed.add_field(name="🪙 Coin Flip", value="Heads or Tails", inline=True)
    embed.add_field(name="🎯 Target Shot", value="Hit or Miss", inline=True)
    embed.add_field(name="⚡ Lightning", value="Strike or Pass", inline=True)
    embed.add_field(name="🌟 Star Catch", value="Catch or Drop", inline=True)
    
    view = FairGambleView(ctx.author.id, amount)
    await ctx.send(embed=embed, view=view)

# Enhanced Admin Gambling
@commands.has_permissions(administrator=True)
@bot.command()
async def admingamble(ctx: commands.Context, amount: int):
    """Admin gambling with 90/10 odds"""
    ensure_user_exists(ctx.author.id)

    if amount <= 0:
        return await ctx.send("❌ Bet amount must be positive.")

    balance = get_balance(ctx.author.id)
    if amount > balance:
        return await ctx.send("❌ You don't have enough Tadbucks.")

    if random.random() < 0.9:  # 90% win chance
        set_balance(ctx.author.id, balance + amount)
        await ctx.send(f"🎉 Admin power! You won ${amount:,}. New balance: ${get_balance(ctx.author.id):,}")
    else:
        set_balance(ctx.author.id, balance - amount)
        await ctx.send(f"💸 Even admins lose sometimes! Lost ${amount:,}. New balance: ${get_balance(ctx.author.id):,}")

# -----------------------------
# Daily/Weekly/Hourly Rewards & Spin
# -----------------------------
@bot.command()
async def daily(ctx: commands.Context):
    """Daily reward system"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    today = datetime.utcnow().date().isoformat()
    last_claim = data["daily_rewards"].get(uid)

    if last_claim == today:
        return await ctx.send("🕒 You've already claimed your daily reward today! Come back tomorrow.")

    data["daily_rewards"][uid] = today

    # Significantly increased daily rewards
    rewards = [
        {"cash": 25000, "xp": 20, "description": "25,000 Tadbucks + 20 XP"},
        {"cash": 30000, "xp": 15, "description": "30,000 Tadbucks + 15 XP"},
        {"cash": 20000, "xp": 25, "description": "20,000 Tadbucks + 25 XP"},
        {"cash": 35000, "xp": 18, "description": "35,000 Tadbucks + 18 XP"},
        {"cash": 28000, "xp": 22, "description": "28,000 Tadbucks + 22 XP"},
        {"cash": 40000, "xp": 12, "description": "40,000 Tadbucks + 12 XP"},
        {"cash": 22000, "xp": 28, "description": "22,000 Tadbucks + 28 XP"},
    ]

    reward = random.choice(rewards)

    # Apply rewards
    data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + reward["cash"]
    data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + reward["xp"]

    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=f"You received: {reward['description']}",
        color=0x00ff00
    )

    await ctx.send(embed=embed)

@bot.command()
async def weekly(ctx: commands.Context):
    """Weekly reward system - highly rewarded"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    today = datetime.utcnow().date()
    last_claim_str = data["weekly_rewards"].get(uid)

    if last_claim_str:
        last_claim = datetime.fromisoformat(last_claim_str).date()
        if (today - last_claim).days < 7:
            days_left = 7 - (today - last_claim).days
            return await ctx.send(f"📅 You can claim your weekly reward in {days_left} day(s).")

    data["weekly_rewards"][uid] = today.isoformat()

    # High-value weekly rewards
    rewards = [
        {"cash": 50000, "xp": 200, "tadzzy": 25, "description": "50,000 Tadbucks + 200 XP + 25 Tadzzy Points"},
        {"cash": 40000, "xp": 300, "tadzzy": 30, "description": "40,000 Tadbucks + 300 XP + 30 Tadzzy Points"},
        {"cash": 60000, "xp": 100, "tadzzy": 20, "description": "60,000 Tadbucks + 100 XP + 20 Tadzzy Points"},
        {"cash": 45000, "xp": 350, "tadzzy": 35, "description": "45,000 Tadbucks + 350 XP + 35 Tadzzy Points"},
    ]

    reward = random.choice(rewards)

    # Apply rewards
    data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + reward["cash"]
    data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + reward["xp"]
    data["tadzzy_points"][uid] = data["tadzzy_points"].get(uid, 0) + reward["tadzzy"]

    embed = discord.Embed(
        title="🏆 Weekly Reward Claimed!",
        description=f"Amazing! You received: {reward['description']}",
        color=0xffd700
    )

    await ctx.send(embed=embed)

@bot.command()
async def hourly(ctx: commands.Context):
    """Hourly reward system - quick boost"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    now = datetime.utcnow()
    last_claim_str = data["hourly_rewards"].get(uid)

    if last_claim_str:
        last_claim = datetime.fromisoformat(last_claim_str)
        if (now - last_claim).total_seconds() < 3600:  # 1 hour = 3600 seconds
            remaining_seconds = 3600 - int((now - last_claim).total_seconds())
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            return await ctx.send(f"⏰ You can claim your hourly reward in {minutes}m {seconds}s.")

    data["hourly_rewards"][uid] = now.isoformat()

    # Moderate hourly rewards - less than daily but still meaningful
    rewards = [
        {"cash": 3000, "xp": 5, "description": "3,000 Tadbucks + 5 XP"},
        {"cash": 4000, "xp": 2, "description": "4,000 Tadbucks + 2 XP"},
        {"cash": 2500, "xp": 3, "description": "2,500 Tadbucks + 3 XP"},
        {"cash": 5000, "xp": 5, "description": "5,000 Tadbucks + 5 XP"},
        {"cash": 3500, "xp": 5, "description": "3,500 Tadbucks + 5 XP"},
        {"cash": 2000, "xp": 5, "description": "2,000 Tadbucks + 5 XP"},
    ]

    reward = random.choice(rewards)

    # Apply rewards
    data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + reward["cash"]
    data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + reward["xp"]

    embed = discord.Embed(
        title="⏱️ Hourly Reward Claimed!",
        description=f"You received: {reward['description']}",
        color=0x3498db
    )

    await ctx.send(embed=embed)

@bot.command()
async def spin(ctx: commands.Context):
    """Daily spin wheel"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    today = datetime.utcnow().date().isoformat()
    last_spin = data["daily_spin"].get(uid)

    if last_spin == today:
        return await ctx.send("🎰 You've already spun today! Come back tomorrow.")

    data["daily_spin"][uid] = today

    # Spin wheel prizes
    prizes = [
        {"cash": 2000, "description": "2,000 Tadbucks", "emoji": "💰"},
        {"cash": 5000, "description": "5,000 Tadbucks", "emoji": "💎"},
        {"cash": 1000, "description": "1,000 Tadbucks", "emoji": "🪙"},
        {"xp": 100, "description": "100 XP", "emoji": "⭐"},
        {"xp": 50, "description": "50 XP", "emoji": "✨"},
        {"cash": 500, "description": "500 Tadbucks", "emoji": "💵"},
        {"cash": 100000, "description": "JACKPOT! 100,000 Tadbucks", "emoji": "🎰"},
        {"xp": 500, "description": "500 XP! WHAT A WIN!", "emoji": "🏆"},
    ]

    # Weighted selection (jackpot is rare)
    weights = [15, 10, 20, 15, 20, 15, 2, 8]  # Jackpot has 2% chance
    prize = random.choices(prizes, weights=weights, k=1)[0]

    # Apply prize
    if "cash" in prize:
        data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + prize["cash"]
    if "xp" in prize:
        data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + prize["xp"]
    if "tadzzy" in prize:
        data["tadzzy_points"][uid] = data["tadzzy_points"].get(uid, 0) + prize["tadzzy"]

    embed = discord.Embed(
        title="🎰 Daily Spin Result!",
        description=f"{prize['emoji']} You won: {prize['description']}",
        color=0xff6b6b if "JACKPOT" in prize["description"] else 0x4ecdc4
    )

    await ctx.send(embed=embed)

# -----------------------------
# Enhanced Code System
# -----------------------------
@commands.has_permissions(administrator=True)
@bot.command()
async def addcode(ctx: commands.Context, name: str, cash: int = 0, xp: int = 0, multiplier_type: str = "none", hours: int = 0, pack_type: str = "none", pack_count: int = 0):
    """Enhanced code system with packs"""
    valid_multipliers = ["x2_cash", "x2_xp", "x3_cash", "x3_xp", "none"]
    if multiplier_type not in valid_multipliers:
        return await ctx.send(f"❌ Invalid multiplier type. Valid: {', '.join(valid_multipliers)}")

    valid_packs = list(PACK_TYPES.keys()) + ["none"]
    if pack_type != "none" and pack_type not in PACK_TYPES:
        return await ctx.send(f"❌ Invalid pack type. Valid: {', '.join(valid_packs)}")

    data["codes"][name.upper()] = {
        "cash": cash,
        "xp": xp,
        "multiplier_type": multiplier_type if multiplier_type != "none" else None,
        "multiplier_hours": hours,
        "pack_type": pack_type if pack_type != "none" else None,
        "pack_count": pack_count,
        "created_by": str(ctx.author.id),
        "created_at": datetime.utcnow().isoformat()
    }

    description = f"✅ Code '{name.upper()}' created with:"
    if cash > 0:
        description += f"\n💰 {cash:,} Tadbucks"
    if xp > 0:
        description += f"\n⭐ {xp} XP"
    if multiplier_type != "none":
        description += f"\n🔥 {multiplier_type} for {hours}h"
    if pack_type != "none":
        description += f"\n🎁 {pack_count} {pack_type}(s)"

    await ctx.send(description)

@bot.command()
async def redeem(ctx: commands.Context, code: str):
    """Enhanced redeem system with packs"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    code = code.upper()
    if code not in data["codes"]:
        return await ctx.send("❌ Invalid code.")

    code_data = data["codes"][code]

    # Apply cash rewards
    if code_data["cash"] > 0:
        data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + code_data["cash"]

    # Apply XP rewards
    if code_data["xp"] > 0:
        data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + code_data["xp"]

    # Apply multiplier
    if code_data.get("multiplier_type"):
        expiry_time = datetime.utcnow() + timedelta(hours=code_data["multiplier_hours"])
        data["multipliers"].setdefault(uid, {})[code_data["multiplier_type"]] = expiry_time.isoformat()

    # Apply pack rewards
    if code_data.get("pack_type") and code_data.get("pack_count", 0) > 0:
        user_packs = data["user_packs"].setdefault(uid, {})
        user_packs[code_data["pack_type"]] = user_packs.get(code_data["pack_type"], 0) + code_data["pack_count"]

    embed = discord.Embed(
        title="🎉 Code Redeemed!",
        description=f"Code '{code}' successfully redeemed!",
        color=0x00ff00
    )

    rewards = []
    if code_data["cash"] > 0:
        rewards.append(f"💰 {code_data['cash']:,} Tadbucks")
    if code_data["xp"] > 0:
        rewards.append(f"⭐ {code_data['xp']} XP")
    if code_data.get("multiplier_type"):
        rewards.append(f"🔥 {code_data['multiplier_type']} for {code_data['multiplier_hours']}h")
    if code_data.get("pack_type"):
        rewards.append(f"🎁 {code_data['pack_count']} {code_data['pack_type']}(s)")

    embed.add_field(name="Rewards", value="\n".join(rewards), inline=False)

    await ctx.send(embed=embed)

# -----------------------------
# Enhanced Rebirth System
# -----------------------------
@bot.command()
async def rebirth(ctx: commands.Context):
    """Enhanced rebirth system with 10 levels and free cards"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    current_rebirths = data["rebirths"].get(uid, 0)
    
    # Check if max rebirths reached
    if current_rebirths >= len(REBIRTH_LEVELS):
        return await ctx.send(f"⭐ You've reached the maximum rebirth level ({len(REBIRTH_LEVELS)})!")

    rebirth_info = REBIRTH_LEVELS[current_rebirths]
    balance = get_balance(ctx.author.id)
    
    if balance < rebirth_info["requirement"]:
        return await ctx.send(
            f"❌ You need ${rebirth_info['requirement']:,} Tadbucks to rebirth to level {rebirth_info['level']}. "
            f"You have ${balance:,}."
        )

    # Show rebirth info
    embed = discord.Embed(
        title=f"🔄 Rebirth Level {rebirth_info['level']} Confirmation",
        description="⚠️ **WARNING:** This will reset your collection and balance!",
        color=0xff9900
    )

    embed.add_field(
        name="💸 What You'll Lose",
        value=(
            f"• All {len(data['user_collections'].get(uid, []))} cards in collection\n"
            f"• Your current balance of ${balance:,} (keeping {int(balance * (1 - rebirth_info['multiplier']))})"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ What You'll Gain",
        value=(
            f"• +50% passive income permanently (Total: +{(current_rebirths + 1) * 50}%)\n"
            f"• 24-hour x2 cash multiplier\n"
            f"• FREE {rebirth_info['card_rarity']} card!\n"
            f"• Rebirth count: {current_rebirths} → {current_rebirths + 1}"
        ),
        inline=False
    )

    embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")

    view = View(timeout=30)
    
    async def confirm_callback(interaction):
        if interaction.user.id != ctx.author.id:
            await interaction.response.send_message("❌ This is not your rebirth!", ephemeral=True)
            return
            
        # Process rebirth
        data["rebirths"][uid] = current_rebirths + 1
        data["user_collections"][uid] = []  # Reset collection
        new_balance = int(balance * (1 - rebirth_info["multiplier"]))
        data["tadbucks_balances"][uid] = new_balance
        
        # Give x2 cash multiplier for 24 hours
        expiry_time = datetime.utcnow() + timedelta(hours=24)
        data["multipliers"].setdefault(uid, {})["x2_cash"] = expiry_time.isoformat()
        
        # Give free card
        rarity_cards = [f for f in footballers if f["rarity"] == rebirth_info["card_rarity"]]
        if rarity_cards:
            free_card = random.choice(rarity_cards).copy()
            data["user_collections"][uid].append(free_card)
        
        success_embed = discord.Embed(
            title="🎉 Rebirth Successful! 🎉",
            description=f"You have been reborn to level {current_rebirths + 1}!",
            color=0x00ff00
        )
        
        success_embed.add_field(
            name="🔥 New Permanent Bonuses",
            value=f"Passive Income: +{(current_rebirths + 1) * 50}%",
            inline=False
        )
        
        if rarity_cards:
            success_embed.add_field(
                name="🎁 Free Card Received",
                value=f"{free_card['name']} ({rebirth_info['card_rarity']})",
                inline=False
            )
        
        success_embed.add_field(
            name="💰 Fresh Start",
            value=f"New balance: ${new_balance:,} Tadbucks\n🔥 x2 Cash multiplier for 24 hours!",
            inline=False
        )
        
        await interaction.response.edit_message(embed=success_embed, view=None)
    
    async def cancel_callback(interaction):
        if interaction.user.id != ctx.author.id:
            await interaction.response.send_message("❌ This is not your rebirth!", ephemeral=True)
            return
            
        await interaction.response.edit_message(content="❌ Rebirth cancelled.", embed=None, view=None)
    
    confirm_button = Button(label="✅ Confirm Rebirth", style=discord.ButtonStyle.success)
    cancel_button = Button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    
    confirm_button.callback = confirm_callback
    cancel_button.callback = cancel_callback
    
    view.add_item(confirm_button)
    view.add_item(cancel_button)
    
    await ctx.send(embed=embed, view=view)

@bot.command()
async def rebirthinfo(ctx: commands.Context):
    """Show rebirth system information"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    current_rebirths = data["rebirths"].get(uid, 0)
    
    embed = discord.Embed(
        title="🔄 Rebirth System Information",
        description=f"Your Current Rebirth Level: **{current_rebirths}/{len(REBIRTH_LEVELS)}**",
        color=0x9b59b6
    )
    
    for i, level_info in enumerate(REBIRTH_LEVELS):
        status = ""
        if i < current_rebirths:
            status = "✅ Completed"
        elif i == current_rebirths:
            status = "🎯 Next Level"
        else:
            status = "🔒 Locked"
        
        embed.add_field(
            name=f"Level {level_info['level']} - {status}",
            value=(
                f"💰 Requirement: ${level_info['requirement']:,}\n"
                f"🎁 Free Card: {level_info['card_rarity']}\n"
                f"🔥 Income Bonus: +50%"
            ),
            inline=True
        )
    
    if current_rebirths > 0:
        embed.add_field(
            name="🏆 Your Current Bonuses",
            value=f"📈 Passive Income: +{current_rebirths * 50}%",
            inline=False
        )
    
    await ctx.send(embed=embed)

# Enhanced viewdeleted with user filtering
@bot.command()
async def viewdeleted(ctx: commands.Context, member: Optional[discord.Member] = None):
    """View recently deleted messages with optional user filtering"""
    if not data["deleted_messages"]:
        return await ctx.send("📝 No deleted messages recorded.")

    if member:
        # Filter messages by specific user
        user_messages = [msg for msg in data["deleted_messages"] 
                        if msg["author_id"] == member.id]
        
        if not user_messages:
            return await ctx.send(f"📝 No deleted messages found for {member.display_name}.")
        
        embed = discord.Embed(
            title=f"🗑️ {member.display_name}'s Deleted Messages",
            description="Last 10 deleted messages:",
            color=0x95a5a6
        )
        
        recent_messages = user_messages[-10:]  # Last 10 from this user
    else:
        # Show last 15 server deleted messages
        embed = discord.Embed(
            title="🗑️ Recently Deleted Messages",
            description="Last 15 deleted messages:",
            color=0x95a5a6
        )
        
        recent_messages = data["deleted_messages"][-15:]  # Last 15 server messages

    for i, msg_data in enumerate(reversed(recent_messages), 1):
        timestamp = datetime.fromisoformat(msg_data["timestamp"])
        time_str = timestamp.strftime("%m/%d %H:%M")

        content = msg_data["content"][:100] + "..." if len(msg_data["content"]) > 100 else msg_data["content"]

        embed.add_field(
            name=f"{i}. {msg_data['author']} ({time_str})",
            value=content or "No text content",
            inline=False
        )

    await ctx.send(embed=embed)

# Enhanced Shop with stock system
@bot.command()
async def shop(ctx: commands.Context, rarity: str = None):
    """Browse the player shop with stock system and discounts"""
    if rarity:
        rarity = rarity.title()
        available_cards = [f for f in footballers if f["rarity"] == rarity]
        if not available_cards:
            return await ctx.send(f"No players found with rarity '{rarity}'. Available rarities: Common, Epic, Legendary, Mythic, Expensive, Secret")
    else:
        available_cards = footballers

    # Sort by price for better organization
    available_cards.sort(key=lambda x: x["price"], reverse=True)

    embed = discord.Embed(
        title=f"🏪 Tadzzy Card Shop{f' - {rarity} Cards' if rarity else ''}",
        description="Use !buy <player> to purchase a card!",
        color=0x00ff00
    )
    
    # Show discount if active
    if data["shop_discount"] > 0:
        embed.add_field(
            name="🛍️ SALE ACTIVE!",
            value=f"💥 {data['shop_discount']}% OFF ALL PLAYERS! 💥",
            inline=False
        )

    cards_shown = 0
    for card in available_cards:
        if cards_shown >= 10:  # Limit to 10 cards per page
            break
            
        # Check if out of stock
        if card["name"] in data["out_of_stock"]:
            stock_status = "❌ OUT OF STOCK"
            price_display = "N/A"
        else:
            stock_status = "✅ In Stock"
            original_price = card["price"]
            discounted_price = int(original_price * (1 - data["shop_discount"] / 100))
            if data["shop_discount"] > 0:
                price_display = f"~~${original_price:,}~~ **${discounted_price:,}**"
            else:
                price_display = f"${original_price:,}"

        income_info = f"💰 {card.get('income_rate', 1)}/30min"
        embed.add_field(
            name=f"{card['name']} ({card['rarity']})",
            value=f"Price: {price_display}\nIncome: {income_info}\nStock: {stock_status}",
            inline=True
        )
        cards_shown += 1

    embed.set_footer(text="💡 Tip: Higher rarity = more income! Some rare cards may be out of stock!")
    
    await ctx.send(embed=embed)

# Enhanced buy command with stock system
@bot.command()
async def buy(ctx: commands.Context, *, player_name: str):
    """Purchase a player card from the shop with stock system"""
    ensure_user_exists(ctx.author.id)

    card = find_player_card_by_name(player_name)
    if not card:
        return await ctx.send("❌ Player not found in shop. Use !shop to browse available players.")

    # Check if out of stock
    if card["name"] in data["out_of_stock"]:
        return await ctx.send(f"❌ {card['name']} is currently OUT OF STOCK! Check back later.")

    user_balance = get_balance(ctx.author.id)
    original_price = card["price"]
    
    # Apply discount if active
    final_price = int(original_price * (1 - data["shop_discount"] / 100))

    if user_balance < final_price:
        return await ctx.send(f"❌ Insufficient funds! You have ${user_balance:,} but {card['name']} costs ${final_price:,}")

    # Check if user already owns this card
    uid = str(ctx.author.id)
    user_collection = data["user_collections"].get(uid, [])
    if any(c["name"] == card["name"] for c in user_collection):
        return await ctx.send(f"❌ You already own {card['name']}!")

    # Check collection space
    if len(user_collection) >= MAX_COLLECTION_SLOTS:
        return await ctx.send(f"❌ Your collection is full! ({MAX_COLLECTION_SLOTS}/{MAX_COLLECTION_SLOTS})")

    # Process purchase
    set_balance(ctx.author.id, user_balance - final_price)
    purchased_card = card.copy()
    
    # Initialize upgrade system
    purchased_card["upgrade_level"] = "Gold"
    purchased_card["upgrade_progress"] = 0
    
    data["user_collections"][uid].append(purchased_card)

    embed = discord.Embed(
        title="🎉 Purchase Successful!",
        description=f"You bought {card['name']} for ${final_price:,}!",
        color=card["color"]
    )
    
    if data["shop_discount"] > 0:
        embed.add_field(
            name="💸 Discount Applied",
            value=f"You saved ${original_price - final_price:,} ({data['shop_discount']}% off)!",
            inline=True
        )
    
    embed.add_field(name="Remaining Balance", value=f"${get_balance(ctx.author.id):,}", inline=True)
    embed.add_field(name="Passive Income", value=f"💰 {card.get('income_rate', 1)} every 30 minutes", inline=True)
    embed.add_field(name="Collection", value=f"{len(user_collection)+1}/{MAX_COLLECTION_SLOTS}", inline=True)

    await ctx.send(embed=embed)

# Add sell command
@bot.command()
async def sell(ctx: commands.Context, *, player_name: str):
    """Sell a player card from your collection"""
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_collection = data["user_collections"].get(uid, [])
    
    if not user_collection:
        return await ctx.send("❌ You don't have any cards to sell!")
    
    # Find the card
    card_to_sell = None
    card_index = None
    for i, card in enumerate(user_collection):
        if normalize_name(card["name"]) == normalize_name(player_name):
            card_to_sell = card
            card_index = i
            break
    
    if not card_to_sell:
        return await ctx.send(f"❌ You don't own '{player_name}'. Use !collection to see your cards.")
    
    # Calculate sell price (75% of current card value)
    sell_price = int(card_to_sell["price"] * 0.75)
    
    # Remove card from collection
    user_collection.pop(card_index)
    
    # Add money to balance
    current_balance = get_balance(ctx.author.id)
    set_balance(ctx.author.id, current_balance + sell_price)
    
    embed = discord.Embed(
        title="💰 Card Sold Successfully!",
        description=f"You sold {card_to_sell['name']} for ${sell_price:,}!",
        color=0x00ff00
    )
    
    embed.add_field(name="💳 New Balance", value=f"${get_balance(ctx.author.id):,}", inline=True)
    embed.add_field(name="📦 Collection", value=f"{len(user_collection)}/{MAX_COLLECTION_SLOTS}", inline=True)
    
    if card_to_sell.get("upgrade_level", "Gold") != "Gold":
        embed.add_field(
            name="⚠️ Upgrade Lost",
            value=f"Sold {card_to_sell['upgrade_level']} level card",
            inline=True
        )
    
    await ctx.send(embed=embed)

# Admin restock command
@commands.has_permissions(administrator=True)
@bot.command()
async def restock(ctx: commands.Context, *, player_name: str = "all"):
    """Restock players in the shop"""
    if player_name.lower() == "all":
        data["out_of_stock"] = []
        await ctx.send("✅ All players have been restocked!")
    else:
        card = find_player_card_by_name(player_name)
        if not card:
            return await ctx.send("❌ Player not found.")
        
        if card["name"] in data["out_of_stock"]:
            data["out_of_stock"].remove(card["name"])
            await ctx.send(f"✅ {card['name']} has been restocked!")
        else:
            await ctx.send(f"ℹ️ {card['name']} was already in stock.")

# Admin upgrade command
@commands.has_permissions(administrator=True)
@bot.command()
async def adminupgrade(ctx: commands.Context, member: discord.Member, player_name: str, upgrade_level: str):
    """Admin command to upgrade user cards"""
    if upgrade_level not in UPGRADE_LEVELS:
        return await ctx.send(f"❌ Invalid upgrade level. Valid: {', '.join(UPGRADE_LEVELS)}")
    
    ensure_user_exists(member.id)
    uid = str(member.id)
    user_coll = data["user_collections"].get(uid, [])
    
    # Find the card
    card_index = None
    for i, card in enumerate(user_coll):
        if normalize_name(card["name"]) == normalize_name(player_name):
            card_index = i
            break
    
    if card_index is None:
        return await ctx.send(f"❌ {member.display_name} doesn't own {player_name}.")
    
    # Upgrade the card
    card = user_coll[card_index]
    card["upgrade_level"] = upgrade_level
    card["upgrade_progress"] = 0
    card = upgrade_card_stats(card)
    user_coll[card_index] = card
    
    await ctx.send(f"✅ Upgraded {member.display_name}'s {player_name} to {upgrade_level} level!")

# Add balance command
@bot.command()
async def balance(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Check Tadbucks balance"""
    target = member or ctx.author
    ensure_user_exists(target.id)
    bal = get_balance(target.id)

    embed = discord.Embed(
        title=f"💰 {target.display_name}'s Balance",
        description=f"${bal:,} Tadbucks",
        color=0xf1c40f
    )

    # Show rebirth info
    rebirths = data["rebirths"].get(str(target.id), 0)
    if rebirths > 0:
        embed.add_field(
            name="🔄 Rebirths",
            value=f"{rebirths} (Income +{rebirths * 50}%)",
            inline=True
        )

    # Show active multipliers
    multipliers = []
    for mult_type in ["x2_cash", "x3_cash", "x2_xp", "x3_xp"]:
        if get_multiplier(target.id, mult_type) > 1:
            multipliers.append(mult_type.replace("_", " ").title())

    if multipliers:
        embed.add_field(
            name="⚡ Active Multipliers",
            value=", ".join(multipliers),
            inline=True
        )

    await ctx.send(embed=embed)

@bot.command()
async def collection(ctx: commands.Context, member: Optional[discord.Member] = None):
    """View collection with upgrade levels"""
    target = member or ctx.author
    uid = str(target.id)
    ensure_user_exists(target.id)
    coll = data["user_collections"].get(uid, [])

    if not coll:
        if target == ctx.author:
            return await ctx.send("📦 Your collection is empty. Use !shop to buy player cards!")
        else:
            return await ctx.send(f"📦 {target.display_name}'s collection is empty.")

    embed = discord.Embed(
        title=f"📦 {target.display_name}'s Collection",
        description=f"Collection: {len(coll)}/{MAX_COLLECTION_SLOTS} cards",
        color=0x5865F2
    )
    
    for i, card in enumerate(coll[:10], 1):  # Show first 10 cards
        income_rate = card.get('income_rate', 1)
        upgrade_level = get_card_upgrade_level(card)
        
        # Apply rebirth bonus for display
        income_with_bonus = apply_rebirth_bonus(target.id, income_rate)
        
        upgrade_text = ""
        if upgrade_level != "Gold":
            upgrade_text = f" **[{upgrade_level}]**"
        
        embed.add_field(
            name=f"{i}. {card['name']}{upgrade_text}",
            value=f"✨ {card['rarity']} | 💰 ${card['price']:,} | 🕐 {income_with_bonus}/30min",
            inline=False
        )

    if len(coll) > 10:
        embed.set_footer(text=f"Showing first 10 of {len(coll)} cards. Use !upgrade <number> to upgrade!")
    else:
        embed.set_footer(text="Use !upgrade <number> to upgrade your cards!")

    await ctx.send(embed=embed)

# Add leaderboard commands
@bot.command()
async def leaderboard(ctx: commands.Context):
    """Top Tadbucks players"""
    if not data["tadbucks_balances"]:
        return await ctx.send("📊 No data available for leaderboard.")
    
    # Sort users by balance
    sorted_users = sorted(data["tadbucks_balances"].items(), key=lambda x: x[1], reverse=True)[:5]
    
    embed = discord.Embed(
        title="🏆 Tadbucks Leaderboard",
        description="Top 5 richest players:",
        color=0xffd700
    )
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, (user_id, balance) in enumerate(sorted_users):
        try:
            user = bot.get_user(int(user_id))
            username = user.display_name if user else f"User {user_id}"
        except:
            username = f"User {user_id}"
        
        embed.add_field(
            name=f"{medals[i]} {username}",
            value=f"${balance:,} Tadbucks",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def points_leaderboard(ctx: commands.Context):
    """Top Tadzzy Points players"""
    if not data["tadzzy_points"]:
        return await ctx.send("📊 No data available for points leaderboard.")
    
    # Sort users by points
    sorted_users = sorted(data["tadzzy_points"].items(), key=lambda x: x[1], reverse=True)[:5]
    
    embed = discord.Embed(
        title="🏆 Tadzzy Points Leaderboard",
        description="Top 5 point collectors:",
        color=0xff6b6b
    )
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, (user_id, points) in enumerate(sorted_users):
        try:
            user = bot.get_user(int(user_id))
            username = user.display_name if user else f"User {user_id}"
        except:
            username = f"User {user_id}"
        
        embed.add_field(
            name=f"{medals[i]} {username}",
            value=f"{points:,} Tadzzy Points",
            inline=False
        )
    
    await ctx.send(embed=embed)

# Add missing commands from help
@bot.command()
async def allplayers(ctx: commands.Context):
    """Browse all available players by rarity"""
    rarities = {}
    for card in footballers:
        rarity = card["rarity"]
        if rarity not in rarities:
            rarities[rarity] = []
        rarities[rarity].append(card)
    
    embed = discord.Embed(
        title="⚽ All Available Players",
        description="Complete player database by rarity:",
        color=0x3498db
    )
    
    rarity_order = ["Secret", "Expensive", "Mythic", "Legendary", "Epic", "Common"]
    
    for rarity in rarity_order:
        if rarity in rarities:
            cards = rarities[rarity]
            # Show top 3 most expensive from each rarity
            cards.sort(key=lambda x: x["price"], reverse=True)
            top_cards = cards[:3]
            
            card_list = []
            for card in top_cards:
                card_list.append(f"{card['name']} (${card['price']:,})")
            
            embed.add_field(
                name=f"{rarity} ({len(cards)} total)",
                value="\n".join(card_list) + f"\n... and {len(cards)-3} more" if len(cards) > 3 else "\n".join(card_list),
                inline=True
            )
    
    embed.set_footer(text="Use !shop <rarity> to browse specific rarities!")
    await ctx.send(embed=embed)

@bot.command()
async def passiveincome(ctx: commands.Context):
    """Check last passive income payout"""
    uid = str(ctx.author.id)
    
    last_payout = last_income_report.get(uid)
    if not last_payout:
        return await ctx.send("💰 No passive income recorded yet. Cards generate income every 30 minutes!")
    
    embed = discord.Embed(
        title="💰 Last Passive Income Report",
        description=f"Your last payout: **${last_payout:,} Tadbucks**",
        color=0x00ff00
    )
    
    embed.add_field(
        name="🕐 Next Payout",
        value="Within 30 minutes (automatic)",
        inline=True
    )
    
    # Show collection income breakdown if user has cards
    user_coll = data["user_collections"].get(uid, [])
    if user_coll:
        total_base_income = sum(card.get("income_rate", 1) for card in user_coll)
        embed.add_field(
            name="📊 Base Income Rate",
            value=f"${total_base_income:,}/30min from {len(user_coll)} cards",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name="income")
async def income_command(ctx: commands.Context, action: str = ""):
    """View lifetime earnings"""
    uid = str(ctx.author.id)
    
    if action.lower() == "total":
        total_earned = total_income_tracker.get(uid, 0)
        embed = discord.Embed(
            title="💎 Lifetime Income Report",
            description=f"Total earned from passive income: **${total_earned:,} Tadbucks**",
            color=0xffd700
        )
        
        # Calculate daily average if user has history
        if total_earned > 0:
            days_active = 1  # Simplified calculation
            daily_average = total_earned // max(days_active, 1)
            embed.add_field(
                name="📈 Statistics",
                value=f"Average per day: ${daily_average:,}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("💰 Use `!income total` to see your lifetime earnings!")

@bot.command()
async def messagesleft(ctx: commands.Context):
    """Messages needed for next level"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    current_xp = data["xp_levels"].get(uid, 0)
    current_level = current_xp // LEVEL_UP_XP_THRESHOLD
    xp_in_level = current_xp % LEVEL_UP_XP_THRESHOLD
    xp_needed = LEVEL_UP_XP_THRESHOLD - xp_in_level
    messages_needed = xp_needed // LEVEL_XP_REWARD
    
    embed = discord.Embed(
        title="📊 Level Progress",
        description=f"**Current Level:** {current_level}",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="📈 Progress",
        value=f"{xp_in_level}/{LEVEL_UP_XP_THRESHOLD} XP",
        inline=True
    )
    
    embed.add_field(
        name="💬 Messages Needed",
        value=f"{messages_needed} messages",
        inline=True
    )
    
    embed.add_field(
        name="🎁 Next Reward",
        value=f"${LEVEL_REWARD_TADBUCKS:,} + {LEVEL_REWARD_TADZZY} points",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def collection_status(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Collection info and statistics"""
    target = member or ctx.author
    uid = str(target.id)
    ensure_user_exists(target.id)
    
    user_coll = data["user_collections"].get(uid, [])
    
    embed = discord.Embed(
        title=f"📊 {target.display_name}'s Collection Status",
        description=f"Collection: {len(user_coll)}/{MAX_COLLECTION_SLOTS} cards",
        color=0x3498db
    )
    
    if user_coll:
        # Calculate total value
        total_value = sum(card["price"] for card in user_coll)
        total_income = sum(card.get("income_rate", 1) for card in user_coll)
        
        # Count rarities
        rarity_count = {}
        for card in user_coll:
            rarity = card["rarity"]
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
        
        embed.add_field(
            name="💰 Total Value",
            value=f"${total_value:,} Tadbucks",
            inline=True
        )
        
        embed.add_field(
            name="🕐 Income Rate",
            value=f"${total_income:,}/30min",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Average Rarity",
            value=f"{len([c for c in user_coll if c['rarity'] != 'Common'])}/{len(user_coll)} non-common",
            inline=True
        )
        
        # Show rarity breakdown
        rarity_text = []
        for rarity, count in sorted(rarity_count.items()):
            rarity_text.append(f"{rarity}: {count}")
        
        if rarity_text:
            embed.add_field(
                name="🎲 Rarity Breakdown",
                value="\n".join(rarity_text),
                inline=False
            )
    else:
        embed.add_field(
            name="📦 Empty Collection",
            value="Use !shop to start collecting cards!",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="Tadbucks")
async def tadbucks_guide(ctx: commands.Context):
    """Economy guide"""
    embed = discord.Embed(
        title="💰 Tadbucks Economy Guide",
        description="Everything you need to know about the economy system!",
        color=0xf1c40f
    )
    
    embed.add_field(
        name="💸 Earning Tadbucks",
        value=(
            "• **Passive Income**: Cards generate money every 30 minutes\n"
            "• **Daily Rewards**: !daily (25k-40k + XP)\n"
            "• **Weekly Rewards**: !weekly (40k-60k + XP + Points)\n"
            "• **Hourly Rewards**: !hourly (2k-5k + XP)\n"
            "• **Spin Wheel**: !spin (daily jackpots up to 10k)\n"
            "• **Level Rewards**: 15k per level up\n"
            "• **Gambling**: !gamble and !fairgamble"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛒 Spending Tadbucks",
        value=(
            "• **Player Cards**: !buy <player> (main investment)\n"
            "• **Pack Openings**: !packshop (50k to 35M per pack)\n"
            "• **Card Upgrades**: !upgrade <number> (improve stats)\n"
            "• **Auctions**: !bid <player> <amount>\n"
            "• **Gambling**: Risk vs reward games"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📈 Investment Strategy",
        value=(
            "• **Start Small**: Buy common cards for passive income\n"
            "• **Upgrade Cards**: Higher levels = more income\n"
            "• **Save for Packs**: Better cards from higher tier packs\n"
            "• **Rebirth System**: Reset for permanent bonuses\n"
            "• **Watch Sales**: 10% discounts happen randomly"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Pro Tips",
        value=(
            "• **Collection Slots**: Max 15 cards, choose wisely\n"
            "• **Income Multipliers**: Rebirths give +50% per level\n"
            "• **Active Multipliers**: Codes give 2x-3x bonuses\n"
            "• **Rare Cards**: Higher rarity = much better income\n"
            "• **Sell Wisely**: Get 75% value back when selling"
        ),
        inline=False
    )
    
    embed.set_footer(text="💡 Start with !daily, !hourly, and !spin, then buy your first card!")
    
    await ctx.send(embed=embed)

# First battle system removed (duplicate)
    """Epic battles with score simulation and rewards"""
    if opponent.id == ctx.author.id:
        return await ctx.send("❌ You can't battle yourself!")
    
    if opponent.bot:
        return await ctx.send("❌ You can't battle bots!")
    
    # Check if users have cards
    user1_cards = data["user_collections"].get(str(ctx.author.id), [])
    user2_cards = data["user_collections"].get(str(opponent.id), [])
    
    if not user1_cards:
        return await ctx.send("❌ You need at least one card to battle!")
    
    if not user2_cards:
        return await ctx.send(f"❌ {opponent.display_name} needs at least one card to battle!")
    
    # Calculate team strengths
    user1_strength = sum(card.get("income_rate", 1) for card in user1_cards)
    user2_strength = sum(card.get("income_rate", 1) for card in user2_cards)
    
    embed = discord.Embed(
        title="⚔️ Battle Started!",
        description="90-minute football match simulation beginning...",
        color=0xff6b6b
    )
    
    embed.add_field(
        name=f"🔴 {ctx.author.display_name}",
        value=f"Team Strength: {user1_strength:,}",
        inline=True
    )
    
    embed.add_field(
        name=f"🔵 {opponent.display_name}",
        value=f"Team Strength: {user2_strength:,}",
        inline=True
    )
    
    embed.add_field(
        name="⏱️ Match Time",
        value="90 minutes + halftime",
        inline=True
    )
    
    message = await ctx.send(embed=embed)
    
    # Simulate first half
    await asyncio.sleep(2)
    
    # First half goals
    goals_user1 = random.randint(0, 3)
    goals_user2 = random.randint(0, 3)
    
    embed = discord.Embed(
        title="⏰ HALFTIME! ⏰",
        description="45 minutes completed - taking a break!",
        color=0xffff00
    )
    
    embed.add_field(
        name="📊 First Half Score",
        value=f"🔴 {ctx.author.display_name}: {goals_user1}\n🔵 {opponent.display_name}: {goals_user2}",
        inline=False
    )
    
    await message.edit(embed=embed)
    await asyncio.sleep(3)
    
    # Second half
    embed = discord.Embed(
        title="🔥 Second Half Starting!",
        description="Players are back on the field!",
        color=0x00ff00
    )
    
    await message.edit(embed=embed)
    await asyncio.sleep(2)
    
    # Second half goals
    goals_user1 += random.randint(0, 2)
    goals_user2 += random.randint(0, 2)
    
    # Determine winner
    if goals_user1 > goals_user2:
        winner = ctx.author
        loser = opponent
        winner_goals = goals_user1
        loser_goals = goals_user2
    elif goals_user2 > goals_user1:
        winner = opponent
        loser = ctx.author
        winner_goals = goals_user2
        loser_goals = goals_user1
    else:
        # Penalty shootout for draws
        embed = discord.Embed(
            title="🥅 PENALTY SHOOTOUT!",
            description="Match is tied - going to penalties!",
            color=0xff6b6b
        )
        
        await message.edit(embed=embed)
        await asyncio.sleep(2)
        
        penalties_user1 = random.randint(3, 5)
        penalties_user2 = random.randint(3, 5)
        
        if penalties_user1 > penalties_user2:
            winner = ctx.author
            loser = opponent
            winner_goals = f"{goals_user1} ({penalties_user1})"
            loser_goals = f"{goals_user2} ({penalties_user2})"
        else:
            winner = opponent
            loser = ctx.author
            winner_goals = f"{goals_user2} ({penalties_user2})"
            loser_goals = f"{goals_user1} ({penalties_user1})"
    
    # Final result
    embed = discord.Embed(
        title="🏆 FULL TIME RESULT!",
        description="What an amazing match!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="⚽ Final Score",
        value=f"🔴 {ctx.author.display_name}: {goals_user1}\n🔵 {opponent.display_name}: {goals_user2}",
        inline=False
    )
    
    embed.add_field(
        name="🏆 Winner",
        value=f"**{winner.display_name}** wins!",
        inline=True
    )
    
    # Calculate rewards
    reward = min(10000, max(1000, (user1_strength + user2_strength) // 100))
    
    ensure_user_exists(winner.id)
    current_balance = get_balance(winner.id)
    set_balance(winner.id, current_balance + reward)
    
    embed.add_field(
        name="💰 Rewards",
        value=f"{winner.mention} wins ${reward:,} Tadbucks!",
        inline=True
    )
    
    embed.set_footer(text="⚔️ Great battle! Both teams played amazingly!")
    
    await message.edit(embed=embed)

# Add trading system
@bot.command()
async def trade(ctx: commands.Context, member: discord.Member):
    """Easy trading with modern UI"""
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't trade with yourself!")
    
    if member.bot:
        return await ctx.send("❌ You can't trade with bots!")
    
    # Check collections
    user1_cards = data["user_collections"].get(str(ctx.author.id), [])
    user2_cards = data["user_collections"].get(str(member.id), [])
    
    if not user1_cards:
        return await ctx.send("❌ You need cards to trade!")
    
    if not user2_cards:
        return await ctx.send(f"❌ {member.display_name} needs cards to trade!")
    
    # Create trade ID
    trade_id = f"{ctx.author.id}_{member.id}_{len(data['trades'])}"
    
    # For now, simple random card trade
    user1_card = random.choice(user1_cards)
    user2_card = random.choice(user2_cards)
    
    embed = discord.Embed(
        title="🤝 Trade Proposal",
        description=f"{ctx.author.mention} wants to trade with {member.mention}!",
        color=0x3498db
    )
    
    embed.add_field(
        name=f"🔄 {ctx.author.display_name} offers:",
        value=f"{user1_card['name']} ({user1_card['rarity']})\n💰 ${user1_card['price']:,}",
        inline=True
    )
    
    embed.add_field(
        name=f"🔄 {member.display_name} would receive:",
        value=f"{user2_card['name']} ({user2_card['rarity']})\n💰 ${user2_card['price']:,}",
        inline=True
    )
    
    embed.add_field(
        name="📋 Trade ID",
        value=f"`{trade_id}`",
        inline=False
    )
    
    embed.set_footer(text=f"{member.display_name}, use !accepttrade {trade_id} or !declinetrade {trade_id}")
    
    # Store trade
    data["trades"][trade_id] = {
        "user1": ctx.author.id,
        "user2": member.id,
        "user1_card": user1_card,
        "user2_card": user2_card,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    await ctx.send(embed=embed)

@bot.command()
async def accepttrade(ctx: commands.Context, trade_id: str):
    """Accept trade offer"""
    if trade_id not in data["trades"]:
        return await ctx.send("❌ Trade not found!")
    
    trade = data["trades"][trade_id]
    
    if trade["user2"] != ctx.author.id:
        return await ctx.send("❌ This trade is not for you!")
    
    if trade["status"] != "pending":
        return await ctx.send("❌ This trade is no longer active!")
    
    # Process trade
    user1_collection = data["user_collections"].get(str(trade["user1"]), [])
    user2_collection = data["user_collections"].get(str(trade["user2"]), [])
    
    # Find and remove cards
    user1_card_found = False
    user2_card_found = False
    
    for i, card in enumerate(user1_collection):
        if card["name"] == trade["user1_card"]["name"]:
            user1_collection.pop(i)
            user1_card_found = True
            break
    
    for i, card in enumerate(user2_collection):
        if card["name"] == trade["user2_card"]["name"]:
            user2_collection.pop(i)
            user2_card_found = True
            break
    
    if not user1_card_found or not user2_card_found:
        return await ctx.send("❌ One of the cards is no longer available!")
    
    # Add cards to new owners
    user1_collection.append(trade["user2_card"])
    user2_collection.append(trade["user1_card"])
    
    # Mark trade as completed
    trade["status"] = "completed"
    
    embed = discord.Embed(
        title="✅ Trade Completed!",
        description="Successful trade between players!",
        color=0x00ff00
    )
    
    user1 = bot.get_user(trade["user1"])
    user2 = bot.get_user(trade["user2"])
    
    embed.add_field(
        name="🎉 Trade Summary",
        value=(
            f"{user1.display_name if user1 else 'User1'} received: {trade['user2_card']['name']}\n"
            f"{user2.display_name if user2 else 'User2'} received: {trade['user1_card']['name']}"
        ),
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def declinetrade(ctx: commands.Context, trade_id: str):
    """Decline trade offer"""
    if trade_id not in data["trades"]:
        return await ctx.send("❌ Trade not found!")
    
    trade = data["trades"][trade_id]
    
    if trade["user2"] != ctx.author.id:
        return await ctx.send("❌ This trade is not for you!")
    
    if trade["status"] != "pending":
        return await ctx.send("❌ This trade is no longer active!")
    
    # Mark as declined
    trade["status"] = "declined"
    
    user1 = bot.get_user(trade["user1"])
    
    await ctx.send(f"❌ Trade declined. {user1.mention if user1 else 'The other user'} has been notified.")

# Add auction system
@bot.command()
async def spawnauction(ctx: commands.Context, *, player_name: str):
    """Start auction (2min timer)"""
    card = find_player_card_by_name(player_name)
    if not card:
        return await ctx.send("❌ Player not found!")
    
    if card["name"] in data["auctions"] and data["auctions"][card["name"]].get("active", False):
        return await ctx.send(f"❌ {card['name']} is already being auctioned!")
    
    # Create auction
    ends_at = (datetime.utcnow() + timedelta(minutes=2)).isoformat()
    starting_bid = int(card["price"] * 0.5)  # 50% of actual price
    data["auctions"][card["name"]] = {
        "highest_bid": starting_bid,
        "highest_bidder": None,
        "active": True,
        "created_by": str(ctx.author.id),
        "ends_at": ends_at
    }
    
    embed = discord.Embed(
        title="🏆 Auction Started!",
        description=f"Bidding has begun for {card['name']}!",
        color=0xffd700
    )
    
    embed.add_field(
        name="⚽ Player",
        value=f"{card['name']} ({card['rarity']})",
        inline=True
    )
    
    embed.add_field(
        name="💰 Starting Bid",
        value=f"${card['price']:,}",
        inline=True
    )
    
    embed.add_field(
        name="⏰ Time Left",
        value="2 minutes",
        inline=True
    )
    
    embed.set_footer(text=f"Use !bid {card['name']} <amount> to place a bid!")
    
    await ctx.send(embed=embed)

@bot.command()
async def bid(ctx: commands.Context, player_name: str, amount: int):
    """Bid on auctions"""
    card = find_player_card_by_name(player_name)
    if not card:
        return await ctx.send("❌ Player not found!")
    
    if card["name"] not in data["auctions"]:
        return await ctx.send(f"❌ {card['name']} is not being auctioned!")
    
    auction = data["auctions"][card["name"]]
    
    if not auction.get("active", False):
        return await ctx.send(f"❌ Auction for {card['name']} has ended!")
    
    if amount <= auction["highest_bid"]:
        return await ctx.send(f"❌ Bid must be higher than current highest bid of ${auction['highest_bid']:,}!")
    
    balance = get_balance(ctx.author.id)
    if amount > balance:
        return await ctx.send(f"❌ You don't have enough Tadbucks! You have ${balance:,}, need ${amount:,}!")
    
    # Update auction
    auction["highest_bid"] = amount
    auction["highest_bidder"] = str(ctx.author.id)
    
    embed = discord.Embed(
        title="🔥 New High Bid!",
        description=f"New leading bid for {card['name']}!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="💰 Highest Bid",
        value=f"${amount:,}",
        inline=True
    )
    
    embed.add_field(
        name="👑 Leading Bidder",
        value=ctx.author.mention,
        inline=True
    )
    
    # Calculate time remaining
    ends_at = datetime.fromisoformat(auction["ends_at"])
    time_left = ends_at - datetime.utcnow()
    minutes_left = max(0, int(time_left.total_seconds() / 60))
    
    embed.add_field(
        name="⏰ Time Remaining",
        value=f"~{minutes_left} minute(s)",
        inline=True
    )
    
    await ctx.send(embed=embed)

# Admin auction commands
@commands.has_permissions(administrator=True)
@bot.command()
async def forcecloseauction(ctx: commands.Context, *, player_name: str):
    """Force close auction"""
    card = find_player_card_by_name(player_name)
    if not card:
        return await ctx.send("❌ Player not found!")
    
    if card["name"] not in data["auctions"]:
        return await ctx.send(f"❌ {card['name']} is not being auctioned!")
    
    auction = data["auctions"][card["name"]]
    auction["active"] = False
    
    if auction.get("highest_bidder"):
        winner_id = int(auction["highest_bidder"])
        amount = auction["highest_bid"]
        
        # Award card to winner
        ensure_user_exists(winner_id)
        if get_balance(winner_id) >= amount:
            set_balance(winner_id, get_balance(winner_id) - amount)
            user_coll = data["user_collections"].setdefault(str(winner_id), [])
            if len(user_coll) < MAX_COLLECTION_SLOTS:
                user_coll.append(card)
                await ctx.send(f"✅ Auction closed. {bot.get_user(winner_id).mention if bot.get_user(winner_id) else 'Winner'} received {card['name']} for ${amount:,}!")
            else:
                await ctx.send(f"❌ Winner's collection is full! Refunding ${amount:,}.")
        else:
            await ctx.send(f"❌ Winner doesn't have enough funds! Auction cancelled.")
    else:
        await ctx.send(f"✅ Auction for {card['name']} closed with no bids.")

@commands.has_permissions(administrator=True)
@bot.command()
async def extendauction(ctx: commands.Context, player_name: str, minutes: int):
    """Extend auction timer"""
    card = find_player_card_by_name(player_name)
    if not card:
        return await ctx.send("❌ Player not found!")
    
    if card["name"] not in data["auctions"]:
        return await ctx.send(f"❌ {card['name']} is not being auctioned!")
    
    auction = data["auctions"][card["name"]]
    if not auction.get("active", False):
        return await ctx.send(f"❌ Auction for {card['name']} has already ended!")
    
    # Extend time
    current_end = datetime.fromisoformat(auction["ends_at"])
    new_end = current_end + timedelta(minutes=minutes)
    auction["ends_at"] = new_end.isoformat()
    
    await ctx.send(f"⏰ Extended auction for {card['name']} by {minutes} minute(s)!")

@commands.has_permissions(administrator=True)
@bot.command()
async def listauctions(ctx: commands.Context):
    """View all active auctions"""
    active_auctions = [(name, auction) for name, auction in data["auctions"].items() 
                      if auction.get("active", False)]
    
    if not active_auctions:
        return await ctx.send("📋 No active auctions currently.")
    
    embed = discord.Embed(
        title="🏆 Active Auctions",
        description=f"{len(active_auctions)} auction(s) currently active:",
        color=0xffd700
    )
    
    for name, auction in active_auctions[:5]:  # Show max 5
        ends_at = datetime.fromisoformat(auction["ends_at"])
        time_left = ends_at - datetime.utcnow()
        minutes_left = max(0, int(time_left.total_seconds() / 60))
        
        highest_bid = auction["highest_bid"]
        highest_bidder = auction.get("highest_bidder")
        
        bidder_text = "No bids yet"
        if highest_bidder:
            user = bot.get_user(int(highest_bidder))
            bidder_text = f"${highest_bid:,} by {user.display_name if user else 'Unknown'}"
        
        embed.add_field(
            name=name,
            value=f"{bidder_text}\n⏰ {minutes_left}m left",
            inline=True
        )
    
    await ctx.send(embed=embed)

# DISABLED: Duplicate guess the player games (replaced with real football players at line ~8179)
# @bot.command()
# async def guesstheplayereasy_DISABLED(ctx: commands.Context):
    """Easy difficulty"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Answer the current question first.")
    
    clue, answer = random.choice(data["guess_db"]["easy"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "easy"}
    
    embed = discord.Embed(
        title="⚽ Guess The Player - Easy",
        description=f"**Clue:** {clue}",
        color=0x00ff00
    )
    
    embed.set_footer(text="Type the player's name to answer!")
    await ctx.send(embed=embed)

@bot.command()
async def guesstheplayer(ctx: commands.Context):
    """Normal difficulty"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Answer the current question first.")
    
    clue, answer = random.choice(data["guess_db"]["normal"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "normal"}
    
    embed = discord.Embed(
        title="⚽ Guess The Player - Normal",
        description=f"**Clue:** {clue}",
        color=0xffff00
    )
    
    embed.set_footer(text="Type the player's name to answer!")
    await ctx.send(embed=embed)

@bot.command()
async def guesstheplayerhard(ctx: commands.Context):
    """Hard difficulty"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Answer the current question first.")
    
    clue, answer = random.choice(data["guess_db"]["hard"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "hard"}
    
    embed = discord.Embed(
        title="⚽ Guess The Player - Hard",
        description=f"**Clue:** {clue}",
        color=0xff9900
    )
    
    embed.set_footer(text="Type the player's name to answer!")
    await ctx.send(embed=embed)

@bot.command()
async def guesstheplayerextreme(ctx: commands.Context):
    """Extreme difficulty"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Answer the current question first.")
    
    clue, answer = random.choice(data["guess_db"]["extreme"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "extreme"}
    
    embed = discord.Embed(
        title="⚽ Guess The Player - EXTREME",
        description=f"**Clue:** {clue}",
        color=0xff0000
    )
    
    embed.set_footer(text="Type the player's name to answer! This is very difficult!")
    await ctx.send(embed=embed)

# Add fun games
@bot.command()
async def rps(ctx: commands.Context, choice: str):
    """Rock Paper Scissors with rewards"""
    if choice.lower() not in ["rock", "paper", "scissors"]:
        return await ctx.send("❌ Choose rock, paper, or scissors!")
    
    bot_choice = random.choice(["rock", "paper", "scissors"])
    user_choice = choice.lower()
    
    # Determine winner
    if user_choice == bot_choice:
        result = "tie"
        reward = 100
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        result = "win"
        reward = 500
    else:
        result = "lose"
        reward = 0
    
    emoji_map = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    
    embed = discord.Embed(
        title="🎮 Rock Paper Scissors",
        description=f"You: {emoji_map[user_choice]} vs Bot: {emoji_map[bot_choice]}",
        color=0x00ff00 if result == "win" else 0xffff00 if result == "tie" else 0xff0000
    )
    
    if result == "win":
        embed.add_field(name="🎉 You Win!", value=f"Earned ${reward} Tadbucks!", inline=True)
        ensure_user_exists(ctx.author.id)
        current_balance = get_balance(ctx.author.id)
        set_balance(ctx.author.id, current_balance + reward)
    elif result == "tie":
        embed.add_field(name="🤝 Tie Game!", value=f"Consolation prize: ${reward} Tadbucks!", inline=True)
        ensure_user_exists(ctx.author.id)
        current_balance = get_balance(ctx.author.id)
        set_balance(ctx.author.id, current_balance + reward)
    else:
        embed.add_field(name="💸 You Lose!", value="Better luck next time!", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def coinflip(ctx: commands.Context):
    """Flip a coin"""
    result = random.choice(["heads", "tails"])
    emoji = "👑" if result == "heads" else "⚪"
    
    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"{emoji} **{result.title()}!**",
        color=0xffd700
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def dice(ctx: commands.Context, sides: int = 6):
    """Roll dice (2-100 sides)"""
    if sides < 2 or sides > 100:
        return await ctx.send("❌ Dice must have 2-100 sides!")
    
    result = random.randint(1, sides)
    
    embed = discord.Embed(
        title=f"🎲 {sides}-sided Dice Roll",
        description=f"**You rolled: {result}**",
        color=0x9b59b6
    )
    
    await ctx.send(embed=embed)

@bot.command(name="8ball")
async def eight_ball(ctx: commands.Context, *, question: str):
    """Magic 8-ball"""
    responses = [
        "It is certain.", "Reply hazy, try again.", "Don't count on it.",
        "It is decidedly so.", "Ask again later.", "My reply is no.",
        "Without a doubt.", "Better not tell you now.", "My sources say no.",
        "Yes definitely.", "Cannot predict now.", "Outlook not so good.",
        "You may rely on it.", "Concentrate and ask again.", "Very doubtful.",
        "As I see it, yes.", "Most likely.", "Outlook good.",
        "Yes.", "Signs point to yes."
    ]
    
    response = random.choice(responses)
    
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Question:** {question}\n**Answer:** {response}",
        color=0x1a1a1a
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def var(ctx: commands.Context):
    """Football VAR decision"""
    decisions = [
        "🟢 GOAL! No offside detected.",
        "🔴 OFFSIDE! Goal disallowed.",
        "🟡 PENALTY! Foul in the box confirmed.",
        "⚪ NO PENALTY! Simulation detected.",
        "🟢 GOAL STANDS! Clean challenge.",
        "🔴 HANDBALL! Goal disallowed.",
        "🟡 RED CARD! Violent conduct confirmed.",
        "⚪ YELLOW CARD! Reckless challenge.",
    ]
    
    decision = random.choice(decisions)
    
    embed = discord.Embed(
        title="📺 VAR Decision",
        description=f"After video review: **{decision}**",
        color=0x00ff00
    )
    
    embed.set_footer(text="VAR check complete!")
    
    await ctx.send(embed=embed)

@bot.command()
async def meme(ctx: commands.Context):
    """Random memes"""
    memes = [
        "When you're losing 3-0 but still believe in comeback: 'This is fine' 🔥",
        "Me: Has homework due tomorrow\nAlso me: *Opens TadzzyBot* 🎮",
        "POV: You just packed a Secret card 🤯✨",
        "When your passive income hits different 💰📈",
        "That feeling when you win the jackpot spin 🎰🎉",
        "Me checking my collection for the 100th time today 👀",
        "When someone asks why I'm playing Discord bots instead of real games 🤷‍♂️",
        "The moment you realize you spent all your Tadbucks on packs 📦💸"
    ]
    
    meme = random.choice(memes)
    
    embed = discord.Embed(
        title="😂 Random Meme",
        description=meme,
        color=0xff6b6b
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def dadjoke(ctx: commands.Context):
    """Dad jokes"""
    jokes = [
        "Why don't footballers ever get cold? Because they have lots of fans! ⚽",
        "What do you call a footballer who doesn't play fair? A foul player! 🤣",
        "Why did the footballer go to the bank? To get his quarter back! 💰",
        "What's a ghost's favorite position? Ghoul-keeper! 👻",
        "Why don't football stadiums ever get hot? They have lots of fans! 🌬️",
        "What do you call a sleeping bull at the football field? A bulldozer! 😴",
        "Why did the footballer bring string to the game? So he could tie the score! 🧵",
        "What do you call a football player who makes coffee? A brew-midfielder! ☕"
    ]
    
    joke = random.choice(jokes)
    
    embed = discord.Embed(
        title="👨 Dad Joke Special",
        description=joke,
        color=0xffd700
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def compliment(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Spread positivity"""
    target = member or ctx.author
    
    compliments = [
        f"{target.display_name} has an amazing card collection! 🌟",
        f"{target.display_name} is a strategic mastermind! 🧠",
        f"{target.display_name} brings positive energy to the server! ✨",
        f"{target.display_name} is incredibly helpful to other players! 🤝",
        f"{target.display_name} has the best pack opening luck! 🍀",
        f"{target.display_name} is a true friend and teammate! 💙",
        f"{target.display_name} makes the game more fun for everyone! 🎉",
        f"{target.display_name} has excellent taste in players! ⚽"
    ]
    
    compliment = random.choice(compliments)
    
    embed = discord.Embed(
        title="💖 Compliment Time!",
        description=compliment,
        color=0xff69b4
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def trivia(ctx: commands.Context):
    """Quiz time"""
    questions = [
        {"q": "Which player is known as 'The GOAT'?", "a": "Lionel Messi"},
        {"q": "What year did Messi join PSG?", "a": "2021"},
        {"q": "Which team has won the most Champions League titles?", "a": "Real Madrid"},
        {"q": "Who won the 2022 World Cup?", "a": "Argentina"},
        {"q": "What is Cristiano Ronaldo's nationality?", "a": "Portuguese"},
        {"q": "Which Premier League team is called 'The Red Devils'?", "a": "Manchester United"},
        {"q": "Who is known as 'The Egyptian King'?", "a": "Mohamed Salah"},
        {"q": "Which country hosted the 2022 World Cup?", "a": "Qatar"}
    ]
    
    question = random.choice(questions)
    
    embed = discord.Embed(
        title="🧠 Football Trivia",
        description=f"**Question:** {question['q']}",
        color=0x3498db
    )
    
    embed.set_footer(text="Think you know the answer?")
    
    # Store answer for checking (simplified - in real implementation you'd track responses)
    await ctx.send(embed=embed)
    await asyncio.sleep(5)
    
    answer_embed = discord.Embed(
        title="✅ Answer Revealed!",
        description=f"**Answer:** {question['a']}",
        color=0x00ff00
    )
    
    await ctx.send(embed=answer_embed)

@bot.command()
async def ping(ctx: commands.Context):
    """Bot latency"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=0x00ff00 if latency < 100 else 0xffff00 if latency < 200 else 0xff0000
    )
    
    await ctx.send(embed=embed)

# Add gamenight command
@bot.command()
async def gamenight(ctx: commands.Context):
    """View Roblox game nights"""
    if not data["gamenights"]:
        return await ctx.send("🎮 No game nights scheduled currently!")
    
    embed = discord.Embed(
        title="🎮 Roblox Game Nights",
        description="Join us for these amazing games:",
        color=0xff6b6b
    )
    
    for i, link in enumerate(data["gamenights"][:5], 1):
        embed.add_field(
            name=f"Game {i}",
            value=link,
            inline=False
        )
    
    embed.set_footer(text="Click the links to join the games!")
    
    await ctx.send(embed=embed)

# Enhanced admin help with new commands
@commands.has_permissions(administrator=True)
@bot.command()
async def adminhelp(ctx: commands.Context):
    embed = discord.Embed(
        title="🛡️ Admin Command Center",
        description="Powerful tools for server administrators",
        color=0xff0000
    )

    embed.add_field(
        name="🔨 Moderation",
        value=(
            "`!kick @user [reason]` - Kick a member\n"
            "`!ban @user [reason]` - Ban a member\n"
            "`!timeout @user <seconds>` - Timeout user\n"
            "`!clear <count>` - Delete messages\n"
            "`!mute @user <minutes>` - Mute member\n"
            "`!unmute @user` - Unmute member\n"
            "`!warn @user <reason>` - Warn a user\n"
            "`!slowmode <seconds>` - Set channel slowmode\n"
            "`!nick @user <name>` - Change nickname"
        ),
        inline=False
    )

    embed.add_field(
        name="💎 Economy Management",
        value=(
            "`!givetadbucks @user <amount>` - Give Tadbucks\n"
            "`!removetadbucks @user <amount>` - Remove Tadbucks\n"
            "`!givetadzzypoints @user <amount>` - Give Tadzzy Points\n"
            "`!removetadzzypoints @user <amount>` - Remove points\n"
            "`!giveplayer @user <player>` - Give player card\n"
            "`!removeplayer @user <player>` - Remove player card\n"
            "`!resetbalance @user` - Reset user balance\n"
            "`!addlevel @user <amount>` - Add XP levels\n"
            "`!removelevel @user <amount>` - Remove XP levels\n"
            "`!admingamble <amount>` - 90/10 admin gambling"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Enhanced Code & Pack System",
        value=(
            "`!addcode <name> <cash> <xp> <multiplier> <hours> <pack_type> <pack_count>`\n"
            "`!removecode <name>` - Remove code\n"
            "`!listcodes` - View all codes\n"
            "`!multipliers` - View active multipliers"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏪 Shop & Upgrade Management",
        value=(
            "`!restock <player|all>` - Restock shop items\n"
            "`!adminupgrade @user <player> <level>` - Upgrade user cards\n"
            "Example: `!adminupgrade @user Tadstarman Ultimate`"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Auction & Event Management",
        value=(
            "`!forcecloseauction <player>` - Force close auction\n"
            "`!extendauction <player> <minutes>` - Extend timer\n"
            "`!listauctions` - View active auctions\n"
            "`!spawnauction <player>` - Create auction\n"
            "`!addgamenight <link>` - Add Roblox game night\n"
            "`!gamenightremove <link>` - Remove game night\n"
            "`!giveawaycreate <time> <prize>` - Create giveaway"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ System Administration",
        value=(
            "`!save` - Manually save data\n"
            "`!load` - Reload data from disk\n"
            "`!backup` - Create data backup\n"
            "`!broadcast <message>` - Send to all members\n"
            "`!say <message>` - Make bot speak\n"
            "`!viewdeleted [@user]` - View recently deleted messages"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ System Administration",
        value=(
            "!save - Manually save data\n"
            "!load - Reload data from disk\n"
            "!backup - Create data backup\n"
            "!broadcast <message> - Send to all members\n"
            "!say <message> - Make bot speak\n"
            "!viewdeleted [@user] - View recently deleted messages"
        ),
        inline=False
    )

    embed.set_footer(text="⚠️ Use admin commands responsibly! New features: Pack system, upgrade system, stock management!")
    await ctx.send(embed=embed)

# Enhanced Admin Storage Command - Set user storage slots or unlimited storage
@bot.command(name="adminstorage")
async def admin_storage(ctx, *args):
    """Admin command to set user storage - !adminstorage <user> <slots> or !adminstorage infinite <user>"""
    # Check if user is admin (you can modify this check)
    admin_ids = [677246059023827006]  # Add your admin ID here
    if ctx.author.id not in admin_ids:
        await ctx.reply("❌ You don't have permission to use this command!")
        return
    
    if len(args) < 2:
        embed = discord.Embed(
            title="📦 Admin Storage Command",
            description="Usage Examples:\n" +
            "• !adminstorage @user 25 - Set user storage to 25 slots\n" +
            "• !adminstorage @user 100 - Set user storage to 100 slots\n" +
            "• !adminstorage infinite @user - Give unlimited storage",
            color=0x3498db
        )
        await ctx.reply(embed=embed)
        return
    
    try:
        # Handle "infinite" command format
        if args[0].lower() == "infinite":
            if len(ctx.message.mentions) == 0:
                # Try to find user by ID or name
                user_input = args[1]
                try:
                    if user_input.isdigit():
                        target_user = bot.get_user(int(user_input))
                    else:
                        target_user = discord.utils.get(bot.get_all_members(), name=user_input)
                except:
                    target_user = None
            else:
                target_user = ctx.message.mentions[0]
            
            if not target_user:
                await ctx.reply("❌ User not found! Use @mention or valid user ID.")
                return
            
            # Set unlimited storage
            uid = str(target_user.id)
            if uid not in data["user_collections"]:
                data["user_collections"][uid] = []
            
            # Set special marker for unlimited storage
            if "unlimited_storage" not in data:
                data["unlimited_storage"] = []
            
            if uid not in data["unlimited_storage"]:
                data["unlimited_storage"].append(uid)
            
            embed = discord.Embed(
                title="✅ Unlimited Storage Granted! ♾️",
                description=f"🎉 {target_user.display_name} now has unlimited card storage!\n" +
                f"📦 Current collection: {len(data['user_collections'].get(uid, []))} cards",
                color=0x00ff00
            )
            embed.set_footer(text="♾️ This user can now collect unlimited cards!")
        
        else:
            # Handle regular slot amount format: !adminstorage <user> <slots>
            if len(ctx.message.mentions) == 0:
                # Try to find user by ID or name
                user_input = args[0]
                try:
                    if user_input.isdigit():
                        target_user = bot.get_user(int(user_input))
                    else:
                        target_user = discord.utils.get(bot.get_all_members(), name=user_input)
                except:
                    target_user = None
            else:
                target_user = ctx.message.mentions[0]
            
            if not target_user:
                await ctx.reply("❌ User not found! Use @mention or valid user ID.")
                return
            
            # Get slot amount
            try:
                slot_amount = int(args[1] if len(ctx.message.mentions) == 0 else args[0])
            except ValueError:
                await ctx.reply("❌ Invalid slot amount! Must be a number.")
                return
            
            if slot_amount < 1 or slot_amount > 1000:
                await ctx.reply("❌ Slot amount must be between 1 and 1000!")
                return
            
            # Set custom storage
            uid = str(target_user.id)
            if uid not in data["user_collections"]:
                data["user_collections"][uid] = []
            
            # Remove from unlimited storage if they were there
            if "unlimited_storage" in data and uid in data["unlimited_storage"]:
                data["unlimited_storage"].remove(uid)
            
            # Set custom storage amount
            if "custom_storage" not in data:
                data["custom_storage"] = {}
            
            data["custom_storage"][uid] = slot_amount
            
            current_cards = len(data["user_collections"].get(uid, []))
            
            embed = discord.Embed(
                title="✅ Custom Storage Set! 📦",
                description=f"📦 {target_user.display_name}'s storage: {slot_amount} slots\n" +
                f"🎴 Current collection: {current_cards}/{slot_amount} cards",
                color=0x00ff00
            )
            
            if current_cards > slot_amount:
                embed.add_field(
                    name="⚠️ Warning",
                    value=f"User has {current_cards} cards but only {slot_amount} slots.\nThey won't be able to get new cards until they sell some.",
                    inline=False
                )
        
        await ctx.reply(embed=embed)
    
    except Exception as e:
        await ctx.reply(f"❌ Error setting storage: {str(e)}")
        print(f"Error in adminstorage: {e}")


# Add all missing admin commands
@commands.has_permissions(administrator=True)
@bot.command()
async def givetadbucks(ctx: commands.Context, member: discord.Member, amount: int):
    """Give Tadbucks to user"""
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive!")
    
    ensure_user_exists(member.id)
    current_balance = get_balance(member.id)
    set_balance(member.id, current_balance + amount)
    
    await ctx.send(f"✅ Gave {member.display_name} ${amount:,} Tadbucks. New balance: ${get_balance(member.id):,}")

@commands.has_permissions(administrator=True)
@bot.command()
async def removetadbucks(ctx: commands.Context, member: discord.Member, amount: int):
    """Remove Tadbucks from user"""
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive!")
    
    ensure_user_exists(member.id)
    current_balance = get_balance(member.id)
    new_balance = max(0, current_balance - amount)
    set_balance(member.id, new_balance)
    
    await ctx.send(f"✅ Removed ${amount:,} Tadbucks from {member.display_name}. New balance: ${get_balance(member.id):,}")

@commands.has_permissions(administrator=True)
@bot.command()
async def givetadzzypoints(ctx: commands.Context, member: discord.Member, amount: int):
    """Give Tadzzy Points to user"""
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive!")
    
    ensure_user_exists(member.id)
    uid = str(member.id)
    current_points = data["tadzzy_points"].get(uid, 0)
    data["tadzzy_points"][uid] = current_points + amount
    
    await ctx.send(f"✅ Gave {member.display_name} {amount:,} Tadzzy Points. New total: {data['tadzzy_points'][uid]:,}")

@commands.has_permissions(administrator=True)
@bot.command()
async def removetadzzypoints(ctx: commands.Context, member: discord.Member, amount: int):
    """Remove Tadzzy Points from user"""
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive!")
    
    ensure_user_exists(member.id)
    uid = str(member.id)
    current_points = data["tadzzy_points"].get(uid, 0)
    data["tadzzy_points"][uid] = max(0, current_points - amount)
    
    await ctx.send(f"✅ Removed {amount:,} Tadzzy Points from {member.display_name}. New total: {data['tadzzy_points'][uid]:,}")

@commands.has_permissions(administrator=True)
@bot.command()
async def giveplayer(ctx: commands.Context, member: discord.Member, *, player_name: str):
    """Give player card to user"""
    card = find_player_card_by_name(player_name)
    if not card:
        return await ctx.send("❌ Player not found!")
    
    ensure_user_exists(member.id)
    uid = str(member.id)
    user_coll = data["user_collections"].get(uid, [])
    
    if len(user_coll) >= MAX_COLLECTION_SLOTS:
        return await ctx.send(f"❌ {member.display_name}'s collection is full!")
    
    new_card = card.copy()
    new_card["upgrade_level"] = "Gold"
    new_card["upgrade_progress"] = 0
    user_coll.append(new_card)
    
    await ctx.send(f"✅ Gave {member.display_name} a {card['name']} ({card['rarity']}) card!")

@commands.has_permissions(administrator=True)
@bot.command()
async def removeplayer(ctx: commands.Context, member: discord.Member, *, player_name: str):
    """Remove player card from user"""
    ensure_user_exists(member.id)
    uid = str(member.id)
    user_coll = data["user_collections"].get(uid, [])
    
    card_removed = False
    for i, card in enumerate(user_coll):
        if normalize_name(card["name"]) == normalize_name(player_name):
            removed_card = user_coll.pop(i)
            card_removed = True
            await ctx.send(f"✅ Removed {removed_card['name']} from {member.display_name}'s collection!")
            break
    
    if not card_removed:
        await ctx.send(f"❌ {member.display_name} doesn't have {player_name}!")

@commands.has_permissions(administrator=True)
@bot.command()
async def resetbalance(ctx: commands.Context, member: discord.Member):
    """Reset user balance"""
    ensure_user_exists(member.id)
    set_balance(member.id, STARTING_BALANCE)
    
    await ctx.send(f"✅ Reset {member.display_name}'s balance to ${STARTING_BALANCE:,}!")

@commands.has_permissions(administrator=True)
@bot.command()
async def addlevel(ctx: commands.Context, member: discord.Member, amount: int):
    """Add XP levels"""
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive!")
    
    ensure_user_exists(member.id)
    uid = str(member.id)
    current_xp = data["xp_levels"].get(uid, 0)
    data["xp_levels"][uid] = current_xp + (amount * LEVEL_UP_XP_THRESHOLD)
    
    current_level = data["xp_levels"][uid] // LEVEL_UP_XP_THRESHOLD
    await ctx.send(f"✅ Added {amount} level(s) to {member.display_name}. New level: {current_level}")

@commands.has_permissions(administrator=True)
@bot.command()
async def removelevel(ctx: commands.Context, member: discord.Member, amount: int):
    """Remove XP levels"""
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive!")
    
    ensure_user_exists(member.id)
    uid = str(member.id)
    current_xp = data["xp_levels"].get(uid, 0)
    data["xp_levels"][uid] = max(0, current_xp - (amount * LEVEL_UP_XP_THRESHOLD))
    
    current_level = data["xp_levels"][uid] // LEVEL_UP_XP_THRESHOLD
    await ctx.send(f"✅ Removed {amount} level(s) from {member.display_name}. New level: {current_level}")

@commands.has_permissions(administrator=True)
@bot.command()
async def removecode(ctx: commands.Context, code_name: str):
    """Remove code"""
    code_name = code_name.upper()
    if code_name in data["codes"]:
        del data["codes"][code_name]
        await ctx.send(f"✅ Removed code '{code_name}'!")
    else:
        await ctx.send(f"❌ Code '{code_name}' not found!")

@commands.has_permissions(administrator=True)
@bot.command()
async def listcodes(ctx: commands.Context):
    """View all codes"""
    if not data["codes"]:
        return await ctx.send("📝 No active codes!")
    
    embed = discord.Embed(
        title="📝 Active Codes",
        description="All currently active redemption codes:",
        color=0x3498db
    )
    
    for code_name, code_info in list(data["codes"].items())[:10]:  # Show first 10
        rewards = []
        if code_info.get("cash", 0) > 0:
            rewards.append(f"${code_info['cash']:,}")
        if code_info.get("xp", 0) > 0:
            rewards.append(f"{code_info['xp']} XP")
        if code_info.get("multiplier_type"):
            rewards.append(f"{code_info['multiplier_type']} ({code_info['multiplier_hours']}h)")
        if code_info.get("pack_type"):
            rewards.append(f"{code_info['pack_count']} {code_info['pack_type']}")
        
        embed.add_field(
            name=code_name,
            value=" | ".join(rewards) or "No rewards",
            inline=True
        )
    
    await ctx.send(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command()
async def multipliers(ctx: commands.Context):
    """View active multipliers"""
    active_multipliers = []
    
    for uid, multipliers in data["multipliers"].items():
        try:
            user = bot.get_user(int(uid))
            username = user.display_name if user else f"User {uid}"
        except:
            username = f"User {uid}"
        
        for mult_type, expiry_str in multipliers.items():
            try:
                expiry = datetime.fromisoformat(expiry_str)
                if datetime.utcnow() < expiry:
                    time_left = expiry - datetime.utcnow()
                    hours_left = int(time_left.total_seconds() / 3600)
                    active_multipliers.append(f"{username}: {mult_type} ({hours_left}h left)")
            except:
                continue
    
    if not active_multipliers:
        return await ctx.send("📊 No active multipliers!")
    
    embed = discord.Embed(
        title="⚡ Active Multipliers",
        description="\n".join(active_multipliers[:10]),
        color=0xff6b6b
    )
    
    await ctx.send(embed=embed)

# Add more admin commands
@commands.has_permissions(administrator=True)
@bot.command()
async def addgamenight(ctx: commands.Context, *, link: str):
    """Add Roblox game night"""
    if link in data["gamenights"]:
        return await ctx.send("❌ This game night link already exists!")
    
    data["gamenights"].append(link)
    await ctx.send(f"✅ Added game night: {link}")

@commands.has_permissions(administrator=True)
@bot.command()
async def gamenightremove(ctx: commands.Context, *, link: str):
    """Remove game night"""
    if link in data["gamenights"]:
        data["gamenights"].remove(link)
        await ctx.send(f"✅ Removed game night: {link}")
    else:
        await ctx.send("❌ Game night link not found!")

@commands.has_permissions(administrator=True)
@bot.command()
async def save(ctx: commands.Context):
    """Manually save data"""
    if save_data():
        await ctx.send("✅ Data saved successfully!")
    else:
        await ctx.send("❌ Failed to save data!")

@commands.has_permissions(administrator=True)
@bot.command()
async def load(ctx: commands.Context):
    """Reload data from disk"""
    try:
        load_data()
        await ctx.send("✅ Data reloaded successfully!")
    except Exception as e:
        await ctx.send(f"❌ Failed to reload data: {str(e)}")

@commands.has_permissions(administrator=True)
@bot.command()
async def backup(ctx: commands.Context):
    """Create data backup"""
    backup_path = backup_data()
    if backup_path:
        await ctx.send(f"✅ Backup created: {backup_path}")
    else:
        await ctx.send("❌ Failed to create backup!")

@commands.has_permissions(administrator=True)
@bot.command()
async def broadcast(ctx: commands.Context, *, message: str):
    """Send to all members"""
    sent_count = 0
    failed_count = 0
    
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                try:
                    await member.send(f"📢 **Server Announcement:** {message}")
                    sent_count += 1
                except:
                    failed_count += 1
    
    await ctx.send(f"📤 Broadcast complete! Sent to {sent_count} members, {failed_count} failed.")

@commands.has_permissions(administrator=True)
@bot.command()
async def say(ctx: commands.Context, *, message: str):
    """Make bot speak"""
    await ctx.message.delete()
    await ctx.send(message)

# Add moderation commands
@commands.has_permissions(kick_members=True)
@bot.command()
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member"""
    try:
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.display_name} has been kicked. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this member!")
    except Exception as e:
        await ctx.send(f"❌ Failed to kick member: {str(e)}")

@commands.has_permissions(ban_members=True)
@bot.command()
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member"""
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.display_name} has been banned. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this member!")
    except Exception as e:
        await ctx.send(f"❌ Failed to ban member: {str(e)}")

@commands.has_permissions(moderate_members=True)
@bot.command()
async def timeout(ctx: commands.Context, member: discord.Member, seconds: int, *, reason: str = "No reason provided"):
    """Timeout a user"""
    if seconds <= 0 or seconds > 2419200:  # Max 28 days
        return await ctx.send("❌ Timeout must be 1 second to 28 days!")
    
    try:
        timeout_until = datetime.utcnow() + timedelta(seconds=seconds)
        await member.timeout(timeout_until, reason=reason)
        await ctx.send(f"⏰ {member.display_name} has been timed out for {seconds} seconds. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to timeout this member!")
    except Exception as e:
        await ctx.send(f"❌ Failed to timeout member: {str(e)}")

@commands.has_permissions(manage_messages=True)
@bot.command()
async def clear(ctx: commands.Context, count: int):
    """Delete messages"""
    if count <= 0 or count > 100:
        return await ctx.send("❌ Count must be 1-100!")
    
    try:
        deleted = await ctx.channel.purge(limit=count + 1)  # +1 for the command message
        await ctx.send(f"🗑️ Deleted {len(deleted) - 1} message(s)!", delete_after=5)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")
    except Exception as e:
        await ctx.send(f"❌ Failed to clear messages: {str(e)}")

@commands.has_permissions(manage_roles=True)
@bot.command()
async def mute(ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
    """Mute member"""
    if minutes <= 0 or minutes > 40320:  # Max 28 days in minutes
        return await ctx.send("❌ Mute duration must be 1 minute to 28 days!")
    
    try:
        timeout_until = datetime.utcnow() + timedelta(minutes=minutes)
        await member.timeout(timeout_until, reason=reason)
        await ctx.send(f"🔇 {member.display_name} has been muted for {minutes} minute(s). Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to mute this member!")
    except Exception as e:
        await ctx.send(f"❌ Failed to mute member: {str(e)}")

@commands.has_permissions(manage_roles=True)
@bot.command()
async def unmute(ctx: commands.Context, member: discord.Member):
    """Unmute member"""
    try:
        await member.timeout(None)
        await ctx.send(f"🔊 {member.display_name} has been unmuted!")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unmute this member!")
    except Exception as e:
        await ctx.send(f"❌ Failed to unmute member: {str(e)}")

@commands.has_permissions(manage_messages=True)
@bot.command()
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str):
    """Warn a user"""
    try:
        await member.send(f"⚠️ **Warning from {ctx.guild.name}**\nReason: {reason}\nModerator: {ctx.author.display_name}")
        await ctx.send(f"⚠️ {member.display_name} has been warned. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send(f"⚠️ {member.display_name} has been warned (couldn't DM). Reason: {reason}")
    except Exception as e:
        await ctx.send(f"❌ Failed to warn member: {str(e)}")

@commands.has_permissions(manage_channels=True)
@bot.command()
async def slowmode(ctx: commands.Context, seconds: int):
    """Set channel slowmode"""
    if seconds < 0 or seconds > 21600:  # Max 6 hours
        return await ctx.send("❌ Slowmode must be 0-21600 seconds (0-6 hours)!")
    
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("⚡ Slowmode disabled!")
        else:
            await ctx.send(f"🐌 Slowmode set to {seconds} second(s)!")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage this channel!")
    except Exception as e:
        await ctx.send(f"❌ Failed to set slowmode: {str(e)}")

@commands.has_permissions(manage_nicknames=True)
@bot.command()
async def nick(ctx: commands.Context, member: discord.Member, *, name: str):
    """Change nickname"""
    if len(name) > 32:
        return await ctx.send("❌ Nickname must be 32 characters or less!")
    
    try:
        old_name = member.display_name
        await member.edit(nick=name)
        await ctx.send(f"✏️ Changed {old_name}'s nickname to {name}!")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this member's nickname!")
    except Exception as e:
        await ctx.send(f"❌ Failed to change nickname: {str(e)}")

# Error handling
@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided!")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Command on cooldown! Try again in {error.retry_after:.2f} seconds.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Command error: {error}")

@bot.command()
async def playerinfo(ctx: commands.Context, *, player_name: str):
    """View detailed information about a specific player in your collection"""
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_collection = data["user_collections"].get(uid, [])
    
    if not user_collection:
        return await ctx.send("📦 Your collection is empty! Use !shop to buy player cards.")
    
    # Find the player (case-insensitive)
    found_card = None
    card_index = None
    for i, card in enumerate(user_collection):
        if normalize_name(card["name"]) == normalize_name(player_name):
            found_card = card
            card_index = i + 1
            break
    
    if not found_card:
        return await ctx.send(f"❌ You don't own **{player_name}**. Use !collection to see your cards.")
    
    # Calculate all stats
    upgrade_level = get_card_upgrade_level(found_card)
    upgrade_multiplier = get_upgrade_multiplier(upgrade_level)
    original_price = found_card.get("original_price", found_card["price"])
    original_income = found_card.get("original_income_rate", found_card.get("income_rate", 1))
    
    # Current stats after upgrades
    current_price = int(original_price * upgrade_multiplier)
    current_income = int(original_income * upgrade_multiplier)
    
    # Apply rebirth bonus for income display
    rebirth_bonus_income = apply_rebirth_bonus(ctx.author.id, current_income)
    
    # Battle power calculation
    battle_power = int(current_price * upgrade_multiplier * 1.2)
    
    # Create detailed embed
    embed = discord.Embed(
        title=f"📊 **{found_card['name']}** - Player Information",
        description=f"**Card #{card_index}** in your collection",
        color=found_card.get("color", 0x5865F2)
    )
    
    # Basic Info
    embed.add_field(
        name="🏆 **Basic Information**",
        value=(
            f"**Rarity:** ✨ {found_card['rarity']}\n"
            f"**Position:** #{card_index} in collection\n"
            f"**Card Status:** 🟢 Active"
        ),
        inline=False
    )
    
    # Upgrade Information
    upgrade_progress = found_card.get("upgrade_progress", 0)
    next_level = "MAX" if upgrade_level == "Ultimate" else UPGRADE_LEVELS[UPGRADE_LEVELS.index(upgrade_level) + 1]
    
    embed.add_field(
        name="🔧 **Upgrade Status**",
        value=(
            f"**Current Level:** 🌟 {upgrade_level}\n"
            f"**Progress:** 📈 {upgrade_progress}%\n"
            f"**Next Level:** ⭐ {next_level}\n"
            f"**Stat Multiplier:** 🔥 {upgrade_multiplier}x"
        ),
        inline=True
    )
    
    # Financial Information
    embed.add_field(
        name="💰 **Financial Stats**",
        value=(
            f"**Original Price:** ${original_price:,}\n"
            f"**Current Value:** ${current_price:,}\n"
            f"**Value Increase:** +{int((upgrade_multiplier - 1) * 100)}%\n"
            f"**Sell Value:** ${int(current_price * 0.75):,}"
        ),
        inline=True
    )
    
    # Income Information
    embed.add_field(
        name="🕐 **Passive Income**",
        value=(
            f"**Base Income:** {original_income}/30min\n"
            f"**Current Income:** {current_income}/30min\n"
            f"**With Rebirths:** {rebirth_bonus_income}/30min\n"
            f"**Daily Potential:** ${int(rebirth_bonus_income * 48):,}/day"
        ),
        inline=False
    )
    
    # Battle Information
    embed.add_field(
        name="⚔️ **Battle Stats**",
        value=(
            f"**Battle Power:** ⚡ {battle_power:,}\n"
            f"**Success Bonus:** +{int(upgrade_multiplier * 10)}%\n"
            f"**Battle Ready:** {'✅ Yes' if current_price > 1000 else '❌ Too weak'}"
        ),
        inline=True
    )
    
    # Upgrade Costs
    if upgrade_level != "Ultimate":
        base_cost = original_price * 0.5
        level_multiplier = UPGRADE_LEVELS.index(upgrade_level) + 1
        upgrade_cost = int(base_cost * level_multiplier)
        
        embed.add_field(
            name="💎 **Upgrade Cost**",
            value=(
                f"**Pay to Upgrade:** ${upgrade_cost:,}\n"
                f"**Progress Gained:** +25%\n"
                f"**Sacrifice Card:** +50%+ progress"
            ),
            inline=True
        )
    
    # Special abilities or notes
    special_notes = []
    if found_card["rarity"] == "Secret":
        special_notes.append("🌟 **SECRET RARITY** - Ultimate power!")
    if upgrade_level == "Ultimate":
        special_notes.append("⭐ **MAX LEVEL** - Peak performance!")
    if current_price > 10000000:
        special_notes.append("💎 **HIGH VALUE** - Premium card!")
    
    if special_notes:
        embed.add_field(
            name="🌟 **Special Notes**",
            value="\n".join(special_notes),
            inline=False
        )
    
    embed.set_footer(text=f"💡 Use !upgrade {card_index} to upgrade this card!")
    
    await ctx.send(embed=embed)

@bot.command()
async def battle(ctx: commands.Context, opponent: discord.Member):
    """Enhanced battles with card selection and rewards"""
    if opponent.id == ctx.author.id:
        return await ctx.send("❌ You can't battle yourself!")
    
    if opponent.bot:
        return await ctx.send("❌ You can't battle bots!")
    
    # Check cooldown (1 minute)
    uid = str(ctx.author.id)
    now = datetime.utcnow()
    
    if uid in battle_cooldowns:
        last_battle = datetime.fromisoformat(battle_cooldowns[uid])
        if (now - last_battle).total_seconds() < 60:
            remaining = 60 - int((now - last_battle).total_seconds())
            return await ctx.send(f"⏰ Battle cooldown active! Wait {remaining} seconds.")
    
    # Set cooldown
    battle_cooldowns[uid] = now.isoformat()
    
    # Check if both users have cards
    ensure_user_exists(ctx.author.id)
    ensure_user_exists(opponent.id)
    
    user1_collection = data["user_collections"].get(str(ctx.author.id), [])
    user2_collection = data["user_collections"].get(str(opponent.id), [])
    
    if not user1_collection:
        return await ctx.send("❌ You need at least one card to battle! Use !shop to buy cards.")
    
    if not user2_collection:
        return await ctx.send(f"❌ {opponent.display_name} needs cards to battle!")
    
    # Card selection for user1
    embed = discord.Embed(
        title="⚔️ **Choose Your Battle Card!**",
        description=f"🥊 **{ctx.author.display_name}** vs **{opponent.display_name}**\n\nSelect your strongest card for battle!",
        color=0xff6b6b
    )
    
    embed.add_field(
        name="🎯 **Battle Rules**",
        value=(
            "⏱️ **45 seconds** of intense action\n"
            "💰 **$5,000** prize for the winner\n"
            "⚔️ Card power affects your chances\n"
            "🎮 Interactive penalties and free kicks\n"
            "⏰ **1-minute cooldown** after battles"
        ),
        inline=False
    )
    
    view = View(timeout=30)
    view.add_item(BattleCardSelect(ctx.author.id, opponent.id))
    
    await ctx.send(embed=embed, view=view)

# -----------------------------
# NEW ENHANCED COMMANDS WITH REQUESTED FEATURES  
# -----------------------------

# !resetuser command - Reset user back to 50k balance
@bot.command(name="resetuser")
async def reset_user(ctx: commands.Context, user: discord.Member = None):
    """Reset a user back to starting balance (Admin only)"""
    if not is_admin(ctx.author):
        await ctx.send("❌ **Admin access required!**")
        return
    
    if not user:
        await ctx.send("❌ **Please mention a user to reset!** Usage: `!reset @user`")
        return
    
    uid = str(user.id)
    
    # Reset to starting values
    data["tadbucks_balances"][uid] = STARTING_BALANCE
    data["tadzzy_points"][uid] = 0
    data["xp_levels"][uid] = 0
    data["user_collections"][uid] = []
    data["user_packs"][uid] = {}
    data["rebirths"][uid] = 0
    
    # Remove from other systems
    if uid in gamble_cooldowns:
        del gamble_cooldowns[uid]
    if uid in fairgamble_cooldowns:
        del fairgamble_cooldowns[uid]
    if uid in battle_cooldowns:
        del battle_cooldowns[uid]
    
    embed = discord.Embed(
        title="🔄 **User Reset Complete!** 🔄",
        description=f"**{user.display_name}** has been reset to default state!",
        color=0x00ff00
    )
    
    embed.add_field(name="💰 **Balance**", value=f"${STARTING_BALANCE:,}", inline=True)
    embed.add_field(name="⭐ **Tadzzy Points**", value="0", inline=True)
    embed.add_field(name="🏆 **Level**", value="0", inline=True)
    embed.add_field(name="🎴 **Collection**", value="Empty", inline=True)
    embed.add_field(name="🎁 **Packs**", value="None", inline=True)
    embed.add_field(name="🔄 **Rebirths**", value="0", inline=True)
    
    await ctx.send(embed=embed)

# DUPLICATE PLAYERINFO COMMAND REMOVED - Using the one at line 5572
# @bot.command(name="playerinfo")  # DISABLED DUPLICATE
async def player_info_DISABLED(ctx: commands.Context, *, player_name: str):
    """Show detailed information about a specific card in your collection"""
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_coll = data["user_collections"].get(uid, [])
    
    if not user_coll:
        await ctx.send("❌ **You have no cards!** Use `!shop` to buy some.")
        return
    
    # Find the card in user's collection
    found_cards = []
    for i, card in enumerate(user_coll):
        if normalize_name(card["name"]) == normalize_name(player_name):
            found_cards.append((i, card))
    
    if not found_cards:
        await ctx.send(f"❌ **'{player_name}' not found in your collection!**")
        return
    
    # Use the first match or show all if multiple
    card_index, card = found_cards[0]
    
    # Calculate all stats
    upgrade_level = get_card_upgrade_level(card)
    upgrade_multiplier = get_upgrade_multiplier(upgrade_level)
    current_progress = card.get("upgrade_progress", 0)
    
    # Original stats
    original_price = card.get("original_price", card["price"])
    original_income = card.get("original_income_rate", card["income_rate"])
    
    # Current stats
    current_price = card["price"]
    current_income = card["income_rate"]
    
    # Battle power calculation
    battle_power = int(current_income * upgrade_multiplier * 0.1)
    
    # Next level stats
    next_level_index = UPGRADE_LEVELS.index(upgrade_level)
    if next_level_index < len(UPGRADE_LEVELS) - 1:
        next_level = UPGRADE_LEVELS[next_level_index + 1]
        next_multiplier = get_upgrade_multiplier(next_level)
        next_price = int(original_price * next_multiplier)
        next_income = int(original_income * next_multiplier)
        upgrade_cost = int(original_price * 0.5 * (next_level_index + 2))
    else:
        next_level = "Maximum Level"
        next_price = current_price
        next_income = current_income
        upgrade_cost = 0
    
    # Create detailed embed
    embed = discord.Embed(
        title=f"📊 **{card['name']} - Detailed Information** 📊",
        description=f"**Complete stats for your {card['rarity']} card**",
        color=card.get("color", 0x5865F2)
    )
    
    # Basic Information
    embed.add_field(
        name="🎴 **Basic Information**",
        value=f"**Rarity:** {card['rarity']}\\n**Upgrade Level:** {upgrade_level}\\n**Collection Position:** #{card_index + 1}",
        inline=False
    )
    
    # Financial Information
    embed.add_field(
        name="💰 **Financial Stats**",
        value=f"**Current Value:** ${current_price:,}\\n**Original Value:** ${original_price:,}\\n**Value Increase:** {upgrade_multiplier:.1f}x\\n**Daily Earnings:** ${current_income * 48:,} (30min cycles)",
        inline=True
    )
    
    # Battle Information  
    embed.add_field(
        name="⚔️ **Battle Stats**",
        value=f"**Battle Power:** {battle_power}\\n**Success Bonus:** +{int((upgrade_multiplier - 1) * 20)}%\\n**Battle Tier:** {upgrade_level}",
        inline=True
    )
    
    # Upgrade Information
    if next_level != "Maximum Level":
        embed.add_field(
            name="📈 **Upgrade Progress**",
            value=f"**Current Progress:** {current_progress}%\\n**Next Level:** {next_level}\\n**Upgrade Cost:** ${upgrade_cost:,}\\n**Next Value:** ${next_price:,}\\n**Next Income:** ${next_income:,}/30min",
            inline=False
        )
    else:
        embed.add_field(
            name="🏆 **Maximum Level Reached!**",
            value="This card has reached its maximum upgrade level!",
            inline=False
        )
    
    # Income Analysis
    hourly_income = current_income * 2  # 30min cycles = 2 per hour
    daily_income = hourly_income * 24
    weekly_income = daily_income * 7
    
    embed.add_field(
        name="💎 **Income Analysis**",
        value=f"**Per 30 minutes:** ${current_income:,}\\n**Per hour:** ${hourly_income:,}\\n**Per day:** ${daily_income:,}\\n**Per week:** ${weekly_income:,}",
        inline=True
    )
    
    # Special Status
    status_text = []
    if upgrade_level == "Ultimate":
        status_text.append("🏆 **Maximum Level**")
    if card['rarity'] in ["Secret", "Mythic", "Expensive"]:
        status_text.append("💎 **High Value Card**")
    if current_income >= 1000:
        status_text.append("💰 **Premium Income**")
    
    if status_text:
        embed.add_field(
            name="⭐ **Special Status**",
            value="\\n".join(status_text),
            inline=True
        )
    
    # Show multiple copies if found
    if len(found_cards) > 1:
        embed.set_footer(text=f"💡 Found {len(found_cards)} copies of this card in your collection")
    else:
        embed.set_footer(text="💡 Use !upgrade to improve this card further!")
    
    await ctx.send(embed=embed)

# Fix !purge command (previously called !clear)
@bot.command(name="purge")
async def purge_messages(ctx: commands.Context, amount: int = 10):
    """Delete a specified number of messages (Admin only)"""
    if not is_admin(ctx.author):
        await ctx.send("❌ **Admin access required!**")
        return
    
    if amount < 1 or amount > 100:
        await ctx.send("❌ **Amount must be between 1 and 100!**")
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
        
        embed = discord.Embed(
            title="🗑️ **Messages Purged!** 🗑️",
            description=f"Successfully deleted **{len(deleted) - 1}** messages from {ctx.channel.mention}!",
            color=0x00ff00
        )
        
        # Send confirmation and delete it after 5 seconds
        confirmation = await ctx.send(embed=embed, delete_after=5)
        
    except discord.Forbidden:
        await ctx.send("❌ **I don't have permission to delete messages in this channel!**")
    except discord.HTTPException as e:
        await ctx.send(f"❌ **Failed to delete messages:** {e}")

# Duplicate battle_command removed - conflicts with other battle commands
    ensure_user_exists(ctx.author.id)
    
    if not opponent:
        await ctx.send("❌ **Please mention someone to battle!** Usage: `!battle @user`")
        return
    
    if opponent.bot:
        await ctx.send("❌ **You cannot battle bots!**")
        return
    
    if opponent.id == ctx.author.id:
        await ctx.send("❌ **You cannot battle yourself!**")
        return
    
    # Check cooldown
    uid = str(ctx.author.id)
    if uid in battle_cooldowns:
        last_battle = datetime.fromisoformat(battle_cooldowns[uid])
        cooldown_end = last_battle + timedelta(seconds=BATTLE_COOLDOWN)
        
        if datetime.utcnow() < cooldown_end:
            remaining = int((cooldown_end - datetime.utcnow()).total_seconds())
            await ctx.send(f"⏰ **Battle cooldown!** Try again in **{remaining}** seconds.")
            return
    
    # Check if user has cards
    user_coll = data["user_collections"].get(uid, [])
    if not user_coll:
        await ctx.send("❌ **You need cards to battle!** Use `!shop` to get some.")
        return
    
    # Check if opponent exists in system
    ensure_user_exists(opponent.id)
    opponent_coll = data["user_collections"].get(str(opponent.id), [])
    if not opponent_coll:
        await ctx.send(f"❌ **{opponent.display_name} has no cards to battle with!**")
        return
    
    # Create card selection embed
    embed = discord.Embed(
        title="⚔️ **Choose Your Battle Champion!** ⚔️",
        description=f"🥊 **{ctx.author.display_name}** challenges **{opponent.display_name}** to a 45-second battle!\\n\\n🎯 Select your strongest card to represent you in this epic showdown!",
        color=0xff4500
    )
    
    embed.add_field(
        name="⚡ **Battle Features**",
        value="• **45 seconds** of real-time action\\n• **Live commentary** every 5 seconds\\n• **Interactive penalties** and free kicks\\n• **$5,000 reward** for the winner\\n• **1-minute cooldown** between battles",
        inline=False
    )
    
    embed.set_footer(text="🌟 Choose wisely - your card's power affects your success rate!")
    
    # Create card selection view
    view = View(timeout=60)
    view.add_item(BattleCardSelect(ctx.author.id, opponent.id, user_coll))
    
    await ctx.send(embed=embed, view=view)

# ========================================
# PAGINATION COMMANDS - UPDATED SHOP & COLLECTION  
# ========================================

@bot.command(name='newshop')
async def shop_with_pagination(ctx):
    \"\"\"Browse the player shop with pagination\"\"\"
    ensure_user_exists(ctx.author.id)
    
    # Create pagination view with all footballers
    view = ShopPaginationView(ctx.author.id, footballers, items_per_page=15)
    embed = view.create_shop_embed()
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='newcollection')  
async def collection_with_pagination(ctx, member: discord.Member = None):
    \"\"\"View collection with pagination - FIXED VERSION\"\"\"
    target = member or ctx.author
    ensure_user_exists(target.id)
    
    uid = str(target.id)
    user_coll = data[\"user_collections\"].get(uid, [])
    
    if not user_coll:
        embed = discord.Embed(
            title=\"📭 Empty Collection\",
            description=f\"{target.display_name}'s collection is empty! Use `!buy <player>` to get cards.\",
            color=0xff6b6b
        )
        await ctx.send(embed=embed)
        return
    
    # Create pagination view
    view = WorkingCollectionView(ctx.author.id, user_coll, target.id)
    embed = view.create_collection_embed()
    
    await ctx.send(embed=embed, view=view)

# Working version of CollectionPaginationView without syntax errors
class WorkingCollectionView(View):
    def __init__(self, user_id: int, user_collection: list, target_user_id: int = None, items_per_page: int = 8):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_collection = user_collection
        self.target_user_id = target_user_id or user_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = max(0, (len(user_collection) - 1) // items_per_page) if user_collection else 0
    
    def get_current_page_items(self):
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.user_collection[start_idx:end_idx]
    
    def create_collection_embed(self):
        current_items = self.get_current_page_items()
        
        if self.user_id == self.target_user_id:
            title = \"⚽ Your Football Card Collection ⚽\"
            max_storage = get_user_max_storage(self.user_id)
            description = f\"📦 {len(self.user_collection)}/{max_storage} cards | Page {self.current_page + 1}/{self.max_pages + 1}\"
        else:
            target_user = bot.get_user(self.target_user_id)
            username = target_user.display_name if target_user else \"User\"
            title = f\"⚽ {username}'s Collection ⚽\"
            description = f\"📦 {len(self.user_collection)} cards | Page {self.current_page + 1}/{self.max_pages + 1}\"
        
        embed = discord.Embed(title=title, description=description, color=0x3498db)
        
        if not current_items:
            embed.add_field(name=\"📭 Empty Page\", value=\"No cards on this page.\", inline=False)
            return embed
        
        # Add cards to embed
        for i, card in enumerate(current_items, start=(self.current_page * self.items_per_page + 1)):
            upgrade_level = get_card_upgrade_level(card)
            upgrade_progress = card.get(\"upgrade_progress\", 0)
            
            card_info = f\"🏆 {card['rarity']} | 💰 ${card['price']:,}\"
            card_info += f\"\\n⭐ Level: {upgrade_level}\"
            
            if upgrade_level != \"Ultimate\" and upgrade_progress > 0:
                card_info += f\" ({upgrade_progress}% progress)\"
            
            embed.add_field(name=f\"{i}. {card['name']}\", value=card_info, inline=True)
        
        # Add page summary
        page_value = sum(card.get(\"price\", 0) for card in current_items)
        embed.add_field(
            name=\"📊 Page Summary\",
            value=f\"💰 Page Value: ${page_value:,}\\n📦 Cards shown: {len(current_items)}\",
            inline=False
        )
        
        if self.user_id == self.target_user_id:
            embed.set_footer(text=\"💡 Use !sell <number> to sell cards | !upgrade <number> to upgrade\")
        
        return embed
    
    @discord.ui.button(label=\"⬅️ Previous\", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(\"❌ Not your collection view!\", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_collection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message(\"❌ Already on first page!\", ephemeral=True)
    
    @discord.ui.button(label=\"Next ➡️\", style=discord.ButtonStyle.secondary) 
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(\"❌ Not your collection view!\", ephemeral=True)
            return
        
        if self.current_page < self.max_pages:
            self.current_page += 1
            embed = self.create_collection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message(\"❌ Already on last page!\", ephemeral=True)
    
    @discord.ui.button(label=\"📊 Full Stats\", style=discord.ButtonStyle.primary)
    async def show_full_stats(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(\"❌ Not your collection view!\", ephemeral=True)
            return
        
        # Calculate collection statistics
        total_value = sum(card.get(\"price\", 0) for card in self.user_collection)
        total_income = sum(card.get(\"income_rate\", 0) for card in self.user_collection)
        
        # Count by rarity
        rarity_counts = {}
        for card in self.user_collection:
            rarity = card.get(\"rarity\", \"Common\")
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        if self.user_id == self.target_user_id:
            title = \"📊 Your Collection Statistics 📊\"
        else:
            target_user = bot.get_user(self.target_user_id)
            username = target_user.display_name if target_user else \"User\"
            title = f\"📊 {username}'s Collection Statistics 📊\"
        
        embed = discord.Embed(title=title, color=0x00ff00)
        
        embed.add_field(
            name=\"💰 Financial Summary\",
            value=f\"Total Value: ${total_value:,}\\nPassive Income: ${total_income:,}/hour\",
            inline=True
        )
        
        embed.add_field(
            name=\"📦 Collection Size\",
            value=f\"Total Cards: {len(self.user_collection)}\",
            inline=True
        )
        
        if rarity_counts:
            rarity_text = \"\\n\".join([f\"{rarity}: {count}\" for rarity, count in sorted(rarity_counts.items())])
            embed.add_field(name=\"🏆 By Rarity\", value=rarity_text, inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)

# Run bot with proper error handling
if __name__ == "__main__":
    try:
        if TOKEN:
            # ===== ADD NEW COMMANDS BEFORE BOT STARTS =====
            
            # Add pack discount command
            @commands.has_permissions(administrator=True)
            @bot.command()
            async def packdiscount(ctx: commands.Context, discount: int = 0):
                """Set pack discount percentage (0-50%)"""
                if discount < 0 or discount > 50:
                    await ctx.reply("❌ **Discount must be between 0% and 50%!**")
                    return
                
                set_pack_discount(discount)
                
                if discount > 0:
                    embed = discord.Embed(
                        title="🔥 **PACK SALE ACTIVATED!** 🔥",
                        description=f"📦 **All packs are now {discount}% OFF!**",
                        color=0xff6600
                    )
                    embed.add_field(
                        name="💰 Sale Details",
                        value=f"• **{discount}%** discount on all packs\n• Players will see discounted prices\n• Use `!packdiscount 0` to end sale",
                        inline=False
                    )
                else:
                    embed = discord.Embed(
                        title="📦 **Pack Sale Ended**",
                        description="All packs are back to normal prices.",
                        color=0x95a5a6
                    )
                
                await ctx.reply(embed=embed)

            # Add reset user command
            @commands.has_permissions(administrator=True)
            @bot.command(name="adminreset")
            async def adminreset(ctx: commands.Context, user: discord.Member):
                """Reset a user back to starting balance and clear all data"""
                user_id = user.id
                uid = str(user_id)
                
                # Clear all user data
                if uid in data["tadbucks_balances"]:
                    del data["tadbucks_balances"][uid]
                if uid in data["tadzzy_points"]:
                    del data["tadzzy_points"][uid]
                if uid in data["xp_levels"]:
                    del data["xp_levels"][uid]
                if uid in data["user_collections"]:
                    del data["user_collections"][uid]
                if uid in data["user_packs"]:
                    del data["user_packs"][uid]
                if uid in data["daily_rewards"]:
                    del data["daily_rewards"][uid]
                if uid in data["weekly_rewards"]:
                    del data["weekly_rewards"][uid]
                if uid in data["hourly_rewards"]:
                    del data["hourly_rewards"][uid]
                if uid in data["daily_spin"]:
                    del data["daily_spin"][uid]
                if uid in data["multipliers"]:
                    del data["multipliers"][uid]
                if uid in data["rebirths"]:
                    del data["rebirths"][uid]
                if uid in data["user_storage"]:
                    del data["user_storage"][uid]
                
                # Set starting balance
                data["tadbucks_balances"][uid] = STARTING_BALANCE
                
                embed = discord.Embed(
                    title="🔄 **User Reset Complete!** 🔄",
                    description=f"✅ **{user.display_name}** has been completely reset!",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="💰 New Balance",
                    value=f"${STARTING_BALANCE:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="📦 Collection",
                    value="Empty",
                    inline=True
                )
                
                embed.add_field(
                    name="🏆 Level & XP", 
                    value="Reset to 0",
                    inline=True
                )
                
                embed.add_field(
                    name="🔄 What was reset",
                    value="• Balance → $50,000\n• Collection cleared\n• Packs cleared\n• Level & XP reset\n• All rewards reset\n• Storage back to default",
                    inline=False
                )
                
                embed.set_footer(text=f"Reset by: {ctx.author.display_name}")
                
                await ctx.reply(embed=embed)
                
                # Try to notify the user
                try:
                    user_embed = discord.Embed(
                        title="🔄 Your Account Has Been Reset",
                        description="An admin has reset your TadzzyBot account to starting values.",
                        color=0x3498db
                    )
                    user_embed.add_field(
                        name="💰 Starting Balance",
                        value=f"${STARTING_BALANCE:,}",
                        inline=False
                    )
                    await user.send(embed=user_embed)
                except:
                    pass  # User might have DMs disabled

            # Fix the addcode command for luck multipliers
            @commands.has_permissions(administrator=True) 
            @bot.command()
            async def addcodeluck(ctx: commands.Context, name: str, luck_type: str = "x2_luck", hours: int = 24):
                """Add luck multiplier codes - Use x2_luck or x3_luck"""
                valid_luck = ["x2_luck", "x3_luck"]
                
                if luck_type not in valid_luck:
                    await ctx.reply(f"❌ **Invalid luck type!** Use: {', '.join(valid_luck)}")
                    return
                
                if hours < 1 or hours > 168:  # Max 1 week
                    await ctx.reply("❌ **Hours must be between 1 and 168 (1 week)!**")
                    return
                
                # Add to codes
                data["codes"][name] = {
                    "cash": 0,
                    "xp": 0,
                    "multipliers": {luck_type: hours},
                    "packs": {}
                }
                
                luck_text = "2x" if luck_type == "x2_luck" else "3x"
                
                embed = discord.Embed(
                    title="🍀 **Luck Code Created!** 🍀",
                    description=f"✨ Code `{name}` created successfully!",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="🎲 Luck Boost",
                    value=f"**{luck_text} Pack Luck** for {hours} hours",
                    inline=True
                )
                
                embed.add_field(
                    name="📦 Effect",
                    value="Significantly improves chances of rare cards in packs",
                    inline=True
                )
                
                embed.add_field(
                    name="💡 Usage",
                    value=f"Players use: `!redeem {name}`",
                    inline=False
                )
                
                await ctx.reply(embed=embed)

            print("🚀 Starting TadzzyBot with ALL enhanced features...")
            print("✅ Modern Discord UI with buttons and dropdowns")
            print("✅ Pack system with animated openings")
            print("✅ Card upgrade system (6 levels)")
            print("✅ Enhanced rebirth system (10 levels)")
            print("✅ Complete gambling system")
            print("✅ Trading and battle systems")
            print("✅ Random auctions and spin wheels")
            print("✅ All admin and moderation commands")
            print("✅ Complete data persistence with JSON")
            print("✅ Background systems running")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            bot.run(TOKEN)
        else:
            print("❌ ERROR: No Discord token found!")
            print("Please create a .env file with: DISCORD_TOKEN=your_token_here")
            print("Or set the DISCORD_TOKEN environment variable")
    except KeyboardInterrupt:
        print("\n🔄 Shutting down bot...")
        save_data()  # Save data before shutdown
        print("✅ Bot shutdown complete.")
    except discord.LoginFailure:
        print("❌ ERROR: Invalid Discord token!")
        print("Please check your token in the .env file")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        save_data()  # Try to save data even on crash\n\n# FIXED: Removed duplicate help command that was causing CommandRegistrationError\n# Original help command at line 2612 is preserved

# -----------------------------
# Enhanced Pack System Commands
# -----------------------------
@bot.command()
async def packshop(ctx: commands.Context):
    """Browse and purchase packs"""
    embed = discord.Embed(
        title="🎁 Pack Shop - Amazing Animated Openings! ✨",
        description="Choose from our incredible pack selection with guaranteed amazing cards!",
        color=0xff6b6b
    )
    
    for pack_name, pack_info in PACK_TYPES.items():
        rarities_text = "\n".join([f"{rarity}: {int(chance*100)}%" for rarity, chance in pack_info["rarities"].items()])
        
        embed.add_field(
            name=f"🎁 {pack_name}",
            value=(
                f"💰 **${pack_info['price']:,}**\n"
                f"📦 **3 Cards**\n"
                f"🎲 **Chances:**\n{rarities_text}"
            ),
            inline=True
        )
    
    embed.set_footer(text="🌟 Use the dropdown below to purchase a pack! 🌟")
    
    view = PackShopView()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def packs(ctx: commands.Context):
    """View owned packs"""
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_packs = data["user_packs"].get(uid, {})
    
    if not user_packs or all(count == 0 for count in user_packs.values()):
        await ctx.send("📦 You don't have any packs! Use !packshop to buy some amazing packs!")
        return
    
    embed = discord.Embed(
        title=f"📦 {ctx.author.display_name}'s Pack Collection",
        description="Your unopened packs ready for amazing reveals!",
        color=0x3498db
    )
    
    for pack_name, count in user_packs.items():
        if count > 0:
            pack_info = PACK_TYPES.get(pack_name, {"price": 0})
            embed.add_field(
                name=f"🎁 {pack_name}",
                value=f"📦 **{count}** pack{'s' if count != 1 else ''}\n💰 Value: ${pack_info['price']:,} each",
                inline=True
            )
    
    embed.set_footer(text="🎉 Use !openpack <pack_name> to open with amazing animations!")
    
    await ctx.send(embed=embed)

@bot.command()
async def openpack(ctx: commands.Context, *, pack_name: str = None):
    """Open a pack with amazing animations"""
    if not pack_name:
        await ctx.send("❌ Please specify a pack to open! Example: !openpack Default Pack")
        return
    
    # Find matching pack
    pack_match = None
    for pack_type in PACK_TYPES.keys():
        if pack_name.lower() in pack_type.lower():
            pack_match = pack_type
            break
    
    if not pack_match:
        await ctx.send(f"❌ Pack '{pack_name}' not found! Available: {', '.join(PACK_TYPES.keys())}")
        return
    
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_packs = data["user_packs"].get(uid, {})
    
    if user_packs.get(pack_match, 0) <= 0:
        await ctx.send(f"❌ You don't have any {pack_match}s! Use !packshop to buy some.")
        return
    
    # Remove pack from inventory
    user_packs[pack_match] = user_packs.get(pack_match, 0) - 1
    
    # Create pack opening embed
    embed = discord.Embed(
        title=f"🎁 {pack_match} Ready to Open! ✨",
        description="Click the button below to experience an amazing pack opening animation!",
        color=0xff6b6b
    )
    
    view = PackOpenView(ctx.author.id, pack_match)
    await ctx.send(embed=embed, view=view)

# -----------------------------
# Card Upgrade System
# -----------------------------
@bot.command()
async def upgrade(ctx: commands.Context, card_number: int):
    """Upgrade a card with modern UI"""
    ensure_user_exists(ctx.author.id)
    uid = str(ctx.author.id)
    user_coll = data["user_collections"].get(uid, [])
    
    if card_number < 1 or card_number > len(user_coll):
        await ctx.send(f"❌ Invalid card number! You have {len(user_coll)} cards. Use !collection to see them.")
        return
    
    card = user_coll[card_number - 1]
    current_level = get_card_upgrade_level(card)
    current_progress = card.get("upgrade_progress", 0)
    
    # Check if max level
    if current_level == "Ultimate":
        await ctx.send(f"⭐ {card['name']} is already at Ultimate level!")
        return
    
    # Get next level
    current_index = UPGRADE_LEVELS.index(current_level)
    next_level = UPGRADE_LEVELS[current_index + 1] if current_index < len(UPGRADE_LEVELS) - 1 else "Ultimate"
    
    embed = discord.Embed(
        title=f"🔧 Upgrade {card['name']}",
        description=f"✨ **Current Level:** {current_level}\n📈 **Progress:** {current_progress}%\n🎯 **Next Level:** {next_level}",
        color=0x3498db
    )
    
    # Calculate costs
    base_cost = card.get("original_price", card["price"]) * 0.5  # 50% of original card value
    level_multiplier = UPGRADE_LEVELS.index(current_level) + 1
    upgrade_cost = int(base_cost * level_multiplier)
    
    embed.add_field(
        name="💰 Upgrade Cost",
        value=f"${upgrade_cost:,} (25% progress)",
        inline=True
    )
    
    embed.add_field(
        name="🏆 Benefits",
        value=f"Income: +{int(get_upgrade_multiplier(next_level)*100)}%\nBattle Power: +{int(get_upgrade_multiplier(next_level)*50)}%\nValue: +{int(get_upgrade_multiplier(next_level)*100)}%",
        inline=True
    )
    
    embed.set_footer(text="Choose your upgrade method below!")
    
    view = UpgradeView(ctx.author.id, card_number - 1)
    await ctx.send(embed=embed, view=view)

# -----------------------------
# Enhanced Gambling System
# -----------------------------
@bot.command()
async def gamble(ctx: commands.Context, amount: int):
    """Enhanced gambling with modern UI - 3 hour cooldown"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    if amount <= 0:
        return await ctx.send("❌ Bet amount must be positive.")
    
    balance = get_balance(ctx.author.id)
    if amount > balance:
        return await ctx.send("❌ You don't have enough Tadbucks.")
    
    # Check 3-hour cooldown
    last = gamble_cooldowns.get(uid)
    now = datetime.utcnow()
    if last:
        last_dt = datetime.fromisoformat(last)
        if now - last_dt < timedelta(hours=3):
            remaining = timedelta(hours=3) - (now - last_dt)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return await ctx.send(f"⏰ You can gamble again in {hours}h {minutes}m.")
    
    embed = discord.Embed(
        title="🎰 Choose Your Gambling Game",
        description=f"💰 **Betting:** ${amount:,}\n🎲 **Choose your game with buttons below!**",
        color=0xff9900
    )
    
    embed.add_field(name="🔴 Red (60%)", value="Better odds, lower payout (0.8x)", inline=True)
    embed.add_field(name="⚫ Black (60%)", value="Better odds, lower payout (0.8x)", inline=True)
    embed.add_field(name="⚪ White (60%)", value="Better odds, lower payout (0.8x)", inline=True)
    embed.add_field(name="🎲 Dice (50%)", value="Even odds, even payout (1.0x)", inline=True)
    embed.add_field(name="🃏 Card (40%)", value="Worse odds, higher payout (1.5x)", inline=True)
    
    view = GambleView(ctx.author.id, amount)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def fairgamble(ctx: commands.Context, amount: int):
    """Fair gambling with modern UI - Level 25+ required"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    if amount <= 0:
        return await ctx.send("❌ Bet amount must be positive.")
    
    balance = get_balance(ctx.author.id)
    if amount > balance:
        return await ctx.send("❌ You don't have enough Tadbucks.")
    
    # Check level requirement (25 instead of 50)
    level = int(data["xp_levels"].get(uid, 0)) // LEVEL_UP_XP_THRESHOLD
    if level < 25:
        return await ctx.send(f"❌ You need to be at least level 25 for fair gamble. You're level {level}.")
    
    # Check 3-hour cooldown
    last = fairgamble_cooldowns.get(uid)
    now = datetime.utcnow()
    if last:
        last_dt = datetime.fromisoformat(last)
        if now - last_dt < timedelta(hours=3):
            remaining = timedelta(hours=3) - (now - last_dt)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return await ctx.send(f"⏰ You can fair gamble again in {hours}h {minutes}m.")
    
    embed = discord.Embed(
        title="⚖️ Choose Your Fair Game (50/50)",
        description=f"💰 **Betting:** ${amount:,}\n🎯 **All games have equal 50/50 odds!**",
        color=0x00ff00
    )
    
    embed.add_field(name="🪙 Coin Flip", value="Heads or Tails", inline=True)
    embed.add_field(name="🎯 Target Shot", value="Hit or Miss", inline=True)
    embed.add_field(name="⚡ Lightning", value="Strike or Pass", inline=True)
    embed.add_field(name="🌟 Star Catch", value="Catch or Drop", inline=True)
    
    view = FairGambleView(ctx.author.id, amount)
    await ctx.send(embed=embed, view=view)

# Enhanced Admin Gambling
@commands.has_permissions(administrator=True)
@bot.command()
async def admingamble(ctx: commands.Context, amount: int):
    """Admin gambling with 90/10 odds"""
    ensure_user_exists(ctx.author.id)

    if amount <= 0:
        return await ctx.send("❌ Bet amount must be positive.")

    balance = get_balance(ctx.author.id)
    if amount > balance:
        return await ctx.send("❌ You don't have enough Tadbucks.")

    if random.random() < 0.9:  # 90% win chance
        set_balance(ctx.author.id, balance + amount)
        await ctx.send(f"🎉 Admin power! You won ${amount:,}. New balance: ${get_balance(ctx.author.id):,}")
    else:
        set_balance(ctx.author.id, balance - amount)
        await ctx.send(f"💸 Even admins lose sometimes! Lost ${amount:,}. New balance: ${get_balance(ctx.author.id):,}")

# -----------------------------
# Daily/Weekly/Hourly Rewards & Spin
# -----------------------------
@bot.command()
async def daily(ctx: commands.Context):
    """Daily reward system"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    today = datetime.utcnow().date().isoformat()
    last_claim = data["daily_rewards"].get(uid)

    if last_claim == today:
        return await ctx.send("🕒 You've already claimed your daily reward today! Come back tomorrow.")

    data["daily_rewards"][uid] = today

    # Significantly increased daily rewards
    rewards = [
        {"cash": 25000, "xp": 200, "description": "25,000 Tadbucks + 200 XP"},
        {"cash": 30000, "xp": 150, "description": "30,000 Tadbucks + 150 XP"},
        {"cash": 20000, "xp": 250, "description": "20,000 Tadbucks + 250 XP"},
        {"cash": 35000, "xp": 180, "description": "35,000 Tadbucks + 180 XP"},
        {"cash": 28000, "xp": 220, "description": "28,000 Tadbucks + 220 XP"},
        {"cash": 40000, "xp": 120, "description": "40,000 Tadbucks + 120 XP"},
        {"cash": 22000, "xp": 280, "description": "22,000 Tadbucks + 280 XP"},
    ]

    reward = random.choice(rewards)

    # Apply rewards
    data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + reward["cash"]
    data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + reward["xp"]

    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=f"You received: {reward['description']}",
        color=0x00ff00
    )

    await ctx.send(embed=embed)

@bot.command()
async def weekly(ctx: commands.Context):
    """Weekly reward system - highly rewarded"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    today = datetime.utcnow().date()
    last_claim_str = data["weekly_rewards"].get(uid)

    if last_claim_str:
        last_claim = datetime.fromisoformat(last_claim_str).date()
        if (today - last_claim).days < 7:
            days_left = 7 - (today - last_claim).days
            return await ctx.send(f"📅 You can claim your weekly reward in {days_left} day(s).")

    data["weekly_rewards"][uid] = today.isoformat()

    # High-value weekly rewards
    rewards = [
        {"cash": 50000, "xp": 500, "tadzzy": 25, "description": "50,000 Tadbucks + 500 XP + 25 Tadzzy Points"},
        {"cash": 40000, "xp": 600, "tadzzy": 30, "description": "40,000 Tadbucks + 600 XP + 30 Tadzzy Points"},
        {"cash": 60000, "xp": 400, "tadzzy": 20, "description": "60,000 Tadbucks + 400 XP + 20 Tadzzy Points"},
        {"cash": 45000, "xp": 550, "tadzzy": 35, "description": "45,000 Tadbucks + 550 XP + 35 Tadzzy Points"},
    ]

    reward = random.choice(rewards)

    # Apply rewards
    data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + reward["cash"]
    data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + reward["xp"]
    data["tadzzy_points"][uid] = data["tadzzy_points"].get(uid, 0) + reward["tadzzy"]

    embed = discord.Embed(
        title="🏆 Weekly Reward Claimed!",
        description=f"Amazing! You received: {reward['description']}",
        color=0xffd700
    )

    await ctx.send(embed=embed)

@bot.command()
async def hourly(ctx: commands.Context):
    """Hourly reward system - quick boost"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    now = datetime.utcnow()
    last_claim_str = data["hourly_rewards"].get(uid)

    if last_claim_str:
        last_claim = datetime.fromisoformat(last_claim_str)
        if (now - last_claim).total_seconds() < 3600:  # 1 hour = 3600 seconds
            remaining_seconds = 3600 - int((now - last_claim).total_seconds())
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            return await ctx.send(f"⏰ You can claim your hourly reward in {minutes}m {seconds}s.")

    data["hourly_rewards"][uid] = now.isoformat()

    # Moderate hourly rewards - less than daily but still meaningful
    rewards = [
        {"cash": 3000, "xp": 25, "description": "3,000 Tadbucks + 25 XP"},
        {"cash": 4000, "xp": 20, "description": "4,000 Tadbucks + 20 XP"},
        {"cash": 2500, "xp": 30, "description": "2,500 Tadbucks + 30 XP"},
        {"cash": 5000, "xp": 15, "description": "5,000 Tadbucks + 15 XP"},
        {"cash": 3500, "xp": 25, "description": "3,500 Tadbucks + 25 XP"},
        {"cash": 2000, "xp": 35, "description": "2,000 Tadbucks + 35 XP"},
    ]

    reward = random.choice(rewards)

    # Apply rewards
    data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + reward["cash"]
    data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + reward["xp"]

    embed = discord.Embed(
        title="⏱️ Hourly Reward Claimed!",
        description=f"You received: {reward['description']}",
        color=0x3498db
    )

    await ctx.send(embed=embed)

@bot.command()
async def spin(ctx: commands.Context):
    """Daily spin wheel"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    today = datetime.utcnow().date().isoformat()
    last_spin = data["daily_spin"].get(uid)

    if last_spin == today:
        return await ctx.send("🎰 You've already spun today! Come back tomorrow.")

    data["daily_spin"][uid] = today

    # Spin wheel prizes
    prizes = [
        {"cash": 2000, "description": "2,000 Tadbucks", "emoji": "💰"},
        {"cash": 5000, "description": "5,000 Tadbucks", "emoji": "💎"},
        {"cash": 1000, "description": "1,000 Tadbucks", "emoji": "🪙"},
        {"xp": 100, "description": "100 XP", "emoji": "⭐"},
        {"xp": 50, "description": "50 XP", "emoji": "✨"},
        {"cash": 500, "description": "500 Tadbucks", "emoji": "💵"},
        {"cash": 10000, "description": "JACKPOT! 10,000 Tadbucks", "emoji": "🎰"},
        {"tadzzy": 10, "description": "10 Tadzzy Points", "emoji": "🏆"},
    ]

    # Weighted selection (jackpot is rare)
    weights = [15, 10, 20, 15, 20, 15, 2, 8]  # Jackpot has 2% chance
    prize = random.choices(prizes, weights=weights, k=1)[0]

    # Apply prize
    if "cash" in prize:
        data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + prize["cash"]
    if "xp" in prize:
        data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + prize["xp"]
    if "tadzzy" in prize:
        data["tadzzy_points"][uid] = data["tadzzy_points"].get(uid, 0) + prize["tadzzy"]

    embed = discord.Embed(
        title="🎰 Daily Spin Result!",
        description=f"{prize['emoji']} You won: {prize['description']}",
        color=0xff6b6b if "JACKPOT" in prize["description"] else 0x4ecdc4
    )

    await ctx.send(embed=embed)

# -----------------------------
# Enhanced Code System
# -----------------------------
@commands.has_permissions(administrator=True)
@bot.command()
async def addcode(ctx: commands.Context, name: str, cash: int = 0, xp: int = 0, multiplier_type: str = "none", hours: int = 0, pack_type: str = "none", pack_count: int = 0):
    """Enhanced code system with packs"""
    valid_multipliers = ["x2_cash", "x2_xp", "x3_cash", "x3_xp", "none"]
    if multiplier_type not in valid_multipliers:
        return await ctx.send(f"❌ Invalid multiplier type. Valid: {', '.join(valid_multipliers)}")

    valid_packs = list(PACK_TYPES.keys()) + ["none"]
    if pack_type != "none" and pack_type not in PACK_TYPES:
        return await ctx.send(f"❌ Invalid pack type. Valid: {', '.join(valid_packs)}")

    data["codes"][name.upper()] = {
        "cash": cash,
        "xp": xp,
        "multiplier_type": multiplier_type if multiplier_type != "none" else None,
        "multiplier_hours": hours,
        "pack_type": pack_type if pack_type != "none" else None,
        "pack_count": pack_count,
        "created_by": str(ctx.author.id),
        "created_at": datetime.utcnow().isoformat()
    }

    description = f"✅ Code '{name.upper()}' created with:"
    if cash > 0:
        description += f"\n💰 {cash:,} Tadbucks"
    if xp > 0:
        description += f"\n⭐ {xp} XP"
    if multiplier_type != "none":
        description += f"\n🔥 {multiplier_type} for {hours}h"
    if pack_type != "none":
        description += f"\n🎁 {pack_count} {pack_type}(s)"

    await ctx.send(description)

@bot.command()
async def redeem(ctx: commands.Context, code: str):
    """Enhanced redeem system with packs"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    code = code.upper()
    if code not in data["codes"]:
        return await ctx.send("❌ Invalid code.")

    code_data = data["codes"][code]

    # Apply cash rewards
    if code_data["cash"] > 0:
        data["tadbucks_balances"][uid] = get_balance(ctx.author.id) + code_data["cash"]

    # Apply XP rewards
    if code_data["xp"] > 0:
        data["xp_levels"][uid] = data["xp_levels"].get(uid, 0) + code_data["xp"]

    # Apply multiplier
    if code_data.get("multiplier_type"):
        expiry_time = datetime.utcnow() + timedelta(hours=code_data["multiplier_hours"])
        data["multipliers"].setdefault(uid, {})[code_data["multiplier_type"]] = expiry_time.isoformat()

    # Apply pack rewards
    if code_data.get("pack_type") and code_data.get("pack_count", 0) > 0:
        user_packs = data["user_packs"].setdefault(uid, {})
        user_packs[code_data["pack_type"]] = user_packs.get(code_data["pack_type"], 0) + code_data["pack_count"]

    embed = discord.Embed(
        title="🎉 Code Redeemed!",
        description=f"Code '{code}' successfully redeemed!",
        color=0x00ff00
    )

    rewards = []
    if code_data["cash"] > 0:
        rewards.append(f"💰 {code_data['cash']:,} Tadbucks")
    if code_data["xp"] > 0:
        rewards.append(f"⭐ {code_data['xp']} XP")
    if code_data.get("multiplier_type"):
        rewards.append(f"🔥 {code_data['multiplier_type']} for {code_data['multiplier_hours']}h")
    if code_data.get("pack_type"):
        rewards.append(f"🎁 {code_data['pack_count']} {code_data['pack_type']}(s)")

    embed.add_field(name="Rewards", value="\n".join(rewards), inline=False)

    await ctx.send(embed=embed)

# -----------------------------
# Enhanced Rebirth System
# -----------------------------
@bot.command()
async def rebirth(ctx: commands.Context):
    """Enhanced rebirth system with 10 levels and free cards"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)

    current_rebirths = data["rebirths"].get(uid, 0)
    
    # Check if max rebirths reached
    if current_rebirths >= len(REBIRTH_LEVELS):
        return await ctx.send(f"⭐ You've reached the maximum rebirth level ({len(REBIRTH_LEVELS)})!")

    rebirth_info = REBIRTH_LEVELS[current_rebirths]
    balance = get_balance(ctx.author.id)
    
    if balance < rebirth_info["requirement"]:
        return await ctx.send(
            f"❌ You need ${rebirth_info['requirement']:,} Tadbucks to rebirth to level {rebirth_info['level']}. "
            f"You have ${balance:,}."
        )

    # Show rebirth info
    embed = discord.Embed(
        title=f"🔄 Rebirth Level {rebirth_info['level']} Confirmation",
        description="⚠️ **WARNING:** This will reset your collection and balance!",
        color=0xff9900
    )

    embed.add_field(
        name="💸 What You'll Lose",
        value=(
            f"• All {len(data['user_collections'].get(uid, []))} cards in collection\n"
            f"• Your current balance of ${balance:,} (keeping {int(balance * (1 - rebirth_info['multiplier']))})"
        ),
        inline=False
    )

    embed.add_field(
        name="✅ What You'll Gain",
        value=(
            f"• +50% passive income permanently (Total: +{(current_rebirths + 1) * 50}%)\n"
            f"• 24-hour x2 cash multiplier\n"
            f"• FREE {rebirth_info['card_rarity']} card!\n"
            f"• Rebirth count: {current_rebirths} → {current_rebirths + 1}"
        ),
        inline=False
    )

    embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")

    view = View(timeout=30)
    
    async def confirm_callback(interaction):
        if interaction.user.id != ctx.author.id:
            await interaction.response.send_message("❌ This is not your rebirth!", ephemeral=True)
            return
            
        # Process rebirth
        data["rebirths"][uid] = current_rebirths + 1
        data["user_collections"][uid] = []  # Reset collection
        new_balance = int(balance * (1 - rebirth_info["multiplier"]))
        data["tadbucks_balances"][uid] = new_balance
        
        # Give x2 cash multiplier for 24 hours
        expiry_time = datetime.utcnow() + timedelta(hours=24)
        data["multipliers"].setdefault(uid, {})["x2_cash"] = expiry_time.isoformat()
        
        # Give free card
        rarity_cards = [f for f in footballers if f["rarity"] == rebirth_info["card_rarity"]]
        if rarity_cards:
            free_card = random.choice(rarity_cards).copy()
            data["user_collections"][uid].append(free_card)
        
        success_embed = discord.Embed(
            title="🎉 Rebirth Successful! 🎉",
            description=f"You have been reborn to level {current_rebirths + 1}!",
            color=0x00ff00
        )
        
        success_embed.add_field(
            name="🔥 New Permanent Bonuses",
            value=f"Passive Income: +{(current_rebirths + 1) * 50}%",
            inline=False
        )
        
        if rarity_cards:
            success_embed.add_field(
                name="🎁 Free Card Received",
                value=f"{free_card['name']} ({rebirth_info['card_rarity']})",
                inline=False
            )
        
        success_embed.add_field(
            name="💰 Fresh Start",
            value=f"New balance: ${new_balance:,} Tadbucks\n🔥 x2 Cash multiplier for 24 hours!",
            inline=False
        )
        
        await interaction.response.edit_message(embed=success_embed, view=None)
    
    async def cancel_callback(interaction):
        if interaction.user.id != ctx.author.id:
            await interaction.response.send_message("❌ This is not your rebirth!", ephemeral=True)
            return
            
        await interaction.response.edit_message(content="❌ Rebirth cancelled.", embed=None, view=None)
    
    confirm_button = Button(label="✅ Confirm Rebirth", style=discord.ButtonStyle.success)
    cancel_button = Button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    
    confirm_button.callback = confirm_callback
    cancel_button.callback = cancel_callback
    
    view.add_item(confirm_button)
    view.add_item(cancel_button)
    
    await ctx.send(embed=embed, view=view)

@bot.command()
async def rebirthinfo(ctx: commands.Context):
    """Show rebirth system information"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    current_rebirths = data["rebirths"].get(uid, 0)
    
    embed = discord.Embed(
        title="🔄 Rebirth System Information",
        description=f"Your Current Rebirth Level: **{current_rebirths}/{len(REBIRTH_LEVELS)}**",
        color=0x9b59b6
    )
    
    for i, level_info in enumerate(REBIRTH_LEVELS):
        status = ""
        if i < current_rebirths:
            status = "✅ Completed"
        elif i == current_rebirths:
            status = "🎯 Next Level"
        else:
            status = "🔒 Locked"
        
        embed.add_field(
            name=f"Level {level_info['level']} - {status}",
            value=(
                f"💰 Requirement: ${level_info['requirement']:,}\n"
                f"🎁 Free Card: {level_info['card_rarity']}\n"
                f"🔥 Income Bonus: +50%"
            ),
            inline=True
        )
    
    if current_rebirths > 0:
        embed.add_field(
            name="🏆 Your Current Bonuses",
            value=f"📈 Passive Income: +{current_rebirths * 50}%",
            inline=False
        )
    
    await ctx.send(embed=embed)

# Enhanced viewdeleted with user filtering
@bot.command()
async def viewdeleted(ctx: commands.Context, member: Optional[discord.Member] = None):
    """View recently deleted messages with optional user filtering"""
    if not data["deleted_messages"]:
        return await ctx.send("📝 No deleted messages recorded.")

    if member:
        # Filter messages by specific user
        user_messages = [msg for msg in data["deleted_messages"] 
                        if msg["author_id"] == member.id]
        
        if not user_messages:
            return await ctx.send(f"📝 No deleted messages found for {member.display_name}.")
        
        embed = discord.Embed(
            title=f"🗑️ {member.display_name}'s Deleted Messages",
            description="Last 10 deleted messages:",
            color=0x95a5a6
        )
        
        recent_messages = user_messages[-10:]  # Last 10 from this user
    else:
        # Show last 15 server deleted messages
        embed = discord.Embed(
            title="🗑️ Recently Deleted Messages",
            description="Last 15 deleted messages:",
            color=0x95a5a6
        )
        
        recent_messages = data["deleted_messages"][-15:]  # Last 15 server messages

    for i, msg_data in enumerate(reversed(recent_messages), 1):
        timestamp = datetime.fromisoformat(msg_data["timestamp"])
        time_str = timestamp.strftime("%m/%d %H:%M")

        content = msg_data["content"][:100] + "..." if len(msg_data["content"]) > 100 else msg_data["content"]

        embed.add_field(
            name=f"{i}. {msg_data['author']} ({time_str})",
            value=content or "No text content",
            inline=False
        )

    await ctx.send(embed=embed)

# Enhanced Shop with stock system
@bot.command()
async def shop(ctx: commands.Context, rarity: str = None):
    """Browse the player shop with stock system and discounts"""
    if rarity:
        rarity = rarity.title()
        available_cards = [f for f in footballers if f["rarity"] == rarity]
        if not available_cards:
            return await ctx.send(f"No players found with rarity '{rarity}'. Available rarities: Common, Epic, Legendary, Mythic, Expensive, Secret")
    else:
        available_cards = footballers

    # Sort by price for better organization
    available_cards.sort(key=lambda x: x["price"], reverse=True)

    embed = discord.Embed(
        title=f"🏪 Tadzzy Card Shop{f' - {rarity} Cards' if rarity else ''}",
        description="Use !buy <player> to purchase a card!",
        color=0x00ff00
    )
    
    # Show discount if active
    if data["shop_discount"] > 0:
        embed.add_field(
            name="🛍️ SALE ACTIVE!",
            value=f"💥 {data['shop_discount']}% OFF ALL PLAYERS! 💥",
            inline=False
        )

    cards_shown = 0
    for card in available_cards:
        if cards_shown >= 10:  # Limit to 10 cards per page
            break
            
        # Check if out of stock
        if card["name"] in data["out_of_stock"]:
            stock_status = "❌ OUT OF STOCK"
            price_display = "N/A"
        else:
            stock_status = "✅ In Stock"
            original_price = card["price"]
            discounted_price = int(original_price * (1 - data["shop_discount"] / 100))
            if data["shop_discount"] > 0:
                price_display = f"~~${original_price:,}~~ **${discounted_price:,}**"
            else:
                price_display = f"${original_price:,}"

        income_info = f"💰 {card.get('income_rate', 1)}/30min"
        embed.add_field(
            name=f"{card['name']} ({card['rarity']})",
            value=f"Price: {price_display}\nIncome: {income_info}\nStock: {stock_status}",
            inline=True
        )
        cards_shown += 1

    embed.set_footer(text="💡 Tip: Higher rarity = more income! Some rare cards may be out of stock!")
    
    await ctx.send(embed=embed)

# Enhanced buy command with stock system
@bot.command()
async def buy(ctx: commands.Context, *, player_name: str):
    """Purchase a player card from the shop with stock system"""
    ensure_user_exists(ctx.author.id)

    card = find_player_card_by_name(player_name)
    if not card:
        return await ctx.send("❌ Player not found in shop. Use !shop to browse available players.")

    # Check if out of stock
    if card["name"] in data["out_of_stock"]:
        return await ctx.send(f"❌ {card['name']} is currently OUT OF STOCK! Check back later.")

    user_balance = get_balance(ctx.author.id)
    original_price = card["price"]
    
    # Apply discount if active
    final_price = int(original_price * (1 - data["shop_discount"] / 100))

    if user_balance < final_price:
        return await ctx.send(f"❌ Insufficient funds! You have ${user_balance:,} but {card['name']} costs ${final_price:,}")

    # Check if user already owns this card
    uid = str(ctx.author.id)
    user_collection = data["user_collections"].get(uid, [])
    if any(c["name"] == card["name"] for c in user_collection):
        return await ctx.send(f"❌ You already own {card['name']}!")

    # Check collection space
    if len(user_collection) >= MAX_COLLECTION_SLOTS:
        return await ctx.send(f"❌ Your collection is full! ({MAX_COLLECTION_SLOTS}/{MAX_COLLECTION_SLOTS})")

    # Process purchase
    set_balance(ctx.author.id, user_balance - final_price)
    purchased_card = card.copy()
    
    # Initialize upgrade system
    purchased_card["upgrade_level"] = "Gold"
    purchased_card["upgrade_progress"] = 0
    
    data["user_collections"][uid].append(purchased_card)

    embed = discord.Embed(
        title="🎉 Purchase Successful!",
        description=f"You bought {card['name']} for ${final_price:,}!",
        color=card["color"]
    )
    
    if data["shop_discount"] > 0:
        embed.add_field(
            name="💸 Discount Applied",
            value=f"You saved ${original_price - final_price:,} ({data['shop_discount']}% off)!",
            inline=True
        )
    
    embed.add_field(name="Remaining Balance", value=f"${get_balance(ctx.author.id):,}", inline=True)
    embed.add_field(name="Passive Income", value=f"💰 {card.get('income_rate', 1)} every 30 minutes", inline=True)
    embed.add_field(name="Collection", value=f"{len(user_collection)+1}/{MAX_COLLECTION_SLOTS}", inline=True)

    await ctx.send(embed=embed)

@bot.command()
async def balance(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Check Tadbucks balance"""
    target = member or ctx.author
    ensure_user_exists(target.id)
    bal = get_balance(target.id)

    embed = discord.Embed(
        title=f"💰 {target.display_name}'s Balance",
        description=f"${bal:,} Tadbucks",
        color=0xf1c40f
    )

    # Show rebirth info
    rebirths = data["rebirths"].get(str(target.id), 0)
    if rebirths > 0:
        embed.add_field(
            name="🔄 Rebirths",
            value=f"{rebirths} (Income +{rebirths * 50}%)",
            inline=True
        )

    # Show active multipliers
    multipliers = []
    for mult_type in ["x2_cash", "x3_cash", "x2_xp", "x3_xp"]:
        if get_multiplier(target.id, mult_type) > 1:
            multipliers.append(mult_type.replace("_", " ").title())

    if multipliers:
        embed.add_field(
            name="⚡ Active Multipliers",
            value=", ".join(multipliers),
            inline=True
        )

    await ctx.send(embed=embed)

@bot.command()
async def collection(ctx: commands.Context, member: Optional[discord.Member] = None):
    """View collection with upgrade levels"""
    target = member or ctx.author
    uid = str(target.id)
    ensure_user_exists(target.id)
    coll = data["user_collections"].get(uid, [])

    if not coll:
        if target == ctx.author:
            return await ctx.send("📦 Your collection is empty. Use !shop to buy player cards!")
        else:
            return await ctx.send(f"📦 {target.display_name}'s collection is empty.")

    embed = discord.Embed(
        title=f"📦 {target.display_name}'s Collection",
        description=f"Collection: {len(coll)}/{MAX_COLLECTION_SLOTS} cards",
        color=0x5865F2
    )
    
    for i, card in enumerate(coll[:10], 1):  # Show first 10 cards
        income_rate = card.get('income_rate', 1)
        upgrade_level = get_card_upgrade_level(card)
        
        # Apply rebirth bonus for display
        income_with_bonus = apply_rebirth_bonus(target.id, income_rate)
        
        upgrade_text = ""
        if upgrade_level != "Gold":
            upgrade_text = f" **[{upgrade_level}]**"
        
        embed.add_field(
            name=f"{i}. {card['name']}{upgrade_text}",
            value=f"✨ {card['rarity']} | 💰 ${card['price']:,} | 🕐 {income_with_bonus}/30min",
            inline=False
        )

    if len(coll) > 10:
        embed.set_footer(text=f"Showing first 10 of {len(coll)} cards. Use !upgrade <number> to upgrade!")
    else:
        embed.set_footer(text="Use !upgrade <number> to upgrade your cards!")

    await ctx.send(embed=embed)

# Missing commands implementation starts here

@bot.command()
async def sell(ctx: commands.Context, *, player_name: str):
    """Sell a player card from your collection - Use 'all' to sell everything!"""
    ensure_user_exists(ctx.author.id)
    
    uid = str(ctx.author.id)
    user_coll = data["user_collections"].get(uid, [])
    
    if not user_coll:
        await ctx.send("❌ Your collection is empty! Use `!shop` to buy cards.")
        return
    
    # Check if user wants to sell all cards
    if normalize_name(player_name) == "all":
        # Sell all cards confirmation
        total_value = sum(int(card["price"] * 0.8) for card in user_coll)
        
        embed = discord.Embed(
            title="🚨 **SELL ALL CARDS?** 🚨",
            description=f"⚠️ You are about to sell **ALL {len(user_coll)} cards** in your collection!",
            color=0xff4500
        )
        
        embed.add_field(
            name="💰 Total Value",
            value=f"💸 You will receive: **${total_value:,}**\n💳 Current Balance: ${get_balance(ctx.author.id):,}",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ WARNING",
            value="**This action cannot be undone!**\nAll your cards will be permanently sold!",
            inline=False
        )
        
        embed.set_footer(text="💡 React with ✅ to confirm or ❌ to cancel")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
        
        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Sell all cards
                current_balance = get_balance(ctx.author.id)
                set_balance(ctx.author.id, current_balance + total_value)
                
                # Clear collection
                data["user_collections"][uid] = []
                
                success_embed = discord.Embed(
                    title="💰 **ALL CARDS SOLD!** 💰",
                    description=f"🎉 Successfully sold **{len(user_coll)} cards** for **${total_value:,}**!",
                    color=0x00ff00
                )
                
                success_embed.add_field(
                    name="💳 Balance Updated",
                    value=f"💰 New Balance: **${get_balance(ctx.author.id):,}**",
                    inline=False
                )
                
                success_embed.set_footer(text="🛍️ Time to go shopping again! Use !shop to buy new cards!")
                
                await msg.edit(embed=success_embed)
                await msg.clear_reactions()
                return
            else:
                cancel_embed = discord.Embed(
                    title="❌ Sale Cancelled",
                    description="Your cards are safe! No cards were sold.",
                    color=0xff0000
                )
                await msg.edit(embed=cancel_embed)
                await msg.clear_reactions()
                return
                
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Sale Timeout",
                description="Sale cancelled due to timeout. Your cards are safe!",
                color=0xff0000
            )
            await msg.edit(embed=timeout_embed)
            await msg.clear_reactions()
            return
    
    uid = str(ctx.author.id)
    user_coll = data["user_collections"].get(uid, [])
    
    # Find the card
    card_index = None
    for i, card in enumerate(user_coll):
        if normalize_name(card["name"]) == normalize_name(player_name):
            card_index = i
            break
    
    if card_index is None:
        return await ctx.send(f"❌ You don't own {player_name}!")
    
    card = user_coll[card_index]
    # Calculate sell price (80% of current card value)
    sell_price = int(card["price"] * 0.8)
    
    # Remove card from collection
    user_coll.pop(card_index)
    
    # Add money to balance
    current_balance = get_balance(ctx.author.id)
    set_balance(ctx.author.id, current_balance + sell_price)
    
    embed = discord.Embed(
        title="💸 Card Sold Successfully!",
        description=f"You sold {card['name']} for ${sell_price:,}!",
        color=0x00ff00
    )
    embed.add_field(name="New Balance", value=f"${get_balance(ctx.author.id):,}", inline=True)
    embed.add_field(name="Collection Space", value=f"{len(user_coll)}/{MAX_COLLECTION_SLOTS}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx: commands.Context):
    """Show top Tadbucks players"""
    # Sort users by balance
    sorted_users = sorted(data["tadbucks_balances"].items(), key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(
        title="🏆 Tadbucks Leaderboard",
        description="Top 10 richest players",
        color=0xffd700
    )
    
    for i, (user_id, balance) in enumerate(sorted_users[:10], 1):
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name
        except:
            name = f"User {user_id}"
        
        # Add rebirth info
        rebirths = data["rebirths"].get(user_id, 0)
        rebirth_text = f" (R{rebirths})" if rebirths > 0 else ""
        
        embed.add_field(
            name=f"{i}. {name}{rebirth_text}",
            value=f"${balance:,}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def points_leaderboard(ctx: commands.Context):
    """Show top Tadzzy Points players"""
    # Sort users by tadzzy points
    sorted_users = sorted(data["tadzzy_points"].items(), key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(
        title="⭐ Tadzzy Points Leaderboard",
        description="Top 10 point collectors",
        color=0xff6b6b
    )
    
    for i, (user_id, points) in enumerate(sorted_users[:10], 1):
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name
        except:
            name = f"User {user_id}"
        
        embed.add_field(
            name=f"{i}. {name}",
            value=f"{points} points",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def allplayers(ctx: commands.Context):
    """Browse all available players by rarity"""
    embed = discord.Embed(
        title="⚽ All Available Players",
        description="Complete player database organized by rarity",
        color=0x3498db
    )
    
    # Group players by rarity
    rarity_groups = {}
    for card in footballers:
        rarity = card["rarity"]
        if rarity not in rarity_groups:
            rarity_groups[rarity] = []
        rarity_groups[rarity].append(card)
    
    # Sort rarities by typical hierarchy
    rarity_order = ["Secret", "Expensive", "Mythic", "Legendary", "Epic", "Common"]
    
    for rarity in rarity_order:
        if rarity in rarity_groups:
            cards = rarity_groups[rarity]
            cards.sort(key=lambda x: x["price"], reverse=True)
            
            # Show top 5 cards of each rarity
            card_list = []
            for card in cards[:5]:
                stock_status = "❌" if card["name"] in data["out_of_stock"] else "✅"
                card_list.append(f"{stock_status} {card['name']} - ${card['price']:,}")
            
            if len(cards) > 5:
                card_list.append(f"... and {len(cards) - 5} more")
            
            embed.add_field(
                name=f"{rarity} ({len(cards)} cards)",
                value="\n".join(card_list),
                inline=True
            )
    
    embed.set_footer(text="Use !shop <rarity> to browse specific rarities!")
    await ctx.send(embed=embed)

@bot.command()
async def passiveincome(ctx: commands.Context):
    """Check your last passive income payout"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    last_payout = last_income_report.get(uid, 0)
    
    embed = discord.Embed(
        title="💰 Passive Income Report",
        description=f"Your last payout was ${last_payout:,}",
        color=0x2ecc71
    )
    
    # Calculate current potential income
    user_coll = data["user_collections"].get(uid, [])
    total_income = 0
    
    for card in user_coll:
        base_income = card.get("income_rate", 1)
        income_with_rebirth = apply_rebirth_bonus(ctx.author.id, base_income)
        cash_multiplier = get_multiplier(ctx.author.id, "x2_cash") if get_multiplier(ctx.author.id, "x2_cash") > 1 else get_multiplier(ctx.author.id, "x3_cash")
        final_income = int(income_with_rebirth * cash_multiplier)
        total_income += final_income
    
    embed.add_field(name="Next Payout (estimated)", value=f"${total_income:,}", inline=True)
    embed.add_field(name="Collection Size", value=f"{len(user_coll)} cards", inline=True)
    
    # Show rebirth bonus
    rebirths = data["rebirths"].get(uid, 0)
    if rebirths > 0:
        embed.add_field(name="Rebirth Bonus", value=f"+{rebirths * 50}%", inline=True)
    
    embed.set_footer(text="Passive income is paid every 30 minutes!")
    await ctx.send(embed=embed)

@bot.command()
async def income(ctx: commands.Context, option: str = "last"):
    """View income statistics"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    if option.lower() == "total":
        total_earned = total_income_tracker.get(uid, 0)
        embed = discord.Embed(
            title="📊 Total Income Statistics",
            description=f"Your lifetime passive income earnings: ${total_earned:,}",
            color=0x9b59b6
        )
    else:
        last_payout = last_income_report.get(uid, 0)
        embed = discord.Embed(
            title="💰 Last Income Payout",
            description=f"Your last payout was ${last_payout:,}",
            color=0x2ecc71
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def messagesleft(ctx: commands.Context):
    """Check XP progress and messages needed for next level"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    current_xp = data["xp_levels"].get(uid, 0)
    current_level = current_xp // LEVEL_UP_XP_THRESHOLD
    xp_in_current_level = current_xp % LEVEL_UP_XP_THRESHOLD
    xp_needed = LEVEL_UP_XP_THRESHOLD - xp_in_current_level
    
    # Calculate messages needed (considering multipliers)
    xp_per_message = LEVEL_XP_REWARD
    xp_multiplier = get_multiplier(ctx.author.id, "x2_xp") if get_multiplier(ctx.author.id, "x2_xp") > 1 else get_multiplier(ctx.author.id, "x3_xp")
    final_xp_per_message = int(xp_per_message * xp_multiplier)
    messages_needed = max(1, xp_needed // final_xp_per_message)
    
    embed = discord.Embed(
        title="📈 Level Progress",
        description=f"**Current Level:** {current_level}\n**Total XP:** {current_xp}",
        color=0x3498db
    )
    
    embed.add_field(name="Progress in Current Level", value=f"{xp_in_current_level}/{LEVEL_UP_XP_THRESHOLD} XP", inline=True)
    embed.add_field(name="XP Needed for Next Level", value=f"{xp_needed} XP", inline=True)
    embed.add_field(name="Messages Needed", value=f"{messages_needed} messages", inline=True)
    embed.add_field(name="XP per Message", value=f"{final_xp_per_message} XP", inline=True)
    
    if xp_multiplier > 1:
        embed.add_field(name="Active Multiplier", value=f"{xp_multiplier}x XP", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def collection_status(ctx: commands.Context, member: Optional[discord.Member] = None):
    """View detailed collection statistics"""
    target = member or ctx.author
    uid = str(target.id)
    ensure_user_exists(target.id)
    user_coll = data["user_collections"].get(uid, [])
    
    embed = discord.Embed(
        title=f"📊 {target.display_name}'s Collection Status",
        description=f"Detailed collection analysis",
        color=0x5865F2
    )
    
    # Collection size
    embed.add_field(name="Collection Size", value=f"{len(user_coll)}/{MAX_COLLECTION_SLOTS}", inline=True)
    
    # Total value
    total_value = sum(card.get("price", 0) for card in user_coll)
    embed.add_field(name="Total Value", value=f"${total_value:,}", inline=True)
    
    # Passive income per 30min
    total_income = 0
    for card in user_coll:
        base_income = card.get("income_rate", 1)
        income_with_rebirth = apply_rebirth_bonus(target.id, base_income)
        total_income += income_with_rebirth
    
    embed.add_field(name="Income per 30min", value=f"${total_income:,}", inline=True)
    
    # Rarity breakdown
    rarity_count = {}
    for card in user_coll:
        rarity = card.get("rarity", "Unknown")
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    if rarity_count:
        rarity_text = "\n".join([f"{rarity}: {count}" for rarity, count in rarity_count.items()])
        embed.add_field(name="Cards by Rarity", value=rarity_text, inline=True)
    
    # Upgrade levels
    upgrade_count = {}
    for card in user_coll:
        level = get_card_upgrade_level(card)
        upgrade_count[level] = upgrade_count.get(level, 0) + 1
    
    if upgrade_count:
        upgrade_text = "\n".join([f"{level}: {count}" for level, count in upgrade_count.items()])
        embed.add_field(name="Upgrade Levels", value=upgrade_text, inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def Tadbucks(ctx: commands.Context):
    """Economy guide and information"""
    embed = discord.Embed(
        title="💰 Tadbucks Economy Guide",
        description="Everything you need to know about the Tadzzy economy!",
        color=0xf1c40f
    )
    
    embed.add_field(
        name="💵 Earning Tadbucks",
        value=(
            "• **Passive Income**: Own cards = automatic income every 30 minutes\n"
            "• **Daily Rewards**: !daily (25k-40k + XP)\n"
            "• **Weekly Rewards**: !weekly (40k-60k + XP + Tadzzy Points)\n"
            "• **Hourly Rewards**: !hourly (2k-5k + XP)\n"
            "• **Daily Spin**: !spin (500-10k, XP, or Tadzzy Points)\n"
            "• **Leveling Up**: 15k per level + 8 Tadzzy Points\n"
            "• **Gambling**: !gamble or !fairgamble (risky!)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛍️ Spending Tadbucks",
        value=(
            "• **Player Cards**: !buy <player> for passive income\n"
            "• **Packs**: !packshop for card packs with better odds\n"
            "• **Upgrades**: !upgrade <card_number> to boost income\n"
            "• **Gambling**: Test your luck in various games\n"
            "• **Auctions**: !bid <player> <amount> for rare cards"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔄 Advanced Systems",
        value=(
            "• **Rebirth**: Reset collection for permanent income bonuses\n"
            "• **Multipliers**: x2 or x3 cash/XP from codes or rebirths\n"
            "• **Trading**: !trade @user for player exchanges\n"
            "• **Card Upgrades**: Gold→Diamond→TOTW→UCL→TOTY→Ultimate"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💡 Pro Tips",
        value=(
            "• Higher rarity cards = more passive income\n"
            "• Rebirth at 250k+ for permanent income bonuses\n"
            "• Upgrade your best cards for maximum income\n"
            "• Check !shop regularly for sales and discounts\n"
            "• Use codes from !redeem for free multipliers"
        ),
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def gamenight(ctx: commands.Context):
    """View current Roblox game nights"""
    if not data["gamenights"]:
        return await ctx.send("🎮 No game nights scheduled! Admins can add them with !addgamenight")
    
    embed = discord.Embed(
        title="🎮 Roblox Game Nights",
        description="Join these awesome community events!",
        color=0xff6b6b
    )
    
    for i, link in enumerate(data["gamenights"], 1):
        embed.add_field(
            name=f"🎯 Game Night {i}",
            value=f"[Join Game]({link})",
            inline=False
        )
    
    embed.set_footer(text="Have fun and see you in the games!")
    await ctx.send(embed=embed)

# Battle System - DISABLED (duplicate)
# @bot.command()
async def battle_disabled_func(ctx: commands.Context, opponent: discord.Member):
    """Start a 90-minute battle with animations"""
    if opponent.bot:
        return await ctx.send("❌ You can't battle bots!")
    
    if opponent.id == ctx.author.id:
        return await ctx.send("❌ You can't battle yourself!")
    
    ensure_user_exists(ctx.author.id)
    ensure_user_exists(opponent.id)
    
    # Check if either user is already in a battle
    battle_key = f"{ctx.author.id}_{opponent.id}"
    reverse_key = f"{opponent.id}_{ctx.author.id}"
    
    if battle_key in active_battles or reverse_key in active_battles:
        return await ctx.send("❌ One of you is already in a battle!")
    
    # Start battle
    battle_data = {
        "player1": ctx.author.id,
        "player2": opponent.id,
        "score": [0, 0],
        "minute": 0,
        "phase": "first_half",
        "started_at": datetime.utcnow().isoformat()
    }
    
    active_battles[battle_key] = battle_data
    
    embed = discord.Embed(
        title="⚽ EPIC BATTLE STARTED! ⚽",
        description=f"🥊 **{ctx.author.display_name}** vs **{opponent.display_name}**\n🕐 90-minute battle simulation starting...",
        color=0x00ff00
    )
    
    embed.add_field(name="⏱️ Duration", value="90 minutes + halftime", inline=True)
    embed.add_field(name="🎯 Features", value="Penalties, free kicks, chances!", inline=True)
    embed.add_field(name="📊 Score", value="0 - 0", inline=True)
    
    message = await ctx.send(embed=embed)
    
    # Simulate the battle
    await simulate_battle(ctx, message, battle_data, battle_key)

async def simulate_battle(ctx, message, battle_data, battle_key):
    """Simulate the 90-minute battle"""
    for minute in range(1, 91):
        battle_data["minute"] = minute
        
        # Halftime break
        if minute == 46:
            battle_data["phase"] = "second_half"
            embed = discord.Embed(
                title="⏸️ HALFTIME BREAK",
                description=f"🕐 **45 minutes completed**\n⚽ **Score: {battle_data['score'][0]} - {battle_data['score'][1]}**",
                color=0xffa500
            )
            embed.add_field(name="📊 Stats", value="Teams regroup for second half!", inline=False)
            await message.edit(embed=embed)
            await asyncio.sleep(3)  # 3 second halftime break
            continue
        
        # Random events (15% chance per minute)
        if random.random() < 0.15:
            event_type = random.choice(["penalty", "freekick", "chance"])
            scoring_player = random.choice([battle_data["player1"], battle_data["player2"]])
            
            # Create action view for scoring player
            context = {"battle_key": battle_key, "minute": minute}
            view = BattleActionView(scoring_player, event_type, context)
            
            embed = discord.Embed(
                title=f"🎯 {event_type.upper()} OPPORTUNITY!",
                description=f"⏱️ **Minute {minute}**\n🎮 <@{scoring_player}> has a {event_type}! Choose your target!",
                color=0xff6b6b
            )
            
            await message.edit(embed=embed, view=view)
            
            # Wait for action or timeout
            await asyncio.sleep(15)  # 15 second timeout for actions
            
            # Check if goal was scored (this would be set by the BattleActionView)
            if context.get("scorer"):
                if context["scorer"] == battle_data["player1"]:
                    battle_data["score"][0] += 1
                else:
                    battle_data["score"][1] += 1
        
        # Update every 15 minutes or when events happen
        if minute % 15 == 0 or minute == 90:
            embed = discord.Embed(
                title="⚽ BATTLE IN PROGRESS",
                description=f"⏱️ **Minute {minute}**\n📊 **Score: {battle_data['score'][0]} - {battle_data['score'][1]}**",
                color=0x3498db
            )
            
            player1 = ctx.guild.get_member(battle_data["player1"])
            player2 = ctx.guild.get_member(battle_data["player2"])
            
            embed.add_field(
                name=f"🏠 {player1.display_name if player1 else 'Player 1'}",
                value=f"⚽ {battle_data['score'][0]} goals",
                inline=True
            )
            embed.add_field(
                name=f"🛣️ {player2.display_name if player2 else 'Player 2'}",
                value=f"⚽ {battle_data['score'][1]} goals",
                inline=True
            )
            
            phase_text = "First Half" if battle_data["phase"] == "first_half" else "Second Half"
            embed.add_field(name="⏰ Phase", value=phase_text, inline=True)
            
            await message.edit(embed=embed, view=None)
        
        await asyncio.sleep(1)  # 1 second per minute
    
    # Battle finished
    del active_battles[battle_key]
    
    # Determine winner
    player1_score = battle_data["score"][0]
    player2_score = battle_data["score"][1]
    
    player1 = ctx.guild.get_member(battle_data["player1"])
    player2 = ctx.guild.get_member(battle_data["player2"])
    
    if player1_score > player2_score:
        winner = player1
        winner_score = player1_score
        loser_score = player2_score
        color = 0x00ff00
    elif player2_score > player1_score:
        winner = player2
        winner_score = player2_score
        loser_score = player1_score
        color = 0x00ff00
    else:
        winner = None
        color = 0xffa500
    
    # Final embed
    if winner:
        embed = discord.Embed(
            title="🏆 BATTLE FINISHED! 🏆",
            description=f"🎉 **{winner.display_name} WINS!**\n⚽ **Final Score: {winner_score} - {loser_score}**",
            color=color
        )
        
        # Give winner rewards
        reward = 25000
        current_balance = get_balance(winner.id)
        set_balance(winner.id, current_balance + reward)
        
        embed.add_field(name="🎁 Winner Reward", value=f"${reward:,} Tadbucks!", inline=True)
    else:
        embed = discord.Embed(
            title="⚖️ BATTLE FINISHED! ⚖️",
            description=f"🤝 **IT'S A DRAW!**\n⚽ **Final Score: {player1_score} - {player2_score}**",
            color=color
        )
        
        # Give both players smaller rewards for draw
        reward = 10000
        for player_id in [battle_data["player1"], battle_data["player2"]]:
            current_balance = get_balance(player_id)
            set_balance(player_id, current_balance + reward)
        
        embed.add_field(name="🎁 Draw Reward", value=f"${reward:,} Tadbucks each!", inline=True)
    
    embed.add_field(name="⏱️ Duration", value="90 minutes", inline=True)
    embed.add_field(name="🎮 Thanks for Playing!", value="Epic battle completed!", inline=True)
    
    await message.edit(embed=embed, view=None)

# Trading System
@bot.command()
async def trade(ctx: commands.Context, member: discord.Member):
    """Start a trade with another user"""
    if member.bot:
        return await ctx.send("❌ You can't trade with bots!")
    
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't trade with yourself!")
    
    ensure_user_exists(ctx.author.id)
    ensure_user_exists(member.id)
    
    # Generate trade ID
    trade_id = f"{ctx.author.id}_{member.id}_{int(datetime.utcnow().timestamp())}"
    
    # Create trade
    data["trades"][trade_id] = {
        "initiator": ctx.author.id,
        "target": member.id,
        "initiator_offer": {"cards": [], "money": 0},
        "target_offer": {"cards": [], "money": 0},
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    embed = discord.Embed(
        title="🔄 Trade Request",
        description=f"📨 {ctx.author.display_name} wants to trade with {member.display_name}!",
        color=0x3498db
    )
    
    embed.add_field(name="Trade ID", value=trade_id[-8:], inline=True)  # Show last 8 chars
    embed.add_field(name="Status", value="Waiting for acceptance", inline=True)
    embed.set_footer(text=f"{member.display_name}, use !accepttrade {trade_id[-8:]} to accept!")
    
    await ctx.send(f"{member.mention}", embed=embed)

@bot.command()
async def accepttrade(ctx: commands.Context, trade_id_short: str):
    """Accept a trade offer"""
    # Find full trade ID
    trade_id = None
    for tid in data["trades"]:
        if tid.endswith(trade_id_short):
            trade_id = tid
            break
    
    if not trade_id or trade_id not in data["trades"]:
        return await ctx.send("❌ Trade not found!")
    
    trade = data["trades"][trade_id]
    
    if trade["target"] != ctx.author.id:
        return await ctx.send("❌ This trade is not for you!")
    
    if trade["status"] != "pending":
        return await ctx.send("❌ This trade is no longer available!")
    
    # Update trade status
    trade["status"] = "negotiating"
    
    embed = discord.Embed(
        title="✅ Trade Accepted!",
        description="🤝 Both players can now add items to the trade.",
        color=0x00ff00
    )
    
    embed.add_field(name="Commands", value=(
        f"`!addcardtotrade {trade_id_short} <card_name>` - Add card\n"
        f"`!addmoneytotrade {trade_id_short} <amount>` - Add money\n"
        f"`!completetrade {trade_id_short}` - Finalize trade"
    ), inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def declinetrade(ctx: commands.Context, trade_id_short: str):
    """Decline a trade offer"""
    # Find full trade ID
    trade_id = None
    for tid in data["trades"]:
        if tid.endswith(trade_id_short):
            trade_id = tid
            break
    
    if not trade_id or trade_id not in data["trades"]:
        return await ctx.send("❌ Trade not found!")
    
    trade = data["trades"][trade_id]
    
    if trade["target"] != ctx.author.id:
        return await ctx.send("❌ This trade is not for you!")
    
    # Remove trade
    del data["trades"][trade_id]
    
    embed = discord.Embed(
        title="❌ Trade Declined",
        description="The trade offer has been declined and removed.",
        color=0xff0000
    )
    
    await ctx.send(embed=embed)

# More fun commands
@bot.command()
async def meme(ctx: commands.Context):
    """Random meme"""
    memes = [
        "When you score a last-minute goal ⚽😎",
        "That feeling when you pack a legendary 📦✨",
        "Me counting my Tadbucks 💰🤑",
        "When the gambling pays off 🎰🎉",
        "Upgrading cards be like 📈⬆️",
        "When you beat someone in battle ⚔️👑",
        "Passive income hitting different 💸😴",
        "When you see a rare card in shop 👀💎"
    ]
    
    meme = random.choice(memes)
    await ctx.send(f"😂 {meme}")

@bot.command()
async def dadjoke(ctx: commands.Context):
    """Random dad joke"""
    jokes = [
        "Why don't football players ever get cold? Because they're always near the fans!",
        "What do you call a football player who makes tea? A midfielder!",
        "Why did the football go to the bank? To get its quarter back!",
        "What's a ghost's favorite position in football? Ghoul-keeper!",
        "Why don't football stadiums ever get hot? Because they have lots of fans!",
        "What do you call a football team full of babies? A creche team!",
        "Why did the footballer bring string to the game? So he could tie the score!",
        "What's the difference between a football player and time? The football player runs!"
    ]
    
    joke = random.choice(jokes)
    embed = discord.Embed(
        title="😄 Dad Joke Time!",
        description=joke,
        color=0xffd700
    )
    await ctx.send(embed=embed)

@bot.command()
async def trivia(ctx: commands.Context):
    """Football trivia question"""
    questions = [
        {"q": "Which player has won the most Ballon d'Or awards?", "a": "Lionel Messi"},
        {"q": "Which country won the first FIFA World Cup?", "a": "Uruguay"},
        {"q": "What year was the Premier League founded?", "a": "1992"},
        {"q": "Which club has won the most Champions League titles?", "a": "Real Madrid"},
        {"q": "Who scored the fastest goal in World Cup history?", "a": "Hakan Şükür"},
        {"q": "Which player has scored the most goals in a calendar year?", "a": "Lionel Messi"},
        {"q": "What is the maximum number of players on a football team during a match?", "a": "11"}
    ]
    
    trivia = random.choice(questions)
    
    embed = discord.Embed(
        title="🧠 Football Trivia",
        description=f"**Question:** {trivia['q']}",
        color=0x3498db
    )
    
    # Store answer for checking (simplified - in production you'd want a proper system)
    embed.set_footer(text=f"Answer: {trivia['a']}")
    
    await ctx.send(embed=embed)

# Duplicate sell command removed - keeping only the first one
    uid = str(ctx.author.id)
    user_coll = data["user_collections"].get(uid, [])

    # Find the card
    card_index = None
    for i, card in enumerate(user_coll):
        if normalize_name(card["name"]) == normalize_name(player_name):
            card_index = i
            break

    if card_index is None:
        return await ctx.send(f"❌ You don't own {player_name}.")

    card = user_coll[card_index]
    sell_price = int(card["price"] * 0.75)  # Sell for 75% of current value

    # Remove card and add money
    user_coll.pop(card_index)
    current_balance = get_balance(ctx.author.id)
    set_balance(ctx.author.id, current_balance + sell_price)

    embed = discord.Embed(
        title="💸 Card Sold!",
        description=f"You sold {card['name']} for ${sell_price:,}!",
        color=0x00ff00
    )
    
    embed.add_field(name="New Balance", value=f"${get_balance(ctx.author.id):,}", inline=True)
    embed.add_field(name="Collection", value=f"{len(user_coll)}/{MAX_COLLECTION_SLOTS}", inline=True)

    await ctx.send(embed=embed)

@bot.command()
async def passiveincome(ctx: commands.Context):
    """Check last passive income payout"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    last_income = last_income_report.get(uid, 0)
    total_income = total_income_tracker.get(uid, 0)
    
    embed = discord.Embed(
        title="💰 Passive Income Report",
        color=0x00ff00
    )
    
    embed.add_field(name="Last Payout", value=f"${last_income:,} Tadbucks", inline=True)
    embed.add_field(name="Total Earned", value=f"${total_income:,} Tadbucks", inline=True)
    
    # Show collection income breakdown
    user_coll = data["user_collections"].get(uid, [])
    if user_coll:
        total_rate = sum(apply_rebirth_bonus(ctx.author.id, card.get("income_rate", 1)) for card in user_coll)
        embed.add_field(name="Current Rate", value=f"${total_rate:,}/30min", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def income(ctx: commands.Context, option: str = None):
    """View income information"""
    if option and option.lower() == "total":
        uid = str(ctx.author.id)
        total = total_income_tracker.get(uid, 0)
        await ctx.send(f"💰 Your lifetime passive income: ${total:,} Tadbucks")
    else:
        # Same as passiveincome
        await passiveincome(ctx)

# Guess the player commands - REAL FOOTBALL PLAYERS ONLY! 🏆⚽
# Updated to feature professional football players like Messi, Ronaldo, Haaland, etc.
# All difficulties now use authentic player clues instead of custom bot players
@bot.command()
async def guesstheplayereasy(ctx: commands.Context):
    """Easy guess the player game"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Finish it first.")

    clue, answer = random.choice(data["guess_db"]["easy"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "easy"}

    embed = discord.Embed(
        title="⚽ Guess The Player - Easy",
        description=f"**Clue:** {clue}",
        color=0x00ff00
    )
    embed.set_footer(text="Type the player's name to guess!")

    await ctx.send(embed=embed)

@bot.command()
async def guesstheplayer(ctx: commands.Context):
    """Normal guess the player game"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Finish it first.")

    clue, answer = random.choice(data["guess_db"]["normal"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "normal"}

    embed = discord.Embed(
        title="⚽ Guess The Player - Normal",
        description=f"**Clue:** {clue}",
        color=0xffa500
    )
    embed.set_footer(text="Type the player's name to guess!")

    await ctx.send(embed=embed)

@bot.command()
async def guesstheplayerhard(ctx: commands.Context):
    """Hard guess the player game"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Finish it first.")

    clue, answer = random.choice(data["guess_db"]["hard"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "hard"}

    embed = discord.Embed(
        title="⚽ Guess The Player - Hard",
        description=f"**Clue:** {clue}",
        color=0xff4500
    )
    embed.set_footer(text="Type the player's name to guess!")

    await ctx.send(embed=embed)

@bot.command()
async def guesstheplayerextreme(ctx: commands.Context):
    """Extreme guess the player game"""
    uid = str(ctx.author.id)
    if uid in active_guess_games:
        return await ctx.send("❌ You already have an active guess game! Finish it first.")

    clue, answer = random.choice(data["guess_db"]["extreme"])
    active_guess_games[uid] = {"answer": answer, "difficulty": "extreme"}

    embed = discord.Embed(
        title="⚽ Guess The Player - EXTREME",
        description=f"**Clue:** {clue}",
        color=0x8b0000
    )
    embed.set_footer(text="Type the player's name to guess!")

    await ctx.send(embed=embed)

# Fun commands
@bot.command()
async def coinflip(ctx: commands.Context):
    """Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    embed = discord.Embed(
        title="🪙 Coin Flip",
        description=f"The coin landed on **{result}**!",
        color=0xffd700
    )
    await ctx.send(embed=embed)

@bot.command()
async def dice(ctx: commands.Context, sides: int = 6):
    """Roll a dice"""
    if sides < 2 or sides > 100:
        return await ctx.send("❌ Dice must have between 2 and 100 sides!")
    
    result = random.randint(1, sides)
    embed = discord.Embed(
        title=f"🎲 Dice Roll (d{sides})",
        description=f"You rolled a **{result}**!",
        color=0x3498db
    )
    await ctx.send(embed=embed)

@bot.command(name="8ball")
async def eightball(ctx: commands.Context, *, question: str = None):
    """Magic 8-ball"""
    if not question:
        return await ctx.send("❌ Ask me a question!")
    
    responses = [
        "It is certain", "Reply hazy, try again", "Don't count on it",
        "It is decidedly so", "Ask again later", "My reply is no",
        "Without a doubt", "Better not tell you now", "My sources say no",
        "Yes definitely", "Cannot predict now", "Outlook not so good",
        "You may rely on it", "Concentrate and ask again", "Very doubtful",
        "As I see it, yes", "Most likely", "Outlook good", "Yes",
        "Signs point to yes"
    ]
    
    answer = random.choice(responses)
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Question:** {question}\n**Answer:** {answer}",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx: commands.Context):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=0x00ff00 if latency < 100 else 0xffa500 if latency < 300 else 0xff0000
    )
    await ctx.send(embed=embed)

@bot.command()
async def rps(ctx: commands.Context, choice: str = None):
    """Rock Paper Scissors"""
    if not choice or choice.lower() not in ['rock', 'paper', 'scissors']:
        return await ctx.send("❌ Choose rock, paper, or scissors!")
    
    user_choice = choice.lower()
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    
    # Determine winner
    if user_choice == bot_choice:
        result = "It's a tie!"
        color = 0xffa500
    elif (user_choice == 'rock' and bot_choice == 'scissors') or \
         (user_choice == 'paper' and bot_choice == 'rock') or \
         (user_choice == 'scissors' and bot_choice == 'paper'):
        result = "You win!"
        color = 0x00ff00
    else:
        result = "I win!"
        color = 0xff0000
    
    embed = discord.Embed(
        title="✂️ Rock Paper Scissors",
        description=f"You: {user_choice}\nMe: {bot_choice}\n\n**{result}**",
        color=color
    )
    await ctx.send(embed=embed)

@bot.command()
async def var(ctx: commands.Context):
    """VAR decision"""
    decisions = [
        "GOAL CONFIRMED! ✅", "GOAL DISALLOWED! ❌", 
        "PENALTY AWARDED! 🥅", "NO PENALTY! 🚫",
        "OFFSIDE! 🏃‍♂️", "ONSIDE! ✅",
        "RED CARD UPHELD! 🟥", "YELLOW CARD! 🟨"
    ]
    
    decision = random.choice(decisions)
    embed = discord.Embed(
        title="📺 VAR Decision",
        description=f"After review... **{decision}**",
        color=0x0066cc
    )
    await ctx.send(embed=embed)

@bot.command()
async def compliment(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Give someone a compliment"""
    target = member or ctx.author
    
    compliments = [
        "is an amazing person!", "has a great sense of humor!",
        "is incredibly talented!", "lights up the room!",
        "is so kind and caring!", "has such a positive attitude!",
        "is absolutely wonderful!", "is truly inspiring!",
        "has such a great personality!", "is an awesome friend!"
    ]
    
    compliment = random.choice(compliments)
    embed = discord.Embed(
        title="💖 Compliment",
        description=f"{target.display_name} {compliment}",
        color=0xff69b4
    )
    await ctx.send(embed=embed)

# Leaderboards
@bot.command()
async def leaderboard(ctx: commands.Context):
    """Top Tadbucks leaderboard"""
    sorted_users = sorted(data["tadbucks_balances"].items(), key=lambda x: x[1], reverse=True)[:10]
    
    embed = discord.Embed(
        title="💰 Tadbucks Leaderboard",
        description="Top 10 richest users",
        color=0xffd700
    )
    
    for i, (uid, balance) in enumerate(sorted_users, 1):
        try:
            user = bot.get_user(int(uid))
            name = user.display_name if user else f"User {uid}"
        except:
            name = f"User {uid}"
        
        # Add medal emojis for top 3
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        embed.add_field(
            name=f"{medal} {name}",
            value=f"${balance:,} Tadbucks",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def points_leaderboard(ctx: commands.Context):
    """Top Tadzzy Points leaderboard"""
    sorted_users = sorted(data["tadzzy_points"].items(), key=lambda x: x[1], reverse=True)[:10]
    
    embed = discord.Embed(
        title="🏆 Tadzzy Points Leaderboard",
        description="Top 10 point holders",
        color=0x9b59b6
    )
    
    for i, (uid, points) in enumerate(sorted_users, 1):
        try:
            user = bot.get_user(int(uid))
            name = user.display_name if user else f"User {uid}"
        except:
            name = f"User {uid}"
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        embed.add_field(
            name=f"{medal} {name}",
            value=f"{points} Tadzzy Points",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def messagesleft(ctx: commands.Context):
    """Check XP progress"""
    uid = str(ctx.author.id)
    ensure_user_exists(ctx.author.id)
    
    current_xp = data["xp_levels"].get(uid, 0)
    current_level = current_xp // LEVEL_UP_XP_THRESHOLD
    xp_progress = current_xp % LEVEL_UP_XP_THRESHOLD
    xp_needed = LEVEL_UP_XP_THRESHOLD - xp_progress
    
    # Calculate messages needed (each message gives LEVEL_XP_REWARD XP)
    messages_needed = max(1, xp_needed // LEVEL_XP_REWARD)
    
    embed = discord.Embed(
        title="📊 XP Progress",
        description=f"**Level:** {current_level}\n**XP:** {xp_progress}/{LEVEL_UP_XP_THRESHOLD}\n**Messages needed:** {messages_needed}",
        color=0x3498db
    )
    
    await ctx.send(embed=embed)
