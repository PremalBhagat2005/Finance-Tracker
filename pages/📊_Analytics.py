import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Home import get_transactions_data, init_session_state, render_auth_ui
from services.auth import get_current_user, is_authenticated, logout_user
from services.mongo_store import get_pending_dataframe


def get_date_filters() -> tuple[datetime.date, datetime.date]:
    st.sidebar.title("📅 Date Filter")
    filter_type = st.sidebar.radio("Filter by", ["All Time", "This Year", "This Month", "Custom Range"], key="analytics_filter")
    today = datetime.date.today()
    if filter_type == "All Time":
        start = datetime.date(2000, 1, 1)
        end = today
    elif filter_type == "This Year":
        start = datetime.date(today.year, 1, 1)
        end = today
    elif filter_type == "This Month":
        start = datetime.date(today.year, today.month, 1)
        end = today
    else:
        col1, col2 = st.sidebar.columns(2)
        start = col1.date_input("From", value=datetime.date(today.year, 1, 1), key="start_date")
        end = col2.date_input("To", value=today, key="end_date")
    return start, end


@st.cache_data(ttl=300)
def get_pending_data(user_id: str) -> pd.DataFrame:
    df = get_pending_dataframe(user_id)
    if df.empty:
        return pd.DataFrame(columns=["Date", "Amount", "Type", "Category", "Description", "Due Date", "Status"])
    return df


def show_pending_analytics(user_id: str):
    st.subheader("⏳ Pending Transactions")
    pending_df = get_pending_data(user_id)

    if pending_df.empty:
        st.info("No pending transactions found.")
        return

    open_pending = pending_df[pending_df["Status"].str.lower() == "pending"].copy()
    if open_pending.empty:
        st.info("No open pending transactions.")
        return

    today = datetime.date.today()
    future_or_undated = open_pending[
        open_pending["Due Date"].isna() | (open_pending["Due Date"].dt.date >= today)
    ].copy()

    if future_or_undated.empty:
        st.info("No pending transactions with upcoming due dates.")
        return

    to_receive = future_or_undated[future_or_undated["Type"] == "To Receive"]["Amount"].sum()
    to_pay = future_or_undated[future_or_undated["Type"] == "To Pay"]["Amount"].sum()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("💸 Pending To Pay", f"₹{to_pay:,.2f}")
    with col2:
        st.metric("💰 Pending To Receive", f"₹{to_receive:,.2f}")

    display_df = future_or_undated[
        ["Date", "Due Date", "Amount", "Type", "Category", "Description", "Status"]
    ].sort_values("Due Date", ascending=True)

    st.dataframe(display_df, use_container_width=True)


