# Import required libraries
import requests
import pandas as pd
from datetime import date

# Define start date for historical data (from 01/01/2022 onwards)
START_DATE = '2022-01-01'
# Define coordinates for weather for Charlottesville, VA
LAT, LON = 38.0302, -78.4769
# Define path to output historical weather data csv
OUTPUT_CSV = 'data/historical_weather.csv'

# Function to extract data from OpenMeteo's Historical Weather Data source
def extract(lat, lon, start, end):
    # Setup historical weather URL for API with necessary params
    url = f"https://archive-api.open-meteo.com/v1/era5?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&daily=temperature_2m_max,temperature_2m_min&timezone=UTC&temperature_unit=fahrenheit"
    # Make API call and get json data for each day as pandas dataframe
    resp = requests.get(url)
    resp.raise_for_status()
    return pd.DataFrame(resp.json()['daily'])

# Function to transform data by formatting dates into datetimes and renaming columns
def transform(df):
    # Convert time column to pandas datetime
    df['date'] = pd.to_datetime(df['time'])
    # Select only date, max temp, and min temp columns
    df = df[['date', 'temperature_2m_max', 'temperature_2m_min']]
    # Rename columns to more understandable labels
    df.rename(columns={'temperature_2m_max': 'temp_max', 'temperature_2m_min': 'temp_min'}, inplace=True)
    # Return transformed pandas df
    return df

# Function to load cleaned data to output path
def load(df, path):
    df.to_csv(path, index=False)
    print(f"Saved historical data to {path}")

# Main function to run ETL
def main():
    # Set end date to today's date (because only weather data up to today)
    end_date = date.today().isoformat()
    
    # Extract raw data from historical weather source
    df_raw = extract(LAT, LON, START_DATE, end_date)
    # Transform the raw data into clean, usable data
    df = transform(df_raw)
    # Load the transformed data into local csv
    load(df, OUTPUT_CSV)

# Run the main function
if __name__ == '__main__':
    main()
