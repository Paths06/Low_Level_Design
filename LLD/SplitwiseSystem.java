package com.splitwise.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/*
 * ==============================================================================================
 * SPLITWISE LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Features:
 * 1. User/Group Management: Create users, create groups, add members.
 * 2. Expense Management: Add expenses with Equal, Exact, or Percentage splits.
 * 3. Balance Calculation: Automatically calculate "Who owes Whom" (Positive/Negative offsets).
 * 4. Settlement: Logic for users to pay back and clear debts.
 * 
 * Design Patterns:
 * 1. Singleton: SplitwiseService (Facade).
 * 2. Strategy: SplitStrategy (HANDLES Equal, Exact, Percent logic).
 * 3. Factory: SplitFactory (Creates Split objects).
 *
 * Class Design Diagram:
 * ---------------------
 * [SplitwiseService] "1" *-- "*" [User]
 * [SplitwiseService] "1" *-- "*" [Group]
 * [Group] "1" *-- "*" [Expense]
 * [Expense] "1" *-- "*" [Split]
 * [Expense] "1" *-- "1" [User] (PaidBy)
 * [Split] <|-- [EqualSplit]
 * [Split] <|-- [ExactSplit]
 * [Split] <|-- [PercentSplit]
 * [User] ..> [BalanceSheet] (Map<User, Double>)
 *
 * Class Details:
 * ---------------------
 * 1. SplitwiseService (Singleton)
 *    - Role: Main controller.
 *    - Methods: addExpense(), settleBalance(), showBalance().
 * 
 * 2. Expense
 *    - Role: Represents a transaction.
 *    - Attributes: amount, paidBy, splits (List), splitType.
 *
 * 3. Split (Abstract)
 *    - Role: Represents a share of an expense.
 *    - Attributes: user, amount.
 *    - Subclasses: EqualSplit, ExactSplit, PercentSplit (has 'percent' field).
 *
 * 4. SplitType (Enum)
 *    - Types: EQUAL, EXACT, PERCENT.
 *
 * 5. User
 *    - Role: Participant.
 *    - Attributes: id, name, email.
 */

public class SplitwiseSystem {
    public static void main(String[] args) {
        System.out.println("--- Splitwise System Demo ---");
        
        SplitwiseService service = SplitwiseService.getInstance();

        // 1. Create Users
        User u1 = new User("U1", "Alice", "alice@test.com", "9999");
        User u2 = new User("U2", "Bob", "bob@test.com", "8888");
        User u3 = new User("U3", "Charlie", "charlie@test.com", "7777");
        
        service.addUser(u1); service.addUser(u2); service.addUser(u3);

        // 2. Create Group
        Group g1 = new Group("G1", "Trip");
        g1.addMember(u1); g1.addMember(u2); g1.addMember(u3);
        service.addGroup(g1);

        // 3. Add Expense: EQUAL SPLIT
        // Alice pays 300, split equally among Alice, Bob, Charlie (100 each)
        System.out.println("\n[Transaction] Alice pays 300 for Lunch (Equal Split)");
        List<Split> splits1 = new ArrayList<>();
        splits1.add(new EqualSplit(u1));
        splits1.add(new EqualSplit(u2));
        splits1.add(new EqualSplit(u3));
        
        service.addExpense("Lunch", 300, u1, splits1, SplitType.EQUAL);
        
        service.showBalance(u2.getId()); // Bob should owe Alice 100
        service.showBalance(u3.getId()); // Charlie should owe Alice 100

        // 4. Add Expense: EXACT SPLIT
        // Bob pays 1000, Alice owes 300, Charlie owes 700. (Bob owes 0 to self)
        System.out.println("\n[Transaction] Bob pays 1000 for Cab (Exact: Alice 300, Charlie 700)");
        List<Split> splits2 = new ArrayList<>();
        splits2.add(new ExactSplit(u1, 300));
        splits2.add(new ExactSplit(u3, 700));
        
        service.addExpense("Cab", 1000, u2, splits2, SplitType.EXACT);
        
        // 5. Add Expense: PERCENT SPLIT
        // Charlie pays 500. Alice 50%, Bob 20%, Charlie 30%.
        System.out.println("\n[Transaction] Charlie pays 500 for Party (Percent: Alice 50%, Bob 20%, Charlie 30%)");
        List<Split> splits3 = new ArrayList<>();
        splits3.add(new PercentSplit(u1, 50.0));
        splits3.add(new PercentSplit(u2, 20.0));
        splits3.add(new PercentSplit(u3, 30.0));
        
        service.addExpense("Party", 500, u3, splits3, SplitType.PERCENT);

        // 6. Show Final Balances
        System.out.println("\n--- Balances Before Settlement ---");
        service.showBalance(u1.getId());
        
        // 7. Settle Debt
        // Alice owes Charlie some amount. Let's say she pays 200 to Charlie.
        System.out.println("\n[Transaction] Alice pays 200 to Charlie to settle part of the debt");
        service.settleBalance(u1, u3, 200.0);
        
        System.out.println("\n--- Final Balances After Settlement ---");
        service.showBalance(u1.getId());
        service.showBalance(u2.getId());
        service.showBalance(u3.getId());
    }
}

// ==========================================
// Enums & Strategy
// ==========================================

enum SplitType { EQUAL, EXACT, PERCENT }

abstract class Split {
    User user;
    double amount;
    
