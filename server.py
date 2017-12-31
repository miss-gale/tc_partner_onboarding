from flask import Flask, request, redirect, render_template, session, flash
from mysqlconnection import MySQLConnector

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import smtplib

app = Flask(__name__)
app.secret_key = "ThisIsSomethingSuperSecret"
mysql = MySQLConnector(app,"tc_partner_onboarding_db")

import re
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9\.\+_-]+@[a-zA-Z0-9\._-]+\.[a-zA-Z]*$')

# -------------------------------------------
# Base Route
@app.route('/')
def index():
    return render_template('index.html')

# -------------------------------------------
#
@app.route('/process', methods=['POST'])
def process():

    if request.form['action'] == "register":

        # ------------------------------------------------
        # Create the new user
        new_user_query = "INSERT INTO users (first_name, last_name, email, password) VALUES (:first_name_injestion, :last_name_injestion, :email_injestion, :password_injestion)"
        new_user_data = {
            # ------------------------------------------------
            # Need to add form validation
            "first_name_injestion": request.form['first_name'],
            "last_name_injestion": request.form['last_name'],
            "company_name_injestion": request.form['company_name'],
            "email_injestion": request.form['email'],
            # ------------------------------------------------
            # Need to encrypt password
            "password_injestion": request.form['password']
            }
        new_user = mysql.query_db(new_user_query, new_user_data)
        flash("New user created!")

        # ------------------------------------------------
        # Create the new partner
        new_partner_query = "INSERT INTO partners (company_name, partner_type) VALUES (:company_name_injestion, :partner_type_injestion)"
        new_partner_data = {
            "company_name_injestion": request.form['company_name'],
            "partner_type_injestion": request.form['partner_type']
            }
        new_partner = mysql.query_db(new_partner_query, new_partner_data)
        flash("New partner created!")
        return redirect('/')

    elif request.form['action'] == "login":
        user_query = "SELECT * FROM users WHERE email = :provided_email"
        user_data = {
            'provided_email': request.form['email']
        }
        find_user = mysql.query_db(user_query, user_data)
        if len(find_user) == 0:
            flash("Hey, this doesnt seem to be a real username. Want to try again?")
            return redirect('/')
        else:
            get_user = find_user[0]
            if get_user['password'] == request.form['password']:
                session['id'] = get_user['user_id']
                company_query = "SELECT * FROM partners WHERE partner_id = :session_id"
                company_data = {
                    'session_id': get_user['user_id']
                }
                get_company = mysql.query_db(company_query, company_data)
                return render_template('intake_form.html', current_user=get_user, current_company=get_company[0])
            else:
                flash("The password is not correct.")
                return redirect('/')
        print("Could not located stored user information. Please login and try again.")
        return redirect('/')

