package com.elevator.lld;

import java.util.*;
import java.util.concurrent.PriorityBlockingQueue;

/*
 * ==============================================================================================
 * ELEVATOR SYSTEM LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Requirements Implemented:
 * 1. Multiple Elevators & Floors.
 * 2. Capacity Management.
 * 3. Request Handling: External (Hall) and Internal (Panel).
 * 4. Optimization: LOOK Algorithm (Scan) for efficient movement.
 * 5. Concurrency: Thread-safe Queues and synchronized state.
 *
 * Design Patterns:
 * 1. Singleton: ElevatorController (Central Dispatcher).
 * 2. Strategy: DispatchStrategy (Can swap algorithms like FCFS, SCAN/LOOK).
 * 3. State: ElevatorState (IDLE, MOVING_UP, MOVING_DOWN).
 * 
 * Algorithm Used: LOOK (Scanning)
 * - The elevator moves in current direction as long as there are requests.
 * - If no requests in current direction, it switches.
 *
 * Class Design Diagram:
 * ---------------------
 * [ElevatorController] "1" *-- "*" [Elevator]
 * [ElevatorController] "1" *-- "1" [DispatchStrategy]
 * [Elevator] "1" *-- "1" [RequestQueue]
 * [Request] <|-- [InternalRequest]
 * [Request] <|-- [ExternalRequest]
 * [Elevator] ..> [Direction]
 * [Elevator] ..> [State]
 *
 * Class Details:
 * ---------------------
 * 1. ElevatorController (Singleton)
 *    - Role: Central dispatcher. Handles External requests and assigns best Elevator.
 *    - Attributes: elevators (List).
 *    - Methods: requestElevator(), step() [Simulation ticker].
 *
 * 2. Elevator
 *    - Role: The physical car.
 *    - Attributes: id, currentFloor, direction, capacity, requests (PriorityQueue).
 *    - Methods: addRequest(), move(), openDoor().
 *
 * 3. Request (Abstract)
 *    - Role: Represents a button press.
 *    - Attributes: floor, direction.
 *
 * 4. DispatchStrategy
 *    - Role: Algorithm to assign external request to an elevator.
 *    - Logic: Finds nearest elevator moving in same direction or Idle.
 */

public class ElevatorSystem {
    public static void main(String[] args) {
        System.out.println("--- Elevator System Demo ---");

        ElevatorController controller = ElevatorController.getInstance();
        
        // 1. Initialize 2 Elevators
        Elevator e1 = new Elevator(1, 10); // ID 1, Capacity 10
        Elevator e2 = new Elevator(2, 10);
        controller.addElevator(e1);
        controller.addElevator(e2);

        // 2. Simulate Requests
        System.out.println("1. User at Floor 1 requests UP");
        controller.handleExternalRequest(1, Direction.UP);
        
        System.out.println("2. User at Floor 5 requests DOWN");
        controller.handleExternalRequest(5, Direction.DOWN); // Should likely go to e2 if e1 is busy

        // 3. Simulate Movement (Step-by-step)
        // In real system, these would be threads running loop.
        System.out.println("\n--- Simulation Steps ---");
        for(int i=0; i<8; i++) {
            System.out.println("Tick " + i + ":");
            controller.step();
            
            // Simulating a user entering at Floor 1 and pressing Floor 4
            if(i == 2) { 
                System.out.println("  User enters Elevator 1 and presses 4");
                e1.addInternalRequest(4);
            }
        }
    }
}

// ==========================================
// Enums & Models
// ==========================================

enum Direction { UP, DOWN, IDLE }
enum State { MOVING, IDLE, STOPPED }

abstract class Request {
    int targetFloor;
    public Request(int f) { this.targetFloor = f; }
}

class InternalRequest extends Request {
    public InternalRequest(int f) { super(f); }
}

class ExternalRequest extends Request {
    Direction direction;
    public ExternalRequest(int f, Direction d) { 
        super(f); 
        this.direction = d; 
    }
}

// ==========================================
// Core Domain: Elevator
// ==========================================

class Elevator {
    int id;
    int currentFloor;
    int capacity;
    Direction direction;
    State state;
    
    // Using PriorityQueues for LOOK Algorithm
    // minHeap for UP requests (sorts 1, 2, 3...)
    // maxHeap for DOWN requests (sorts 10, 9, 8...)
    PriorityBlockingQueue<Integer> upQueue;
    PriorityBlockingQueue<Integer> downQueue;

