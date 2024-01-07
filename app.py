import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute(
        "SELECT symbol AS name, SUM(shares) AS shares FROM users JOIN purchases ON users.id = purchases.user_id WHERE owned=true AND users.id = ? GROUP BY symbol",
        session["user_id"],
    )
    print(stocks)  # Add this line to check the contents of 'stocks'
    for i in range(len(stocks)):
        # stocks[stock]["name"]
        # stocks[stock]["shares"]
        stock = stocks[i]
        tmp = stock["shares"]
        print(stock)
        stocks[i] = lookup(stock["name"])
        stocks[i]["shares"] = tmp
        print(stocks[i])

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    print(stocks)  # Add this line to check the contents of 'stocks'
    return render_template("index.html", cash=usd(cash[0]["cash"]), stocks=stocks)

    # return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        shares = int(shares)

        quoted = dict()
        quoted = lookup(symbol)

        if quoted is None:
            return apology("Error in finding your stock ticker")
        elif shares < 1:
            return apology("Share count was less than 1")
        else:
            # quoted["price"] = usd(quoted["price"])
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            cash = cash[0]
            quoted_price = float(quoted["price"])
            purchase_price = float(quoted_price) * shares
            if cash["cash"] < purchase_price:
                return apology("Not enough money to purchase these shares")
            else:
                db.execute(
                    "INSERT INTO purchases (user_id, symbol, price, shares, current_cash, owned, bought) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    session["user_id"],
                    quoted["name"],
                    purchase_price,
                    shares,
                    cash["cash"],
                    1,
                    1,
                )
                db.execute(
                    "UPDATE users SET cash = cash - ? WHERE id = ?",
                    purchase_price,
                    session["user_id"],
                )
                return render_template(
                    "bought.html",
                    quoted=quoted,
                    purchase_price=usd(purchase_price),
                    current_cash=usd(cash["cash"] - purchase_price),
                )

    else:
        return render_template("buy.html")

    # return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    data = db.execute(
        "SELECT timestamp, current_cash, bought, sold, username, symbol, shares, owned, price FROM users JOIN purchases ON users.id = purchases.user_id WHERE users.id = ?",
        session["user_id"],
    )
    return render_template("history.html", rows=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quoted = dict()
        quoted = lookup(symbol)
        if quoted is None:
            return apology("Error in finding your stock ticker")
        quoted["price"] = usd(quoted["price"])
        return render_template("quoted.html", quoted=quoted)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return apology("Username cannot be empty")
        password = str(request.form.get("password"))
        confpassword = request.form.get("confirmation")
        if db.execute("SELECT username FROM users WHERE username=?", username):
            return apology("Username Already Exists")
        else:
            if str(password) != str(confpassword):
                return apology("Passwords do not match")
            else:
                passhash = generate_password_hash(password, salt_length=16)
                db.execute(
                    "INSERT INTO users (username, hash) VALUES (?, ?)",
                    username,
                    passhash,
                )
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stocks = db.execute(
        "SELECT purchases.id, symbol AS name, SUM(shares) AS shares FROM users JOIN purchases ON users.id = purchases.user_id WHERE owned=true AND users.id = ? GROUP BY symbol",
        session["user_id"],
    )
    for i in range(len(stocks)):
        stock = stocks[i]
        tmp = stock["shares"]
        tmp1 = stock["id"]
        print(stock)
        stocks[i] = lookup(stock["name"])
        stocks[i]["shares"] = tmp
        stocks[i]["id"] = tmp1
        print(stocks[i])
    if request.method == "GET":
        return render_template("sell.html", stocks=stocks)
    elif request.method == "POST":
        stock_to_sell = request.form.get("symbol")
        shares_to_sell = request.form.get("shares")
        shares_to_sell = int(shares_to_sell)
        # print(shares_to_sell)

        stock_sold = False
        for i in range(len(stocks)):
            stock = stocks[i]
            if stock_sold is True:
                break
            elif stock_to_sell == stocks[i]["name"]:
                if shares_to_sell > stocks[i]["shares"]:
                    print("Trying to sell more shares than owned.")
                    return apology("Trying to sell more shares than owned.")
                elif shares_to_sell < 1:
                    print("You must sell at least 1 share")
                    return apology("You must sell at least 1 share")
                else:
                    price = stocks[i]["price"] * shares_to_sell
                    cash = db.execute(
                        "SELECT cash FROM users WHERE id = ?", session["user_id"]
                    )
                    cash = cash[0]
                    if (stocks[i]["shares"] - shares_to_sell) < 1:
                        owned = 0
                    else:
                        owned = 1
                    db.execute("BEGIN TRANSACTION")
                    db.execute(
                        "UPDATE purchases SET owned = ? WHERE user_id = ? AND purchases.id = ?",
                        owned,
                        session["user_id"],
                        stocks[i]["id"],
                    )
                    db.execute(
                        "INSERT INTO purchases (shares, owned, sold, user_id, symbol, price, current_cash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (shares_to_sell * (-1)),
                        owned,
                        1,
                        session["user_id"],
                        stock_to_sell,
                        price,
                        cash["cash"],
                    )
                    db.execute(
                        "UPDATE users SET cash = cash + ? WHERE id = ? ",
                        price,
                        session["user_id"],
                    )
                    db.execute("COMMIT")
                    stock_sold = True
                    break
            else:
                continue
        return redirect("/")
