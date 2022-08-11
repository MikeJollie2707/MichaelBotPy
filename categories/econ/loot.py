'''Define the loot tables for the economy system.'''

# A few special keywords that are reserved in the loot tables:
# - "result": Usually in crafting-related stuff, it defines how many items will end up as the result of the craft.
# - "money": The money as a reward.
# - "bonus": Same as "money", just different message.
# - "cost": The money lost.

import copy
import random
import typing as t

RESERVED_KEYS = (
    "result",
    "money",
    "bonus",
    "cost",
)

class RewardRNG:
    '''Define the RNG to randomize.

    Attributes
    ----------
    rate : float
        Define the drop rate of the associated item. Must be between 0 and 1.
    min_amount : int
        Define the minimum amount of this item to drop if it happens to roll. This should be positive.
    max_amount : int
        Define the maximum amount of this item to drop if it happens to roll. This should be positive.
    amount_layout : tuple[int], optional
        Define the rng distribution between `min_amount` and `max_amount`. This should satisfy `len(amount_layout) == (max_amount - min_amount + 1) and sum(amount_layout) == 100`
    '''
    __slots__ = ("rate", "min_amount", "max_amount", "amount_layout")

    def __init__(self, rate: float, min_amount: int, max_amount: int, *, amount_layout: tuple[int] = None):
        if rate < 0 or rate > 1:
            raise ValueError("'rate' must be in [0, 1].")
        if min_amount > max_amount:
            raise ValueError("'min_amount' must be smaller than or equal to 'max_amount'.")
        if amount_layout:
            if len(amount_layout) != (max_amount - min_amount + 1):
                raise ValueError("'amount_layout' must have the same amount of items as (max_amount - min_amount + 1).")
            if sum(amount_layout) != 100:
                print(sum(amount_layout))
                raise ValueError("'amount_layout' must sum up to 100.")

        self.rate = rate
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.amount_layout = amount_layout

    def roll(self) -> int:
        '''Roll the RNG based on the provided information.

        Returns
        -------
        int
            The number after randomizing.
        '''
        
        if self.rate < 1:
            r = random.random()
            if r > self.rate:
                return 0
            
        if self.min_amount == self.max_amount:
            return self.min_amount
        
        if not self.amount_layout:
            return random.choice(range(self.min_amount, self.max_amount + 1))
        
        r = random.random()
        rate = 0
        for index, amount_rate in enumerate(self.amount_layout):
            rate += amount_rate / 100.0
            if r <= rate:
                return min(self.min_amount + index, self.max_amount)
        
        return self.max_amount

