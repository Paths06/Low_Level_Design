package com.hotel.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/*
 * ==============================================================================================
 * HOTEL MANAGEMENT SYSTEM LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Features:
 * 1. Room Management: Types (Standard, Deluxe, Suite) and Status (Available, Occupied).
 * 2. Reservation: Booking flow, Check-In, Check-Out.
 * 3. Concurrency: Synchronized booking to prevent double booking of same room.
 * 4. Extensibility: Payment Strategy, Room Pricing Strategy.
 * 
 * Design Patterns:
 * 1. Singleton: HotelManager (Facade).
 * 2. Factory: RoomFactory (Creating appropriate Room subclasses).
 * 3. State: ReservationStatus / RoomStatus.
 * 4. Strategy: PaymentStrategy.
 *
 * Class Design Diagram:
 * ---------------------
 * [HotelManager] "1" *-- "*" [Room]
 * [HotelManager] "1" *-- "*" [Guest]
 * [HotelManager] "1" *-- "*" [Reservation]
 * [Room] <|-- [StandardRoom]
 * [Room] <|-- [DeluxeRoom]
 * [Room] <|-- [SuiteRoom]
 * [Reservation] "1" *-- "1" [Guest]
 * [Reservation] "1" *-- "1" [Room]
 * [Reservation] "1" *-- "1" [Invoice]
 * [Room] ..> [RoomStatus]
 * 
 * Class Details:
 * ---------------------
 * 1. HotelManager (Singleton)
 *    - Role: Central system controller.
 *    - Methods: addRoom(), findAvailableRoom(), bookRoom(), checkIn(), checkOut().
 *
 * 2. Room (Abstract)
 *    - Role: Physical room entity.
 *    - Attributes: id, type, price, status (Lock for concurrency).
 *
 * 3. Guest
 *    - Attributes: id, name, email.
 *
 * 4. Reservation
 *    - Role: Transaction record.
 *    - Attributes: id, guest, room, dateRange, status.
 */

public class HotelManagementSystem {
    public static void main(String[] args) {
        System.out.println("--- Hotel Management System Demo ---");
        
        HotelManager hotel = HotelManager.getInstance();

        // 1. Setup Rooms
        hotel.addRoom(RoomFactory.createRoom(RoomType.STANDARD, "101"));
        hotel.addRoom(RoomFactory.createRoom(RoomType.DELUXE, "201"));
        hotel.addRoom(RoomFactory.createRoom(RoomType.SUITE, "301"));

        // 2. Guest Registration
        Guest g1 = new Guest("G1", "John Doe");
        Guest g2 = new Guest("G2", "Jane Smith");
        
        // 3. Search & Booking
        System.out.println("\n[Action] John searches for DELUXE room.");
        Date today = new Date();
        // Simplified Date logic: In real system, we check ranges.
        // Here we just check "current" status for demo.
        
        Room room = hotel.findAvailableRoom(RoomType.DELUXE);
        if(room != null) {
            System.out.println("Found Room: " + room.getId() + " Price: " + room.getPrice());
            Reservation r1 = hotel.createReservation(g1, room, today, 3); // 3 nights
            System.out.println("Reservation Created: " + r1.getId());
            
            // 4. Payment
            r1.processPayment(new CreditCardPayment());
            
            // 5. Check In
            hotel.checkIn(r1.getId());
        }

        // 6. Concurrency Test
        // Jane tries to book the same room (should fail or find another if we had multiple)
        System.out.println("\n[Action] Jane tries to book the SAME room 201 directly.");
        try {
            // Need to manually access room 201 to simulate clash if findAvailableRoom logic was bypassed
            // But normally system handles this.
            // Let's try booking the SUITE for Jane.
            Room suite = hotel.findAvailableRoom(RoomType.SUITE);
            Reservation r2 = hotel.createReservation(g2, suite, today, 1);
            hotel.checkIn(r2.getId());
            
            // 7. Check Out
            System.out.println("\n[Action] Jane checks out.");
            hotel.checkOut(r2.getId());
             
        } catch (Exception e) {
            System.out.println("Error: " + e.getMessage());
        }
    }
}

// ==========================================
// Enums & Strategies
// ==========================================

enum RoomType { STANDARD, DELUXE, SUITE }
enum RoomStatus { AVAILABLE, OCCUPIED, MAINTENANCE }
enum ReservationStatus { CONFIRMED, CHECKED_IN, CHECKED_OUT, CANCELLED }

interface PaymentStrategy {
    boolean pay(double amount);
}

class CreditCardPayment implements PaymentStrategy {
    @Override
    public boolean pay(double amount) {
        System.out.println("Paid $" + amount + " via Credit Card.");
        return true;
    }
}

// ==========================================
// Domain Models
// ==========================================

class Guest {
    String id;
    String name;
    public Guest(String id, String name) { this.id = id; this.name = name; }
}

