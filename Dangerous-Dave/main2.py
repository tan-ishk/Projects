import pygame
import sys
from pathlib import Path

# ---------- Constants ----------
SCREEN_WIDTH = 1115
SCREEN_HEIGHT = 435
FPS = 60

GRAVITY = 0.3
PLAYER_SPEED = 4
JUMP_VELOCITY = -10
BULLET_SPEED = 10

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235)
RED = (200, 50, 50)
GREEN = (50, 200, 50)

# ---------- Load Sounds ----------
pygame.mixer.init()
SOUND_DIR = Path("sounds")
SOUNDS = {
    "jump": pygame.mixer.Sound(SOUND_DIR / "jump.wav"),
    "shoot": pygame.mixer.Sound(SOUND_DIR / "shoot.wav"),
    "hit": pygame.mixer.Sound(SOUND_DIR / "hit.wav"),
    "hurt": pygame.mixer.Sound(SOUND_DIR / "hurt.wav"),
    "win": pygame.mixer.Sound(SOUND_DIR / "win.wav"),
    "explosion": pygame.mixer.Sound(SOUND_DIR / "explosion.wav"),
}

# ---------- Load Images ----------
pygame.display.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
ASSET_DIR = Path("assets")
IMAGES = {
    # "player": pygame.image.load(ASSET_DIR / "player.png").convert_alpha(),
    # "enemy": pygame.image.load(ASSET_DIR / "enemy.png").convert_alpha(),
    "goal": pygame.image.load(ASSET_DIR / "goal.jpg").convert_alpha(),
    "platform": pygame.image.load(ASSET_DIR / "platform.png").convert_alpha(),
}

# ---------- Helper Classes ----------

class GameObject(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color=WHITE):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

IMAGES["platform"] = pygame.image.load(ASSET_DIR / "platform.png").convert_alpha()
class Platform(GameObject):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        self.image = pygame.transform.scale(IMAGES["platform"], (w, h))

class Bullet(GameObject):
    def __init__(self, x, y, direction):
        super().__init__(x, y, 8, 4, color=BLACK)
        self.vx = BULLET_SPEED * direction

    def update(self, dt, level):
        self.rect.x += self.vx
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()
        for plat in level.platforms:
            if self.rect.colliderect(plat.rect):
                self.kill()
                break

class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image = pygame.image.load(ASSET_DIR / "explosion.png").convert_alpha()
        self.rect = self.image.get_rect(center=pos)
        self.start_time = pygame.time.get_ticks()
        self.duration = 300

    def update(self):
        if pygame.time.get_ticks() - self.start_time > self.duration:
            self.kill()


class Grenade(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x):
        super().__init__()
        self.image = pygame.image.load(ASSET_DIR / "grenade.png").convert_alpha()
        self.rect = self.image.get_rect(center=(x, y))

        # Simple projectile physics
        self.vx = (target_x - x) / 30  # adjust for arc length
        self.vy = -5  # upward arc
        self.gravity = 0.3
        self.timer = 2000  # milliseconds until explosion
        self.spawn_time = pygame.time.get_ticks()

    def update(self, level, player_group, explosion_group):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.vy += self.gravity

        # Timer explosion
        if pygame.time.get_ticks() - self.spawn_time > self.timer:
            explosion = Explosion(self.rect.center)
            explosion_group.add(explosion)
            self.kill()

        # Ground collision or player hit
        if self.rect.bottom >= level.ground_y or pygame.sprite.spritecollideany(self, player_group):
            explosion = Explosion(self.rect.center)
            explosion_group.add(explosion)
            SOUNDS["explosion"].play()
            self.kill()


