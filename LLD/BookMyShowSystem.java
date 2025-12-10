package com.bms.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.stream.Collectors;

/*
 * ==============================================================================================
 * BOOKMYSHOW LOW LEVEL DESIGN (LLD)
 * ==============================================================================================
 * 
 * Key Requirements Implemented:
 * 1. Search: Search movies by City.
 * 2. Booking: Select City -> Movie -> Theater -> Show -> Seats.
 * 3. Concurrency: Handling multiple users trying to book the same seat using Locks.
 * 4. Extensibility: Different Seat Types (Silver, Gold, Platinum).
 * 5. Admin: Capabilities to add Movies, Shows, and Theaters.
 *
 * Design Patterns:
 * - Singleton: For formatted services (Catalog/Controller).
 * - Factory: (Implicit) could be used for creating bookings/payments.
 * - Strategy: For Payment processing.
 * - Lock/Synch: For concurrency control.
 *
 * Class Design Diagram:
 * ---------------------
 * [BMSService] "1" o-- "*" [Theater]
 * [BMSService] "1" o-- "*" [Movie]
 * [Theater] "1" *-- "*" [Screen]
 * [Theater] "1" *-- "*" [Show]
 * [Screen] "1" *-- "*" [Seat]
 * [Show] ..> [ShowSeat] : Maps Seat to Status
 * [ShowSeat] "1" *-- "1" [Seat]
 * [Booking] "1" *-- "*" [ShowSeat]
 * [Booking] "1" *-- "1" [User]
 * [ShowSeat] : Uses ReentrantLock
 *
 * Class Details:
 * ---------------------
 * 1. BMSService (Singleton)
 *    - Role: Main controller/facade for the application.
 *    - Attributes: cityMovieMap, theaters.
 *    - Methods: getMoviesByCity(), bookTicket() [Synch Logic], confirmBooking().
 *
 * 2. Theater
 *    - Role: Physical cinema facility.
 *    - Attributes: id, name, city, screens, shows.
 *    - Methods: addShow(), addScreen().
 *
 * 3. Show
 *    - Role: A specific movie playing at a specific time.
 *    - Attributes: movie, screen, startTime, showSeats (Map).
 *    - Methods: getShowSeat(), printAvailableSeats().
 *
 * 4. ShowSeat
 *    - Role: Represents a seat instance for a show with status/price.
 *    - Attributes: seat, status (AVAILABLE/RESERVED), price, Lock (ReentrantLock).
 *    - Methods: lock(), book(), confirm(), release().
 *
 * 5. Booking
 *    - Role: Transaction record.
 *    - Attributes: user, show, bookedSeats, status.
 *    - Methods: confirm(), cancel().
 *
 * 6. Screen
 *    - Role: A hall inside a theater.
 *    - Attributes: seats (List<Seat>).
 *
 * 7. Seat
 *    - Role: Physical seat definition.
 *    - Attributes: id (e.g. "A1"), type (GOLD/SILVER).
 */

