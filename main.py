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

# Colors (fallback)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235)
RED = (200, 50, 50)
GREEN = (50, 200, 50)

# ---------- Helper Classes ----------

class GameObject(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color=WHITE):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

class Platform(GameObject):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h, color=GREEN)

# to fire bullets
class Bullet(GameObject):
    def __init__(self, x, y, direction):
        super().__init__(x, y, 8, 4, color=BLACK)
        self.vx = BULLET_SPEED * direction

    def update(self, dt, level):
        self.rect.x += self.vx
        # Remove if offscreen or hits platform
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()
        # Simple collision with platforms
        for plat in level.platforms:
            if self.rect.colliderect(plat.rect):
                self.kill()
                break

# the protagonist
class Player(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, color=RED)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing = 1  # 1 right, -1 left
        self.lives = 3
        self.score = 0
        self.can_shoot = True
        self.shoot_cooldown = 300  # milliseconds
        self.last_shot = 0

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

    def shoot(self, now, bullets_group):
        if now - self.last_shot >= self.shoot_cooldown:
            self.last_shot = now
            bx = self.rect.centerx + (self.facing * 20)
            by = self.rect.centery
            bullet = Bullet(bx, by, self.facing)
            bullets_group.add(bullet)

    def apply_gravity(self):
        self.vy += GRAVITY
        if self.vy > 15:
            self.vy = 15  # terminal velocity

    def update(self, dt, level):
        # Horizontal movement
        self.rect.x += self.vx
        self._check_collision(level.platforms, dx=self.vx)

        # Vertical movement
        self.apply_gravity()
        self.rect.y += self.vy
        self.on_ground = False
        self._check_collision(level.platforms, dy=self.vy)

    def _check_collision(self, platforms, dx=0, dy=0):
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if dx > 0:  # moving right
                    self.rect.right = plat.rect.left
                if dx < 0:  # moving left
                    self.rect.left = plat.rect.right
                if dy > 0:  # falling
                    self.rect.bottom = plat.rect.top
                    self.vy = 0
                    self.on_ground = True
                if dy < 0:  # jumping
                    self.rect.top = plat.rect.bottom
                    self.vy = 0

class Enemy(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, color=(128, 0, 128))
        self.vx = 2
        self.patrol_range = 100
        self.origin_x = x

    def update(self, dt, level):
        self.rect.x += self.vx
        if abs(self.rect.x - self.origin_x) > self.patrol_range:
            self.vx *= -1

# ---------- Level Loading ----------

class Level:
    TILE_SIZE = 40
    def __init__(self, layout_lines):
        self.platforms = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.player_start = (50, SCREEN_HEIGHT - 100)
        self.parse_layout(layout_lines)

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
                # Add other tile types here (collectibles, hazards, exit, etc.)

# ---------- Sample Levels (you can move these to separate files) ----------

SAMPLE_LEVELS = [
    [
        "############################",
        "#                          #",
        "#                          #",
        "#          E               #",
        "#       #####              #",
        "#                 E        #",
        "#               #####      #",
        "#    P            E        #",
        "#######           #####  ###",
        "#                          #",
        "############################",
    ],
    # Placeholder for up to 10 levels; you can add more list-of-strings here
]

# ---------- Game Loop ----------

def draw_hud(screen, player, level_no):
    font = pygame.font.SysFont(None, 24)
    score_surf = font.render(f"Score: {player.score}", True, BLACK)
    lives_surf = font.render(f"Lives: {player.lives}", True, BLACK)
    level_surf = font.render(f"Level: {level_no+1}", True, BLACK)
    screen.blit(score_surf, (10, 10))
    screen.blit(lives_surf, (10, 35))
    screen.blit(level_surf, (10, 60))

def load_level(index):
    if 0 <= index < len(SAMPLE_LEVELS):
        return Level(SAMPLE_LEVELS[index])
    else:
        # fallback empty level
        empty = ["#" * 30] + ["#" + " " * 28 + "#" for _ in range(12)] + ["#" * 30]
        return Level(empty)

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Dangerous Dave Clone")
    clock = pygame.time.Clock()

    current_level_index = 0
    level = load_level(current_level_index)

    player = Player(*level.player_start)
    player_group = pygame.sprite.GroupSingle(player)

    bullets = pygame.sprite.Group()

    running = True
    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        player.handle_input(keys)
        if keys[pygame.K_f]:  # shoot with 'F'
            player.shoot(now, bullets)

        # Update
        player.update(dt, level)
        bullets.update(dt, level)
        level.enemies.update(dt, level)

        # Collision: player with enemies
        for enemy in level.enemies:
            if player.rect.colliderect(enemy.rect):
                # rudimentary damage
                player.lives -= 1
                # respawn
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

        # Render
        screen.fill(SKY_BLUE)
        level.platforms.draw(screen)
        level.enemies.draw(screen)
        bullets.draw(screen)
        player_group.draw(screen)
        draw_hud(screen, player, current_level_index)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
