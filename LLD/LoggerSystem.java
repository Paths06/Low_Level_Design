package com.logging.lld;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/*
 * ==============================================================================================
 * LOGGING FRAMEWORK LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Requirements Implemented:
 * 1. Support Log Levels (DEBUG, INFO, WARN, ERROR, FATAL).
 * 2. Log Format: Timestamp + Level + Message.
 * 3. Multiple Destinations: Console, File, Database (Simulated).
 * 4. Configuration: Set minimum log level and add destinations.
 * 5. Thread Safety: Handles concurrent logging.
 * 6. Extensibility: Interface-based appenders.
 *
 * Design Patterns:
 * 1. Singleton: For the central 'Logger' instance.
 * 2. Observer / Strategy: 'LogAppender' interface allows broadcasting to multiple varying implementations.
 * 3. Factory: (Implicit) Logic to create/config appenders.
 *
 * Class Design Diagram:
 * ---------------------
 * [Logger] "1" *-- "1" [LoggerConfig]
 * [LoggerConfig] "1" *-- "*" [LogAppender]
 * [LogAppender] <|.. [ConsoleAppender]
 * [LogAppender] <|.. [FileAppender]
 * [LogAppender] <|.. [DatabaseAppender]
 * [LogMessage] : Data Transfer Object
 * [LogLevel] : Enum
 *
 * Class Details:
 * ---------------------
 * 1. Logger (Singleton)
 *    - Role: Central access point for logging.
 *    - Attributes: config.
 *    - Methods: log(), debug(), info(), error(), setConfig().
 *
 * 2. LoggerConfig
 *    - Role: Holds configuration state.
 *    - Attributes: minimumLevel, appenders (List).
 *    - Methods: addAppender(), setLevel().
 *
 * 3. LogAppender (Interface)
 *    - Role: Abstraction for output destinations.
 *    - Methods: append(LogMessage).
 *
 * 4. ConsoleAppender / FileAppender
 *    - Role: Concrete implementations.
 *    - Logic: Writes formatted string to specific output (System.out, File).
 *    - Thread Safety: FileAppender must handle synchronized writes.
 * 
 * 5. LogMessage
 *    - Role: Encapsulation of log data.
 *    - Attributes: message, level, timestamp.
 */

public class LoggerSystem {
    public static void main(String[] args) {
        System.out.println("--- Logging Framework Demo ---");

        // 1. Initialize Logger
        Logger logger = Logger.getInstance();

        // 2. Configure System
        // By default, just Console, Level INFO
        logger.config().setLevel(LogLevel.DEBUG);
        logger.config().addAppender(new ConsoleAppender());
        logger.config().addAppender(new FileAppender("app_logs.txt"));

        // 3. Simple Logging
        logger.info("System initialized.");
        logger.debug("Debugging internal modules..."); // Should show because level is DEBUG
        
        // 4. Change Level Runtime
        logger.config().setLevel(LogLevel.WARNING);
        logger.info("This info message will NOT be printed.");
        logger.error("Database connection failed!");

        // 5. Concurrent Logging Simulation
        System.out.println("\n--- Starting Concurrent Logging ---");
        ExecutorService executor = Executors.newFixedThreadPool(10);
        
        Runnable logTask = () -> {
            for (int i = 0; i < 5; i++) {
                logger.warn("Thread " + Thread.currentThread().getName() + " reporting issue " + i);
            }
        };

        for (int i = 0; i < 5; i++) {
            executor.execute(logTask);
        }

        executor.shutdown();
    }
}

// ==========================================
// Enums & Models
// ==========================================

enum LogLevel {
    DEBUG(1), INFO(2), WARNING(3), ERROR(4), FATAL(5);
    
    private int val;
    LogLevel(int val) { this.val = val; }
    public int getVal() { return val; }
}

class LogMessage {
    private String content;
    private LogLevel level;
    private LocalDateTime timestamp;

    public LogMessage(LogLevel level, String content) {
        this.level = level;
        this.content = content;
        this.timestamp = LocalDateTime.now();
    }

    @Override
    public String toString() {
        return String.format("[%s] [%s] %s", timestamp, level, content);
    }
    
    public LogLevel getLevel() { return level; }
}

// ==========================================
// Appenders (Strategy / Observer)
// ==========================================

interface LogAppender {
    void append(LogMessage message);
}

class ConsoleAppender implements LogAppender {
    @Override
    public void append(LogMessage message) {
        System.out.println("CONSOLE: " + message);
    }
}

class FileAppender implements LogAppender {
    private String outputFilePath;
    // Lock for safe writing to file from multiple threads
    private final Lock lock = new ReentrantLock();

    public FileAppender(String outputFilePath) {
        this.outputFilePath = outputFilePath;
    }

    @Override
    public void append(LogMessage message) {
        lock.lock();
        try (PrintWriter out = new PrintWriter(new FileWriter(outputFilePath, true))) {
            out.println(message);
        } catch (IOException e) {
            System.err.println("Failed to write to log file: " + e.getMessage());
        } finally {
            lock.unlock();
        }
    }
}

class DatabaseAppender implements LogAppender {
    // Simulated DB Connection
    private String dbUrl;

    public DatabaseAppender(String dbUrl) {
        this.dbUrl = dbUrl;
    }

    @Override
    public void append(LogMessage message) {
        // Real impl would use JDBC
        System.out.println("DB (" + dbUrl + "): INSERT INTO LOGS VALUES ('" + message + "')");
    }
}

// ==========================================
// Configuration
// ==========================================

class LoggerConfig {
    private LogLevel minimumLevel;
    private List<LogAppender> appenders;

    public LoggerConfig() {
        this.minimumLevel = LogLevel.INFO; // Default
        this.appenders = new ArrayList<>();
    }

    public void setLevel(LogLevel level) {
        this.minimumLevel = level;
    }

    public LogLevel getLevel() {
        return minimumLevel;
    }

    public void addAppender(LogAppender appender) {
        this.appenders.add(appender);
    }

    public List<LogAppender> getAppenders() {
        return appenders;
    }
}

// ==========================================
// Logger (Singleton)
// ==========================================

class Logger {
    private static volatile Logger instance; // Volatile for double-checked locking
    private LoggerConfig config;

    private Logger() {
        this.config = new LoggerConfig();
    }

    public static Logger getInstance() {
        if (instance == null) {
            synchronized (Logger.class) {
                if (instance == null) {
                    instance = new Logger();
                }
            }
        }
        return instance;
    }

    public LoggerConfig config() {
        return config;
    }

    // Main functionality
    public void log(LogLevel level, String message) {
        if (level.getVal() >= config.getLevel().getVal()) {
            LogMessage logData = new LogMessage(level, message);
            // Notify all observers (appenders)
            for (LogAppender appender : config.getAppenders()) {
                appender.append(logData);
            }
        }
    }

    // Convenience methods
    public void debug(String message) { log(LogLevel.DEBUG, message); }
    public void info(String message) { log(LogLevel.INFO, message); }
    public void warn(String message) { log(LogLevel.WARNING, message); }
    public void error(String message) { log(LogLevel.ERROR, message); }
    public void fatal(String message) { log(LogLevel.FATAL, message); }
}
