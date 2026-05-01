import streamlit as st
import os
import re
import json
import datetime
import pandas as pd
from google import genai
from dotenv import load_dotenv
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
from config.constants import TRANSACTION_TYPES, CATEGORIES
from services.auth import authenticate_user, get_current_user, is_authenticated, logout_user, register_user, set_current_user
from services.mongo_store import ensure_indexes, find_pending_match, get_expenses_dataframe, get_pending_dataframe, insert_expense, insert_pending, insert_income, update_pending_status
from services.google_sheets import export_user_data
from utils.logging_utils import logger

load_dotenv()


def init_session_state():
	if "messages" not in st.session_state:
		st.session_state.messages = []
	if "current_transaction" not in st.session_state:
		st.session_state.current_transaction = None
	if "form_submitted" not in st.session_state:
		st.session_state.form_submitted = False
	if "save_clicked" not in st.session_state:
		st.session_state.save_clicked = False
	if "global_filter_type" not in st.session_state:
		st.session_state.global_filter_type = 'All Time'
	if "global_selected_year" not in st.session_state:
		st.session_state.global_selected_year = datetime.datetime.now().year
	if "global_selected_month" not in st.session_state:
		st.session_state.global_selected_month = 1
	if "authenticated" not in st.session_state:
		st.session_state.authenticated = False
	if "current_user" not in st.session_state:
		st.session_state.current_user = None


def render_auth_ui() -> bool:
	st.title("Smart Finance Tracker")
	st.subheader("Sign in to continue")
	st.caption("Create one account per person. Each account stores its own expenses in MongoDB.")

	login_tab, register_tab = st.tabs(["Login", "Create account"])
	auth_success = False

	with login_tab:
		with st.form("login_form", clear_on_submit=False):
			email = st.text_input("Email")
			password = st.text_input("Password", type="password")
			submit = st.form_submit_button("Login")
		if submit:
			try:
				user = authenticate_user(email, password)
				if user:
					set_current_user(user)
					st.success(f"Welcome back, {user['name']}.")
					auth_success = True
				else:
					st.error("Invalid email or password.")
			except Exception as e:
				st.error(f"Login failed: {e}")

	with register_tab:
		with st.form("register_form", clear_on_submit=False):
			name = st.text_input("Name")
			email = st.text_input("Email ", key="register_email")
			password = st.text_input("Password ", type="password", key="register_password")
			confirm_password = st.text_input("Confirm password", type="password")
			submit = st.form_submit_button("Create account")
		if submit:
			if password != confirm_password:
				st.error("Passwords do not match.")
			elif not name.strip() or not email.strip() or not password:
				st.error("Please fill in all fields.")
			else:
				try:
					user = register_user(name, email, password)
					set_current_user(user)
					st.success(f"Account created for {user['name']}.")
					auth_success = True
				except Exception as e:
					st.error(f"Registration failed: {e}")

	return auth_success


@st.cache_resource
def get_gemini_client():
	return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


