import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union, Any, Callable
from sqlalchemy import create_engine, Engine
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


# Set up and load your env parameters and instantiate your model.
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE = os.getenv("OPENAI_BASE_URL", "https://openai.vocareum.com/v1")
MODEL_ID = os.getenv("OPENAI_MODEL_ID", "gpt-4o-mini")

client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE,
)

"""Set up tools for your agents to use, these should be methods that combine the database functions above
 and apply criteria to them to ensure that the flow of the system is correct."""

# Common tool types for our agents
class Tool:
    def __init__(self, name: str, func: Callable, description: str):
        self.name = name
        self.func = func
        self.description = description
    
    def execute(self, *args, **kwargs):
        return self.func(*args, **kwargs)

# Base class for all agents
class Agent:
    def __init__(self, name: str, model: str = MODEL_ID, tools: List[Tool] = None):
        self.name = name
        self.model = model
        self.tools = tools or []
        self.memory = []
    
    def run(self, task: str, *args, **kwargs):
        # This will be implemented by specific agent types
        pass
    
    def add_to_memory(self, message: Dict):
        self.memory.append(message)

# Tools for inventory agent
def check_stock_level(item_name: str, as_of_date: str) -> Dict:
    """
    Check the current stock level of a specific item.
    
    Args:
        item_name (str): The name of the item to check
        as_of_date (str): The date as of which to check the stock
        
    Returns:
        Dict: A dictionary containing item name and current stock
    """
    stock_info = get_stock_level(item_name, as_of_date)
    return {"item_name": item_name, "current_stock": stock_info["current_stock"].iloc[0]}

def check_inventory_status(as_of_date: str) -> Dict:
    """
    Get a complete inventory snapshot as of a given date.
    
    Args:
        as_of_date (str): The date for which to check inventory
        
    Returns:
        Dict: A dictionary mapping item names to their stock levels
    """
    return get_all_inventory(as_of_date)

def check_reorder_requirements(as_of_date: str) -> List[Dict]:
    """
    Check which items need to be reordered based on minimum stock levels.
    
    Args:
        as_of_date (str): The date for which to check reorder needs
        
    Returns:
        List[Dict]: A list of items that need reordering with quantities
    """
    # Get current inventory
    current_inventory = get_all_inventory(as_of_date)
    
    # Get minimum stock levels from inventory table
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    
    # Identify items that need reordering
    reorder_items = []
    for _, item in inventory_df.iterrows():
        item_name = item["item_name"]
        min_level = item["min_stock_level"]
        current_level = current_inventory.get(item_name, 0)
        
        if current_level <= min_level:
            reorder_items.append({
                "item_name": item_name,
                "current_stock": current_level,
                "min_stock_level": min_level,
                "reorder_quantity": max(500, min_level * 2 - current_level)  # Simple reorder formula
            })
    
    return reorder_items

def place_stock_order(item_name: str, quantity: int, date: str) -> Dict:
    """
    Place an order for more stock of a specific item.
    
    Args:
        item_name (str): The name of the item to order
        quantity (int): The quantity to order
        date (str): The date of the order
        
    Returns:
        Dict: Order details including delivery date and transaction ID
    """
    # Get item price from inventory
    inventory_df = pd.read_sql(
        "SELECT * FROM inventory WHERE item_name = :item_name",
        db_engine,
        params={"item_name": item_name}
    )
    
    if inventory_df.empty:
        return {"error": f"Item {item_name} not found in inventory"}
    
    unit_price = inventory_df["unit_price"].iloc[0]
    total_price = unit_price * quantity
    
    # Check if we have enough cash
    cash_balance = get_cash_balance(date)
    if cash_balance < total_price:
        return {
            "error": f"Insufficient funds to order {quantity} units of {item_name}. "
                     f"Required: ${total_price:.2f}, Available: ${cash_balance:.2f}"
        }
    
    # Calculate delivery date
    delivery_date = get_supplier_delivery_date(date, quantity)
    
    # Create transaction
    transaction_id = create_transaction(
        item_name=item_name,
        transaction_type="stock_orders",
        quantity=quantity,
        price=total_price,
        date=date
    )
    
    return {
        "item_name": item_name,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "order_date": date,
        "delivery_date": delivery_date,
        "transaction_id": transaction_id
    }

