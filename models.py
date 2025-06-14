from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
import uuid


class Position:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def distance_to(self, other_position) -> float:
        return ((self.x - other_position.x) ** 2 +
                (self.y - other_position.y) ** 2 +
                (self.z - other_position.z) ** 2) ** 0.5

    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y, "z": self.z}


class Dimensions:
    def __init__(self, width: float, depth: float, height: float):
        self.width = width
        self.depth = depth
        self.height = height

    def volume(self) -> float:
        return self.width * self.depth * self.height

    def to_dict(self) -> Dict:
        return {"width": self.width, "depth": self.depth, "height": self.height}


class Container:
    def __init__(self, container_id: str, zone: str, dimensions: Dimensions, position: Position):
        self.id = container_id
        self.zone = zone
        self.dimensions = dimensions
        self.position = position
        self.items: List[Item] = []

    def available_volume(self) -> float:
        used_volume = sum(item.dimensions.volume() for item in self.items)
        return self.dimensions.volume() - used_volume

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "zone": self.zone,
            "dimensions": self.dimensions.to_dict(),
            "position": self.position.to_dict(),
            "items": [item.id for item in self.items],
            "availableVolume": self.available_volume()
        }


class Item:
    def __init__(self, item_id: str, name: str, dimensions: Dimensions,
                 priority: int, expiry_date: datetime, usage_limit: int,
                 preferred_zone: str, weight: float):
        self.id = item_id
        self.name = name
        self.dimensions = dimensions
        self.priority = priority
        self.expiry_date = expiry_date
        self.usage_limit = usage_limit
        self.usage_count = 0
        self.preferred_zone = preferred_zone
        self.weight = weight
        self.container_id: Optional[str] = None
        self.position: Optional[Position] = None

    def is_expired(self, current_date: datetime) -> bool:
        return current_date > self.expiry_date

    def is_wasted(self, current_date: datetime) -> bool:
        return self.is_expired(current_date) or self.usage_count >= self.usage_limit

    def remaining_uses(self) -> int:
        return max(0, self.usage_limit - self.usage_count)

    def use(self) -> bool:
        if self.usage_count < self.usage_limit:
            self.usage_count += 1
            return True
        return False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "dimensions": self.dimensions.to_dict(),
            "priority": self.priority,
            "expiryDate": self.expiry_date.isoformat(),
            "usageLimit": self.usage_limit,
            "usageCount": self.usage_count,
            "preferredZone": self.preferred_zone,
            "weight": self.weight,
            "containerId": self.container_id,
            "position": self.position.to_dict() if self.position else None
        }


class LogEntry:
    def __init__(self, action: str, item_id: str, user_id: str, timestamp: datetime = None):
        self.id = str(uuid.uuid4())
        self.action = action
        self.item_id = item_id
        self.user_id = user_id
        self.timestamp = timestamp or datetime.now()
        self.details: Dict[str, Any] = {}

    def add_detail(self, key: str, value: Any) -> None:
        self.details[key] = value

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "action": self.action,
            "itemId": self.item_id,
            "userId": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


class CargoSystem:
    def __init__(self):
        self.items: Dict[str, Item] = {}
        self.containers: Dict[str, Container] = {}
        self.logs: List[LogEntry] = []
        self.current_date = datetime.now()

    def add_item(self, item: Item) -> None:
        self.items[item.id] = item
        self.log_action("add_item", item.id, "system")

    def add_container(self, container: Container) -> None:
        self.containers[container.id] = container
        self.log_action("add_container", container.id, "system")

    def place_item(self, item_id: str, container_id: str, position: Position) -> bool:
        if item_id not in self.items or container_id not in self.containers:
            return False

        item = self.items[item_id]
        container = self.containers[container_id]

        # Update item location
        item.container_id = container_id
        item.position = position

        # Add item to container
        container.items.append(item)

        self.log_action("place_item", item_id, "system",
                        {"container_id": container_id, "position": position.to_dict()})
        return True

    def retrieve_item(self, item_id: str, user_id: str) -> bool:
        if item_id not in self.items:
            return False

        item = self.items[item_id]

        # Check usage limit
        if not item.use():
            return False

        # If fully used, mark for removal
        if item.remaining_uses() <= 0:
            self.log_action("fully_used", item_id, user_id)

        # Log retrieval
        self.log_action("retrieve", item_id, user_id)
        return True

    def get_waste_items(self) -> List[Item]:
        return [item for item in self.items.values()
                if item.is_wasted(self.current_date)]

    def simulate_day(self, days: int = 1) -> None:
        self.current_date += timedelta(days=days)
        self.log_action("simulate_day", "", "system", {"days": days})

        # Check for newly expired items
        for item in self.items.values():
            if item.is_expired(self.current_date) and not item.is_expired(self.current_date - timedelta(days=days)):
                self.log_action("item_expired", item.id, "system")

    def log_action(self, action: str, item_id: str, user_id: str, details: Dict = None) -> None:
        log_entry = LogEntry(action, item_id, user_id)
        if details:
            for key, value in details.items():
                log_entry.add_detail(key, value)
        self.logs.append(log_entry)

    def get_logs(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[LogEntry]:
        filtered_logs = self.logs

        if start_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_date]

        if end_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_date]

        return filtered_logs
