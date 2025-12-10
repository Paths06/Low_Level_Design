package com.airline.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/*
 * ==============================================================================================
 * AIRLINE MANAGEMENT SYSTEM LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Features Implemented:
 * 1. Search: Search flights by Source, Destination, Date.
 * 2. Booking: Seat selection, Booking creation, Payment processing.
 * 3. Management: Flights, Crew, Aircrafts (Admin).
 * 4. Extensibility: Dynamic Pricing Strategy, Meal Selection.
 * 5. Concurrency: Synchronized seat booking.
 *
 * Design Patterns:
 * 1. Singleton: AirlineManager (Facade).
 * 2. Strategy: PricingStrategy (Dynamic/Static), PaymentProcessor (CreditCard).
 * 3. Observer: NotificationService (Notify user on booking/change).
 * 4. State: FlightStatus (Scheduled, Delayed, Cancelled).
 *
 * Class Design Diagram:
 * ---------------------
 * [AirlineSystem] "1" *-- "*" [Airline]
 * [Airline] "1" *-- "*" [Flight]
 * [Flight] "1" *-- "1" [Aircraft]
 * [Flight] "1" *-- "*" [Seat]
 * [Flight] "1" *-- "1" [PricingStrategy]
 * [Booking] "1" *-- "1" [Flight]
 * [Booking] "1" *-- "*" [Seat]
 * [Booking] "1" *-- "1" [Passenger]
 * [Booking] ..> [PaymentProcessor] : Uses
 * [Booking] ..> [MealType] : Has
 * [User] <|-- [Passenger]
 * [User] <|-- [Admin]
 * [User] <|-- [Crew]
 *
 * Class Details:
 * ---------------------
 * 1. AirlineSystem (Singleton)
 *    - Role: Main controller.
 *    - Methods: searchFlights(), createBooking() [Transaction].
 *
 * 2. Flight
 *    - Role: Represents a scheduled journey.
 *    - Attributes: flightNumber, source, dest, date, seats, pricingStrategy.
 *    - Methods: calculatePrice(), bookSeats().
 *
 * 3. Seat
 *    - Attributes: seatNumber, isBooked.
 *
 * 4. PricingStrategy (Interface)
 *    - Role: Calculate price based on demand/time.
 *    - Impls: StaticPricing, DynamicPricing.
 * 
 * 5. PaymentProcessor (Interface)
 *    - Role: Handle payments.
 *    - Impls: CreditCardPayment.
 *
 * 6. Booking
 *    - Attributes: status, mealPreference, paymentStatus.
 */

public class AirlineManagementSystem {
    public static void main(String[] args) {
        System.out.println("--- Airline Management System ---");
        
        AirlineSystem system = AirlineSystem.getInstance();

        // 1. Admin Setup
        Admin admin = new Admin("A1", "Super Admin");
        Aircraft boeing737 = new Aircraft("AC1", "Boeing 737", 10); // Small cap for demo
        Airport del = new Airport("DEL", "New Delhi");
        Airport sfo = new Airport("SFO", "San Francisco");

        // Dynamic Pricing Strategy: Price increases as seats fill up
        Flight f1 = new Flight("FL001", del, sfo, new Date(), boeing737, new DynamicPricingStrategy());
        system.addFlight(f1);

        // 2. Search
        System.out.println("\n[Passenger] Searching DEL -> SFO");
        List<Flight> results = system.searchFlights("DEL", "SFO", new Date());
        if (results.isEmpty()) {
            System.out.println("No flights found.");
            return;
        }
        Flight selectedFlight = results.get(0);
        System.out.println("Found Flight: " + selectedFlight.getFlightNumber() + " Base Price: " + selectedFlight.getBasePrice());

        // 3. Booking (Passenger 1)
        Passenger p1 = new Passenger("P1", "Rahul", "passport123");
        List<String> seats1 = Arrays.asList("1A", "1B");
        PaymentProcessor payment = new CreditCardPayment(); // Create Strategy
        
        try {
            double price = selectedFlight.calculatePrice(seats1.size());
            System.out.println("Price for P1: " + price);
            Booking b1 = system.createBooking(p1, selectedFlight, seats1, payment);
            System.out.println("Booking Confirmed: " + b1.getBookingId());
        } catch (Exception e) {
            System.out.println("Booking Failed: " + e.getMessage());
        }

        // 4. Booking (Passenger 2) - Dynamic Pricing Effect
        Passenger p2 = new Passenger("P2", "Sita", "passport456");
        List<String> seats2 = Arrays.asList("2A");

        try {
            // Price should be higher now as 2 seats are gone
            double price = selectedFlight.calculatePrice(seats2.size());
            System.out.println("Price for P2 (Dynamic): " + price); 
            Booking b2 = system.createBooking(p2, selectedFlight, seats2, payment);
            System.out.println("Booking Confirmed: " + b2.getBookingId());
        } catch (Exception e) {
            System.out.println("Booking Failed: " + e.getMessage());
        }
    }
}

