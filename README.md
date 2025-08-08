Of course\! Based on your code, here is a detailed and well-structured description perfect for a GitHub repository README file.

-----

### AI-Powered Equities Trading Bot with LLM Risk Analysis

This project is a Python-based algorithmic trading bot that uses a **Martingale Dollar-Cost Averaging (DCA)** strategy, managed through a simple **Tkinter GUI**. The bot connects to the **Alpaca API** for paper trading and uniquely integrates a **Large Language Model (LLM)** to act as an AI portfolio manager, providing risk analysis and insights on command. 🤖

-----

### Core Features

  * **Interactive GUI (`Tkinter`):** A user-friendly graphical interface allows you to add, remove, and monitor equities without touching the code. You can define key strategy parameters like the number of buy levels and the drawdown percentage for each equity.

  * **Live Paper Trading (`Alpaca API`):** The bot connects directly to the Alpaca paper trading service to fetch real-time price data, submit market and limit orders, and track your live portfolio positions.

  * **Martingale DCA Strategy:** The core trading logic is an automated DCA strategy. When you add an equity, the bot places an initial market order. It then calculates and places a series of limit buy orders at progressively lower prices based on the drawdown percentage you set. This aims to lower your average entry price as the market dips.

  * **LLM-Powered Portfolio Manager (`Together AI`):** The bot's most powerful feature. You can ask your portfolio questions in plain English. The integrated LLM analyzes your current positions and open orders to provide:

      * Risk exposure evaluation.
      * Insights into portfolio health.
      * Commentary on market conditions and potential risks.

  * **Persistent State (`JSON`):** The bot saves its configuration (the list of equities and their status) to a `equities.json` file, so your setup is preserved even after you close the application.

  * **Multithreaded Operations (`threading`):** The core trading logic runs in a separate background thread, ensuring the GUI remains responsive while the bot continuously monitors the market and manages trades.

-----

### Tech Stack

  * **Language:** Python 3
  * **GUI:** Tkinter
  * **Trading API:** `alpaca-trade-api`
  * **LLM Integration:** `together`
  * **Environment Management:** `python-dotenv`

-----

### How To Use

1.  **Prerequisites:** Make sure you have Python and `pip` installed.

2.  **Clone the Repository:**

    ```bash
    git clone https://your-repo-link.com/
    cd your-repo-folder
    ```

3.  **Install Dependencies:**

    ```bash
    pip install tkinter alpaca-trade-api python-dotenv together
    ```

4.  **Set Up API Keys:**

      * Create a **`.env`** file in the project directory.
      * Sign up for an [Alpaca paper trading account](https://alpaca.markets/) to get your `key` and `secret_key`.
      * Sign up for [Together AI](https://www.together.ai/) to get your `TOGETHER_API_KEY`.
      * Add your keys to the `.env` file and update them in the script:

    <!-- end list -->

    ```env
    # .env file
    TOGETHER_API_KEY="your_together_api_key_here" 
    ```

    *Note: You've hardcoded the Alpaca keys in the script. It's highly recommended to also move them to the `.env` file for better security.*

5.  **Run the Bot:**

    ```bash
    python main.py
    ```