class Player(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, color=RED)

        # Load and scale the player image to 32x32
        self.image = pygame.transform.scale(
            pygame.image.load(ASSET_DIR / "player.png").convert_alpha(), (32, 32)
        )

        # Update the rect using new image dimensions
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        # Movement and game state
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing = 1  # You can keep this if needed for future logic
        self.lives = 3
        self.score = 0
        self.last_shot = 0
        self.shoot_cooldown = 300  # milliseconds


    def handle_input(self, keys):
        self.vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -PLAYER_SPEED
            self.facing = 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = PLAYER_SPEED
            self.facing = 1
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = JUMP_VELOCITY
            self.on_ground = False
            SOUNDS["jump"].play()

    def shoot(self, now, bullets_group):
        if now - self.last_shot >= self.shoot_cooldown:
            self.last_shot = now
            bx = self.rect.centerx + (self.facing * 20)
            by = self.rect.centery
            bullet = Bullet(bx, by, self.facing)
            bullets_group.add(bullet)
            SOUNDS["shoot"].play()

    def apply_gravity(self):
        self.vy += GRAVITY
        if self.vy > 15:
            self.vy = 15

    def update(self, dt, level):
        self.rect.x += self.vx
        self._check_collision(level.platforms, dx=self.vx)
        self.apply_gravity()
        self.rect.y += self.vy
        self.on_ground = False
        self._check_collision(level.platforms, dy=self.vy)

    def _check_collision(self, platforms, dx=0, dy=0):
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if dx > 0:
                    self.rect.right = plat.rect.left
                if dx < 0:
                    self.rect.left = plat.rect.right
                if dy > 0:
                    self.rect.bottom = plat.rect.top
                    self.vy = 0
                    self.on_ground = True
                if dy < 0:
                    self.rect.top = plat.rect.bottom
                    self.vy = 0

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image_right = pygame.image.load(ASSET_DIR / "enemy.png").convert_alpha()
        self.image_left = pygame.transform.flip(self.image_right, True, False)
        self.image = self.image_left

        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        self.start_x = x - 100
        self.end_x = x + 100
        self.speed = 2
        self.direction = 1

    def update(self, dt, level):
        self.rect.x += self.speed * self.direction

        if self.rect.x <= self.start_x:
            self.rect.x = self.start_x
            self.direction = 1
            self.image = self.image_left
        elif self.rect.x >= self.end_x:
            self.rect.x = self.end_x
            self.direction = -1
            self.image = self.image_right

class ShooterEnemy(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32)
        # self.image = pygame.Surface((32, 32))
        # self.image.fill((0, 0, 255))  # Blue for shooter
        self.image_left = pygame.image.load(ASSET_DIR / "ShooterEnemy.png").convert_alpha()
        self.image_right = pygame.transform.flip(self.image_left, True, False)
        self.image = self.image_left  # default facing
        self.last_shot = 0
        self.shoot_delay = 1000  # milliseconds
        self.direction = 1  # 1 = facing right, -1 = facing left

    def update(self, dt, level, player, enemy_bullets):
        now = pygame.time.get_ticks()
        dy = abs(self.rect.centery - player.rect.centery)

        # Check if player is in same horizontal line (with small vertical margin)
        if dy < 16 and now - self.last_shot >= self.shoot_delay:
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            bullet = Bullet(self.rect.centerx, self.rect.centery, direction)
            bullet.image.fill((0, 0, 150))  # Dark blue bullet
            enemy_bullets.add(bullet)
            SOUNDS["shoot"].play()
            self.last_shot = now

        # Flip direction if player crosses shooter's x position
        if player.rect.centerx < self.rect.centerx:
            self.direction = -1
            self.image = self.image_left
        else:
            self.direction = 1
            self.image = self.image_right

    # Existing shoot logic, optional cooldown etc.
    # Example: fire bullet if player is on same y-level and cooldown passed

class GrenadeEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.image.load(ASSET_DIR / "grenade_enemy.png").convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.throw_cooldown = 3000  # milliseconds
        self.last_throw = pygame.time.get_ticks()

    def update(self, player, grenade_group):
        now = pygame.time.get_ticks()
        if abs(player.rect.centerx - self.rect.centerx) < 300 and now - self.last_throw > self.throw_cooldown:
            self.last_throw = now
            grenade = Grenade(self.rect.centerx, self.rect.top, player.rect.centerx)
            grenade_group.add(grenade)


# ---------- Level ----------
class Level:
    TILE_SIZE = 40
    def __init__(self, layout_lines):
        self.platforms = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.grenade_enemies = pygame.sprite.Group()  # <-- Add this line
        self.goal = None
        self.player_start = (50, SCREEN_HEIGHT - 100)
        self.parse_layout(layout_lines)
        self.ground_y = SCREEN_HEIGHT - 40  # or whatever is your ground level

    def parse_layout(self, lines):
        for row_idx, line in enumerate(lines):
            for col_idx, ch in enumerate(line.rstrip("\n")):
                x = col_idx * self.TILE_SIZE
                y = row_idx * self.TILE_SIZE
                if ch == "#":
                    self.platforms.add(Platform(x, y, self.TILE_SIZE, self.TILE_SIZE))
                elif ch == "P":
                    self.player_start = (x, y - 8)
                elif ch == "E":
                    self.enemies.add(Enemy(x, y + self.TILE_SIZE - 32))

                elif ch == "S":
                    shooter = ShooterEnemy(x, y + self.TILE_SIZE - 32)
                    self.enemies.add(shooter)

                elif ch == "G":
                    self.grenade_enemies.add(GrenadeEnemy(x, y))

 
                elif ch == "X":
                    self.goal = GameObject(x, y, self.TILE_SIZE, self.TILE_SIZE)
                    self.goal.image = pygame.transform.scale(IMAGES["goal"], (self.TILE_SIZE, self.TILE_SIZE))
                    self.goal.rect = self.goal.image.get_rect(topleft=(x, y))

