import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pygame


VIRTUAL_WIDTH = 384
VIRTUAL_HEIGHT = 180
SCALE = 3
WINDOW_SIZE = (VIRTUAL_WIDTH * SCALE, VIRTUAL_HEIGHT * SCALE)
FPS = 60

PLAYER_ANCHOR_X = 112
GRAVITY = 245.0
JUMP_SPEED = -145.0
MAX_SPEED = 222.0
MIN_SPEED = 58.0
INITIAL_SPEED = 104.0
DOUBLE_CAMERA_GAP = VIRTUAL_WIDTH - 96

SKY_TOP = (126, 194, 214)
SKY_LOW = (174, 225, 224)
SNOW = (242, 248, 244)
SNOW_SHADOW = (190, 220, 216)
ICE_BLUE = (100, 167, 192)
MOUNTAIN_DARK = (83, 123, 132)
MOUNTAIN_MID = (119, 166, 166)
PINE_DARK = (26, 87, 76)
PINE_LIGHT = (42, 135, 103)
INK = (21, 33, 36)
MUTED = (69, 91, 94)
GOLD = (246, 199, 73)
CORAL = (224, 84, 77)
WHITE = (255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)
ASSET_DIR = Path(__file__).resolve().parent
BACKGROUNDS = {}
SUN_IMAGES = {}
STARTUP_BACKGROUND = None
MAX_HEALTH = 100
CRASH_DAMAGE = 10
RANDOM_BOX_DISTANCE_INTERVAL = 1000
AVALANCHE_SPEED_MULTIPLIER = 1.12
SEASON_TRANSITION_SECONDS = 1.0
SEASONAL_ENTITY_KINDS = {"rock", "pine", "shard"}
MUSIC_VOLUME = 0.28
DEFAULT_SOUND_VOLUME = 0.55
CRASH_SOUND_VOLUME = 0.60
WIN_SOUND_VOLUME = 0.65
SOUNDS: dict[str, pygame.mixer.Sound] = {}

P1_COLOR = (70, 158, 215)
P2_COLOR = (230, 93, 85)
P1_CONTROLS = {
    "jump": (pygame.K_w,),
    "tuck": (pygame.K_s,),
    "left": (pygame.K_a,),
    "right": (pygame.K_d,),
    "attack": pygame.K_e,
}
P2_CONTROLS = {
    "jump": (pygame.K_UP,),
    "tuck": (pygame.K_DOWN,),
    "left": (pygame.K_LEFT,),
    "right": (pygame.K_RIGHT,),
    "attack": pygame.K_SLASH,
}
SINGLE_CONTROLS = {
    "jump": (pygame.K_SPACE, pygame.K_UP, pygame.K_w),
    "tuck": (pygame.K_DOWN, pygame.K_s),
    "left": (pygame.K_LEFT, pygame.K_a),
    "right": (pygame.K_RIGHT, pygame.K_d),
    "attack": pygame.K_e,
}


@dataclass
class Player:
    label: str = "P1"
    color: tuple[int, int, int] = P1_COLOR
    x: float = 36.0
    y: float = 0.0
    vx: float = INITIAL_SPEED
    vy: float = 0.0
    grounded: bool = True
    tuck: bool = False
    angle: float = 0.0
    spin: float = 0.0
    stun_timer: float = 0.0
    invincible_timer: float = 0.0
    air_time: float = 0.0
    attack_cooldown: float = 0.0
    score: int = 0
    shards: int = 0
    combo: int = 1
    eliminated: bool = False
    health: int = MAX_HEALTH


@dataclass
class Entity:
    kind: str
    x: float
    y: float = 0.0
    collected: bool = False
    used: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple[int, int, int]


@dataclass
class Projectile:
    owner: str
    x: float
    y: float
    vx: float
    life: float = 1.2


@dataclass
class SlopeGame:
    rng: random.Random = field(default_factory=random.Random)
    player: Player = field(default_factory=Player)
    player2: Player | None = None
    entities: list[Entity] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    projectiles: list[Projectile] = field(default_factory=list)
    next_spawn_x: float = 180.0
    avalanche_x: float = -190.0
    camera_x: float = 0.0
    score: int = 0
    shards: int = 0
    combo: int = 1
    best_distance: int = 0
    game_over: bool = False
    paused: bool = False
    show_help: bool = True
    mode: str = "single"
    state: str = "menu"
    menu_choice: int = 0
    pause_choice: int = 0
    result_title: str = ""
    result_subtitle: str = ""
    season: str = "winter"
    season_start_distance: int = 0
    next_box_distance: int = RANDOM_BOX_DISTANCE_INTERVAL
    transition_timer: float = 0.0
    transition_from: str = "winter"
    transition_to: str = "winter"
    message: str = "Choose Single or Double to start."
    message_timer: float = 4.0
    shake_timer: float = 0.0

    def all_players(self) -> list[Player]:
        players = [self.player]
        if self.player2 is not None:
            players.append(self.player2)
        return players

    def active_players(self) -> list[Player]:
        return [player for player in self.all_players() if not player.eliminated]

    def leader(self) -> Player:
        players = self.active_players() or self.all_players()
        return max(players, key=lambda player: player.x)

    def reset(self, mode: str | None = None) -> None:
        if mode is not None:
            self.mode = mode
        self.player = Player(label="P1", color=P1_COLOR, x=48.0, vx=INITIAL_SPEED)
        self.player.y = terrain_y(self.player.x)
        if self.mode == "double":
            self.player2 = Player(label="P2", color=P2_COLOR, x=30.0, vx=INITIAL_SPEED - 2.0)
            self.player2.y = terrain_y(self.player2.x)
        else:
            self.player2 = None
        self.entities = []
        self.particles = []
        self.projectiles = []
        self.next_spawn_x = 180.0
        self.avalanche_x = -240.0
        self.camera_x = 0.0
        self.score = 0
        self.shards = 0
        self.combo = 1
        self.game_over = False
        self.paused = False
        self.show_help = True
        self.pause_choice = 0
        self.result_title = ""
        self.result_subtitle = ""
        self.season = "winter"
        self.season_start_distance = 0
        self.next_box_distance = RANDOM_BOX_DISTANCE_INTERVAL
        self.transition_timer = 0.0
        self.transition_from = "winter"
        self.transition_to = "winter"
        self.state = "playing"
        if self.mode == "double":
            self.message = "P1 WASD+E. P2 arrows+/."
        else:
            self.message = "Space jumps. Down tucks. Keep ahead of the snow wall."
        self.message_timer = 4.0
        self.shake_timer = 0.0


def terrain_y(x: float) -> float:
    """Smooth hand-tuned terrain; lower screen y means higher snow."""
    base = 132.0
    rolling = (
        math.sin(x * 0.020) * 13.0
        + math.sin(x * 0.047 + 1.9) * 6.0
        + math.sin(x * 0.009 + 4.2) * 10.0
    )
    micro = math.sin(x * 0.125) * 1.4
    return base + rolling + micro


def slope_at(x: float) -> float:
    return (terrain_y(x + 3.0) - terrain_y(x - 3.0)) / 6.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pressed_any(keys, key_codes: tuple[int, ...]) -> bool:
    return any(keys[key_code] for key_code in key_codes)


def play_sound(name: str) -> None:
    sound = SOUNDS.get(name)
    if sound is None:
        return
    try:
        sound.play()
    except pygame.error:
        pass


def load_audio() -> dict[str, pygame.mixer.Sound]:
    sounds: dict[str, pygame.mixer.Sound] = {}
    if pygame.mixer.get_init() is None:
        return sounds

    files = {
        "crash": "crash.wav",
        "switch": "switch.wav",
        "star": "star_collection.wav",
        "attack": "attack.wav",
        "win": "win.wav",
        "ramp": "ramp.wav",
    }
    volumes = {
        "crash": CRASH_SOUND_VOLUME,
        "win": WIN_SOUND_VOLUME,
    }
    for name, filename in files.items():
        path = ASSET_DIR / filename
        try:
            sound = pygame.mixer.Sound(str(path))
        except (pygame.error, FileNotFoundError):
            continue
        sound.set_volume(volumes.get(name, DEFAULT_SOUND_VOLUME))
        sounds[name] = sound

    music_path = ASSET_DIR / "Soundroll - Troublemaker.mp3"
    try:
        pygame.mixer.music.load(str(music_path))
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        pygame.mixer.music.play(-1)
    except (pygame.error, FileNotFoundError):
        pass

    return sounds


