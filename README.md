# 🛒 E-Commerce Analytics Project

## 📌 Overview

This project is a complete end-to-end E-Commerce Analytics pipeline built using Python, PostgreSQL, SQLAlchemy, and Streamlit.

It transforms raw datasets into meaningful insights through data cleaning, database storage, and visualization.

---

## 🧠 Problem Statement

Raw e-commerce data is often messy, inconsistent, and spread across multiple files.
This project solves that by:

* Cleaning and standardizing data
* Merging multiple datasets
* Enabling SQL-based analytics
* Visualizing insights using a dashboard

---

## ⚙️ How to Use This Project

### Step 1: Download Raw Data

* Download dataset from the provided Google Drive link
* Place all files inside the `raw_data/` folder

---

### Step 2: Install Requirements

pip install -r requirements.txt

---

### Step 3: Run Data Cleaning Pipeline

* Go to `cleaning_code_ques/` folder
* Run all notebooks/scripts one by one

This will:

* Clean individual datasets
* Merge them into a final dataset

---

### Step 4: Setup Database for EDA

Run this in PostgreSQL:
CREATE DATABASE amazon_eda;

Use this database for running EDA (`eda.ipynb`)

---

### Step 5: Configure Environment Variables

Create a `.env` file using `.env.example` as reference:

DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecommerce_analytics
DB_USER=postgres
DB_PASSWORD=your_password

---

### Step 6: Setup Application Database

Run:
CREATE DATABASE ecommerce_analytics;

Then load data:
python load_data.py

This will load cleaned data into PostgreSQL tables.

---

### Step 7: Run Streamlit Application

streamlit run app.py

---

### Step 8: View Results

* Data is stored in PostgreSQL
* Insights are visible in the Streamlit dashboard

---

## 📊 Project Workflow

Raw Data → Cleaning → Merging → PostgreSQL → SQL Analysis → Streamlit Dashboard

---

## 📊 Key Insights

* Revenue trends across years
* Category-wise performance
* Customer behavior analysis
* Payment method trends
* Festival impact on sales

---

## 🧱 Project Structure

cleaned_data/              - Cleaned datasets
cleaning_code_ques/        - Data cleaning scripts
raw_data/                  - Raw datasets
app.py                     - Streamlit dashboard
eda.ipynb                  - Analysis
load_data.py               - Data loading pipeline
schema.sql                 - Database schema
.env                       - Local config (not pushed)
.env.example               - Template config
requirements.txt           - Dependencies
README.md                  - Documentation

---

## 🧠 Tech Stack

* Python (Pandas, NumPy)
* PostgreSQL
* SQLAlchemy
* Streamlit

---

## 🚀 Future Improvements

* Optimize schema and datatypes
* Add indexing for faster queries
* Improve dashboard UI
* Deploy application online

---

## 👤 Author

Rama Sekar