@st.cache_data(ttl=300)
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

	match = re.search(r'next (\d+) days?', text)
	if match:
		return now + relativedelta(days=int(match.group(1)))

	match = re.search(r'next (\d+) weeks?', text)
	if match:
		return now + relativedelta(weeks=int(match.group(1)))

	match = re.search(r'next (\d+) months?', text)
	if match:
		return now + relativedelta(months=int(match.group(1)))

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
		if any(word in search_text for word in ["hospital", "doctor", "medical", "pharmacy", "clinic", "health"]):
			return "Healthcare", "Medical"
		if any(word in search_text for word in ["recharge", "mobile recharge", "prepaid", "postpaid", "dth", "broadband", "internet bill", "electricity bill", "water bill", "gas bill", "lpg", "ott", "landline", "property tax", "municipal tax"]):
			if any(word in search_text for word in ["mobile recharge", "recharge", "prepaid"]):
				return "Recharge & Bills", "Mobile Recharge"
			if "postpaid" in search_text:
				return "Recharge & Bills", "Postpaid Bill"
			if "dth" in search_text:
				return "Recharge & Bills", "DTH Recharge"
			if "broadband" in search_text:
				return "Recharge & Bills", "Broadband Bill"
			if "internet" in search_text:
				return "Recharge & Bills", "Internet Bill"
			if "electricity" in search_text:
				return "Recharge & Bills", "Electricity Bill"
			if "water" in search_text:
				return "Recharge & Bills", "Water Bill"
			if "gas" in search_text or "lpg" in search_text:
				return "Recharge & Bills", "Gas Bill"
			if "ott" in search_text:
				return "Recharge & Bills", "OTT Recharge"
			if "landline" in search_text:
				return "Recharge & Bills", "Landline Bill"
			if "property tax" in search_text:
				return "Recharge & Bills", "Property Tax"
			if "municipal tax" in search_text:
				return "Recharge & Bills", "Municipal Tax"
			return "Recharge & Bills", "Mobile Recharge"
		if any(word in search_text for word in ["gaming", "game", "games", "video game", "playstation", "xbox", "steam", "console", "movie", "movies", "cinema", "ticket", "event", "concert"]):
			return "Entertainment", "Games" if any(word in search_text for word in ["gaming", "game", "games", "video game", "playstation", "xbox", "steam", "console"]) else "Movies" if "movie" in search_text or "movies" in search_text or "cinema" in search_text else "Events"
		if any(word in search_text for word in ["food", "grocery", "groceries", "dining", "restaurant", "snack", "cafe", "lunch", "dinner"]):
			if any(word in search_text for word in ["grocery", "groceries"]):
				return "Food", "Groceries"
			if any(word in search_text for word in ["dining", "restaurant", "cafe", "lunch", "dinner"]):
				return "Food", "Dining Out"
			return "Food", "Snacks"
		if any(word in search_text for word in ["transport", "fuel", "petrol", "bus", "train", "taxi", "cab", "uber", "ola", "metro"]):
			return "Transportation", "Fuel" if any(word in search_text for word in ["fuel", "petrol"]) else "Public Transit"
		if any(word in search_text for word in ["rent", "utility", "electric", "water", "wifi", "internet", "maintenance"]):
			return "Housing", "Rent" if "rent" in search_text else "Utilities"
		if any(word in search_text for word in ["shop", "shopping", "clothes", "clothing", "electronic", "electronics", "gadget", "home item"]):
			return "Shopping", "Clothes" if any(word in search_text for word in ["clothes", "clothing"]) else "Electronics" if any(word in search_text for word in ["electronic", "electronics", "gadget"]) else "Home Items"
		if any(word in search_text for word in ["gift", "birthday", "wedding", "holiday", "present", "anniversary"]):
			return "Gift", "Birthday" if "birthday" in search_text else "Wedding" if "wedding" in search_text else "Holiday"
		return None, None

	if display_type == "Income":
		if any(word in search_text for word in ["salary", "payroll", "job", "paycheck", "pay cheque", "wage", "wages", "stipend"]):
			return "Salary", "Regular"
		if any(word in search_text for word in ["bonus", "overtime", "incentive", "performance bonus"]):
			return "Salary", "Bonus" if "bonus" in search_text else "Overtime"
		if any(word in search_text for word in ["dividend", "interest", "capital gain", "investment", "mutual fund", "stock", "fd"]):
			return "Investment", "Dividends" if "dividend" in search_text else "Interest" if "interest" in search_text else "Capital Gains"
		if any(word in search_text for word in ["refund", "gift", "misc", "other", "aunt", "uncle", "mom", "mother", "dad", "father", "brother", "sister", "friend", "relative", "family", "cashback", "reimbursement", "freelance", "side hustle", "client", "commission", "scholarship"]):
			return "Other", "Refunds" if "refund" in search_text else "Gifts" if "gift" in search_text else "Miscellaneous"
		return None, None

	if display_type == "To Receive":
		if any(word in search_text for word in ["salary", "job", "payroll", "wage", "stipend"]):
			return "Pending Income", "Salary"
		if any(word in search_text for word in ["investment", "interest", "dividend", "fd", "stock"]):
			return "Pending Income", "Investment"
		return "Pending Income", "Other"

	if display_type == "To Pay":
		if any(word in search_text for word in ["rent", "utility", "electric", "water", "wifi", "internet", "bill", "phone bill", "subscription"]):
			return "Bills", "Rent" if "rent" in search_text else "Utilities"
		if any(word in search_text for word in ["credit card", "loan", "debt", "emi", "borrowed", "dues"]):
			return "Debt", "Credit Card" if "credit card" in search_text else "Loan"
		return "Bills", "Other"

	return None, None


