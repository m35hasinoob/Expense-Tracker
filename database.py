from sqlalchemy import create_engine, Column, Integer, String, Float, Date, text
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash
from datetime import datetime


load_dotenv()

engine= create_engine(os.getenv("DB_connection_string"))

def load_catagories():
    with engine.connect() as conn:
        result= conn.execute(text("SELECT * FROM catagories"))
        categories=result.mappings().all()
        print("Categories loaded successfully")
        print(categories[0])
        return categories

def update_user_password(user_id, password):
    password_hash = generate_password_hash(password)
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET password_hash = :password_hash WHERE id = :user_id"),
            {"password_hash": password_hash, "user_id": user_id}
        )
        conn.commit()

def verify_user(email, password):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.mappings().first()
        if user:
            if user['password_hash'] is None:
                flash('Please set your password first')
                return None
            if check_password_hash(user['password_hash'], password):
                return user
        return None


def add_user_to_db(name, email, password):
    password_hash = generate_password_hash(password)
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO users (name, email, password_hash) VALUES (:name, :email, :password_hash)"),
            {"name": name, "email": email, "password_hash": password_hash}
        )
        conn.commit()
def load_users():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users"))
        users = result.mappings().all()
        print("Users loaded successfully", users)
        return users
    
def add_expense_to_db(title, user_id, catagory_id, amount, expense_date):
    with engine.connect() as conn:
        with conn.begin():
            # Insert expense
            result = conn.execute(
                text("INSERT INTO expenses (title, user_id, catagory_id, amount, expense_date) VALUES (:title, :user_id, :catagory_id, :amount, :expense_date)"),
                {"title": title, "user_id": user_id, "catagory_id": catagory_id, "amount": amount, "expense_date": expense_date}
            )
            expense_id = result.lastrowid
            # Create audit record 
            conn.execute(
                text("""INSERT INTO expense_audit 
                    (expense_id, action_type, new_amount, user_id)
                    VALUES (:expense_id, 'INSERT', :amount, :user_id)"""),
                {"expense_id": expense_id, "amount": amount, "user_id": user_id}
            )

def load_expenses():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM expense_details"))
        expenses = result.mappings().all()
        print("Expenses loaded successfully")
        return expenses
    
def load_user_details(user_id):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id})
        user_details = result.mappings().all()
        print("User details loaded successfully")
        return user_details
    

def dashboard():
    with engine.connect() as conn:
        result= conn.execute(text("""
            SELECT c.name AS category_name,
                   SUM(e.amount) AS total_amount
            FROM expenses e
            JOIN catagories c ON e.catagory_id = c.id
            
            GROUP BY c.name
        """),)
        dashboard_data = result.mappings().all()
        print("Dashboard data loaded successfully")
        return dashboard_data
    
def dashboard_by_month():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DATE_FORMAT(e.expense_date, '%Y-%m') AS month,
                   SUM(e.amount) AS total_amount
            FROM expenses e
            GROUP BY month
        """))
        monthly_data = result.mappings().all()
        print("Monthly dashboard data loaded successfully")
        return monthly_data
    
def edit_expense(expense_id, title, user_id, catagory_id, amount, expense_date):
    with engine.connect() as conn:
        with conn.begin():
            # Fetch old expense details for audit
            old_expense = conn.execute(
                text("SELECT * FROM expenses WHERE id = :id"),
                {"id": expense_id}
            ).mappings().first()
            
            conn.execute(
                text("""UPDATE expenses
                    SET title = :title, user_id = :user_id,
                        catagory_id = :catagory_id, amount = :amount,
                        expense_date = :expense_date
                    WHERE id = :expense_id"""),
                {"title": title, "user_id": user_id, "catagory_id": catagory_id,
                 "amount": amount, "expense_date": expense_date, "expense_id": expense_id}
            )
            # Create audit record for update
            conn.execute(
                text("""INSERT INTO expense_audit 
                    (expense_id, action_type, old_amount, new_amount, user_id)
                    VALUES (:expense_id, 'UPDATE', :old_amount, :new_amount, :user_id)"""),
                {"expense_id": expense_id, "old_amount": old_expense['amount'], 
                 "new_amount": amount, "user_id": user_id}
            )

def delete_expense(expense_id):
    with engine.connect() as conn:
        with conn.begin():
            # Fetch old expense details for audit
            old_expense = conn.execute(
                text("SELECT * FROM expenses WHERE id = :id"),
                {"id": expense_id}
            ).mappings().first()
            
            conn.execute(
                text("DELETE FROM expenses WHERE id = :expense_id"),
                {"expense_id": expense_id}
            )

            # Create audit record for delete
            conn.execute(
                text("""INSERT INTO expense_audit 
                    (expense_id, action_type, old_amount, user_id)
                    VALUES (:expense_id, 'DELETE', :old_amount, :user_id)"""),
                {"expense_id": expense_id, "old_amount": old_expense['amount'],
                 "user_id": old_expense['user_id']}
            )

def set_password_for_existing_user(email, password):
    password_hash = generate_password_hash(password)
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET password_hash = :password_hash WHERE email = :email"),
            {"password_hash": password_hash, "email": email}
        )
        conn.commit()

def load_expenses_by_user(user_id):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM expense_details WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        expenses = result.mappings().all()
        return expenses

def dashboard_by_user(user_id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.name AS category_name,
                   SUM(e.amount) AS total_amount
            FROM expenses e
            JOIN catagories c ON e.catagory_id = c.id
            WHERE e.user_id = :user_id
            GROUP BY c.name
        """), {"user_id": user_id})
        dashboard_data = result.mappings().all()
        return dashboard_data