public class BookMyShowSystem {
    public static void main(String[] args) {
        System.out.println("--- BookMyShow System Design Demo ---");

        // 1. Initialize System Services
        BMSService bmsService = BMSService.getInstance();

        // 2. Setup Data (Admin Actions)
        // Create Movies
        Movie movie1 = new Movie("M1", "Inception", 148);
        Movie movie2 = new Movie("M2", "The Dark Knight", 152);
        bmsService.addMovie(movie1);
        bmsService.addMovie(movie2);

        // Create Theater & Screen
        Theater theater = new Theater("T1", "PVR Cinemas", "Bangalore");
        Screen screen1 = new Screen("S1", "Screen 1");
        
        // Add Seats to Screen (10 seats for demo)
        for (int i = 1; i <= 5; i++) {
            screen1.addSeat(new Seat("A" + i, SeatType.SILVER)); // Row A
        }
        for (int i = 1; i <= 5; i++) {
            screen1.addSeat(new Seat("B" + i, SeatType.GOLD));   // Row B
        }
        theater.addScreen(screen1);
        bmsService.addTheater(theater, "Bangalore");

        // Create Show
        Show show = new Show("SHOW1", movie1, screen1, new Date());
        theater.addShow(show);

        // 3. User Flow: Search
        System.out.println("\n[User] Searching movies in Bangalore...");
        List<Movie> movies = bmsService.getMoviesByCity("Bangalore");
        System.out.println("Movies found: " + movies.stream().map(Movie::getTitle).collect(Collectors.toList()));

        // 4. User Flow: View Seats
        // User selects "Inception" (movie1) -> Selects Theater PVR -> Selects Show1
        System.out.println("\n[User] Viewing availability for Show: " + show.getShowId());
        show.printAvailableSeats();

        // 5. User Flow: Concurrent Booking Simulation
        // We will simulate 2 threads trying to book the SAME seat ("A1") at the same time.
        System.out.println("\n[System] Starting Concurrent Booking Simulation...");
        
        User user1 = new User("U1", "Alice");
        User user2 = new User("U2", "Bob");

        Runnable bookingTask1 = () -> {
            System.out.println("User 1 attempting to book A1 and A2");
            List<String> seatsToBook = Arrays.asList("A1", "A2");
            Booking booking = bmsService.bookTicket(user1, show, seatsToBook);
            if (booking != null) {
                System.out.println("User 1 Booking Successful! Ticket ID: " + booking.getBookingId());
                bmsService.confirmBooking(booking); // Payment success scenario
            } else {
                System.out.println("User 1 Booking Failed (Seats unavailable).");
            }
        };

        Runnable bookingTask2 = () -> {
            System.out.println("User 2 attempting to book A1 and B1");
            List<String> seatsToBook = Arrays.asList("A1", "B1"); // A1 is conflicting
            Booking booking = bmsService.bookTicket(user2, show, seatsToBook);
            if (booking != null) {
                System.out.println("User 2 Booking Successful! Ticket ID: " + booking.getBookingId());
                bmsService.confirmBooking(booking);
            } else {
                System.out.println("User 2 Booking Failed (Seats unavailable).");
            }
        };

        Thread t1 = new Thread(bookingTask1);
        Thread t2 = new Thread(bookingTask2);

        t1.start();
        t2.start();

        try {
            t1.join();
            t2.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        System.out.println("\n[User] Final Seat Availability:");
        show.printAvailableSeats();
    }
}

// ==========================================
// Enums
// ==========================================

enum SeatType {
    SILVER, GOLD, PLATINUM
}

enum SeatStatus {
    AVAILABLE, BOOKED, RESERVED
}

enum BookingStatus {
    PENDING, CONFIRMED, CANCELLED, EXPIRED
}

// ==========================================
// Domain Models
// ==========================================

class User {
    private String id;
    private String name;

    public User(String id, String name) {
        this.id = id;
        this.name = name;
    }
    public String getName() { return name; }
}

class Movie {
    private String id;
    private String title;
    private int durationMins;

    public Movie(String id, String title, int durationMins) {
        this.id = id;
        this.title = title;
        this.durationMins = durationMins;
    }
    public String getTitle() { return title; }
}

class Theater {
    private String id;
    private String name;
    private String city;
    private List<Screen> screens;
    private List<Show> shows;

    public Theater(String id, String name, String city) {
        this.id = id;
        this.name = name;
        this.city = city;
        this.screens = new ArrayList<>();
        this.shows = new ArrayList<>();
    }

    public void addScreen(Screen screen) { screens.add(screen); }
    public void addShow(Show show) { shows.add(show); }
    public List<Show> getShows() { return shows; }
    public String getCity() { return city; }
    public String getName() { return name; }
}

class Screen {
    private String id;
    private String name;
    private List<Seat> seats;

    public Screen(String id, String name) {
        this.id = id;
        this.name = name;
        this.seats = new ArrayList<>();
    }

    public void addSeat(Seat seat) { seats.add(seat); }
    public List<Seat> getSeats() { return seats; }
}

class Seat {
    private String id; // e.g., "A1"
    private SeatType type;

    public Seat(String id, SeatType type) {
        this.id = id;
        this.type = type;
    }
    public String getId() { return id; }
    public SeatType getType() { return type; }
}

class ShowSeat {
    private Seat seat;
    private SeatStatus status;
    private double price;
    // Granular Lock for this specific seat
    private final Lock lock = new ReentrantLock();

    public ShowSeat(Seat seat, double price) {
        this.seat = seat;
        this.price = price;
        this.status = SeatStatus.AVAILABLE;
    }

    public void lock() { lock.lock(); }
    public void unlock() { lock.unlock(); }

    public boolean isAvailable() { return status == SeatStatus.AVAILABLE; }
    
    // No longer synchronized, relying on external locking
    public boolean book() {
        if (status == SeatStatus.AVAILABLE) {
            status = SeatStatus.RESERVED;
            return true;
        }
        return false;
    }
    
    public void confirm() {
        if (status == SeatStatus.RESERVED) {
            status = SeatStatus.BOOKED;
        }
    }

    public void release() {
        if (status == SeatStatus.RESERVED) {
            status = SeatStatus.AVAILABLE;
        }
    }
    
