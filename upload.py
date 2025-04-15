import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text  # Import text
from datetime import datetime

# Database credentials
DB_CONFIG = {
    'dbname': 'bidev',
    'user': 'avnadmin',
    'password': 'AVNS_LzxcmNp8sZ9AWhzDl10',
    'host': 'bidev-magicsync.f.aivencloud.com',
    'port': '25241'
}

def get_db_engine():
    db_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    return create_engine(db_url)

def data_page():
    st.title("NICE Data Tool")
    st.write(f"Welcome, {st.session_state['username']}!")
    
    # Add logout button
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.experimental_rerun()
    
    # Database connection
    engine = get_db_engine()
    
    # Hardcoded table names
    table_names = ['nutrition_budget', 'subcounty_reserves']
    
    # Create tabs
    tabs = st.tabs(["Download Template", "Upload Data"])
    
    # Tab 1: Preview Table and Download Template
    with tabs[0]:
        st.subheader("Preview of the selected table:")
        selected_table = st.selectbox("Select table:", [""] + table_names, key="download_select")
        
        if selected_table:
            with engine.connect() as conn:
                preview_query = text(f"SELECT * FROM raw.{selected_table} LIMIT 5")  # Wrap with text()
                preview_result = conn.execute(preview_query)
                preview_df = pd.DataFrame(preview_result.fetchall(), columns=preview_result.keys())
                st.write(preview_df)
            
            # Button to download template
            st.subheader("Download Template")
            download_filename = f"{selected_table}_template.csv"
            preview_df['create_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            preview_df['created_by'] = st.session_state['username']
            download_csv = preview_df.to_csv(index=False).encode()
            st.download_button(
                label="Download CSV Template",
                data=download_csv,
                file_name=download_filename,
                mime="text/csv"
            )
        else:
            st.info("Please select a table to preview.")
    
    # Tab 2: Upload Data
    with tabs[1]:
        st.subheader("Upload Data")
        st.text("Please select your file to start the upload process")
        
        if 'clicked' not in st.session_state:
            st.session_state.clicked = False
        
        if st.button('Upload File'):
            st.session_state.clicked = True
        
        uploaded_file = None
        if st.session_state.clicked:
            uploaded_file = st.file_uploader("Choose a file", type=['csv', 'xlsx'])
        
        if uploaded_file is not None:
            st.write("You selected the file:", uploaded_file.name)
            
            # Read the file into a DataFrame
            if uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            
            # Convert all columns to string and handle NaN
            df = df.astype(str)
            df.fillna(' ', inplace=True)
            
            # Add create_date and created_by columns
            df['create_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            df['created_by'] = st.session_state['username']
            
            st.subheader("Sample of the file:")
            st.write(df.head())
            
            # Select Table to Insert into
            st.title("Select Table to Update")
            selected_table = st.selectbox("Select table to insert into:", [""] + table_names, key="upload_select")
            
            if selected_table:
                with engine.connect() as conn:
                    columns_query = text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{selected_table}' AND table_schema = 'raw'")  # Wrap with text()
                    result = conn.execute(columns_query)
                    db_columns = [row[0] for row in result]
                
                # Map DataFrame column names to database column names
                column_mapping = {col: col for col in df.columns if col in db_columns}
                
                if st.button('Submit'):
                    connection = engine.raw_connection()
                    cursor = connection.cursor()
                    try:
                        # Truncate table before inserting new data
                        cursor.execute(f"TRUNCATE TABLE raw.{selected_table}")
                        
                        for _, row in df.iterrows():
                            row = row.apply(lambda x: '' if str(x).lower() == 'nan' else x)
                            columns = ', '.join(column_mapping[col] for col in row.index if col in column_mapping)
                            values = ', '.join(['%s'] * len([col for col in row.index if col in column_mapping]))
                            query = f"INSERT INTO raw.{selected_table} ({columns}) VALUES ({values})"
                            cursor.execute(query, [row[col] for col in row.index if col in column_mapping])
                        connection.commit()
                        st.write(" ✅ Records inserted successfully.")
                    except Exception as e:
                        connection.rollback()
                        st.error(f"🥺Oops! Error inserting records: {e}")
                    finally:
                        cursor.close()
                        connection.close()