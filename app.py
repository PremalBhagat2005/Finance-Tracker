import os
import io
import json
import datetime
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import plotly.express as px
import plotly.utils

from services.auth import authenticate_user, register_user, is_authenticated, logout_user
from services.chat import process_user_input, add_transaction, get_transactions_data
from services.mongo_store import get_pending_dataframe, ensure_indexes
from config.constants import TRANSACTION_TYPES, CATEGORIES

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_dev_key")

@app.before_request
def ensure_db_indexes():
    ensure_indexes()

@app.route("/")
def index():
    if not is_authenticated():
        return redirect(url_for("login"))
    
    if "messages" not in session:
        session["messages"] = []
    
    return render_template("index.html", 
                           messages=session.get("messages", []), 
                           current_transaction=session.get("current_transaction"),
                           transaction_types=TRANSACTION_TYPES,
                           categories=CATEGORIES)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
        
    user_input = request.json.get("user_input")
    if not user_input:
        return jsonify({"error": "No input"}), 400
        
    messages = session.get("messages", [])
    messages.append({"role": "user", "content": user_input})
    
    result = process_user_input(user_input)
    
    if result.get("auto_processed") == True:
        if result.get("error"):
            assistant_msg = f"<i data-lucide='x-circle' style='color: var(--danger-color); width:14px; height:14px; margin-bottom:-2px'></i> {result.get('error')}"
        else:
            assistant_msg = f"<i data-lucide='check-circle' style='color: var(--success-color); width:14px; height:14px; margin-bottom:-2px'></i> Auto-processed! Found and updated your pending transaction. ₹{result.get('amount')} recorded as {result.get('type')}."
        messages.append({"role": "assistant", "content": assistant_msg})
        session["current_transaction"] = None
    else:
        assistant_msg = f"I understood: **{result.get('type')}** of **₹{result.get('amount')}** — {result.get('description')}. Please confirm or edit the details below."
        messages.append({"role": "assistant", "content": assistant_msg})
        
        if result.get("date") and isinstance(result.get("date"), (datetime.date, datetime.datetime)):
            result["date"] = result["date"].strftime('%Y-%m-%d')
        if result.get("due_date") and isinstance(result.get("due_date"), (datetime.date, datetime.datetime)):
            result["due_date"] = result["due_date"].strftime('%Y-%m-%d')
            
        session["current_transaction"] = result
    
    session["messages"] = messages
    session.modified = True
    return jsonify({
        "messages": messages,
        "current_transaction": session.get("current_transaction"),
        "transaction_types": TRANSACTION_TYPES,
        "categories": CATEGORIES
    })

@app.route("/api/confirm", methods=["POST"])
def api_confirm():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    success = add_transaction(data)
    messages = session.get("messages", [])
    if success:
        messages.append({"role": "assistant", "content": "<i data-lucide='check-circle' style='color: var(--success-color); width:14px; height:14px; margin-bottom:-2px'></i> Transaction saved successfully!"})
    else:
        messages.append({"role": "assistant", "content": "<i data-lucide='x-circle' style='color: var(--danger-color); width:14px; height:14px; margin-bottom:-2px'></i> Failed to save transaction."})
        
    session["messages"] = messages
    session["current_transaction"] = None
    session.modified = True
    return jsonify({"messages": messages, "current_transaction": None})

@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
    session["current_transaction"] = None
    session.modified = True
    return jsonify({"success": True})

@app.route("/api/clear", methods=["POST"])
def api_clear():
    if not is_authenticated():
        return jsonify({"error": "Unauthorized"}), 401
    session["messages"] = []
    session["current_transaction"] = None
    session.modified = True
    return jsonify({"messages": [], "current_transaction": None})