def make_sprite(pattern: list[str], palette: dict[str, tuple[int, int, int]]) -> pygame.Surface:
    width = max(len(row) for row in pattern)
    height = len(pattern)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill(TRANSPARENT)
    for y, row in enumerate(pattern):
        for x, char in enumerate(row):
            if char != ".":
                surface.set_at((x, y), palette[char])
    return surface


def trim_alpha(surface: pygame.Surface) -> pygame.Surface:
    bounds = surface.get_bounding_rect()
    if bounds.width <= 0 or bounds.height <= 0:
        return surface
    return surface.subsurface(bounds).copy()


def load_scaled_sprite(
    filename: str,
    size: tuple[int, int],
    fallback: pygame.Surface,
) -> pygame.Surface:
    path = ASSET_DIR / filename
    if not path.exists():
        return fallback

    image = pygame.image.load(str(path)).convert_alpha()
    image = trim_alpha(image)
    return pygame.transform.smoothscale(image, size)


def load_scaled_background(filename: str) -> pygame.Surface | None:
    path = ASSET_DIR / filename
    if not path.exists():
        return None

    image = pygame.image.load(str(path)).convert()
    source_ratio = image.get_width() / image.get_height()
    target_ratio = VIRTUAL_WIDTH / VIRTUAL_HEIGHT
    if source_ratio > target_ratio:
        crop_width = round(image.get_height() * target_ratio)
        crop_x = (image.get_width() - crop_width) // 2
        image = image.subsurface((crop_x, 0, crop_width, image.get_height())).copy()
    elif source_ratio < target_ratio:
        crop_height = round(image.get_width() / target_ratio)
        crop_y = (image.get_height() - crop_height) // 2
        image = image.subsurface((0, crop_y, image.get_width(), crop_height)).copy()
    return pygame.transform.smoothscale(image, (VIRTUAL_WIDTH, VIRTUAL_HEIGHT))


def build_sprites() -> dict[str, pygame.Surface]:
    global BACKGROUNDS, SUN_IMAGES, STARTUP_BACKGROUND

    skin = (237, 178, 128)
    goggles = (40, 62, 70)
    jacket = (222, 74, 72)
    jacket_dark = (150, 51, 59)
    pants = (50, 102, 126)
    board = (41, 51, 56)
    scarf = (246, 199, 73)
    metal = (188, 207, 204)

    player = make_sprite(
        [
            ".....................",
            ".........hh..........",
            "........hggg.........",
            "........hhhh.........",
            ".........jjjss.......",
            "........jjjjs........",
            ".......jpppp.........",
            "......jjppppp........",
            ".....jjjpppp.........",
            ".....pppppp..........",
            "....pppppmm..........",
            "...bbbbbbbbbbbb......",
            "..bb............bb...",
            ".bb...............bb.",
            ".....................",
        ],
        {
            "h": skin,
            "g": goggles,
            "j": jacket,
            "p": pants,
            "s": scarf,
            "m": metal,
            "b": board,
        },
    )

    player_tuck = make_sprite(
        [
            "......................",
            "..........hh..........",
            ".........hggg.........",
            ".......jjhhhhss.......",
            ".....jjjjppps.........",
            "....jjjjpppp..........",
            "...ppppppppmm.........",
            "..bbbbbbbbbbbbbbb.....",
            ".bb..............bb...",
            "......................",
        ],
        {
            "h": skin,
            "g": goggles,
            "j": jacket,
            "p": pants,
            "s": scarf,
            "m": metal,
            "b": board,
        },
    )

    rock = make_sprite(
        [
            "....rrr....",
            "...rrrrr...",
            "..rRrrrrr..",
            ".rrrrRRrr..",
            ".rrrRrrrrr.",
            "rrrrrrrrrr.",
            ".rrrrrrrr..",
        ],
        {"r": (93, 101, 96), "R": (141, 153, 145)},
    )

    pine = make_sprite(
        [
            ".....l.....",
            "....lll....",
            "...lllll...",
            "..LLlllLL..",
            "....lll....",
            "...lllll...",
            "..LLlllLL..",
            ".LLLLLLLLL.",
            "....ttt....",
            "....ttt....",
        ],
        {"l": PINE_LIGHT, "L": PINE_DARK, "t": (105, 83, 62)},
    )

    ramp = make_sprite(
        [
            "...........w",
            ".........www",
            ".......wwwww",
            ".....wwwwwww",
            "...wwwwwwwwx",
            ".wwwwwwwwxxx",
            "xxxxxxxxxxx",
        ],
        {"w": (208, 232, 226), "x": (94, 132, 128)},
    )

    shard = make_sprite(
        [
            "...y...",
            "..yYy..",
            ".yYYYy.",
            "..yYy..",
            "...y...",
        ],
        {"y": GOLD, "Y": (255, 239, 146)},
    )

    snowball = make_sprite(
        [
            "...ww....",
            ".wwWWww.",
            "wWWWWWWw",
            "wWWWWWWw",
            ".wwWWww.",
            "...ww...",
        ],
        {"w": (221, 238, 236), "W": WHITE},
    )

    fallback_sun = make_sprite(
        [
            "...yyy...",
            ".yyyyyyy.",
            ".yyYYYyy.",
            "yyYYYYYyy",
            ".yyYYYyy.",
            ".yyyyyyy.",
            "...yyy...",
        ],
        {"y": GOLD, "Y": (255, 244, 188)},
    )

    random_box = make_sprite(
        [
            "..bbbbbb..",
            ".bYYYYYYb.",
            "bYYbbYYbb",
            "bYbYYbYYb",
            "bYYYbbYYb",
            "bYYbbYYYb",
            "bYYYYYYbb",
            "bYYbbYYbb",
            ".bYYYYYYb.",
            "..bbbbbb..",
        ],
        {"b": INK, "Y": GOLD},
    )

    sprites = {
        "player": player,
        "player_tuck": player_tuck,
        "player2": player,
        "player2_tuck": player_tuck,
        "summer_player": player,
        "summer_player_tuck": player_tuck,
        "summer_player2": player,
        "summer_player2_tuck": player_tuck,
        "rock": rock,
        "summer_rock": rock,
        "pine": pine,
        "summer_pine": pine,
        "ramp": ramp,
        "shard": shard,
        "summer_shard": shard,
        "snowball": snowball,
        "random_box": random_box,
    }

    BACKGROUNDS = {
        "winter": load_scaled_background("background.png"),
        "summer": load_scaled_background("summer_background.png"),
    }
    STARTUP_BACKGROUND = load_scaled_background("starup_page.png") or BACKGROUNDS.get("winter")
    player_asset = load_scaled_sprite("player.png", (28, 31), sprites["player"])
    player2_asset = load_scaled_sprite("player2.png", (28, 31), player_asset)
    summer_player_asset = load_scaled_sprite("summer_player1.png", (28, 31), player_asset)
    summer_player2_asset = load_scaled_sprite("summer_player2.png", (28, 31), player2_asset)
    sprites["player"] = player_asset
    sprites["player_tuck"] = pygame.transform.smoothscale(player_asset, (30, 23))
    sprites["player2"] = player2_asset
    sprites["player2_tuck"] = pygame.transform.smoothscale(player2_asset, (30, 23))
    sprites["summer_player"] = summer_player_asset
    sprites["summer_player_tuck"] = pygame.transform.smoothscale(summer_player_asset, (30, 23))
    sprites["summer_player2"] = summer_player2_asset
    sprites["summer_player2_tuck"] = pygame.transform.smoothscale(summer_player2_asset, (30, 23))
    sprites["rock"] = load_scaled_sprite("rock.png", (16, 10), sprites["rock"])
    sprites["summer_rock"] = load_scaled_sprite("summer_rock.png", (16, 10), sprites["rock"])
    sprites["pine"] = load_scaled_sprite("tree.png", (18, 25), sprites["pine"])
    sprites["summer_pine"] = load_scaled_sprite("summer_tree.png", (18, 25), sprites["pine"])
    sprites["shard"] = load_scaled_sprite("star.png", (12, 12), sprites["shard"])
    sprites["summer_shard"] = load_scaled_sprite("summer_star.png", (12, 12), sprites["shard"])
    sprites["random_box"] = load_scaled_sprite("random_box.png", (16, 16), sprites["random_box"])
    sun_image = load_scaled_sprite("sun.png", (34, 34), fallback_sun)
    SUN_IMAGES = {"winter": sun_image, "summer": sun_image}

    return sprites


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: tuple[int, int],
    color: tuple[int, int, int] = INK,
) -> None:
    rendered = font.render(text, True, color)
    surface.blit(rendered, pos)