    public Split(User user) { this.user = user; }
    public double getAmount() { return amount; }
    public void setAmount(double amount) { this.amount = amount; }
    public User getUser() { return user; }
}

class EqualSplit extends Split {
    public EqualSplit(User user) { super(user); }
}

class ExactSplit extends Split {
    public ExactSplit(User user, double amount) { 
        super(user); 
        this.amount = amount;
    }
}

class PercentSplit extends Split {
    double percent;
    public PercentSplit(User user, double percent) { 
        super(user); 
        this.percent = percent;
    }
    public double getPercent() { return percent; }
}

// ==========================================
// Domain Models
// ==========================================

class User {
    private String id;
    private String name;
    
    // Helper to print nice output (Who owes Whom)
    // Map<OtherUserID, Amount> -> +ive means User gets back, -ive means User owes
    // Actually, simpler is: userExpenseSheet: Map<User, Double>
    
    public User(String id, String name, String email, String phone) {
        this.id = id; this.name = name;
    }
    public String getId() { return id; }
    public String getName() { return name; }
}

class Group {
    String id;
    String name;
    List<User> members;
    List<Expense> expenses;

    public Group(String id, String name) {
        this.id = id; this.name = name;
        this.members = new ArrayList<>();
        this.expenses = new ArrayList<>();
    }
    public void addMember(User u) { members.add(u); }
    public void addExpense(Expense e) { expenses.add(e); }
}

class Expense {
    String id;
    String description;
    double amount;
    User paidBy;
    SplitType splitType;
    List<Split> splits;

    public Expense(String id, String desc, double amount, User paidBy, SplitType type, List<Split> splits) {
        this.id = id; this.description = desc; this.amount = amount;
        this.paidBy = paidBy; this.splitType = type; this.splits = splits;
    }
}

// ==========================================
// Service (Singleton)
// ==========================================

class SplitwiseService {
    private static SplitwiseService instance;
    private Map<String, User> users;
    private Map<String, Group> groups;
    
    // Balance Sheet: Map<User1, Map<User2, Double>>
    // User1 owes/gets User2 Amount. 
    // If > 0, User1 gets from User2. If < 0, User1 owes User2.
    private Map<String, Map<String, Double>> balanceSheet;

    private SplitwiseService() {
        users = new ConcurrentHashMap<>();
        groups = new ConcurrentHashMap<>();
        balanceSheet = new ConcurrentHashMap<>();
    }

    public static synchronized SplitwiseService getInstance() {
        if(instance == null) instance = new SplitwiseService();
        return instance;
    }

    public void addUser(User u) { 
        users.put(u.getId(), u); 
        balanceSheet.put(u.getId(), new HashMap<>());
    }
    public void addGroup(Group g) { groups.put(g.id, g); }

    public void addExpense(String desc, double amount, User paidBy, List<Split> splits, SplitType type) {
        // Validate Splits based on Type
        if(type == SplitType.EQUAL) {
            double splitAmount = amount / splits.size();
            for(Split s : splits) s.setAmount(splitAmount);
        } 
        else if (type == SplitType.PERCENT) {
            for(Split s : splits) {
                PercentSplit ps = (PercentSplit) s;
                double splitAmount = (amount * ps.getPercent()) / 100.0;
                s.setAmount(splitAmount);
            }
        }
        // For EXACT, amount is already set in Split
        
        // Update Balances
        for(Split split : splits) {
            User paidTo = split.getUser();
            double splitAmt = split.getAmount();
            
            // Should not add debt to self
            if(!paidBy.getId().equals(paidTo.getId())) {
                updateBalance(paidBy.getId(), paidTo.getId(), splitAmt);
                updateBalance(paidTo.getId(), paidBy.getId(), -splitAmt);
            }
        }
        
        System.out.println("Expense Added: " + desc);
    }
    
    // Settlement: User 'paidBy' pays 'paidTo' to clear debt
    public void settleBalance(User paidBy, User paidTo, double amount) {
        updateBalance(paidBy.getId(), paidTo.getId(), amount); // Payer is 'giving' money, so they get positive offset vs Payee
        updateBalance(paidTo.getId(), paidBy.getId(), -amount);
        System.out.println("Settled: " + paidBy.getName() + " paid " + amount + " to " + paidTo.getName());
    }
    
    private void updateBalance(String u1, String u2, double amount) {
        Map<String, Double> u1Balances = balanceSheet.get(u1);
        u1Balances.put(u2, u1Balances.getOrDefault(u2, 0.0) + amount);
    }

    public void showBalance(String userId) {
        Map<String, Double> balances = balanceSheet.get(userId);
        boolean isEmpty = true;
        for(Map.Entry<String, Double> entry : balances.entrySet()) {
            // Only show non-zero balances
            if(Math.abs(entry.getValue()) > 0.01) { 
                isEmpty = false;
                printBalance(userId, entry.getKey(), entry.getValue());
            }
        }
        if(isEmpty) System.out.println("No balances for " + users.get(userId).getName());
    }

    private void printBalance(String u1, String u2, double amount) {
        String user1Name = users.get(u1).getName();
        String user2Name = users.get(u2).getName();
        if(amount > 0) {
            System.out.println(user1Name + " gets " + String.format("%.2f", amount) + " from " + user2Name);
        } else if (amount < 0) {
            System.out.println(user1Name + " owes " + String.format("%.2f", Math.abs(amount)) + " to " + user2Name);
        }
    }
}