def classify_transaction_type(text: str, client) -> dict:
	try:
		prompt = f"""Classify this financial transaction and extract details.

Transaction: "{text}"

You MUST respond in EXACTLY this format, 3 lines only, nothing else:
TYPE: EXPENSE_NORMAL
AMOUNT: 400
DESCRIPTION: food expense

Choose TYPE from: EXPENSE_NORMAL, INCOME_NORMAL, PENDING_TO_RECEIVE, PENDING_TO_PAY, PENDING_RECEIVED, PENDING_PAID

For AMOUNT: extract ONLY the number from the text. No currency symbols. No words. Just digits.

Now classify: "{text}"
TYPE: """

		response = client.models.generate_content(
			model="gemini-2.0-flash",
			contents=prompt
		)
		response_text = (getattr(response, "text", "") or "").strip()
		logger.info(f"Gemini classify response: {response_text}")

		# Parse TYPE
		type_match = re.search(r'(?:TYPE:\s*)?([A-Z_]+NORMAL|PENDING_\w+)', response_text, re.IGNORECASE)
		trans_type = type_match.group(1).upper().strip() if type_match else "EXPENSE_NORMAL"

		# Parse AMOUNT - try multiple patterns
		amount = 0.0
		amount_match = re.search(r'AMOUNT:\s*([\d,]+\.?\d*)', response_text, re.IGNORECASE)
		if amount_match:
			amount = float(amount_match.group(1).replace(',', ''))
		
		# If amount still 0, extract number directly from original user text
		if amount <= 0:
			numbers = re.findall(r'\b\d{1,8}(?:\.\d{1,2})?\b', text)
			if numbers:
				amount = max(float(n) for n in numbers)

		# Parse DESCRIPTION
		desc_match = re.search(r'DESCRIPTION:\s*(.+)', response_text, re.IGNORECASE)
		description = desc_match.group(1).strip() if desc_match else text

		text_lower = text.lower()
		income_cues = [
			"received", "receive", "got salary", "salary", "got paid", "paid me",
			"earned", "income", "refund", "dividend", "interest", "bonus",
			"from job", "job", "paycheck", "pay cheque", "wage", "wages", "credited",
			"deposit", "salary credited", "salary received", "payment received",
			"from aunt", "from uncle", "from mom", "from mother", "from dad", "from father",
			"from brother", "from sister", "from friend", "from family", "gifted", "reimbursement",
			"cashback", "freelance", "commission", "scholarship", "stipend"
		]
		expense_cues = ["spent", "bought", "paid for", "purchase", "expense", "bill", "rent", "grocery", "groceries", "shopping", "hospital", "pharmacy", "fuel", "transport", "movie ticket", "subscription"]
		if trans_type == "EXPENSE_NORMAL" and any(cue in text_lower for cue in income_cues) and not any(cue in text_lower for cue in expense_cues):
			trans_type = "INCOME_NORMAL"

		return {"type": trans_type, "amount": amount, "description": description}

	except Exception as e:
		logger.error(f"classify_transaction_type error: {e}")
		# Even on full failure, still extract number from text
		numbers = re.findall(r'\b\d{1,8}(?:\.\d{1,2})?\b', text)
		amount = max(float(n) for n in numbers) if numbers else 0.0
		return {"type": "EXPENSE_NORMAL", "amount": amount, "description": text}


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
		st.cache_data.clear()
		return {"auto_processed": True, "type": "Income", "amount": amount, "description": description, "category": "Other", "subcategory": "Pending Received", "date": datetime.datetime.now(), "due_date": None}
	except Exception as e:
		logger.error(str(e))
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
		st.cache_data.clear()
		return {"auto_processed": True, "type": "Expense", "amount": amount, "description": description, "category": "Other", "subcategory": "Pending Paid", "date": datetime.datetime.now(), "due_date": None}
	except Exception as e:
		logger.error(str(e))
		return {"auto_processed": False, "error": str(e)}


