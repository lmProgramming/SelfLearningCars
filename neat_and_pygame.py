import neat
import os
import pygame as pg
from pygame.math import Vector2
import math
import random
from typing import List
from car import Car

from intersection_math import check_if_intersect
from map_reader import read_map_txt

pg.font.init()

WIDTH = 1280
HEIGHT = 960

PLAYER_ONLY = False
LOAD_MAP = True

GEN = 0

CAR_IMG = pg.image.load(os.path.join("imgs", "car_img.png"))

CAR_WIDTH = CAR_IMG.get_width()
CAR_HEIGHT = CAR_IMG.get_height()

BG_IMG = pg.image.load(os.path.join("imgs", "bg_img.png"))

STAT_FONT = pg.font.SysFont("comic sans", 25)

WHEEL_TURN_SPEED = 3

STARTING_CAR_POSITION = Vector2(450, HEIGHT - 472)

RAY_DISTANCE_KILL = 10

RAY_COUNT = 5
RAY_LENGTH = 100

class AICar(Car):
    def get_desired_movement(self):
        return super().get_desired_movement()


class CarRay:
    def __init__(self, car, additional_angle, base_dist):
        self.car = car
        self.additional_angle = additional_angle
        self.base_dist = base_dist
        self.color = pg.Color(0, 0, 0, 255)

    def get_origin_position(self):
        return self.car.get_centre_position()
    
    def get_end_position(self):
        return self.get_origin_position() + get_position_change_based_on_length_and_angle(-self.car.angle + self.additional_angle, self.base_dist)

    def check_intersection(self, border):
        result = check_if_intersect(self, border)

        hit, x, y = result
        distance = self.base_dist if not hit else Vector2(x, y).distance_to(self.get_origin_position())

        return (hit, x, y, distance)

    def draw(self, win):
        pg.draw.line(win, self.color, self.get_origin_position(), self.get_end_position(), 3)

class Wall:
    def __init__(self, x1, y1, x2, y2, thickness=6):
        self.start_position: Vector2 = Vector2(x1, y1)
        self.end_position: Vector2 = Vector2(x2, y2)
        self.thickness = thickness

    def draw(self, win):
        pg.draw.line(win, (0, 0, 0), self.start_position, self.end_position, self.thickness)

class Gate:
    def __init__(self, num, x1, y1, x2, y2, thickness=6):
        self.start_position: Vector2 = Vector2(x1, y1)
        self.end_position: Vector2 = Vector2(x2, y2)
        self.thickness = thickness
        self.num = num

    def get_centre_position(self):
        return self.start_position + (self.end_position - self.start_position) / 2

    def check_if_inside(self, position):
        if self.start_position.x < self.end_position.x:
            x1 = self.start_position.x
            x2 = self.end_position.x
        else:
            x1 = self.end_position.x
            x2 = self.start_position.x
        
        if self.start_position.y < self.end_position.y:
            y1 = self.start_position.y
            y2 = self.end_position.y
        else:
            y1 = self.end_position.y
            y2 = self.start_position.y

        return position.x > x1 and \
               position.y > y1 and \
               position.x < x2 and \
               position.y < y2

    def draw(self, win):
        pg.draw.line(win, (0, 0, 255), self.start_position, self.end_position, self.thickness)


def draw_line(position, angle, line_length, line_width, color, screen):
    vector = Vector2()
    vector.from_polar((line_length, angle))
    pg.draw.line(screen, color, position, position+vector, line_width)

def get_position_change_based_on_length_and_angle(angle, length):
    delta_y = length * math.cos(math.radians(angle))
    delta_x = length * math.sin(math.radians(angle))

    return Vector2(delta_x, delta_y)

def draw_window(win, cars: List[Car], borders, gates, bg_img, score, gen, debug=False):
    win.blit(bg_img, (0, 0))

    for car in cars:
        car.draw(win)
        if debug:
            for line in car.lines:
                line.draw(win)
            text = STAT_FONT.render(str(int(car.genome.fitness)), True, (255, 255, 255))
            win.blit(text, car.get_centre_position())

    for border in borders:
        border.draw(win)

    for gate in gates:
        gate.draw(win)
        if debug:
            text = STAT_FONT.render(str(gate.num), True, (255, 255, 255))
            win.blit(text, gate.get_centre_position())

    text = STAT_FONT.render("Score: " + str(score), True, (255, 255, 255))
    win.blit(text, (WIDTH - 10 - text.get_width(), 10))

    text = STAT_FONT.render("Gen: " + str(gen), True, (255, 255, 255))
    win.blit(text, (10, 10))

    pg.display.update()


def main(genomes, config):
    global GEN
    GEN += 1
    nets = []
    ges = []
    cars = []

    if LOAD_MAP:
        borders, gates, starting_point = read_map_txt()
    else:
        borders = []
        gates = []
        starting_point = STARTING_CAR_POSITION

    if PLAYER_ONLY:
        new_car = Car(starting_point.x, starting_point.y, random.randrange(-180, 180))
        _, genome = genomes[0]
        genome.fitness = 0
        new_car.genome = genome
        new_car.generate_rays()
        cars.append(new_car)
        
        ges.append(genomes[0][1])
        nets.append(neat.nn.FeedForwardNetwork.create(genomes[0][1], config))
    else:    
        for _, genome in genomes:
            genome.fitness = 0
            ges.append(genome)
            nets.append(neat.nn.FeedForwardNetwork.create(genome, config))
            
            new_car = Car(starting_point.x, starting_point.y, random.randrange(-180, 180))
            new_car.genome = genome
            new_car.generate_rays()
            cars.append(new_car)

    win = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()

    score = 0
    run = True
    frames = 0
    while run:
        clock.tick(60)

        m_x, m_y = pg.mouse.get_pos()
        mouse_pressed = pg.mouse.get_pressed()

        if mouse_pressed[0]:
            print(m_x, ",", m_y)

        keys = pg.key.get_pressed()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                run = False
                pg.quit()
                quit()

        if keys[pg.K_ESCAPE]:
            run = False
            pg.quit()
            quit() 
              
        i = 0
        while i < len(cars):
            neural_net, genome, car = nets[i], ges[i], cars[i]

            refresh_inputs = frames % 4 == 0
            inputs = car.get_line_distances(borders, refresh_inputs) + [random.random()]
            if PLAYER_ONLY:
                outputs = [0.5, 0.5]                    
                if keys[pg.K_w]:
                    outputs[0] += 0.5
                if keys[pg.K_s]:
                    outputs[0] -= 0.5

                if keys[pg.K_a]:
                    outputs[1] -= 0.5

                if keys[pg.K_d]:
                    outputs[1] += 0.5
            else:
                outputs = neural_net.activate(inputs)

            car.move_forward(outputs[0])
            car.steer(outputs[1])    

            if car.check_if_in_next_gate(gates):
                genome.fitness += 10

            genome.fitness += car.speed / 60

            if car.dead:
                genome.fitness -= 10

                nets.pop(i)
                ges.pop(i)
                cars.pop(i)
            else:
                i += 1
                
        for car in cars:
            car.move()

        if len(cars) == 0 or frames > 60 * (10 + GEN):
            run = False     

        draw_window(win, cars, borders, gates, BG_IMG, score, GEN, debug=keys[pg.K_f])

        frames += 1

def run(config_path):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet,
                                neat.DefaultStagnation, config_path)
    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    winner = p.run(main, 500)

    print(winner)


if __name__ == "__main__":    
    with open('config', 'r') as f:
        for line in f:
            if line.startswith("num_inputs"):
                RAY_COUNT = int(line.strip().split(" = ")[1]) - 1

    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config")
    run(config_path)