# Define the loot generated by equipments in each world.
# The amount of loot is set to an RNG, which will then be rolled when calling `get_activity_loot()`.
# Note that for each equipment in each world, it should generate at least 1 non-zero entry.
__ACTIVITY_LOOT = {
    "overworld": {
        # Pickaxe
        "wood_pickaxe": {
            "stone": RewardRNG(rate = 1, min_amount = 1, max_amount = 2),
        },
        "stone_pickaxe": {
            # - stone: 86.49%
            # - iron: 13.51%
            "stone": RewardRNG(rate = 1, min_amount = 3, max_amount = 5),
            "iron": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 2, amount_layout = (75, 25)),
        },
        "iron_pickaxe": {
            # - stone: 83.83%
            # - iron: 14.50%
            # - diamond: 1.67%
            "stone": RewardRNG(rate = 1, min_amount = 4, max_amount = 7),
            "iron": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 4, amount_layout = (50, 20, 20, 10)),
            "diamond": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 2, amount_layout = (90, 10)),
        },
        "diamond_pickaxe": {
            # - stone: 85.85%
            # - iron: 10.85%
            # - diamond: 1.50%
            # - obsidian: 1.80%
            "stone": RewardRNG(rate = 1, min_amount = 8, max_amount = 11),
            "iron": RewardRNG(rate = 0.6, min_amount = 1, max_amount = 5, amount_layout = (45, 25, 20, 5, 5)),
            "diamond": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 4, amount_layout = (50, 40, 5, 5)),
            "obsidian": RewardRNG(rate = 0.2, min_amount = 1, max_amount = 1),
        },
        "nether_pickaxe": {
            # - stone: 77.41%
            # - iron: 17.48%
            # - diamond: 1.40%
            # - obsidian: 3.71%
            "stone": RewardRNG(rate = 1, min_amount = 9, max_amount = 12),
            "iron": RewardRNG(rate = 0.6, min_amount = 3, max_amount = 5, amount_layout = (35, 35, 30)),
            "diamond": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 4, amount_layout = (40, 40, 10, 10)),
            "obsidian": RewardRNG(rate = 0.2, min_amount = 1, max_amount = 4),
        },

        # Sword
        "stone_sword": {
            # - rotten_flesh: 81.83%
            # - spider_eye: 18.17%
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 3, max_amount = 6),
            "spider_eye": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 3),
        },
        "iron_sword": {
            # - rotten_flesh: 61.23%
            # - spider_eye: 32.65%
            # - gunpowder: 6.12%
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 5, max_amount = 10),
            "spider_eye": RewardRNG(rate = 1, min_amount = 3, max_amount = 5),
            "gunpowder": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 2),
        },
        "diamond_sword": {
            # - rotten_flesh: 51.18%
            # - spider_eye: 36.95%
            # - gunpowder: 11.30%
            # - pearl: 0.57%
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 6, max_amount = 12),
            "spider_eye": RewardRNG(rate = 1, min_amount = 5, max_amount = 8),
            "gunpowder": RewardRNG(rate = 0.75, min_amount = 2, max_amount = 4, amount_layout = (50, 35, 15)),
            "pearl": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 1),
        },
        "nether_sword": {
            # - rotten_flesh: 48.49%
            # - spider_eye: 36.36%
            # - gunpowder: 14.18%
            # - pearl: 0.97%
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 9, max_amount = 11),
            "spider_eye": RewardRNG(rate = 1, min_amount = 6, max_amount = 9),
            "gunpowder": RewardRNG(rate = 0.75, min_amount = 3, max_amount = 6, amount_layout = (40, 40, 10, 10)),
            "pearl": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 3),
        },

        # Axe
        "stone_axe": {
            # - wood: 11.12%
            # - leaf: 69.46%
            # - hibiscus: 5.55%
            # - tulip: 5.56%
            # - rose: 5.55%
            # - bed_pickaxe: 1.65%
            # - lucky_clover: 1.11%
            "wood": RewardRNG(rate = 1, min_amount = 1, max_amount = 3),
            "leaf": RewardRNG(rate = 1, min_amount = 10, max_amount = 15),
            "hibiscus": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 3),
            "tulip": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 3),
            "rose": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 3),
            "bed_pickaxe": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 5),
            "lucky_clover": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 3),
        },
        "iron_axe": {
            # - wood: 7.69%
            # - leaf: 67.29%
            # - hibiscus: 7.70%
            # - tulip: 7.70%
            # - rose: 7.69%
            # - bed_pickaxe: 1.16%
            # - lucky_clover: 0.77%
            "wood": RewardRNG(rate = 1, min_amount = 1, max_amount = 3),
            "leaf": RewardRNG(rate = 1, min_amount = 15, max_amount = 20),
            "hibiscus": RewardRNG(rate = 0.5, min_amount = 3, max_amount = 5),
            "tulip": RewardRNG(rate = 0.5, min_amount = 3, max_amount = 5),
            "rose": RewardRNG(rate = 0.5, min_amount = 3, max_amount = 5),
            "bed_pickaxe": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 5),
            "lucky_clover": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 3),
        },
        "diamond_axe": {
            # - wood: 5.50%
            # - leaf: 61.91%
            # - hibiscus: 10.32%
            # - tulip: 10.30%
            # - rose: 10.32%
            # - bed_pickaxe: 0.83%
            # - lucky_clover: 0.82%
            "wood": RewardRNG(rate = 1, min_amount = 1, max_amount = 3),
            "leaf": RewardRNG(rate = 1, min_amount = 20, max_amount = 25),
            "hibiscus": RewardRNG(rate = 0.5, min_amount = 5, max_amount = 10),
            "tulip": RewardRNG(rate = 0.5, min_amount = 5, max_amount = 10),
            "rose": RewardRNG(rate = 0.5, min_amount = 5, max_amount = 10),
            "bed_pickaxe": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 5),
            "lucky_clover": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 5),
        },
        "nether_axe": {
            # - wood: 5.66%
            # - leaf: 62.29%
            # - hibiscus: 10.19%
            # - tulip: 10.20%
            # - rose: 10.19%
            # - bed_pickaxe: 0.67%
            # - lucky_clover: 0.79%
            "wood": RewardRNG(rate = 1, min_amount = 2, max_amount = 3),
            "leaf": RewardRNG(rate = 1, min_amount = 25, max_amount = 30),
            "hibiscus": RewardRNG(rate = 0.5, min_amount = 8, max_amount = 10),
            "tulip": RewardRNG(rate = 0.5, min_amount = 8, max_amount = 10),
            "rose": RewardRNG(rate = 0.5, min_amount = 8, max_amount = 10),
            "bed_pickaxe": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 5),
            "lucky_clover": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 6),
        }
    },
    "nether": {
        # Pickaxe
        "wood_pickaxe": {
            "redstone": RewardRNG(rate = 1, min_amount = 1, max_amount = 5),
            "gold": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 1)
        },
        "stone_pickaxe": {
            "redstone": RewardRNG(rate = 1, min_amount = 4, max_amount = 7),
            "gold": RewardRNG(rate = 0.3, min_amount = 1, max_amount = 2),
        },
        "iron_pickaxe": {
            "redstone": RewardRNG(rate = 1, min_amount = 10, max_amount = 15),
            "gold": RewardRNG(rate = 0.3, min_amount = 5, max_amount = 9),
        },
        "diamond_pickaxe": {
            "redstone": RewardRNG(rate = 1, min_amount = 15, max_amount = 20),
            "gold": RewardRNG(rate = 0.6, min_amount = 10, max_amount = 15),
            "obsidian": RewardRNG(rate = 0.2, min_amount = 1, max_amount = 1),
            "debris": RewardRNG(rate = 0.05, min_amount = 1, max_amount = 1),
        },
        "nether_pickaxe": {
            "redstone": RewardRNG(rate = 1, min_amount = 30, max_amount = 50),
            "gold": RewardRNG(rate = 0.6, min_amount = 15, max_amount = 20),
            "obsidian": RewardRNG(rate = 0.3, min_amount = 1, max_amount = 2),
            "debris": RewardRNG(rate = 0.05, min_amount = 1, max_amount = 4, amount_layout = (50, 30, 10, 10)),
        },
        "bed_pickaxe": {
            "redstone": RewardRNG(rate = 1, min_amount = 60, max_amount = 100),
            "gold": RewardRNG(rate = 1, min_amount = 15, max_amount = 20),
            "obsidian": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 2),
            "debris": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 4, amount_layout = (30, 20, 30, 20)),
        },

        # Sword
        "stone_sword": {
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 3, max_amount = 6),
            "gold": RewardRNG(rate = 0.2, min_amount = 1, max_amount = 1),
            "magma_cream": RewardRNG(rate = 0.25, min_amount = 3, max_amount = 5),
            "blaze_rod": RewardRNG(rate = 0.01, min_amount = 1, max_amount = 1),
        },
        "iron_sword": {
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 5, max_amount = 10),
            "gold": RewardRNG(rate = 1, min_amount = 1, max_amount = 2, amount_layout = (90, 10)),
            "magma_cream": RewardRNG(rate = 0.5, min_amount = 5, max_amount = 8),
            "gunpowder": RewardRNG(rate = 0.5, min_amount = 1, max_amount = 2),
            "blaze_rod": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 2),
            #"nether_star": RewardRNG(rate = 0.01, min_amount = 1, max_amount = 1),
        },
        "diamond_sword": {
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 6, max_amount = 12),
            "gold": RewardRNG(rate = 1, min_amount = 2, max_amount = 2),
            "magma_cream": RewardRNG(rate = 0.75, min_amount = 7, max_amount = 10),
            "gunpowder": RewardRNG(rate = 0.75, min_amount = 2, max_amount = 4, amount_layout = (50, 35, 15)),
            "blaze_rod": RewardRNG(rate = 0.2, min_amount = 1, max_amount = 2),
            #"nether_star": RewardRNG(rate = 0.05, min_amount = 1, max_amount = 1),
        },
        "nether_sword": {
            "rotten_flesh": RewardRNG(rate = 1, min_amount = 9, max_amount = 11),
            "gold": RewardRNG(rate = 1, min_amount = 2, max_amount = 3),
            "magma_cream": RewardRNG(rate = 0.75, min_amount = 8, max_amount = 10),
            "gunpowder": RewardRNG(rate = 0.75, min_amount = 3, max_amount = 6, amount_layout = (40, 40, 10, 10)),
            "blaze_rod": RewardRNG(rate = 0.25, min_amount = 1, max_amount = 2),
            #"nether_star": RewardRNG(rate = 0.1, min_amount = 1, max_amount = 1),
        },

        # Axe
        "stone_axe": {
            "wood": RewardRNG(rate = 1, min_amount = 5, max_amount = 7),
            "dry_leaf": RewardRNG(rate = 1, min_amount = 100, max_amount = 150),
        },
        "iron_axe": {
            "wood": RewardRNG(rate = 1, min_amount = 10, max_amount = 15),
            "dry_leaf": RewardRNG(rate = 1, min_amount = 150, max_amount = 200),
            "mushroom": RewardRNG(rate = 0.3, min_amount = 3, max_amount = 5),
        },
        "diamond_axe": {
            "wood": RewardRNG(rate = 1, min_amount = 15, max_amount = 20),
            "dry_leaf": RewardRNG(rate = 1, min_amount = 200, max_amount = 250),
            "mushroom": RewardRNG(rate = 0.3, min_amount = 5, max_amount = 7),
        },
        "nether_axe": {
            "wood": RewardRNG(rate = 1, min_amount = 20, max_amount = 25),
            "dry_leaf": RewardRNG(rate = 1, min_amount = 250, max_amount = 300),
            "mushroom": RewardRNG(rate = 0.3, min_amount = 5, max_amount = 7),
        }
    },
}

