package com.wallet.lld;

import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/*
 * ==============================================================================================
 * DIGITAL WALLET SERVICE LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Features:
 * 1. Multi-Currency Support: Balances tracked per currency.
 * 2. Payment Methods: Link Bank/Card.
 * 3. Transactions: Transfer between users, or Load/Withdraw funds.
 * 4. Currency Conversion: Exchange rates (simplified).
 * 5. Concurrency: Thread-safe balance updates.
 * 
 * Design Patterns:
 * 1. Singleton: WalletService (Facade).
 * 2. Factory: For creating Transactions.
 * 3. Strategy: PaymentMethod (Bank/Card strategy for external funding).
 *
 * Class Design Diagram:
 * ---------------------
 * [WalletService] "1" *-- "*" [User]
 * [User] "1" *-- "1" [Wallet]
 * [Wallet] "1" *-- "*" [PaymentMethod]
 * [Wallet] "1" *-- "*" [Transaction]
 * [Wallet] "1" *-- "*" [Currency] (Balance Map)
 * [Transaction] <|-- [TransferTransaction]
 * [Transaction] <|-- [TopUpTransaction]
 * [Transaction] <|-- [WithdrawTransaction]
 * 
 * Class Details:
 * ---------------------
 * 1. WalletService
 *    - Role: Facade.
 *    - Methods: registerUser(), processTransaction().
 *
 * 2. User & Wallet
 *    - Wallet holds a Map<Currency, BigDecimal> for balances.
 * 
 * 3. Transaction
 *    - Role: Immutable record.
 *    - Attributes: id, source, target, amount, currency, status.
 *
 * 4. CurrencyManager
 *    - Role: Handles rates and conversion.
 */

public class DigitalWalletSystem {
    public static void main(String[] args) {
        System.out.println("--- Digital Wallet Demo ---");
        
        WalletService service = WalletService.getInstance();

        // 1. Create Users
        User u1 = new User("U1", "Alice");
        User u2 = new User("U2", "Bob");
        service.registerUser(u1);
        service.registerUser(u2);

        // 2. Add Payment Methods
        u1.getWallet().addPaymentMethod(new BankAccount("B1", "Alice Bank", "123456"));
        
        // 3. Top Up (Load Money)
        System.out.println("\n[Transaction] Alice adds 100 USD via Bank.");
        service.processTransaction(
            TransactionFactory.createTopUp(u1, BigDecimal.valueOf(100), Currency.USD)
        );
        u1.getWallet().showBalance();

        // 4. Transfer (Same Currency)
        System.out.println("\n[Transaction] Alice sends 50 USD to Bob.");
        service.processTransaction(
            TransactionFactory.createTransfer(u1, u2, BigDecimal.valueOf(50), Currency.USD)
        );
        u1.getWallet().showBalance();
        u2.getWallet().showBalance();
        
        // 5. Currency Conversion Transfer
        // Alice (USD) sends to Bob (EUR). 
        // Logic: Alice sends 10 USD -> Converted to EUR -> Credited to Bob.
        System.out.println("\n[Transaction] Alice sends 10 USD to Bob (Converted to EUR).");
        // Note: Our TransferTransaction handles conversion if target wallet prefers/holds target currency.
        // For simplicity, let's assume sender specifies Source Currency amount.
        
        service.processTransaction(
             TransactionFactory.createTransfer(u1, u2, BigDecimal.valueOf(10), Currency.USD)
        );
        
        // Bob should have USD now, OR converted if we enforce distinct wallets. 
        // In this design, a Wallet can hold multiple currencies. Bob will just receive USD.
        // To demo conversion, let's say Alice wants to convert her remaining USD to EUR.
        
        System.out.println("\n[Action] Alice converts 20 USD to EUR internally.");
        service.convertCurrency(u1, BigDecimal.valueOf(20), Currency.USD, Currency.EUR);
        u1.getWallet().showBalance();
    }
}

// ==========================================
// Enums & Utils
// ==========================================

enum Currency { USD, EUR, INR, GBP }
enum TransactionStatus { PENDING, SUCCESS, FAILED }

class CurrencyConverter {
    private static final Map<Currency, Double> ratesToUSD = new HashMap<>();
    static {
        ratesToUSD.put(Currency.USD, 1.0);
        ratesToUSD.put(Currency.EUR, 1.1); // 1 EUR = 1.1 USD
        ratesToUSD.put(Currency.INR, 0.012); // 1 INR = 0.012 USD
    }

    public static BigDecimal convert(BigDecimal amount, Currency from, Currency to) {
        if(from == to) return amount;
        
        // Convert 'from' to USD, then USD to 'to'
        double rateFrom = ratesToUSD.get(from);
        double rateTo = ratesToUSD.get(to);
        
        double amountInUSD = amount.doubleValue() * rateFrom;
        double finalAmount = amountInUSD / rateTo;
        
        return BigDecimal.valueOf(finalAmount);
    }
}

