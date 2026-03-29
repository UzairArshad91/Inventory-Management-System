import customtkinter as ctk
from tkinter import messagebox
import json
from pathlib import Path
import csv
import logging
import shutil
from typing import Optional, List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# ==================== CONFIGURATION & CONSTANTS ====================

# Application Settings
WINDOW_SIZE_FACTOR = 0.8
HEADER_HEIGHT = 80
LOW_STOCK_THRESHOLD_DEFAULT = 10
MAX_PRODUCT_NAME_LENGTH = 100
MAX_CATEGORY_NAME_LENGTH = 50
PRODUCT_ID_MIN = 1

# File Settings
DEFAULT_INVENTORY_FILE = "inventory.json"
DEFAULT_BACKUP_FILE = "inventory_backup.json"
DEFAULT_CSV_FILE = "inventory_export.csv"
DEFAULT_PDF_FILE = "inventory_export.pdf"
BACKUP_COUNT = 3  # Keep last 3 backups

# UI Colors & Theme
PRIMARY_COLOR = "blue"
APPEARANCE_MODE = "dark"
ERROR_COLOR = "#dc2626"
ERROR_HOVER_COLOR = "#b91c1c"
SUCCESS_COLOR = "#22c55e"
ALERT_COLOR = "#FF7E7E"
ROW_ALTERNATE_COLOR_1 = "#2b2b2b"
ROW_ALTERNATE_COLOR_2 = "#232323"
HEADER_BG_COLOR = "#1f1f1f"

# UI Dimensions
SEARCH_ENTRY_WIDTH_FACTOR = 0.3
STANDARD_ENTRY_WIDTH = 200
DELETE_BTN_WIDTH = 300

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ==================== CUSTOM EXCEPTIONS ====================

class InventoryError(Exception):
    """Base exception for inventory-related errors."""
    pass


class ProductNotFoundError(InventoryError):
    """Raised when a product is not found in the inventory."""
    pass


class InvalidInputError(InventoryError):
    """Raised when input validation fails."""
    pass


class CategoryNotFoundError(InventoryError):
    """Raised when a category is not found in the category manager."""
    pass


class DuplicateProductError(InventoryError):
    """Raised when trying to add a product with a duplicate ID."""
    pass


# Backend Classes

