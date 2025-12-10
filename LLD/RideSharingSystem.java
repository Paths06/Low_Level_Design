package com.uber.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/*
 * ==============================================================================================
 * RIDE SHARING SERVICE (LIKE UBER) LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Features:
 * 1. User Management: Rider and Driver (Extends User).
 * 2. Geo-Location: Tracking driver locations.
 * 3. Matching Service: Assign closest AVERAGE driver to Rider.
 * 4. Trip Lifecycle: REQUESTED -> ASSIGNED -> ON_TRIP -> COMPLETED.
 * 5. Cost Calculation: Strategy for different ride types (Regular/Premium).
 * 
 * Design Patterns:
 * 1. Observer: Rider gets notified when Driver status changes.
 * 2. Strategy: PricingStrategy (Surge/RideType).
 * 3. Singleton: UberSystem (Facade).
 * 4. State: TripStatus.
 *
 * Class Design Diagram:
 * ---------------------
 * [UberSystem] "1" *-- "*" [Rider]
 * [UberSystem] "1" *-- "*" [Driver]
 * [UberSystem] "1" *-- "1" [TripManager]
 * [TripManager] "1" *-- "*" [Trip]
 * [Trip] "1" *-- "1" [Rider]
 * [Trip] "1" *-- "1" [Driver]
 * [Trip] "1" *-- "1" [PricingStrategy]
 * [Driver] ..> [Location]
 * [Driver] ..> [DriverStatus]
 * [Trip] ..> [TripStatus]
 *
 * Class Details:
 * ---------------------
 * 1. UberSystem (Facade)
 *    - Role: Main entry point.
 *    - Methods: requestRide(), completeTrip().
 *
 * 2. TripManager
 *    - Role: Handles matching logic.
 *    - Methods: findDriver(), createTrip().
 *
 * 3. Driver
 *    - Attributes: currentLocation, status (AVAILABLE/BUSY).
 *
 * 4. Location
 *    - Attributes: lat, lon.
 *    - Methods: distanceTo().
 */

public class RideSharingSystem {
    public static void main(String[] args) {
        System.out.println("--- Uber System Demo ---");
        
        UberSystem system = UberSystem.getInstance();

        // 1. Register Users
        Rider rider = new Rider("R1", "Alice", new Location(0, 0)); // At Origin
        Driver d1 = new Driver("D1", "Bob", new Location(1, 1)); // Close
        Driver d2 = new Driver("D2", "Charlie", new Location(10, 10)); // Far
        
        system.addDriver(d1);
        system.addDriver(d2);

        // 2. Request Ride
        System.out.println("\n[Action] Alice requests ride from (0,0) to (5,5)");
        Location dropOff = new Location(5, 5);
        
        try {
            Trip trip = system.requestRide(rider, rider.getLocation(), dropOff, RideType.REGULAR);
            System.out.println("Trip Created: " + trip.getId());
            System.out.println("Driver Assigned: " + trip.getDriver().getName());
            
            // 3. Simulate Trip
            System.out.println("\n[Action] Driver starts trip...");
            trip.setStatus(TripStatus.ON_TRIP);
            
            System.out.println("[Action] Trip Completed.");
            system.completeTrip(trip.getId());
            
        } catch (Exception e) {
            System.out.println("Error: " + e.getMessage());
        }
    }
}

// ==========================================
// Enums & Strategy
// ==========================================

enum RideType { REGULAR, PREMIUM }
enum TripStatus { REQUESTED, ASSIGNED, ON_TRIP, COMPLETED, CANCELLED }
enum DriverStatus { AVAILABLE, ON_TRIP, OFFLINE }

interface PricingStrategy {
    double calculateFare(double distance, double time);
}

class RegularPricing implements PricingStrategy {
    @Override
    public double calculateFare(double distance, double time) {
        return (distance * 10) + (time * 1); // Base calculation
    }
}

class PremiumPricing implements PricingStrategy {
    @Override
    public double calculateFare(double distance, double time) {
        return (distance * 20) + (time * 2); // 2x cost
    }
}

// ==========================================
// Domain Models
// ==========================================

class Location {
    double x, y;
    public Location(double x, double y) { this.x = x; this.y = y; }
    