# Define the crafting recipe for items.
# For each item's crafting recipe, there must be a special key "result" which denote the amount of items as a result of crafting.
__CRAFT_RECIPE = {
    "stick": {
        "wood": 1,
        "result": 2
    },
    "wood_pickaxe": {
        "wood": 3,
        "stick": 2,
        "result": 1
    },
    "stone_pickaxe": {
        "stone": 3,
        "stick": 2,
        "result": 1
    },
    "stone_sword": {
        "stone": 2,
        "stick": 1,
        "result": 1
    },
    "stone_axe": {
        "stone": 3,
        "stick": 2,
        "result": 1
    },
    "iron_pickaxe": {
        "iron": 3,
        "stick": 2,
        "result": 1
    },
    "iron_sword": {
        "iron": 2,
        "stick": 1,
        "result": 1
    },
    "iron_axe": {
        "iron": 3,
        "stick": 1,
        "result": 1
    },
    "diamond_pickaxe": {
        "diamond": 3,
        "stick": 2,
        "result": 1
    },
    "diamond_sword": {
        "diamond": 2,
        "stick": 1,
        "result": 1
    },
    "diamond_axe": {
        "diamond": 3,
        "stick": 2,
        "result": 1
    },
    "nether_ticket": {
        "obsidian": 10,
        "result": 5
    },
    "netherite": {
        "debris": 4,
        "gold": 4,
        "result": 1
    },
    "nether_pickaxe": {
        "netherite": 1,
        "diamond_pickaxe": 1,
        "result": 1
    },
    "nether_sword": {
        "netherite": 1,
        "diamond_sword": 1,
        "result": 1
    },
    "nether_axe": {
        "netherite": 1,
        "diamond_axe": 1,
        "result": 1
    }
}

