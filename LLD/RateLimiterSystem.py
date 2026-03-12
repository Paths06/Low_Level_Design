# fmt: off
# ==============================================================================
#  RATE LIMITER SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                    IN-MEMORY RATE LIMITER SYSTEM                         │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────────────────────────────────────────┐
#  │                    RateLimiter (Facade)                     │
#  ├─────────────────────────────────────────────────────────────┤
#  │ + rules: Dict[endpoint, RateLimitRule]                      │
#  │ + limiters: Dict[(endpoint,client_id), RateLimitAlgorithm]  │
#  ├─────────────────────────────────────────────────────────────┤
#  │ + add_rule(endpoint, limit, window_secs, algorithm_type)    │
#  │ + allow_request(endpoint, client_id): bool                  │
#  │ - _create_limiter(rule): RateLimitAlgorithm                 │
#  └──────────────────────────────┬──────────────────────────────┘
#                                 │ creates & manages
#                                 ▼
#  ┌─────────────────────────────────────────────────────────────┐
#  │              RateLimitAlgorithm (ABC)                       │
#  ├─────────────────────────────────────────────────────────────┤
#  │ + allow_request(): bool                                     │
#  └──────────────────────────┬──────────────────────────────────┘
#                             │
#          ┌──────────────────┼──────────────────┐
#          ▼                  ▼                  ▼
#  ┌────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
#  │  TokenBucket   │ │SlidingWindowLog  │ │ FixedWindowCounter   │
#  ├────────────────┤ ├──────────────────┤ ├──────────────────────┤
#  │ + capacity: int│ │ + max_requests   │ │ + max_requests: int  │
#  │ + refill_rate  │ │ + window_secs    │ │ + window_secs: float │
#  │ + tokens: float│ │ + timestamps:    │ │ + count: int         │
#  │ + last_refill  │ │   deque          │ │ + window_start: float│
#  │ - _lock: Lock  │ │ - _lock: Lock    │ │ - _lock: Lock        │
#  ├────────────────┤ ├──────────────────┤ ├──────────────────────┤
#  │ Refills token  │ │ Evicts old       │ │ Resets counter each  │
#  │ based on time  │ │ timestamps       │ │ window boundary      │
#  │ delta since    │ │ outside rolling  │ │                      │
#  │ last call      │ │ window           │ │                      │
#  └────────────────┘ └──────────────────┘ └──────────────────────┘
#
#  ┌─────────────────────────────────────────────────────────────┐
#  │                    RateLimitRule                            │
#  ├─────────────────────────────────────────────────────────────┤
#  │ + endpoint: str                                             │
#  │ + max_requests: int                                         │
#  │ + window_secs: float                                        │
#  │ + algorithm_type: str  ("token_bucket" | "sliding_window"  │
#  │                          | "fixed_window")                  │
#  └─────────────────────────────────────────────────────────────┘
#
#  ALGORITHM COMPARISON:
#  ┌──────────────────┬──────────────────┬──────────────────────┐
#  │  Token Bucket    │  Sliding Window  │   Fixed Window       │
#  ├──────────────────┼──────────────────┼──────────────────────┤
#  │ Allows bursts    │ Most precise     │ Simplest to impl.    │
#  │ up to capacity   │ O(n) memory      │ Boundary spike risk  │
#  │ Smooth long-term │ per client       │ O(1) per request     │
#  └──────────────────┴──────────────────┴──────────────────────┘
#
#  RELATIONSHIPS:
#  RateLimiter ──*──> RateLimitRule         (one rule per endpoint)
#  RateLimiter ──*──> RateLimitAlgorithm    (one instance per endpoint+client pair)
#  TokenBucket      ──▷── RateLimitAlgorithm (implements)
#  SlidingWindowLog ──▷── RateLimitAlgorithm (implements, most accurate)
#  FixedWindowCounter──▷── RateLimitAlgorithm(implements, most efficient)
#  Key: (endpoint, client_id) → algorithm instance in limiters dict
# ==============================================================================
# fmt: on
import threading
import time
from abc import ABC, abstractmethod
from collections import deque

"""
==============================================================================================
RATE LIMITER SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. Per-Endpoint Configuration: Each API endpoint can have its own rate limit rule.
2. Per-Client Tracking: Rate limits are enforced per (endpoint, client_id) pair.
3. Multiple Algorithms: Token Bucket, Sliding Window Log, Fixed Window Counter.
4. Clean & Simple: Optimized for 45-minute whiteboard interview setups.
5. Thread-Safety: Lock-based synchronization for concurrent requests.

Class Design Diagram:
---------------------
[RateLimiter] "1" *-- "*" [RateLimitAlgorithm] : Manages rules and instances
[RateLimitAlgorithm] <|-- [TokenBucket]
[RateLimitAlgorithm] <|-- [SlidingWindowLog]
[RateLimitAlgorithm] <|-- [FixedWindowCounter]

Class Details:
---------------------
1. RateLimiter (Facade/Manager)
   - Role: Manages rate limit rules per endpoint and dispatches allow_request().
   - Methods: add_rule(), _create_limiter(), allow_request().

2. RateLimitAlgorithm (ABC)
   - Role: Interface for all rate limit algorithms.
   - Methods: allow_request() -> bool.

3. TokenBucket
   - Role: Refills tokens at a steady rate; allows bursts up to capacity.
   - Logic: Time elapsed since last request determines token refill.

4. SlidingWindowLog
   - Role: Most precise tracking; evicts old logs outside the rolling window.
   - Logic: Maintains a queue of exact timestamps.

5. FixedWindowCounter
   - Role: Counts requests in distinct time blocks.
   - Logic: Resets counter when the time window boundary is crossed.
"""

