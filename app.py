from flask import Flask, render_template, request, session, redirect, url_for, flash
from functools import wraps

from database import add_expense_to_db, add_user_to_db, dashboard, dashboard_by_month, delete_expense, edit_expense, load_catagories, load_expenses, load_user_details, load_users, verify_user, set_password_for_existing_user, add_budget, get_user_budgets, delete_budget

def load_expenses_by_user(user_id):
    """Load expenses for a specific user."""
    all_expenses = load_expenses()
    return [expense for expense in all_expenses if expense.get('user_id') == user_id]


app = Flask(__name__)
app.secret_key = 'ABC1' 
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = verify_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('home'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        try:
            add_user_to_db(name, email, password)
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Email might already exist.')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    dashboard_data_by_month = dashboard_by_month(user_id)  
    dashboard_data = dashboard(user_id)
    
    categories = [row['category_name'] for row in dashboard_data]
    total_amounts = [row['total_amount'] for row in dashboard_data]
    months = [row['month'] for row in dashboard_data_by_month]
    amount_by_month = [row['total_amount'] for row in dashboard_data_by_month]
    
    return render_template('Home.html', 
                         categories=categories, 
                         total_amounts=total_amounts, 
                         month=months, 
                         amount_by_month=amount_by_month)

@app.route('/add_user',methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        user_data=request.form
        add_user_to_db(user_data['username'], user_data['email'])
        return render_template('add_user.html')
    return render_template('add_user.html')

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        title = request.form['expenseName']
        amount = request.form['expenseAmount']
        category_id = request.form['expenseCategory']
        expense_date = request.form['expenseDate']
        user_id = session.get('user_id')  
        
        add_expense_to_db(title, user_id, category_id, amount, expense_date)
        flash('Expense added successfully!', 'success')
        return redirect(url_for('view_expenses'))
    
    categories = load_catagories()
    return render_template('add_expense.html', cat=categories)

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense_page(expense_id):
    user_id = session.get('user_id')
    if request.method == 'POST':
        title = request.form['expenseName']
        amount = request.form['expenseAmount']
        category_id = request.form['expenseCategory']
        expense_date = request.form['expenseDate']
        
        edit_expense(expense_id, title, user_id, category_id, amount, expense_date)
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('view_expenses'))
    
    expense = next((e for e in load_expenses_by_user(user_id) if e['id'] == expense_id), None)
    if not expense:
        flash('Expense not found or unauthorized', 'error')
        return redirect(url_for('view_expenses'))
    
    categories = load_catagories()
    return render_template('edit_expense.html', expense=expense, cat=categories)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense_page(expense_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    expense = load_expenses_by_user(user_id)
    expense = next((e for e in expense if e['id'] == expense_id), None)
    
    if not expense:
        return "Unauthorized", 403
        
    delete_expense(expense_id)
    return redirect(url_for('view_expenses'))

@app.route('/view_expenses')
@login_required
def view_expenses():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    expenses = load_expenses_by_user(user_id)
    categories = load_catagories()
    users = load_users()
    user_map = {user['id']: user['name'] for user in users}
    
    return render_template('view_expenses.html', 
                         expenses=expenses, 
                         categories=categories, 
                         users=user_map)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            set_password_for_existing_user(email, password)
            flash('Password reset successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Password reset failed. Please try again.', 'error')
    return render_template('reset_password.html')

@app.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    user_id = session.get('user_id')
    if request.method == 'POST':
        category_id = request.form['category']
        amount = request.form['amount']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        try:
            add_budget(user_id, category_id, amount, start_date, end_date)
            flash('Budget added successfully!', 'success')
        except Exception as e:
            flash('Failed to add budget. Please try again.', 'error')
        
        return redirect(url_for('budgets'))
    
    budgets = get_user_budgets(user_id)
    categories = load_catagories()
    return render_template('budgets.html', budgets=budgets, categories=categories)

@app.route('/delete_budget/<int:budget_id>', methods=['POST'])
@login_required
def delete_budget_route(budget_id):
    user_id = session.get('user_id')
    delete_budget(budget_id, user_id)
    flash('Budget deleted successfully!', 'success')
    return redirect(url_for('budgets'))

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0")