def draw_centered_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    center: tuple[int, int],
    color: tuple[int, int, int] = INK,
) -> None:
    rendered = font.render(text, True, color)
    surface.blit(rendered, rendered.get_rect(center=center))


def world_to_screen(x: float, y: float, camera_x: float) -> tuple[int, int]:
    return round(x - camera_x), round(y)


def bottom_blit(
    surface: pygame.Surface,
    sprite: pygame.Surface,
    bottom_center: tuple[int, int],
    angle: float = 0.0,
) -> pygame.Rect:
    image = pygame.transform.rotate(sprite, angle) if angle else sprite
    rect = image.get_rect(midbottom=bottom_center)
    surface.blit(image, rect)
    return rect


def season_sprite_key(kind: str, season: str) -> str:
    if season == "summer" and kind in {"player", "player2", "rock", "pine", "shard"}:
        return f"summer_{kind}"
    return kind


def entity_bottom_y(kind: str, x: float) -> float:
    base_y = terrain_y(x)
    if kind == "rock":
        return base_y + 3.0
    if kind == "pine":
        return base_y + 1.0
    return base_y


def entity_rect(entity: Entity, sprites: dict[str, pygame.Surface]) -> pygame.Rect:
    sprite = sprites[entity.kind]
    if entity.kind == "shard":
        return pygame.Rect(round(entity.x - 6), round(entity.y - 6), 12, 12)
    if entity.kind == "random_box":
        return pygame.Rect(round(entity.x - 8), round(entity.y - 8), 16, 16)
    bottom_y = entity_bottom_y(entity.kind, entity.x)
    rect = sprite.get_rect(midbottom=(round(entity.x), round(bottom_y)))
    if entity.kind == "rock":
        return rect.inflate(-5, -4)
    if entity.kind == "pine":
        return rect.inflate(-12, -5)
    if entity.kind == "ramp":
        return rect.inflate(-1, -1)
    return rect


def player_rect(player: Player) -> pygame.Rect:
    if player.tuck and player.grounded:
        return pygame.Rect(round(player.x - 13), round(player.y - 16), 26, 14)
    return pygame.Rect(round(player.x - 10), round(player.y - 28), 20, 26)


def spawn_entities(game: SlopeGame) -> None:
    horizon = game.camera_x + VIRTUAL_WIDTH + 260
    while game.next_spawn_x < horizon:
        roll = game.rng.random()
        x = game.next_spawn_x + game.rng.uniform(-12.0, 12.0)
        ground = terrain_y(x)

        if roll < 0.34:
            arc = game.rng.choice((0.0, 0.7, 1.4))
            for index in range(game.rng.randint(4, 7)):
                shard_x = x + index * 11.0
                shard_y = terrain_y(shard_x) - 26.0 - math.sin(index * 0.9 + arc) * 10.0
                game.entities.append(Entity("shard", shard_x, shard_y))
            game.next_spawn_x += game.rng.uniform(90.0, 145.0)
        elif roll < 0.52:
            game.entities.append(Entity("rock", x, ground))
            game.next_spawn_x += game.rng.uniform(62.0, 108.0)
        elif roll < 0.68:
            game.entities.append(Entity("pine", x, ground))
            game.next_spawn_x += game.rng.uniform(74.0, 118.0)
        elif roll < 0.83:
            game.entities.append(Entity("ramp", x, ground))
            game.next_spawn_x += game.rng.uniform(96.0, 150.0)
        else:
            game.next_spawn_x += game.rng.uniform(45.0, 80.0)


def has_random_box(game: SlopeGame) -> bool:
    return any(entity.kind == "random_box" and not entity.collected for entity in game.entities)


def current_distance(game: SlopeGame) -> int:
    return int(game.leader().x / 8.0)


def spawn_random_box_if_ready(game: SlopeGame) -> None:
    distance = current_distance(game)
    if distance < game.next_box_distance or has_random_box(game):
        return

    box_x = game.camera_x + VIRTUAL_WIDTH + game.rng.uniform(95.0, 155.0)
    box_y = terrain_y(box_x) - 24.0
    game.entities.append(Entity("random_box", box_x, box_y))
    game.next_box_distance = distance + RANDOM_BOX_DISTANCE_INTERVAL
    game.message = "Mystery box ahead!"
    game.message_timer = 1.2


def switch_season(game: SlopeGame) -> None:
    old_season = game.season
    new_season = "summer" if old_season == "winter" else "winter"
    game.season = new_season
    distance = current_distance(game)
    game.season_start_distance = distance
    game.next_box_distance = distance + RANDOM_BOX_DISTANCE_INTERVAL
    game.transition_from = old_season
    game.transition_to = new_season
    game.transition_timer = SEASON_TRANSITION_SECONDS

    clear_left = game.camera_x - 60.0
    clear_right = game.camera_x + VIRTUAL_WIDTH + 100.0
    game.entities = [
        entity
        for entity in game.entities
        if not (
            entity.kind == "random_box"
            or (entity.kind in SEASONAL_ENTITY_KINDS and clear_left <= entity.x <= clear_right)
        )
    ]

    game.message = "Summer Mode!" if new_season == "summer" else "Winter Mode!"
    game.message_timer = 1.4
    game.shake_timer = 0.18
    add_snow_puff(game, game.leader().x, game.leader().y - 8.0, 20, 0.9)
    play_sound("switch")


def add_snow_puff(game: SlopeGame, x: float, y: float, amount: int, strength: float = 1.0) -> None:
    for _ in range(amount):
        game.particles.append(
            Particle(
                x=x + game.rng.uniform(-3.0, 3.0),
                y=y + game.rng.uniform(-2.0, 2.0),
                vx=game.rng.uniform(-42.0, 14.0) * strength,
                vy=game.rng.uniform(-28.0, 4.0) * strength,
                life=game.rng.uniform(0.35, 0.75),
                color=game.rng.choice((WHITE, SNOW, SNOW_SHADOW)),
            )
        )


def add_shard_burst(game: SlopeGame, x: float, y: float) -> None:
    for _ in range(8):
        game.particles.append(
            Particle(
                x=x,
                y=y,
                vx=game.rng.uniform(-36.0, 36.0),
                vy=game.rng.uniform(-42.0, -12.0),
                life=game.rng.uniform(0.25, 0.55),
                color=game.rng.choice((GOLD, WHITE, (255, 239, 146))),
            )
        )


def set_result(game: SlopeGame, title: str, subtitle: str) -> None:
    game.game_over = True
    game.paused = False
    game.result_title = title
    game.result_subtitle = subtitle
    game.message = subtitle
    game.message_timer = 99.0
    game.shake_timer = 0.5


def finish_double_match(game: SlopeGame, loser: Player | None, reason: str) -> None:
    players = game.all_players()
    if loser is None:
        title = "Game Over"
        subtitle = "Both riders fell. Press any key for menu."
    else:
        loser.eliminated = True
        winner = next((player for player in players if player is not loser), None)
        if winner is None or winner.eliminated:
            title = "Game Over"
            subtitle = "Both riders fell. Press any key for menu."
        else:
            title = f"{winner.label} Wins"
            subtitle = f"{loser.label} {reason}. Press any key for menu."

    for player in players:
        player.vx = 0.0
        player.vy = 0.0
        player.stun_timer = 0.0
        player.invincible_timer = 0.0
    game.projectiles = []
    set_result(game, title, subtitle)
    play_sound("win")


def damage_player(game: SlopeGame, player: Player, amount: int = CRASH_DAMAGE) -> None:
    if game.mode != "double" or player.eliminated or game.game_over:
        return

    player.health = clamp(player.health - amount, 0, MAX_HEALTH)
    if player.health <= 0:
        finish_double_match(game, player, "ran out of health")


def crash(game: SlopeGame, reason: str, player: Player | None = None) -> None:
    if player is None:
        player = game.player
    if player.invincible_timer > 0.0 or player.eliminated:
        return

    player.vx = max(MIN_SPEED + 8.0, player.vx * 0.60)
    player.vy = -54.0
    player.grounded = False
    player.stun_timer = 0.58
    player.invincible_timer = 1.05
    player.spin = game.rng.choice((-180.0, 180.0))
    player.combo = 1
    game.combo = game.player.combo
    prefix = f"{player.label}: " if game.mode == "double" else ""
    game.message = f"{prefix}{reason}"
    game.message_timer = 1.6
    game.shake_timer = 0.24
    add_snow_puff(game, player.x, player.y - 2.0, 18, 1.4)
    play_sound("crash")
    damage_player(game, player)


