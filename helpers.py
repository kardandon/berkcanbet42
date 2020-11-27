import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session, g, current_app
from functools import wraps
from database import *
import sqlite3
import re

def is_comment_inapporiate(comment):
    Apikey="9b1950a0e8msh338391d6e915e55p1f1938jsn15ee80023608"
    Url = "https://neutrinoapi-bad-word-filter.p.rapidapi.com/bad-word-filter"
  
    payload = "censor-character=*&content="+comment
    headers = {
        'x-rapidapi-host': "neutrinoapi-bad-word-filter.p.rapidapi.com",
        'x-rapidapi-key':Apikey ,
        'content-type': "application/x-www-form-urlencoded"
        }
    response = requests.request("POST", Url, data=payload, headers=headers)
    if response.json().get('is-bad'):
        return True #bad word
    return False      

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("error.html", message=str(code)+ " " + escape(message)), code
