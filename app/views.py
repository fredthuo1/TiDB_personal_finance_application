from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
import requests
from dotenv import load_dotenv
from flask_login import login_required, current_user
from .models import Note, Transactions
from .forms import CSVUploadForm
from sqlalchemy import func
from datetime import datetime
import os
from requests.auth import HTTPDigestAuth
import csv
import io
from . import db
import json
from datetime import datetime
from calendar import monthrange
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

load_dotenv()

views = Blueprint('views', __name__)

public_key = os.getenv('PUBLIC_KEY')
private_key = os.getenv('PRIVATE_KEY')

class MonthYearForm(FlaskForm):
    month_year = StringField('Month and Year')
    submit = SubmitField('Submit')

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    return render_template("home.html", user=current_user)


@views.route('/delete-note', methods=['POST'])
def delete_note():  
    note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

    return jsonify({})


@views.route('/transactions', methods=['GET'])
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search_term', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    url = 'https://eu-central-1.data.tidbcloud.com/api/v1beta/app/dataapp-NklHdJgE/endpoint/transactions'
    headers = {
        'Authorization': 'Bearer 0WMwUpuq:93e911c1-575f-4352-8e89-4151f9e4dcce',
    }
    response = requests.get(url, auth=HTTPDigestAuth(public_key, private_key))

    if response.status_code == 200:
        try:
            raw_transactions = response.json()['data']['rows']
            transactions = []
            for raw_transaction in raw_transactions:
                transaction = raw_transaction.copy()
                transaction['date'] = datetime.strptime(transaction['date'], '%Y-%m-%d %H:%M:%S')
                transactions.append(transaction)
        except json.JSONDecodeError:
            print("Decoding JSON has failed")
            transactions = []
    else:
        print(f"Request failed with status code {response.status_code}")
        transactions = []  # default value in case of failure

    if search_term:
        transactions = [t for t in transactions if search_term.lower() in t['description'].lower()]

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        transactions = [t for t in transactions if t['date'].date() >= start_date]

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        transactions = [t for t in transactions if t['date'].date() <= end_date]

    return render_template('transactions.html', user=current_user, transactions=transactions)

@views.route('/income', methods=['GET'])
@login_required
def income():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search_term', '')
    start_date_str = request.args.get('start_date', '')


    url = 'https://eu-central-1.data.tidbcloud.com/api/v1beta/app/dataapp-NklHdJgE/endpoint/income'
    headers = {
        'Authorization': 'Bearer 0WMwUpuq:93e911c1-575f-4352-8e89-4151f9e4dcce',
    }
    response = requests.get(url, auth=HTTPDigestAuth(public_key, private_key))

    if response.status_code == 200:
        try:
            raw_transactions = response.json()['data']['rows']
            transactions = []
            for raw_transaction in raw_transactions:
                transaction = raw_transaction.copy()
                transaction['date'] = datetime.strptime(transaction['date'], '%Y-%m-%d %H:%M:%S')
                transactions.append(transaction)
        except json.JSONDecodeError:
            print("Decoding JSON has failed")
            transactions = []
    else:
        print(f"Request failed with status code {response.status_code}")
        transactions = []  # default value in case of failure

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m').date()
        end_date = start_date.replace(day=monthrange(start_date.year, start_date.month)[1])  # get last day of the month
        transactions = [t for t in transactions if start_date <= t['date'].date() <= end_date]

    if search_term:
        transactions = [t for t in transactions if search_term.lower() in t['description'].lower()]

    return render_template('income.html', user=current_user, transactions=transactions)

def str_to_bool(s):
    if s == 'true':
         return True
    elif s == 'false':
         return False
    else:
         raise ValueError

def str_to_date(s):
    return datetime.strptime(s, "%m/%d/%y")  # change to the format of your date string if it's different

@views.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_csv():
    form = CSVUploadForm()

    if form.validate_on_submit():
        csv_file = form.csv_file.data
        stream = io.StringIO(csv_file.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input)  # This skips the header row

        # Query for the last used id
        last_id_query = db.session.query(func.max(Transactions.id)).scalar()
        if last_id_query is None:
            last_id = 0
        else:
            last_id = last_id_query

        for row in csv_input:
            last_id += 1  # increment the id for each new row
            transactions = Transactions(
                id=last_id,
                date=str_to_date(row[0]),  # convert the date string to a datetime object
                description=row[1],
                original_description=row[2],
                amount=row[3],
                type=row[4],
                parent_category=row[5],
                category=row[6],
                account=row[7],
                tags=row[8],
                memo=row[9],
                pending=str_to_bool(row[10])  # call the conversion function
            )
            db.session.add(transactions)

        db.session.commit()
        
        return redirect(url_for('views.transactions'))

    return render_template('upload_csv.html', form=form, user=current_user)

