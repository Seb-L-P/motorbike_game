import pygame
import sys
import math
import random

pygame.init()

WIDTH, HEIGHT = 768, 1024
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Neon Ride")

clock = pygame.time.Clock()

# Load assets
background = pygame.image.load("80s_synth_background.png").convert()
bike_original = pygame.image.load("bike.png").convert_alpha()

background = pygame.transform.scale(background, (WIDTH, HEIGHT))
bike_original = pygame.transform.scale(bike_original, (200, 200))

# Lane + player setup
lanes = [0, 1, 2]
player_lane = 1
bike_y_base = HEIGHT - 250
bike_x_pos = WIDTH // 2
time = 0

# Visuals
lean_angle = 0
lean_target = 0
trail = []
base_trail_color = (255, 0, 150)
smoke_particles = []

# Obstacles
obstacles = []  # each = {"lane": int, "z": float, "scored": bool}
spawn_timer = 0
spawn_interval = 75
score = 0
font = pygame.font.Font(None, 48)
game_over = False

# Road perspective constants
road_y_bottom = HEIGHT - 150
road_y_top = 300
base_obstacle_size = 160
max_obstacle_size = 260
obstacle_speed = 0.1
center_x = WIDTH // 2
max_lane_offset = 180
min_lane_offset = 40


# ============================= FUNCTIONS =============================

def lane_blocked_in_future(lane, z_distance=3):
    """Return True if this lane already has an obstacle within z_distance"""
    for o in obstacles:
        if o["lane"] == lane and o["z"] < 16 and o["z"] > 16 - z_distance:
            return True
    return False


def safe_to_spawn():
    """Ensure not all 3 lanes will be blocked close together"""
    # Look at upcoming road section
    lanes_blocked = {o["lane"] for o in obstacles if 2 < o["z"] < 6}
    return len(lanes_blocked) < 3  # at least one open lane ahead


def spawn_obstacles():
    """Spawn 1–2 obstacles in free lanes, never creating an impossible wall"""
    if not safe_to_spawn():
        return  # skip if next section already fully blocked

    available_lanes = [0, 1, 2]
    active_lanes = {o["lane"] for o in obstacles if o["z"] > 6}
    free_lanes = [l for l in available_lanes if l not in active_lanes and not lane_blocked_in_future(l)]

    if not free_lanes:
        return

    num_to_spawn = min(len(free_lanes), random.choice([1, 1, 2]))  # mostly 1, sometimes 2
    chosen_lanes = random.sample(free_lanes, num_to_spawn)

    for lane in chosen_lanes:
        z_start = random.uniform(10, 16)
        obstacles.append({"lane": lane, "z": z_start, "scored": False})


def reset_game():
    global obstacles, spawn_timer, score, game_over
    obstacles = []
    spawn_timer = 0
    score = 0
    game_over = False


