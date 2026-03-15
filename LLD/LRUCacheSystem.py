# fmt: off
# ==============================================================================
#  LRU CACHE SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │                            LRU CACHE SYSTEM                             │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐
#  │        LRUCache         │  ← Manages both Data Structures
#  ├─────────────────────────┤
#  │ + capacity: int         │
#  │ + hash_map: Dict[K, Node]
#  │ + list: DoublyLinkedList│
#  ├─────────────────────────┤
#  │ + get(key)              │
#  │ + set(key, value)       │
#  │ + print_cache()         │
#  └─────────────────────────┘
#            │          │
#        ....│..........│....
#        .   ▼          ▼   .
#  ┌──────────────┐  ┌──────────────────────────┐
#  │  Dictionary  │  │    DoublyLinkedList      │
#  │  (Hash Map)  │  ├──────────────────────────┤
#  ├──────────────┤  │ + head: Node (MRU)       │
#  │ K -> Node    │  │ + tail: Node (LRU)       │
#  │    O(1)      │  ├──────────────────────────┤
#  └──────────────┘  │ + add_node_to_head()     │
#                    │ + remove_node()          │
#                    │ + move_to_head()         │
#                    │ + pop_tail()             │
#                    └──────────────────────────┘
#                                 │
#                                 ▼
#                    ┌──────────────────────────┐
#                    │           Node           │
#                    ├──────────────────────────┤
#                    │ + key: K                 │
#                    │ + value: V               │
#                    │ + prev: Node             │
#                    │ + next: Node             │
#                    └──────────────────────────┘
#
#  RELATIONSHIPS & TIME COMPLEXITY:
#  LRUCache ──1──> DoublyLinkedList             (maintains order of usage)
#  LRUCache ──1──> Hash Map                     (maintains fast lookups)
#  get(): O(1) Hash Map lookup + O(1) DLL move_to_head
#  set(): O(1) Hash Map insertion + O(1) DLL add/evict
#
#  MEMORY LAYOUT:
#  [Head(MRU)] <-> [Node] <-> [Node] <-> [Tail(LRU)]
# ==============================================================================
# fmt: on

import threading
from typing import Any, Dict, Optional

"""
==============================================================================================
LRU CACHE LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. True O(1) Time Complexity for Get and Put Operations using HashMap + DoublyLinkedList.
2. Eviction policy for Least Recently Used items when reaching capacity.
3. Thread Safety using RLock for atomic operations.
4. Clean separation of concerns between standard Cache API and internal DLL mechanics.

Design Patterns:
1. Combination of Data Structures: Hash Map for O(1) lookup. Doubly Linked List for 
   O(1) sequence rearrangements (unlike an array which takes O(N) to shift).
"""

# ==========================================
# Internal Data Structures
# ==========================================

class Node:
    """Represents a node in the Doubly Linked List."""
    def __init__(self, key: Any = None, value: Any = None):
        self.key = key
        self.value = value
        self.prev: Optional['Node'] = None
        self.next: Optional['Node'] = None

    def __repr__(self):
        return f"[{self.key}:{self.value}]"


class DoublyLinkedList:
    """Manages the chronological ordering of the LRU cache."""
    def __init__(self):
        # Dummy head and tail to avoid edge cases during insertions/deletions
        self.head = Node()
        self.tail = Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def add_node_to_head(self, node: Node):
        """Always add the new node right after the dummy head (Most Recently Used)."""
        node.prev = self.head
        node.next = self.head.next
        
        self.head.next.prev = node
        self.head.next = node

    def remove_node(self, node: Node):
        """Remove an existing node from the linked list."""
        prev_node = node.prev
        next_node = node.next
        
        if prev_node:
            prev_node.next = next_node
        if next_node:
            next_node.prev = prev_node

    def move_to_head(self, node: Node):
        """Move an existing node to the MRU position (head)."""
        self.remove_node(node)
        self.add_node_to_head(node)

    def pop_tail(self) -> Optional[Node]:
        """Pop the Least Recently Used node (right before dummy tail)."""
        res = self.tail.prev
        if res == self.head:
            return None # List is empty
        self.remove_node(res)
        return res


# ==========================================
# Core Cache Domain
# ==========================================

class LRUCache:
    """The LRU Cache containing a hash map for lookups and a DLL for ordering."""
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than 0")
            
        self.capacity = capacity
        self.size = 0
        self.cache: Dict[Any, Node] = {}
        self.dll = DoublyLinkedList()
        self._lock = threading.RLock() # Reentrant lock for thread safety

    def get(self, key: Any) -> Any:
        with self._lock:
            # 1. Lookup in Hash Map
            node = self.cache.get(key)
            
            if not node:
                return -1 # Or raise KeyError / return None depending on requirements
            
            # 2. Node exists, so it's recently used! Move to head of DLL.
            self.dll.move_to_head(node)
            return node.value

    def put(self, key: Any, value: Any):
        with self._lock:
            node = self.cache.get(key)

            # Case 1: Key already exists. Update value and move to head (MRU).
            if node:
                node.value = value
                self.dll.move_to_head(node)
            
            # Case 2: Key does not exist. We need to create it.
            else:
                new_node = Node(key, value)
                self.cache[key] = new_node
                self.dll.add_node_to_head(new_node)
                self.size += 1

                # If we breached capacity, we must evict the LRU element (the tail)
                if self.size > self.capacity:
                    lru_node = self.dll.pop_tail()
                    if lru_node:
                        del self.cache[lru_node.key]
                        self.size -= 1
                        print(f"INFO: Evicted LRU key [{lru_node.key}]")

    def __repr__(self):
        with self._lock:
            items = []
            curr = self.dll.head.next
            while curr != self.dll.tail:
                items.append(f"{curr.key}:{curr.value}")
                curr = curr.next
            return "Head(MRU) -> " + " <-> ".join(items) + " <- Tail(LRU)"


# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting LRU Cache System Demo ---")
    
    # Init cache of capacity 3
    lru = LRUCache(3)
    print("Capacity: 3")
    
    print("\n[Action] Put (1: A), (2: B), (3: C)")
    lru.put(1, "A")
    lru.put(2, "B")
    lru.put(3, "C")
    print(lru)
    
    print("\n[Action] Get (1)")
    # '1' becomes MRU
    val = lru.get(1)
    print(f"Result: {val}")
    print(lru)
    
    print("\n[Action] Put (4: D) (Should evict LRU)")
    # '2' is currently LRU, so it gets evicted
    lru.put(4, "D")
    print(lru)
    
    print("\n[Action] Get (2)")
    # Should not be found
    val = lru.get(2)
    print(f"Result: {val}")
    
    print("\n[Action] Put (3: E) (Update existing key)")
    # '3' is updated to E, becomes MRU
    lru.put(3, "E")
    print(lru)
