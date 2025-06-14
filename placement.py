import numpy as np
import random
from typing import List, Tuple, Dict, Any
from app.models import Item, Container, Position


class GuilotineBin:
    def __init__(self, width, height, depth):
        self.width = width
        self.height = height
        self.depth = depth
        self.used_space = []
        self.free_rects = [(0, 0, 0, width, height, depth)]

    def insert(self, item_width, item_height, item_depth) -> Tuple[bool, int, int, int]:
        """Find position for item using Guillotine Cut algorithm"""
        best_rect_index = -1
        best_x, best_y, best_z = 0, 0, 0

        # Find best fit rectangle
        min_waste = float('inf')
        for i, (x, y, z, w, h, d) in enumerate(self.free_rects):
            if w >= item_width and h >= item_height and d >= item_depth:
                waste = w * h * d - item_width * item_height * item_depth
                if waste < min_waste:
                    best_rect_index = i
                    best_x, best_y, best_z = x, y, z
                    min_waste = waste

        if best_rect_index == -1:
            return False, 0, 0, 0

        # Split free rectangle
        x, y, z, w, h, d = self.free_rects[best_rect_index]
        self.free_rects.pop(best_rect_index)

        # Add item to used space
        self.used_space.append((best_x, best_y, best_z, item_width, item_height, item_depth))

        # Split remaining space (6 possible splits in 3D)
        if w > item_width:
            self.free_rects.append((x + item_width, y, z, w - item_width, item_height, item_depth))
        if h > item_height:
            self.free_rects.append((x, y + item_height, z, item_width, h - item_height, item_depth))
        if d > item_depth:
            self.free_rects.append((x, y, z + item_depth, item_width, item_height, d - item_depth))
        if w > item_width and h > item_height:
            self.free_rects.append((x + item_width, y + item_height, z, w - item_width, h - item_height, item_depth))
        if w > item_width and d > item_depth:
            self.free_rects.append((x + item_width, y, z + item_depth, w - item_width, item_height, d - item_depth))
        if h > item_height and d > item_depth:
            self.free_rects.append((x, y + item_height, z + item_depth, item_width, h - item_height, d - item_depth))

        return True, best_x, best_y, best_z


def fitness_function(placement_solution, containers, items, zones_priority):
    """Calculate fitness of a placement solution"""
    # Evaluate based on:
    # 1. Space utilization
    # 2. Priority items in preferred zones
    # 3. Items with similar expiry dates grouped together
    # 4. Access difficulty minimized for high-priority items

    total_score = 0
    space_utilization = 0
    priority_score = 0
    expiry_score = 0
    access_score = 0

    for item_idx, (container_idx, x, y, z) in enumerate(placement_solution):
        if container_idx >= len(containers):
            # Invalid placement
            return -1000

        item = items[item_idx]
        container = containers[container_idx]

        # Check if item fits
        if (x + item.dimensions.width > container.dimensions.width or
                y + item.dimensions.height > container.dimensions.height or
                z + item.dimensions.depth > container.dimensions.depth):
            return -1000  # Invalid placement

        # Zone preference score
        if item.preferred_zone == container.zone:
            priority_score += item.priority * 10

        # Access score - items closer to the entrance (assumed to be at 0,0,0) are more accessible
        distance = (x + y + z) ** 0.5
        access_score += (1.0 / (distance + 1)) * item.priority

        # Calculate overlapping with other items
        for other_idx, (other_container_idx, ox, oy, oz) in enumerate(placement_solution):
            if item_idx != other_idx and container_idx == other_container_idx:
                other_item = items[other_idx]

                # Check for overlap
                if (x < ox + other_item.dimensions.width and x + item.dimensions.width > ox and
                        y < oy + other_item.dimensions.height and y + item.dimensions.height > oy and
                        z < oz + other_item.dimensions.depth and z + item.dimensions.depth > oz):
                    return -2000  # Invalid - overlapping items

                # Expiry grouping score
                days_diff = abs((item.expiry_date - other_item.expiry_date).days)
                if days_diff < 30:  # Items expiring within a month of each other
                    expiry_score += 5

        # Space utilization - reward compact placements
        space_utilization += item.dimensions.volume() / container.dimensions.volume()

    # Combine scores with weights
    total_score = (
            space_utilization * 100 +
            priority_score * 50 +
            expiry_score * 20 +
            access_score * 30
    )

    return total_score