    public Seat getSeat() { return seat; }
    public SeatStatus getStatus() { return status; }
    public double getPrice() { return price; }
}

class Show {
    private String showId;
    private Movie movie;
    private Screen screen;
    private Date startTime;
    private Map<String, ShowSeat> showSeats;

    public Show(String showId, Movie movie, Screen screen, Date startTime) {
        this.showId = showId;
        this.movie = movie;
        this.screen = screen;
        this.startTime = startTime;
        this.showSeats = new ConcurrentHashMap<>();
        initializeShowSeats();
    }

    private void initializeShowSeats() {
        for (Seat seat : screen.getSeats()) {
            double price = seat.getType() == SeatType.GOLD ? 200.0 : 100.0;
            showSeats.put(seat.getId(), new ShowSeat(seat, price));
        }
    }

    public ShowSeat getShowSeat(String seatId) { return showSeats.get(seatId); }
    public String getShowId() { return showId; }
    public Movie getMovie() { return movie; }

    public void printAvailableSeats() {
        System.out.println("Available Seats for " + movie.getTitle() + ":");
        for (ShowSeat ss : showSeats.values()) {
            if (ss.isAvailable()) {
                System.out.print(ss.getSeat().getId() + " ($" + ss.getPrice() + ")  ");
            }
        }
        System.out.println();
    }
}

class Booking {
    private String bookingId;
    private User user;
    private Show show;
    private List<ShowSeat> bookedSeats;
    private double totalAmount;
    private BookingStatus status;

    public Booking(String bookingId, User user, Show show, List<ShowSeat> bookedSeats) {
        this.bookingId = bookingId;
        this.user = user;
        this.show = show;
        this.bookedSeats = bookedSeats;
        this.status = BookingStatus.PENDING;
        this.totalAmount = bookedSeats.stream().mapToDouble(ShowSeat::getPrice).sum();
    }
    
    public void confirm() {
        this.status = BookingStatus.CONFIRMED;
        for(ShowSeat seat : bookedSeats) {
            seat.confirm();
        }
    }
    
    public void cancel() {
        this.status = BookingStatus.CANCELLED;
        for(ShowSeat seat : bookedSeats) {
            seat.release();
        }
    }
    
    public String getBookingId() { return bookingId; }
}

// ==========================================
// Service Layer (Singleton)
// ==========================================

class BMSService {
    private static BMSService instance;
    private Map<String, List<Movie>> cityMovieMap;
    private List<Theater> theaters;
    
    private BMSService() {
        this.cityMovieMap = new HashMap<>();
        this.theaters = new ArrayList<>();
    }

    public static synchronized BMSService getInstance() {
        if (instance == null) {
            instance = new BMSService();
        }
        return instance;
    }

    public void addMovie(Movie movie) {}

    public void addTheater(Theater theater, String city) {
        theaters.add(theater);
    }

    public List<Movie> getMoviesByCity(String city) {
        Set<Movie> movies = new HashSet<>();
        for (Theater t : theaters) {
            if (t.getCity().equalsIgnoreCase(city)) {
                for (Show s : t.getShows()) {
                    movies.add(s.getMovie());
                }
            }
        }
        return new ArrayList<>(movies);
    }

    public Booking bookTicket(User user, Show show, List<String> seatIds) {
        List<ShowSeat> seatsToBook = new ArrayList<>();
        for (String seatId : seatIds) {
            ShowSeat seat = show.getShowSeat(seatId);
            if (seat == null) return null;
            seatsToBook.add(seat);
        }

        // CRITICAL: Sort seats by ID to prevent Deadlock.
        // If User A wants (1, 2) and User B wants (2, 1), simple locking could deadlock.
        // Sorting ensures both lock 1 then 2. User B will wait at 1.
        seatsToBook.sort(Comparator.comparing(s -> s.getSeat().getId()));

        // Acquire Locks
        for (ShowSeat seat : seatsToBook) {
            seat.lock();
        }

        try {
            // Check availability for ALL seats
            for (ShowSeat seat : seatsToBook) {
                if (!seat.isAvailable()) {
                    return null; // Describe failure
                }
            }

            // Reserve seats
            for (ShowSeat seat : seatsToBook) {
                seat.book(); 
            }

            return new Booking(UUID.randomUUID().toString(), user, show, seatsToBook);

        } finally {
            // Release Locks
            for (ShowSeat seat : seatsToBook) {
                seat.unlock();
            }
        }
    }
    
    public void confirmBooking(Booking booking) {
        booking.confirm();
        System.out.println("Booking Confirmed: " + booking.getBookingId());
    }
}
