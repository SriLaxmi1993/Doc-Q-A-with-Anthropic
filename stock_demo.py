import yfinance as yf
from anthropic import Anthropic
from rich import print
import re
import os

# Initialize Anthropic client
# Access API key from environment variable
api_key = os.getenv('ANTHROPIC_API_KEY')
client = Anthropic(api_key=api_key)
MODEL_NAME = "claude-3-opus-20240229"

# create a messgae for anthropic model

stock_message = {
    "role": "user", 
    "content": "Find the current price of General Motors stock"
}

message = client.messages.create(
    model=MODEL_NAME,
    max_tokens=1024,
    messages=[stock_message]
).content[0].text
print("##### Before Function Calling ####\n\n" + message)


# Define the stock price finding function 

def get_stock_price(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    hist = stock.history(period="1d")
    current_price = hist['Close'].iloc[0]
    return current_price

# 2. Construct Tool description

tool_description = """
<tool_description>
    <tool_name>get_stock_price</tool_name>
    <description>
        Function for finding the current price of a stock using its ticker symbol.
    </description>
    <parameters>
        <parameter>
            <name>ticker_symbol</name>
            <type>str</type>
            <description>Ticker symbol of the stock</description>
        </parameter>
    </parameters>
</tool_description>
"""



# 3. Ask Claude with a sytem prompt and a tool. Another message is created and sent to the Anthropic model, this time including the system prompt which describes the available tools.
system_prompt = f"""
In this environment you have access to a set of tools you can use to answer the 
user's question.

You may call them like this:
<function_calls>
    <invoke>
        <tool_name>$TOOL_NAME</tool_name>
        <parameters>
            <$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>
            ...
        </parameters>
    </invoke>
</function_calls>

Here are the tools available:
<tools>{tool_description}</tools>
"""

function_calling_message = client.messages.create(
    model=MODEL_NAME,
    max_tokens=1024,
    messages=[stock_message],
    system=system_prompt
).content[0].text


# 4. Extract parameters from response & call the function ( converting xml format )

def extract_between_tags(tag, string, strip=False):
    ext_list = re.findall(f"<{tag}>(.+?)</{tag}>", string, re.DOTALL)
    return [e.strip() for e in ext_list] if strip else ext_list

function_params = {"ticker_symbol": extract_between_tags("ticker_symbol", function_calling_message)[0]}
function_name = extract_between_tags("tool_name", function_calling_message)[0]
names_to_functions = {
    'get_stock_price': get_stock_price,
}
price = names_to_functions[function_name](**function_params)


# Construct function results and send back to Claude

function_results = f"""
<function_results>
  <result>
    <tool_name>get_stock_price</tool_name>
    <stdout>{price}</stdout>
  </result>
</function_results>"""

partial_assistant_message = function_calling_message + function_results

final_message = client.messages.create(
    model=MODEL_NAME,
    max_tokens=1024,
    messages=[
        stock_message,
        {
            "role": "assistant",
            "content": partial_assistant_message
        }
    ],
    system=system_prompt
).content[0].text
print("\n\n##### After Function Calling #####"+ final_message)