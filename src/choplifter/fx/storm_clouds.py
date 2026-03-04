import pygame
import random
from typing import List, Tuple

class StormCloud:
    def __init__(self, x, y, speed, layer, size, flash_timer=0.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.layer = layer  # 'back' or 'front'
        self.size = size  # (w, h)
        self.flash_timer = flash_timer
        self.flash_on = False
        self.oval_offsets = self._generate_ovals()

    def _generate_ovals(self):
        # Each cloud is made of several overlapping ovals
        count = random.randint(3, 7)
        offsets = []
        for _ in range(count):
            ox = random.randint(-self.size[0]//3, self.size[0]//3)
            oy = random.randint(-self.size[1]//4, self.size[1]//4)
            rw = random.randint(self.size[0]//2, self.size[0])
            rh = random.randint(self.size[1]//2, self.size[1])
            offsets.append((ox, oy, rw, rh))
        return offsets

    def update(self, dt, screen_w):
        self.x -= self.speed * dt
        if self.x < -self.size[0]:
            self.x = screen_w + self.size[0]
            self.y = random.randint(40, screen_w//2)
        if self.flash_timer > 0:
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.flash_on = False
        elif random.random() < 0.002:
            self.flash_on = True
            self.flash_timer = random.uniform(0.08, 0.18)

    def draw(self, surface):
        base_color = (40, 40, 50) if not self.flash_on else (180, 180, 200)
        alpha = 180 if not self.flash_on else 220
        for ox, oy, rw, rh in self.oval_offsets:
            cloud_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
            pygame.draw.ellipse(cloud_surf, (*base_color, alpha), (0, 0, rw, rh))
            surface.blit(cloud_surf, (int(self.x + ox - rw//2), int(self.y + oy - rh//2)))

class StormCloudSystem:
    def __init__(self, screen_w, screen_h, n_back=5, n_front=3):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.clouds: List[StormCloud] = []
        # Back layer clouds
        for _ in range(n_back):
            x = random.randint(0, screen_w)
            y = random.randint(40, int(screen_h * 0.5))
            speed = random.uniform(30, 60)
            size = (random.randint(120, 220), random.randint(40, 90))
            self.clouds.append(StormCloud(x, y, speed, 'back', size))
        # Front layer clouds
        for _ in range(n_front):
            x = random.randint(0, screen_w)
            y = random.randint(int(screen_h * 0.55), int(screen_h * 0.8))
            speed = random.uniform(60, 110)
            size = (random.randint(140, 260), random.randint(60, 120))
            self.clouds.append(StormCloud(x, y, speed, 'front', size))

    def update(self, dt):
        for c in self.clouds:
            c.update(dt, self.screen_w)

    def draw(self, surface, layer):
        for c in self.clouds:
            if c.layer == layer:
                c.draw(surface)
