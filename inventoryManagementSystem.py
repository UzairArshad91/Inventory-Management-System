import customtkinter as ctk
from tkinter import messagebox
import json
from pathlib import Path
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime


# Custom Exceptions
class InventoryError(Exception):
    """Base exception for inventory-related errors"""
    pass

class ProductNotFoundError(InventoryError):
    """Raised when a product is not found"""
    pass

class InvalidInputError(InventoryError):
    """Raised when input validation fails"""
    pass

class CategoryNotFoundError(InventoryError):
    """Raised when a category is not found"""
    pass

class DuplicateProductError(InventoryError):
    """Raised when trying to add a duplicate product ID"""
    pass


# Backend Classes

class Product:
    """Represents a product with validation"""
    def __init__(self, id, name, category, price, quantity):
        self._validate_id(id)
        self._validate_name(name)
        self._validate_category(category)
        self._validate_price(price)
        self._validate_quantity(quantity)
        
        self.id = id
        self.name = name.strip()
        self.category = category.strip()
        self._price = price
        self._quantity = quantity

    def _validate_id(self, id):
        """Validate product ID"""
        if not isinstance(id, int) or id <= 0:
            raise InvalidInputError("Product ID must be a positive integer.")

    def _validate_name(self, name):
        """Validate product name"""
        if not name or not isinstance(name, str) or not name.strip():
            raise InvalidInputError("Product name cannot be empty.")
        if len(name.strip()) > 100:
            raise InvalidInputError("Product name cannot exceed 100 characters.")

    def _validate_category(self, category):
        """Validate product category"""
        if not category or not isinstance(category, str) or not category.strip():
            raise InvalidInputError("Product category cannot be empty.")
        if len(category.strip()) > 50:
            raise InvalidInputError("Category name cannot exceed 50 characters.")

    def _validate_price(self, price):
        """Validate product price"""
        if not isinstance(price, (int, float)) or price < 0:
            raise InvalidInputError("Price must be a non-negative number.")

    def _validate_quantity(self, quantity):
        """Validate product quantity"""
        if not isinstance(quantity, int) or quantity < 0:
            raise InvalidInputError("Quantity must be a non-negative integer.")

    @property
    def price(self):
        return self._price
    
    @price.setter
    def price(self, value):
        self._validate_price(value)
        self._price = value

    @property
    def quantity(self):
        return self._quantity

    def increase_stock(self, amount):
        if not isinstance(amount, int) or amount < 0:
            raise InvalidInputError("Stock increase amount must be a non-negative integer.")
        self._quantity += amount

    def decrease_stock(self, amount):
        if not isinstance(amount, int) or amount < 0:
            raise InvalidInputError("Stock decrease amount must be a non-negative integer.")
        if amount > self._quantity:
            raise InvalidInputError(f"Cannot decrease stock by {amount}. Only {self._quantity} items available.")
        self._quantity -= amount

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'quantity': self.quantity
        }

    def __str__(self):
        return f"ID: {self.id} | {self.name} | {self.category} | ${self.price:.2f} | Qty: {self.quantity}"


class CategoryManager:
    """Manages product categories"""
    def __init__(self):
        self._categories = set()

    def add_category(self, category):
        if not category or not category.strip():
            raise ValueError("Category name cannot be empty.")
        self._categories.add(category.strip())

    def remove_category(self, category, inventory):
        if inventory.get_products_by_category(category):
            raise ValueError("Cannot remove category with products.")
        self._categories.discard(category)

    def list_categories(self):
        return sorted(self._categories)

    def category_exists(self, category):
        return category in self._categories


