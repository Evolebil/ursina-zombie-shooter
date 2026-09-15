from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math
from panda3d.core import globalClock

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

PLAYER_MAX_HP = 5
PLAYER_START_POS = (0, 1, 0)

# Оружие
WEAPONS = {
    'pistol': {
        'name': 'Пистолет',
        'damage': 20,
        'rays': 1,
        'cooldown': 0.2,
        'spread': 0.15,
    },
    'shotgun': {
        'name': 'Дробовик',
        'damage': 35,
        'rays': 8,
        'cooldown': 0.8,
        'spread': 0.5,
    },
    'rifle': {
        'name': 'Автомат',
        'damage': 10,
        'rays': 1,
        'cooldown': 0.05,
        'spread': 0.1,
    },
}

WEAPON_ORDER = ['pistol', 'shotgun', 'rifle']

# Зомби
ZOMBIE_MAX_HP = 100
ZOMBIE_SPEED = 2.5
ZOMBIE_ATTACK_DAMAGE = 1
ZOMBIE_ATTACK_COOLDOWN = 1.0
ZOMBIE_SPAWN_DISTANCE_MIN = 5
ZOMBIE_SPAWN_DISTANCE_MAX = 15

# Спавн
SPAWN_INTERVAL_START = 2.0
SPAWN_INTERVAL_MIN = 0.5

# ============================================================================
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ============================================================================

app = Ursina(title="Zombie Shooter")
camera.z = 0

# ============================================================================
# ИГРОВОЕ СОСТОЯНИЕ
# ============================================================================

class GameState:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.hp = PLAYER_MAX_HP
        self.kills = 0
        self.current_weapon = 0  # индекс в WEAPON_ORDER
        self.game_over = False
        self.last_shot_time = 0
        self.last_spawn_time = 0
        self.zombies = []

game_state = GameState()

# ============================================================================
# СОЗДАНИЕ АРЕНЫ
# ============================================================================

def create_arena():
    """Создаёт простую арену с полом, стенами и препятствиями."""
    
    # Пол (зелёная поверхность)
    floor = Entity(
        model='cube',
        scale=(50, 1, 50),
        color=color.green,
        position=(0, -1, 0),
        collider='box'
    )
    
    # Северная стена
    wall_n = Entity(
        model='cube',
        scale=(50, 3, 1),
        color=color.dark_gray,
        position=(0, 1, -25),
        collider='box'
    )
    
    # Южная стена
    wall_s = Entity(
        model='cube',
        scale=(50, 3, 1),
        color=color.dark_gray,
        position=(0, 1, 25),
        collider='box'
    )
    
    # Западная стена
    wall_w = Entity(
        model='cube',
        scale=(1, 3, 50),
        color=color.dark_gray,
        position=(-25, 1, 0),
        collider='box'
    )
    
    # Восточная стена
    wall_e = Entity(
        model='cube',
        scale=(1, 3, 50),
        color=color.dark_gray,
        position=(25, 1, 0),
        collider='box'
    )
    
    # Препятствия (блоки внутри арены)
    obstacles = [
        (-10, 1, -10),
        (10, 1, -10),
        (-10, 1, 10),
        (10, 1, 10),
        (0, 1, 0),
    ]
    
    for pos in obstacles:
        Entity(
            model='cube',
            scale=(3, 2, 3),
            color=color.dark_gray,
            position=pos,
            collider='box'
        )

# ============================================================================
# КЛАСС ИГРОКА
# ============================================================================

