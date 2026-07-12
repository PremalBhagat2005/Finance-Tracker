import os
from dotenv import load_dotenv
load_dotenv()
from services.chat import process_user_input
import json

res = process_user_input("Got salary 50000 today")
print(json.dumps(res, indent=2, default=str))