def process_user_input(text: str) -> dict:
	try:
		client = get_gemini_client()
		classification = classify_transaction_type(text, client)
		trans_type = classification["type"]
		amount = classification["amount"]
		description = classification["description"]
		text_lower = text.lower()
		income_cues = [
			"received", "receive", "got salary", "salary", "got paid", "paid me",
			"earned", "income", "refund", "dividend", "interest", "bonus",
			"from job", "job", "paycheck", "pay cheque", "wage", "wages", "credited",
			"deposit", "salary credited", "salary received", "payment received",
			"from aunt", "from uncle", "from mom", "from mother", "from dad", "from father",
			"from brother", "from sister", "from friend", "from family", "gifted", "reimbursement",
			"cashback", "freelance", "commission", "scholarship", "stipend"
		]
		expense_cues = ["spent", "bought", "paid for", "purchase", "expense", "bill", "rent", "grocery", "groceries", "shopping", "hospital", "pharmacy", "fuel", "transport", "movie ticket", "subscription"]
		future_cues = ["tomorrow", "next ", "will ", "upcoming", "future", "due", "later"]
		pending_receive_cues = ["will receive", "to receive", "expected", "owe me", "owed me", "coming"]
		pending_pay_cues = ["will pay", "to pay", "need to pay", "have to pay", "pay later", "dues"]

		is_future = any(cue in text_lower for cue in future_cues)
		is_income_like = any(cue in text_lower for cue in income_cues)
		is_expense_like = any(cue in text_lower for cue in expense_cues)

		if trans_type not in ["PENDING_RECEIVED", "PENDING_PAID"]:
			if is_future and (any(cue in text_lower for cue in pending_receive_cues) or (is_income_like and not is_expense_like)):
				trans_type = "PENDING_TO_RECEIVE"
			elif is_future and (any(cue in text_lower for cue in pending_pay_cues) or (is_expense_like and not is_income_like)):
				trans_type = "PENDING_TO_PAY"
			elif is_income_like and not is_expense_like:
				trans_type = "INCOME_NORMAL"

		if amount <= 0:
			num_match = re.search(r'[\d,]+\.?\d*', text)
			if num_match:
				amount = float(num_match.group().replace(',', ''))
			else:
				amount = 0.0

		if trans_type == "PENDING_RECEIVED":
			return handle_received_pending_transaction(amount, description)

		if trans_type == "PENDING_PAID":
			return handle_paid_pending_transaction(amount, description)

		type_map = {
			"EXPENSE_NORMAL": "Expense",
			"INCOME_NORMAL": "Income",
			"PENDING_TO_RECEIVE": "To Receive",
			"PENDING_TO_PAY": "To Pay"
		}
		display_type = type_map.get(trans_type, "Expense")

		valid_categories = list(CATEGORIES.get(display_type, {}).keys())
		default_category = valid_categories[0] if valid_categories else "Other"
		default_subcategory = CATEGORIES.get(display_type, {}).get(default_category, ["Other"])[0]

		prompt2 = f"""You are categorizing a financial transaction.

Transaction: "{description}"
Type: "{display_type}"
Original text: "{text}"

Available categories and subcategories:
{json.dumps(CATEGORIES.get(display_type, {}), indent=2)}

Today's date: {datetime.datetime.now().strftime('%Y-%m-%d')}

Respond in this EXACT format, nothing else, no extra text:
CATEGORY: Food
SUBCATEGORY: Groceries
DATE: 2026-04-25
DUE_DATE: null

Pick CATEGORY and SUBCATEGORY only from the lists above."""

		response2_text = ""
		try:
			response2 = client.models.generate_content(
				model="gemini-2.0-flash",
				contents=prompt2
			)
			response2_text = (getattr(response2, "text", "") or "").strip()
			logger.info(f"Gemini categorize response: {response2_text}")
		except Exception as e:
			logger.error(f"Gemini categorize error: {e}")

		# Parse with simple line-by-line approach instead of JSON
		category = default_category
		subcategory = default_subcategory
		date_str = datetime.datetime.now().strftime('%Y-%m-%d')
		due_date_str = None

		for line in response2_text.split('\n'):
			line = line.strip()
			if line.upper().startswith('CATEGORY:'):
				category = line.split(':', 1)[1].strip()
			elif line.upper().startswith('SUBCATEGORY:'):
				subcategory = line.split(':', 1)[1].strip()
			elif line.upper().startswith('DATE:'):
				date_str = line.split(':', 1)[1].strip()
			elif line.upper().startswith('DUE_DATE:'):
				due_date_str = line.split(':', 1)[1].strip()
				if due_date_str.lower() == 'null':
					due_date_str = None

		# Validate category exists
		valid_cats = list(CATEGORIES.get(display_type, {}).keys())
		if category not in valid_cats:
			category = default_category
		
		# Validate subcategory exists
		valid_subs = CATEGORIES.get(display_type, {}).get(category, [default_subcategory])
		if subcategory not in valid_subs:
			subcategory = valid_subs[0]

		# If the model response was empty or unhelpful, fall back to keyword matching.
		if category == default_category and subcategory == default_subcategory:
			search_text = f"{text} {description}".lower()
			for candidate_category, candidate_subs in CATEGORIES.get(display_type, {}).items():
				if candidate_category.lower() in search_text:
					category = candidate_category
					subcategory = candidate_subs[0]
					break
				for candidate_sub in candidate_subs:
					if candidate_sub.lower() in search_text:
						category = candidate_category
						subcategory = candidate_sub
						break

		# Parse dates
		text_date_obj = parse_date_from_text(text)
		try:
			date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
		except:
			date_obj = text_date_obj

		text_lower = text.lower()
		if any(keyword in text_lower for keyword in ["today", "yesterday", "tomorrow", "last ", "next "]):
			date_obj = text_date_obj

		due_date_obj = None
		if due_date_str:
			try:
				due_date_obj = datetime.datetime.strptime(due_date_str, '%Y-%m-%d')
			except:
				due_date_obj = None

		inferred_category, inferred_subcategory = infer_category_from_keywords(display_type, text, description)
		if inferred_category and inferred_subcategory:
			category = inferred_category
			subcategory = inferred_subcategory

		if category == default_category and subcategory == default_subcategory:
			search_text = f"{text} {description}".lower()
			if display_type == "Expense":
				if any(word in search_text for word in ["food", "grocery", "groceries", "dining", "restaurant", "snack"]):
					category = "Food"
					subcategory = "Groceries" if "grocery" in search_text or "groceries" in search_text else "Dining Out" if "dining" in search_text or "restaurant" in search_text else "Snacks"
				elif any(word in search_text for word in ["transport", "fuel", "petrol", "bus", "train", "taxi"]):
					category = "Transportation"
					subcategory = "Fuel" if any(word in search_text for word in ["fuel", "petrol"]) else "Public Transit"
				elif any(word in search_text for word in ["rent", "utility", "electric", "water", "wifi", "internet"]):
					category = "Housing"
					subcategory = "Rent" if "rent" in search_text else "Utilities"
				elif any(word in search_text for word in ["movie", "event", "ticket"]):
					category = "Entertainment"
					subcategory = "Movies" if "movie" in search_text else "Events"
				elif any(word in search_text for word in ["shop", "clothes", "electronic", "home item"]):
					category = "Shopping"
					subcategory = "Clothes" if "cloth" in search_text else "Electronics"
				elif any(word in search_text for word in ["medical", "pharmacy", "insurance", "doctor"]):
					category = "Healthcare"
					subcategory = "Medical"
				elif any(word in search_text for word in ["gift", "birthday", "wedding", "holiday"]):
					category = "Gift"
					subcategory = "Birthday" if "birthday" in search_text else "Holiday"

		valid_cats = list(CATEGORIES.get(display_type, {}).keys())
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
	except Exception:
		return {"auto_processed": False, "type": "Expense", "amount": 0.0, "description": text, "category": "Other", "subcategory": "Miscellaneous", "date": datetime.datetime.now(), "due_date": None}