class Product:
    """Represents a product in the inventory with full validation.
    
    Attributes:
        id: Unique product identifier (positive integer)
        name: Product name (non-empty string, max 100 chars)
        category: Product category (non-empty string, max 50 chars)
        price: Product price (non-negative float)
        quantity: Stock quantity (non-negative integer)
    """
    
    def __init__(self, id: int, name: str, category: str, price: float, quantity: int) -> None:
        """Initialize a product with validation.
        
        Args:
            id: Unique product identifier
            name: Product name
            category: Product category
            price: Product price
            quantity: Initial stock quantity
            
        Raises:
            InvalidInputError: If any validation fails
        """
        self._validate_id(id)
        self._validate_name(name)
        self._validate_category(category)
        self._validate_price(price)
        self._validate_quantity(quantity)
        
        self.id: int = id
        self.name: str = name.strip()
        self.category: str = category.strip()
        self._price: float = price
        self._quantity: int = quantity

    def _validate_id(self, id: int) -> None:
        """Validate that product ID is a positive integer."""
        if not isinstance(id, int) or isinstance(id, bool) or id < PRODUCT_ID_MIN:
            raise InvalidInputError("Product ID must be a positive integer.")

    def _validate_name(self, name: str) -> None:
        """Validate that product name is non-empty and within length limits."""
        if not name or not isinstance(name, str) or not name.strip():
            raise InvalidInputError("Product name cannot be empty.")
        if len(name.strip()) > MAX_PRODUCT_NAME_LENGTH:
            raise InvalidInputError(f"Product name cannot exceed {MAX_PRODUCT_NAME_LENGTH} characters.")

    def _validate_category(self, category: str) -> None:
        """Validate that category is non-empty and within length limits."""
        if not category or not isinstance(category, str) or not category.strip():
            raise InvalidInputError("Product category cannot be empty.")
        if len(category.strip()) > MAX_CATEGORY_NAME_LENGTH:
            raise InvalidInputError(f"Category name cannot exceed {MAX_CATEGORY_NAME_LENGTH} characters.")

    def _validate_price(self, price: float) -> None:
        """Validate that price is a non-negative number."""
        if not isinstance(price, (int, float)) or isinstance(price, bool) or price < 0:
            raise InvalidInputError("Price must be a non-negative number.")

    def _validate_quantity(self, quantity: int) -> None:
        """Validate that quantity is a non-negative integer."""
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            raise InvalidInputError("Quantity must be a non-negative integer.")

    @property
    def price(self) -> float:
        """Get the product price."""
        return self._price
    
    @price.setter
    def price(self, value: float) -> None:
        """Set the product price with validation."""
        self._validate_price(value)
        self._price = value

    @property
    def quantity(self) -> int:
        """Get the current stock quantity."""
        return self._quantity
    
    @quantity.setter
    def quantity(self, value: int) -> None:
        """Set the stock quantity with validation."""
        self._validate_quantity(value)
        self._quantity = value

    def increase_stock(self, amount: int) -> None:
        """Increase stock by the specified amount.
        
        Args:
            amount: Quantity to add (non-negative integer)
            
        Raises:
            InvalidInputError: If amount is invalid
        """
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise InvalidInputError("Stock increase amount must be a non-negative integer.")
        self._quantity += amount
        logger.info(f"Stock increased for {self.name} (ID: {self.id}) by {amount}. New quantity: {self._quantity}")

    def decrease_stock(self, amount: int) -> None:
        """Decrease stock by the specified amount.
        
        Args:
            amount: Quantity to remove (non-negative integer)
            
        Raises:
            InvalidInputError: If amount is invalid or exceeds available stock
        """
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise InvalidInputError("Stock decrease amount must be a non-negative integer.")
        if amount > self._quantity:
            raise InvalidInputError(f"Cannot decrease stock by {amount}. Only {self._quantity} items available.")
        self._quantity -= amount
        logger.info(f"Stock decreased for {self.name} (ID: {self.id}) by {amount}. New quantity: {self._quantity}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary for serialization.
        
        Returns:
            Dictionary with product data
        """
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'quantity': self.quantity
        }

    def __str__(self) -> str:
        """Return formatted string representation of the product."""
        return f"ID: {self.id} | {self.name} | {self.category} | ${self.price:.2f} | Qty: {self.quantity}"


class CategoryManager:
    """Manages product categories with validation and conflict checking."""
    
    def __init__(self) -> None:
        """Initialize the category manager with an empty set of categories."""
        self._categories: set = set()

    def add_category(self, category: str) -> None:
        """Add a new category.
        
        Args:
            category: Category name to add
            
        Raises:
            ValueError: If category is empty or exceeds length limits
        """
        if not category or not category.strip():
            raise ValueError("Category name cannot be empty.")
        if len(category.strip()) > MAX_CATEGORY_NAME_LENGTH:
            raise ValueError(f"Category name cannot exceed {MAX_CATEGORY_NAME_LENGTH} characters.")
        clean_category = category.strip()
        if clean_category in self._categories:
            raise ValueError(f"Category '{clean_category}' already exists.")
        self._categories.add(clean_category)
        self._categories.add(clean_category)
        logger.info(f"Category '{clean_category}' added.")

    def remove_category(self, category: str, inventory: 'Inventory') -> None:
        """Remove a category if it has no associated products.
        
        Args:
            category: Category name to remove
            inventory: Inventory instance to check for products
            
        Raises:
            ValueError: If category has associated products
        """
        if inventory.get_products_by_category(category):
            raise ValueError("Cannot remove category with products.")
        
        if category not in self._categories:
            raise CategoryNotFoundError(f"Category '{category}' does not exist.")

        self._categories.remove(category)

        logger.info(f"Category '{category}' removed.")

    def list_categories(self) -> List[str]:
        """Get sorted list of all categories.
        
        Returns:
            Sorted list of category names
        """
        return sorted(self._categories)

    def category_exists(self, category: str) -> bool:
        """Check if a category exists.
        
        Args:
            category: Category name to check
            
        Returns:
            True if category exists, False otherwise
        """
        return category in self._categories


class Inventory:
    """Manages the product inventory with categories and stock tracking.
    
    Handles adding, removing, updating products and their stock levels,
    as well as category management and inventory valuation.

    The inventory maintains a "dirty" flag that is set whenever the data
    changes. This enables debounced autosave behavior from the GUI layer.
    """
    
    def __init__(self) -> None:
        """Initialize an empty inventory with a category manager."""
        self._products: Dict[int, Product] = {}
        self.category_manager: CategoryManager = CategoryManager()
        self._dirty: bool = False

    # dirty flag helpers
    def _mark_dirty(self) -> None:
        """Mark inventory as modified."""
        self._dirty = True
        logger.debug("Inventory marked dirty")

    def clear_dirty(self) -> None:
        """Clear the dirty state after a successful save."""
        self._dirty = False
        logger.debug("Inventory dirty flag cleared")

    def is_dirty(self) -> bool:
        """Return whether the inventory has unsaved changes."""
        return self._dirty

    def add_product(self, product: Product) -> int:
        """Add a new product or update an existing one.
        
        Args:
            product: Product instance to add
            
        Returns:
            1 if product was updated, 2 if product was added
            
        Raises:
            InvalidInputError: If product is invalid
            CategoryNotFoundError: If category doesn't exist
        """
        if not isinstance(product, Product):
            raise InvalidInputError("Invalid product object.")
        
        if not self.category_manager.category_exists(product.category):
            raise CategoryNotFoundError(f"Category '{product.category}' does not exist. Please add the category first.")

        if product.id in self._products:
            self._products[product.id] = product
            logger.info(f"Product updated: {product}")
            self._mark_dirty()
            return 1  # Updated
        else:
            self._products[product.id] = product
            logger.info(f"Product added: {product}")
            self._mark_dirty()
            return 2  # Added

    def remove_product(self, product_id: int) -> None:
        """Remove a product by ID.
        
        Args:
            product_id: ID of product to remove
            
        Raises:
            InvalidInputError: If product ID is invalid
            ProductNotFoundError: If product doesn't exist
        """
        if not isinstance(product_id, int) or product_id <= 0:
            raise InvalidInputError("Product ID must be a positive integer.")
        
        if product_id not in self._products:
            raise ProductNotFoundError(f"Product with ID {product_id} not found.")
        
        product = self._products[product_id]
        del self._products[product_id]
        logger.info(f"Product removed: {product}")
        self._mark_dirty()

    def get_product(self, product_id: int) -> Optional[Product]:
        """Get a product by ID.
        
        Args:
            product_id: ID of product to retrieve
            
        Returns:
            Product instance or None if not found
            
        Raises:
            InvalidInputError: If product ID is invalid
        """
        if not isinstance(product_id, int) or product_id <= 0:
            raise InvalidInputError("Product ID must be a positive integer.")
        return self._products.get(product_id, None)

    def list_products(self) -> List[Product]:
        """Get all products sorted by ID.
        
        Returns:
            Sorted list of all products
        """
        return sorted(self._products.values(), key=lambda p: p.id)

    def get_products_by_category(self, category: str) -> List[Product]:
        """Get all products in a specific category.
        
        Args:
            category: Category name to filter by
            
        Returns:
            List of products in the category
            
        Raises:
            InvalidInputError: If category is invalid
        """
        if not category or not isinstance(category, str):
            raise InvalidInputError("Invalid category name.")
        return [p for p in self._products.values() if p.category == category.strip()]

    def update_stock(self, product_id: int, amount: int) -> None:
        """Update stock quantity for a product.
        
        Args:
            product_id: ID of product to update
            amount: Quantity change (positive or negative)
            
        Raises:
            InvalidInputError: If inputs are invalid
            ProductNotFoundError: If product doesn't exist
        """
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
        self._mark_dirty()

    def get_total_value(self) -> float:
        """Calculate the total monetary value of all inventory.
        
        Returns:
            Sum of (price * quantity) for all products
        """
        return sum(p.price * p.quantity for p in self._products.values())
    
    def get_low_stock_products(self, threshold: int) -> List[Product]:
        """Get products with stock below threshold.
        
        Args:
            threshold: Stock level threshold
            
        Returns:
            List of products with quantity <= threshold
        """
        return [p for p in self._products.values() if p.quantity <= threshold]


class StorageManager:
    """Handles loading, saving, and exporting inventory data.
    
    Supports JSON serialization, CSV export, PDF reports, and automatic backups.
    """
    
    def __init__(self, filename: str = DEFAULT_INVENTORY_FILE) -> None:
        """Initialize storage manager with a filename.
        
        Args:
            filename: Path to the inventory JSON file
        """
        self.filename: str = filename
        self.backup_dir: Path = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

    def save_inventory(self, inventory: Inventory) -> None:
        """Save inventory to JSON file with automatic backup.
        
        Args:
            inventory: Inventory instance to save
        """
        try:
            # Create automatic backup
            self._create_backup()
            
            data = {
                'categories': inventory.category_manager.list_categories(),
                'products': [p.to_dict() for p in inventory.list_products()]
            }
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Inventory saved to {self.filename}")
        except Exception as e:
            logger.error(f"Failed to save inventory: {e}")
            raise

    def _create_backup(self) -> None:
        """Create an automatic backup of the current inventory file.
        
        Maintains a limited number of backups to save disk space.
        """
        if not Path(self.filename).exists():
            return
        
        try:
            backup_file = self.backup_dir / f"{Path(self.filename).stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            shutil.copy2(self.filename, backup_file)
            logger.info(f"Backup created: {backup_file}")
            
            # Clean up old backups
            backups = sorted(self.backup_dir.glob(f"{Path(self.filename).stem}_backup_*.json"), reverse=True)
            for old_backup in backups[BACKUP_COUNT:]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Backup creation failed: {e}")
    
    def load_inventory(self) -> Inventory:
        """Load inventory from JSON file.
        
        Returns:
            Inventory instance with loaded data
        """
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
                inv.clear_dirty()
                logger.info(f"Inventory loaded from {self.filename}")
            else:
                logger.info("No existing inventory file found. Starting with empty inventory.")
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, InventoryError, ValueError) as e:
            logger.error(f"Error loading inventory: {e}")
        return inv

    def export_to_csv(self, inventory: Inventory, filename: str = DEFAULT_CSV_FILE) -> None:
        """Export inventory to CSV file.
        
        Args:
            inventory: Inventory instance to export
            filename: Output CSV file path
            
        Raises:
            ValueError: If inventory is empty
        """
        if not inventory.list_products():
            raise ValueError("No products to export.")

        try:
            with open(filename, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["ID", "Name", "Category", "Price", "Quantity"])
                for product in inventory.list_products():
                    writer.writerow([
                        product.id,
                        product.name,
                        product.category,
                        product.price,
                        product.quantity
                    ])
            logger.info(f"Inventory exported to CSV: {filename}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            raise

    def export_to_pdf(self, inventory: Inventory, filename: str = DEFAULT_PDF_FILE) -> None:
        """Export inventory to PDF report.
        
        Args:
            inventory: Inventory instance to export
            filename: Output PDF file path
            
        Raises:
            ValueError: If inventory is empty
        """
        if not inventory.list_products():
            raise ValueError("No products to export.")

        try:
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
                    y = height - 50
                    c.setFont("Helvetica-Bold", 10)
                    for header, x in zip(headers, x_positions):
                        c.drawString(x, y, header)
                    y -= 20
                    c.setFont("Helvetica", 10)

                c.drawString(50, y, str(product.id))
                c.drawString(100, y, product.name[:20])
                c.drawString(260, y, product.category[:15])
                c.drawString(380, y, f"${product.price:.2f}")
                c.drawString(450, y, str(product.quantity))

                y -= 18

            c.save()
            logger.info(f"Inventory exported to PDF: {filename}")
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise




# ==================== GUI SECTION ====================

class InventoryApp(ctk.CTk):
    """Main GUI application for inventory management system.
    
    Provides a tabbed interface for managing categories, products, and stock levels
    with real-time UI updates and automatic data persistence.
    """
    
    def __init__(self) -> None:
        """Initialize the GUI application and load data."""
        super().__init__()

        # Get screen dimensions
        screen_width: int = self.winfo_screenwidth()
        screen_height: int = self.winfo_screenheight()

        # Calculate window size
        window_width: int = int(screen_width * WINDOW_SIZE_FACTOR)
        window_height: int = int(screen_height * WINDOW_SIZE_FACTOR)

        # Calculate center position
        x_position: int = (screen_width - window_width) // 2
        y_position: int = (screen_height - window_height) // 2

        self.title("Inventory Management System")
        self.update_idletasks()
        self.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        ctk.set_appearance_mode(APPEARANCE_MODE)
        ctk.set_default_color_theme(PRIMARY_COLOR)

        # Backend initialization
        self.storage: StorageManager = StorageManager()
        self.inventory: Inventory = self.storage.load_inventory()
        self.low_stock_threshold: int = LOW_STOCK_THRESHOLD_DEFAULT
        
        # UI components (initialized in create_* methods)
        self.tabview: Optional[ctk.CTkTabview] = None
        self.total_value_label: Optional[ctk.CTkLabel] = None
        self.cat_scroll: Optional[ctk.CTkScrollableFrame] = None
        self.prod_scroll: Optional[ctk.CTkScrollableFrame] = None
        self.low_stock_scroll: Optional[ctk.CTkScrollableFrame] = None
        self.search_entry: Optional[ctk.CTkEntry] = None
        self.sort_var: Optional[ctk.StringVar] = None
        self.category_filter_var: Optional[ctk.StringVar] = None

        # Create UI
        self.create_header()
        self.create_main_content()
        
        # Load initial data
        self.refresh_all()
        self.set_default_next_product_id()
        logger.info("Application initialized successfully")
        
        # Start periodic autosave (every 5 seconds)
        self.schedule_autosave()
        
        # Auto-save on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_header(self) -> None:
        """Create header frame with title and total inventory value display."""
        header = ctk.CTkFrame(self, height=HEADER_HEIGHT)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(header, text="Inventory Management System", 
                            font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=10)
        
        self.total_value_label = ctk.CTkLabel(header, text="", 
                                             font=ctk.CTkFont(size=16))
        self.total_value_label.pack()

    def create_main_content(self) -> None:
        """Create tabbed main content area with three tabs.
        
        Creates tabs for:
        - Categories: Manage product categories
        - Products: Add/update/delete products
        - Stock Management: Update stock and view low stock alerts
        """
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tabview.add("Categories")
        self.tabview.add("Products")
        self.tabview.add("Stock Management")
        
        self.create_category_tab()
        self.create_product_tab()
        self.create_stock_tab()

    def create_category_tab(self) -> None:
        """Create category management tab with add/delete and list display."""
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


    def create_product_tab(self) -> None:
        """Create product management tab with CRUD operations and search.
        
        Features:
        - Add/update products
        - Delete products  
        - Search by name
        - Sort by price
        - Export to CSV/PDF
        """
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
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Enter product name", width=int(self.winfo_screenwidth() * SEARCH_ENTRY_WIDTH_FACTOR))
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

        # Category filter dropdown
        self.category_filter_var = ctk.StringVar(value="All Categories")
        self.category_filter_dropdown = ctk.CTkOptionMenu(
            search_frame,
            values=["All Categories"],
            variable=self.category_filter_var,
            width=170,
            command=lambda _: self.update_product_list()
        )
        self.category_filter_dropdown.pack(side="left", padx=10)

        # Clear Sort button
        ctk.CTkButton(
            search_frame,
            text="Sort by ID",
            command=self.clear_sort
        ).pack(side="left", padx=10)


        # Product tab
        self.prod_scroll = ctk.CTkScrollableFrame(list_frame)
        self.prod_scroll.pack(fill="both", expand=True, padx=5, pady=5)

    def create_stock_tab(self) -> None:
        """Create stock management tab with update and low stock alerts.
        
        Features:
        - Update stock quantities
        - Set low stock threshold
        - View low stock alerts
        """
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


    # ==================== CATEGORY OPERATIONS ====================
    
    def add_category(self) -> None:
        """Add a new category from user input."""
        name = self.cat_entry.get().strip()
        if not name:
            self.show_error("Category name cannot be empty")
            return
        
        try:
            self.inventory.category_manager.add_category(name)
            self.inventory._mark_dirty()
            self.cat_entry.delete(0, 'end')
            self.refresh_all()
            self.show_success(f"Category '{name}' added successfully")
        except (ValueError, InventoryError) as e:
            self.show_error(str(e))
    
    def delete_category(self) -> None:
        """Delete a category after confirmation.
        
        Prevents deletion of categories with associated products.
        """
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
            self.inventory._mark_dirty()
            self.cat_delete_entry.delete(0, 'end')
            self.refresh_all()
            self.show_success(f"Category '{name}' deleted successfully")
        except (ValueError, InventoryError) as e:
            self.show_error(str(e))

    def update_category_list(self) -> None:
        """Refresh the category list display and update category dropdown."""
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

        # Update category dropdown, preserving current selection if still valid
        if categories:
            current = self.cat_dropdown.get()
            self.cat_dropdown.configure(values=categories)
            if current in categories:
                self.cat_dropdown.set(current)
            else:
                self.cat_dropdown.set(categories[0])
        else:
            self.cat_dropdown.configure(values=["Select Category"])
            self.cat_dropdown.set("Select Category")

        # Update product-category filter dropdown
        filter_values = ["All Categories"] + categories
        current_filter = self.category_filter_var.get() if self.category_filter_var else "All Categories"
        if hasattr(self, "category_filter_dropdown"):
            self.category_filter_dropdown.configure(values=filter_values)
        if self.category_filter_var:
            if current_filter in filter_values:
                self.category_filter_var.set(current_filter)
            else:
                self.category_filter_var.set("All Categories")



    # ==================== PRODUCT OPERATIONS ====================

    def get_next_product_id(self) -> int:
        """Return the next suggested product ID (last ID + 1)."""
        products = self.inventory.list_products()
        if not products:
            return PRODUCT_ID_MIN
        return products[-1].id + 1

    def set_default_next_product_id(self) -> None:
        """Auto-fill the ID field with the next suggested product ID."""
        self.id_entry.configure(state="normal")
        self.id_entry.delete(0, 'end')
        self.id_entry.insert(0, str(self.get_next_product_id()))
    
    def add_product(self) -> None:
        """Add or update a product from form input.
        
        Validates input, prompts for update confirmation if product exists.
        """
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
                    existing_product._validate_name(name)
                    existing_product._validate_category(category)
                    existing_product.name = name.strip()
                    existing_product.category = category.strip()
                    existing_product.price = price
                    existing_product.quantity = quantity  # Use property setter
                    self.inventory._mark_dirty()
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
            
        except (ValueError, InventoryError) as e:
            self.show_error(str(e))

    
    def delete_product(self) -> None:
        """Delete a product after confirmation."""
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
            
        except (ValueError, InventoryError) as e:
            self.show_error(str(e))

    def clear_product_form(self) -> None:
        """Clear form fields and restore next suggested ID."""
        self.set_default_next_product_id()
        self.name_entry.delete(0, 'end')
        self.price_entry.delete(0, 'end')
        self.qty_entry.delete(0, 'end')

    def load_product_into_form(self, product: Product) -> None:
        """Load a product into the form for editing.
        
        Args:
            product: Product instance to load
        """
        self.clear_product_form()

        # Fill fields
        self.id_entry.delete(0, 'end')
        self.id_entry.insert(0, str(product.id))
        self.name_entry.insert(0, product.name)
        self.price_entry.insert(0, str(product.price))
        self.qty_entry.insert(0, str(product.quantity))
        self.cat_dropdown.set(product.category)

        #Disable ID editing while editing
        self.id_entry.configure(state="disabled")



    def update_product_list(self) -> None:
        """Update product list with search and sorting applied.
        
        Applies live search filter and price sorting dynamically.
        """
        for widget in self.prod_scroll.winfo_children():
            widget.destroy()
        
        products = self.inventory.list_products()

        # 1️⃣ Apply search
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            products = [p for p in products if search_text in p.name.lower()]

        # 2️⃣ Apply category filter
        selected_category = self.category_filter_var.get() if self.category_filter_var else "All Categories"
        if selected_category and selected_category != "All Categories":
            products = [p for p in products if p.category == selected_category]

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
                row_color = ROW_ALTERNATE_COLOR_1 if i % 2 == 0 else ROW_ALTERNATE_COLOR_2

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




    # ==================== STOCK OPERATIONS ====================
    
    def update_stock(self) -> None:
        """Update stock quantity for a product."""
        try:
            product_id = int(self.stock_id_entry.get())
            amount = int(self.stock_amount_entry.get())

            if amount == 0:
                raise ValueError("Amount cannot be zero.")
            
            self.inventory.update_stock(product_id, amount)
            
            self.stock_id_entry.delete(0, 'end')
            self.stock_amount_entry.delete(0, 'end')
            self.refresh_all()
            
            action = "increased" if amount > 0 else "decreased"
            self.show_success(f"Stock {action} by {abs(amount)}")
            
        except (ValueError, InventoryError) as e:
            self.show_error(str(e))

    def apply_low_stock_threshold(self) -> None:
        """Apply and save the low stock threshold setting."""
        try:
            text = self.threshold_entry.get().strip()

            if not text:
                raise ValueError("Threshold cannot be empty")

            value = int(text)

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


    def update_low_stock_list(self) -> None:
        """Update low stock alert list based on current threshold."""
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

    # ==================== UTILITY FUNCTIONS ====================
    
    def refresh_all(self) -> None:
        """Refresh all UI elements.
        
        This no longer writes to disk immediately; autosave is handled by a
        periodic timer to reduce write frequency.
        """
        self.update_category_list()
        self.update_product_list()
        self.update_low_stock_list()
        
        total = self.inventory.get_total_value()
        self.total_value_label.configure(text=f"Total Inventory Value: ${total:,.2f}")

    def show_error(self, message: str) -> None:
        """Display error message dialog.
        
        Args:
            message: Error message to display
        """
        logger.warning(f"User error: {message}")
        messagebox.showerror("Error", message)

    def show_success(self, message: str) -> None:
        """Display success message dialog.
        
        Args:
            message: Success message to display
        """
        logger.info(f"User action: {message}")
        messagebox.showinfo("Success", message)

    def export_inventory_csv(self) -> None:
        """Export current inventory to CSV file."""
        try:
            self.storage.export_to_csv(self.inventory)
            self.show_success("Inventory exported successfully as inventory_export.csv")
        except ValueError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Export failed: {e}")
    
    def export_inventory_pdf(self) -> None:
        """Export current inventory to PDF report."""
        try:
            self.storage.export_to_pdf(self.inventory)
            self.show_success("Inventory exported successfully as inventory_export.pdf")
        except ValueError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Export failed: {e}")

    def clear_sort(self) -> None:
        """Reset product list sorting to default (by ID)."""
        self.sort_var.set("Sort by Price")
        self.update_product_list()

    # ------------------ Autosave Helpers ------------------
    def schedule_autosave(self) -> None:
        """Schedule periodic autosave checks."""
        self.after(5000, self._autosave)

    def _autosave(self) -> None:
        """Autosave inventory if it has unsaved changes."""
        if self.inventory.is_dirty():
            try:
                self.storage.save_inventory(self.inventory)
                self.inventory.clear_dirty()
                logger.info("Autosave completed")
            except Exception as e:
                logger.error(f"Autosave failed: {e}")
        self.schedule_autosave()

    def on_close(self) -> None:
        """Save inventory and close the application."""
        try:
            if self.inventory.is_dirty():
                self.storage.save_inventory(self.inventory)
                logger.info("Application closing. Inventory saved.")
        except Exception as e:
            logger.error(f"Save error on close: {e}")
            messagebox.showerror("Save Error", f"Could not save inventory: {e}")
        self.destroy()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()