def handle_collectible(game: SlopeGame, entity: Entity, player: Player | None = None) -> None:
    if player is None:
        player = game.player
    entity.collected = True
    player.shards += 1
    if game.mode == "double":
        player.health = min(MAX_HEALTH, player.health + 1)
    player.score += 50 * player.combo
    player.combo = min(8, player.combo + 1)
    player.vx = min(MAX_SPEED, player.vx + 2.4)
    game.score = game.player.score
    game.shards = game.player.shards
    game.combo = game.player.combo
    prefix = f"{player.label} " if game.mode == "double" else ""
    game.message = f"{prefix}star combo x{player.combo}"
    game.message_timer = 0.8
    add_shard_burst(game, entity.x, entity.y)
    play_sound("star")


def update_player(
    game: SlopeGame,
    player: Player,
    controls: dict[str, tuple[int, ...] | int],
    dt: float,
) -> None:
    if player.eliminated:
        return

    keys = pygame.key.get_pressed()
    jump_pressed = pressed_any(keys, controls["jump"])
    player.tuck = pressed_any(keys, controls["tuck"])

    player.stun_timer = max(0.0, player.stun_timer - dt)
    player.invincible_timer = max(0.0, player.invincible_timer - dt)
    player.attack_cooldown = max(0.0, player.attack_cooldown - dt)

    ground_y = terrain_y(player.x)
    slope = slope_at(player.x)
    target_angle = math.degrees(math.atan2(slope, 1.0))

    if player.grounded:
        player.y = ground_y
        player.vy = 0.0
        player.spin = 0.0
        acceleration = slope * 126.0 - 2.0
        if player.tuck and player.stun_timer <= 0.0:
            acceleration += 42.0
        if player.stun_timer > 0.0:
            acceleration -= 22.0
        player.vx = clamp(player.vx + acceleration * dt, MIN_SPEED, MAX_SPEED)
        cruise = 96.0 + min(42.0, player.x / 1000.0)
        if player.vx < cruise and player.stun_timer <= 0.0:
            player.vx = min(cruise, player.vx + 28.0 * dt)
        player.angle += (target_angle - player.angle) * min(1.0, dt * 12.0)
        player.air_time = 0.0

        if jump_pressed and player.stun_timer <= 0.0:
            player.grounded = False
            player.vy = JUMP_SPEED - min(24.0, max(0.0, slope * 34.0))
            player.air_time = 0.01
            player.angle = target_angle
            add_snow_puff(game, player.x - 5.0, player.y - 1.0, 8, 0.8)
    else:
        player.air_time += dt
        player.vy += GRAVITY * dt
        player.y += player.vy * dt
        player.vx = clamp(player.vx - 1.0 * dt, MIN_SPEED, MAX_SPEED)
        rotation_input = 0.0
        if pressed_any(keys, controls["left"]):
            rotation_input += 150.0
        if pressed_any(keys, controls["right"]):
            rotation_input -= 150.0
        if player.tuck:
            rotation_input -= 55.0
        player.spin += rotation_input * dt
        player.angle += player.spin * dt

        next_ground = terrain_y(player.x)
        if player.y >= next_ground:
            impact = abs(player.vy)
            terrain_angle = math.degrees(math.atan2(slope_at(player.x), 1.0))
            landing_mismatch = abs((player.angle - terrain_angle + 180.0) % 360.0 - 180.0)
            player.y = next_ground
            player.grounded = True
            player.vy = 0.0
            player.angle = terrain_angle
            if impact > 205.0 or landing_mismatch > 82.0:
                crash(game, "Rough landing.", player)
            elif player.air_time > 0.55:
                bonus = min(300, int(player.air_time * 120.0)) * player.combo
                player.score += bonus
                game.score = game.player.score
                prefix = f"{player.label} " if game.mode == "double" else ""
                game.message = f"{prefix}clean air +{bonus}"
                game.message_timer = 0.8
                add_snow_puff(game, player.x, player.y, 12, 0.9)

    player.x += player.vx * dt


def update_entities(game: SlopeGame, sprites: dict[str, pygame.Surface]) -> None:
    for entity in game.entities:
        if entity.collected:
            continue

        hitbox = entity_rect(entity, sprites)
        for player in game.active_players():
            player_hitbox = player_rect(player)
            if entity.kind == "random_box":
                if player_hitbox.colliderect(hitbox):
                    entity.collected = True
                    switch_season(game)
                    return
            elif entity.kind == "shard":
                if player_hitbox.colliderect(hitbox):
                    handle_collectible(game, entity, player)
                    break
            elif entity.kind == "ramp":
                if not entity.used and player.grounded and player_hitbox.colliderect(hitbox):
                    entity.used = True
                    player.grounded = False
                    player.vy = -162.0
                    player.vx = min(MAX_SPEED, player.vx + 30.0)
                    player.spin = -52.0 if player.tuck else -18.0
                    player.score += 120 * player.combo
                    game.score = game.player.score
                    prefix = f"{player.label} " if game.mode == "double" else ""
                    game.message = f"{prefix}ramp launch"
                    game.message_timer = 0.8
                    add_snow_puff(game, player.x, player.y, 14, 1.1)
                    play_sound("ramp")
                    break
            elif player_hitbox.colliderect(hitbox):
                if entity.kind == "rock":
                    crash(game, "Rock hit.", player)
                elif entity.kind == "pine":
                    crash(game, "Tree wipeout.", player)

    cutoff = game.camera_x - 80.0
    game.entities = [entity for entity in game.entities if entity.x > cutoff and not entity.collected]


def fire_projectile(game: SlopeGame, player: Player) -> None:
    if game.mode != "double" or game.game_over or game.paused or game.state != "playing":
        return
    if player.attack_cooldown > 0.0 or player.stun_timer > 0.0 or player.eliminated:
        return

    player.attack_cooldown = 0.72
    shot_speed = max(210.0, player.vx + 128.0)
    game.projectiles.append(
        Projectile(
            owner=player.label,
            x=player.x + 12.0,
            y=player.y - 22.0,
            vx=shot_speed,
        )
    )
    game.message = f"{player.label} star shot"
    game.message_timer = 0.55
    play_sound("attack")


def update_projectiles(game: SlopeGame, dt: float) -> None:
    for projectile in game.projectiles:
        projectile.life -= dt
        projectile.x += projectile.vx * dt
        projectile.y += math.sin((projectile.life + projectile.x) * 0.08) * 0.25
        shot_rect = pygame.Rect(round(projectile.x - 5), round(projectile.y - 5), 10, 10)

        for target in game.active_players():
            if target.label == projectile.owner:
                continue
            if shot_rect.colliderect(player_rect(target)):
                projectile.life = 0.0
                crash(game, "hit by a star shot.", target)
                shooter = game.player if projectile.owner == "P1" else game.player2
                if shooter is not None:
                    shooter.score += 160
                break

    cutoff = game.camera_x - 40.0
    game.projectiles = [
        projectile
        for projectile in game.projectiles
        if projectile.life > 0.0 and cutoff <= projectile.x <= game.camera_x + VIRTUAL_WIDTH + 80.0
    ]


def eliminate_player(game: SlopeGame, player: Player) -> None:
    if player.eliminated:
        return

    add_snow_puff(game, player.x, player.y - 4.0, 24, 1.5)
    if game.mode == "double":
        finish_double_match(game, player, "was caught")
        return

    leader = game.leader()
    game.best_distance = max(game.best_distance, int(leader.x / 8.0))
    set_result(game, "Snowed In", "The snow wall caught you. Press R to run again.")


def keep_double_players_in_view(game: SlopeGame) -> None:
    if game.mode != "double":
        return

    players = game.active_players()
    if len(players) < 2:
        return

    leader = max(players, key=lambda player: player.x)
    lagger = min(players, key=lambda player: player.x)
    if leader.x - lagger.x <= DOUBLE_CAMERA_GAP:
        return

    lagger.x = leader.x - DOUBLE_CAMERA_GAP
    if lagger.grounded:
        lagger.y = terrain_y(lagger.x)
    lagger.vx = max(lagger.vx, leader.vx * 0.86, MIN_SPEED + 18.0)
    lagger.invincible_timer = max(lagger.invincible_timer, 0.45)
    game.message = f"{lagger.label} camera catch-up"
    game.message_timer = 0.9