class Inventory:
    """Manages the product inventory"""
    def __init__(self):
        self._products = {}
        self.category_manager = CategoryManager()

    def add_product(self, product):
        """Add a new product to inventory"""
        if not isinstance(product, Product):
            raise InvalidInputError("Invalid product object.")
        
        if not self.category_manager.category_exists(product.category):
            raise CategoryNotFoundError(f"Category '{product.category}' does not exist. Please add the category first.")

        if product.id in self._products:
            # Update existing product
            self._products[product.id] = product
            return 1  # Updated
        else:
            # Add new product
            self._products[product.id] = product
            return 2  # Added

    def remove_product(self, product_id):
        """Remove a product by ID"""
        if not isinstance(product_id, int) or product_id <= 0:
            raise InvalidInputError("Product ID must be a positive integer.")
        
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID {product_id} not found.")
        
        del self._products[product_id]

    def get_product(self, product_id):
        """Get a product by ID"""
        if not isinstance(product_id, int) or product_id <= 0:
            raise InvalidInputError("Product ID must be a positive integer.")
        return self._products.get(product_id, None)

    def list_products(self):
        """Return sorted list of all products"""
        return sorted(self._products.values(), key=lambda p: p.id)

    def get_products_by_category(self, category):
        """Get products by category"""
        if not category or not isinstance(category, str):
            raise InvalidInputError("Invalid category name.")
        return [p for p in self._products.values() if p.category == category.strip()]

    def update_stock(self, product_id, amount):
        """Update stock for a product"""
        if not isinstance(product_id, int) or product_id <= 0:
            raise InvalidInputError("Product ID must be a positive integer.")
        if not isinstance(amount, int):
            raise InvalidInputError("Stock change amount must be an integer.")
        
        product = self.get_product(product_id)
        if product is None:
            raise ProductNotFoundError(f"Product with ID {product_id} not found.")
        
        if amount >= 0:
            product.increase_stock(amount)
        else:
            product.decrease_stock(-amount)

    def get_total_value(self):
        """Calculate total inventory value"""
        return sum(p.price * p.quantity for p in self._products.values())
            
        # if product.id in self._products:
        #     raise ValueError("Product ID already exists.")
        self._products[product.id] = product
        return 2

    def remove_product(self, product_id):
        if product_id not in self._products:
            raise ValueError("Product not found.")
        del self._products[product_id]

    def get_product(self, product_id):
        return self._products.get(product_id, None)

    def list_products(self):
        return sorted(self._products.values(), key=lambda p: p.id)

    def get_products_by_category(self, category):
        return [p for p in self._products.values() if p.category == category]

    def update_stock(self, product_id, amount):
        product = self.get_product(product_id)
        if product is None:
            raise ValueError("Product not found.")
        if amount >= 0:
            product.increase_stock(amount)
        else:
            product.decrease_stock(-amount)

    def get_total_value(self):
        return sum(p.price * p.quantity for p in self._products.values())


class StorageManager:
    """Handles saving and loading inventory data"""
    def __init__(self, filename="inventory.json"):
        self.filename = filename

    def save_inventory(self, inventory):
        data = {
            'categories': inventory.category_manager.list_categories(),
            'products': [p.to_dict() for p in inventory.list_products()]
        }
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_inventory(self):
        inv = Inventory()
        try:
            if Path(self.filename).exists():
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                
                for cat in data.get('categories', []):
                    inv.category_manager.add_category(cat)
                
                for p_data in data.get('products', []):
                    p = Product(
                        p_data['id'],
                        p_data['name'],
                        p_data['category'],
                        p_data['price'],
                        p_data['quantity']
                    )
                    inv.add_product(p)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return inv

    def export_to_csv(self, inventory, filename="inventory_export.csv"):
        if not inventory.list_products():
            raise ValueError("No products to export.")

        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            # Header
            writer.writerow(["ID", "Name", "Category", "Price", "Quantity"])

            # Data rows
            for product in inventory.list_products():
                writer.writerow([
                    product.id,
                    product.name,
                    product.category,
                    product.price,
                    product.quantity
                ])

    def export_to_pdf(self, inventory, filename="inventory_export.pdf"):
        if not inventory.list_products():
            raise ValueError("No products to export.")

        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4

        y = height - 50

        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, y, "Inventory Report")
        y -= 25

        # Date & time
        current_time = datetime.now().strftime("%d %b %Y, %H:%M")
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Generated on: {current_time}")
        y -= 25

        # Table header
        c.setFont("Helvetica-Bold", 10)
        headers = ["ID", "Name", "Category", "Price", "Quantity"]
        x_positions = [50, 100, 260, 380, 450]

        for header, x in zip(headers, x_positions):
            c.drawString(x, y, header)

        y -= 20
        c.setFont("Helvetica", 10)

        # Table rows
        for product in inventory.list_products():
            if y < 50:  # New page
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 50

            c.drawString(50, y, str(product.id))
            c.drawString(100, y, product.name[:20])
            c.drawString(260, y, product.category[:15])
            c.drawString(380, y, f"${product.price:.2f}")
            c.drawString(450, y, str(product.quantity))

            y -= 18

        c.save()




#GUI