# Tools for quoting agent
def calculate_quote(
    items: List[Dict[str, Union[str, int]]],
    date: str,
    request_context: Dict = None
) -> Dict:
    """
    Calculate a quote for a customer request.
    
    Args:
        items (List[Dict]): List of items and quantities requested
        date (str): Date of the quote
        request_context (Dict, optional): Additional context about the request
        
    Returns:
        Dict: Quote details including pricing and availability
    """
    # Get current inventory
    current_inventory = get_all_inventory(date)
    
    # Get item prices from inventory
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    
    # Initialize response
    response = {
        "date": date,
        "items": [],
        "total_amount": 0.0,
        "all_items_available": True,
        "explanation": "",
        "context": request_context or {}
    }
    
    # Process each requested item
    for item in items:
        item_name = item["item_name"]
        quantity = item["quantity"]
        
        # Get item details
        item_info = inventory_df[inventory_df["item_name"] == item_name]
        
        if item_info.empty:
            # Item not in catalog
            response["items"].append({
                "item_name": item_name,
                "quantity": quantity,
                "available": False,
                "reason": "Item not in catalog"
            })
            response["all_items_available"] = False
            continue
        
        unit_price = item_info["unit_price"].iloc[0]
        available_stock = current_inventory.get(item_name, 0)
        
        if available_stock < quantity:
            # Not enough stock
            response["items"].append({
                "item_name": item_name,
                "quantity": quantity,
                "available": False,
                "available_stock": available_stock,
                "unit_price": unit_price,
                "reason": f"Insufficient stock. Only {available_stock} units available."
            })
            response["all_items_available"] = False
        else:
            # Item available
            item_total = unit_price * quantity
            response["items"].append({
                "item_name": item_name,
                "quantity": quantity,
                "available": True,
                "unit_price": unit_price,
                "item_total": item_total
            })
            response["total_amount"] += item_total
    
    # Apply volume discount if applicable
    total_quantity = sum(item["quantity"] for item in items)
    if total_quantity > 1000:
        discount = 0.15  # 15% discount for large orders
        original_amount = response["total_amount"]
        response["total_amount"] *= (1 - discount)
        response["discount_applied"] = {
            "rate": discount,
            "amount": original_amount * discount,
            "reason": "Volume discount for orders over 1000 units"
        }
    
    # Generate explanation
    if response["all_items_available"]:
        response["explanation"] = "All requested items are available. "
        if response.get("discount_applied"):
            response["explanation"] += f"A {response['discount_applied']['rate']*100}% discount was applied due to the large order size."
    else:
        response["explanation"] = "Some items are not available in the requested quantities. See item details for more information."
    
    return response

def search_similar_quotes(request_context: Dict) -> List[Dict]:
    """
    Search for similar historical quotes based on request context.
    
    Args:
        request_context (Dict): Context of the current request
        
    Returns:
        List[Dict]: List of similar historical quotes
    """
    search_terms = []
    
    # Extract relevant terms from context
    if "job_type" in request_context and request_context["job_type"]:
        search_terms.append(request_context["job_type"])
    
    if "event_type" in request_context and request_context["event_type"]:
        search_terms.append(request_context["event_type"])
    
    if "items" in request_context:
        for item in request_context["items"]:
            if isinstance(item, dict) and "item_name" in item:
                search_terms.append(item["item_name"])
    
    # Add any other relevant terms
    for key in ["organization", "industry", "purpose"]:
        if key in request_context and request_context[key]:
            search_terms.append(request_context[key])
    
    # Remove duplicates and empty terms
    search_terms = list(set(term for term in search_terms if term))
    
    if not search_terms:
        return []
    
    # Search for similar quotes
    return search_quote_history(search_terms)

