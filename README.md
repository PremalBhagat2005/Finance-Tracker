# Smart Finance Tracker

Smart Finance Tracker is a personal AI-powered expense and income tracking app built with Streamlit, Google Gemini, and Google Sheets.

It lets you type transactions in natural language (for example, "spent 450 on recharge" or "will receive 14000 from job tomorrow"), then auto-detects amount, type, category, date, and pending status before saving to Google Sheets.

## Project Highlights

- Natural language transaction input using Gemini (`gemini-2.0-flash`)
- Smart classification for:
  - Expense
  - Income
  - To Receive (pending incoming)
  - To Pay (pending outgoing)
- Auto date parsing (`today`, `yesterday`, `tomorrow`, `last/next ...`)
- Keyword-enhanced category mapping for better reliability
- Pending transaction workflow:
  - Save future/pending items in `Pending` sheet
  - Auto-mark received/paid pending entries
- Analytics dashboard with:
  - Income vs Expense KPIs
  - Monthly trend chart
  - Category breakdown
  - Monthly summary
  - Recent transactions
  - Weekday vs weekend expense insights
  - Pending table with upcoming to-pay / to-receive totals

## Tech Stack

- Python 3.14
- Streamlit 1.56+
- Gemini via `google-genai` (official SDK)
- Google Sheets API v4
- pandas 3.x
- Plotly Express 6.x
- Rich logging

## Project Structure

```text
smart-finance-tracker/
├── Home.py
├── requirements.txt
├── .env
├── .gitignore
├── credentials.json
├── README.md
├── config/
│   ├── __init__.py
│   └── constants.py
├── services/
│   ├── __init__.py
│   └── google_sheets.py
├── utils/
│   ├── __init__.py
│   └── logging_utils.py
└── pages/
    └── 📊_Analytics.py
```

## Setup

### 1. Clone and open project

```bash
git clone <your-repo-url>
cd Finance_Traker
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

### 4. Configure environment variables

Create/update `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEET_ID=your_google_sheet_id
```

### 5. Google Sheets setup

1. Create a Google Sheet.
2. Copy the Sheet ID into `GOOGLE_SHEET_ID`.
3. Keep service account JSON in `credentials.json`.
4. Share the Google Sheet with your service account email (`client_email` from `credentials.json`) as **Editor**.

Without sharing, Sheets API calls will fail with permission errors.

## Run the App

```bash
streamlit run Home.py
```

Open the local URL shown in terminal (usually `http://localhost:8501`).

## How to Use

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

- Future incoming/outgoing records are stored in `Pending` sheet.
- Completed pending records can be auto-processed:
  - Pending receive -> marks as `Received` and adds to `Expenses` as `Income`
  - Pending pay -> marks as `Paid` and adds to `Expenses` as `Expense`

### Analytics

Go to the Analytics page to view:

- Total income, total expense, net balance, savings rate
- Monthly Income vs Expense trend
- Category pies
- Monthly summary table
- Recent transactions
- Weekday vs weekend spending
- Pending table with future/open pending entries

## Data Model (Google Sheets)

### `Expenses` sheet columns

- Date
- Amount
- Type
- Category
- Subcategory
- Description

### `Pending` sheet columns

- Date
- Amount
- Type
- Category
- Description
- Due Date
- Status

## Important Notes

- This is a personal project and currently stores data in Google Sheets.
- Chat history is kept in Streamlit session state and is not persisted as a separate chat log in Sheets.
- Keep `.env` and `credentials.json` private.
- Do not commit API keys or service-account secrets to public repositories.

## Known Practical Behavior

- If your analytics chart has only one month of data, lines appear as single points.
- Future-dated transactions are excluded by default in date filters that end at today.
  Use `Custom Range` to include future dates.

## Future Improvements

- Add transaction edit/delete UI
- Add recurring transaction support
- Export reports to CSV/PDF
- Add authentication per user profile
- Add budget alerts and spending limits

## License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for full text.