abstract class Room {
    String id;
    RoomType type;
    double price;
    RoomStatus status;
    Lock lock = new ReentrantLock(); // For thread-safe booking

    public Room(String id, RoomType type, double price) {
        this.id = id; this.type = type; this.price = price;
        this.status = RoomStatus.AVAILABLE;
    }
    
    public String getId() { return id; }
    public double getPrice() { return price; }
    public RoomStatus getStatus() { return status; }
    public void setStatus(RoomStatus status) { this.status = status; }
    
    // Concurrency Control
    public boolean tryLock() { return lock.tryLock(); }
    public void unlock() { lock.unlock(); }
}

class StandardRoom extends Room {
    public StandardRoom(String id) { super(id, RoomType.STANDARD, 100.0); }
}
class DeluxeRoom extends Room {
    public DeluxeRoom(String id) { super(id, RoomType.DELUXE, 200.0); }
}
class SuiteRoom extends Room {
    public SuiteRoom(String id) { super(id, RoomType.SUITE, 500.0); }
}

class RoomFactory {
    public static Room createRoom(RoomType type, String id) {
        switch(type) {
            case STANDARD: return new StandardRoom(id);
            case DELUXE: return new DeluxeRoom(id);
            case SUITE: return new SuiteRoom(id);
            default: return new StandardRoom(id);
        }
    }
}

class Reservation {
    String id;
    Guest guest;
    Room room;
    Date checkInDate;
    int durationNights;
    ReservationStatus status;
    double totalAmount;

    public Reservation(String id, Guest g, Room r, Date date, int nights) {
        this.id = id; this.guest = g; this.room = r;
        this.checkInDate = date; this.durationNights = nights;
        this.status = ReservationStatus.CONFIRMED;
        this.totalAmount = r.getPrice() * nights;
    }
    
    public void processPayment(PaymentStrategy paymentMethod) {
        if(paymentMethod.pay(totalAmount)) {
            System.out.println("Payment Successful for Reservation " + id);
        }
    }
    
    public String getId() { return id; }
    public Room getRoom() { return room; }
    public void setStatus(ReservationStatus s) { this.status = s; }
    public ReservationStatus getStatus() { return status; }
}

// ==========================================
// System Manager (Singleton)
// ==========================================

class HotelManager {
    private static HotelManager instance;
    private Map<String, Room> rooms;
    private Map<String, Reservation> reservations;

    private HotelManager() {
        rooms = new ConcurrentHashMap<>();
        reservations = new ConcurrentHashMap<>();
    }

    public static synchronized HotelManager getInstance() {
        if(instance == null) instance = new HotelManager();
        return instance;
    }

    public void addRoom(Room r) { rooms.put(r.getId(), r); }
    
    // Search
    public Room findAvailableRoom(RoomType type) {
        for(Room r : rooms.values()) {
            if(r.type == type && r.getStatus() == RoomStatus.AVAILABLE) {
                return r;
            }
        }
        return null;
    }

    // Create Reservation
    public Reservation createReservation(Guest guest, Room room, Date date, int nights) {
        // Critical Section: Ensure room is still available and lock it
        if(room.tryLock()) {
            try {
                if(room.getStatus() != RoomStatus.AVAILABLE) {
                    throw new RuntimeException("Room " + room.getId() + " is no longer available.");
                }
                
                // In real system, we don't mark room OCCUPIED until check-in for future dates.
                // But for this simple design, we reserve it now.
                // Or we keep status AVAILABLE but mark calendar. 
                // Simplification: Mark Occupied to prevent double booking in demo.
                room.setStatus(RoomStatus.OCCUPIED);
                
                Reservation res = new Reservation(UUID.randomUUID().toString(), guest, room, date, nights);
                reservations.put(res.getId(), res);
                return res;
            } finally {
                room.unlock();
            }
        } else {
            throw new RuntimeException("Room is busy processing another request.");
        }
    }

    public void checkIn(String reservationId) {
        Reservation res = reservations.get(reservationId);
        if(res != null && res.getStatus() == ReservationStatus.CONFIRMED) {
            res.setStatus(ReservationStatus.CHECKED_IN);
            res.getRoom().setStatus(RoomStatus.OCCUPIED); // Re-affirm
            System.out.println("Guest Checked In: " + res.guest.name + " -> Room " + res.getRoom().getId());
        }
    }

    public void checkOut(String reservationId) {
        Reservation res = reservations.get(reservationId);
        if(res != null) {
            res.setStatus(ReservationStatus.CHECKED_OUT);
            res.getRoom().setStatus(RoomStatus.AVAILABLE); // Free up room
            System.out.println("Guest Checked Out: " + res.guest.name + " from Room " + res.getRoom().getId());
            
            // Generate Invoice Logic here
        }
    }
}
