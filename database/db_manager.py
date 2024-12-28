import sqlite3
import hashlib
import random
import time
import os
import threading
from typing import Optional, Tuple, List, Dict
from queue import Queue
from threading import Lock, Semaphore

class DatabaseManager:
    _instance = None
    _lock = Lock()
    _connection_pool = Queue(maxsize=10)  # Connection pool with max 10 connections
    _initialized = False
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        with self._lock:
            if not self._initialized:
                self._initialized = True
                self.db_name = "user_database.db"
                self._init_connection_pool()
                self.create_tables()
                self.initialize_products()
                self.initialize_customers()
    
    def _init_connection_pool(self):
        """Initialize the connection pool"""
        try:
            for _ in range(10):  # Create 10 connections
                conn = sqlite3.connect(self.db_name, timeout=30, check_same_thread=False)
                conn.execute("PRAGMA busy_timeout = 30000")
                conn.execute("PRAGMA journal_mode = WAL")
                self._connection_pool.put(conn)
        except Exception as e:
            print(f"Error initializing connection pool: {e}")
            raise
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool with timeout"""
        try:
            return self._connection_pool.get(timeout=30)
        except Exception as e:
            print(f"Error getting connection: {e}")
            raise
    
    def _return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool"""
        try:
            if self._connection_pool.qsize() < 10:  # Check if pool is not full
                self._connection_pool.put(conn)
            else:
                conn.close()
        except Exception as e:
            print(f"Error returning connection: {e}")
            try:
                conn.close()
            except:
                pass
    
    def execute_transaction(self, func, *args, **kwargs):
        """Execute a function within a transaction"""
        conn = None
        try:
            conn = self._get_connection()
            conn.execute("BEGIN IMMEDIATE")
            result = func(conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            print(f"Transaction error: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def create_tables(self):
        """Create database tables"""
        def _do_create_tables(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL
                    )
                ''')
                
                # Create customers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS customers (
                        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_name TEXT NOT NULL,
                        budget REAL NOT NULL,
                        customer_type TEXT NOT NULL,
                        total_spent REAL DEFAULT 0,
                        username TEXT UNIQUE,
                        FOREIGN KEY (username) REFERENCES users(username)
                    )
                ''')
                
                # Create products table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS products (
                        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_name TEXT NOT NULL,
                        stock INTEGER NOT NULL,
                        price REAL NOT NULL,
                        version INTEGER DEFAULT 1
                    )
                ''')
                
                # Create orders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                        FOREIGN KEY (product_id) REFERENCES products(product_id)
                    )
                ''')
                
                # Create admin user if not exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
                if cursor.fetchone()[0] == 0:
                    hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
                    cursor.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        ("admin", hashed_password, "admin")
                    )
                
                return True
                
            except Exception as e:
                print(f"Error in _do_create_tables: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_create_tables)
        except Exception as e:
            print(f"Error in create_tables: {e}")
            return False
    
    def initialize_products(self):
        """Initialize the default products"""
        def _do_initialize_products(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                # Delete existing products
                cursor.execute("DELETE FROM products")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='products'")
                
                # Default products
                default_products = [
                    ("Product1", 500, 100),
                    ("Product2", 10, 50),
                    ("Product3", 200, 45),
                    ("Product4", 75, 75),
                    ("Product5", 0, 500)
                ]
                
                # Add default products
                cursor.executemany(
                    "INSERT INTO products (product_name, stock, price) VALUES (?, ?, ?)",
                    default_products
                )
                
                return True
                
            except Exception as e:
                print(f"Error in _do_initialize_products: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_initialize_products)
        except Exception as e:
            print(f"Error in initialize_products: {e}")
            return False
    
    def initialize_customers(self):
        """Initialize random customers"""
        def _do_initialize_customers(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                # Delete existing customers
                cursor.execute("DELETE FROM customers")
                cursor.execute("DELETE FROM users WHERE role = 'customer'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='customers'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='users'")
                
                # Generate random number of customers (5-10)
                num_customers = random.randint(5, 10)
                
                # Generate random number of premium customers (at least 2)
                premium_count = random.randint(2, max(2, num_customers - 1))
                standard_count = num_customers - premium_count
                
                # Add premium customers
                for i in range(premium_count):
                    customer_name = f"customer{i+1}"
                    budget = round(random.uniform(500, 3000), 2)
                    username = customer_name
                    password = "1234"
                    
                    # Add user account
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    cursor.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        (username, hashed_password, "customer")
                    )
                    
                    # Add customer details
                    cursor.execute('''
                        INSERT INTO customers (customer_name, budget, customer_type, username)
                        VALUES (?, ?, ?, ?)
                    ''', (customer_name, budget, "Premium", username))
                
                # Add standard customers
                for i in range(standard_count):
                    customer_name = f"customer{i+premium_count+1}"
                    budget = round(random.uniform(500, 3000), 2)
                    username = customer_name
                    password = "1234"
                    
                    # Add user account
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    cursor.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        (username, hashed_password, "customer")
                    )
                    
                    # Add customer details
                    cursor.execute('''
                        INSERT INTO customers (customer_name, budget, customer_type, username)
                        VALUES (?, ?, ?, ?)
                    ''', (customer_name, budget, "Standard", username))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_initialize_customers: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_initialize_customers)
        except Exception as e:
            print(f"Error in initialize_customers: {e}")
            return False
    
    def verify_user(self, username: str, password: str) -> Optional[Tuple[bool, str]]:
        """Verify user credentials"""
        def _do_verify_user(conn: sqlite3.Connection, username: str, password: str) -> Optional[Tuple[bool, str]]:
            try:
                cursor = conn.cursor()
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                
                cursor.execute(
                    "SELECT password, role FROM users WHERE username = ?",
                    (username,)
                )
                result = cursor.fetchone()
                
                if result and result[0] == hashed_password:
                    return True, result[1]
                return False, None
                
            except Exception as e:
                print(f"Error in _do_verify_user: {e}")
                return None
        
        try:
            return self.execute_transaction(_do_verify_user, username, password)
        except Exception as e:
            print(f"Error in verify_user: {e}")
            return None
    
    def get_customer_details(self, username: str) -> Optional[dict]:
        """Get customer details"""
        def _do_get_customer_details(conn: sqlite3.Connection, username: str) -> Optional[dict]:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT customer_id, customer_name, budget, customer_type, total_spent
                    FROM customers
                    WHERE username = ?
                ''', (username,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        "customer_id": result[0],
                        "customer_name": result[1],
                        "budget": result[2],
                        "customer_type": result[3],
                        "total_spent": result[4]
                    }
                return None
                
            except Exception as e:
                print(f"Error in _do_get_customer_details: {e}")
                return None
        
        try:
            return self.execute_transaction(_do_get_customer_details, username)
        except Exception as e:
            print(f"Error in get_customer_details: {e}")
            return None
    
    def get_all_products(self) -> List[dict]:
        """Get all products"""
        def _do_get_all_products(conn: sqlite3.Connection) -> List[dict]:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT product_id, product_name, stock, price
                    FROM products
                    ORDER BY product_id
                ''')
                results = cursor.fetchall()
                
                return [{
                    "product_id": row[0],
                    "product_name": row[1],
                    "stock": row[2],
                    "price": row[3]
                } for row in results]
            except Exception as e:
                print(f"Error in _do_get_all_products: {e}")
                return []
        
        try:
            return self.execute_transaction(_do_get_all_products)
        except Exception as e:
            print(f"Error in get_all_products: {e}")
            return []
    
    def place_order(self, customer_id: int, product_id: int, quantity: int) -> bool:
        """Yeni sipariş oluştur - sadece sipariş kaydı oluşturur, stok ve bütçe güncellemesi yapmaz"""
        def _do_place_order(conn: sqlite3.Connection, customer_id: int, product_id: int, quantity: int) -> bool:
            try:
                cursor = conn.cursor()
                
                # Get product details
                cursor.execute('''
                    SELECT product_name, stock, price
                    FROM products
                    WHERE product_id = ?
                ''', (product_id,))
                
                product = cursor.fetchone()
                if not product:
                    return False
                    
                product_name, stock, price = product
                
                # Stok kontrolü
                if stock < quantity:
                    return False
                
                # Get customer details
                cursor.execute('''
                    SELECT budget, customer_type
                    FROM customers
                    WHERE customer_id = ?
                ''', (customer_id,))
                
                customer = cursor.fetchone()
                if not customer:
                    return False
                
                budget, customer_type = customer
                total_cost = price * quantity
                
                # Bütçe kontrolü
                if budget < total_cost:
                    return False
                
                # Create order
                cursor.execute('''
                    INSERT INTO orders (customer_id, product_id, quantity, status)
                    VALUES (?, ?, ?, 'pending')
                ''', (customer_id, product_id, quantity))
                
                # Add log
                cursor.execute('''
                    INSERT INTO logs (customer_id, log_type, customer_type, product,
                                    quantity, result_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (customer_id, "Order Created", customer_type, product_name,
                      quantity, f"Order created successfully. Awaiting admin approval."))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_place_order: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_place_order, customer_id, product_id, quantity)
        except Exception as e:
            print(f"Error in place_order: {e}")
            return False
            
    def get_all_customers(self) -> List[dict]:
        """Get all customers with their details"""
        def _do_get_all_customers(conn: sqlite3.Connection) -> List[dict]:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT customer_id, customer_name, budget, customer_type, total_spent, username
                    FROM customers
                    ORDER BY customer_id
                ''')
                results = cursor.fetchall()
                
                return [{
                    "customer_id": row[0],
                    "customer_name": row[1],
                    "budget": row[2],
                    "customer_type": row[3],
                    "total_spent": row[4],
                    "username": row[5]
                } for row in results]
                
            except Exception as e:
                print(f"Error in _do_get_all_customers: {e}")
                return []
        
        try:
            return self.execute_transaction(_do_get_all_customers)
        except Exception as e:
            print(f"Error in get_all_customers: {e}")
            return []
            
    def get_pending_orders(self) -> list:
        """Bekleyen tüm siparişleri getir"""
        def _do_get_pending_orders(conn: sqlite3.Connection) -> list:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT o.order_id, o.customer_id, c.customer_type, o.product_id,
                           p.product_name, o.quantity, o.order_time,
                           ROUND((julianday('now') - julianday(o.order_time)) * 86400) as wait_time
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    JOIN products p ON o.product_id = p.product_id
                    WHERE o.status = 'pending'
                ''')
                return cursor.fetchall()
            except Exception as e:
                print(f"Error in _do_get_pending_orders: {e}")
                return []

        try:
            return self.execute_transaction(_do_get_pending_orders)
        except Exception as e:
            print(f"Error in get_pending_orders: {e}")
            return []
            
    def get_recent_logs(self, limit: int = 100) -> List[dict]:
        """Get recent logs with details"""
        def _do_get_recent_logs(conn: sqlite3.Connection, limit: int) -> List[dict]:
            try:
                cursor = conn.cursor()
                
                # Create logs table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS logs (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER,
                        log_type TEXT NOT NULL,
                        customer_type TEXT,
                        product TEXT,
                        quantity INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        result_message TEXT,
                        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                    )
                ''')
                
                # Get recent logs
                cursor.execute('''
                    SELECT l.log_id, l.customer_id, c.customer_name, l.log_type,
                           l.customer_type, l.product, l.quantity, l.timestamp,
                           l.result_message
                    FROM logs l
                    LEFT JOIN customers c ON l.customer_id = c.customer_id
                    ORDER BY l.timestamp DESC
                    LIMIT ?
                ''', (limit,))
                results = cursor.fetchall()
                
                return [{
                    "log_id": row[0],
                    "customer_id": row[1],
                    "customer_name": row[2] if row[2] else "System",
                    "log_type": row[3],
                    "customer_type": row[4],
                    "product": row[5],
                    "quantity": row[6],
                    "timestamp": row[7],
                    "result_message": row[8]
                } for row in results]
                
            except Exception as e:
                print(f"Error in _do_get_recent_logs: {e}")
                return []
        
        try:
            return self.execute_transaction(_do_get_recent_logs, limit)
        except Exception as e:
            print(f"Error in get_recent_logs: {e}")
            return []
            
    def add_log(self, customer_id: Optional[int], log_type: str, customer_type: Optional[str],
                product: Optional[str], quantity: Optional[int], result_message: str) -> bool:
        """Add a new log entry"""
        def _do_add_log(conn: sqlite3.Connection, customer_id: Optional[int], log_type: str,
                       customer_type: Optional[str], product: Optional[str],
                       quantity: Optional[int], result_message: str) -> bool:
            try:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO logs (customer_id, log_type, customer_type, product,
                                    quantity, result_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (customer_id, log_type, customer_type, product, quantity, result_message))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_add_log: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_add_log, customer_id, log_type,
                                         customer_type, product, quantity, result_message)
        except Exception as e:
            print(f"Error in add_log: {e}")
            return False
            
    def process_order(self, order_id: int) -> bool:
        """Siparişi işle - stok ve bütçe güncellemesi yapar"""
        def _do_process_order(conn: sqlite3.Connection, order_id: int) -> bool:
            try:
                cursor = conn.cursor()
                
                # Get order details with product and customer info
                cursor.execute('''
                    SELECT o.customer_id, c.customer_type, o.product_id, p.product_name,
                           o.quantity, o.status, p.price, p.version, p.stock,
                           c.budget
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    JOIN products p ON o.product_id = p.product_id
                    WHERE o.order_id = ? AND o.status = 'pending'
                ''', (order_id,))
                
                order = cursor.fetchone()
                if not order:
                    return False
                
                customer_id, customer_type, product_id, product_name, quantity, status, \
                price, version, current_stock, current_budget = order
                
                total_cost = price * quantity
                
                # Son kontroller
                if current_stock < quantity:
                    cursor.execute('''
                        UPDATE orders SET status = 'failed'
                        WHERE order_id = ?
                    ''', (order_id,))
                    
                    cursor.execute('''
                        INSERT INTO logs (customer_id, log_type, customer_type, product,
                                        quantity, result_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (customer_id, "Error", customer_type, product_name,
                          quantity, f"Order {order_id} failed: Insufficient stock"))
                    return False
                
                if current_budget < total_cost:
                    cursor.execute('''
                        UPDATE orders SET status = 'failed'
                        WHERE order_id = ?
                    ''', (order_id,))
                    
                    cursor.execute('''
                        INSERT INTO logs (customer_id, log_type, customer_type, product,
                                        quantity, result_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (customer_id, "Error", customer_type, product_name,
                          quantity, f"Order {order_id} failed: Insufficient budget"))
                    return False
                
                # Update stock with optimistic locking
                cursor.execute('''
                    UPDATE products
                    SET stock = stock - ?, version = version + 1
                    WHERE product_id = ? AND version = ? AND stock >= ?
                ''', (quantity, product_id, version, quantity))
                
                if cursor.rowcount == 0:
                    return False
                
                # Update customer budget and total spent
                cursor.execute('''
                    UPDATE customers
                    SET budget = budget - ?,
                        total_spent = total_spent + ?
                    WHERE customer_id = ? AND budget >= ?
                ''', (total_cost, total_cost, customer_id, total_cost))
                
                if cursor.rowcount == 0:
                    return False
                
                # Update order status
                cursor.execute('''
                    UPDATE orders
                    SET status = 'processed'
                    WHERE order_id = ?
                ''', (order_id,))
                
                # Add success log
                cursor.execute('''
                    INSERT INTO logs (customer_id, log_type, customer_type, product,
                                    quantity, result_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (customer_id, "Order Processed", customer_type, product_name,
                      quantity, f"Order {order_id} processed successfully"))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_process_order: {e}")
                
                # Log error
                try:
                    cursor.execute('''
                        INSERT INTO logs (customer_id, log_type, customer_type, product,
                                        quantity, result_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (customer_id, "Error", customer_type, product_name,
                          quantity, f"Order {order_id} failed: {str(e)}"))
                except:
                    pass
                    
                return False
        
        try:
            return self.execute_transaction(_do_process_order, order_id)
        except Exception as e:
            print(f"Error in process_order: {e}")
            return False
            
    def process_all_orders(self) -> Tuple[int, int]:
        """Process all pending orders, returns (success_count, failed_count)"""
        def _do_process_all_orders(conn: sqlite3.Connection) -> Tuple[int, int]:
            try:
                cursor = conn.cursor()
                
                # Get all pending orders sorted by priority
                cursor.execute('''
                    SELECT o.order_id, o.customer_id, c.customer_type, o.product_id,
                           p.product_name, o.quantity, o.order_time,
                           ROUND((julianday('now') - julianday(o.order_time)) * 86400) as wait_time
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    JOIN products p ON o.product_id = p.product_id
                    WHERE o.status = 'pending'
                    ORDER BY 
                        CASE WHEN c.customer_type = 'Premium' THEN 1 ELSE 2 END,
                        wait_time DESC
                ''')
                
                orders = cursor.fetchall()
                success_count = 0
                failed_count = 0
                
                for order in orders:
                    order_id, customer_id, customer_type, product_id, product_name, quantity, order_time, wait_time = order
                    
                    # Calculate priority score
                    customer_type_multiplier = 2.0 if customer_type == "Premium" else 1.0
                    priority_score = customer_type_multiplier * (1.0 + wait_time / 3600.0)
                    
                    try:
                        # Update order status
                        cursor.execute('''
                            UPDATE orders
                            SET status = 'processed'
                            WHERE order_id = ?
                        ''', (order_id,))
                        
                        # Add detailed log entry with priority information
                        log_message = (
                            f"Order {order_id} processed | "
                            f"Priority: {priority_score:.2f} | "
                            f"Wait: {wait_time:.0f}s | "
                            f"Multiplier: {customer_type_multiplier:.1f}x"
                        )
                        
                        cursor.execute('''
                            INSERT INTO logs (customer_id, log_type, customer_type, product,
                                            quantity, result_message)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (customer_id, "Order Processed", customer_type, product_name,
                              quantity, log_message))
                        
                        success_count += 1
                        
                    except Exception as e:
                        print(f"Error processing order {order_id}: {e}")
                        failed_count += 1
                        
                        # Add error log with priority information
                        try:
                            error_message = (
                                f"Failed to process order {order_id} | "
                                f"Priority: {priority_score:.2f} | "
                                f"Wait: {wait_time:.0f}s | "
                                f"Error: {str(e)}"
                            )
                            
                            cursor.execute('''
                                INSERT INTO logs (customer_id, log_type, customer_type, product,
                                                quantity, result_message)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (customer_id, "Error", customer_type, product_name,
                                  quantity, error_message))
                        except:
                            pass
                
                # Add summary log
                if orders:
                    summary_message = (
                        f"Batch processing completed | "
                        f"Total: {len(orders)} | "
                        f"Success: {success_count} | "
                        f"Failed: {failed_count} | "
                        f"Order: Premium first, then by wait time"
                    )
                    
                    cursor.execute('''
                        INSERT INTO logs (log_type, result_message)
                        VALUES (?, ?)
                    ''', ("System", summary_message))
                
                return success_count, failed_count
                
            except Exception as e:
                print(f"Error in _do_process_all_orders: {e}")
                return 0, 0
        
        try:
            return self.execute_transaction(_do_process_all_orders)
        except Exception as e:
            print(f"Error in process_all_orders: {e}")
            return 0, 0
            
    def create_test_orders(self) -> bool:
        """Test için örnek siparişler oluştur"""
        def _do_create_test_orders(conn: sqlite3.Connection) -> bool:
            try:
                cursor = conn.cursor()
                
                # Mevcut müşterileri al
                cursor.execute("SELECT customer_id, customer_type FROM customers")
                customers = cursor.fetchall()
                
                # Mevcut ürünleri al
                cursor.execute("SELECT product_id FROM products WHERE stock > 0")
                products = cursor.fetchall()
                
                # Test siparişleri oluştur
                for i, customer in enumerate(customers):
                    customer_id, customer_type = customer
                    product_id = products[i % len(products)][0]
                    quantity = random.randint(1, 5)
                    
                    # Farklı zamanlarda oluşturulmuş gibi görünmesi için
                    time_offset = random.randint(0, 3600)  # 0-1 saat arası
                    order_time = time.strftime(
                        '%Y-%m-%d %H:%M:%S',
                        time.localtime(time.time() - time_offset)
                    )
                    
                    cursor.execute('''
                        INSERT INTO orders (customer_id, product_id, quantity, order_time, status)
                        VALUES (?, ?, ?, ?, 'pending')
                    ''', (customer_id, product_id, quantity, order_time))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_create_test_orders: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_create_test_orders)
        except Exception as e:
            print(f"Error in create_test_orders: {e}")
            return False
            
    def delete_product(self, product_id: int) -> bool:
        """Ürünü sil"""
        def _do_delete_product(conn: sqlite3.Connection, product_id: int) -> bool:
            try:
                cursor = conn.cursor()
                
                # Önce ürünün var olduğunu kontrol et
                cursor.execute("SELECT product_name FROM products WHERE product_id = ?", (product_id,))
                if not cursor.fetchone():
                    return False
                
                # Ürünü sil
                cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
                return True
                
            except Exception as e:
                print(f"Error in _do_delete_product: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_delete_product, product_id)
        except Exception as e:
            print(f"Error in delete_product: {e}")
            return False
            
    def update_stock(self, product_id: int, new_stock: int) -> bool:
        """Ürün stok miktarını güncelle"""
        def _do_update_stock(conn: sqlite3.Connection, product_id: int, new_stock: int) -> bool:
            try:
                cursor = conn.cursor()
                
                # Önce ürünün var olduğunu kontrol et
                cursor.execute("SELECT product_name FROM products WHERE product_id = ?", (product_id,))
                if not cursor.fetchone():
                    return False
                
                # Stok miktarını güncelle
                cursor.execute('''
                    UPDATE products 
                    SET stock = ?, version = version + 1
                    WHERE product_id = ?
                ''', (new_stock, product_id))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_update_stock: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_update_stock, product_id, new_stock)
        except Exception as e:
            print(f"Error in update_stock: {e}")
            return False
            
    def update_price(self, product_id: int, new_price: float) -> bool:
        """Ürün fiyatını güncelle"""
        def _do_update_price(conn: sqlite3.Connection, product_id: int, new_price: float) -> bool:
            try:
                cursor = conn.cursor()
                
                # Önce ürünün var olduğunu kontrol et
                cursor.execute("SELECT product_name FROM products WHERE product_id = ?", (product_id,))
                if not cursor.fetchone():
                    return False
                
                # Fiyatı güncelle
                cursor.execute('''
                    UPDATE products 
                    SET price = ?, version = version + 1
                    WHERE product_id = ?
                ''', (new_price, product_id))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_update_price: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_update_price, product_id, new_price)
        except Exception as e:
            print(f"Error in update_price: {e}")
            return False
            
    def get_customer_orders(self, customer_id: int) -> List[Dict]:
        """Müşterinin siparişlerini getir"""
        def _do_get_customer_orders(conn: sqlite3.Connection, customer_id: int) -> List[Dict]:
            try:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        o.order_id,
                        p.product_name,
                        o.quantity,
                        o.status,
                        o.order_time,
                        CAST((julianday('now') - julianday(o.order_time)) * 24 * 60 * 60 AS INTEGER) as wait_time
                    FROM orders o
                    JOIN products p ON o.product_id = p.product_id
                    WHERE o.customer_id = ?
                    ORDER BY o.order_time DESC
                ''', (customer_id,))
                
                orders = []
                for row in cursor.fetchall():
                    orders.append({
                        'order_id': row[0],
                        'product_name': row[1],
                        'quantity': row[2],
                        'status': row[3],
                        'order_time': row[4],
                        'wait_time': row[5]
                    })
                
                return orders
                
            except Exception as e:
                print(f"Error in _do_get_customer_orders: {e}")
                return []
        
        try:
            return self.execute_transaction(_do_get_customer_orders, customer_id)
        except Exception as e:
            print(f"Error in get_customer_orders: {e}")
            return []
            
    def add_product(self, product_name: str, stock: int, price: float) -> bool:
        """Yeni ürün ekle"""
        def _do_add_product(conn: sqlite3.Connection, product_name: str, stock: int, price: float) -> bool:
            try:
                cursor = conn.cursor()
                
                # Ürünü ekle
                cursor.execute('''
                    INSERT INTO products (product_name, stock, price)
                    VALUES (?, ?, ?)
                ''', (product_name, stock, price))
                
                return True
                
            except Exception as e:
                print(f"Error in _do_add_product: {e}")
                return False
        
        try:
            return self.execute_transaction(_do_add_product, product_name, stock, price)
        except Exception as e:
            print(f"Error in add_product: {e}")
            return False 