# -------------------------------------------
# Process the Intake Form
@app.route('/submit', methods=['POST'])
def submit():

    # -------------------------------------------
    # Store product details in db
    product_query = "INSERT INTO products (reward_name, reward_type, currency, denom_type, min_load_value, max_load_value, fixed_amounts, expiration_period) VALUES (:reward_name_injection, :reward_type_injection, :currency_injection, :denom_type_injection, :min_load_value_injection, :max_load_value_injection, :fixed_amounts_injection, :expiration_period_injection)"
    product_data = {
        # ------------------------------------------------
        # Need to add form validation
        "reward_name_injection": request.form['reward_name'],
        "reward_type_injection": request.form['reward_type'],
        "currency_injection": request.form['currency'],
        "denom_type_injection": request.form['denom_type'],
        "min_load_value_injection": request.form['min_load_value'],
        "max_load_value_injection": request.form['max_load_value'],
        "fixed_amounts_injection": request.form['fixed_amounts'],
        "expiration_period_injection": request.form['expiration_period']
    }
    new_product = mysql.query_db(product_query, product_data)

    # -------------------------------------------
    # Store code details in db
    code_details_query = "INSERT INTO code_details (code_format, code_label, code_sample) VALUES (:code_format_injection, :code_label_injection, :code_sample_injection)"
    code_details_data = {
        "code_format_injection": request.form['code_format'],
        "code_label_injection": request.form['code_label'],
        "code_sample_injection": request.form['code_sample']
    }
    new_code_details = mysql.query_db(code_details_query, code_details_data)

    # -------------------------------------------
    # Store guideline details in db
    guidelines_query = "INSERT INTO guidelines (short_description, long_description, redemption_types, redemption_instructions, terms_conditions, disclaimer) VALUES (:short_description_injection, :long_description_injection, :redemption_types_injection, :redemption_instructions_injection, :terms_conditions_injection, :promotional_disclaimer_injection)"
    guidelines_data = {
        "short_description_injection": request.form['short_description'],
        "long_description_injection": request.form['long_description'],
        "redemption_types_injection": request.form['redemption_types'],
        "redemption_instructions_injection": request.form['redemption_instructions'],
        "terms_conditions_injection": request.form['terms_conditions'],
        "promotional_disclaimer_injection": request.form['promotional_disclaimer']
    }
    new_guidelines = mysql.query_db(guidelines_query, guidelines_data)


    get_product_query = "SELECT * FROM products WHERE product_id = :product_id_injection"
    get_product_data = {
        "product_id_injection": session['id']
        }
    get_product = mysql.query_db(get_product_query, get_product_data)

    get_code_details_query = "SELECT * FROM code_details WHERE code_detail_id = :code_details_id_injection"
    get_code_details_data = {
        "code_details_id_injection": session['id']
        }
    get_code_details = mysql.query_db(get_code_details_query, get_code_details_data)

    get_guidelines_query = "SELECT * FROM guidelines WHERE guideline_id = :guideline_id_injection"
    get_guideline_data = {
        "guideline_id_injection": session['id']
        }
    get_guidelines = mysql.query_db(get_guidelines_query, get_guideline_data)

    return render_template('completed_form.html', current_product=get_product[0], current_code_details=get_code_details[0], current_guidelines=get_guidelines[0])


# -------------------------------------------
#
@app.route('/mail_form', methods=['POST'])
def mail_form():

    get_current_user_query = "SELECT * FROM users WHERE users.user_id = :user_id_injection"
    get_current_user_data = {
        "user_id_injection": session['id']
        }
    get_current_user = mysql.query_db(get_current_user_query, get_current_user_data)
    current_user = get_current_user[0]
    current_email = current_user['email']
    current_user_name = current_user['first_name'] + " " + current_user['last_name']

    get_current_reward_info_query = "SELECT * FROM products WHERE products.product_id = :product_id_injection"
    get_current_reward_info_data = {
        "product_id_injection": session['id']
        }
    current_reward_info = mysql.query_db(get_current_reward_info_query, get_current_reward_info_data)
    current_reward = current_reward_info[0]

    fromaddr = current_email
    toaddr = "lindsay@tangocard.com"
    msg = MIMEMultipart()
    msg['From'] = current_user_name
    msg['To'] = "Lindsay Gale"
    msg['Subject'] = "Here's a New Partner Intake Form"
    body = "Reward Name: " + current_reward['reward_name'] + "\n" \
            "Reward Type: " + current_reward['reward_type'] + "\n" \
            "Currency: " + current_reward['currency'] + "\n" \
            "Denomination Type: " + current_reward['denom_type'] + "\n" \
            "Minimum Load Value: " + current_reward['min_load_value'] + "\n" \
            "Maximum Load Value: " + current_reward['max_load_value'] + "\n" \
            "Fixed Amounts: " + current_reward['fixed_amounts'] + "\n" \
            "Expiration Period: " + current_reward['expiration_period']
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login("buckle.everest@gmail.com", "FuckBuckle!")
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)

    flash("Thank you! Your form has been submitted to partnerships@tangocard.com.")
    return redirect('/')


# -------------------------------------------
#
@app.route('/log_out', methods=['POST'])
def log_out():
    session['id'] = ""
    return redirect('/')


app.run(debug=True)