# Tools for ordering agent
def process_order(quote: Dict, date: str) -> Dict:
    """
    Process an approved quote into an order.
    
    Args:
        quote (Dict): The quote to process
        date (str): The date of the order
        
    Returns:
        Dict: Order details including status and transaction IDs
    """
    if not quote["all_items_available"]:
        return {
            "status": "failed",
            "reason": "Cannot process order with unavailable items",
            "date": date
        }
    
    # Initialize response
    response = {
        "status": "processing",
        "date": date,
        "items": [],
        "total_amount": quote["total_amount"],
        "transactions": []
    }
    
    # Process each item in the quote
    for item in quote["items"]:
        if not item["available"]:
            # This shouldn't happen if all_items_available is True
            response["status"] = "failed"
            response["reason"] = f"Item {item['item_name']} is not available"
            return response
        
        # Create sales transaction
        transaction_id = create_transaction(
            item_name=item["item_name"],
            transaction_type="sales",
            quantity=item["quantity"],
            price=item["item_total"] if "discount_applied" not in quote else item["item_total"] * (1 - quote["discount_applied"]["rate"]),
            date=date
        )
        
        response["items"].append({
            "item_name": item["item_name"],
            "quantity": item["quantity"],
            "transaction_id": transaction_id
        })
        
        response["transactions"].append(transaction_id)
    
    response["status"] = "completed"
    return response

def generate_order_summary(order: Dict) -> str:
    """
    Generate a customer-friendly summary of an order.
    
    Args:
        order (Dict): The processed order
        
    Returns:
        str: A formatted summary of the order
    """
    if order["status"] != "completed":
        return f"Order Status: {order['status']}\nReason: {order.get('reason', 'Unknown error')}"
    
    summary = [
        f"Order successfully processed on {order['date']}",
        f"Total amount: ${order['total_amount']:.2f}",
        "\nItems ordered:"
    ]
    
    for item in order["items"]:
        summary.append(f"- {item['quantity']} units of {item['item_name']}")
    
    summary.append("\nThank you for your business!")
    
    return "\n".join(summary)

def get_financial_snapshot(date: str) -> Dict:
    """
    Get a financial snapshot of the company.
    
    Args:
        date (str): The date for the snapshot
        
    Returns:
        Dict: Financial summary including cash and inventory
    """
    report = generate_financial_report(date)
    return {
        "date": date,
        "cash_balance": report["cash_balance"],
        "inventory_value": report["inventory_value"],
        "total_assets": report["total_assets"]
    }

# Set up your agents and create an orchestration agent that will manage them.

# Inventory Agent - Responsible for inventory management
class InventoryAgent(Agent):
    def __init__(self):
        tools = [
            Tool("check_stock", check_stock_level, "Check the stock level of a specific item"),
            Tool("check_inventory", check_inventory_status, "Get a snapshot of all inventory"),
            Tool("check_reorder", check_reorder_requirements, "Check which items need reordering"),
            Tool("place_order", place_stock_order, "Place an order for more stock")
        ]
        super().__init__("Inventory Agent", tools=tools)
    
    def run(self, task: str, **kwargs):
        if task == "check_stock":
            return self.tools[0].execute(kwargs["item_name"], kwargs["date"])
        elif task == "check_inventory":
            return self.tools[1].execute(kwargs["date"])
        elif task == "check_reorder":
            return self.tools[2].execute(kwargs["date"])
        elif task == "place_order":
            return self.tools[3].execute(
                kwargs["item_name"], 
                kwargs["quantity"], 
                kwargs["date"]
            )
        else:
            return {"error": f"Unknown task: {task}"}

# Quoting Agent - Responsible for generating quotes
class QuotingAgent(Agent):
    def __init__(self):
        tools = [
            Tool("calculate_quote", calculate_quote, "Calculate a quote for a customer request"),
            Tool("search_similar", search_similar_quotes, "Search for similar historical quotes")
        ]
        super().__init__("Quoting Agent", tools=tools)
    
    def run(self, task: str, **kwargs):
        if task == "calculate_quote":
            return self.tools[0].execute(
                kwargs["items"], 
                kwargs["date"], 
                kwargs.get("request_context")
            )
        elif task == "search_similar":
            return self.tools[1].execute(kwargs["request_context"])
        else:
            return {"error": f"Unknown task: {task}"}