# ==========================================
# Strategy Pattern: Rate Limit Algorithms
# ==========================================

class RateLimitAlgorithm(ABC):
    @abstractmethod
    def allow_request(self) -> bool:
        pass


class TokenBucket(RateLimitAlgorithm):
    """Refills tokens at a steady rate. Allows bursts up to capacity."""
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill_time = time.time()
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill_time
            
            # Refill tokens
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill_time = now
            
            # Consume token
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


class SlidingWindowLog(RateLimitAlgorithm):
    """Tracks exact timestamps. Evicts old logs. Most precise but memory heavy."""
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_log = deque()
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        with self.lock:
            now = time.time()
            
            # Evict timestamps older than the window
            while self.request_log and self.request_log[0] <= now - self.window_seconds:
                self.request_log.popleft()
            
            # Check against limit
            if len(self.request_log) < self.max_requests:
                self.request_log.append(now)
                return True
            return False


class FixedWindowCounter(RateLimitAlgorithm):
    """Counts requests in fixed, distinct windows. Simple but allows boundary bursts."""
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.current_count = 0
        self.window_start = time.time()
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        with self.lock:
            now = time.time()
            
            # Reset the window if enough time has passed
            if now - self.window_start >= self.window_seconds:
                self.current_count = 0
                self.window_start = now
            
            # Check against limit
            if self.current_count < self.max_requests:
                self.current_count += 1
                return True
            return False

# ==========================================
# Rate Limiter Facade
# ==========================================

class RateLimiter:
    """Manages rules per endpoint and isolates limits per client."""
    def __init__(self):
        # Maps endpoint -> (algorithm_name, max_requests, window_seconds)
        self.rules = {}
        # Maps (endpoint, client_id) -> RateLimitAlgorithm instance
        self.client_limiters = {}
        self.lock = threading.Lock()

    def add_rule(self, endpoint: str, algo_name: str, max_requests: int, window_seconds: float):
        """Configures the rate limiting rule for a specific endpoint."""
        with self.lock:
            self.rules[endpoint] = (algo_name, max_requests, window_seconds)
            # Clear existing limiters for this endpoint so they are recreated with new rules
            self.client_limiters = {k: v for k, v in self.client_limiters.items() if k[0] != endpoint}
            print(f"INFO: Configured {endpoint} with {algo_name}")

    def _create_limiter(self, endpoint: str) -> RateLimitAlgorithm:
        """Factory method to create the appropriate limiter algorithm."""
        algo_name, max_requests, window_seconds = self.rules[endpoint]
        
        if algo_name == "TOKEN_BUCKET":
            return TokenBucket(capacity=max_requests, refill_rate=max_requests/window_seconds)
        elif algo_name == "SLIDING_WINDOW":
            return SlidingWindowLog(max_requests, window_seconds)
        elif algo_name == "FIXED_WINDOW":
            return FixedWindowCounter(max_requests, window_seconds)
        else:
            raise ValueError(f"Unknown algorithm: {algo_name}")

    def allow_request(self, endpoint: str, client_id: str) -> bool:
        """Checks if a request is allowed. Instantiates limiter lazily."""
        if endpoint not in self.rules:
            print(f"WARNING: No rule for {endpoint}. Allowing default.")
            return True 

        key = (endpoint, client_id)
        
        # Double-checked locking pattern for efficiency
        if key not in self.client_limiters:
            with self.lock:
                if key not in self.client_limiters:
                    self.client_limiters[key] = self._create_limiter(endpoint)
        
        return self.client_limiters[key].allow_request()

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    limiter = RateLimiter()
    limiter.add_rule("/api/search", "TOKEN_BUCKET", max_requests=3, window_seconds=1.0)
    limiter.add_rule("/api/pay", "FIXED_WINDOW", max_requests=2, window_seconds=10.0)

    print("\n[Demo] Token Bucket (/api/search, 3 req/s)")
    for i in range(5):
        status = "ALLOWED" if limiter.allow_request("/api/search", "user1") else "DENIED"
        print(f"Request {i+1}: {status}")

    print("\n[Demo] Fixed Window (/api/pay, 2 req/10s)")
    for i in range(4):
        status = "ALLOWED" if limiter.allow_request("/api/pay", "user2") else "DENIED"
        print(f"Request {i+1}: {status}")

    print("\n[Demo] Per-Client Isolation (/api/search)")
    status = "ALLOWED" if limiter.allow_request("/api/search", "user_new") else "DENIED"
    print(f"New User Request: {status}")
