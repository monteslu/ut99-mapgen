"""
items.py - UT99 weapon, ammo and powerup class names.

Every name here was taken from the actor list of the stock maps (decompiled
with tools/decompile.py) or from the 469 SDK sources, not from memory: UT99's
class names are inconsistent enough that guessing gets you silent no-ops.
Note the capitalisation oddities - `ut_biorifle`, `ripper`, `minigun2`,
`Miniammo` are genuinely spelled that way.

Counts in DM-Deck16][ for reference: ~13 weapons, ~30 ammo pickups,
12 HealthVial, 4 MedBox, 1 each of ShieldBelt / UDamage / Armor2 / ThighPads.

All 27 names below were verified to spawn via ACTOR ADD. Two of them are
reported back by the editor under a different actor name than the class you
asked for - `Armor2` logs as `Armor` and `minigun2` logs as `minigun`. That is
normal, not a failed spawn.
"""

# ---------------------------------------------------------------- weapons
# NOTE: "enforcer" is the spawn weapon every player already carries. UT99
# does not place it as a map pickup, so it will not appear in a built map -
# that is engine behaviour, not a failed placement.
WEAPONS = {
    "enforcer":     "Enforcer",
    "biorifle":     "ut_biorifle",
    "shockrifle":   "ShockRifle",
    "pulsegun":     "PulseGun",
    "ripper":       "ripper",
    "minigun":      "minigun2",
    "flakcannon":   "UT_FlakCannon",
    "rocket":       "UT_Eightball",
    "sniper":       "SniperRifle",
    "redeemer":     "WarheadLauncher",
}

# The ammo pickup that feeds each weapon.
AMMO = {
    "enforcer":     "BulletBox",
    "biorifle":     "BioAmmo",
    "shockrifle":   "ShockCore",
    "pulsegun":     "PAmmo",
    "ripper":       "BladeHopper",
    "minigun":      "Miniammo",
    "flakcannon":   "FlakAmmo",
    "rocket":       "RocketPack",
    "sniper":       "RifleShell",
    "redeemer":     "WarHeadAmmo",
}

# ------------------------------------------------------------ health/armour
HEALTH_SMALL = "HealthVial"      # +5, stacks over 100
HEALTH_LARGE = "MedBox"          # +20
ARMOR_LARGE = "Armor2"           # body armour
ARMOR_SMALL = "ThighPads"
SHIELD_BELT = "UT_ShieldBelt"    # the big one
POWERUP_DAMAGE = "UDamage"
JUMP_BOOTS = "UT_Jumpboots"

# A sensible spread for a mid-size deathmatch map, in rough order of how
# strong the item is. Pair each weapon with ammo nearby, as Epic does.
STARTER = ["shockrifle", "biorifle", "flakcannon"]
STRONG = ["rocket", "minigun", "pulsegun"]
SNIPE = ["sniper", "ripper"]


def weapon(key):
    return WEAPONS[key]


def ammo(key):
    return AMMO[key]


def all_classes():
    """Every class name this module can emit - used to sanity-check maps."""
    return (set(WEAPONS.values()) | set(AMMO.values()) |
            {HEALTH_SMALL, HEALTH_LARGE, ARMOR_LARGE, ARMOR_SMALL,
             SHIELD_BELT, POWERUP_DAMAGE, JUMP_BOOTS})