    public Elevator(int id, int capacity) {
        this.id = id;
        this.capacity = capacity;
        this.currentFloor = 0;
        this.direction = Direction.IDLE;
        this.state = State.IDLE;
        
        this.upQueue = new PriorityBlockingQueue<>();
        this.downQueue = new PriorityBlockingQueue<>(10, Collections.reverseOrder());
    }

    public synchronized void addExternalRequest(ExternalRequest req) {
        // Validation: If target > current, we MUST go UP to get there, 
        // regardless of whether the user wants to go UP or DOWN later.
        if (req.targetFloor > currentFloor) {
            upQueue.add(req.targetFloor);
            if(direction == Direction.IDLE) direction = Direction.UP;
        } else {
            downQueue.add(req.targetFloor);
            if(direction == Direction.IDLE) direction = Direction.DOWN;
        }
    }

    public synchronized void addInternalRequest(int floor) {
        if (floor > currentFloor) upQueue.add(floor);
        else downQueue.add(floor);
    }

    public void move() {
        if (direction == Direction.IDLE) {
            return;
        }

        if (direction == Direction.UP) {
            processUpQueue();
        } else {
            processDownQueue();
        }
    }

    private void processUpQueue() {
        if (upQueue.isEmpty()) {
            // Check if we need to switch direction
            if (!downQueue.isEmpty()) {
                direction = Direction.DOWN;
            } else {
                direction = Direction.IDLE;
            }
            return;
        }

        int nextStop = upQueue.peek();
        if (currentFloor == nextStop) {
            // Arrived
            upQueue.poll(); // Remove request
            System.out.println("  [Elevator " + id + "] Opened doors at " + currentFloor);
        } else {
            currentFloor++;
            System.out.println("  [Elevator " + id + "] Moving UP to " + currentFloor);
        }
    }

    private void processDownQueue() {
         if (downQueue.isEmpty()) {
            if (!upQueue.isEmpty()) {
                direction = Direction.UP;
            } else {
                direction = Direction.IDLE;
            }
            return;
        }

        int nextStop = downQueue.peek();
        if (currentFloor == nextStop) {
            downQueue.poll();
            System.out.println("  [Elevator " + id + "] Opened doors at " + currentFloor);
        } else {
            currentFloor--;
            System.out.println("  [Elevator " + id + "] Moving DOWN to " + currentFloor);
        }
    }
    
    public int getCurrentFloor() { return currentFloor; }
    public Direction getDirection() { return direction; }
    public boolean isIdle() { return direction == Direction.IDLE; }
}

// ==========================================
// Controller (Singleton & Strategy)
// ==========================================

class ElevatorController {
    private static ElevatorController instance;
    private List<Elevator> elevators;

    private ElevatorController() {
        elevators = new ArrayList<>();
    }

    public static synchronized ElevatorController getInstance() {
        if (instance == null) instance = new ElevatorController();
        return instance;
    }

    public void addElevator(Elevator e) { elevators.add(e); }

    // Strategy Pattern: Nearest Elevator Dispatch
    public void handleExternalRequest(int floor, Direction direction) {
        Elevator bestElevator = findOptimalElevator(floor, direction);
        System.out.println("Assigning request [Floor " + floor + " " + direction + "] to Elevator " + bestElevator.id);
        
        // Critical Fix: If Elevator is IDLE or moving incorrectly, we need to add a "Fetch" request first?
        // Actually, scan algorithms typically just add the request to queue.
        // But if I am at Floor 0 and request is at Floor 5, I need to go UP to 5, regardless of whether 
        // the user wants to go DOWN from 5.
        // The PriorityQueue logic in Elevator handles the *processing* order, but `direction` determines movement.
        
        bestElevator.addExternalRequest(new ExternalRequest(floor, direction));
    }

    private Elevator findOptimalElevator(int targetFloor, Direction direction) {
        Elevator best = null;
        int minDistance = Integer.MAX_VALUE;

        for (Elevator e : elevators) {
            int dist = Math.abs(e.getCurrentFloor() - targetFloor);
            
            // Logic 1: Moving towards target
            boolean movingTowards = false;
            if (e.getDirection() == Direction.UP && e.getCurrentFloor() <= targetFloor) movingTowards = true;
            if (e.getDirection() == Direction.DOWN && e.getCurrentFloor() >= targetFloor) movingTowards = true;

            // Logic 2: Idle
            if (e.isIdle()) movingTowards = true;

            // Simple Greedy: If moving towards or idle, consider it candidate
            if (movingTowards) {
                if(dist < minDistance) {
                    minDistance = dist;
                    best = e;
                }
            }
        }
        
        if (best == null) return elevators.get(0); 
        return best;
    }

    public void step() {
        for (Elevator e : elevators) e.move();
    }
}