def update_camera(game: SlopeGame) -> None:
    players = game.active_players()
    if game.mode == "double" and players:
        leftmost = min(player.x for player in players)
        rightmost = max(player.x for player in players)
        desired = (leftmost + rightmost) * 0.5 - VIRTUAL_WIDTH * 0.5
        desired = max(desired, rightmost - (VIRTUAL_WIDTH - 58.0))
        desired = min(desired, leftmost - 30.0)
        game.camera_x = max(0.0, desired)
    else:
        game.camera_x = max(0.0, game.player.x - PLAYER_ANCHOR_X)


def update_particles(game: SlopeGame, dt: float) -> None:
    for particle in game.particles:
        particle.life -= dt
        particle.x += particle.vx * dt
        particle.y += particle.vy * dt
        particle.vy += 95.0 * dt
    game.particles = [particle for particle in game.particles if particle.life > 0.0]


def update_game(game: SlopeGame, sprites: dict[str, pygame.Surface], dt: float) -> None:
    if game.state != "playing":
        return

    if game.paused:
        return

    if game.game_over:
        update_particles(game, dt)
        update_projectiles(game, dt)
        game.shake_timer = max(0.0, game.shake_timer - dt)
        return

    game.transition_timer = max(0.0, game.transition_timer - dt)
    game.message_timer = max(0.0, game.message_timer - dt)
    game.shake_timer = max(0.0, game.shake_timer - dt)
    if game.mode == "double":
        update_player(game, game.player, P1_CONTROLS, dt)
        if game.player2 is not None:
            update_player(game, game.player2, P2_CONTROLS, dt)
    else:
        update_player(game, game.player, SINGLE_CONTROLS, dt)

    keep_double_players_in_view(game)
    update_camera(game)
    players = game.active_players()
    spawn_entities(game)
    spawn_random_box_if_ready(game)
    update_entities(game, sprites)
    update_projectiles(game, dt)
    update_particles(game, dt)

    for player in players:
        if player.grounded and player.vx > 92.0:
            if game.rng.random() < 0.65:
                add_snow_puff(game, player.x - 10.0, player.y, 1, 0.45)

    for player in players:
        distance_score = int(player.x * 0.6)
        player.score = max(player.score, distance_score + player.shards * 75)
    game.score = game.player.score
    game.shards = game.player.shards
    game.combo = game.player.combo

    leader = game.leader()
    avalanche_speed = 61.0 + min(48.0, leader.x / 1500.0)
    if any(player.stun_timer > 0.0 for player in players):
        avalanche_speed += 10.0
    avalanche_speed *= AVALANCHE_SPEED_MULTIPLIER
    game.avalanche_x += avalanche_speed * dt

    caught = [player for player in players if game.avalanche_x > player.x - 15.0]
    if game.mode == "double" and len(caught) >= 2:
        for player in caught:
            add_snow_puff(game, player.x, player.y - 4.0, 18, 1.4)
            player.eliminated = True
        finish_double_match(game, None, "were caught")
    else:
        for player in caught:
            eliminate_player(game, player)


def draw_sky(surface: pygame.Surface, camera_x: float, season: str = "winter") -> None:
    background = BACKGROUNDS.get(season)
    if background is not None:
        surface.blit(background, (0, 0))
        cool_wash = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.SRCALPHA)
        if season == "summer":
            cool_wash.fill((255, 229, 143, 14))
        else:
            cool_wash.fill((149, 202, 218, 24))
        surface.blit(cool_wash, (0, 0))
    else:
        surface.fill(SKY_TOP)
        for y in range(VIRTUAL_HEIGHT):
            mix = y / VIRTUAL_HEIGHT
            color = (
                round(SKY_TOP[0] * (1 - mix) + SKY_LOW[0] * mix),
                round(SKY_TOP[1] * (1 - mix) + SKY_LOW[1] * mix),
                round(SKY_TOP[2] * (1 - mix) + SKY_LOW[2] * mix),
            )
            pygame.draw.line(surface, color, (0, y), (VIRTUAL_WIDTH, y))

        far_shift = int(camera_x * 0.09) % 240
        for start_x in range(-far_shift - 80, VIRTUAL_WIDTH + 180, 120):
            points = [
                (start_x, 119),
                (start_x + 42, 53),
                (start_x + 86, 119),
            ]
            pygame.draw.polygon(surface, MOUNTAIN_DARK, points)
            pygame.draw.polygon(
                surface,
                MOUNTAIN_MID,
                [(start_x + 42, 53), (start_x + 57, 119), (start_x + 86, 119)],
            )
            pygame.draw.polygon(
                surface,
                SNOW,
                [(start_x + 42, 53), (start_x + 31, 72), (start_x + 52, 73)],
            )

    sun_x = 250 - int(camera_x * 0.025) % 360
    sun_image = SUN_IMAGES.get(season)
    if sun_image is not None:
        surface.blit(sun_image, sun_image.get_rect(center=(sun_x + 7, 28)))
    else:
        pygame.draw.rect(surface, (255, 232, 146), (sun_x, 19, 14, 14))
        pygame.draw.rect(surface, (255, 244, 188), (sun_x + 3, 22, 8, 8))


def draw_terrain(surface: pygame.Surface, camera_x: float, season: str = "winter") -> None:
    if season == "summer":
        ground_color = (202, 231, 128)
        crest_color = (236, 249, 176)
        shadow_color = (126, 190, 93)
        detail_color = (151, 207, 109)
    else:
        ground_color = SNOW
        crest_color = WHITE
        shadow_color = SNOW_SHADOW
        detail_color = (218, 235, 231)

    top_points: list[tuple[int, int]] = []
    for screen_x in range(-4, VIRTUAL_WIDTH + 8, 4):
        world_x = camera_x + screen_x
        top_points.append((screen_x, round(terrain_y(world_x))))

    snow_polygon = [(-4, VIRTUAL_HEIGHT + 8), *top_points, (VIRTUAL_WIDTH + 8, VIRTUAL_HEIGHT + 8)]
    pygame.draw.polygon(surface, ground_color, snow_polygon)
    pygame.draw.lines(surface, crest_color, False, top_points, 2)

    shadow_points = [(x, y + 4) for x, y in top_points]
    pygame.draw.lines(surface, shadow_color, False, shadow_points, 1)

    for screen_x in range(-20, VIRTUAL_WIDTH + 30, 28):
        world_x = camera_x + screen_x
        y = terrain_y(world_x) + 11 + int(math.sin(world_x * 0.03) * 4)
        pygame.draw.line(surface, detail_color, (screen_x, y), (screen_x + 10, y - 2), 1)