__BREW_RECIPE = {
    "luck_potion": {
        "lucky_clover": 420,
        "hibiscus": 999,
        "tulip": 999,
        "rose": 999,
        "redstone": 999,
        "gunpowder": 999,
        "blaze_rod": 99,
        "cost": 6969,
        "result": 3
    },
    "fire_potion": {
        "magma_cream": 60,
        "hibiscus": 99,
        "tulip": 99,
        "rose": 99,
        "redstone": 150,
        "gunpowder": 15,
        "spider_eye": 150,
        "blaze_rod": 3,
        "cost": 300,
        "result": 3
    },
    "fortune_potion": {
        "lucky_clover": 60,
        "redstone": 150,
        "gunpowder": 150,
        "gold": 45,
        "blaze_rod": 3,
        "cost": 450,
        "result": 3
    },
    "looting_potion": {
        "rotten_flesh": 360,
        "spider_eye": 120,
        "gunpowder": 120,
        "pearl": 45,
        "redstone": 150,
        "blaze_rod": 3,
        "cost": 450,
        "result": 3
    },
    "nature_potion": {
        "leaf": 900,
        "hibiscus": 120,
        "tulip": 120,
        "rose": 120,
        "redstone": 300,
        "gunpowder": 15,
        "blaze_rod": 3,
        "cost": 450,
        "result": 3
    },
}

