from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from helpers import *
import datetime
# configure application
app = Flask(__name__)

dict1={}

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
   stocks=[]
   id2=session["user_id"]
   if not(id2 in list(dict1.keys())):
      return render_template("index2.html")
   else:      
    m=list(dict1[id2].keys())
    total=0
    for s in m:
        b=lookup(s)
        stocks.append({"stocksym":s,"num":dict1[id2][s],"current":b["price"],"holding":b["price"]*dict1[id2][s]})
        total=total+b["price"]*dict1[id2][s]
    c2=db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    c2=float(c2[0]["cash"])
    total=total+c2;
    return render_template("index.html",stocks=stocks,c2=c2,total=total)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":

        
        # ensure stocksymbol was submitted
        if  request.form.get("stock_symbol")=='':
            return apology("must provide stocksymbol")

        # ensure number of shares was submitted
        n=int(request.form.get("numberofshares"))
        
        if not (request.form.get("numberofshares")):
            return apology("must provide number of shares")
        
       
        if n<=0:
            return apology("must provide positive integer for num of shares")
        b=lookup(request.form.get("stock_symbol"))
        if b==None:
            return apology("ERROR or stock does not exist")
        c1=float(request.form.get("numberofshares"))*float(b["price"])   
        c2=db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        c2=float(c2[0]["cash"])
        if(c2<c1):
            return apology("NOT ENOUGH CASH!")
        u=db.execute("SELECT username FROM users WHERE id=:id",id=session["user_id"])    
        db.execute("UPDATE users SET cash=:c WHERE id=:id",c=c2-c1,id=session["user_id"])
        c1=str(c1)
        trans="-"+c1
        c1=float(c1)
        d=str(datetime.datetime.now())
        db.execute("INSERT INTO history VALUES (:username,:stocksymbol,:transaction,:cash,:dt)",username=str(u[0]["username"]),stocksymbol=b["symbol"],transaction=str(trans),cash=float(c2-c1),dt=d)
        account(int(session["user_id"]),b["symbol"],n)
        return redirect(url_for("index"))  
              
    else:
        return render_template("buy.html")
        
@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    u=db.execute("SELECT username FROM users WHERE id=:id",id=session["user_id"])
    r=db.execute("SELECT * FROM history WHERE username=:u",u=u[0]["username"])
    if(len(r)==0):
     return apology("EMPTY")
    return render_template("history.html",r=r)
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
       
        # ensure username was submitted
        if not request.form.get("stock_symbol"):
            return apology("must provide stock symbol")
        q=lookup(request.form.get("stock_symbol"))
        if q==None:
            return apology("ERROR or stock does not exist")
    
        return render_template("quotedisp.html",name=q["name"],sym=q["symbol"],price=q["price"])
    else:
        return render_template("quote.html")
        
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    # forget any user_id
    session.clear()
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
            
        elif request.form.get("password")!=request.form.get("retype-password"):
            return apology("passwords do not match")
        
        hash1=pwd_context.hash(request.form.get("password"))  
        
        result=db.execute("INSERT INTO users (username,hash) VALUES(:username, :hash)",username=request.form.get("username"),hash=hash1)
       
        if not result:
            return apology("username already exists")
            
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        
        session["user_id"] = rows[0]["id"]
        
        return redirect(url_for("index"))
        
    else:
        return render_template("register.html")
        
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        if not request.form.get("stock_symbol"):
            return apology("must provide stock_symbol")
        id3= session["user_id"]
        if not(id3 in dict1.keys()):
            return apology(" YOU CANT SELL STOCKS THAT YOU DO NOT OWN!-_____-")
        if not(request.form.get("stock_symbol").upper() in dict1[id3].keys()):
            return apology(" YOU CANT SELL STOCKS THAT YOU DO NOT OWN!")
        b=lookup(request.form.get("stock_symbol"))
        if b==None:
            return apology("ERROR or stock does not exist")
        extra=b["price"]*dict1[id3][request.form.get("stock_symbol").upper()]
        c2=db.execute("SELECT * FROM users WHERE id = :id", id=id3)
        c2=float(c2[0]["cash"])
        u=db.execute("SELECT username FROM users WHERE id=:id",id=id3) 
        trans='+'+str(extra)
        d=str(datetime.datetime.now())
        db.execute("INSERT INTO history VALUES (:username,:stocksymbol,:transaction,:cash,:dt)",username=str(u[0]["username"]),stocksymbol=b["symbol"],transaction=str(trans),cash=float(extra+c2),dt=d)
        del(dict1[id3][request.form.get("stock_symbol").upper()])
        db.execute("UPDATE users SET cash=:c WHERE id=:id",c=c2+extra,id=id3)
        return redirect(url_for("index"))  
    else:
        return render_template("sell.html")
@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    """ADD CASH TO YOUR ACCOUNT"""
    if request.method == "POST":
        if not request.form.get("addcash"):
            return apology("must provide the cash value")
        if float(request.form.get("addcash"))<=0:
            return apology("CASH MUST BE GREATER THAN 0")
        c2=db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        c2=float(c2[0]["cash"])
        db.execute("UPDATE users SET cash=:c WHERE id=:id",c=c2+float(request.form.get("addcash")),id=session["user_id"])
        return redirect(url_for("index"))
    else:
        return render_template("addcash.html")
    
def account(id1,sym1,n1):
    """keeps account of the shares owned and its number"""
    if id1 in dict1.keys():
        if sym1 in dict1[id1].keys():
            dict1[id1][sym1]+=n1
        else:
            dict1[id1][sym1]=n1
    else:
        dict1[id1]={sym1:n1}
    