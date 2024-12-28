import tkinter as tk
from tkinter import ttk, messagebox
from auth.auth_manager import AuthManager
from database.db_manager import DatabaseManager

class CustomerPanel:
    def __init__(self, root: tk.Tk, auth_manager: AuthManager, username: str):
        # Store root reference
        self.root = root
        
        # Create main window
        self.window = tk.Toplevel(root)
        self.window.title(f"Customer Panel - {username}")
        self.window.geometry("1200x800")
        self.window.minsize(1000, 600)
        
        # Configure window grid weights
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        
        # Critical state flags
        self._is_closing = False
        self._is_focused = True
        self._refresh_enabled = True
        
        # Initialize managers
        self.auth_manager = auth_manager
        self.db_manager = DatabaseManager()
        self.username = username
        
        # Get customer details
        self.customer_details = self.db_manager.get_customer_details(username)
        
        # Initialize UI elements
        self.order_tree = None
        self.product_tree = None
        
        # Setup UI
        self.setup_ui()
        
        # Make the window modal
        self.window.transient(root)
        self.window.grab_set()
        
        # Start auto refresh
        self._refresh_timer = None
        self.start_auto_refresh()
    
    def setup_ui(self):
        # Create canvas and scrollbar for main window
        self.canvas = tk.Canvas(self.window, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=self.canvas.yview)
        
        # Create main frame inside canvas
        main_frame = ttk.Frame(self.canvas, padding="10")
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid canvas and scrollbar with proper weights
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Create window in canvas
        canvas_window = self.canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        # Configure main frame
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Update canvas window size when main frame changes
        def _on_frame_configure(event):
            # Update the scrollregion to encompass the inner frame
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Get canvas width
            canvas_width = self.canvas.winfo_width()
            
            # Update the canvas window width to match canvas width
            self.canvas.itemconfig(canvas_window, width=canvas_width)
        
        main_frame.bind("<Configure>", _on_frame_configure)
        
        # Update canvas size when window is resized
        def _on_canvas_configure(event):
            # Update the canvas window width to match canvas width
            self.canvas.itemconfig(canvas_window, width=event.width)
        
        self.canvas.bind("<Configure>", _on_canvas_configure)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create frames for each tab
        order_frame = ttk.Frame(notebook, padding="15")
        status_frame = ttk.Frame(notebook, padding="15")
        
        # Add tabs with icons
        notebook.add(order_frame, text=" 🛍️ Place Order ")
        notebook.add(status_frame, text=" 📋 Order Status ")
        
        # Setup tabs
        self.setup_order_tab(order_frame)
        self.setup_status_tab(status_frame)
        
        # Add Logout Button at the bottom
        logout_frame = ttk.Frame(main_frame, padding="5")
        logout_frame.grid(row=1, column=0, sticky="e", padx=10, pady=5)
        
        ttk.Button(logout_frame, text="🚪 Logout", style="Custom.TButton",
                  command=self.logout).pack(side='right')
        
        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            if not hasattr(self, 'window') or not self.window:
                return
            if not hasattr(self, '_is_closing'):
                return
            if not hasattr(self, 'canvas') or not self.canvas:
                return
            
            try:
                if self.window.winfo_exists() and not self._is_closing:
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass
        
        # Bind mousewheel to canvas
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Unbind mousewheel when window is destroyed
        def _on_destroy(event):
            if hasattr(self, 'canvas') and self.canvas:
                try:
                    self.canvas.unbind_all("<MouseWheel>")
                except:
                    pass
            
            # Clear references
            if hasattr(self, 'canvas'):
                self.canvas = None
        
        self.window.bind("<Destroy>", _on_destroy)
    
    def setup_order_tab(self, parent_frame):
        # Customer Info Section
        info_frame = ttk.LabelFrame(parent_frame, text="Customer Information", padding="10")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = f"""
        Customer: {self.customer_details['customer_name']}
        Type: {self.customer_details['customer_type']}
        Available Budget: {self.customer_details['budget']:.2f} TL
        Total Spent: {self.customer_details['total_spent']:.2f} TL
        """
        ttk.Label(info_frame, text=info_text).pack()
        
        # Product Selection Section
        product_frame = ttk.LabelFrame(parent_frame, text="Available Products", padding="10")
        product_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create Treeview for products
        columns = ("ID", "Name", "Stock", "Price (TL)")
        self.product_tree = ttk.Treeview(product_frame, columns=columns, show="headings", height=10)
        
        # Configure columns
        self.product_tree.heading("ID", text="ID")
        self.product_tree.heading("Name", text="Product Name")
        self.product_tree.heading("Stock", text="Available Stock")
        self.product_tree.heading("Price (TL)", text="Price (TL)")
        
        self.product_tree.column("ID", width=50, anchor="center")
        self.product_tree.column("Name", width=200)
        self.product_tree.column("Stock", width=100, anchor="center")
        self.product_tree.column("Price (TL)", width=100, anchor="e")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(product_frame, orient=tk.VERTICAL, command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        self.product_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Order Form Section
        order_form = ttk.LabelFrame(parent_frame, text="Place Order", padding="10")
        order_form.pack(fill=tk.X, padx=5, pady=5)
        
        # Quantity input
        ttk.Label(order_form, text="Quantity:").grid(row=0, column=0, padx=5, pady=5)
        quantity_var = tk.StringVar()
        quantity_entry = ttk.Entry(order_form, textvariable=quantity_var, width=10)
        quantity_entry.grid(row=0, column=1, padx=5, pady=5)
        
        def place_order():
            selected = self.product_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a product first!")
                return
            
            try:
                quantity = int(quantity_var.get())
                if quantity <= 0:
                    messagebox.showerror("Error", "Quantity must be positive!")
                    return
                
                product_id = self.product_tree.item(selected[0])['values'][0]
                
                if self.db_manager.place_order(self.customer_details['customer_id'], product_id, quantity):
                    messagebox.showinfo("Success", "Order placed successfully!")
                    quantity_var.set("")  # Clear quantity
                    self.refresh_all()  # Refresh all views
                else:
                    messagebox.showerror("Error", "Failed to place order! Please check your budget and product availability.")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid quantity!")
        
        ttk.Button(order_form, text="Place Order", command=place_order).grid(row=0, column=2, padx=20, pady=5)
        
        # Configure grid weights
        product_frame.grid_columnconfigure(0, weight=1)
        
        # Load initial data
        self.refresh_product_list()
    
    def setup_status_tab(self, parent_frame):
        # Create Treeview for orders
        columns = ("Order ID", "Product", "Quantity", "Status", "Order Time", "Wait Time")
        self.order_tree = ttk.Treeview(parent_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        column_widths = {
            "Order ID": 80,
            "Product": 200,
            "Quantity": 80,
            "Status": 100,
            "Order Time": 150,
            "Wait Time": 100
        }
        
        for col in columns:
            self.order_tree.heading(col, text=col)
            self.order_tree.column(col, width=column_widths[col], anchor="center")
        
        # Status colors
        self.order_tree.tag_configure('pending', background='#fff3cd')  # Sarı
        self.order_tree.tag_configure('processing', background='#cfe2ff')  # Mavi
        self.order_tree.tag_configure('completed', background='#d1e7dd')  # Yeşil
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=self.order_tree.yview)
        self.order_tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        self.order_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure grid weights
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(0, weight=1)
        
        # Load initial data
        self.refresh_order_list()
    
    def refresh_product_list(self):
        # Clear existing items
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
        
        # Add products to the treeview
        products = self.db_manager.get_all_products()
        for product in products:
            if product['stock'] > 0:  # Only show available products
                self.product_tree.insert("", tk.END, values=(
                    product["product_id"],
                    product["product_name"],
                    product["stock"],
                    f"{product['price']:.2f}"
                ))
    
    def refresh_order_list(self):
        # Clear existing items
        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        
        # Get customer's orders
        orders = self.db_manager.get_customer_orders(self.customer_details['customer_id'])
        
        for order in orders:
            # Determine status tag
            status = order['status'].lower()
            tag = status if status in ['pending', 'processing', 'completed'] else 'pending'
            
            self.order_tree.insert("", tk.END, values=(
                order['order_id'],
                order['product_name'],
                order['quantity'],
                order['status'].title(),
                order['order_time'],
                f"{order['wait_time']:.0f} sec"
            ), tags=(tag,))
    
    def refresh_all(self):
        """Refresh all dynamic content"""
        self.refresh_product_list()
        self.refresh_order_list()
        # Update customer details
        self.customer_details = self.db_manager.get_customer_details(self.username)
    
    def start_auto_refresh(self):
        """Start auto refresh cycle"""
        self.refresh_all()
        self._refresh_timer = self.window.after(5000, self.start_auto_refresh)
    
    def cleanup(self):
        """Cleanup resources"""
        if self._refresh_timer:
            self.window.after_cancel(self._refresh_timer)
        self.window.destroy() 
    
    def logout(self):
        """Safely handle logout request"""
        try:
            if self._is_closing:
                return
            
            if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
                self._cleanup()
        except Exception as e:
            print(f"Error during logout: {e}")
            self._force_close()
    
    def _cleanup(self):
        """Safely cleanup all resources"""
        try:
            if self._is_closing:
                return
                
            self._is_closing = True
            
            # Cancel any pending timers
            if hasattr(self, '_refresh_timer') and self._refresh_timer:
                self.window.after_cancel(self._refresh_timer)
                self._refresh_timer = None
            
            # Clear all bindings
            if hasattr(self, 'canvas') and self.canvas:
                try:
                    self.canvas.unbind_all("<MouseWheel>")
                    self.canvas.unbind("<Configure>")
                except:
                    pass
            
            if self.window:
                try:
                    self.window.unbind("<FocusIn>")
                    self.window.unbind("<FocusOut>")
                    self.window.unbind("<Destroy>")
                except:
                    pass
            
            # Clear references
            if hasattr(self, 'canvas'):
                try:
                    self.canvas.destroy()
                except:
                    pass
                self.canvas = None
            
            # Release window and destroy
            if self.window:
                try:
                    self.window.grab_release()
                    self.window.destroy()
                except:
                    pass
                self.window = None
            
            # Reset flags
            self._refresh_enabled = False
            self._is_focused = False
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            self._force_close()
        finally:
            self._is_closing = True
    
    def _force_close(self):
        """Force close in case of emergency"""
        try:
            if self.window:
                self.window.grab_release()
                self.window.destroy()
                self.window = None
        except:
            pass
        finally:
            self._is_closing = True 