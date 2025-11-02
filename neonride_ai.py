import pygame
import math
import random
import os

WIDTH, HEIGHT = 768, 1024

class NeonRideAI:
    def __init__(self, render=False):
        pygame.init()
        self.render = render

        if self.render:
            os.environ["SDL_VIDEO_WINDOW_POS"] = "100,100"
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            pygame.display.set_caption("Neon Ride AI")
        else:
            self.screen = pygame.Surface((WIDTH, HEIGHT))

        self.clock = pygame.time.Clock()

        # Load assets
        self.background = pygame.image.load("80s_synth_background.png")
        self.bike_original = pygame.image.load("bike.png")
        if self.render:
            self.background = self.background.convert()
            self.bike_original = self.bike_original.convert_alpha()
        self.background = pygame.transform.scale(self.background, (WIDTH, HEIGHT))
        self.bike_original = pygame.transform.scale(self.bike_original, (200, 200))

        self.obstacle_images = [
            pygame.image.load("car_obstacle.png"),
            pygame.image.load("car2_obstacle.png"),
            pygame.image.load("random_obstacle.png"),
            pygame.image.load("barrel_obstacle.png")
        ]
        if self.render:
            self.obstacle_images = [img.convert_alpha() for img in self.obstacle_images]


        self.center_x = WIDTH // 2
        self.road_y_bottom = HEIGHT - 150
        self.road_y_top = 300
        self.max_lane_offset = 180
        self.min_lane_offset = 40
        self.obstacle_speed = 0.1

        self.reset()

    # ---------------- RESET ----------------
    def reset(self):
        self.lanes = [0, 1, 2]
        self.player_lane = 1
        self.time = 0
        self.obstacles = []
        self.spawn_timer = 0
        self.spawn_interval = 75
        self.done = False
        return self.get_state()

    # ---------------- SAFE SPAWN ----------------
    def lane_blocked_in_future(self, lane, z_distance=3):
        for o in self.obstacles:
            if o["lane"] == lane and 16 - z_distance < o["z"] < 16:
                return True
        return False

    def safe_to_spawn(self):
        too_close = any(6 < o["z"] < 9 for o in self.obstacles)
        if too_close:
            return False
        lanes_blocked = {o["lane"] for o in self.obstacles if 2 < o["z"] < 6}
        return len(lanes_blocked) < 3

    def spawn_obstacles(self):
        if not self.safe_to_spawn():
            return
        available_lanes = [0, 1, 2]
        active_lanes = {o["lane"] for o in self.obstacles if o["z"] > 6}
        free_lanes = [l for l in available_lanes if l not in active_lanes and not self.lane_blocked_in_future(l)]
        if not free_lanes:
            return
        num_to_spawn = min(len(free_lanes), random.choice([1, 1, 2]))
        chosen_lanes = random.sample(free_lanes, num_to_spawn)
        for lane in chosen_lanes:
            z_start = random.uniform(6, 11)
            img = random.choice(self.obstacle_images)
            self.obstacles.append({"lane": lane, "z": z_start, "scored": False, "image": img})

    # ---------------- STATE ----------------
    def get_state(self):
        lane_distances = [10] * 3
        for obs in self.obstacles:
            if obs["z"] > 1.2:
                lane_distances[obs["lane"]] = min(lane_distances[obs["lane"]], obs["z"])

        closest = sorted(self.obstacles, key=lambda o: o["z"])[:5]
        extra = [o["lane"] for o in closest]
        distances = [o["z"] for o in closest]

        padding = [0] * (5 - len(extra))
        distance_padding = [10] * (5 - len(distances))

        # Normalize & invert distances
        lane_distances = [max(0, min(1, 1 - (d / 10))) for d in lane_distances]
        extra = [e / 2 for e in extra]
        distances = [max(0, min(1, 1 - (d / 10))) for d in distances]

        return lane_distances + extra + distances + padding + distance_padding + [self.player_lane / 2]

    # ---------------- STEP ----------------
    def step(self, action):
        if self.done:
            return self.get_state(), 0, True

        # Movement
        if action == 1 and self.player_lane > 0:
            self.player_lane -= 1
        elif action == 2 and self.player_lane < 2:
            self.player_lane += 1

        self.spawn_timer += 1
        if self.spawn_timer > self.spawn_interval:
            self.spawn_obstacles()
            self.spawn_timer = random.randint(60, 90)

        new_obstacles = []
        reward = 0.05  # survival reward

        for obs in self.obstacles:
            obs["z"] -= self.obstacle_speed

            # Gradual danger awareness
            lane_diff = abs(obs["lane"] - self.player_lane)
            if obs["z"] < 5:
                if lane_diff == 0:
                    reward -= (5 - obs["z"]) * 0.5
                else:
                    reward += 0.05

            # Passing safely
            if obs["z"] < 1.5 and not obs["scored"]:
                if obs["lane"] != self.player_lane:
                    reward += 5
                    obs["scored"] = True

            # Collision
            if obs["lane"] == self.player_lane and 1.5 < obs["z"] < 2.5:
                reward -= 10
                self.done = True

            if obs["z"] > 1:
                new_obstacles.append(obs)

        self.obstacles = new_obstacles

        if self.render:
            self.render_frame()

        return self.get_state(), reward, self.done

    # ---------------- RENDER ----------------
    def render_frame(self):
        self.screen.blit(self.background, (0, 0))

        for obs in sorted(self.obstacles, key=lambda o: o["z"], reverse=True):
            lane = obs["lane"]
            z = obs["z"]
            img = obs["image"]
            scale = 1.8 / z + 0.25
            size = int(160 * scale)
            size = max(20, min(size, 260))
            img_scaled = pygame.transform.smoothscale(img, (size, size))
            obs_y = self.road_y_bottom - (z / 16) * (self.road_y_bottom - self.road_y_top)
            spread_factor = self.min_lane_offset + (self.max_lane_offset - self.min_lane_offset) * (1 - z / 16)
            lane_offsets = [-spread_factor, 0, spread_factor]
            obs_x = int(self.center_x + lane_offsets[lane] - size / 2)
            self.screen.blit(img_scaled, (obs_x, obs_y))

        spread_factor = self.max_lane_offset
        lane_offsets = [-spread_factor, 0, spread_factor]
        bike_x = int(self.center_x + lane_offsets[self.player_lane] - 100)
        bike_y = HEIGHT - 250
        self.screen.blit(self.bike_original, (bike_x, bike_y))

        pygame.display.flip()
        self.clock.tick(60)
        pygame.event.pump()