def dashboard_by_month_user(user_id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DATE_FORMAT(e.expense_date, '%Y-%m') AS month,
                   SUM(e.amount) AS total_amount
            FROM expenses e
            WHERE e.user_id = :user_id
            GROUP BY month
            ORDER BY month
        """), {"user_id": user_id})
        monthly_data = result.mappings().all()
        return monthly_data

def dashboard_by_month(user_id):
    """Get monthly expense totals for a specific user."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DATE_FORMAT(expense_date, '%Y-%m') AS month,
                   SUM(amount) AS total_amount
            FROM expenses 
            WHERE user_id = :user_id
            GROUP BY month 
            ORDER BY month
        """), {"user_id": user_id})
        monthly_data = result.mappings().all()
        return monthly_data

def dashboard(user_id):
    """Get category-wise expense totals for a specific user."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.name AS category_name,
                   SUM(e.amount) AS total_amount
            FROM expenses e
            JOIN catagories c ON e.catagory_id = c.id
            WHERE e.user_id = :user_id
            GROUP BY c.name
        """), {"user_id": user_id})
        dashboard_data = result.mappings().all()
        return dashboard_data


def get_expense_audit(expense_id=None):
    with engine.connect() as conn:
        if expense_id:
            result = conn.execute(
                text("""
                    SELECT ea.*, u.name as user_name, e.title as expense_title
                    FROM expense_audit ea
                    JOIN users u ON ea.user_id = u.id
                    LEFT JOIN expenses e ON ea.expense_id = e.id
                    WHERE ea.expense_id = :expense_id
                    ORDER BY action_timestamp DESC
                """),
                {"expense_id": expense_id}
            )
        else:
            result = conn.execute(
                text("""
                    SELECT ea.*, u.name as user_name, e.title as expense_title
                    FROM expense_audit ea
                    JOIN users u ON ea.user_id = u.id
                    LEFT JOIN expenses e ON ea.expense_id = e.id
                    ORDER BY action_timestamp DESC
                """)
            )
        audit_data = result.mappings().all()
        return audit_data

def add_budget(user_id, category_id, amount, start_date, end_date):
    """Add a new budget for a category"""
    with engine.connect() as conn:
        conn.execute(
            text("""INSERT INTO budgets 
                (user_id, category_id, amount, start_date, end_date)
                VALUES (:user_id, :category_id, :amount, :start_date, :end_date)"""),
            {"user_id": user_id, "category_id": category_id, 
             "amount": amount, "start_date": start_date, "end_date": end_date}
        )
        conn.commit()

def get_user_budgets(user_id):
    """Get all budgets for a user with category names and spending"""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    b.id,
                    b.user_id,
                    b.category_id,
                    b.amount,
                    b.start_date,
                    b.end_date,
                    b.created_at,
                    c.name as category_name,
                    COALESCE(SUM(e.amount), 0) as spent_amount
                FROM budgets b
                JOIN catagories c ON b.category_id = c.id
                LEFT JOIN expenses e ON e.catagory_id = b.category_id 
                    AND e.user_id = b.user_id 
                    AND e.expense_date BETWEEN b.start_date AND b.end_date
                WHERE b.user_id = :user_id
                GROUP BY 
                    b.id,
                    b.user_id,
                    b.category_id,
                    b.amount,
                    b.start_date,
                    b.end_date,
                    b.created_at,
                    c.name
                ORDER BY b.end_date DESC
            """),
            {"user_id": user_id}
        )
        return result.mappings().all()

def delete_budget(budget_id, user_id):
    """Delete a budget (only if it belongs to the user)"""
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM budgets WHERE id = :budget_id AND user_id = :user_id"),
            {"budget_id": budget_id, "user_id": user_id}
        )
        conn.commit()



