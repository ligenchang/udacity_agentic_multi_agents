# The Beaver's Choice Paper Company - Multi-Agent System Implementation

## Architecture Overview

This multi-agent system implements a paper company management solution with four agents:

1. **Orchestrator Agent**: Coordinates the workflow between specialized agents, handles request parsing, and generates customer responses.
2. **Inventory Agent**: Manages stock levels, checks availability, and handles reordering when stock is low.
3. **Quoting Agent**: Calculates pricing for customer requests and searches for similar historical quotes.
4. **Ordering Agent**: Processes approved quotes into orders and generates financial reports.

## Agent Workflow

1. Customer request comes in → Orchestrator extracts items and context
2. Inventory Agent checks availability of requested items
3. Quoting Agent calculates pricing and applies discounts
4. If all items are available, Ordering Agent processes the transaction
5. Orchestrator generates a customer-friendly response
6. Inventory Agent checks for reorder needs and places orders if necessary

## Tools and Helper Functions

### Inventory Agent Tools:
- `check_stock_level` - Uses `get_stock_level()` to check specific item stock
- `check_inventory_status` - Uses `get_all_inventory()` for a full inventory snapshot
- `check_reorder_requirements` - Identifies items below minimum stock levels
- `place_stock_order` - Uses `create_transaction()` to order more inventory

### Quoting Agent Tools:
- `calculate_quote` - Checks availability and calculates pricing with discounts
- `search_similar_quotes` - Uses `search_quote_history()` to find similar past quotes

### Ordering Agent Tools:
- `process_order` - Uses `create_transaction()` to record sales
- `generate_order_summary` - Creates customer-friendly order summaries
- `get_financial_snapshot` - Uses `generate_financial_report()` for financial status

## Key Features

- **Automated Request Parsing**: Uses LLM to extract item names and quantities from natural language requests
- **Context-Aware Quoting**: Considers job type, event type, and order size
- **Volume Discounts**: Applies 15% discount for orders over 1000 units
- **Inventory Management**: Automatically reorders items when stock is low
- **Financial Tracking**: Monitors cash balance and inventory value

## Running the System

To run the multi-agent system:

1. Install required packages: `pip install -r requirements.txt`
2. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_key_here
   ```
3. Run the project: `python project_starter.py`

The system will process requests from `quote_requests_sample.csv` and generate responses based on inventory availability and pricing.

## Performance and Evaluation

The system is designed to handle a variety of customer requests while maintaining:
- Accurate inventory tracking
- Proper financial records
- Customer-friendly responses
- Automated reordering

Results from test runs are saved to `test_results.csv` for evaluation.

## Future Improvements

Potential enhancements for the system:
1. Advanced pricing strategies based on customer history
2. Smarter inventory management with demand forecasting
3. More sophisticated natural language processing for request parsing
4. Integration with external supplier APIs for real-time ordering