def add_transaction_to_sheet(transaction: dict) -> bool:
	try:
		user = get_current_user()
		if not user:
			raise RuntimeError("Please log in to save transactions.")

		date_val = transaction.get("date", datetime.datetime.now())
		if isinstance(date_val, datetime.datetime):
			date_str = date_val.strftime("%Y-%m-%d")
		elif isinstance(date_val, datetime.date):
			date_str = date_val.strftime("%Y-%m-%d")
		else:
			date_str = str(date_val)

		trans_type = transaction.get("type", "Expense")
		amount = transaction.get("amount", 0.0)
		category = transaction.get("category", "Other")
		subcategory = transaction.get("subcategory", "Miscellaneous")
		description = transaction.get("description", "")
		due_date_val = transaction.get("due_date", None)
		if due_date_val and isinstance(due_date_val, (datetime.datetime, datetime.date)):
			due_date_str = due_date_val.strftime("%Y-%m-%d")
		elif due_date_val:
			due_date_str = str(due_date_val)
		else:
			due_date_str = ""

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
		st.cache_data.clear()
		return True
	except Exception as e:
		logger.error(str(e))
		return False


def show_transaction_form():
	transaction = st.session_state.current_transaction
	if transaction is None:
		return

	if transaction.get("auto_processed") == True:
		if transaction.get("error"):
			st.error(f"❌ {transaction['error']}")
		else:
			st.success(f"✅ Auto-processed: {transaction.get('type')} of ₹{transaction.get('amount')} — {transaction.get('description')}")
		if st.button("OK", key="auto_ok"):
			st.session_state.current_transaction = None
			st.session_state.form_submitted = False
			st.rerun()
		return

	st.subheader("✏️ Confirm Transaction Details")
	with st.form("transaction_form"):
		col1, col2 = st.columns(2)
		with col1:
			date_default = transaction.get("date", datetime.datetime.now())
			if isinstance(date_default, datetime.datetime):
				date_default = date_default.date()
			date_val = st.date_input("Date", value=date_default)
		with col2:
			amount_val = st.number_input("Amount (₹)", min_value=0.0, value=float(transaction.get("amount", 0.0)), step=0.01)

		trans_type_default = transaction.get("type", "Expense")
		type_idx = TRANSACTION_TYPES.index(trans_type_default) if trans_type_default in TRANSACTION_TYPES else 0
		type_val = st.selectbox("Transaction Type", TRANSACTION_TYPES, index=type_idx)
		valid_categories = list(CATEGORIES.get(type_val, {}).keys())
		if not valid_categories:
			valid_categories = ["Other"]
		saved_cat = transaction.get("category", valid_categories[0])
		cat_idx = valid_categories.index(saved_cat) if saved_cat in valid_categories else 0
		category_val = st.selectbox("Category", valid_categories, index=cat_idx)
		valid_subcategories = CATEGORIES.get(type_val, {}).get(category_val, ["Other"])
		saved_sub = transaction.get("subcategory", valid_subcategories[0])
		sub_idx = valid_subcategories.index(saved_sub) if saved_sub in valid_subcategories else 0
		subcategory_val = st.selectbox("Subcategory", valid_subcategories, index=sub_idx)
		description_val = st.text_input("Description", value=transaction.get("description", ""))
		due_date_val = None
		if type_val in ["To Pay", "To Receive"]:
			due_default = transaction.get("due_date", datetime.datetime.now())
			if isinstance(due_default, datetime.datetime):
				due_default = due_default.date()
			if not isinstance(due_default, datetime.date):
				due_default = datetime.date.today()
			due_date_val = st.date_input("Due Date", value=due_default)
		submitted = st.form_submit_button("💾 Save Transaction")

	if submitted:
		updated_transaction = {
			"type": type_val,
			"amount": amount_val,
			"category": category_val,
			"subcategory": subcategory_val,
			"description": description_val,
			"date": date_val,
			"due_date": due_date_val
		}
		success = add_transaction_to_sheet(updated_transaction)
		if success:
			st.success("✅ Transaction saved successfully!")
		else:
			st.error("❌ Failed to save. Check your Google Sheets connection.")
		st.session_state.current_transaction = None
		st.session_state.form_submitted = False
		st.rerun()