# Ordering Agent - Responsible for processing orders
class OrderingAgent(Agent):
    def __init__(self):
        tools = [
            Tool("process_order", process_order, "Process an approved quote into an order"),
            Tool("generate_summary", generate_order_summary, "Generate a customer-friendly summary"),
            Tool("get_financial", get_financial_snapshot, "Get a financial snapshot")
        ]
        super().__init__("Ordering Agent", tools=tools)
    
    def run(self, task: str, **kwargs):
        if task == "process_order":
            return self.tools[0].execute(kwargs["quote"], kwargs["date"])
        elif task == "generate_summary":
            return self.tools[1].execute(kwargs["order"])
        elif task == "get_financial":
            return self.tools[2].execute(kwargs["date"])
        else:
            return {"error": f"Unknown task: {task}"}

# Orchestrator Agent - Manages the workflow between agents
class OrchestratorAgent:
    def __init__(self):
        self.inventory_agent = InventoryAgent()
        self.quoting_agent = QuotingAgent()
        self.ordering_agent = OrderingAgent()
        self.request_history = []
    
    def extract_items_from_request(self, request: str) -> List[Dict]:
        """
        Extract requested items and quantities from a natural language request.
        Uses the model to parse the request and identify paper products and quantities.
        
        Args:
            request (str): The customer's request
            
        Returns:
            List[Dict]: List of items and quantities extracted from the request
        """
        # First, get all inventory items for reference
        inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
        item_names = inventory_df["item_name"].tolist()
        
        # Create a prompt to extract items and quantities
        prompt = f"""
        Extract all paper products and their quantities from the following customer request.
        Only include items that are explicitly mentioned with quantities.
        Format your response as a JSON list of objects, each with "item_name" and "quantity" fields.
        
        Available items in inventory:
        {', '.join(item_names)}
        
        Customer request:
        {request}
        
        Output only the JSON list, nothing else.
        """
        
        try:
            response = client.chat.completions.create(
                model=self.quoting_agent.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            items_data = ast.literal_eval(content)
            
            # Validate and clean up the extracted items
            extracted_items = []
            for item in items_data.get("items", []):
                if "item_name" in item and "quantity" in item:
                    # Find the closest matching item in inventory
                    closest_match = None
                    for inv_item in item_names:
                        if item["item_name"].lower() in inv_item.lower() or inv_item.lower() in item["item_name"].lower():
                            closest_match = inv_item
                            break
                    
                    if closest_match:
                        extracted_items.append({
                            "item_name": closest_match,
                            "quantity": int(item["quantity"])
                        })
            
            return extracted_items
        
        except Exception as e:
            print(f"Error extracting items: {e}")
            return []
    
    def extract_context_from_request(self, request: str, job_type: str = None, event_type: str = None) -> Dict:
        """
        Extract contextual information from a customer request.
        
        Args:
            request (str): The customer's request
            job_type (str, optional): The type of job if known
            event_type (str, optional): The type of event if known
            
        Returns:
            Dict: Contextual information extracted from the request
        """
        prompt = f"""
        Extract contextual information from the following customer request.
        Include details about:
        - Purpose of the order
        - Organization type
        - Industry
        - Event type
        - Order size (small, medium, large)
        - Any special requirements
        
        Format your response as a JSON object with these fields (only include fields with information).
        
        Customer request:
        {request}
        
        Output only the JSON object, nothing else.
        """
        
        try:
            response = client.chat.completions.create(
                model=self.quoting_agent.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            context_data = ast.literal_eval(content)
            
            # Add job_type and event_type if provided
            if job_type:
                context_data["job_type"] = job_type
            if event_type:
                context_data["event_type"] = event_type
            
            return context_data
        
        except Exception as e:
            print(f"Error extracting context: {e}")
            return {"job_type": job_type, "event_type": event_type} if (job_type or event_type) else {}
    
    def generate_response(self, process_result: Dict, request: str, date: str) -> str:
        """
        Generate a customer-friendly response based on the processing result.
        
        Args:
            process_result (Dict): The result of processing the request
            request (str): The original customer request
            date (str): The date of the request
            
        Returns:
            str: A customer-friendly response
        """
        # Create a prompt for generating a response
        prompt = f"""
        Generate a polite and professional response to the customer based on the processing result.
        
        Customer request:
        {request}
        
        Processing result:
        {process_result}
        
        Date: {date}
        
        Your response should:
        1. Be friendly and personalized
        2. Clearly explain if we can fulfill their request or not
        3. Include pricing details if applicable
        4. Mention delivery timeframes if applicable
        5. Thank the customer for their business
        
        Output only the response text, nothing else.
        """
        
        try:
            response = client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"Error generating response: {e}")
            
            # Fallback response
            if process_result.get("status") == "completed":
                return f"Thank you for your order! Your total comes to ${process_result.get('total_amount', 0):.2f}. Your items will be processed promptly."
            elif process_result.get("error"):
                return f"We apologize, but we cannot process your request at this time due to: {process_result.get('error')}. Please contact us for more information."
            else:
                return "Thank you for your inquiry. We will process your request and get back to you soon."
    
    def process_request(self, request: str, date: str, job_type: str = None, event_type: str = None) -> str:
        """
        Process a customer request through the multi-agent system.
        
        Args:
            request (str): The customer's request
            date (str): The date of the request
            job_type (str, optional): The type of job if known
            event_type (str, optional): The type of event if known
            
        Returns:
            str: A response to the customer
        """
        # Step 1: Extract items and context from the request
        items = self.extract_items_from_request(request)
        context = self.extract_context_from_request(request, job_type, event_type)
        
        if not items:
            return "I'm sorry, but I couldn't identify any specific paper products in your request. Could you please provide more details about what items and quantities you need?"
        
        # Step 2: Check inventory for requested items
        inventory_status = self.inventory_agent.run("check_inventory", date=date)
        
        # Step 3: Calculate a quote
        quote = self.quoting_agent.run(
            "calculate_quote", 
            items=items, 
            date=date, 
            request_context=context
        )
        
        # Step 4: Look for similar quotes for reference
        similar_quotes = self.quoting_agent.run(
            "search_similar", 
            request_context=context
        )
        
        # Step 5: Process the order if all items are available
        if quote.get("all_items_available", False):
            order = self.ordering_agent.run(
                "process_order", 
                quote=quote, 
                date=date
            )
            
            # Generate order summary
            if order.get("status") == "completed":
                result = {
                    "status": "completed",
                    "order": order,
                    "total_amount": quote["total_amount"],
                    "explanation": quote.get("explanation", "")
                }
            else:
                result = {
                    "status": "failed",
                    "reason": order.get("reason", "Unknown error processing order"),
                    "quote": quote
                }
        else:
            # Just return the quote if not all items are available
            result = {
                "status": "quote_only",
                "quote": quote,
                "reason": "Not all requested items are available"
            }
        
        # Check if we need to reorder any inventory
        reorder_items = self.inventory_agent.run("check_reorder", date=date)
        for item in reorder_items:
            print(f"Reordering {item['reorder_quantity']} units of {item['item_name']}")
            reorder_result = self.inventory_agent.run(
                "place_order",
                item_name=item["item_name"],
                quantity=item["reorder_quantity"],
                date=date
            )
            if "error" in reorder_result:
                print(f"Error reordering {item['item_name']}: {reorder_result['error']}")
        
        # Get updated financial status
        financial = self.ordering_agent.run("get_financial", date=date)
        
        # Save request and processing details to history
        self.request_history.append({
            "request": request,
            "date": date,
            "items": items,
            "context": context,
            "quote": quote,
            "result": result,
            "financial": financial
        })
        
        # Generate customer response
        return self.generate_response(result, request, date)

# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine)
    
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    ############
    ############
    ############
    # INITIALIZE YOUR MULTI AGENT SYSTEM HERE
    ############
    ############
    ############
    
    # Initialize the orchestrator agent
    orchestrator = OrchestratorAgent()

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        ############
        ############
        ############
        # USE YOUR MULTI AGENT SYSTEM TO HANDLE THE REQUEST
        ############
        ############
        ############

        response = orchestrator.process_request(
            request=request_with_date,
            date=request_date,
            job_type=row['job'],
            event_type=row['event']
        )

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results

# Execute the test scenarios when the script is run
if __name__ == "__main__":
    print("Starting The Beaver's Choice Paper Company Multi-Agent System...")
    run_test_scenarios()
    print("Test scenarios completed. Results saved to test_results.csv")