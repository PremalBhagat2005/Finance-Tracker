import os
import json
from pathlib import Path

import streamlit as st
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

from utils.logging_utils import logger

load_dotenv()


@st.cache_resource
def get_sheets_service():
    try:
        credentials_source = os.getenv('GOOGLE_SHEETS_CREDENTIALS', 'credentials.json').strip()
        scopes = ['https://www.googleapis.com/auth/spreadsheets']

        if credentials_source.startswith('{'):
            creds = service_account.Credentials.from_service_account_info(
                json.loads(credentials_source),
                scopes=scopes
            )
        else:
            credentials_path = Path(credentials_source)
            if not credentials_path.is_absolute():
                project_root = Path(__file__).resolve().parent.parent
                candidate_path = project_root / credentials_path
                if candidate_path.exists():
                    credentials_path = candidate_path
            if not credentials_path.exists():
                fallback_path = Path(__file__).resolve().parent.parent / 'credentials.json'
                if fallback_path.exists():
                    credentials_path = fallback_path
            creds = service_account.Credentials.from_service_account_file(
                str(credentials_path),
                scopes=scopes
            )

        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logger.error(str(e))
        raise


def initialize_sheet(service, sheet_id):
    try:
        result = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        existing_titles = [s['properties']['title'] for s in result['sheets']]

        if 'Expenses' not in existing_titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    'requests': [
                        {
                            'addSheet': {
                                'properties': {
                                    'title': 'Expenses'
                                }
                            }
                        }
                    ]
                }
            ).execute()
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='Expenses!A1',
                valueInputOption='USER_ENTERED',
                body={'values': [['Date', 'Amount', 'Type', 'Category', 'Subcategory', 'Description']]}
            ).execute()

        if 'Pending' not in existing_titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    'requests': [
                        {
                            'addSheet': {
                                'properties': {
                                    'title': 'Pending'
                                }
                            }
                        }
                    ]
                }
            ).execute()
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='Pending!A1',
                valueInputOption='USER_ENTERED',
                body={'values': [['Date', 'Amount', 'Type', 'Category', 'Description', 'Due Date', 'Status']]}
            ).execute()

        if 'Income' not in existing_titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    'requests': [
                        {
                            'addSheet': {
                                'properties': {
                                    'title': 'Income'
                                }
                            }
                        }
                    ]
                }
            ).execute()
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='Income!A1',
                valueInputOption='USER_ENTERED',
                body={'values': [['Date', 'Amount', 'Type', 'Category', 'Subcategory', 'Description']]}
            ).execute()

        return True
    except HttpError as e:
        logger.error(str(e))
        return False
    except Exception as e:
        logger.error(str(e))
        return False


def read_sheet(service, sheet_id, sheet_name, range_='A1:Z') -> list:
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!{range_}"
        ).execute()
        return result.get('values', [])
    except Exception as e:
        logger.error(str(e))
        return []


def append_row(service, sheet_id, sheet_name, values: list):
    try:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={"values": [values]}
        ).execute()
    except Exception as e:
        logger.error(str(e))
        raise


def update_row(service, sheet_id, sheet_name, range_: str, values: list):
    try:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!{range_}",
            valueInputOption='USER_ENTERED',
            body={"values": [values]}
        ).execute()
    except Exception as e:
        logger.error(str(e))
        raise


def export_user_data(user_id: str):
    """Export all user data to Google Sheet"""
    try:
        from services.mongo_store import get_expenses_dataframe, get_income_dataframe, get_pending_dataframe
        from bson import ObjectId
        
        service = get_sheets_service()
        sheet_id = os.getenv('GOOGLE_SHEET_ID')
        
        # Initialize sheets
        initialize_sheet(service, sheet_id)
        
        # Helper to convert DataFrame to sheet values, handling ObjectId
        def df_to_values(df):
            # Remove _id column if present
            if '_id' in df.columns:
                df = df.drop('_id', axis=1)
            
            if df.empty:
                return [df.columns.tolist()]
            values = [df.columns.tolist()]
            for _, row in df.iterrows():
                row_values = []
                for val in row.values:
                    if isinstance(val, ObjectId):
                        row_values.append(str(val))
                    elif val is None or (isinstance(val, float) and str(val) == 'nan'):
                        row_values.append("")
                    else:
                        row_values.append(str(val))
                values.append(row_values)
            return values
        
        # Clear and write expenses
        expenses_df = get_expenses_dataframe(user_id)
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Expenses!A1',
            valueInputOption='USER_ENTERED',
            body={'values': df_to_values(expenses_df)}
        ).execute()
        
        # Clear and write pending
        pending_df = get_pending_dataframe(user_id)
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Pending!A1',
            valueInputOption='USER_ENTERED',
            body={'values': df_to_values(pending_df)}
        ).execute()
        
        # Clear and write income
        income_df = get_income_dataframe(user_id)
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Income!A1',
            valueInputOption='USER_ENTERED',
            body={'values': df_to_values(income_df)}
        ).execute()
        
        return True, sheet_id
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None