class Player:
    def __init__(self):
        self.controller = FirstPersonController(
            position=PLAYER_START_POS,
            speed=8,
            sensitivity=10
        )
        self.weapon_model = self.create_weapon_model()
    
    def create_weapon_model(self):
        """Создаёт простую визуальную модель оружия перед камерой."""
        weapon = Entity(
            model='cube',
            scale=(0.3, 0.15, 1),
            color=color.dark_gray,
            position=(0.3, -0.3, 0.8),
            parent=camera,
            rotation=(0, 0, 0)
        )
        return weapon
    
    def update_weapon_model(self):
        """Обновляет визуал оружия в зависимости от текущего."""
        current_weapon_key = WEAPON_ORDER[game_state.current_weapon]
        weapon_data = WEAPONS[current_weapon_key]
        
        # Меняем размер в зависимости от типа оружия
        if current_weapon_key == 'pistol':
            self.weapon_model.scale = (0.2, 0.12, 0.6)
            self.weapon_model.color = color.gray
        elif current_weapon_key == 'shotgun':
            self.weapon_model.scale = (0.4, 0.2, 0.8)
            self.weapon_model.color = color.dark_gray
        elif current_weapon_key == 'rifle':
            self.weapon_model.scale = (0.25, 0.1, 1.2)
            self.weapon_model.color = color.dark_gray
    
    def shoot(self):
        """Выстрел из текущего оружия (raycast)."""
        current_time = globalClock.getFrameTime()
        current_weapon_key = WEAPON_ORDER[game_state.current_weapon]
        weapon_data = WEAPONS[current_weapon_key]
        
        if current_time - game_state.last_shot_time < weapon_data['cooldown']:
            return
        
        game_state.last_shot_time = current_time
        
        # Стрельба
        for _ in range(weapon_data['rays']):
            # Случайный разброс
            spread_x = random.uniform(-weapon_data['spread'], weapon_data['spread'])
            spread_y = random.uniform(-weapon_data['spread'], weapon_data['spread'])
            
            # Направление луча от камеры (используем .forward(), это свойство, не функция)
            cam_forward = camera.forward
            direction = cam_forward + Vec3(spread_x, spread_y, 0)
            direction = direction.normalized()
            
            # Raycast
            hit_info = raycast(camera.position, direction, distance=1000, ignore=[player.controller])
            
            if hit_info.hit:
                # Проверяем, попали ли в зомби
                for zombie in game_state.zombies:
                    if hit_info.entity == zombie.model:
                        zombie.take_damage(weapon_data['damage'])
                        break

# ============================================================================
# КЛАСС ЗОМБИ
# ============================================================================

class Zombie:
    def __init__(self, position):
        self.hp = ZOMBIE_MAX_HP
        self.position = Vec3(*position)
        self.model = Entity(
            model='cube',
            scale=(1, 2, 1),
            color=color.green,
            position=self.position,
            collider='box'
        )
        self.last_attack_time = 0
    
    def update(self, player_pos, dt):
        """Обновляет поведение зомби."""
        if self.hp <= 0:
            return
        
        # Движение к игроку
        direction = (player_pos - self.position).normalized()
        self.position += direction * ZOMBIE_SPEED * dt
        self.model.position = self.position
        
        # Проверка расстояния для атаки
        distance = distance_between(self.position, player_pos)
        if distance < 2:
            # Зомби может атаковать
            current_time = globalClock.getFrameTime()
            if current_time - self.last_attack_time >= ZOMBIE_ATTACK_COOLDOWN:
                self.attack()
                self.last_attack_time = current_time
    
    def take_damage(self, damage):
        """Получить урон."""
        self.hp -= damage
        if self.hp <= 0:
            self.die()
    
    def attack(self):
        """Атака на игрока."""
        if not game_state.game_over:
            game_state.hp -= ZOMBIE_ATTACK_DAMAGE
            if game_state.hp <= 0:
                game_state.game_over = True
    
    def die(self):
        """Зомби умирает."""
        destroy(self.model)
        game_state.kills += 1

