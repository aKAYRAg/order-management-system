import tkinter as tk
from tkinter import ttk, messagebox
from auth.auth_manager import AuthManager
from database.db_manager import DatabaseManager
import threading
from queue import PriorityQueue
from threading import Lock, Semaphore
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class AdminPanel:
    def __init__(self, root: tk.Tk, auth_manager: AuthManager):
        # Store root reference
        self.root = root
        
        # Thread management
        self.order_threads = {}
        self.order_queue = PriorityQueue()
        self.processing_lock = Lock()
        self.max_concurrent_orders = 8
        self.order_semaphore = Semaphore(self.max_concurrent_orders)
        self.is_processing = False
        
        # Create main window
        self.window = tk.Toplevel(root)
        self.window.title("Admin Panel")
        self.window.geometry("1400x900")
        self.window.minsize(1200, 800)
        
        # Critical state flags
        self._is_closing = False
        self._is_focused = True
        self._refresh_enabled = True
        
        # Timer management
        self._refresh_timer = None
        self._cleanup_timer = None
        self._last_refresh_time = 0
        self._refresh_interval = 5000  # 5 seconds
        
        # Reference keeping
        self._root_bindings = []
        self._window_bindings = []
        
        # Make the window modal
        self.window.transient(root)
        self.window.grab_set()
        
        # Configure grid weights
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        
        # Initialize managers
        self.auth_manager = auth_manager
        self.db_manager = DatabaseManager()
        
        # Initialize UI elements as None
        self.order_tree = None
        self.log_tree = None
        self.customer_tree = None
        self.product_tree = None
        
        # Kritik stok seviyesi
        self.critical_stock_level = 10
        
        # Setup UI before binding events
        self.setup_ui()
        
        # Bind window events - after UI setup
        self._setup_window_bindings()
        
        # Keep strong reference to root window
        self._root = root
        
        # Start refresh cycle with delay and keep reference
        self._initial_timer = self.window.after(1000, self._safe_start_refresh_cycle)
    
    def _setup_window_bindings(self):
        """Setup all window event bindings with strong references"""
        self._window_bindings.extend([
            self.window.protocol("WM_DELETE_WINDOW", self._safe_handle_close),
            self.window.bind("<FocusIn>", self._safe_handle_focus_in),
            self.window.bind("<FocusOut>", self._safe_handle_focus_out),
            self.window.bind("<Destroy>", self._safe_handle_destroy),
            self.window.bind("<Map>", self._safe_handle_map),
            self.window.bind("<Unmap>", self._safe_handle_unmap)
        ])
    
    def _safe_start_refresh_cycle(self):
        """Safely start the refresh cycle with error handling"""
        try:
            if not self._is_closing and self.window.winfo_exists():
                self._refresh_all()
                self._schedule_next_refresh()
        except Exception as e:
            print(f"Error starting refresh cycle: {e}")
            self._handle_refresh_error()
    
    def _schedule_next_refresh(self):
        """Schedule the next refresh cycle with safety checks"""
        try:
            # Cancel existing timer if any
            if self._refresh_timer:
                self.window.after_cancel(self._refresh_timer)
                self._refresh_timer = None
            
            # Only schedule if conditions are met
            if (not self._is_closing and self.window.winfo_exists() and 
                self._refresh_enabled and self._is_focused):
                current_time = self.window.tk.call('clock', 'milliseconds')
                if current_time - self._last_refresh_time >= self._refresh_interval:
                    self._refresh_timer = self.window.after(
                        self._refresh_interval, 
                        self._safe_start_refresh_cycle
                    )
                    self._last_refresh_time = current_time
        except Exception as e:
            print(f"Error scheduling refresh: {e}")
            self._handle_refresh_error()
    
    def _handle_refresh_error(self):
        """Handle refresh cycle errors"""
        try:
            if self._refresh_timer:
                self.window.after_cancel(self._refresh_timer)
                self._refresh_timer = None
            # Try to restart refresh cycle after a delay
            if not self._is_closing and self.window.winfo_exists():
                self._refresh_timer = self.window.after(
                    self._refresh_interval * 2,  # Double the interval on error
                    self._safe_start_refresh_cycle
                )
        except:
            pass
    
    def _safe_handle_map(self, event=None):
        """Handle window map (show) event"""
        if not self._is_closing and self._refresh_enabled:
            self._is_focused = True
            self._safe_start_refresh_cycle()
    
    def _safe_handle_unmap(self, event=None):
        """Handle window unmap (hide) event"""
        self._is_focused = False
        if self._refresh_timer:
            self.window.after_cancel(self._refresh_timer)
            self._refresh_timer = None
    
    def _cleanup(self):
        """Safely cleanup all resources"""
        try:
            if self._is_closing:
                return
            
            self._is_closing = True
            
            # Cancel any pending timers
            if self._refresh_timer:
                self.window.after_cancel(self._refresh_timer)
                self._refresh_timer = None
            
            if self._cleanup_timer:
                self.window.after_cancel(self._cleanup_timer)
                self._cleanup_timer = None
            
            if self._initial_timer:
                self.window.after_cancel(self._initial_timer)
                self._initial_timer = None
            
            # Stop order processing
            self.is_processing = False
            
            # Wait for threads to complete
            for thread in list(self.order_threads.values()):
                if thread.is_alive():
                    thread.join(timeout=1.0)
            
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
            self.order_threads.clear()
            self.order_queue = None
            self.processing_lock = None
            self.order_semaphore = None
            
            if hasattr(self, 'stock_canvas'):
                try:
                    self.stock_canvas.get_tk_widget().destroy()
                except:
                    pass
                self.stock_canvas = None
                self.stock_figure = None
                self.stock_ax = None
            
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
            
            # Clear other references
            self.order_tree = None
            self.log_tree = None
            self.customer_tree = None
            self.product_tree = None
            
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
    
    def _refresh_all(self):
        """Refresh all data"""
        if not self._is_closing and self.window.winfo_exists():
            try:
                # Only refresh if trees are initialized
                if self.order_tree:
                    self.refresh_order_list()
                if self.log_tree:
                    self.refresh_logs()
                if self.customer_tree:
                    self.refresh_customer_list()
                if self.product_tree:
                    self.refresh_product_list()
                
                self.window.update_idletasks()
            except Exception as e:
                print(f"Error refreshing data: {e}")
                if self._refresh_timer:
                    self.window.after_cancel(self._refresh_timer)
                    self._refresh_timer = None
    
    def _safe_handle_focus_in(self, event=None):
        """Safely handle focus in event"""
        try:
            if self._is_closing or not self.window.winfo_exists():
                return
            
            self._is_focused = True
            if self._refresh_enabled:
                self._safe_start_refresh_cycle()
        except Exception as e:
            print(f"Error handling focus in: {e}")
    
    def _safe_handle_focus_out(self, event=None):
        """Safely handle focus out event"""
        try:
            if self._is_closing or not self.window.winfo_exists():
                return
            
            self._is_focused = False
            if self._refresh_timer:
                self.window.after_cancel(self._refresh_timer)
                self._refresh_timer = None
        except Exception as e:
            print(f"Error handling focus out: {e}")
    
    def _safe_handle_destroy(self, event=None):
        """Safely handle destroy event"""
        try:
            if not self._is_closing:
                self._cleanup()
        except Exception as e:
            print(f"Error handling destroy: {e}")
            self._force_close()
    
    def _safe_handle_close(self):
        """Safely handle close request"""
        try:
            if self._is_closing:
                return
            
            if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
                self._cleanup()
        except Exception as e:
            print(f"Error handling close: {e}")
            self._force_close()
    
    def toggle_refresh(self):
        """Safely toggle auto-refresh"""
        try:
            self._refresh_enabled = not self._refresh_enabled
            if self._refresh_enabled and self._is_focused and not self._is_closing:
                self._safe_start_refresh_cycle()
            elif self._refresh_timer:
                self.window.after_cancel(self._refresh_timer)
                self._refresh_timer = None
        except Exception as e:
            print(f"Error toggling refresh: {e}")
    
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
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            if not self._is_closing:
                self._cleanup()
        except:
            pass
    
    def setup_ui(self):
        # Create canvas and scrollbar for main window
        self.canvas = tk.Canvas(self.window, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=self.canvas.yview)
        
        # Create main frame inside canvas
        main_frame = ttk.Frame(self.canvas, padding="10")
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Grid canvas and scrollbar
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Create window in canvas
        self.canvas.create_window((0, 0), window=main_frame, anchor="nw", width=self.canvas.winfo_width())
        
        # Configure main frame
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create frames for each tab with custom style
        customer_frame = ttk.Frame(notebook, padding="15", style="Custom.TLabelframe")
        product_frame = ttk.Frame(notebook, padding="15", style="Custom.TLabelframe")
        order_frame = ttk.Frame(notebook, padding="15", style="Custom.TLabelframe")
        log_frame = ttk.Frame(notebook, padding="15", style="Custom.TLabelframe")
        
        # Add tabs with icons (emoji)
        notebook.add(customer_frame, text=" 👥 Customers ")
        notebook.add(product_frame, text=" 📦 Products ")
        notebook.add(order_frame, text=" 🛍️ Orders ")
        notebook.add(log_frame, text=" 📋 Logs ")
        
        # Setup tabs
        self.setup_customer_tab(customer_frame)
        self.setup_product_tab(product_frame)
        self.setup_order_tab(order_frame)
        self.setup_log_tab(log_frame)
        
        # Add Logout Button at the bottom with custom style
        logout_frame = ttk.Frame(main_frame, padding="5")
        logout_frame.grid(row=1, column=0, sticky="e", padx=10, pady=5)
        
        ttk.Button(logout_frame, text="🚪 Logout", style="Custom.TButton",
                  command=self.logout).pack(side='right')
        
        # Update scroll region when widgets are configured
        def _configure_canvas(event):
            # Update the scrollregion to encompass the inner frame
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Update the canvas window width when the main frame changes
                self.canvas.itemconfig(self.canvas.find_withtag("all")[0], width=event.width)
        
        main_frame.bind("<Configure>", _configure_canvas)
        
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
        
        # Bind canvas resize
        def _on_canvas_configure(event):
            if hasattr(self, 'canvas') and self.canvas:
                try:
                    self.canvas.itemconfig(self.canvas.find_withtag("all")[0], width=event.width)
                except:
                    pass
        
        self.canvas.bind("<Configure>", _on_canvas_configure)
        
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
    
    def setup_customer_tab(self, parent_frame):
        # Title with custom style
        title_label = ttk.Label(parent_frame, text="Customer Management", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Customer List Section with improved style
        list_frame = ttk.LabelFrame(parent_frame, text="Customer List", style="Custom.TLabelframe")
        list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        # Configure weights for list frame
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        # Create Treeview with custom style
        columns = ("ID", "Name", "Budget", "Type", "Total Spent", "Username")
        self.customer_tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                                        style="Tree.Row", height=15)
        
        # Set column headings with custom style
        for col in columns:
            self.customer_tree.heading(col, text=col)
            if col in ["ID", "Type"]:
                self.customer_tree.column(col, width=80, anchor="center")
            elif col in ["Budget", "Total Spent"]:
                self.customer_tree.column(col, width=120, anchor="e")
            else:
                self.customer_tree.column(col, width=150, anchor="w")
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.customer_tree.yview)
        x_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.customer_tree.xview)
        self.customer_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid the treeview and scrollbars
        self.customer_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Button Frame
        button_frame = ttk.Frame(parent_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        button_frame.grid_columnconfigure(0, weight=1)
        
        # Refresh Button with icon
        refresh_btn = ttk.Button(button_frame, text="🔄 Refresh List", 
                               command=self.refresh_customer_list, style="Custom.TButton")
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Add alternating row colors
        self.customer_tree.tag_configure('oddrow', background='#f0f0f0')
        self.customer_tree.tag_configure('evenrow', background='#ffffff')
        
        # Load initial customer data
        self.refresh_customer_list()
    
    def setup_product_tab(self, parent_frame):
        # Title with custom style
        title_label = ttk.Label(parent_frame, text="Product Management", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Stil ayarları
        style = ttk.Style()
        # Treeview stilleri
        style.configure("Treeview", 
                      font=('Arial', 10), 
                      rowheight=30,
                      background="#ffffff",
                      fieldbackground="#ffffff")
        
        style.configure("Treeview.Heading",
                      font=('Arial', 10, 'bold'),
                      background="#f0f0f0",
                      relief="flat")
        
        # Seçili satır için özel renk
        style.map('Treeview',
                 background=[('selected', '#0078D7')],
                 foreground=[('selected', 'white')])
        
        # Create main container frame
        container = ttk.Frame(parent_frame)
        container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        container.grid_columnconfigure(0, weight=2)  # Product list gets more space
        container.grid_columnconfigure(1, weight=1)  # Management panel gets less space
        
        # Product List Section (Left side)
        list_frame = ttk.LabelFrame(container, text="Product List", style="Custom.TLabelframe")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        # Create Treeview with custom style
        columns = ("ID", "Name", "Stock", "Price (TL)")
        self.product_tree = ttk.Treeview(list_frame, columns=columns, show="headings",
                                       style="Treeview", height=20, selectmode="browse")
        
        # Set column headings with custom style
        for col in columns:
            self.product_tree.heading(col, text=col)
            if col == "ID":
                self.product_tree.column(col, width=60, anchor="center")
            elif col == "Stock":
                self.product_tree.column(col, width=80, anchor="center")
            elif col == "Price (TL)":
                self.product_tree.column(col, width=100, anchor="e")
            else:
                self.product_tree.column(col, width=200, anchor="w")
        
        # Bind selection event
        def on_select(event):
            print("Selection made")
            selected = self.product_tree.selection()
            if selected:
                item = self.product_tree.item(selected[0])
                print(f"Selected item: {item['values']}")

        self.product_tree.bind('<<TreeviewSelect>>', on_select)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.product_tree.yview)
        x_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.product_tree.xview)
        self.product_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid the treeview and scrollbars
        self.product_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Button frame for product list
        list_button_frame = ttk.Frame(list_frame)
        list_button_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        def delete_selected_product():
            selected = self.product_tree.selection()
            print(f"Delete button clicked, selection: {selected}")
            if not selected:
                messagebox.showwarning("Warning", "Please select a product to delete")
                return
            
            try:
                product_id = self.product_tree.item(selected[0])['values'][0]
                product_name = self.product_tree.item(selected[0])['values'][1]
                
                if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {product_name}?"):
                    if self.db_manager.delete_product(product_id):
                        messagebox.showinfo("Success", f"{product_name} has been deleted successfully!")
                        self.refresh_product_list()
                    else:
                        messagebox.showerror("Error", "Failed to delete product!")
            except Exception as e:
                print(f"Error in delete_selected_product: {e}")
                messagebox.showerror("Error", "An error occurred while deleting the product")
        
        # Add Delete button
        delete_btn = ttk.Button(list_button_frame, text="Delete Product", command=delete_selected_product)
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(list_button_frame, text="Refresh List", command=self.refresh_product_list)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Management Panel (Right side)
        management_frame = ttk.Frame(container)
        management_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Add Product Section
        add_frame = ttk.LabelFrame(management_frame, text="Add New Product", style="Custom.TLabelframe")
        add_frame.pack(fill="x", padx=5, pady=5)
        
        # Grid for add product inputs
        add_grid = ttk.Frame(add_frame)
        add_grid.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(add_grid, text="Product Name:", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w", pady=2)
        name_entry = ttk.Entry(add_grid, width=30)
        name_entry.grid(row=0, column=1, sticky="ew", pady=2)
        
        ttk.Label(add_grid, text="Stock:", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=2)
        stock_entry = ttk.Entry(add_grid, width=30)
        stock_entry.grid(row=1, column=1, sticky="ew", pady=2)
        
        ttk.Label(add_grid, text="Price (TL):", style="Subtitle.TLabel").grid(row=2, column=0, sticky="w", pady=2)
        price_entry = ttk.Entry(add_grid, width=30)
        price_entry.grid(row=2, column=1, sticky="ew", pady=2)
        
        def add_product():
            try:
                name = name_entry.get().strip()
                stock = int(stock_entry.get())
                price = float(price_entry.get())
                
                if name and stock >= 0 and price >= 0:
                    if self.db_manager.add_product(name, stock, price):
                        messagebox.showinfo("Success", "Product added successfully!")
                        name_entry.delete(0, tk.END)
                        stock_entry.delete(0, tk.END)
                        price_entry.delete(0, tk.END)
                        self.refresh_product_list()
                    else:
                        messagebox.showerror("Error", "Failed to add product!")
                else:
                    messagebox.showerror("Error", "Please enter valid values!")
            except ValueError:
                messagebox.showerror("Error", "Stock and Price must be numbers!")
        
        ttk.Button(add_frame, text="Add Product", command=add_product).pack(pady=10)
        
        # Update Stock Section
        stock_frame = ttk.LabelFrame(management_frame, text="Update Stock", style="Custom.TLabelframe")
        stock_frame.pack(fill="x", padx=5, pady=5)
        
        # Grid for stock update inputs
        stock_grid = ttk.Frame(stock_frame)
        stock_grid.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(stock_grid, text="Product ID:", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w", pady=2)
        product_id_entry = ttk.Entry(stock_grid, width=30)
        product_id_entry.grid(row=0, column=1, sticky="ew", pady=2)
        
        ttk.Label(stock_grid, text="New Stock:", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=2)
        new_stock_entry = ttk.Entry(stock_grid, width=30)
        new_stock_entry.grid(row=1, column=1, sticky="ew", pady=2)
        
        def update_stock():
            try:
                product_id = int(product_id_entry.get())
                new_stock = int(new_stock_entry.get())
                
                if new_stock >= 0:
                    if self.db_manager.update_stock(product_id, new_stock):
                        messagebox.showinfo("Success", "Stock updated successfully!")
                        product_id_entry.delete(0, tk.END)
                        new_stock_entry.delete(0, tk.END)
                        self.refresh_product_list()
                    else:
                        messagebox.showerror("Error", "Product not found!")
                else:
                    messagebox.showerror("Error", "Stock cannot be negative!")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers!")
        
        ttk.Button(stock_frame, text="Update Stock", command=update_stock).pack(pady=10)
        
        # Update Price Section
        price_frame = ttk.LabelFrame(management_frame, text="Update Price", style="Custom.TLabelframe")
        price_frame.pack(fill="x", padx=5, pady=5)
        
        # Grid for price update inputs
        price_grid = ttk.Frame(price_frame)
        price_grid.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(price_grid, text="Product ID:", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w", pady=2)
        price_product_id_entry = ttk.Entry(price_grid, width=30)
        price_product_id_entry.grid(row=0, column=1, sticky="ew", pady=2)
        
        ttk.Label(price_grid, text="New Price (TL):", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=2)
        new_price_entry = ttk.Entry(price_grid, width=30)
        new_price_entry.grid(row=1, column=1, sticky="ew", pady=2)
        
        def update_price():
            try:
                product_id = int(price_product_id_entry.get())
                new_price = float(new_price_entry.get())
                
                if new_price >= 0:
                    if self.db_manager.update_price(product_id, new_price):
                        messagebox.showinfo("Success", "Price updated successfully!")
                        price_product_id_entry.delete(0, tk.END)
                        new_price_entry.delete(0, tk.END)
                        self.refresh_product_list()
                    else:
                        messagebox.showerror("Error", "Product not found!")
                else:
                    messagebox.showerror("Error", "Price cannot be negative!")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid price!")
        
        ttk.Button(price_frame, text="Update Price", command=update_price).pack(pady=10)
        
        # Bind selection event to auto-fill product IDs
        def on_product_select(event):
            selected = self.product_tree.selection()
            if selected:
                product_id = self.product_tree.item(selected[0])['values'][0]
                # Update both stock and price entry fields
                product_id_entry.delete(0, tk.END)
                product_id_entry.insert(0, str(product_id))
                price_product_id_entry.delete(0, tk.END)
                price_product_id_entry.insert(0, str(product_id))
        
        self.product_tree.bind('<<TreeviewSelect>>', on_product_select)
        
        # Stock Visualization Section
        viz_frame = ttk.LabelFrame(management_frame, text="Stock Visualization", style="Custom.TLabelframe")
        viz_frame.pack(fill="x", padx=5, pady=5)
        
        # Create figure for bar chart
        self.stock_figure = Figure(figsize=(6, 4))
        self.stock_ax = self.stock_figure.add_subplot(111)
        
        # Create canvas
        self.stock_canvas = FigureCanvasTkAgg(self.stock_figure, master=viz_frame)
        self.stock_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Update graph when refreshing product list
        def update_stock_graph():
            self.stock_ax.clear()
            products = self.db_manager.get_all_products()
            
            names = [p["product_name"] for p in products]
            stocks = [p["stock"] for p in products]
            
            # Stok durumuna göre renk belirleme
            colors = ['red' if s <= self.critical_stock_level else 'blue' for s in stocks]
            
            # Bar chart
            bars = self.stock_ax.bar(names, stocks, color=colors)
            
            # Görsel düzenlemeler
            self.stock_ax.set_title('Product Stock Levels')
            self.stock_ax.set_xlabel('Products')
            self.stock_ax.set_ylabel('Stock')
            
            # X ekseni etiketlerini döndür
            plt.setp(self.stock_ax.get_xticklabels(), rotation=45, ha='right')
            
            # Kritik seviye çizgisi
            self.stock_ax.axhline(y=self.critical_stock_level, color='r', linestyle='--', alpha=0.5)
            
            # Bar üzerine değerleri yaz
            for bar in bars:
                height = bar.get_height()
                self.stock_ax.text(bar.get_x() + bar.get_width()/2., height,
                                 f'{int(height)}',
                                 ha='center', va='bottom')
            
            # Layout ayarla
            self.stock_figure.tight_layout()
            
            # Canvas'ı güncelle
            self.stock_canvas.draw()
        
        # Orijinal refresh_product_list fonksiyonunu güncelle
        original_refresh = self.refresh_product_list
        def new_refresh():
            original_refresh()
            update_stock_graph()
        self.refresh_product_list = new_refresh
        
        # İlk grafiği çiz
        update_stock_graph()
        
        # Add alternating row colors
        self.product_tree.tag_configure('oddrow', background='#f0f0f0')
        self.product_tree.tag_configure('evenrow', background='white')
        
        # Load initial product data
        self.refresh_product_list()
    
    def setup_order_tab(self, parent_frame):
        # Title
        title_label = ttk.Label(parent_frame, text="Order Management", style="Title.TLabel")
        title_label.grid(row=0, column=0, pady=10, sticky="w")
        
        # Create frame for buttons
        button_frame = ttk.Frame(parent_frame)
        button_frame.grid(row=1, column=0, pady=5, sticky="w")
        
        def process_selected_order():
            selected = self.order_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an order to process")
                return
                
            order_id = self.order_tree.item(selected[0])['values'][0]
            thread = threading.Thread(
                target=self.process_order_thread,
                args=(order_id, 0)  # Tek sipariş için öncelik önemsiz
            )
            self.order_threads[order_id] = thread
            thread.start()

        def process_all_orders():
            if self.is_processing:
                messagebox.showinfo("Info", "Order processing is already running")
                return
                
            self.is_processing = True
            processing_thread = threading.Thread(target=self.start_order_processing)
            processing_thread.start()

        # Buttons
        ttk.Button(button_frame, text="Process Selected", command=process_selected_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Process All Orders", command=process_all_orders).pack(side=tk.LEFT, padx=5)
        
        # Create Treeview for orders
        columns = ("Order ID", "Customer", "Type", "Product", "Quantity", "Priority", "Order Time", "Wait Time")
        self.order_tree = ttk.Treeview(parent_frame, columns=columns, show="headings", height=15)
        
        # Configure columns and headings
        column_widths = {
            "Order ID": 80,
            "Customer": 120,
            "Type": 100,
            "Product": 200,
            "Quantity": 80,
            "Priority": 120,
            "Order Time": 150,
            "Wait Time": 100
        }
        
        column_anchors = {
            "Order ID": "center",
            "Customer": "w",
            "Type": "center",
            "Product": "w",
            "Quantity": "center",
            "Priority": "center",
            "Order Time": "center",
            "Wait Time": "center"
        }
        
        # Stil ayarları
        style = ttk.Style()
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        style.configure("Treeview", font=('Arial', 10), rowheight=25)
        
        # Sütunları yapılandır
        for col in columns:
            self.order_tree.heading(col, text=col)
            self.order_tree.column(col, width=column_widths[col], anchor=column_anchors[col], minwidth=50)
        
        # Alternatif satır renkleri
        self.order_tree.tag_configure('oddrow', background='#f5f5f5')
        self.order_tree.tag_configure('evenrow', background='white')
        
        # Grid yerleşimi
        self.order_tree.grid(row=2, column=0, pady=10, padx=10, sticky="nsew")
        
        # Parent frame'in grid ağırlıklarını ayarla
        parent_frame.grid_rowconfigure(2, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=self.order_tree.yview)
        scrollbar.grid(row=2, column=1, sticky="ns", pady=10)
        self.order_tree.configure(yscrollcommand=scrollbar.set)
    
    def process_order_thread(self, order_id, priority_score):
        """Her bir siparişi ayrı bir thread'de işle"""
        try:
            with self.order_semaphore:  # En fazla 8 eş zamanlı işlem
                print(f"Processing order {order_id} with priority {-priority_score:.2f}")
                
                # Sadece process_order işlemi için mutex kullan
                with self.processing_lock:
                    if not self.is_processing:
                        return
                    success = self.db_manager.process_order(order_id)
                
                if success:
                    print(f"Successfully processed order {order_id}")
                    self.window.after(0, lambda: self.refresh_order_list())
                    self.window.after(0, lambda: self.refresh_logs())
                else:
                    print(f"Failed to process order {order_id}")
        except Exception as e:
            print(f"Error in process_order_thread: {e}")
        finally:
            if order_id in self.order_threads:
                del self.order_threads[order_id]

    def calculate_priority_score(self, order_data):
        """Sipariş öncelik puanını hesapla"""
        customer_type, wait_time, quantity = order_data
        
        # Müşteri tipi katsayısı (Premium: 2x, Normal: 1x)
        type_multiplier = 2.0 if customer_type == "Premium" else 1.0
        
        # Bekleme süresi katsayısı (saat başına artan)
        wait_multiplier = 1.0 + (wait_time / 3600.0)
        
        # Miktar katsayısı
        quantity_multiplier = 1.0 + (quantity / 100.0)
        
        # Toplam öncelik puanı (negatif çünkü PriorityQueue küçük değerlere öncelik verir)
        priority_score = -(type_multiplier * wait_multiplier * quantity_multiplier)
        print(f"Priority Score: {-priority_score:.2f} (Type: {type_multiplier}x, Wait: {wait_multiplier:.2f}x, Quantity: {quantity_multiplier:.2f}x)")
        return priority_score

    def start_order_processing(self):
        """Tüm bekleyen siparişleri öncelik sırasına göre işle"""
        try:
            print("\nStarting order processing...")
            # Bekleyen siparişleri al
            orders = self.db_manager.get_pending_orders()
            print(f"Found {len(orders)} pending orders")
            
            # Her sipariş için öncelik hesapla ve kuyruğa ekle
            for order in orders:
                order_id = order[0]
                customer_type = order[2]
                wait_time = float(order[7])
                quantity = int(order[5])
                
                priority_score = self.calculate_priority_score((customer_type, wait_time, quantity))
                self.order_queue.put((priority_score, order_id))
            
            print("\nProcessing orders by priority...")
            # Kuyruktan siparişleri al ve thread'leri başlat
            while not self.order_queue.empty():
                if not self.is_processing:
                    break
                    
                priority_score, order_id = self.order_queue.get()
                
                # Yeni thread oluştur
                thread = threading.Thread(
                    target=self.process_order_thread,
                    args=(order_id, priority_score)
                )
                self.order_threads[order_id] = thread
                thread.start()
                
            # Tüm thread'lerin tamamlanmasını bekle
            for thread in list(self.order_threads.values()):
                thread.join()
                
        except Exception as e:
            print(f"Error in start_order_processing: {e}")
            messagebox.showerror("Error", f"Failed to process orders: {e}")
        finally:
            self.is_processing = False
            print("Order processing completed")
    
    def refresh_customer_list(self):
        # Clear existing items
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)
        
        # Add customers to the treeview
        customers = self.db_manager.get_all_customers()
        for customer in customers:
            self.customer_tree.insert("", tk.END, values=(
                customer["customer_id"],
                customer["customer_name"],
                f"{customer['budget']:.2f} TL",
                customer["customer_type"],
                f"{customer['total_spent']:.2f} TL",
                customer["username"]
            ))
    
    def refresh_product_list(self):
        # Get current selection
        selected_items = self.product_tree.selection()
        selected_ids = []
        for item in selected_items:
            try:
                selected_ids.append(self.product_tree.item(item)['values'][0])
            except:
                pass

        # Clear existing items
        self.product_tree.delete(*self.product_tree.get_children())
        
        # Add products to the treeview
        products = self.db_manager.get_all_products()
        for i, product in enumerate(products):
            # Alternatif satır renkleri için tag
            row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            
            item_id = self.product_tree.insert("", tk.END, values=(
                product["product_id"],
                product["product_name"],
                product["stock"],
                f"{product['price']:.2f} TL"
            ), tags=(row_tag,))
            
            # Restore selection if this was a selected item
            if product["product_id"] in selected_ids:
                self.product_tree.selection_add(item_id)
    
    def show_product_menu(self, event):
        """Show context menu on right click"""
        # Get the item under cursor
        item = self.product_tree.identify_row(event.y)
        if item:
            # Select the item
            self.product_tree.selection_set(item)
            # Show the menu
            self.product_menu.post(event.x_root, event.y_root)
    
    def delete_selected_product(self):
        """Delete the selected product"""
        # Get selected item
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a product to delete!")
            return
        
        # Get product details
        item = self.product_tree.item(selection[0])
        product_id = int(item['values'][0])  # First column is ID
        product_name = item['values'][1]  # Second column is Name
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {product_name}?"):
            if self.db_manager.delete_product(product_id):
                messagebox.showinfo("Success", f"{product_name} deleted successfully!")
                self.refresh_product_list()
            else:
                messagebox.showerror("Error", "Failed to delete product!") 
    
    def setup_log_tab(self, parent_frame):
        """Setup the log viewing tab"""
        # Title
        title_label = ttk.Label(parent_frame, text="System Logs", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Log List Section
        log_frame = ttk.LabelFrame(parent_frame, text="Recent Logs", padding="10")
        log_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Configure grid weights
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Create Treeview
        columns = ("ID", "Customer", "Type", "Customer Type", "Product", "Quantity", "Time", "Message")
        self.log_tree = ttk.Treeview(log_frame, columns=columns, show="headings", height=20)
        
        # Set column headings and widths
        self.log_tree.heading("ID", text="Log ID")
        self.log_tree.column("ID", width=50, stretch=False)
        
        self.log_tree.heading("Customer", text="Customer")
        self.log_tree.column("Customer", width=100, stretch=False)
        
        self.log_tree.heading("Type", text="Log Type")
        self.log_tree.column("Type", width=100, stretch=False)
        
        self.log_tree.heading("Customer Type", text="Cust. Type")
        self.log_tree.column("Customer Type", width=80, stretch=False)
        
        self.log_tree.heading("Product", text="Product")
        self.log_tree.column("Product", width=100, stretch=False)
        
        self.log_tree.heading("Quantity", text="Qty")
        self.log_tree.column("Quantity", width=50, stretch=False)
        
        self.log_tree.heading("Time", text="Timestamp")
        self.log_tree.column("Time", width=150, stretch=False)
        
        self.log_tree.heading("Message", text="Message")
        self.log_tree.column("Message", width=400, stretch=True)  # Message column will expand
        
        # Enable word wrapping for the Message column
        style = ttk.Style()
        style.configure("Treeview", rowheight=60)  # Increase row height for wrapped text
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        x_scrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_tree.xview)
        self.log_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid the treeview and scrollbars
        self.log_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        y_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        x_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Control buttons
        button_frame = ttk.Frame(parent_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Refresh Logs", 
                  command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
        
        # Auto-refresh setup
        self._refresh_enabled = True
        self._refresh_timer = None
        
        def toggle_auto_refresh():
            self._refresh_enabled = not self._refresh_enabled
            auto_refresh_btn.config(text="Auto-Refresh: " + ("ON" if self._refresh_enabled else "OFF"))
            if self._refresh_enabled:
                self._safe_start_refresh_cycle()
            elif self._refresh_timer:
                self.window.after_cancel(self._refresh_timer)
                self._refresh_timer = None
        
        auto_refresh_btn = ttk.Button(button_frame, text="Auto-Refresh: ON", 
                                    command=toggle_auto_refresh)
        auto_refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Load initial log data and start auto-refresh
        self.refresh_logs()
        self._safe_start_refresh_cycle()
    
    def refresh_order_list(self):
        """Refresh the order list with safety checks"""
        try:
            if self._is_closing or not self.window.winfo_exists():
                return
            
            # Clear existing items
            self.order_tree.delete(*self.order_tree.get_children())
            
            # Add orders to the treeview
            orders = self.db_manager.get_pending_orders()
            for i, order in enumerate(orders):
                # order tuple: (order_id, customer_id, customer_type, product_id, product_name, quantity, order_time, wait_time)
                customer_type = order[2]
                wait_time = float(order[7])
                quantity = int(order[5])
                
                # Öncelik puanını hesapla
                priority_score = self.calculate_priority_score((customer_type, wait_time, quantity))
                
                # Alternatif satır renkleri için tag
                row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                
                self.order_tree.insert("", tk.END, values=(
                    order[0],  # order_id
                    f"Customer {order[1]}",  # customer_id
                    customer_type,  # customer_type
                    order[4],  # product_name
                    quantity,  # quantity
                    f"Priority: {-priority_score:.2f}",  # Negatifi alınmış priority score
                    order[6],  # order_time
                    f"{wait_time:.0f} sec"  # wait_time
                ), tags=(row_tag,))
            
            # Update the window
            if not self._is_closing and self.window.winfo_exists():
                self.window.update_idletasks()
                
        except Exception as e:
            print(f"Error refreshing order list: {e}")
            self._handle_refresh_error()
    
    def refresh_logs(self):
        """Refresh the log list with safety checks"""
        try:
            if self._is_closing or not self.window.winfo_exists():
                return
            
            # Get current selection
            selected_items = self.log_tree.selection()
            selected_ids = [self.log_tree.item(item)['values'][0] for item in selected_items]
            
            # Clear existing items
            self.log_tree.delete(*self.log_tree.get_children())
            
            # Add logs to the treeview
            logs = self.db_manager.get_recent_logs()
            for log in logs:
                if self._is_closing or not self.window.winfo_exists():
                    return
                
                # Set row color based on log type
                tags = ()
                if log["log_type"] == "Error":
                    tags = ("error",)
                elif log["log_type"] == "Warning":
                    tags = ("warning",)
                
                item_id = self.log_tree.insert("", tk.END, values=(
                    log["log_id"],
                    log["customer_name"],
                    log["log_type"],
                    log["customer_type"],
                    log["product"] or "-",
                    log["quantity"] or "-",
                    log["timestamp"],
                    log["result_message"]
                ), tags=tags)
                
                # Restore selection if this was a selected item
                if log["log_id"] in selected_ids:
                    self.log_tree.selection_add(item_id)
            
            # Configure tag colors
            self.log_tree.tag_configure("error", foreground="red")
            self.log_tree.tag_configure("warning", foreground="orange")
            
            # Update the window to prevent display issues
            if not self._is_closing and self.window.winfo_exists():
                self.window.update_idletasks()
            
        except Exception as e:
            print(f"Error refreshing logs: {e}")
            self._handle_refresh_error()
    
    def _force_close(self):
        """Force close the window"""
        self._is_closing = True
        
        # Cancel all timers first
        for timer in [self._refresh_timer, self._cleanup_timer, self._initial_timer]:
            if timer:
                try:
                    self.window.after_cancel(timer)
                except:
                    pass
        
        self._refresh_timer = None
        self._cleanup_timer = None
        self._initial_timer = None
        
        # Force destroy window
        try:
            if self.window and self.window.winfo_exists():
                self.window.destroy()
        except:
            pass
        
        # Clear all references
        self._root = None
        self.window = None
        self.auth_manager = None
        self.db_manager = None 