@views.route('/transactions_by_category', methods=['GET', 'POST'])
@login_required
def transactions_by_category():
    form = MonthYearForm()

    categories = []
    total_amounts = []
    total_expenditure = 0
    total_income = 0
    transactions_by_category = []
    total_savings = 0  # Add this line to initialize savings

    if form.validate_on_submit():
        month_year = form.month_year.data  # the month and year from the form

        # now convert this to a string in the required format
        date_str = datetime.strptime(month_year, '%Y-%m').strftime('%Y-%m-%d %H:%M:%S')

        url = 'https://eu-central-1.data.tidbcloud.com/api/v1beta/app/dataapp-NklHdJgE/endpoint/transactions_by_category'
        headers = {
            'Authorization': 'Bearer 0WMwUpuq:93e911c1-575f-4352-8e89-4151f9e4dcce',
        }
        response = requests.get(url, auth=HTTPDigestAuth(public_key, private_key), params={'date': date_str})
        print(response.json())
        if response.status_code == 200:
            try:
                raw_data = response.json()['data']['rows']
                for item in raw_data:
                    transactions_by_category.append(item)
                    categories.append(item['category'])
                    total_amounts.append(item['total_amount'])
                    if item['category'] == 'Income':
                        total_income += float(item['total_amount'])
                    else:
                        total_expenditure += float(item['total_amount'])

            except json.JSONDecodeError:
                print("Decoding JSON has failed")
                transactions_by_category = []

            total_savings = total_income - total_expenditure  # Add this line to calculate savings

        else:
            print(f"Request failed with status code {response.status_code}")
            transactions_by_category = []  # default value in case of failure

    return render_template('transactions_by_category.html', user=current_user, 
                        transactions=transactions_by_category, 
                        categories=categories, 
                        total_amounts=total_amounts,
                        total_expenditure=total_expenditure, 
                        total_income=total_income, 
                        total_savings=total_savings,  # Add this line to send savings to the template
                        form=form)

@views.route('/transactions_by_parent_category', methods=['GET', 'POST'])
@login_required
def transactions_by_parent_category():
    form = MonthYearForm()

    transactions_by_parent_category = []
    categories = []
    total_amounts = []
    total_expenditure = 0
    total_income = 0
    total_savings = 0  # Add this line to initialize savings

    if form.validate_on_submit():
        month_year = form.month_year.data  # the month and year from the form

        # now convert this to a string in the required format
        date_str = datetime.strptime(month_year, '%Y-%m').strftime('%Y-%m-%d %H:%M:%S')

        url = 'https://eu-central-1.data.tidbcloud.com/api/v1beta/app/dataapp-NklHdJgE/endpoint/transactions_by_category_dump_JGipPA'
        headers = {
            'Authorization': 'Bearer 0WMwUpuq:93e911c1-575f-4352-8e89-4151f9e4dcce',
        }
        response = requests.get(url, auth=HTTPDigestAuth(public_key, private_key), params={'date': date_str})
        print(response.json())
        if response.status_code == 200:
            try:
                raw_data = response.json()['data']['rows']
                for item in raw_data:
                    transactions_by_parent_category.append(item)
                    categories.append(item['parent_category'])
                    total_amounts.append(item['total_amount'])
                    if item['parent_category'] == 'Income':
                        total_income += float(item['total_amount'])
                    else:
                        total_expenditure += float(item['total_amount'])
            except json.JSONDecodeError:
                print("Decoding JSON has failed")

            total_savings = total_income - total_expenditure  # Add this line to calculate savings

    return render_template('transactions_by_parent_category.html', user=current_user, 
                           transactions=transactions_by_parent_category,
                           categories=categories, 
                           total_amounts=total_amounts,
                           total_expenditure=total_expenditure, 
                           total_income=total_income, 
                           total_savings=total_savings,  # Add this line to send savings to the template
                           form=form)

@views.route('/by_category_parent_year_to_date', methods=['GET', 'POST'])
@login_required
def by_category_parent_year_to_date():
    form = MonthYearForm()

    by_category_parent_year_to_date = []
    categories = []
    total_amounts = []
    total_expenditure = 0
    total_income = 0
    total_savings = 0  # Add this line to initialize savings

    url = 'https://eu-central-1.data.tidbcloud.com/api/v1beta/app/dataapp-NklHdJgE/endpoint/by_category_parent_year_to_date'
    headers = {
        'Authorization': 'Bearer 0WMwUpuq:93e911c1-575f-4352-8e89-4151f9e4dcce',
    }
    response = requests.get(url, auth=HTTPDigestAuth(public_key, private_key))
    print(response.json())
    if response.status_code == 200:
        try:
            raw_data = response.json()['data']['rows']
            for item in raw_data:
                by_category_parent_year_to_date.append(item)
                categories.append(item['parent_category'])
                total_amounts.append(item['total_amount'])
                if item['parent_category'] == 'Income':
                    total_income += float(item['total_amount'])
                else:
                    total_expenditure += float(item['total_amount'])
        except json.JSONDecodeError:
            print("Decoding JSON has failed")

        total_savings = total_income - total_expenditure  # Add this line to calculate savings

    return render_template('by_category_parent_year_to_date.html', user=current_user, 
                           transactions=by_category_parent_year_to_date,
                           categories=categories, 
                           total_amounts=total_amounts,
                           total_expenditure=total_expenditure, 
                           total_income=total_income, 
					    total_savings=total_savings,  # Add this line to send savings to the template
                           form=form)


