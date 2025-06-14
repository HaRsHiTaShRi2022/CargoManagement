import random
from typing import List, Tuple, Dict, Any
from app.models import CargoSystem, Item, Container, Position


def calculate_solution_cost(solution, cargo_system, new_items):
    """Calculate cost of a rearrangement solution"""
    cost = 0

    # Count moves
    moves_count = len(solution)
    cost += moves_count * 10  # Base cost per move

    # Check if high-priority items are in preferred zones
    for item_id, container_id, _ in solution:
        item = None

        # Find the item
        if item_id in cargo_system.items:
            item = cargo_system.items[item_id]
        else:
            for new_item in new_items:
                if new_item.id == item_id:
                    item = new_item
                    break

        if not item:
            continue

        container = cargo_system.containers.get(container_id)
        if not container:
            continue

        # Priority alignment
        if item.preferred_zone == container.zone:
            cost -= item.priority * 5  # Reduce cost for good placements
        else:
            cost += (5 - item.priority) * 3  # Increase cost for bad placements

    return cost


def generate_candidate(cargo_system, new_items, alpha=0.3):
    """Generate a candidate solution for GRASP"""
    solution = []

    # Combine existing and new items
    all_items = list(cargo_system.items.values()) + new_items

    # Sort containers by available space (descending)
    containers = sorted(
        cargo_system.containers.values(),
        key=lambda c: c.available_volume(),
        reverse=True
    )

    # Sort items by priority (descending)
    items = sorted(all_items, key=lambda i: i.priority, reverse=True)

    # Greedy randomized construction
    for item in items:
        # Create RCL (Restricted Candidate List)
        rcl = []

        for container in containers:
            # Check if item fits in container
            if (item.dimensions.width <= container.dimensions.width and
                    item.dimensions.height <= container.dimensions.height and
                    item.dimensions.depth <= container.dimensions.depth):

                # Calculate cost of placing item in this container
                cost = 0

                # Zone preference
                if item.preferred_zone == container.zone:
                    cost -= item.priority * 5
                else:
                    cost += (5 - item.priority) * 3

                # Space utilization
                volume_ratio = item.dimensions.volume() / container.dimensions.volume()
                cost += (1 - volume_ratio) * 10

                rcl.append((container, cost))

        if not rcl:
            continue

        # Sort by cost (ascending)
        rcl.sort(key=lambda x: x[1])

        # Select a container from RCL
        cutoff = max(1, int(len(rcl) * alpha))
        selected_container = rcl[random.randint(0, cutoff - 1)][0]

        # Find position in container (simple approach)
        x = random.randint(0, int(selected_container.dimensions.width - item.dimensions.width))
        y = random.randint(0, int(selected_container.dimensions.height - item.dimensions.height))
        z = random.randint(0, int(selected_container.dimensions.depth - item.dimensions.depth))

        position = Position(x, y, z)

        # Add to solution
        solution.append((item.id, selected_container.id, position))

    return solution


def get_neighbors(solution, cargo_system):
    """Generate neighborhood of a solution for Tabu Search"""
    neighbors = []

    # Swap container
    for i in range(len(solution)):
        item_id, _, position = solution[i]

        for container in cargo_system.containers.values():
            if container.id != solution[i][1]:  # Different container
                new_solution = solution.copy()
                new_solution[i] = (item_id, container.id, position)
                neighbors.append(new_solution)

    # Move position
    for i in range(len(solution)):
        item_id, container_id, position = solution[i]
        container = cargo_system.containers.get(container_id)

        if not container:
            continue

        # Generate a few random positions
        for _ in range(3):
            x = random.randint(0, int(container.dimensions.width - 5))
            y = random.randint(0, int(container.dimensions.height - 5))
            z = random.randint(0, int(container.dimensions.depth - 5))

            new_position = Position(x, y, z)

            new_solution = solution.copy()
            new_solution[i] = (item_id, container_id, new_position)
            neighbors.append(new_solution)

    # Swap items
    for i in range(len(solution)):
        for j in range(i + 1, len(solution)):
            new_solution = solution.copy()
            item1, container1, pos1 = solution[i]
            item2, container2, pos2 = solution[j]

            new_solution[i] = (item1, container2, pos2)
            new_solution[j] = (item2, container1, pos1)
            neighbors.append(new_solution)

    return neighbors


def tabu_search(initial_solution, cargo_system, new_items, max_iterations=100, tabu_tenure=10):
    """Tabu search to optimize rearrangements"""
    current_solution = initial_solution
    best_solution = initial_solution
    best_cost = calculate_solution_cost(initial_solution, cargo_system, new_items)

    tabu_list = []

    for iteration in range(max_iterations):
        # Generate neighbors
        neighbors = get_neighbors(current_solution, cargo_system)

        # Evaluate neighbors
        best_neighbor = None
        best_neighbor_cost = float('inf')

        for neighbor in neighbors:
            # Skip if move is in tabu list
            move_signature = str(neighbor)
            if move_signature in tabu_list:
                continue

            cost = calculate_solution_cost(neighbor, cargo_system, new_items)

            # Aspiration criterion - accept tabu move if it's better than best solution
            if cost < best_cost and move_signature in tabu_list:
                best_neighbor = neighbor
                best_neighbor_cost = cost
                break

            if cost < best_neighbor_cost:
                best_neighbor = neighbor
                best_neighbor_cost = cost

        if not best_neighbor:
            break

        # Update current solution
        current_solution = best_neighbor

        # Update best solution
        if best_neighbor_cost < best_cost:
            best_solution = best_neighbor
            best_cost = best_neighbor_cost

        # Update tabu list
        tabu_list.append(str(current_solution))
        if len(tabu_list) > tabu_tenure:
            tabu_list.pop(0)

    return best_solution


def optimize_rearrangement(cargo_system: CargoSystem, new_items: List[Item]):
    """GRASP + Tabu Search for optimal rearrangement"""
    # Use GRASP to construct initial solution
    initial_solution = generate_candidate(cargo_system, new_items)

    # Use Tabu Search to improve solution
    optimized_solution = tabu_search(initial_solution, cargo_system, new_items)

    # Format the solution
    rearrangements = []
    for item_id, container_id, position in optimized_solution:
        rearrangements.append((item_id, container_id, position))

    return rearrangements
