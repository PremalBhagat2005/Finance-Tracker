import os
import re
import json
import datetime
import pandas as pd
from google import genai
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

from config.constants import TRANSACTION_TYPES, CATEGORIES
from services.auth import get_current_user
from services.mongo_store import (
	get_expenses_dataframe,
	find_pending_match,
	insert_expense,
	insert_pending,
	insert_income,
	update_pending_status
)
from utils.logging_utils import logger

_gemini_client = None

def get_gemini_client():
	global _gemini_client
	if _gemini_client is None:
		_gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
	return _gemini_client


def get_transactions_data(user_id: str):
	df = get_expenses_dataframe(user_id)
	if df.empty:
		return pd.DataFrame(columns=['Date', 'Amount', 'Type', 'Category', 'Subcategory', 'Description'])
	return df


def parse_date_from_text(text: str) -> datetime.datetime:
	text = text.lower().strip()
	now = datetime.datetime.now()

	if 'today' in text:
		return now
	if 'yesterday' in text:
		return now - relativedelta(days=1)
	if 'tomorrow' in text:
		return now + relativedelta(days=1)

	match = re.search(r'last (\d+) days?', text)
	if match:
		return now - relativedelta(days=int(match.group(1)))
	match = re.search(r'last (\d+) weeks?', text)
	if match:
		return now - relativedelta(weeks=int(match.group(1)))
	match = re.search(r'last (\d+) months?', text)
	if match:
		return now - relativedelta(months=int(match.group(1)))

	try:
		return datetime.datetime.strptime(text, '%d/%m/%Y')
	except ValueError:
		try:
			return dateutil_parser.parse(text, fuzzy=True)
		except Exception:
			return now


def infer_category_from_keywords(display_type: str, text: str, description: str):
	search_text = f"{text} {description}".lower()
	if display_type == "Expense":
		if any(word in search_text for word in ["hospital", "doctor", "medical", "pharmacy"]):
			return "Healthcare", "Medical"
		if any(word in search_text for word in ["recharge", "mobile", "prepaid", "postpaid", "dth", "broadband", "internet", "electricity", "water", "gas", "lpg"]):
			return "Recharge & Bills", "Mobile Recharge"
		if any(word in search_text for word in ["gaming", "game", "movie", "ticket", "event"]):
			return "Entertainment", "Movies"
		if any(word in search_text for word in ["food", "grocery", "dining", "restaurant", "snack", "cafe"]):
			if "grocery" in search_text: return "Food", "Groceries"
			if any(word in search_text for word in ["dining", "restaurant"]): return "Food", "Dining Out"
			return "Food", "Snacks"
		if any(word in search_text for word in ["transport", "fuel", "petrol", "bus", "train", "taxi", "uber", "ola"]):
			return "Transportation", "Fuel" if "fuel" in search_text or "petrol" in search_text else "Public Transit"
		if any(word in search_text for word in ["rent", "utility", "electric"]):
			return "Housing", "Rent" if "rent" in search_text else "Utilities"
		if any(word in search_text for word in ["shop", "clothes", "electronic"]):
			return "Shopping", "Clothes"
	
	if display_type == "Income":
		if any(word in search_text for word in ["salary", "payroll", "job", "wage"]): return "Salary", "Regular"
		if any(word in search_text for word in ["dividend", "interest", "investment"]): return "Investment", "Interest"
		return "Other", "Miscellaneous"

	if display_type == "To Receive":
		if any(word in search_text for word in ["salary", "job", "wage"]): return "Pending Income", "Salary"
		return "Pending Income", "Other"

	if display_type == "To Pay":
		if any(word in search_text for word in ["rent", "utility", "electric", "bill"]): return "Bills", "Utilities"
		return "Bills", "Other"
	
	return None, None


def handle_received_pending_transaction(amount: float, description: str) -> dict:
	try:
		user = get_current_user()
		if not user:
			return {"auto_processed": False, "error": "Please log in to save transactions."}
		pending_doc = find_pending_match(user["user_id"], amount, "To Receive")
		if not pending_doc:
			return {"auto_processed": False, "error": f"No matching pending 'To Receive' transaction found for amount {amount}"}
		update_pending_status(pending_doc["_id"], "Received")
		insert_income(user["user_id"], {
			"date": datetime.datetime.utcnow(),
			"amount": amount,
			"type": "Income",
			"category": "Other",
			"subcategory": "Pending Received",
			"description": description,
		})
		return {"auto_processed": True, "type": "Income", "amount": amount, "description": description, "category": "Other", "subcategory": "Pending Received", "date": datetime.datetime.now(), "due_date": None}
	except Exception as e:
		return {"auto_processed": False, "error": str(e)}