@app.route("/login", methods=["GET", "POST"])
def login():
    if is_authenticated():
        return redirect(url_for("index"))
        
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        try:
            user = authenticate_user(email, password)
            if user:
                session["authenticated"] = True
                session["current_user"] = user
                flash(f"Welcome back, {user['name']}.", "success")
                return redirect(url_for("index"))
            else:
                flash("Invalid email or password.", "error")
        except Exception as e:
            flash(f"Login failed: {e}", "error")
            
    return render_template("auth.html", active_tab="login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if is_authenticated():
        return redirect(url_for("index"))
        
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
        elif not name.strip() or not email.strip() or not password:
            flash("Please fill in all fields.", "error")
        else:
            try:
                user = register_user(name, email, password)
                session["authenticated"] = True
                session["current_user"] = user
                flash(f"Account created for {user['name']}.", "success")
                return redirect(url_for("index"))
            except Exception as e:
                flash(f"Registration failed: {e}", "error")
                
    return render_template("auth.html", active_tab="register")

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/export/excel")
def export_excel():
    if not is_authenticated():
        return redirect(url_for("login"))
        
    user = session.get("current_user")
    df = get_transactions_data(user["user_id"])
    
    if df.empty:
        flash("No transactions to export.", "error")
        return redirect(url_for("analytics"))
        
    export_df = df.copy()
    if 'Date' in export_df.columns:
        export_df['Date'] = pd.to_datetime(export_df['Date']).dt.strftime('%Y-%m-%d')
    if 'Due Date' in export_df.columns:
        export_df['Due Date'] = pd.to_datetime(export_df['Due Date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Transactions')
    
    output.seek(0)
    
    filename = f"finance_tracker_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/analytics")
def analytics():
    if not is_authenticated():
        return redirect(url_for("login"))
        
    user = session.get("current_user")
    df = get_transactions_data(user["user_id"])
    
    if df.empty:
        return render_template("analytics.html", is_empty=True)
        
    # Data Processing
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    
    income_df = df[df["Type"] == "Income"]
    expense_df = df[df["Type"] == "Expense"]
    
    total_income = income_df["Amount"].sum()
    total_expense = expense_df["Amount"].sum()
    net_balance = total_income - total_expense
    saving_rate = (net_balance / total_income * 100) if total_income > 0 else 0
    
    # Monthly Income vs Expenses Chart
    chart_df = df.copy()
    chart_df["Month"] = chart_df["Date"].dt.year.astype(str) + "-" + chart_df["Date"].dt.month.astype(str).str.zfill(2)
    inc_df = chart_df[chart_df["Type"] == "Income"].copy()
    exp_df = chart_df[chart_df["Type"] == "Expense"].copy()
    
    inc_grouped = inc_df.groupby("Month", as_index=False)["Amount"].sum()
    inc_grouped["Type"] = "Income"
    exp_grouped = exp_df.groupby("Month", as_index=False)["Amount"].sum()
    exp_grouped["Type"] = "Expense"
    
    combined = pd.concat([inc_grouped, exp_grouped], ignore_index=True).sort_values("Month")
    
    trend_chart_json = None
    if not combined.empty:
        fig = px.line(
            combined, x="Month", y="Amount", color="Type", markers=True,
            color_discrete_map={"Income": "#00CC96", "Expense": "#EF553B"},
            title="Monthly Income vs Expenses", template="plotly_dark"
        )
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
        trend_chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
    # Category Breakdown Charts
    expense_pie_json = None
    if not expense_df.empty:
        exp_cat = expense_df.groupby("Category")["Amount"].sum().reset_index()
        fig_exp = px.pie(exp_cat, values="Amount", names="Category", title="Expense by Category", template="plotly_dark")
        fig_exp.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
        expense_pie_json = json.dumps(fig_exp, cls=plotly.utils.PlotlyJSONEncoder)
        
    income_pie_json = None
    if not income_df.empty:
        inc_cat = income_df.groupby("Category")["Amount"].sum().reset_index()
        fig_inc = px.pie(inc_cat, values="Amount", names="Category", title="Income by Category", template="plotly_dark")
        fig_inc.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
        income_pie_json = json.dumps(fig_inc, cls=plotly.utils.PlotlyJSONEncoder)
        
    # Pending Transactions
    pending_df = get_pending_dataframe(user["user_id"])
    to_pay, to_receive = 0.0, 0.0
    pending_display = []
    
    if not pending_df.empty:
        open_pending = pending_df[pending_df["Status"].str.lower() == "pending"].copy()
        if not open_pending.empty:
            today = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
            future_or_undated = open_pending[
                open_pending["Due Date"].isna() | (open_pending["Due Date"] >= today)
            ].copy()
            
            to_receive = future_or_undated[future_or_undated["Type"] == "To Receive"]["Amount"].sum()
            to_pay = future_or_undated[future_or_undated["Type"] == "To Pay"]["Amount"].sum()
            
            future_or_undated["Due Date"] = future_or_undated["Due Date"].dt.strftime('%Y-%m-%d').fillna("N/A")
            future_or_undated["Date"] = future_or_undated["Date"].dt.strftime('%Y-%m-%d')
            pending_display = future_or_undated.sort_values("Due Date").to_dict('records')
            
    # Recent Transactions
    df["Date"] = df["Date"].dt.strftime('%Y-%m-%d')
    recent_transactions = df.sort_values("Date", ascending=False).head(5).to_dict('records')

    return render_template("analytics.html", 
                           is_empty=False,
                           total_income=total_income,
                           total_expense=total_expense,
                           net_balance=net_balance,
                           saving_rate=saving_rate,
                           to_pay=to_pay,
                           to_receive=to_receive,
                           trend_chart_json=trend_chart_json,
                           expense_pie_json=expense_pie_json,
                           income_pie_json=income_pie_json,
                           pending_transactions=pending_display,
                           recent_transactions=recent_transactions)

if __name__ == "__main__":
    app.run(debug=False, port=5001)
