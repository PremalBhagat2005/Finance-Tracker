# 💸 Smart Finance Tracker

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-black.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-Database-brightgreen.svg)
![Gemini](https://img.shields.io/badge/AI-Google_Gemini-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

Smart Finance Tracker is an AI-powered expense and income tracking app built with Flask, Google Gemini, and MongoDB.

It originally used Google Sheets as the main storage layer and Streamlit for the frontend, but it was migrated to a Flask-based web application backed by MongoDB for better performance, scalability, and multi-user data handling. Google Sheets is now used for optional exports and downloadable reports.

It lets you type transactions in natural language (for example, *"spent 450 on recharge"* or *"will receive 14000 from job tomorrow"*), then auto-detects amount, type, category, date, and pending status before saving to MongoDB.

## 📑 Table of Contents

- [Project Highlights](#-project-highlights)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Setup](#-setup)
- [Run the App](#-run-the-app)
- [How to Use](#-how-to-use)
- [Data Model (MongoDB)](#-data-model-mongodb)
- [Important Notes](#-important-notes)
- [Future Improvements](#-future-improvements)
- [License](#-license)

---

## ✨ Project Highlights

- **Web App Interface**: Modern, responsive web interface built with HTML, CSS, and Flask.
- **User Authentication**: Secure multi-user login and registration system.
- **Natural Language Input**: Transaction input using Gemini (`gemini-2.0-flash`).
- **Smart Classification**: 
  - Expense
  - Income
  - To Receive (pending incoming)
  - To Pay (pending outgoing)
- **Auto Date Parsing**: `today`, `yesterday`, `tomorrow`, `last/next ...`
- **Pending Transaction Workflow**:
  - Save future/pending items in MongoDB
  - Auto-mark received/paid pending entries
- **Analytics Dashboard**:
  - Income vs Expense KPIs
  - Monthly trend chart (Interactive Plotly Chart)
  - Category breakdown pies
  - Recent transactions list
  - Pending table with upcoming to-pay / to-receive totals

## 🛠 Tech Stack

- **Backend**: Python 3.14+, Flask
- **Frontend**: HTML5, Vanilla CSS, JS
- **AI/NLP**: Gemini via `google-genai` (official SDK)
- **Database**: MongoDB Atlas or self-hosted MongoDB
- **Data Visualization**: pandas 3.x, Plotly Express 6.x
- **Optional Integrations**: Google Sheets API for exports

## 📁 Project Structure

```text
smart-finance-tracker/
├── app.py                  # Main Flask application
├── requirements.txt
├── .env
├── README.md
├── config/
│   ├── __init__.py
│   └── constants.py
├── services/
│   ├── __init__.py
│   ├── auth.py             # User authentication logic
│   ├── chat.py             # Gemini AI processing logic
│   ├── google_sheets.py
│   └── mongo_store.py      # MongoDB database operations
├── static/
│   ├── css/
│   │   └── style.css       # Main stylesheet
│   └── js/
│       └── main.js         # Frontend interactions
├── templates/              # HTML Templates
│   ├── auth.html           # Login/Register page
│   ├── index.html          # Main chat interface
│   ├── analytics.html      # Dashboard
│   └── base.html           # Layout wrapper
└── utils/
    ├── __init__.py
    └── logging_utils.py
```

## ⚙️ Setup

### 1. Clone and open project

```bash
git clone <your-repo-url>
cd Finance_Tracker
```

### 2. Create and activate virtual environment

Windows PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```
> **Note**: Ensure `flask` is installed if missing from requirements: `pip install flask`

### 4. Configure environment variables

Create/update `.env`:

```env
SECRET_KEY=your_flask_secret_key
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=your_mongodb_connection_string
MONGODB_DB_NAME=smart_finance_tracker
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEET_ID=your_google_sheet_id
```

### 5. MongoDB setup

1. Create a MongoDB Atlas cluster or use a self-hosted MongoDB instance.
2. Copy the connection string into `MONGODB_URI`.
3. Set `MONGODB_DB_NAME` if you want a different database name.
4. Make sure the app can reach MongoDB from your deployment host.

## ▶️ Run the App

```bash
python app.py
```

Open the local URL shown in terminal (usually `http://localhost:5000`).

## 💡 How to Use

### Authentication
Create an account or login to access your personal dashboard. Each user's data is completely isolated.

### Add transactions in chat

Try examples like:
- `Spent 500 on groceries yesterday`
- `Got salary 50000 today`
- `Need to pay rent 15000 next week`
- `Will receive 14000 from job tomorrow`
- `Received pending amount of 2000`
- `Paid pending amount of 5000`

The app extracts and pre-fills details in a confirmation form before saving.

### Pending logic

- Future incoming/outgoing records are stored in MongoDB.
- Completed pending records can be auto-processed:
  - Pending receive -> marks as `Received` and adds to `Expenses` as `Income`
  - Pending pay -> marks as `Paid` and adds to `Expenses` as `Expense`

### Analytics

Go to the Analytics page to view:
- Total income, total expense, net balance, savings rate
- Monthly Income vs Expense trend (Interactive)
- Category pies
- Recent transactions
- Pending table with future/open pending entries

## 🗄️ Data Model (MongoDB)

### `expenses` collection fields
- `user_id`, `Date`, `Amount`, `Type`, `Category`, `Subcategory`, `Description`, `created_at`

### `pending` collection fields
- `user_id`, `Date`, `Amount`, `Type`, `Category`, `Description`, `Due Date`, `Status`, `created_at`

### `users` collection fields
- `name`, `email`, `password_salt`, `password_hash`

## ⚠️ Important Notes

- Each signed-in user gets isolated expense and pending records in MongoDB by `user_id`.
- Keep `.env` private. Do not commit API keys or MongoDB credentials to public repositories.

## 🚀 Future Improvements

- Add transaction edit/delete UI
- Add recurring transaction support
- Export reports to CSV/PDF
- Add budget alerts and spending limits

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for full text.