    public double distanceTo(Location other) {
        return Math.sqrt(Math.pow(this.x - other.x, 2) + Math.pow(this.y - other.y, 2));
    }
    
    @Override public String toString() { return String.format("(%.1f, %.1f)", x, y); }
}

abstract class User {
    String id;
    String name;
    public User(String id, String name) { this.id = id; this.name = name; }
    public String getName() { return name; }
}

class Rider extends User {
    Location currentLocation;
    public Rider(String id, String name, Location loc) { 
        super(id, name); 
        this.currentLocation = loc;
    }
    public Location getLocation() { return currentLocation; }
}

class Driver extends User {
    Location currentLocation;
    DriverStatus status;
    double rating; // Extensibility

    public Driver(String id, String name, Location loc) {
        super(id, name);
        this.currentLocation = loc;
        this.status = DriverStatus.AVAILABLE;
        this.rating = 5.0;
    }
    
    public void setStatus(DriverStatus s) { this.status = s; }
    public void setLocation(Location l) { this.currentLocation = l; }
    public Location getLocation() { return currentLocation; }
    public DriverStatus getStatus() { return status; }
}

class Trip {
    String id;
    Rider rider;
    Driver driver;
    Location src;
    Location dest;
    TripStatus status;
    PricingStrategy pricing;
    double fare;

    public Trip(String id, Rider r, Driver d, Location s, Location dst, PricingStrategy p) {
        this.id = id; this.rider = r; this.driver = d; 
        this.src = s; this.dest = dst; this.pricing = p;
        this.status = TripStatus.ASSIGNED;
    }
    
    public void setStatus(TripStatus s) { 
        this.status = s; 
        System.out.println("Trip " + id + " status updated to: " + s);
        if(s == TripStatus.COMPLETED) {
            calculateFare();
        }
    }
    
    private void calculateFare() {
        double dist = src.distanceTo(dest);
        this.fare = pricing.calculateFare(dist, 10); // Assume 10 mins for demo
        System.out.println("Total Fare: $" + String.format("%.2f", fare));
    }
    
    public String getId() { return id; }
    public Driver getDriver() { return driver; }
}

// ==========================================
// System Manager
// ==========================================

class TripManager {
    public Driver findNearestDriver(Location pickup, List<Driver> drivers) {
        Driver best = null;
        double minDistance = Double.MAX_VALUE;
        
        for(Driver d : drivers) {
            if(d.getStatus() == DriverStatus.AVAILABLE) {
                double dist = d.getLocation().distanceTo(pickup);
                if(dist < minDistance) {
                    minDistance = dist;
                    best = d;
                }
            }
        }
        return best;
    }
}

class UberSystem {
    private static UberSystem instance;
    private List<Driver> drivers;
    private Map<String, Trip> activeTrips;
    private TripManager tripManager;

    private UberSystem() {
        drivers = new ArrayList<>();
        activeTrips = new ConcurrentHashMap<>();
        tripManager = new TripManager();
    }

    public static synchronized UberSystem getInstance() {
        if(instance == null) instance = new UberSystem();
        return instance;
    }

    public void addDriver(Driver d) { drivers.add(d); }

    public Trip requestRide(Rider rider, Location src, Location dest, RideType type) {
        Driver driver = tripManager.findNearestDriver(src, drivers);
        if(driver == null) {
            throw new RuntimeException("No Drivers Available!");
        }
        
        driver.setStatus(DriverStatus.ON_TRIP);
        
        PricingStrategy strategy = (type == RideType.PREMIUM) ? new PremiumPricing() : new RegularPricing();
        Trip trip = new Trip(UUID.randomUUID().toString(), rider, driver, src, dest, strategy);
        
        activeTrips.put(trip.getId(), trip);
        return trip;
    }

    public void completeTrip(String tripId) {
        Trip trip = activeTrips.get(tripId);
        if(trip != null) {
            trip.setStatus(TripStatus.COMPLETED);
            trip.getDriver().setStatus(DriverStatus.AVAILABLE);
            // In real app: Update Driver Location to Dest
            trip.getDriver().setLocation(trip.dest);
        }
    }
}