def handle_paid_pending_transaction(amount: float, description: str) -> dict:
	try:
		user = get_current_user()
		if not user:
			return {"auto_processed": False, "error": "Please log in to save transactions."}
		pending_doc = find_pending_match(user["user_id"], amount, "To Pay")
		if not pending_doc:
			return {"auto_processed": False, "error": f"No matching pending 'To Pay' transaction found for amount {amount}"}
		update_pending_status(pending_doc["_id"], "Paid")
		insert_expense(user["user_id"], {
			"date": datetime.datetime.utcnow(),
			"amount": amount,
			"type": "Expense",
			"category": "Other",
			"subcategory": "Pending Paid",
			"description": description,
		})
		return {"auto_processed": True, "type": "Expense", "amount": amount, "description": description, "category": "Other", "subcategory": "Pending Paid", "date": datetime.datetime.now(), "due_date": None}
	except Exception as e:
		return {"auto_processed": False, "error": str(e)}


def process_user_input(text: str) -> dict:
	client = get_gemini_client()
	
	# Extract numbers as fallback
	numbers = re.findall(r'\b\d{1,8}(?:\.\d{1,2})?\b', text)
	fallback_amount = max(float(n) for n in numbers) if numbers else 0.0

	prompt = f"""Extract and classify ALL details from this financial transaction in a SINGLE step.

Transaction: "{text}"
Today's date: {datetime.datetime.now().strftime('%Y-%m-%d')}

You MUST respond in EXACTLY this format, 7 lines only:
TYPE: EXPENSE_NORMAL
AMOUNT: 400
DESCRIPTION: food expense
CATEGORY: Food
SUBCATEGORY: Groceries
DATE: 2026-04-25
DUE_DATE: null

Rules:
1. Choose TYPE from: EXPENSE_NORMAL, INCOME_NORMAL, PENDING_TO_RECEIVE, PENDING_TO_PAY, PENDING_RECEIVED, PENDING_PAID
2. AMOUNT: extract ONLY the number. No currency symbols.
3. If no CATEGORY applies, write "Other".
4. If no SUBCATEGORY applies, write "Miscellaneous".
5. DUE_DATE is for pending transactions. If not pending, write "null".
"""
	try:
		response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
		response_text = (getattr(response, "text", "") or "").strip()
		logger.info(f"Gemini single-pass response: {response_text}")

		# Parse response
		trans_type = "EXPENSE_NORMAL"
		amount = 0.0
		description = text
		category = "Other"
		subcategory = "Miscellaneous"
		date_str = datetime.datetime.now().strftime('%Y-%m-%d')
		due_date_str = None

		for line in response_text.split('\n'):
			line = line.strip()
			if line.upper().startswith('TYPE:'): trans_type = line.split(':', 1)[1].strip().upper()
			elif line.upper().startswith('AMOUNT:'): 
				try: amount = float(line.split(':', 1)[1].strip().replace(',', ''))
				except: pass
			elif line.upper().startswith('DESCRIPTION:'): description = line.split(':', 1)[1].strip()
			elif line.upper().startswith('CATEGORY:'): category = line.split(':', 1)[1].strip()
			elif line.upper().startswith('SUBCATEGORY:'): subcategory = line.split(':', 1)[1].strip()
			elif line.upper().startswith('DATE:'): date_str = line.split(':', 1)[1].strip()
			elif line.upper().startswith('DUE_DATE:'): 
				due = line.split(':', 1)[1].strip()
				due_date_str = None if due.lower() == 'null' else due

		if amount <= 0: amount = fallback_amount
		
	except Exception as e:
		logger.error(f"Gemini error: {e}")
		trans_type = "EXPENSE_NORMAL"
		amount = fallback_amount
		description = text
		category = "Other"
		subcategory = "Miscellaneous"
		date_str = datetime.datetime.now().strftime('%Y-%m-%d')
		due_date_str = None

	# Keyword cue overrides for Type
	text_lower = text.lower()
	income_cues = ["received", "salary", "earned", "income", "refund", "dividend", "interest", "bonus", "freelance"]
	expense_cues = ["spent", "bought", "paid for", "purchase", "expense", "bill", "rent", "grocery"]
	future_cues = ["tomorrow", "next ", "will ", "upcoming", "due"]
	pending_rx_cues = ["will receive", "to receive", "expected", "owe me", "coming"]
	pending_px_cues = ["will pay", "to pay", "need to pay", "have to pay", "dues"]

	is_future = any(cue in text_lower for cue in future_cues)
	is_inc = any(cue in text_lower for cue in income_cues)
	is_exp = any(cue in text_lower for cue in expense_cues)

	if trans_type not in ["PENDING_RECEIVED", "PENDING_PAID"]:
		if is_future and (any(cue in text_lower for cue in pending_rx_cues) or (is_inc and not is_exp)):
			trans_type = "PENDING_TO_RECEIVE"
		elif is_future and (any(cue in text_lower for cue in pending_px_cues) or (is_exp and not is_inc)):
			trans_type = "PENDING_TO_PAY"
		elif is_inc and not is_exp:
			trans_type = "INCOME_NORMAL"

	# Handle fully auto-processed pending transitions
	if trans_type == "PENDING_RECEIVED": return handle_received_pending_transaction(amount, description)
	if trans_type == "PENDING_PAID": return handle_paid_pending_transaction(amount, description)

	type_map = {
		"EXPENSE_NORMAL": "Expense",
		"INCOME_NORMAL": "Income",
		"PENDING_TO_RECEIVE": "To Receive",
		"PENDING_TO_PAY": "To Pay"
	}
	display_type = type_map.get(trans_type, "Expense")

	# Validate / Infer Categories
	valid_cats = list(CATEGORIES.get(display_type, {}).keys())
	default_cat = valid_cats[0] if valid_cats else "Other"
	default_sub = (CATEGORIES.get(display_type, {}).get(default_cat, ["Other"]))[0] if valid_cats else "Miscellaneous"

	if category not in valid_cats:
		inf_c, inf_s = infer_category_from_keywords(display_type, text, description)
		if inf_c and inf_s:
			category, subcategory = inf_c, inf_s
		else:
			category, subcategory = default_cat, default_sub
	else:
		valid_subs = CATEGORIES.get(display_type, {}).get(category, [default_sub])
		if subcategory not in valid_subs:
			subcategory = valid_subs[0]

	# Parse dates securely
	try: date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
	except: date_obj = parse_date_from_text(text)
	
	if any(kw in text_lower for kw in ["today", "yesterday", "tomorrow", "last ", "next "]):
		date_obj = parse_date_from_text(text)

	due_date_obj = None
	if due_date_str:
		try: due_date_obj = datetime.datetime.strptime(due_date_str, '%Y-%m-%d')
		except: pass

	return {
		"auto_processed": False,
		"type": display_type,
		"amount": amount,
		"description": description,
		"category": category,
		"subcategory": subcategory,
		"date": date_obj,
		"due_date": due_date_obj
	}