class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate 70% of screen size
        window_width = int(screen_width * .8)
        window_height = int(screen_height * .8)

        # Calculate center position
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2


        self.title("Inventory Management System")
        self.update_idletasks()
        self.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Backend
        self.storage = StorageManager()
        self.inventory = self.storage.load_inventory()
        self.low_stock_threshold = 10

        # Create UI
        self.create_header()
        self.create_main_content()
        
        # Load initial data
        self.refresh_all()
        
        # Auto-save on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_header(self):
        """Create header with title and total value"""
        header = ctk.CTkFrame(self, height=80)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(header, text="Inventory Management System", 
                            font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=10)
        
        self.total_value_label = ctk.CTkLabel(header, text="", 
                                             font=ctk.CTkFont(size=16))
        self.total_value_label.pack()

    def create_main_content(self):
        """Create main content area with tabs"""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tabview.add("Categories")
        self.tabview.add("Products")
        self.tabview.add("Stock Management")
        
        self.create_category_tab()
        self.create_product_tab()
        self.create_stock_tab()

    def create_category_tab(self):
        """Create category management tab"""
        tab = self.tabview.tab("Categories")
        
        # Input frame
        input_frame = ctk.CTkFrame(tab)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        self.cat_entry = ctk.CTkEntry(input_frame, placeholder_text="Category Name", width=300)
        self.cat_entry.pack(side="left", padx=5, pady=10)
        
        ctk.CTkButton(input_frame, text="Add Category", command=self.add_category).pack(side="left", padx=5)
        
        # Delete frame
        delete_frame = ctk.CTkFrame(tab)
        delete_frame.pack(fill="x", padx=10, pady=10)
        
        self.cat_delete_entry = ctk.CTkEntry(delete_frame, placeholder_text="Category Name to Delete", width=300)
        self.cat_delete_entry.pack(side="left", padx=5, pady=10)
        
        delete_btn = ctk.CTkButton(delete_frame, text="Delete Category", command=self.delete_category, 
                                  fg_color="#dc2626", hover_color="#b91c1c")
        delete_btn.pack(side="left", padx=5)
        
        # List frame
        list_frame = ctk.CTkFrame(tab)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(list_frame, text="Existing Categories", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.cat_scroll = ctk.CTkScrollableFrame(list_frame)
        self.cat_scroll.pack(fill="both", expand=True, padx=5, pady=5)


    def create_product_tab(self):
        """Create product management tab"""
        tab = self.tabview.tab("Products")
        

        # Input frame
        input_frame = ctk.CTkFrame(tab)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        # Left column
        left_col = ctk.CTkFrame(input_frame)
        left_col.pack(side="left", padx=10, pady=10)
        
        self.id_entry = ctk.CTkEntry(left_col, placeholder_text="ID (number)", width=200)
        self.id_entry.pack(pady=5)
        
        self.name_entry = ctk.CTkEntry(left_col, placeholder_text="Product Name", width=200)
        self.name_entry.pack(pady=5)
        
        self.cat_dropdown = ctk.CTkOptionMenu(left_col, values=["Select Category"], width=200)
        self.cat_dropdown.pack(pady=5)
        
        # Right column
        right_col = ctk.CTkFrame(input_frame)
        right_col.pack(side="left", padx=10, pady=10)
        
        self.price_entry = ctk.CTkEntry(right_col, placeholder_text="Price", width=200)
        self.price_entry.pack(pady=5)
        
        self.qty_entry = ctk.CTkEntry(right_col, placeholder_text="Quantity", width=200)
        self.qty_entry.pack(pady=5)
        
        btn_frame = ctk.CTkFrame(right_col)
        btn_frame.pack(pady=5)
        
        ctk.CTkButton(btn_frame, text="Add/Update Product", command=self.add_product).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Clear", command=self.clear_product_form).pack(side="left", padx=5)

        #Export frame
        exp_col=ctk.CTkFrame(input_frame)
        exp_col.pack(side="left", padx=20, pady=20)

        exp_frame=ctk.CTkFrame(exp_col)
        exp_frame.pack(side="right")
        ctk.CTkButton(exp_frame, text="Export to CSV", command=self.export_inventory_csv).pack(side="top", padx=5)
        ctk.CTkButton(exp_frame, text="Export to PDF", command=self.export_inventory_pdf).pack(side="bottom", pady=5)


        # Delete frame
        delete_frame = ctk.CTkFrame(tab)
        delete_frame.pack(fill="x", padx=10, pady=10)
        
        self.product_delete_entry = ctk.CTkEntry(delete_frame, placeholder_text="Product ID to Delete", width=300)
        self.product_delete_entry.pack(side="left", padx=5, pady=10)
        
        delete_btn = ctk.CTkButton(delete_frame, text="Delete Product", command=self.delete_product,
                                  fg_color="#dc2626", hover_color="#b91c1c")
        delete_btn.pack(side="left", padx=5)
        
        # List frame
        list_frame = ctk.CTkFrame(tab)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(list_frame, text="Product List", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
    
        # Search frame
        search_frame = ctk.CTkFrame(list_frame)
        search_frame.pack(fill="x", padx=5, pady=(0,5))

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)

        # Search entry with reduced width
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Enter product name", width=int(self.winfo_screenwidth() *.3))
        self.search_entry.pack(side="left", padx=20)

        # Bind typing to live search
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_product_list())

        # Sort dropdown (Price)
        self.sort_var = ctk.StringVar(value="Sort by Price")
        self.sort_dropdown = ctk.CTkOptionMenu(
            search_frame, 
            values=["Low to High", "High to Low"],
            variable=self.sort_var,
            width=150,
            command=lambda _: self.update_product_list()  # refresh list when changed
        )
        self.sort_dropdown.pack(side="left", padx=10)

        # Clear Sort button
        ctk.CTkButton(
            search_frame,
            text="Sort by ID",
            command=self.clear_sort
        ).pack(side="left", padx=10)


        # Product tab
        self.prod_scroll = ctk.CTkScrollableFrame(list_frame)
        self.prod_scroll.pack(fill="both", expand=True, padx=5, pady=5)

    def create_stock_tab(self):
        """Create stock management tab"""
        tab = self.tabview.tab("Stock Management")
        
        # Input frame
        input_frame = ctk.CTkFrame(tab)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        self.stock_id_entry = ctk.CTkEntry(input_frame, placeholder_text="Product ID", width=200)
        self.stock_id_entry.pack(side="left", padx=5, pady=10)
        
        self.stock_amount_entry = ctk.CTkEntry(input_frame, placeholder_text="Amount (+/-)", width=200)
        self.stock_amount_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(input_frame, text="Update Stock", command=self.update_stock).pack(side="left", padx=5)
        
        # Info frame
        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Threshold frame
        threshold_frame = ctk.CTkFrame(tab)
        threshold_frame.pack(fill="x", padx=10, pady=(5, 0))

        ctk.CTkLabel(
            threshold_frame,
            text="Low Stock Threshold:"
        ).pack(side="left", padx=5)

        self.threshold_entry = ctk.CTkEntry(
            threshold_frame,
            width=100
        )
        self.threshold_entry.pack(side="left", padx=5)

        # Set default value
        self.threshold_entry.insert(0, str(self.low_stock_threshold))

        ctk.CTkButton(
            threshold_frame,
            text="Apply",
            command=self.apply_low_stock_threshold
        ).pack(side="left", padx=5)

        
        ctk.CTkLabel(info_frame, text="Low Stock Alert", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        
        self.low_stock_scroll = ctk.CTkScrollableFrame(info_frame)
        self.low_stock_scroll.pack(fill="both", expand=True, padx=5, pady=5)


    # ------------------ Category Operations ------------------
    
    def add_category(self):
        name = self.cat_entry.get().strip()
        if not name:
            self.show_error("Category name cannot be empty")
            return
        
        try:
            self.inventory.category_manager.add_category(name)
            self.cat_entry.delete(0, 'end')
            self.refresh_all()
            self.show_success(f"Category '{name}' added successfully")
        except ValueError as e:
            self.show_error(str(e))
    
    def delete_category(self):
        name = self.cat_delete_entry.get().strip()
        if not name:
            self.show_error("Please enter a category name to delete")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", 
                                   f"Are you sure you want to delete category '{name}'?\n\n"
                                   "This will only work if the category has no products."):
            return
        
        try:
            self.inventory.category_manager.remove_category(name, self.inventory)
            self.cat_delete_entry.delete(0, 'end')
            self.refresh_all()
            self.show_success(f"Category '{name}' deleted successfully")
        except ValueError as e:
            self.show_error(str(e))

    def update_category_list(self):
        for widget in self.cat_scroll.winfo_children():
            widget.destroy()

        categories = self.inventory.category_manager.list_categories()

        if not categories:
            label = ctk.CTkLabel(self.cat_scroll, text="No categories yet. Add one above!", text_color="gray")
            label.pack(pady=10)
        else:
            for cat in categories:
                count = len(self.inventory.get_products_by_category(cat))
                cat_frame = ctk.CTkFrame(self.cat_scroll)
                cat_frame.pack(fill="x", padx=5, pady=2)
                
                label = ctk.CTkLabel(cat_frame, text=f"• {cat} ({count} products)")
                label.pack(side="left", padx=10, pady=5)

        # Update category dropdown
        if categories:
            self.cat_dropdown.configure(values=categories)
            self.cat_dropdown.set(categories[0])



    # ------------------ Product Operations ------------------
    
    def add_product(self):
        try:
            product_id = int(self.id_entry.get())
            name = self.name_entry.get().strip()
            category = self.cat_dropdown.get()
            price = float(self.price_entry.get())
            quantity = int(self.qty_entry.get())
            
            if not name:
                raise ValueError("Product name cannot be empty")
            if category == "Select Category":
                raise ValueError("Please select a category")
            
            existing_product = self.inventory.get_product(product_id)
            if existing_product:
                # Prompt the user for update confirmation
                if messagebox.askyesno(
                    "Product ID Exists",
                    f"A product with ID {product_id} already exists:\n\n{existing_product}\n\n"
                    "Do you want to update this product with the new values?"
                ):
                    # Update existing product
                    existing_product.name = name
                    existing_product.category = category
                    existing_product.price = price
                    existing_product._quantity = quantity  # direct update for quantity
                    self.clear_product_form()
                    self.refresh_all()
                    self.show_success(f"Product '{name}' (ID: {product_id}) updated successfully")
                else:
                    # User chose not to update
                    return
            else:
                # Add new product
                product = Product(product_id, name, category, price, quantity)
                self.inventory.add_product(product)
                self.clear_product_form()
                self.refresh_all()
                self.show_success(f"Product '{name}' added successfully")
            
        except ValueError as e:
            self.show_error(str(e))

    
    def delete_product(self):
        try:
            product_id = int(self.product_delete_entry.get())
            
            # Get product details for confirmation
            product = self.inventory.get_product(product_id)
            if product is None:
                raise ValueError("Product not found")
            
            # Confirm deletion
            if not messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete:\n\n{product}\n\n"
                                       "This action cannot be undone."):
                return
            
            self.inventory.remove_product(product_id)
            self.product_delete_entry.delete(0, 'end')
            self.refresh_all()
            self.show_success(f"Product '{product.name}' (ID: {product_id}) deleted successfully")
            
        except ValueError as e:
            self.show_error(str(e))

    def clear_product_form(self):
        self.id_entry.configure(state="normal")

        self.id_entry.delete(0, 'end')
        self.name_entry.delete(0, 'end')
        self.price_entry.delete(0, 'end')
        self.qty_entry.delete(0, 'end')

    def load_product_into_form(self, product):
        self.clear_product_form()

        # Fill fields
        self.id_entry.insert(0, str(product.id))
        self.name_entry.insert(0, product.name)
        self.price_entry.insert(0, str(product.price))
        self.qty_entry.insert(0, str(product.quantity))
        self.cat_dropdown.set(product.category)

        #Disable ID editing while editing
        self.id_entry.configure(state="disabled")



    def update_product_list(self):
        for widget in self.prod_scroll.winfo_children():
            widget.destroy()
        
        products = self.inventory.list_products()

        # 1️⃣ Apply search
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            products = [p for p in products if search_text in p.name.lower()]

        # 3️⃣ Apply sorting
        sort_option = self.sort_var.get()
        if sort_option == "Low to High":
            products.sort(key=lambda p: p.price)
        elif sort_option == "High to Low":
            products.sort(key=lambda p: p.price, reverse=True)

        # 4️⃣ Display products in table
        if not products:
            label = ctk.CTkLabel(self.prod_scroll, text="No products found.", text_color="gray")
            label.pack(pady=10)
        else:
            # Header row
            header_frame = ctk.CTkFrame(self.prod_scroll, fg_color="#1f1f1f")
            header_frame.pack(fill="x", padx=5, pady=(0,2))

            headers = ["ID", "Name", "Category", "Price", "Quantity"]
            widths = [50, 200, 120, 80, 80]

            for text, w in zip(headers, widths):
                lbl = ctk.CTkLabel(header_frame, text=text, width=w, anchor="w", font=ctk.CTkFont(weight="bold"))
                lbl.pack(side="left", padx=2)

            # Product rows
            for i, p in enumerate(products):
                row_color = "#2b2b2b" if i % 2 == 0 else "#232323"

                row_frame = ctk.CTkFrame(
                    self.prod_scroll,
                    fg_color=row_color,
                    cursor="hand2"
                )
                row_frame.pack(fill="x", padx=5, pady=1)

                # Bind click to entire row
                row_frame.bind(
                    "<Button-1>",
                    lambda e, product=p: self.load_product_into_form(product)
                )


                values = [str(p.id), p.name, p.category, f"${p.price:.2f}", str(p.quantity)]
                
                for val, w in zip(values, widths):
                    lbl = ctk.CTkLabel(row_frame, text=val, width=w, anchor="w")
                    lbl.pack(side="left", padx=2)

                    lbl.bind(
                        "<Button-1>",
                        lambda e, product=p: self.load_product_into_form(product)
                    )




    # ------------------ Stock Operations ------------------
    
    def update_stock(self):
        try:
            product_id = int(self.stock_id_entry.get())
            amount = int(self.stock_amount_entry.get())
            
            self.inventory.update_stock(product_id, amount)
            
            self.stock_id_entry.delete(0, 'end')
            self.stock_amount_entry.delete(0, 'end')
            self.refresh_all()
            
            action = "increased" if amount > 0 else "decreased"
            self.show_success(f"Stock {action} by {abs(amount)}")
            
        except ValueError as e:
            self.show_error(str(e))

    def apply_low_stock_threshold(self):
        try:
            value = int(self.threshold_entry.get())

            if value < 0:
                raise ValueError

            self.low_stock_threshold = value
            self.update_low_stock_list()

            self.show_success(
                f"Low stock threshold set to {value}"
            )

        except ValueError:
            self.show_error(
                "Please enter a valid non-negative number"
            )


    def update_low_stock_list(self):
        for widget in self.low_stock_scroll.winfo_children():
            widget.destroy()
        
        low_stock = [ p for p in self.inventory.list_products() if p.quantity <= self.low_stock_threshold]

        info_label = ctk.CTkLabel(
            self.low_stock_scroll,
            text=f"Showing products with quantity ≤ {self.low_stock_threshold}",
            text_color="gray"
        )
        info_label.pack(pady=(0, 5))



        if not low_stock:
            label = ctk.CTkLabel(self.low_stock_scroll, text="✓ All products have sufficient stock!", text_color="#22c55e")
            label.pack(pady=10)
        else:
            for p in low_stock:
                stock_frame = ctk.CTkFrame(self.low_stock_scroll)
                stock_frame.pack(fill="x", padx=5, pady=3)
                
                label = ctk.CTkLabel(stock_frame, text=f"{p}", anchor="w",  text_color="#FF7E7E")
                label.pack(side="left", padx=10, pady=5, fill="x", expand=True)

    # ------------------ Utility Functions ------------------
    
    def refresh_all(self):
        """Refresh all UI elements"""
        self.update_category_list()
        self.update_product_list()
        self.update_low_stock_list()
        
        total = self.inventory.get_total_value()
        self.total_value_label.configure(text=f"Total Inventory Value: ${total:,.2f}")
        
        # Auto-save
        try:
            self.storage.save_inventory(self.inventory)
        except Exception as e:
            print(f"Auto-save error: {e}")

    def show_error(self, message):
        messagebox.showerror("Error", message)

    def show_success(self, message):
        messagebox.showinfo("Success", message)

    def export_inventory_csv(self):
        try:
            self.storage.export_to_csv(self.inventory)
            self.show_success("Inventory exported successfully as inventory_export.csv")
        except ValueError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Export failed: {e}")
    
    def export_inventory_pdf(self):
        try:
            self.storage.export_to_pdf(self.inventory)
            self.show_success("Inventory exported successfully as inventory_export.pdf")
        except ValueError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Export failed: {e}")

    def clear_sort(self):
        self.sort_var.set("Sort by Price")  # reset the dropdown to default value
        self.update_product_list()          # refresh the product list


    def on_close(self):
        """Save and close"""
        try:
            self.storage.save_inventory(self.inventory)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save inventory: {e}")
        self.destroy()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()