def crossover(parent1, parent2):
    """Perform crossover between two parent solutions"""
    if not parent1 or not parent2:
        return parent1 or parent2

    # Single point crossover
    crossover_point = random.randint(1, len(parent1) - 1)
    child = parent1[:crossover_point] + parent2[crossover_point:]
    return child


def mutate(solution, containers, mutation_rate=0.1):
    """Mutate a solution with a given probability"""
    mutated = solution.copy()

    for i in range(len(mutated)):
        if random.random() < mutation_rate:
            # Change container or position
            container_idx = random.randint(0, len(containers) - 1)
            container = containers[container_idx]

            x = random.randint(0, int(container.dimensions.width - 5))
            y = random.randint(0, int(container.dimensions.height - 5))
            z = random.randint(0, int(container.dimensions.depth - 5))

            mutated[i] = (container_idx, x, y, z)

    return mutated


def genetic_algorithm(containers, items, population_size=50, generations=100):
    """Genetic algorithm for optimizing placement"""
    # Initialize population with guillotine cut solutions and random placements
    population = []

    # Add guillotine cut solutions
    for _ in range(population_size // 2):
        solution = []
        remaining_items = items.copy()
        random.shuffle(remaining_items)

        for item in remaining_items:
            placed = False
            for c_idx, container in enumerate(containers):
                bin = GuilotineBin(
                    container.dimensions.width,
                    container.dimensions.height,
                    container.dimensions.depth
                )

                # Try to place items that are already in the container
                for i, existing_item in enumerate(solution):
                    container_idx, x, y, z = existing_item
                    if container_idx == c_idx:
                        existing = items[i]
                        bin.insert(
                            existing.dimensions.width,
                            existing.dimensions.height,
                            existing.dimensions.depth
                        )

                # Try to place the new item
                success, x, y, z = bin.insert(
                    item.dimensions.width,
                    item.dimensions.height,
                    item.dimensions.depth
                )

                if success:
                    solution.append((c_idx, x, y, z))
                    placed = True
                    break

            if not placed:
                # Try to place in any container with available space
                for c_idx, container in enumerate(containers):
                    x = random.randint(0, int(container.dimensions.width - item.dimensions.width))
                    y = random.randint(0, int(container.dimensions.height - item.dimensions.height))
                    z = random.randint(0, int(container.dimensions.depth - item.dimensions.depth))
                    solution.append((c_idx, x, y, z))
                    break

        population.append(solution)

    # Add random solutions
    for _ in range(population_size - len(population)):
        solution = []
        for _ in range(len(items)):
            c_idx = random.randint(0, len(containers) - 1)
            container = containers[c_idx]
            x = random.randint(0, int(container.dimensions.width - 5))
            y = random.randint(0, int(container.dimensions.height - 5))
            z = random.randint(0, int(container.dimensions.depth - 5))
            solution.append((c_idx, x, y, z))
        population.append(solution)

    # Define zone priorities
    zones_priority = {"A": 3, "B": 2, "C": 1}

    # Evolution loop
    for generation in range(generations):
        # Evaluate fitness
        fitness_scores = [
            fitness_function(solution, containers, items, zones_priority)
            for solution in population
        ]

        # Select parents using tournament selection
        def tournament_selection(k=3):
            indices = random.sample(range(len(population)), k)
            return population[max(indices, key=lambda i: fitness_scores[i])]

        # Create new population
        new_population = []

        # Elitism - keep the best solution
        elite_idx = fitness_scores.index(max(fitness_scores))
        new_population.append(population[elite_idx])

        # Generate rest of the new population
        while len(new_population) < population_size:
            parent1 = tournament_selection()
            parent2 = tournament_selection()

            child = crossover(parent1, parent2)
            child = mutate(child, containers)

            new_population.append(child)

        population = new_population

    # Return the best solution
    fitness_scores = [
        fitness_function(solution, containers, items, zones_priority)
        for solution in population
    ]
    best_idx = fitness_scores.index(max(fitness_scores))

    return population[best_idx]


def hybrid_placement(containers, items):
    """Combines Guillotine Cut with Genetic Algorithm for optimal placement"""
    # Sort items by priority (descending)
    sorted_items = sorted(items, key=lambda x: x.priority, reverse=True)

    # Use genetic algorithm for placement
    placement_solution = genetic_algorithm(containers, sorted_items)

    # Convert solution to returnable format
    placements = []
    rearrangements = []

    for i, (container_idx, x, y, z) in enumerate(placement_solution):
        item = sorted_items[i]
        container = containers[container_idx]
        position = Position(x, y, z)

        placements.append((item, container.id, position))

    return placements, rearrangements