def draw_avalanche(
    surface: pygame.Surface,
    game: SlopeGame,
    sprites: dict[str, pygame.Surface],
) -> None:
    screen_x = round(game.avalanche_x - game.camera_x)
    if screen_x > VIRTUAL_WIDTH + 20:
        return

    wall_right = screen_x + 35
    if game.season == "summer":
        pygame.draw.rect(surface, (128, 96, 65), (screen_x - 38, 0, 76, VIRTUAL_HEIGHT))
        pygame.draw.rect(surface, (82, 61, 48), (wall_right - 8, 0, 9, VIRTUAL_HEIGHT))
        pygame.draw.rect(surface, (166, 130, 85), (screen_x - 38, 0, 12, VIRTUAL_HEIGHT))
        for y in range(-8, VIRTUAL_HEIGHT + 16, 18):
            wave = int(math.sin((y + game.avalanche_x) * 0.12) * 8)
            pygame.draw.line(
                surface,
                (91, 69, 51),
                (wall_right - 32 + wave, y),
                (wall_right - 5 + wave // 2, y + 10),
                3,
            )
        for y in range(7, VIRTUAL_HEIGHT, 22):
            offset = int(math.sin((y + game.avalanche_x) * 0.21) * 6)
            pygame.draw.rect(surface, (73, 76, 68), (wall_right - 25 + offset, y, 8, 6))
            pygame.draw.rect(surface, (188, 145, 89), (wall_right - 17 - offset, y + 8, 5, 4))
        return

    pygame.draw.rect(surface, (217, 236, 236), (screen_x - 36, 0, 72, VIRTUAL_HEIGHT))
    pygame.draw.rect(surface, (190, 220, 224), (wall_right - 6, 0, 6, VIRTUAL_HEIGHT))
    for y in range(4, VIRTUAL_HEIGHT, 16):
        offset = int(math.sin((y + game.avalanche_x) * 0.2) * 5)
        surface.blit(sprites["snowball"], (wall_right - 24 + offset, y))
    for y in range(0, VIRTUAL_HEIGHT, 9):
        pygame.draw.line(surface, WHITE, (wall_right - 9, y), (wall_right + 2, y + 4), 1)


def draw_entities(
    surface: pygame.Surface,
    game: SlopeGame,
    sprites: dict[str, pygame.Surface],
    season: str,
) -> None:
    for entity in game.entities:
        if entity.collected:
            continue
        if entity.x < game.camera_x - 40 or entity.x > game.camera_x + VIRTUAL_WIDTH + 40:
            continue

        sprite = sprites[season_sprite_key(entity.kind, season)]
        if entity.kind in ("shard", "random_box"):
            bob = math.sin(pygame.time.get_ticks() * 0.008 + entity.x) * 2.0
            screen_pos = world_to_screen(entity.x, entity.y + bob, game.camera_x)
            rect = sprite.get_rect(center=screen_pos)
            surface.blit(sprite, rect)
        else:
            screen_pos = world_to_screen(entity.x, entity_bottom_y(entity.kind, entity.x), game.camera_x)
            bottom_blit(surface, sprite, screen_pos)


def draw_projectiles(
    surface: pygame.Surface,
    game: SlopeGame,
    sprites: dict[str, pygame.Surface],
    season: str,
) -> None:
    sprite = sprites[season_sprite_key("shard", season)]
    for projectile in game.projectiles:
        x, y = world_to_screen(projectile.x, projectile.y, game.camera_x)
        if -12 <= x <= VIRTUAL_WIDTH + 12 and -12 <= y <= VIRTUAL_HEIGHT + 12:
            rect = sprite.get_rect(center=(x, y))
            surface.blit(sprite, rect)
            color = P1_COLOR if projectile.owner == "P1" else P2_COLOR
            pygame.draw.rect(surface, color, rect.inflate(-5, -5), 1)


def draw_player(
    surface: pygame.Surface,
    game: SlopeGame,
    sprites: dict[str, pygame.Surface],
    season: str,
    player: Player | None = None,
) -> None:
    if player is None:
        player = game.player
    if player.eliminated:
        return
    sprite_key = "player2" if player.label == "P2" else "player"
    sprite_key = season_sprite_key(sprite_key, season)
    if player.tuck and player.grounded:
        sprite_key += "_tuck"
    sprite = sprites[sprite_key]
    screen_pos = world_to_screen(player.x, player.y, game.camera_x)
    flicker = player.invincible_timer > 0.0 and int(player.invincible_timer * 18) % 2 == 0
    if not flicker:
        if game.mode == "double":
            pygame.draw.rect(surface, player.color, (screen_pos[0] - 9, screen_pos[1] - 36, 18, 3))
            pygame.draw.rect(surface, INK, (screen_pos[0] - 9, screen_pos[1] - 36, 18, 3), 1)
        bottom_blit(surface, sprite, screen_pos, -player.angle)


def draw_particles(surface: pygame.Surface, game: SlopeGame) -> None:
    for particle in game.particles:
        x, y = world_to_screen(particle.x, particle.y, game.camera_x)
        if -4 <= x <= VIRTUAL_WIDTH + 4 and -4 <= y <= VIRTUAL_HEIGHT + 4:
            pygame.draw.rect(surface, particle.color, (x, y, 2, 2))


def draw_health_bar(
    surface: pygame.Surface,
    player: Player,
    font: pygame.font.Font,
    pos: tuple[int, int],
    width: int = 94,
) -> None:
    x, y = pos
    fill = round(clamp(player.health / MAX_HEALTH, 0.0, 1.0) * width)
    pygame.draw.rect(surface, INK, (x, y, width + 2, 7), 1)
    pygame.draw.rect(surface, CORAL, (x + 1, y + 1, width, 5))
    pygame.draw.rect(surface, player.color, (x + 1, y + 1, fill, 5))
    draw_text(surface, font, f"HP {player.health}", (x + width + 6, y), INK)


def draw_hud(surface: pygame.Surface, game: SlopeGame, fonts: dict[str, pygame.font.Font]) -> None:
    if game.mode == "double" and game.player2 is not None:
        panels = [(game.player, 4), (game.player2, VIRTUAL_WIDTH - 157)]
        for player, x in panels:
            pygame.draw.rect(surface, (231, 242, 238), (x, 4, 153, 39))
            pygame.draw.rect(surface, player.color, (x, 4, 153, 3))
            pygame.draw.rect(surface, INK, (x, 4, 153, 39), 1)
            status = "OUT" if player.eliminated else f"{int(player.x / 8)}m"
            draw_text(surface, fonts["tiny"], f"{player.label} SCORE {player.score}", (x + 5, 9), INK)
            draw_text(surface, fonts["tiny"], f"{status}  STARS {player.shards}", (x + 5, 20), MUTED)
            draw_health_bar(surface, player, fonts["tiny"], (x + 5, 31))
    else:
        pygame.draw.rect(surface, (231, 242, 238), (4, 4, 142, 25))
        pygame.draw.rect(surface, INK, (4, 4, 142, 25), 1)
        draw_text(surface, fonts["tiny"], f"SCORE {game.score}", (9, 8), INK)
        draw_text(surface, fonts["tiny"], f"DIST {int(game.player.x / 8)}m", (9, 18), MUTED)
        draw_text(surface, fonts["tiny"], f"STARS {game.shards}", (86, 18), MUTED)

    leader = game.leader()
    gap = max(0.0, leader.x - game.avalanche_x)
    bar_width = 62
    fill = round(clamp(gap / 180.0, 0.0, 1.0) * bar_width)
    bar_x = VIRTUAL_WIDTH - 72 if game.mode != "double" else (VIRTUAL_WIDTH - bar_width) // 2
    bar_y = 8 if game.mode != "double" else 48
    pygame.draw.rect(surface, INK, (bar_x, bar_y, bar_width + 2, 8), 1)
    pygame.draw.rect(surface, CORAL, (bar_x + 1, bar_y + 1, bar_width - fill, 6))
    pygame.draw.rect(surface, ICE_BLUE, (bar_x + 1 + bar_width - fill, bar_y + 1, fill, 6))
    draw_text(surface, fonts["tiny"], "SNOW WALL", (bar_x + 2, bar_y + 10), INK)

    if game.message_timer > 0.0:
        text = game.message
        rendered = fonts["tiny"].render(text, False, INK)
        width = min(rendered.get_width() + 10, VIRTUAL_WIDTH - 18)
        message_rect = pygame.Rect(9, 151, width, 16)
        pygame.draw.rect(surface, (249, 249, 236), message_rect)
        pygame.draw.rect(surface, INK, message_rect, 1)
        surface.blit(rendered, (message_rect.x + 5, message_rect.y + 5))

    if game.paused:
        draw_pause_menu(surface, game, fonts)
    elif game.game_over:
        title = game.result_title or "Snowed In"
        subtitle = game.result_subtitle
        if not subtitle:
            if game.mode == "double" and game.player2 is not None:
                subtitle = f"P1 {game.player.score}  P2 {game.player2.score}  Press any key"
            else:
                subtitle = f"Score {game.score}  Best {game.best_distance}m  Press R"
        draw_center_panel(
            surface,
            fonts,
            title,
            subtitle,
        )
    elif game.show_help and leader.x < 95:
        if game.mode != "double":
            draw_text(surface, fonts["tiny"], "Space/up jump  Down/S tuck  A/D spin", (69, 40), INK)


def draw_center_panel(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    title: str,
    subtitle: str,
) -> None:
    title_width = fonts["small"].render(title, False, INK).get_width()
    subtitle_width = fonts["tiny"].render(subtitle, False, MUTED).get_width()
    panel_width = min(VIRTUAL_WIDTH - 36, max(172, title_width + 24, subtitle_width + 24))
    rect = pygame.Rect(0, 66, panel_width, 46)
    rect.centerx = VIRTUAL_WIDTH // 2
    pygame.draw.rect(surface, (249, 249, 236), rect)
    pygame.draw.rect(surface, INK, rect, 1)
    draw_centered_text(surface, fonts["small"], title, (rect.centerx, rect.y + 16), INK)
    draw_centered_text(surface, fonts["tiny"], subtitle, (rect.centerx, rect.y + 32), MUTED)


def draw_pause_menu(
    surface: pygame.Surface,
    game: SlopeGame,
    fonts: dict[str, pygame.font.Font],
) -> None:
    rect = pygame.Rect(0, 53, 228, 74)
    rect.centerx = VIRTUAL_WIDTH // 2
    pygame.draw.rect(surface, (249, 249, 236), rect)
    pygame.draw.rect(surface, INK, rect, 1)
    draw_centered_text(surface, fonts["small"], "Paused", (rect.centerx, rect.y + 17), INK)

    options = ["Continue", "Menu"]
    for index, label in enumerate(options):
        option_rect = pygame.Rect(rect.x + 24 + index * 100, rect.y + 34, 82, 25)
        selected = index == game.pause_choice
        pygame.draw.rect(surface, (231, 242, 238) if selected else WHITE, option_rect)
        pygame.draw.rect(surface, ICE_BLUE if selected else MUTED, option_rect, 2 if selected else 1)
        draw_centered_text(surface, fonts["tiny"], label, option_rect.center, INK)

    draw_centered_text(surface, fonts["tiny"], "A/D choose   Enter or Space", (rect.centerx, rect.y + 66), MUTED)


def draw_menu(
    surface: pygame.Surface,
    game: SlopeGame,
    fonts: dict[str, pygame.font.Font],
) -> None:
    rect = pygame.Rect(0, 43, 228, 94)
    rect.centerx = VIRTUAL_WIDTH // 2
    pygame.draw.rect(surface, (249, 249, 236), rect)
    pygame.draw.rect(surface, INK, rect, 1)
    draw_centered_text(surface, fonts["small"], "Pixel Slope Escape", (rect.centerx, rect.y + 18), INK)

    options = [("Single", "solo run"), ("Double", "race + shots")]
    for index, (label, detail) in enumerate(options):
        option_rect = pygame.Rect(rect.x + 20 + index * 97, rect.y + 37, 84, 31)
        selected = index == game.menu_choice
        pygame.draw.rect(surface, (231, 242, 238) if selected else WHITE, option_rect)
        pygame.draw.rect(surface, ICE_BLUE if selected else MUTED, option_rect, 2 if selected else 1)
        draw_centered_text(surface, fonts["tiny"], label, (option_rect.centerx, option_rect.y + 10), INK)
        draw_centered_text(surface, fonts["tiny"], detail, (option_rect.centerx, option_rect.y + 22), MUTED)

    draw_centered_text(surface, fonts["tiny"], "1/2 choose   Enter start   Esc quit", (rect.centerx, rect.y + 81), MUTED)


def draw_world_layer(
    game: SlopeGame,
    sprites: dict[str, pygame.Surface],
    season: str,
) -> pygame.Surface:
    world_layer = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.SRCALPHA)
    draw_sky(world_layer, game.camera_x, season)
    draw_avalanche(world_layer, game, sprites)
    draw_terrain(world_layer, game.camera_x, season)
    draw_entities(world_layer, game, sprites, season)
    draw_projectiles(world_layer, game, sprites, season)
    draw_particles(world_layer, game)
    for player in game.active_players():
        draw_player(world_layer, game, sprites, season, player)
    return world_layer