def add_transaction(transaction: dict) -> bool:
	try:
		user = get_current_user()
		if not user:
			raise RuntimeError("Please log in to save transactions.")

		date_val = transaction.get("date", datetime.datetime.now())
		if isinstance(date_val, datetime.datetime): date_str = date_val.strftime("%Y-%m-%d")
		elif isinstance(date_val, datetime.date): date_str = date_val.strftime("%Y-%m-%d")
		else: date_str = str(date_val)

		trans_type = transaction.get("type", "Expense")
		amount = transaction.get("amount", 0.0)
		category = transaction.get("category", "Other")
		subcategory = transaction.get("subcategory", "Miscellaneous")
		description = transaction.get("description", "")
		
		due_date_val = transaction.get("due_date", None)
		if due_date_val and isinstance(due_date_val, (datetime.datetime, datetime.date)):
			due_date_str = due_date_val.strftime("%Y-%m-%d")
		elif due_date_val: due_date_str = str(due_date_val)
		else: due_date_str = ""

		if trans_type in ["To Pay", "To Receive"]:
			insert_pending(user["user_id"], {
				"date": datetime.datetime.strptime(date_str, "%Y-%m-%d"),
				"amount": amount,
				"type": trans_type,
				"category": category,
				"description": description,
				"due_date": datetime.datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None,
				"status": "Pending",
			})
		else:
			if trans_type == "Income":
				insert_income(user["user_id"], {
					"date": datetime.datetime.strptime(date_str, "%Y-%m-%d"),
					"amount": amount,
					"type": trans_type,
					"category": category,
					"subcategory": subcategory,
					"description": description,
				})
			else:
				insert_expense(user["user_id"], {
					"date": datetime.datetime.strptime(date_str, "%Y-%m-%d"),
					"amount": amount,
					"type": trans_type,
					"category": category,
					"subcategory": subcategory,
					"description": description,
				})
		return True
	except Exception as e:
		logger.error(str(e))
		return False
