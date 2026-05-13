import streamlit as st
import pandas as pd
import sqlite3
import re
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# ---------------- CONFIG ---------------- #
st.set_page_config(page_title="AI Data Analyst Bot (SQL)", layout="wide")
st.title("📊 AI Data Analyst Bot (SQL)")

# ---------------- LOAD API ---------------- #
load_dotenv()

# Ensure you have GROQ_API_KEY set in your environment variables or .env file
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile"
)

# ---------------- CLEAN CODE ---------------- #
def clean_sql(text):
    # Remove markdown code block tags
    text = re.sub(r"```sql", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

# ---------------- FILE UPLOAD ---------------- #
file = st.file_uploader("Upload CSV", type=["csv"])

if file:
    df = pd.read_csv(file)

    st.subheader("📄 Data Preview")
    st.dataframe(df.head())

    # Initialize SQLite in-memory database
    conn = sqlite3.connect(':memory:')
    
    # Write dataframe to SQL table
    table_name = "data_table"
    df.to_sql(table_name, conn, if_exists='replace', index=False)

    # Get schema information
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    schema_info = cursor.fetchall()
    columns_with_types = {col[1]: col[2] for col in schema_info}

    question = st.text_input("Ask a question about your data (e.g., 'SELECT ...')")

    if question:
        # Prompt for Text-to-SQL
        prompt = f"""
You are a senior SQL data analyst.
Database: SQLite
Table Name: {table_name}
Columns and Types: {columns_with_types}

Write ONLY the valid, executable SQL query to answer the user's question based on the table schema.

Rules:
- Do not use markdown backticks (e.g. ```sql).
- Do not add any explanation or conversational text.

Question: {question}
"""

        response = llm.invoke(prompt)
        sql_query = clean_sql(response.content)

        st.subheader("🧠 Generated SQL Query")
        st.code(sql_query, language="sql")

        # 📊 EXECUTION & VISUALIZATION
        try:
            # Execute the SQL query directly into a Pandas DataFrame
            result_df = pd.read_sql_query(sql_query, conn)

            # Display Answer
            st.subheader("📊 Answer")
            st.dataframe(result_df)

            # Visualization Attempt
            st.subheader("📈 Visualization")
            if not result_df.empty:
                # If the result has two or more columns, try to plot the first two as categorical and numeric
                if result_df.shape[1] >= 2:
                    # Let's clean up column names just in case
                    result_df.columns = ['Category', 'Value'] if result_df.shape[1] == 2 else result_df.columns
                    
                    # Try to convert the second column to numeric
                    try:
                        result_df.iloc[:, 1] = pd.to_numeric(result_df.iloc[:, 1])
                        # Set index as the first column for the bar chart
                        chart_data = result_df.set_index(result_df.columns[0])
                        st.bar_chart(chart_data)
                    except Exception:
                        st.info("The output data could not be automatically plotted.")
                else:
                    st.info("Query results do not contain enough dimensions for plotting.")
            else:
                st.warning("The query returned no results.")

        except Exception as e:
            st.error(f"Execution Error: {e}")

    # Close connection when done
    conn.close()