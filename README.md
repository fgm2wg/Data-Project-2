# Data Project 2

## How to Use
* The website should be up and running on the IP address: 35.193.202.40 (on port 5000)
* This will take you to the homepage (http://35.193.202.40:5000/), to access the chat go to `http://35.193.202.40:5000/chat` or click the 'Start Chatting' button on the homepage
* To chat with the bot, simply type in your message and hit Enter or click the 'Send' button. Then, the bot will return a response to your message.
* The bot is only capable of outputting high and low temperature for the requested date. Additionally, the data for past dates only goes back until 01/01/2022 in the historical weather data csv, so requests beyond that date cannot be fetched. For future dates, data is only available up to 16 days ahead from the OpenMeteo Forecast API, so requests beyond that range cannot be fetched.
* The static csv is generated from data from OpenMeteo Historical Weather API. If the date requested is not in this file, then it try to call the OpenMeteo Forecast API to attempt getting forecast for future date.
* Some examples of messages that the bot will accept include: 'today', 'yesterday', 'tomorrow', 'next <day>', 'last <day>', 'this <day>', 'was <day>', 'MM/DD/YYYY', or 'YYYY-MM-DD'.
* Here is a non-comprehensive list of some realistic messages that it would accept:
  * “What’s the weather today?”
  * “How cold was it yesterday?”
  * “Show me the forecast for tomorrow.”
  * “What will the weather be next Thursday?”
  * “I need the highs and lows for last Monday.”
  * “What was the temperature on 2023-09-15?”
  * “Give me the forecast for 12/25/2025.”
  * “What will the weather be this Sunday?”
  * “What was the weather on 05/05/2025?”
* Chat history is held, so when you come back to the site it will have all of your previous session's chat messages. You can click the 'Clear Chat' button that routes to http://35.193.202.40:5000/clear and returns to a new, empty chat with no messages.
* There is also support for JSON-type POST requests to the API which will return a JSON repsonse of the bot's message. Here is an example Python script to retrieve data from the chat API:
```python
import requests

question = "What is the weather today?"

API_URL = "http://35.193.202.40:5000/chat"

response = requests.post(API_URL, json={"message": question})

if response.status_code == 200:
    data = response.json()
    print("Bot:", data.get("response"))
else:
    print("Error:", response.status_code, response.text)
```
* This will return a repsonse such as: 'Bot: On 2025-05-07, the forecast max will be 81.4°F and min will be 55.4°F.'

## Other Notes
* To install all required dependencies, simply create a new venv and run `pip install -r requirements.txt`.
* You will also need to setup a .env file and add a `SECRET_KEY` variable with a strong secret key for the app to work
* To run the app, simply execute `python app.py`.
* Additionally, you can individually execute `python etl.py` which will generate the historical weather data csv up to today's date from the OpenMeteo Historical Weather API source. However, app.py already handles creating this csv file and calling ETL functions from etl.py to update the csv if its out of date.
* The 2-page reflection paper is also included within this repository named `reflection.pdf`
