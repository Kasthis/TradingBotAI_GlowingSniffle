import tkinter as tk  # used for building a gui interface
from tkinter import (
    ttk,
    messagebox,
)  # It refers to pop up messages, buttons, progress bars etc.
import json  # applied for configurating files and API responses
import time
import threading  # to run multiple activities plus running background
import alpaca_trade_api as tradeapi
from dotenv import (
    load_dotenv,
)  # Make sure to pip install python-dotenv if you haven't already
from together import Together
import os

DATA_FILE = "equities.json"  # it basically stores the equities we are trading and the levels we are trading at, so actual positions.

key = "PKGHDEM3SP5EACLSW37S"
secret_key = "7PVtNJU0o1N3IGoHKqLfp3IQ5rTlEgYpSW4BdMKE"
BASE_URL = "https://paper-api.alpaca.markets/"
api = tradeapi.REST(key, secret_key, BASE_URL, api_version="v2")


load_dotenv()

api_key = os.environ.get("TOGETHER_API_KEY")

client = Together(api_key=api_key)


# MOCK FUNCTIONS:
def fetch_mock_api(symbol):
    return {"price": 100}


def mock_llm_response(message):
    # Simulate a delay for the mock LLM response
    return f"Mock response to: {message}"


def fetch_portfolio():
    """Fetches current market positions."""
    positions = api.list_positions()
    portfolio = []
    for pos in positions:
        portfolio.append(
            {
                "symbol": pos.symbol,
                "qty": pos.qty,
                "entry_price": pos.avg_entry_price,
                "current_price": pos.current_price,
                "unrealized_pl": pos.unrealized_pl,
                "side": "buy",
            }
        )
    return portfolio


def fetch_open_orders():
    """Fetches open orders that have not been filled."""
    orders = api.list_orders(status="open")
    open_orders = []
    for order in orders:
        open_orders.append(
            {
                "symbol": order.symbol,
                "qty": order.qty,
                "order_type": order.order_type,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price,
                "side": "buy",
            }
        )


def llm_response(message):
    portfolio_data = fetch_portfolio()
    open_orders = fetch_open_orders()

    # --- NEW: Check if both portfolio and orders are empty ---
    if not portfolio_data and not open_orders:
        return "You have no open positions or pending orders at the moment. Your portfolio is currently empty."

    pre_prompt = f""" You are an AI Portfolio Manage responsible for analyzing my portfolio. 
    Your tasks are the following: 
    1.) Evaluate risk exposures of my current holdings 
    2.) Analyze my open limit orders and their potential impact 
    3.) provide insights into portfolio health, diversification, trade adj. etc. 
    4.) Speculate on the market outlook based on current market conditions 
    5.) Identify potential market risks and suggest risk management strategies 
    
    Here is my portfolio: {portfolio_data if portfolio_data else "No open positions."}
    
    Here are my open_orders: {open_orders if open_orders else "No open orders"} 
    
    Overall, answer the following question with priority having that background: {message}
    
    """

    response = client.chat.completions.create(
        model="meta-llama/Llama-Vision-Free",
        messages=[{"role": "system", "content": pre_prompt}],
    )
    # --- CHANGE 1: Extract the text content from the response object ---
    return response.choices[0].message.content