# ============================= GAME LOOP =============================

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if not game_over:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and player_lane > 0:
                    player_lane -= 1
                    lean_target = 15
                elif event.key == pygame.K_RIGHT and player_lane < 2:
                    player_lane += 1
                    lean_target = -15
        else:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                reset_game()

    if not game_over:
        # Smooth lane slide
        lane_target = player_lane
        spread_factor = max_lane_offset
        lane_offsets = [-spread_factor, 0, spread_factor]
        target_x = int(center_x + lane_offsets[lane_target])
        prev_x = bike_x_pos
        bike_x_pos += (target_x - bike_x_pos) * 0.1
        move_speed = abs(bike_x_pos - prev_x) * 5

        # Lean recovery
        lean_angle += (lean_target - lean_angle) * 0.1
        lean_target *= 0.9

        # Bobbing
        time += 0.1
        bike_y = bike_y_base + math.sin(time) * 2.5

        # Rotate bike
        bike = pygame.transform.rotate(bike_original, lean_angle)
        bike_rect = bike.get_rect(center=(bike_x_pos, bike_y + bike.get_height() // 2))

        # --- Trail ---
        trail_intensity = min(20 + int(move_speed * 10), 50)
        trail_color = (
            min(255, base_trail_color[0] + trail_intensity),
            base_trail_color[1],
            min(255, base_trail_color[2] + trail_intensity)
        )
        trail.append([bike_rect.centerx, bike_rect.centery, 255, 12 + move_speed, trail_color])
        if len(trail) > 25:
            trail.pop(0)

        # --- Smoke ---
        if random.random() < 0.07:
            smoke_particles.append([
                bike_rect.centerx - 10,
                bike_rect.bottom - 30,
                200, random.randint(6, 12),
                random.uniform(0.5, 1.2)
            ])
        for s in smoke_particles:
            s[1] -= s[4]
            s[2] -= 3
            s[3] += 0.1
        smoke_particles = [s for s in smoke_particles if s[2] > 0]

        # --- Obstacles ---
        spawn_timer += 1
        if spawn_timer > spawn_interval:
            spawn_obstacles()
            spawn_timer = random.randint(60, 90)

        # Move + score + collision
        new_obstacles = []
        for obs in obstacles:
            obs["z"] -= obstacle_speed

            # Scoring — passed safely
            if obs["z"] < 1.5 and not obs["scored"]:
                if obs["lane"] != player_lane:
                    score += 1
                    obs["scored"] = True

            # Collision
            if obs["lane"] == player_lane and 1.5 < obs["z"] < 2.5:
                game_over = True

            if obs["z"] > 1:
                new_obstacles.append(obs)

        obstacles = new_obstacles

        # --- Draw everything ---
        screen.blit(background, (0, 0))

        # Trails
        for t in trail:
            s = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(s, (t[4][0], t[4][1], t[4][2], t[2]), (15, 15), int(t[3]))
            screen.blit(s, (t[0] - 15, t[1] - 15))
            t[2] = max(0, t[2] - 20)

        # Smoke
        for s in smoke_particles:
            surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(surf, (180, 180, 180, int(s[2])), (20, 20), int(s[3]))
            screen.blit(surf, (s[0] - 20, s[1] - 20))

        # Obstacles (draw far → near)
        for obs in sorted(obstacles, key=lambda o: o["z"], reverse=True):
            lane = obs["lane"]
            z = obs["z"]

            scale = 1.8 / z + 0.25
            obs_size = int(base_obstacle_size * scale)
            obs_size = max(20, min(obs_size, max_obstacle_size))
            obs_y = road_y_bottom - (z / 16) * (road_y_bottom - road_y_top)

            spread_factor = min_lane_offset + (max_lane_offset - min_lane_offset) * (1 - z / 16)
            lane_offsets = [-spread_factor, 0, spread_factor]
            obs_x = int(center_x + lane_offsets[lane] - obs_size / 2)

            tilt_angle = (lane - 1) * -5
            rect_surf = pygame.Surface((obs_size, obs_size), pygame.SRCALPHA)
            color = (255, 100 + int(155 * (1 - z / 16)), 100)
            pygame.draw.rect(rect_surf, color, (0, 0, obs_size, obs_size), border_radius=20)
            rect_surf = pygame.transform.rotate(rect_surf, tilt_angle)
            screen.blit(rect_surf, (obs_x, obs_y))

        # Player
        screen.blit(bike, bike_rect.topleft)

        # Score
        score_text = font.render(f"Score: {int(score)}", True, (255, 255, 255))
        screen.blit(score_text, (20, 20))

    else:
        # Game Over
        screen.blit(background, (0, 0))
        msg = font.render("GAME OVER", True, (255, 0, 100))
        msg2 = font.render("Press R to Restart", True, (255, 255, 255))
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 60))
        screen.blit(msg2, (WIDTH // 2 - msg2.get_width() // 2, HEIGHT // 2 + 10))
        score_text = font.render(f"Final Score: {int(score)}", True, (255, 255, 255))
        screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 + 70))

    pygame.display.flip()
    clock.tick(60)
