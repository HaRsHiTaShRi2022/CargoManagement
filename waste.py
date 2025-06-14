from typing import List, Dict, Any
from app.models import Item


def calculate_disposal_priority(item: Item) -> float:
    """Calculate disposal priority of an item"""
    # Items that are more expired or more used should have higher priority
    expiry_priority = 0

    if item.is_expired:
        days_expired = (item.expiry_date - item.current_date).days
        expiry_priority = max(0, -days_expired) * 5

    usage_priority = (item.usage_count / max(1, item.usage_limit)) * 10

    # Combine with item's priority (lower priority items should be disposed first)
    return expiry_priority + usage_priority + (6 - item.priority) * 20


def knapsack_01(items: List[Item], max_weight: float, max_volume: float):
    """0-1 Knapsack algorithm using dynamic programming"""
    n = len(items)

    # Discretize weight and volume
    weight_scale = 100 / max_weight if max_weight > 0 else 1
    volume_scale = 100 / max_volume if max_volume > 0 else 1

    scaled_weights = [max(1, int(item.weight * weight_scale)) for item in items]
    scaled_volumes = [max(1, int(item.dimensions.volume() * volume_scale)) for item in items]

    max_scaled_weight = sum(scaled_weights)
    max_scaled_volume = sum(scaled_volumes)

    # If we can fit all items, return them all
    if sum(item.weight for item in items) <= max_weight and sum(
            item.dimensions.volume() for item in items) <= max_volume:
        return items

    # Create DP table
    dp = {}

    def knapsack_recursive(idx, remaining_weight, remaining_volume):
        if idx == n:
            return 0, []

        # Check if we've already computed this state
        key = (idx, remaining_weight, remaining_volume)
        if key in dp:
            return dp[key]

        # Skip this item
        skip_value, skip_items = knapsack_recursive(idx + 1, remaining_weight, remaining_volume)

        # Take this item if possible
        take_value, take_items = 0, []
        if scaled_weights[idx] <= remaining_weight and scaled_volumes[idx] <= remaining_volume:
            sub_value, sub_items = knapsack_recursive(
                idx + 1,
                remaining_weight - scaled_weights[idx],
                remaining_volume - scaled_volumes[idx]
            )
            take_value = calculate_disposal_priority(items[idx]) + sub_value
            take_items = [items[idx]] + sub_items

        # Choose better option
        if take_value > skip_value:
            dp[key] = (take_value, take_items)
        else:
            dp[key] = (skip_value, skip_items)

        return dp[key]

    _, selected_items = knapsack_recursive(0, max_scaled_weight, max_scaled_volume)

    # Double-check weight and volume constraints
    total_weight = sum(item.weight for item in selected_items)
    total_volume = sum(item.dimensions.volume() for item in selected_items)

    if total_weight > max_weight or total_volume > max_volume:
        # If constraints are violated, sort by disposal priority and take items until limit
        sorted_items = sorted(items, key=lambda x: calculate_disposal_priority(x), reverse=True)
        selected_items = []
        current_weight = 0
        current_volume = 0

        for item in sorted_items:
            if current_weight + item.weight <= max_weight and current_volume + item.dimensions.volume() <= max_volume:
                selected_items.append(item)
                current_weight += item.weight
                current_volume += item.dimensions.volume()

    return selected_items


def optimize_waste_return(waste_items: List[Item], max_capacity: Dict[str, float]):
    """Use 0-1 Knapsack to optimize waste return"""
    max_weight = max_capacity.get("weight", float('inf'))
    max_volume = max_capacity.get("volume", float('inf'))

    # Use knapsack algorithm to select optimal items for disposal
    selected_items = knapsack_01(waste_items, max_weight, max_volume)

    return selected_items
