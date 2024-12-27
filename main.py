import tkinter as tk
from tkinter import ttk, messagebox
from auth.auth_manager import AuthManager
from gui.admin_panel import AdminPanel
from gui.customer_panel import CustomerPanel

class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Login")
        self.root.geometry("300x200")
        
        self.auth_manager = AuthManager()
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Username
        ttk.Label(main_frame, text="Username:").grid(row=0, column=0, pady=5)
        self.username_entry = ttk.Entry(main_frame)
        self.username_entry.grid(row=0, column=1, pady=5)
        
        # Password
        ttk.Label(main_frame, text="Password:").grid(row=1, column=0, pady=5)
        self.password_entry = ttk.Entry(main_frame, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)
        
        # Login Button
        ttk.Button(main_frame, text="Login", command=self.login).grid(row=2, column=0, columnspan=2, pady=20)
    
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if username and password:
            success, role = self.auth_manager.login(username, password)
            
            if success:
                if role == "admin":
                    AdminPanel(self.root, self.auth_manager)
                else:
                    CustomerPanel(self.root, self.auth_manager, username)
                
                # Clear login fields
                self.username_entry.delete(0, tk.END)
                self.password_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Invalid username or password!")
        else:
            messagebox.showerror("Error", "Please fill all fields!")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = LoginWindow()
    app.run() 