def distance_between(pos1, pos2):
    """Расстояние между двумя позициями."""
    return math.sqrt((pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2 + (pos1.z - pos2.z)**2)

# ============================================================================
# СПАВН ЗОМБИ
# ============================================================================

def spawn_zombie():
    """Спавнит нового зомби вокруг игрока."""
    player_pos = player.controller.position
    
    # Случайный угол
    angle = random.uniform(0, 2 * math.pi)
    
    # Случайное расстояние
    dist = random.uniform(ZOMBIE_SPAWN_DISTANCE_MIN, ZOMBIE_SPAWN_DISTANCE_MAX)
    
    # Позиция спавна
    spawn_x = player_pos.x + math.cos(angle) * dist
    spawn_z = player_pos.z + math.sin(angle) * dist
    spawn_pos = (spawn_x, 1, spawn_z)
    
    zombie = Zombie(spawn_pos)
    game_state.zombies.append(zombie)

def update_spawn():
    """Обновляет спавн зомби."""
    if game_state.game_over:
        return
    
    current_time = globalClock.getFrameTime()
    
    # Вычисляем интервал в зависимости от количества убитых
    spawn_interval = max(
        SPAWN_INTERVAL_MIN,
        SPAWN_INTERVAL_START - (game_state.kills * 0.1)
    )
    
    if current_time - game_state.last_spawn_time >= spawn_interval:
        spawn_zombie()
        game_state.last_spawn_time = current_time

# ============================================================================
# UI
# ============================================================================

ui_text = Text(
    text="",
    position=(-0.45, 0.45),
    scale=1,
    origin=(0, 0)
)

def update_ui():
    """Обновляет UI."""
    current_weapon_key = WEAPON_ORDER[game_state.current_weapon]
    weapon_name = WEAPONS[current_weapon_key]['name']
    
    ui_text.text = f"HP: {game_state.hp}/{PLAYER_MAX_HP}\nОружие: {weapon_name}\nУбито: {game_state.kills}"

game_over_panel = None
restart_button = None

def show_game_over():
    """Показывает экран Game Over."""
    global game_over_panel, restart_button
    
    # Полупрозрачная панель
    game_over_panel = Panel(
        size=(0.6, 0.6),
        color=color.rgba(0, 0, 0, 0.8)
    )
    
    # Текст GAME OVER
    game_over_text = Text(
        text=f"GAME OVER\n\nУбито зомби: {game_state.kills}",
        position=(0, 0.1),
        scale=2,
        parent=game_over_panel,
        origin=(0, 0)
    )
    
    # Кнопка Играть снова
    restart_button = Button(
        text="Играть снова",
        position=(0, -0.15),
        scale=(0.3, 0.1),
        parent=game_over_panel,
        on_click=restart_game
    )

def restart_game():
    """Перезапускает игру."""
    global game_over_panel, restart_button
    
    # Удаляем Game Over панель
    if game_over_panel:
        destroy(game_over_panel)
        game_over_panel = None
    if restart_button:
        destroy(restart_button)
        restart_button = None
    
    # Удаляем всех зомби
    for zombie in game_state.zombies:
        destroy(zombie.model)
    
    # Сбрасываем состояние
    game_state.reset()
    
    # Возвращаем игрока на стартовую позицию
    player.controller.position = Vec3(*PLAYER_START_POS)
    
    # Запускаем спавн
    game_state.last_spawn_time = globalClock.getFrameTime()

# ============================================================================
# ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ
# ============================================================================

def game_update():
    """Основное обновление игры."""
    if game_state.game_over:
        return
    
    # Обновляем UI
    update_ui()
    
    # Обновляем спавн
    update_spawn()
    
    # Получаем delta time
    dt = globalClock.getDeltaTime()
    
    # Обновляем зомби
    player_pos = player.controller.position
    
    # Удаляем мёртвых зомби из списка
    game_state.zombies = [z for z in game_state.zombies if z.hp > 0]
    
    for zombie in game_state.zombies:
        zombie.update(player_pos, dt)
    
    # Обработка выстрела
    if held_keys['left mouse']:
        player.shoot()
    
    # Переключение оружия
    if held_keys['1']:
        game_state.current_weapon = 0
        player.update_weapon_model()
    if held_keys['2']:
        game_state.current_weapon = 1
        player.update_weapon_model()
    if held_keys['3']:
        game_state.current_weapon = 2
        player.update_weapon_model()
    
    # Проверка Game Over
    if game_state.hp <= 0 and not game_state.game_over:
        game_state.game_over = True
        show_game_over()

def input(key):
    """Обработка входа."""
    pass

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================================

def init_game():
    """Инициализирует игру."""
    global player
    
    # Создаём арену
    create_arena()
    
    # Создаём игрока
    player = Player()
    player.update_weapon_model()
    
    # Инициализируем UI
    update_ui()
    
    # Инициализируем спавн
    game_state.last_spawn_time = globalClock.getFrameTime()

init_game()

# ============================================================================
# ГЛАВНЫЙ ЦИК
# ============================================================================

def update():
    game_update()

# ============================================================================
# ЗАПУСК
# ============================================================================

app.run()
