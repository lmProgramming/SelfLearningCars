import pygame as pg
from pygame.key import ScancodeWrapper
from pygame.math import Vector2
import math
from typing import List
import os
from abc import ABC, abstractmethod
from neat import DefaultGenome
from cars.car_ray import CarRay
from neat.nn import FeedForwardNetwork

CAR_IMG = pg.image.load(os.path.join("imgs", "car_img.png"))

CAR_WIDTH = CAR_IMG.get_width()
CAR_HEIGHT = CAR_IMG.get_height()

RAY_DISTANCE_KILL = 10

WHEEL_TURN = 60
WHEEL_TURN_SPEED = 3    

ACCELERATION = 0.3
BACK_ACCELERATION_MULTIPLIER = 0.3

class Car(ABC):
    def __init__(self, x, y, starting_angle: float) -> None:
        self.position = Vector2(x, y)
        self.angle: float = starting_angle
        self._speed = 0
        self.rays: List[CarRay] = []
        self.last_gate: int
        self.direction: int = 0
        self.rect: pg.Rect = pg.Rect(x, y, CAR_WIDTH, CAR_HEIGHT)
        
    def _next_gate_index(self, gates) -> int:
        return ((self.last_gate) + self.direction) % len(gates)

    def check_if_in_next_gate(self, gates) -> bool:
        if self.direction == 0:
            return self._check_if_in_gate(gates, 0, dir=1) or self._check_if_in_gate(gates, -1, dir=-1)
        return self._check_if_in_gate(gates, self._next_gate_index(gates), self.direction)

    def _check_if_in_gate(self, gates, gate_num, dir) -> bool:
        gate = gates[gate_num]

        if gate.check_if_inside(self.get_centre_position()):
            if self.direction == 0:
                self.direction = dir
            self.last_gate = gate.num
            return True
        return False
    
    def get_shortest_last_distance(self) -> float:
        return min([line.last_distance for line in self.rays])            

    def calculate_line_distances(self, walls) -> None:      
        for ray in self.rays:
            lowest_distance: float = ray.length
            closest_point: Vector2 | None = None
            for wall in walls:
                _, point, distance = ray.find_distance_to_wall(wall)
                if distance < lowest_distance:                    
                    lowest_distance = distance
                    closest_point = point
                                                
            ray.set_last_distance(lowest_distance)                            
            ray.set_last_point(closest_point)          
            
    def calculate_line_distances_quick(self, walls) -> None:      
        for ray in self.rays:
            lowest_distance: float
            closest_point: Vector2 | None
            closest_point, lowest_distance = ray.find_distance_to_walls_quick(walls)
                                                
            ray.set_last_distance(lowest_distance)  
            
            ray.set_last_point(closest_point)
    
    @abstractmethod    
    def get_reward(self, reward: float):
        ...
        
    @abstractmethod            
    def get_score(self):
        ...
    
    def check_if_hit_wall(self):
        if min([line.last_distance for line in self.rays]) < RAY_DISTANCE_KILL:
            self.die()
    
    @abstractmethod
    def get_desired_movement(self) -> Vector2:
        ...

    def get_centre_position(self):
        return self.position + Vector2(CAR_WIDTH / 2, CAR_HEIGHT / 2)

    def move_forward(self, force):
        normalized_force = force * 2 - 1

        self._speed += normalized_force * ACCELERATION * (1 if force >= 0 else BACK_ACCELERATION_MULTIPLIER)

    def generate_rays(self, ray_count, ray_length, processing_function) -> None:
        for i in range(0, 360, 360 // ray_count):
            self.rays.append(CarRay(self, i, ray_length, processing_function))
            
    def _calculate_wheel_turn_coefficient(self):
        return math.sqrt(abs(self._speed))

    def steer(self, way):
        wheel_turn_coefficient = self._calculate_wheel_turn_coefficient()

        if way < 0.5:
            self.angle -= WHEEL_TURN_SPEED * (0.5 - way) * wheel_turn_coefficient * (1 if self._speed >= 0 else -1)
        if way > 0.5:
            self.angle += WHEEL_TURN_SPEED * (way - 0.5) * wheel_turn_coefficient * (1 if self._speed >= 0 else -1)

    def move(self):
        self._speed *= 0.94

        if self.angle < -180:
            self.angle = 180
        if self.angle > 180:
            self.angle = -180
        
        delta_y = -self._speed * math.cos(math.radians(self.angle))
        delta_x = self._speed * math.sin(math.radians(self.angle))

        self.position += Vector2(delta_x, delta_y)

    def check_intersections(self, walls):
        ...

    def draw(self, win):
        rotated_image = pg.transform.rotate(CAR_IMG, -self.angle)
        self.rect = rotated_image.get_rect(center=CAR_IMG.get_rect(topleft=(self.position.x, self.position.y)).center)
        win.blit(rotated_image, self.rect.topleft)
        
class AICar(Car):    
    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.genome: DefaultGenome
        self.neural_net: FeedForwardNetwork
        
    def set_neural_net(self, neural_net):
        self.neural_net = neural_net
    
    def get_desired_movement(self) -> Vector2:      
        inputs: List[float] = [ray.last_distance for ray in self.rays] + [self._speed, self._calculate_wheel_turn_coefficient()]
        outputs = self.neural_net.activate(inputs)
        
        return outputs
    
    def get_reward(self, reward: float):
        self.genome.fitness += reward
        
    def get_score(self):
        return self.genome.fitness
    
class HumanCar(Car):
    def __init__(self, *args):
        super().__init__(*args)
        self._score = 0
        
    def get_desired_movement(self) -> Vector2:
        keys: ScancodeWrapper = pg.key.get_pressed()
        
        outputs = Vector2(0.5, 0.5)                    
        if keys[pg.K_w]:
            outputs.x += 0.5
        if keys[pg.K_s]:
            outputs.x -= 0.5

        if keys[pg.K_a]:
            outputs.y -= 0.5
        if keys[pg.K_d]:
            outputs.y += 0.5
            
        return outputs
    
    def get_reward(self, reward: float) -> None:            
        self._score += reward
    
    def get_score(self) -> int:
        return self._score
        