// ==========================================
// Domain Models
// ==========================================

interface PaymentMethod {
    boolean executePayment(BigDecimal amount);
}

class BankAccount implements PaymentMethod {
    String bankName, accountNumber;
    public BankAccount(String id, String name, String num) { this.bankName = name; this.accountNumber = num; }
    
    @Override
    public boolean executePayment(BigDecimal amount) {
        System.out.println("Processing Bank Transfer of " + amount + " from " + bankName);
        return true; // Stub
    }
}

class Wallet {
    private String walletId;
    private Map<Currency, BigDecimal> balances;
    private List<PaymentMethod> paymentMethods;
    private List<Transaction> history;
    
    public Wallet(String uid) {
        this.walletId = UUID.randomUUID().toString();
        this.balances = new ConcurrentHashMap<>();
        this.paymentMethods = new ArrayList<>();
        this.history = new ArrayList<>();
    }
    
    public synchronized void deposit(BigDecimal amount, Currency currency) {
        balances.put(currency, getBalance(currency).add(amount));
    }
    
    public synchronized boolean withdraw(BigDecimal amount, Currency currency) {
        BigDecimal current = getBalance(currency);
        if(current.compareTo(amount) >= 0) {
            balances.put(currency, current.subtract(amount));
            return true;
        }
        return false;
    }
    
    public BigDecimal getBalance(Currency c) {
        return balances.getOrDefault(c, BigDecimal.ZERO);
    }
    
    public void addPaymentMethod(PaymentMethod pm) { paymentMethods.add(pm); }
    public void addTransaction(Transaction t) { history.add(t); }
    
    public void showBalance() {
        System.out.println("Wallet Balance: " + balances);
    }
}

class User {
    String id;
    String name;
    Wallet wallet;

    public User(String id, String name) {
        this.id = id; this.name = name;
        this.wallet = new Wallet(id);
    }
    public Wallet getWallet() { return wallet; }
    public String getName() { return name; }
}

// ==========================================
// Transactions
// ==========================================

abstract class Transaction {
    String id;
    Date timestamp;
    BigDecimal amount;
    Currency currency;
    TransactionStatus status;
    
    // Template Method Pattern could be used here for process()
    public Transaction(BigDecimal amt, Currency cur) {
        this.id = UUID.randomUUID().toString();
        this.timestamp = new Date();
        this.amount = amt;
        this.currency = cur;
        this.status = TransactionStatus.PENDING;
    }
    
    public abstract void execute();
}

class TopUpTransaction extends Transaction {
    User user;
    
    public TopUpTransaction(User u, BigDecimal amt, Currency cur) { 
        super(amt, cur); 
        this.user = u; 
    }
    
    @Override
    public void execute() {
        // Logic: Pull money from external source (PaymentMethod) and add to Wallet
        // Simplified: Assume default payment method exists and works
        user.getWallet().deposit(amount, currency);
        this.status = TransactionStatus.SUCCESS;
        System.out.println("TopUp Successful (" + id + ")");
    }
}

class TransferTransaction extends Transaction {
    User sender;
    User receiver;
    
    public TransferTransaction(User s, User r, BigDecimal amt, Currency cur) {
        super(amt, cur);
        this.sender = s; this.receiver = r;
    }
    
    @Override
    public void execute() {
        if(sender.getWallet().withdraw(amount, currency)) {
            receiver.getWallet().deposit(amount, currency);
            this.status = TransactionStatus.SUCCESS;
            System.out.println("Transfer Successful from " + sender.getName() + " to " + receiver.getName());
        } else {
            this.status = TransactionStatus.FAILED;
            System.out.println("Transfer Failed: Insufficient Funds");
        }
    }
}

class TransactionFactory {
    public static Transaction createTopUp(User u, BigDecimal amt, Currency cur) {
        return new TopUpTransaction(u, amt, cur);
    }
    public static Transaction createTransfer(User s, User r, BigDecimal amt, Currency cur) {
        return new TransferTransaction(s, r, amt, cur);
    }
}

// ==========================================
// Service Manager
// ==========================================

class WalletService {
    private static WalletService instance;
    private Map<String, User> users;

    private WalletService() {
        users = new HashMap<>();
    }

    public static synchronized WalletService getInstance() {
        if(instance == null) instance = new WalletService();
        return instance;
    }

    public void registerUser(User u) { users.put(u.id, u); }
    
    public void processTransaction(Transaction t) {
        t.execute();
        // Log transaction history
    }
    
    public void convertCurrency(User u, BigDecimal amount, Currency from, Currency to) {
        if(u.getWallet().withdraw(amount, from)) {
             BigDecimal converted = CurrencyConverter.convert(amount, from, to);
             u.getWallet().deposit(converted, to);
             System.out.println("Converted " + amount + " " + from + " to " + String.format("%.2f", converted) + " " + to);
        } else {
            System.out.println("Conversion Failed: Insufficient " + from);
        }
    }
}