def show_overview_analytics(df: pd.DataFrame):
    df = df.copy()
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    income_df = df[df["Type"] == "Income"]
    expense_df = df[df["Type"] == "Expense"]
    total_income = income_df["Amount"].sum()
    total_expense = expense_df["Amount"].sum()
    net_balance = total_income - total_expense
    saving_rate = (net_balance / total_income * 100) if total_income > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Total Income", f"₹{total_income:,.2f}")
    with col2:
        st.metric("💸 Total Expenses", f"₹{total_expense:,.2f}")
    with col3:
        delta_value = f"₹{net_balance:+,.2f}"
        st.metric("📊 Net Balance", f"₹{net_balance:,.2f}", delta=delta_value, delta_color="normal")
    with col4:
        st.metric("📈 Saving Rate", f"{saving_rate:.1f}%")

    st.subheader("📈 Monthly Income vs Expenses")

    # Make a clean copy with proper types
    chart_df = df.copy()
    chart_df["Date"] = pd.to_datetime(chart_df["Date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["Date"])
    chart_df["Amount"] = pd.to_numeric(chart_df["Amount"], errors="coerce").fillna(0)
    
    # Create Month column as string in "YYYY-MM" format directly from date parts
    chart_df["Month"] = chart_df["Date"].dt.year.astype(str) + "-" + chart_df["Date"].dt.month.astype(str).str.zfill(2)

    # Separate income and expense
    inc_df = chart_df[chart_df["Type"] == "Income"].copy()
    exp_df = chart_df[chart_df["Type"] == "Expense"].copy()

    # Group by month
    inc_grouped = inc_df.groupby("Month", as_index=False)["Amount"].sum()
    inc_grouped["Type"] = "Income"

    exp_grouped = exp_df.groupby("Month", as_index=False)["Amount"].sum()
    exp_grouped["Type"] = "Expense"

    # Combine and sort
    combined = pd.concat([inc_grouped, exp_grouped], ignore_index=True)
    combined = combined.sort_values("Month")

    if not combined.empty:
        fig = px.line(
            combined,
            x="Month",
            y="Amount",
            color="Type",
            markers=True,
            color_discrete_map={"Income": "#00CC96", "Expense": "#EF553B"},
            labels={"Month": "Month", "Amount": "Amount (₹)"},
            title="Monthly Income vs Expenses"
        )
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
            hovermode="x unified",
            xaxis=dict(type="category")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data to display monthly trend.")

    st.subheader("🏷️ Category Breakdown")
    col1, col2 = st.columns(2)
    if not expense_df.empty:
        exp_cat = expense_df.groupby("Category")["Amount"].sum().reset_index()
        fig_exp = px.pie(exp_cat, values="Amount", names="Category", title="Expense by Category")
        col1.plotly_chart(fig_exp, use_container_width=True)
    if not income_df.empty:
        inc_cat = income_df.groupby("Category")["Amount"].sum().reset_index()
        fig_inc = px.pie(inc_cat, values="Amount", names="Category", title="Income by Category")
        col2.plotly_chart(fig_inc, use_container_width=True)

    st.subheader("📅 Monthly Summary")
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    inc_monthly = df[df["Type"] == "Income"].groupby("Month")["Amount"].sum()
    exp_monthly = df[df["Type"] == "Expense"].groupby("Month")["Amount"].sum()
    summary = pd.DataFrame({"Income": inc_monthly, "Expenses": exp_monthly}).fillna(0)
    summary["Net"] = summary["Income"] - summary["Expenses"]
    summary = summary.sort_index(ascending=False)
    st.dataframe(summary, use_container_width=True)

    st.subheader("🕐 Recent Transactions")
    recent = df.sort_values("Date", ascending=False).head(5)
    st.dataframe(recent[["Date", "Amount", "Type", "Category", "Subcategory", "Description"]], use_container_width=True)

    st.subheader("📊 Weekday vs Weekend Spending")
    if not expense_df.empty:
        exp_copy = expense_df.copy()
        exp_copy["DayOfWeek"] = exp_copy["Date"].dt.dayofweek
        exp_copy["DayType"] = exp_copy["DayOfWeek"].apply(lambda x: "Weekend" if x >= 5 else "Weekday")
        day_grouped = exp_copy.groupby("DayType")["Amount"].sum().reset_index()
        fig_day = px.bar(day_grouped, x="DayType", y="Amount", color="DayType", color_discrete_map={"Weekday": "steelblue", "Weekend": "coral"}, title="Weekday vs Weekend Spending")
        st.plotly_chart(fig_day, use_container_width=True)


def main():
    st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
    init_session_state()
    if not is_authenticated():
        if render_auth_ui():
            st.switch_page("Home.py")
        return

    user = get_current_user()
    st.title("Financial Analytics Dashboard")
    st.sidebar.button("Log out", on_click=logout_user)
    start_date, end_date = get_date_filters()
    with st.spinner("Loading transactions..."):
        df = get_transactions_data(user["user_id"])
    if df.empty:
        st.info("📭 No transactions yet. Go to the Home page and add some transactions first!")
        return
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    mask = (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)
    filtered_df = df[mask]
    if filtered_df.empty:
        st.info("📭 No transactions found for the selected date range.")
        return
    show_overview_analytics(filtered_df)
    show_pending_analytics(user["user_id"])


if __name__ == "__main__":
    main()