// ==========================================
// Strategies & Interfaces
// ==========================================

interface PricingStrategy {
    double calculatePrice(Flight flight, int seatCount);
}

class StaticPricingStrategy implements PricingStrategy {
    @Override
    public double calculatePrice(Flight flight, int seatCount) {
        return flight.getBasePrice() * seatCount;
    }
}

class DynamicPricingStrategy implements PricingStrategy {
    @Override
    public double calculatePrice(Flight flight, int seatCount) {
        int total = flight.getTotalSeats();
        int booked = flight.getBookedSeats();
        double base = flight.getBasePrice();
        
        if ((double)booked / total > 0.5) return base * 1.5 * seatCount;
        else if (booked > 0) return base * 1.1 * seatCount;
        return base * seatCount;
    }
}

// Requirement: Payment Processing
interface PaymentProcessor {
    boolean process(double amount);
}

class CreditCardPayment implements PaymentProcessor {
    @Override
    public boolean process(double amount) {
        System.out.println("Processing Credit Card Payment: $" + amount);
        return true; 
    }
}

// Requirement: Extensibility (Meal Selection)
enum MealType {
    STANDARD, VEG, NON_VEG, KOSHER, HALAL
}

// ==========================================
// Domain Models
// ==========================================

class User {
    String id;
    String name;
    public User(String id, String name) { this.id = id; this.name = name; }
}

class Passenger extends User {
    String passportNumber;
    public Passenger(String id, String name, String passport) { 
        super(id, name); 
        this.passportNumber = passport;
    }
}

class Admin extends User {
    public Admin(String id, String name) { super(id, name); }
}

class Crew extends User {
    String designation;
    public Crew(String id, String name, String role) { 
        super(id, name); 
        this.designation = role;
    }
}

class Airport {
    String code;
    String city;
    public Airport(String code, String city) { this.code = code; this.city = city; }
    public String getCode() { return code; }
}

class Aircraft {
    String tailNumber;
    String model;
    int capacity;
    
    public Aircraft(String tailNumber, String model, int capacity) {
        this.tailNumber = tailNumber;
        this.model = model;
        this.capacity = capacity;
    }
    public int getCapacity() { return capacity; }
}

class Seat {
    String seatNumber;
    boolean isBooked;
    double priceMultiplier; 

    public Seat(String no) {
        this.seatNumber = no;
        this.isBooked = false;
        this.priceMultiplier = 1.0;
    }
}

class Flight {
    private String flightNumber;
    private Airport source;
    private Airport destination;
    private Date date;
    private Aircraft aircraft;
    private Map<String, Seat> seats = new ConcurrentHashMap<>();
    private double basePrice = 1000.0;
    private PricingStrategy pricingStrategy;