def main():
	st.set_page_config(page_title="Smart Finance Tracker", page_icon="💰", layout="wide")
	init_session_state()
	if not is_authenticated():
		if render_auth_ui():
			st.rerun()
		return

	try:
		ensure_indexes()
	except Exception as e:
		st.error(f"MongoDB connection failed: {e}")
		return

	user = get_current_user()
	st.title(" Smart Finance Tracker")
	st.caption(f"Signed in as {user['name']} ({user['email']})")

	st.sidebar.title(" How to use")
	st.sidebar.markdown("""
	**Type transactions naturally:**
	- 'Spent 500 on groceries yesterday'
	- 'Got salary 50000 today'
	- 'Need to pay rent 15000 next week'
	- 'Received pending amount of 2000'
	- 'Paid pending amount of 5000'
	""")
	st.sidebar.divider()
	if st.sidebar.button("Log out"):
		logout_user()
		st.rerun()
	if st.sidebar.button("🗑️ Clear Chat History"):
		st.session_state.messages = []
		st.session_state.current_transaction = None
		st.session_state.form_submitted = False
		st.rerun()
	
	st.sidebar.divider()
	# st.sidebar.subheader("📊 Export Data")
	# if st.sidebar.button("Download to Google Sheets"):
	# 	try:
	# 		success, sheet_id = export_user_data(user['_id'])
	# 		if success:
	# 			st.sidebar.success(f"✅ Data exported! Sheet ID: {sheet_id}")
	# 			st.sidebar.markdown(f"[Open in Google Sheets](https://docs.google.com/spreadsheets/d/{sheet_id})")
	# 		else:
	# 			st.sidebar.error("❌ Export failed. Check your credentials.")
	# 	except Exception as e:
	# 		st.sidebar.error(f"❌ Error: {str(e)}")
	# 		logger.error(f"Export error: {str(e)}")

	for msg in st.session_state.messages:
		with st.chat_message(msg["role"]):
			st.markdown(msg["content"])

	if st.session_state.form_submitted and st.session_state.current_transaction is not None:
		show_transaction_form()

	user_input = st.chat_input("Type your transaction... e.g. 'Spent 500 on groceries yesterday'")
	if user_input:
		with st.chat_message("user"):
			st.markdown(user_input)
		st.session_state.messages.append({"role": "user", "content": user_input})
		with st.spinner("🤔 Processing your transaction..."):
			result = process_user_input(user_input)
		st.session_state.current_transaction = result
		st.session_state.form_submitted = True
		if result.get("auto_processed") == True and not result.get("error"):
			assistant_msg = f"✅ Auto-processed! Found and updated your pending transaction. ₹{result.get('amount')} recorded as {result.get('type')}."
		elif result.get("auto_processed") == True and result.get("error"):
			assistant_msg = f"❌ {result.get('error')}"
		else:
			assistant_msg = f"I understood: **{result.get('type')}** of **₹{result.get('amount')}** — {result.get('description')}. Please confirm or edit the details below."
		st.session_state.messages.append({"role": "assistant", "content": assistant_msg})
		with st.chat_message("assistant"):
			st.markdown(assistant_msg)
		st.rerun()


if __name__ == "__main__":
	main()
