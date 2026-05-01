import os
import datetime as dt

import pandas as pd
import streamlit as st
from bson import ObjectId
from pymongo import ASCENDING, MongoClient


@st.cache_resource
def get_mongo_client():
	uri = os.getenv("MONGODB_URI", "").strip()
	if not uri:
		raise RuntimeError("MONGODB_URI is not set")
	return MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)


def get_db():
	db_name = os.getenv("MONGODB_DB_NAME", "smart_finance_tracker").strip()
	return get_mongo_client()[db_name]


def ensure_indexes():
	db = get_db()
	db.users.create_index("email", unique=True)
	db.expenses.create_index([("user_id", ASCENDING), ("Date", ASCENDING)])
	db.pending.create_index([("user_id", ASCENDING), ("Status", ASCENDING), ("Type", ASCENDING)])
	db.income.create_index([("user_id", ASCENDING), ("Date", ASCENDING)])


def _frame_from_records(records: list[dict], columns: list[str]) -> pd.DataFrame:
	if not records:
		return pd.DataFrame(columns=columns)
	df = pd.DataFrame(records)
	for column in columns:
		if column not in df.columns:
			df[column] = None
	return df[columns]


def get_expenses_dataframe(user_id: str) -> pd.DataFrame:
	records = list(
		get_db().expenses.find(
			{"user_id": user_id},
			{"_id": 0, "user_id": 0, "created_at": 0, "updated_at": 0}
		).sort("Date", 1)
	)
	df = _frame_from_records(records, ["Date", "Amount", "Type", "Category", "Subcategory", "Description"])
	if not df.empty:
		df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
		df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
	return df


def get_pending_dataframe(user_id: str) -> pd.DataFrame:
	records = list(
		get_db().pending.find(
			{"user_id": user_id},
			{"_id": 1, "user_id": 0, "created_at": 0, "updated_at": 0}
		).sort("Due Date", 1)
	)
	df = _frame_from_records(records, ["_id", "Date", "Amount", "Type", "Category", "Description", "Due Date", "Status"])
	if not df.empty:
		df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
		df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
		df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce")
		df["Status"] = df["Status"].fillna("Pending")
	return df


def get_income_dataframe(user_id: str) -> pd.DataFrame:
	records = list(
		get_db().income.find(
			{"user_id": user_id},
			{"_id": 0, "user_id": 0, "created_at": 0, "updated_at": 0}
		).sort("Date", 1)
	)
	df = _frame_from_records(records, ["Date", "Amount", "Type", "Category", "Subcategory", "Description"])
	if not df.empty:
		df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
		df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
	return df


def insert_expense(user_id: str, transaction: dict):
	doc = {
		"user_id": user_id,
		"Date": transaction.get("date", dt.datetime.utcnow()),
		"Amount": float(transaction.get("amount", 0.0)),
		"Type": transaction.get("type", "Expense"),
		"Category": transaction.get("category", "Other"),
		"Subcategory": transaction.get("subcategory", "Miscellaneous"),
		"Description": transaction.get("description", ""),
		"created_at": dt.datetime.utcnow(),
	}
	get_db().expenses.insert_one(doc)


def insert_pending(user_id: str, transaction: dict):
	doc = {
		"user_id": user_id,
		"Date": transaction.get("date", dt.datetime.utcnow()),
		"Amount": float(transaction.get("amount", 0.0)),
		"Type": transaction.get("type", "To Pay"),
		"Category": transaction.get("category", "Other"),
		"Description": transaction.get("description", ""),
		"Due Date": transaction.get("due_date", None),
		"Status": transaction.get("status", "Pending"),
		"created_at": dt.datetime.utcnow(),
	}
	get_db().pending.insert_one(doc)


def insert_income(user_id: str, transaction: dict):
	doc = {
		"user_id": user_id,
		"Date": transaction.get("date", dt.datetime.utcnow()),
		"Amount": float(transaction.get("amount", 0.0)),
		"Type": transaction.get("type", "Income"),
		"Category": transaction.get("category", "Other"),
		"Subcategory": transaction.get("subcategory", "Miscellaneous"),
		"Description": transaction.get("description", ""),
		"created_at": dt.datetime.utcnow(),
	}
	get_db().income.insert_one(doc)


def find_pending_match(user_id: str, amount: float, pending_type: str):
	query = {"user_id": user_id, "Type": pending_type, "Status": "Pending"}
	for doc in get_db().pending.find(query):
		try:
			if abs(float(doc.get("Amount", 0.0)) - amount) < 0.01:
				return doc
		except (TypeError, ValueError):
			continue
	return None


def update_pending_status(pending_id: ObjectId, status: str):
	get_db().pending.update_one(
		{"_id": pending_id},
		{"$set": {"Status": status, "updated_at": dt.datetime.utcnow()}}
	)