# ---------- Sample Levels ----------
SAMPLE_LEVELS = [
    [
        "############################",
        "#                          #",
        "#                          #",
        "#         E                #",
        "#       #####              #",
        "#                 E        #",
        "#               #####      #",
        "#P                  E     X#",
        "#######           #####  ###",
        "#                          #",
        "############################",
    ],
    [
        "############################",
        "#                          #",
        "#               E          #",
        "#             #####        #",
        "#                          #",
        "#          E           E  X#",
        "#        ######     ########",
        "#P       E          E      #",
        "#####  ######     #####  ###",
        "#                          #",
        "############################",
    ],
    [
        "############################",
        "#                          #",
        "#               S          #",
        "#             #####        #",
        "#                          #",
        "#          S           E  X#",
        "#        ######     ########",
        "#P       E          E      #",
        "#############     #####  ###",
        "#                          #",
        "############################",
    ],
    [
        "############################",
        "#                          #",
        "#               G          #",
        "#             #####        #",
        "#                          #",
        "#          G           S  X#",
        "#        ######     ########",
        "#P       E          E      #",
        "#############     #####  ###",
        "#                          #",
        "############################",
    ]
]

# ---------- HUD ----------
def draw_hud(screen, player, level_no):
    font = pygame.font.SysFont(None, 24)
    screen.blit(font.render(f"Score: {player.score}", True, BLACK), (10, 10))
    screen.blit(font.render(f"Lives: {player.lives}", True, BLACK), (10, 35))
    screen.blit(font.render(f"Level: {level_no+1}", True, BLACK), (10, 60))

# ---------- Game ----------
def load_level(index):
    if 0 <= index < len(SAMPLE_LEVELS):
        return Level(SAMPLE_LEVELS[index])
    else:
        return Level(["#"*30]*12)

def main():
    pygame.init()
    # screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Shooter")
    clock = pygame.time.Clock()

    current_level_index = 0
    level = load_level(current_level_index)

    player = Player(*level.player_start)
    player_group = pygame.sprite.GroupSingle(player)
    bullets = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()

    grenade_enemies = level.grenade_enemies
    grenades = pygame.sprite.Group()
    explosions = pygame.sprite.Group()


    running = True
    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        player.handle_input(keys)
        if keys[pygame.K_f]:
            player.shoot(now, bullets)

        player.update(dt, level)
        bullets.update(dt, level)
        enemy_bullets.update(dt, level)

        # level.enemies.update(dt, level)

        # Enemy collision
        for enemy in level.enemies:
            if player.rect.colliderect(enemy.rect):
                player.lives -= 1
                SOUNDS["hurt"].play()
                player.rect.topleft = level.player_start
                player.vx = player.vy = 0
                if player.lives <= 0:
                    print("Game Over")
                    running = False

        # Bullet hits enemy
        for bullet in bullets:
            hit = pygame.sprite.spritecollideany(bullet, level.enemies)
            if hit:
                hit.kill()
                bullet.kill()
                player.score += 100
                SOUNDS["hit"].play()

        # update enemies
        for enemy in level.enemies:
            if isinstance(enemy, ShooterEnemy):
                enemy.update(dt, level, player, enemy_bullets)
            else:
                enemy.update(dt, level)

        grenade_enemies.update(player, grenades)
        grenades.update(level, player_group, explosions)
        explosions.update()


        # player hit by enemy bullet
        for bullet in enemy_bullets:
            if player.rect.colliderect(bullet.rect):
                bullet.kill()
                player.lives -= 1
                SOUNDS["hurt"].play()
                player.rect.topleft = level.player_start
                player.vx = player.vy = 0
                if player.lives <= 0:
                    print("Game Over")
                    running = False


        # Level complete
        if level.goal and player.rect.colliderect(level.goal.rect):
            font = pygame.font.SysFont(None, 48)
            text = font.render("Level Complete!", True, (0, 100, 0))
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2))
            pygame.display.flip()
            SOUNDS["win"].play()
            pygame.time.delay(2000)

            current_level_index += 1
            if current_level_index < len(SAMPLE_LEVELS):
                level = load_level(current_level_index)
                player.rect.topleft = level.player_start
                player.vx = player.vy = 0
                bullets.empty()
            else:
                print("All levels complete!")
                running = False

        # Draw
        screen.fill(SKY_BLUE)
        level.platforms.draw(screen)
        level.enemies.draw(screen)
        grenade_enemies.draw(screen)
        enemy_bullets.draw(screen)
        grenades.draw(screen)
        explosions.draw(screen)
        if level.goal:
            screen.blit(level.goal.image, level.goal.rect)
        bullets.draw(screen)
        player_group.draw(screen)
        draw_hud(screen, player, current_level_index)
        pygame.display.flip()


    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