def draw_game(
    virtual: pygame.Surface,
    game: SlopeGame,
    sprites: dict[str, pygame.Surface],
    fonts: dict[str, pygame.font.Font],
) -> None:
    if game.state == "menu":
        if STARTUP_BACKGROUND is not None:
            virtual.blit(STARTUP_BACKGROUND, (0, 0))
        else:
            draw_sky(virtual, 0.0, "winter")
            draw_terrain(virtual, 0.0, "winter")
        return

    shake_x = 0
    shake_y = 0
    if game.shake_timer > 0.0:
        shake_x = game.rng.randint(-2, 2)
        shake_y = game.rng.randint(-2, 2)

    world_layer = draw_world_layer(game, sprites, game.season)
    if game.transition_timer > 0.0 and game.transition_from != game.season:
        old_layer = draw_world_layer(game, sprites, game.transition_from)
        old_alpha = round(clamp(game.transition_timer / SEASON_TRANSITION_SECONDS, 0.0, 1.0) * 255)
        old_layer.set_alpha(old_alpha)
        world_layer.blit(old_layer, (0, 0))

    virtual.fill(SKY_TOP)
    virtual.blit(world_layer, (shake_x, shake_y))


def ui_pos(x: float, y: float) -> tuple[int, int]:
    return round(x * SCALE), round(y * SCALE)


def ui_rect(x: float, y: float, width: float, height: float) -> pygame.Rect:
    return pygame.Rect(round(x * SCALE), round(y * SCALE), round(width * SCALE), round(height * SCALE))


def draw_screen_center_panel(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    title: str,
    subtitle: str,
) -> None:
    title_width = fonts["small"].render(title, True, INK).get_width()
    subtitle_width = fonts["tiny"].render(subtitle, True, MUTED).get_width()
    panel_width = min(WINDOW_SIZE[0] - 108, max(516, title_width + 72, subtitle_width + 72))
    rect = pygame.Rect(0, round(66 * SCALE), panel_width, round(50 * SCALE))
    rect.centerx = WINDOW_SIZE[0] // 2
    pygame.draw.rect(surface, (249, 249, 236), rect)
    pygame.draw.rect(surface, INK, rect, 3)
    draw_centered_text(surface, fonts["small"], title, (rect.centerx, rect.y + round(18 * SCALE)), INK)
    draw_centered_text(surface, fonts["tiny"], subtitle, (rect.centerx, rect.y + round(35 * SCALE)), MUTED)


def draw_screen_health_bar(
    surface: pygame.Surface,
    player: Player,
    font: pygame.font.Font,
    pos: tuple[int, int],
    width: int,
) -> None:
    x, y = pos
    bar_height = round(7 * SCALE)
    fill = round(clamp(player.health / MAX_HEALTH, 0.0, 1.0) * width)
    pygame.draw.rect(surface, INK, (x, y, width + 4, bar_height), 2)
    pygame.draw.rect(surface, CORAL, (x + 2, y + 2, width, bar_height - 4))
    pygame.draw.rect(surface, player.color, (x + 2, y + 2, fill, bar_height - 4))
    draw_text(surface, font, f"HP {player.health}", (x + width + round(10 * SCALE), y - 2), INK)


def draw_screen_hud(surface: pygame.Surface, game: SlopeGame, fonts: dict[str, pygame.font.Font]) -> None:
    if game.mode == "double" and game.player2 is not None:
        panel_specs = [(game.player, 4), (game.player2, VIRTUAL_WIDTH - 114)]
        for player, virtual_x in panel_specs:
            rect = ui_rect(virtual_x, 4, 110, 39)
            pygame.draw.rect(surface, (231, 242, 238), rect)
            pygame.draw.rect(surface, player.color, (rect.x, rect.y, rect.width, round(3 * SCALE)))
            pygame.draw.rect(surface, INK, rect, 3)
            status = "OUT" if player.eliminated else f"{int(player.x / 8)}m"
            draw_text(surface, fonts["tiny"], f"{player.label} {player.score}", ui_pos(virtual_x + 5, 8), INK)
            draw_text(surface, fonts["tiny"], f"{status}  STARS {player.shards}", ui_pos(virtual_x + 5, 20), MUTED)
            draw_screen_health_bar(surface, player, fonts["tiny"], ui_pos(virtual_x + 5, 31), round(58 * SCALE))
    else:
        rect = ui_rect(4, 4, 142, 25)
        pygame.draw.rect(surface, (231, 242, 238), rect)
        pygame.draw.rect(surface, INK, rect, 3)
        draw_text(surface, fonts["tiny"], f"SCORE {game.score}", ui_pos(9, 7), INK)
        draw_text(surface, fonts["tiny"], f"DIST {int(game.player.x / 8)}m", ui_pos(9, 17), MUTED)
        draw_text(surface, fonts["tiny"], f"STARS {game.shards}", ui_pos(86, 17), MUTED)

    leader = game.leader()
    gap = max(0.0, leader.x - game.avalanche_x)
    meter_rect = ui_rect(VIRTUAL_WIDTH - 78, 8, 68, 24)
    if game.mode == "double":
        meter_rect = ui_rect(0, 46, 78, 25)
        meter_rect.centerx = WINDOW_SIZE[0] // 2

    pygame.draw.rect(surface, (231, 242, 238), meter_rect)
    pygame.draw.rect(surface, INK, meter_rect, 3)
    threat_label = "MUDSLIDE" if game.season == "summer" else "SNOW WALL"
    draw_centered_text(surface, fonts["micro"], threat_label, (meter_rect.centerx, meter_rect.y + round(7 * SCALE)), INK)

    bar_rect = pygame.Rect(
        meter_rect.x + round(6 * SCALE),
        meter_rect.y + round(15 * SCALE),
        meter_rect.width - round(12 * SCALE),
        round(6 * SCALE),
    )
    fill = round(clamp(gap / 180.0, 0.0, 1.0) * bar_rect.width)
    pygame.draw.rect(surface, CORAL, bar_rect)
    pygame.draw.rect(surface, ICE_BLUE, (bar_rect.right - fill, bar_rect.y, fill, bar_rect.height))
    pygame.draw.rect(surface, INK, bar_rect, 2)

    if game.message_timer > 0.0:
        rendered = fonts["tiny"].render(game.message, True, INK)
        width = min(rendered.get_width() + round(10 * SCALE), WINDOW_SIZE[0] - round(18 * SCALE))
        message_rect = pygame.Rect(round(9 * SCALE), round(151 * SCALE), width, round(17 * SCALE))
        pygame.draw.rect(surface, (249, 249, 236), message_rect)
        pygame.draw.rect(surface, INK, message_rect, 3)
        surface.blit(rendered, (message_rect.x + round(5 * SCALE), message_rect.y + round(2 * SCALE)))