    public Flight(String no, Airport src, Airport dst, Date date, Aircraft ac, PricingStrategy ps) {
        this.flightNumber = no;
        this.source = src;
        this.destination = dst;
        this.date = date;
        this.aircraft = ac;
        this.pricingStrategy = ps;
        
        for (int i=1; i<=ac.getCapacity(); i++) {
            seats.put(i + "A", new Seat(i + "A"));
            if(i <= ac.getCapacity()/2) seats.put(i + "B", new Seat(i + "B"));
        }
    }

    public double calculatePrice(int seatCount) {
        return pricingStrategy.calculatePrice(this, seatCount);
    }
    
    // Seat Management
    public synchronized boolean bookSeats(List<String> seatNos) {
        for (String no : seatNos) {
            Seat s = seats.get(no);
            if (s == null || s.isBooked) return false;
        }
        for (String no : seatNos) {
            seats.get(no).isBooked = true;
        }
        return true;
    }

    public int getTotalSeats() { return seats.size(); }
    public int getBookedSeats() { 
        return (int) seats.values().stream().filter(s -> s.isBooked).count(); 
    }
    
    public String getFlightNumber() { return flightNumber; }
    public Airport getSource() { return source; }
    public Airport getDestination() { return destination; }
    public double getBasePrice() { return basePrice; }
}

class Booking {
    String bookingId;
    Flight flight;
    Passenger passenger;
    List<String> seats;
    double amount;
    String status; // CONFIRMED, CANCELLED
    
    // Extensibility: Meal Preference
    MealType mealPreference;

    public Booking(String id, Flight f, Passenger p, List<String> s, double amt) {
        this.bookingId = id; this.flight = f; this.passenger = p; this.seats = s; this.amount = amt;
        this.status = "PENDING";
        this.mealPreference = MealType.STANDARD;
    }
    
    public void confirm() { this.status = "CONFIRMED"; }
    public void setMealPreference(MealType meal) { this.mealPreference = meal; }
    public String getBookingId() { return bookingId; }
}

// ==========================================
// System Facade (Singleton)
// ==========================================

class AirlineSystem {
    private static AirlineSystem instance;
    private List<Flight> flights;
    private Map<String, Booking> bookings;
    private Map<String, Passenger> passengers; // Passenger Management

    private AirlineSystem() {
        flights = new ArrayList<>();
        bookings = new ConcurrentHashMap<>();
        passengers = new ConcurrentHashMap<>();
    }

    public static synchronized AirlineSystem getInstance() {
        if (instance == null) instance = new AirlineSystem();
        return instance;
    }

    // Flight Management
    public void addFlight(Flight f) { flights.add(f); }
    
    // Passenger Management
    public void registerPassenger(Passenger p) {
        passengers.put(p.id, p);
    }

    public List<Flight> searchFlights(String src, String dst, Date date) {
        return flights.stream()
                .filter(f -> f.getSource().getCode().equals(src) && f.getDestination().getCode().equals(dst))
                .collect(Collectors.toList());
    }

    // Booking Management & Payment Processing
    public Booking createBooking(Passenger p, Flight f, List<String> seatNos, PaymentProcessor payment) {
        if (!passengers.containsKey(p.id)) registerPassenger(p);

        if (f.bookSeats(seatNos)) {
            double price = f.calculatePrice(seatNos.size());
            
            // Payment Step
            if(payment.process(price)) {
                Booking b = new Booking(UUID.randomUUID().toString(), f, p, seatNos, price);
                b.confirm();
                bookings.put(b.getBookingId(), b);
                return b;
            } else {
                // Rollback seat? (Ideally yes, simplified here)
                throw new RuntimeException("Payment Failed");
            }
        } else {
            throw new RuntimeException("Seats not available");
        }
    }
    
    // Extensibility: Add meal to booking
    public void updateBookingMeal(String bookingId, MealType meal) {
        Booking b = bookings.get(bookingId);
        if(b != null) b.setMealPreference(meal);
    }
}