# Now let us build the trading bot class
class TradingBotGUI:
    def __init__(self, root):  # constructor class
        self.root = root
        self.root.title("AI Equities Trading Bot")
        self.equities = (
            self.load_equities()
        )  # We have to populate the saved information in some way right?

        # Create a flag if the system is running or not
        self.system_running = False  # it tell us if we actively trading or not. And we want to toggle that on and off

        self.form_frame = tk.Frame(
            root
        )  # Creates a Widget container for other widgets, root is the parent widget
        self.form_frame.pack(
            pady=10
        )  # Pack is a geometry manager, in this case it adds spacing between the widgets

        # Different Labels deployments.

        # Form to add new equity to our bot - symbol to trade
        self.symbol_label = tk.Label(self.form_frame, text="Symbol")
        self.symbol_label.grid(row=0, column=0)  # Implement a table like structure.
        self.symbol_entry = tk.Entry(self.form_frame)
        self.symbol_entry.grid(row=0, column=1)

        # Form to add levels to our bot - level to trade
        tk.Label(self.form_frame, text="Levels").grid(row=0, column=2)
        self.level_entry = tk.Entry(self.form_frame)
        self.level_entry.grid(row=0, column=3)

        # Form to add drawdown to our bot
        tk.Label(self.form_frame, text="Drawdown").grid(row=0, column=4)
        self.drawdown_entry = tk.Entry(self.form_frame)
        self.drawdown_entry.grid(row=0, column=5)

        self.add_button = tk.Button(
            self.form_frame, text="Add equity", command=self.add_equity
        )
        self.add_button.grid(row=0, column=6)

        # Table to track the traded equities
        self.tree = ttk.Treeview(
            root,
            columns=("Symbol", "Position", "Entry Price", "Levels", "Status"),
            show="headings",
        )

        # Check the current portfolio in the trading bot
        for col in ["Symbol", "Position", "Entry Price", "Levels", "Status"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(pady=10)

        # Insert Buttons to control the bot
        self.toggle_system_button = tk.Button(
            root, text="Toggle Selected System", command=self.toggle_selected_system
        )
        self.toggle_system_button.pack(pady=6)

        self.remove_button = tk.Button(
            root,
            text="Remove Toggle Selected Equity",
            command=self.remove_selected_equity,
        )
        self.remove_button.pack(pady=6)

        # Making the AI(llm) component
        self.llm_frame = tk.Frame(root)
        self.llm_frame.pack(pady=10)

        self.llm_input = tk.Entry(self.llm_frame, width=60)
        self.llm_input.grid(row=0, column=0, padx=5)

        self.send_button = tk.Button(
            self.llm_frame, text="Send", command=self.send_message
        )
        self.send_button.grid(row=0, column=1)

        self.llm_output = tk.Text(root, height=5, width=60, state=tk.DISABLED)
        self.llm_output.pack()

        # # # # # # # # # # # # # # # # # - UI FINISHED

        # Time to make functionalities
        # Load saved data
        self.refresh_table()  # IT is gonna help to load the json file

        # Auto refresh function
        self.system_running = True
        self.auto_update_thread = threading.Thread(
            target=self.auto_update, daemon=True
        )  # Creates a new thread (parallel execution path) separate from the main program
        # Automatically terminates when the main program exits.

        self.auto_update_thread.start()  # Allow to query the updates

    def add_equity(self):
        symbol = self.symbol_entry.get().upper()
        levels = self.level_entry.get()
        drawdown = self.drawdown_entry.get()

        # Handling for valid inputs reasonable first line of defense
        if (
            not symbol
            or not levels.isdigit()
            or not drawdown.replace(".", "", 1).isdigit()
        ):
            messagebox.showerror("Error", "Invalid Input")
            return

        levels = int(levels)
        drawdown = float(drawdown) / 100
        entry_price = fetch_mock_api(symbol)["price"]  # type: ignore

        # Determine the prices to trade at for the following levels
        level_prices = {
            i + 1: round(entry_price * (1 - drawdown * (i + 1)), 2)  # Fixed!
            for i in range(levels)
        }  # Formula for the Strategy. We enter at 100, we are 10% drawdown per level, then we are gonna assume that level entry price is fixed, every 10 dollars we are gonna place a buy

        self.equities[symbol] = {
            "position": 0,
            "entry_price": entry_price,
            "levels": level_prices,
            "drawdown": drawdown,
            "status": "Off",
        }

        self.save_equities()
        self.refresh_table()

    def toggle_selected_system(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "No Equity is selected")
            return

        # Otherwise
        for item in selected_items:
            symbol = self.tree.item(item)["values"][0]
            self.equities[symbol]["status"] = (
                "On" if self.equities[symbol]["status"] == "Off" else "Off"
            )

        self.save_equities()
        self.refresh_table()

    # Write code to remove an equity in case its going badly or don't like it. Opposite of ADD Equity
    def remove_selected_equity(self):
        selected_items = self.tree.selection()
        if not selected_items:  # if nothing is selected
            messagebox.showwarning("Warning", "No Equity selected")
            return

        for item in selected_items:
            symbol = self.tree.item(item)["values"][0]
            if symbol in self.equities:
                del self.equities[symbol]  # Deletion of the symbol

        self.save_equities()
        self.refresh_table()

    # Filler function for the LLM language output
    def send_message(self):
        message = self.llm_input.get()
        # Once we send and get the message from the form created we will insert to the llm
        if not message:
            return

        response = llm_response(message)  # Will build later on

        self.llm_output.config(state=tk.NORMAL)
        self.llm_output.insert(tk.END, f"You: {message}\n{response}\n\n")
        self.llm_frame_output.config(state=tk.DISABLED)
        self.llm_input.delete(0, tk.END)  # Deleting the words once we needed them

    # first usage of API method
    def check_existing_orders(self, symbol, price):
        try:
            # That's where we use the API.
            # We get the orders from the account and bring it here:
            orders = api.list_orders(status="open", symbols=symbol)
            for order in orders:
                if (order.limit_price) == price:
                    return True
        except Exception as e:
            messagebox.showerror("API Error", f"Error Checking orders {e}")
        return False

    # Get current pricing information
    def fetch_alpaca_data(self, symbol):
        try:
            barset = api.get_latest_trade(symbol)
            return {"price": barset.price}
        except Exception as e:
            return {"price": -1}

    def get_max_entry_price(self, symbol):
        try:
            orders = api.list_orders(status="filled", limit=50)
            prices = [
                float(order.filled_avg_price)
                for order in orders
                if order.filled_avg_price and order.symbol == symbol
            ]
            return max(prices) if prices else -1
        except Exception as e:
            messagebox.showerror("API error", f"Error Fetching Orders {e}")
            return 0

    def trade_system(self):
        for symbol, data in list(self.equities.items()):
            if data["status"] == "On":
                current_price = self.fetch_alpaca_data(symbol)[
                    "price"
                ]  # Get current price first

                if current_price == -1:  # Handle API data fetch failure
                    print(f"Skipping {symbol}: Could not fetch current price.")
                    continue

                position_exist = False
                try:
                    position = api.get_position(symbol)
                    entry_price = float(
                        position.avg_entry_price
                    )  # Directly get from position object
                    position_exist = True

                    # If position exists, also update our stored entry_price in case it changed
                    self.equities[symbol]["entry_price"] = entry_price
                    self.equities[symbol]["position"] = int(
                        float(position.qty)
                    )  # Update qty from live position

                # If we do not have any active position then:
                except Exception as e:
                    print(f"No existing position for {symbol}. Placing initial order.")
                    try:
                        api.submit_order(
                            symbol=symbol,
                            qty=1,
                            side="buy",
                            type="market",
                            time_in_force="gtc",
                        )
                        messagebox.showinfo(
                            "Order Placed", f"Initial Order Placed for {symbol}"
                        )
                        # --- Wait for order to fill and get entry price ---
                        max_wait_time = 30  # seconds
                        poll_interval = 5  # seconds
                        order_filled = False
                        for _ in range(max_wait_time // poll_interval):
                            time.sleep(poll_interval)
                            try:
                                position = api.get_position(symbol)
                                entry_price = float(position.avg_entry_price)
                                self.equities[symbol]["entry_price"] = entry_price
                                self.equities[symbol]["position"] = int(
                                    float(position.qty)
                                )
                                position_exist = True
                                order_filled = True
                                print(
                                    f"Initial order for {symbol} filled. Entry price: {entry_price}"
                                )
                                break  # Exit polling loop
                            except Exception:
                                print(
                                    f"Waiting for initial order for {symbol} to fill..."
                                )
                                continue

                        if not order_filled:
                            messagebox.showerror(
                                "Order Timeout",
                                f"Initial Order  for {symbol} did not fill in time",
                            )
                            print(
                                f"Skipping {symbol}: Initial order did not fill in time."
                            )
                            continue  # Move to next symbol if order didn't fill

                    except Exception as order_e:
                        messagebox.showerror(
                            "Order Submission Error",
                            f"Error submitting initial order for {symbol}: {order_e}",
                        )
                        print(f"Skipping {symbol}: Error submitting initial order.")
                        continue  # Move to next symbol if order submission failed

                # If we reach here, entry_price should be valid (positive)
                if entry_price <= 0:  # Double check after polling/getting position
                    print(f"Skipping {symbol}: Invalid entry price ({entry_price}).")
                    continue

                print(f"Current entry_price for {symbol}: {entry_price}")

                # Recalculate levels using the confirmed positive entry_price
                level_prices = {
                    i + 1: round(entry_price * (1 - data["drawdown"] * (i + 1)), 2)
                    for i in range(len(data["levels"]))
                }

                existing_levels = self.equities[symbol]["levels"]

                # No change to the existing_levels assignment based on the current for loop behavior.
                # This ensures the original levels from add_equity are retained unless they are "traded" to negative.

                self.equities[symbol]["entry_price"] = entry_price
                # self.equities[symbol]["levels"] is already updated by place_order
                # self.equities[symbol]["position"] is updated above when position exists

                # Logic to place orders for calculated level:
                for level_num, calculated_price in level_prices.items():
                    # Check if this positive level still exists and hasn't been "traded" yet (marked negative)
                    if (
                        level_num in self.equities[symbol]["levels"]
                        and -level_num not in self.equities[symbol]["levels"]
                    ):
                        # Only place if the calculated price is valid
                        if calculated_price > 0:
                            self.place_order(symbol, calculated_price, level_num)
                        else:
                            print(
                                f"Skipping order for {symbol} level {level_num}: Calculated price is not positive ({calculated_price})."
                            )

            self.save_equities()
            self.refresh_table()

        else:
            return  # if the system is off

    # If we've already dealt with this specific price level (or its inverse) in some way,
    # then there's no need to process it again, so let's move on
    def place_order(
        self, symbol, price, level
    ):  # To place the order and update the data on the backend
        if -level in self.equities[symbol]["levels"]:
            print(
                f"Skipping order for {symbol} level {level}: Already placed (or marked as traded)."
            )
            return

        # Ensure price is valid before submitting
        if price <= 0:
            messagebox.showerror(
                "Order Error",
                f"Cannot place an order for {symbol} at invalid price: {price}",
            )
            return

        # if not then we are submitting the order
        try:
            api.submit_order(
                symbol=symbol,
                qty=1,
                side="buy",
                type="limit",
                time_in_force="gtc",
                limit_price=price,
            )
            self.equities[symbol]["levels"][-level] = (
                price  # to indicate we got an active position
            )

            # We are deleting the original positive level now:
            del self.equities[symbol]["levels"][level]
            print(f"Placed an Order for {symbol}@{price} for original level {level}")
        except Exception as e:
            messagebox.showerror("Order Error", f"Error Placing Order {e}")
            print(f"Failed to place order for {symbol}@{price}, error: {e}")

    def refresh_table(self):  # Self to access the table
        for row in self.tree.get_children():
            self.tree.delete(row)

        for symbol, data in self.equities.items():  # To know if we actively trading
            self.tree.insert(
                "",
                "end",
                values=(
                    symbol,
                    data["position"],
                    data["entry_price"],
                    str(data["levels"]),
                    data["status"],
                ),
            )

    def auto_update(self):
        while self.system_running:
            time.sleep(5)
            self.trade_system()

    def save_equities(self):
        with open(DATA_FILE, "w") as f:  # To save data you have to add write.
            json.dump(self.equities, f)

    def load_equities(self):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)

        except (
            FileNotFoundError,
            json.JSONDecodeError,
        ):  # This should never happen unless you corrupt the Json file, and it can not read in the dictionary
            return {}  # return empty dictionary

    def on_close(self):
        self.system_running = False
        self.save_equities()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()  # initialization of the window called root
    app = TradingBotGUI(root)
    root.protocol(
        "WM_DELETE_WINDOW", app.on_close
    )  # When it is time to close as you can see it is connected to the on_close function

    root.mainloop()
