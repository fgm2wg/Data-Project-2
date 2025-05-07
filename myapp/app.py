# Import required libraries
import requests
import re
import os
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
import pandas as pd
from etl import extract, transform, load
from dotenv import load_dotenv

# Initialize Flask and set secret key for session management (secret key hidden in .env file)
app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')

# Define start date for historical data (from 01/01/2022 onwards)
START_DATE = date.fromisoformat('2022-01-01')
# Define coordinates for weather for Charlottesville, VA
LAT, LON = 38.0302, -78.4769
# Define path to output historical weather data csv
OUTPUT_CSV = 'data/historical_weather.csv'

# If historical weather data csv missing, then call ETL functions from etl.py to make it
if not os.path.isfile(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0:
    # end_date = date.today().isoformat()
    end_date = date.today()
    end_date = end_date.isoformat()
    raw = extract(LAT, LON, START_DATE.isoformat(), end_date)
    df_boot = transform(raw)
    load(df_boot, OUTPUT_CSV)
    
# Load the historical weather CSV into a pandas df and pare date column
df_hist = pd.read_csv(OUTPUT_CSV, parse_dates=['date'])

# Map weekday names to dateutil codes for relativedelta
WEEKDAYS = { 'monday': MO, 'tuesday': TU, 'wednesday': WE, 'thursday': TH, 'friday': FR, 'saturday': SA, 'sunday': SU }

# Function to update historical weather data csv only if out of date
def update_csv(current_date):
    global df_hist
    # Find latest date in the historical weather csv
    last = df_hist['date'].max().date()

    # If latest date is up to date, then do nothing
    if last >= current_date:
        return

    # Otherwise, need to fill in values for just the missing data
    new_start = (last + timedelta(days=1)).isoformat()
    new_end = date.today().isoformat()

    # Perform ETL functions from etl.py to fill in missing data
    raw = extract(LAT, LON, new_start, new_end)
    df_new = transform(raw)
    
    # Append missing data to csv
    with open(OUTPUT_CSV, 'a') as f:
        df_new.to_csv(f, header=False, index=False)

    # Update df with new values
    df_hist = pd.concat([df_hist, df_new], ignore_index=True)
    # Ensure date column is datetime and properly sorted
    df_hist['date'] = pd.to_datetime(df_hist['date'])
    df_hist.sort_values('date', inplace=True)

# Function to handle past dates (like 'last [day]')
def handle_past_date(msg_clean):
    # Calculate today's date
    today = date.today()

    # If message contains 'yesterday', then return yesterday's date via subtracting timedelta
    if 'yesterday' in msg_clean:
        return today - timedelta(days=1)

    # If message contains 'last [day]', then calculate when last [day] was
    for name, rd in WEEKDAYS.items():
        if f'last {name}' in msg_clean:
            dt = today + relativedelta(weekday=rd(-1))
            # If [day] same day as today, make sure to get last week's [day]
            if dt == today:
                dt -= timedelta(weeks=1)
            return dt

    # If message contains 'was' and [day], then look for past [day]
    if re.search(r'\bwas\b', msg_clean):
        m = re.search(r'\b(' + '|'.join(WEEKDAYS.keys()) + r')\b', msg_clean)
        if m:
            rd = WEEKDAYS[m.group(1)]
            dt = today + relativedelta(weekday=rd(-1))
            if dt == today:
                dt -= timedelta(weeks=1)
            return dt

    # If no date found, then return None
    return None

# Function to handle future dates (like 'next [day]')
def handle_future_date(msg_clean):
    # Calculate today's date
    today = date.today()
    # If message contains today, return today's date
    if 'today' in msg_clean:
        return today
    # If message contains tomorrow, return tomorrow's date via adding timedelta
    if 'tomorrow' in msg_clean:
        return today + timedelta(days=1)

    # If message contains 'next [day]', then calculate when next [day] is next week
    m1 = re.search(r'next (' + '|'.join(WEEKDAYS.keys()) + r')\b', msg_clean)
    if m1:
        rd = WEEKDAYS[m1.group(1)]
        this_week = today + relativedelta(weekday=rd(+1))
        return this_week + timedelta(weeks=1)

    # If message only contains '[day]', then calculate when [day] is this week
    m2 = re.search(r'\b(' + '|'.join(WEEKDAYS.keys()) + r')\b', msg_clean)
    if m2:
        rd = WEEKDAYS[m2.group(1)]
        return today + relativedelta(weekday=rd(+1))

    # If no date found, then return None
    return None

# Function to parse American & ISO date formats (MM/DD/YYYY or YYYY-MM-DD)
def parse_date(msg_clean):
    # Search for American date format (MM/DD/YYYY) and calculate date via US datetime
    m_us = re.search(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', msg_clean)
    if m_us:
        try:
            return datetime.strptime(m_us.group(1), '%m/%d/%Y').date()
        except:
            pass

    # Search for ISO date format (YYYY-MM-DD) and calculate date via ISO datetime
    m_iso = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', msg_clean)
    if m_iso:
        try:
            return date.fromisoformat(m_iso.group(1))
        except:
            pass
        
    # If no date found, then return None
    return None

# Function to generate the bot's response to a user's message
def generate_response(msg):
    # Clean the message (lowercase & remove whitespace)
    msg_clean = msg.lower().strip()
    # Calculate today's date
    today = date.today()
    update_csv(today)

    # Attempt to calculate past date
    past_date = handle_past_date(msg_clean)
    # If past date was found, then handle response
    if past_date:
        # If past date before 01/01/2022, then error with valid date range
        if past_date < START_DATE:
            return f"Sorry, I only have historical data from {START_DATE} onward."
        # Otherwise, index historical data csv with date to get weather data
        row = df_hist[df_hist['date'] == pd.to_datetime(past_date)]
        # If valid weather data for that date, then output results
        if not row.empty:
            r = row.iloc[0]
            return f"On {past_date}, max was {r.temp_max}°F and min was {r.temp_min}°F."
        # Otherwise, error with no data for that date
        return f"Sorry, I have no data for {past_date}."

    # Attempt to calculate past date
    future_date = handle_future_date(msg_clean)
    # If future date wasn't found, then try to look for different date format
    if future_date is None:
        # Attempt to calculate date from US/ISO date format
        formatted_date = parse_date(msg_clean)
        # If formatted date was found, then handle response
        if formatted_date:
            # If formatted date later than today's date, then future date that needs to be forecasted
            if formatted_date > today:
                future_date = formatted_date
            # Otherwise, past date that needs to found from historical weather csv
            else:
                # If past date before 01/01/2022, then error with valid date range
                if formatted_date < START_DATE:
                    return f"Sorry, I only have historical data from {START_DATE} onward."
                # Otherwise, index historical data csv with date to get weather data
                row = df_hist[df_hist['date'] == pd.to_datetime(formatted_date)]
                # If valid weather data for that date, then output results
                if not row.empty:
                    r = row.iloc[0]
                    return (f"On {formatted_date}, max was {r.temp_max}°F and min was {r.temp_min}°F.")
                # Otherwise, error with no data for that date
                return f"Sorry, I have no data for {formatted_date}."

    # If future date was found, then handle response
    if future_date:
        # Calculate difference with today's date
        delta = (future_date - today).days
        # If more than 15 days in the future, out of range for forecast API, so error
        if delta > 15:
            return "Sorry, I can only forecast up to the next 16 days."
        # Setup forecast URL for API with necessary params
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,temperature_2m_min&forecast_days=16&timezone=UTC&temperature_unit=fahrenheit"
        # Make API call and get json data for each day
        resp = requests.get(url); resp.raise_for_status()
        daily = resp.json()['daily']
        # Convert date into ISO date format
        iso_str = future_date.isoformat()
        # If formatted date in the json data, then handle response
        if iso_str in daily['time']:
            idx = daily['time'].index(iso_str)
            return f"On {future_date}, the forecast max will be {daily['temperature_2m_max'][idx]}°F and min will be {daily['temperature_2m_min'][idx]}°F."
        # Otherwise, error with no weather data
        return f"Sorry, I have no forecast data for {future_date}."

    # If all previous date handling fails, then error with valid formats for message
    return "I couldn't parse your date. Try something like: 'yesterday', 'last Monday', 'today', 'tomorrow', 'Thursday', 'next Thursday', 'MM/DD/YYYY', or 'YYYY-MM-DD' (Historical range: {START_DATE} to today; Forecast: next 16 days)"

# Define home page route (http://35.232.83.76:5000/)
@app.route('/')
def home():
    return render_template('home.html')

# Define chat page route (http://35.232.83.76:5000/chat), handles JSON API and form posts
@app.route('/chat', methods=['GET','POST'])
def chat():
    # Initialize or retrieve chat history for session
    history = session.setdefault('history', [])

    # If getting via JSON-based API request
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        # Validate the JSON response
        if not data or 'message' not in data:
            return jsonify({'error': 'Send JSON {"message":"..."}'}), 400
        # Return bot response as JSON
        return jsonify({'response': generate_response(data['message'])})

    # If getting via form submission on actual webpage
    if request.method == 'POST':
        user_msg = request.form['message']
        bot_msg  = generate_response(user_msg)
        # Append to session history for data persistence
        history.append({'user': user_msg, 'bot': bot_msg})
        session.modified = True

    # Return chat interface via html template
    return render_template('chat.html', history=history)

# Define clear page route (http://35.232.83.76:5000/clear) to clear all chat history
@app.route('/clear', methods=['GET'])
def clear():
    session.pop('history', None)
    return redirect(url_for('chat'))

# Run the flask app on http://35.232.83.76:5000/
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