__POTION_CHANCE = {
    "luck_potion": 0.50,
    "fire_potion": 0.75,
    "looting_potion": 0.50,
    "fortune_potion": 0.50,
    "nature_potion": 0.50,
    "undying_potion": 1,
}

def get_daily_loot(streak: int) -> dict[str, int]:
    '''Return the daily loot based on the current streak.

    Parameters
    ----------
    streak : int
        The current streak.

    Returns
    -------
    dict[str, int]
        A `dict` denoting the loot table.
    '''

    if streak <= 1:
        return {
            "money": 50,
            "wood": 5
        }
    if streak <= 6:
        return {
            "money": 10,
            "wood": random.randint(10, 15)
        }
    if streak <= 13:
        return {
            "money": 100,
            "bonus": streak,
            "wood": random.randint(10, 15),
            "leaf": random.randint(50, 60),
            "hibiscus": random.randint(10, 12),
            "tulip": random.randint(10, 12),
            "rose": random.randint(10, 12),
        }
    if streak <= 27:
        return {
            "money": 200,
            "bonus": 5 * streak,
            "wood": random.randint(20, 25),
            "leaf": random.randint(100, 110),
            "hibiscus": random.randint(20, 22),
            "tulip": random.randint(20, 22),
            "rose": random.randint(20, 22),
        }
    if streak <= 60:
        return {
            "money": 1000,
            "bonus": 2 * streak,
            "wood": random.randint(50, 55),
            "leaf": random.randint(210, 220),
            "hibiscus": random.randint(50, 52),
            "tulip": random.randint(50, 52),
            "rose": random.randint(50, 52),
            "lucky_clover": random.randint(1, 5),
        }
    return {
        "money": 2000,
        "bonus": 5 * streak,
        "wood": random.randint(190, 210),
        "leaf": random.randint(190, 210),
        "hibiscus": random.randint(190, 210),
        "tulip": random.randint(190, 210),
        "rose": random.randint(190, 210),
        "lucky_clover": random.randint(1, 10),
    }

def get_activity_loot(equipment_id: str, world: str, has_luck: bool = False) -> t.Optional[dict[str, int]]:
    '''Return the loot generated by an equipment in a world.

    Parameters
    ----------
    equipment_id : str
        The equipment's id. The function won't check for valid id.
    world : str
        The world's name. The function won't check for valid world.

    Returns
    -------
    t.Optional[dict[str, int]]
        A `dict` denoting the loot table, or `None` if there's no matching loot table.
    '''
    
    reward: dict[str, int] = {}

    world_loot = __ACTIVITY_LOOT.get(world)
    if not world_loot:
        return None
    
    equipment_loot = world_loot.get(equipment_id)
    if not equipment_loot:
        return None
    
    for item_id, rng in equipment_loot.items():
        reward[item_id] = rng.roll()
        if has_luck and reward[item_id] == 0:
            # Just in case rng.min_amount is also 0.
            reward[item_id] = min(rng.min_amount, 1)

    return reward

def get_craft_recipe(item_id: str) -> t.Optional[dict[str, int]]:
    '''Return the crafting recipe for an item if existed.

    Notes
    -----
    The returning `dict` has a special key `result`, which denote how many items will be crafted out of the recipe.

    Parameters
    ----------
    item_id : str
        The item's id.

    Returns
    -------
    t.Optional[dict[str, int]]
        A `dict` denoting the crafting recipe, or `None` if no crafting recipe is found.
    '''

    return copy.deepcopy(__CRAFT_RECIPE.get(item_id))

def get_brew_recipe(potion_id: str) -> t.Optional[dict[str, int]]:
    '''Return the brewing recipe for a potion if existed.

    Notes
    -----
    The returning `dict` has a special key `result`, which denote how many potions will be brewed out of the recipe.

    Parameters
    ----------
    potion_id : str
        The potion's id.

    Returns
    -------
    t.Optional[dict[str, int]]
        A `dict` denoting the brewing recipe, or `None` if no brewing recipe is found.
    '''

    return copy.deepcopy(__BREW_RECIPE.get(potion_id))

def roll_potion_activate(potion_id: str) -> bool:
    '''Try to roll and see if the potion activated.

    Parameters
    ----------
    potion_id : str
        The potion's id.

    Returns
    -------
    bool
        Whether the potion activated or not.
    '''
    chance = __POTION_CHANCE.get(potion_id, 0)
    if chance == 1:
        return True
    
    return random.random() <= chance