def draw_screen_pause_menu(surface: pygame.Surface, game: SlopeGame, fonts: dict[str, pygame.font.Font]) -> None:
    rect = ui_rect(78, 53, 228, 74)
    pygame.draw.rect(surface, (249, 249, 236), rect)
    pygame.draw.rect(surface, INK, rect, 3)
    draw_centered_text(surface, fonts["small"], "Paused", (rect.centerx, rect.y + round(17 * SCALE)), INK)

    options = ["Continue", "Menu"]
    for index, label in enumerate(options):
        option_rect = ui_rect(102 + index * 100, 87, 82, 25)
        selected = index == game.pause_choice
        pygame.draw.rect(surface, (231, 242, 238) if selected else WHITE, option_rect)
        pygame.draw.rect(surface, ICE_BLUE if selected else MUTED, option_rect, 4 if selected else 3)
        draw_centered_text(surface, fonts["tiny"], label, option_rect.center, INK)

    draw_centered_text(surface, fonts["tiny"], "A/D choose   Enter or Space", (rect.centerx, rect.y + round(66 * SCALE)), MUTED)


def draw_screen_menu(surface: pygame.Surface, game: SlopeGame, fonts: dict[str, pygame.font.Font]) -> None:
    rect = ui_rect(78, 43, 228, 94)
    pygame.draw.rect(surface, (249, 249, 236), rect)
    pygame.draw.rect(surface, INK, rect, 3)
    draw_centered_text(surface, fonts["small"], "Pixel Slope Escape", (rect.centerx, rect.y + round(18 * SCALE)), INK)

    options = [("Single", "solo run"), ("Double", "race + shots")]
    for index, (label, detail) in enumerate(options):
        option_rect = ui_rect(98 + index * 97, 80, 84, 31)
        selected = index == game.menu_choice
        pygame.draw.rect(surface, (231, 242, 238) if selected else WHITE, option_rect)
        pygame.draw.rect(surface, ICE_BLUE if selected else MUTED, option_rect, 4 if selected else 3)
        draw_centered_text(surface, fonts["tiny"], label, (option_rect.centerx, option_rect.y + round(10 * SCALE)), INK)
        draw_centered_text(surface, fonts["tiny"], detail, (option_rect.centerx, option_rect.y + round(22 * SCALE)), MUTED)

    draw_centered_text(surface, fonts["tiny"], "1/2 choose   Enter start   Esc quit", (rect.centerx, rect.y + round(81 * SCALE)), MUTED)


def draw_ui(surface: pygame.Surface, game: SlopeGame, fonts: dict[str, pygame.font.Font]) -> None:
    if game.state == "menu":
        draw_screen_menu(surface, game, fonts)
        return

    if game.transition_timer > 0.0:
        label = "Summer Mode!" if game.season == "summer" else "Winter Mode!"
        draw_screen_center_panel(surface, fonts, label, "The trail is shifting...")

    draw_screen_hud(surface, game, fonts)

    if game.paused:
        draw_screen_pause_menu(surface, game, fonts)
    elif game.game_over:
        title = game.result_title or "Snowed In"
        subtitle = game.result_subtitle
        if not subtitle:
            if game.mode == "double" and game.player2 is not None:
                subtitle = f"P1 {game.player.score}  P2 {game.player2.score}  Press any key"
            else:
                subtitle = f"Score {game.score}  Best {game.best_distance}m  Press R"
        draw_screen_center_panel(surface, fonts, title, subtitle)
    elif game.show_help and game.leader().x < 95 and game.mode != "double":
        draw_text(surface, fonts["tiny"], "Space/up jump  Down/S tuck  A/D spin", ui_pos(69, 40), INK)


def make_fonts() -> dict[str, pygame.font.Font]:
    return {
        "micro": pygame.font.SysFont("courier", 16, bold=True),
        "tiny": pygame.font.SysFont("courier", 22, bold=True),
        "small": pygame.font.SysFont("courier", 38, bold=True),
    }


def return_to_menu(game: SlopeGame) -> None:
    game.state = "menu"
    game.game_over = False
    game.paused = False
    game.projectiles = []
    game.pause_choice = 0
    game.result_title = ""
    game.result_subtitle = ""
    game.transition_timer = 0.0
    game.message = "Choose Single or Double to start."
    game.message_timer = 4.0


def toggle_pause_choice(game: SlopeGame) -> None:
    game.pause_choice = 1 - game.pause_choice


def activate_pause_choice(game: SlopeGame) -> None:
    if game.pause_choice == 0:
        game.paused = False
    else:
        return_to_menu(game)


def handle_event(event: pygame.event.Event, game: SlopeGame) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return False

        if game.game_over and game.mode == "double":
            return_to_menu(game)
            return True

        if game.state == "menu":
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                game.menu_choice = 1 - game.menu_choice
            elif event.key == pygame.K_1:
                game.menu_choice = 0
            elif event.key == pygame.K_2:
                game.menu_choice = 1
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                best = game.best_distance
                game.reset("double" if game.menu_choice == 1 else "single")
                game.best_distance = best
            return True

        if game.paused:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                toggle_pause_choice(game)
            elif event.key == pygame.K_p:
                if game.pause_choice == 0:
                    game.paused = False
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                activate_pause_choice(game)
            return True

        if event.key == pygame.K_r:
            best = game.best_distance
            if game.game_over:
                return_to_menu(game)
            else:
                game.reset(game.mode)
            game.best_distance = best
        elif event.key == pygame.K_p:
            game.paused = True
            game.pause_choice = 0
        elif event.key == pygame.K_SPACE and (game.paused or game.game_over):
            if game.game_over:
                return_to_menu(game)
            else:
                game.paused = False
        elif game.mode == "double" and event.key == P1_CONTROLS["attack"]:
            fire_projectile(game, game.player)
            game.show_help = False
        elif game.mode == "double" and game.player2 is not None and event.key == P2_CONTROLS["attack"]:
            fire_projectile(game, game.player2)
            game.show_help = False
        elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            game.show_help = False
    return True


def main() -> None:
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    global SOUNDS
    SOUNDS = load_audio()
    pygame.display.set_caption("Pixel Slope Escape")
    screen = pygame.display.set_mode(WINDOW_SIZE)
    virtual = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
    clock = pygame.time.Clock()
    sprites = build_sprites()
    fonts = make_fonts()

    game = SlopeGame(random.Random())
    if "--start-single" in sys.argv:
        game.reset("single")
    elif "--start-double" in sys.argv:
        game.reset("double")

    smoke_frames = 180 if "--smoke-test" in sys.argv else None
    screenshot_path = None
    for arg in sys.argv:
        if arg.startswith("--screenshot="):
            screenshot_path = arg.split("=", 1)[1]
            smoke_frames = 1
    frame_count = 0
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.033)
        for event in pygame.event.get():
            running = handle_event(event, game)

        update_game(game, sprites, dt)
        draw_game(virtual, game, sprites, fonts)
        pygame.transform.scale(virtual, WINDOW_SIZE, screen)
        draw_ui(screen, game, fonts)
        pygame.display.flip()
        if screenshot_path:
            pygame.image.save(screen, screenshot_path)
            running = False

        frame_count += 1
        if smoke_frames is not None and frame_count >= smoke_frames:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
