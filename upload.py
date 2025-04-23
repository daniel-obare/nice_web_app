import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import re, os
from dotenv import load_dotenv
load_dotenv()

# Database credentials
DB_CONFIG = {
    'dbname': os.getenv('dbname'),
    'user': os.getenv('user'),
    'password': os.getenv('password'),
    'host': os.getenv('host'),
    'port': os.getenv('port')
}

def get_db_engine():
    db_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    return create_engine(db_url)

def to_snake_case(name):
    """Convert a string to lowercase snake_case."""
    name = re.sub(r'[\s-]+', '_', name)  # Replace spaces or hyphens with underscore
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name)  # Add underscore before capital letters
    return name.lower()  # Convert to lowercase

def fetch_table_names(engine):
    try:
        with engine.connect() as conn:
            query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'")
            result = conn.execute(query)
            table_names = [row[0] for row in result]
            return sorted(table_names)  # Sort for consistent display
    except Exception as e:
        st.error(f"Error fetching table names: {e}")
        return []

def data_page():
    st.title("NICE Data Tool")
    st.write(f"Welcome, {st.session_state['username']}!")
    
    # Add logout button
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
    
    # Database connection
    engine = get_db_engine()
    
    # Fetch table names dynamically
    table_names = fetch_table_names(engine)
    
    # Create tabs
    tabs = st.tabs(["Download Template", "Upload Data", "Create New Table"])
    
    # Tab 1: Preview Table and Download Template
    with tabs[0]:
        st.subheader("Preview of the selected table:")
        selected_table = st.selectbox("Select table:", [""] + table_names, key="download_select")
        
        if selected_table:
            with engine.connect() as conn:
                preview_query = text(f"SELECT * FROM raw.{selected_table} LIMIT 5")
                preview_result = conn.execute(preview_query)
                preview_df = pd.DataFrame(preview_result.fetchall(), columns=preview_result.keys())
                st.write(preview_df)
            
            # Button to download template
            st.subheader("Download Template")
            download_filename = f"{selected_table}_template.csv"
            preview_df['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
            
            # Read the file into a DataFrame with progress bar
            progress_bar = st.progress(0)
            with st.spinner("⏳ Reading file..."):
                if uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    df = pd.read_excel(uploaded_file)
                else:
                    df = pd.read_csv(uploaded_file)
                progress_bar.progress(0.5)  # Update progress after reading
                
                # Convert column names to lowercase snake_case
                df.columns = [to_snake_case(col) for col in df.columns]
                
                # Convert all columns to string and handle NaN
                df = df.astype(str)
                df.fillna(' ', inplace=True)
                # Add created_date and created_by columns
                df['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                df['created_by'] = st.session_state['username']
                progress_bar.progress(1.0)  # Complete progress after processing
            
            st.subheader("Sample of the file:")
            st.write(df.head())
            
            # Select Table to Insert into
            st.title("Select Table to Update")
            selected_table = st.selectbox("Select table to insert into:", [""] + table_names, key="upload_select")
            
            if selected_table:
                with engine.connect() as conn:
                    columns_query = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{selected_table}' AND table_schema = 'raw'
                    """)
                    result = conn.execute(columns_query)
                    db_columns = [row[0] for row in result]

                # Check for column mismatch
                df_columns = df.columns.tolist()
                missing_cols = [col for col in df_columns if col not in db_columns]

                if missing_cols:
                    st.error(f"🚫 Column mismatch! The following columns are not in the database table '{selected_table}': {missing_cols}")
                else:
                    # Proceed with data insertion only if all columns match
                    column_mapping = {col: col for col in df_columns}

                    if st.button('Submit'):
                        connection = engine.raw_connection()
                        cursor = connection.cursor()
                        progress_bar = st.progress(0)
                        try:
                            # Truncate table before inserting new data
                            cursor.execute(f"TRUNCATE TABLE raw.{selected_table}")
                            
                            total_rows = len(df)
                            for idx, (_, row) in enumerate(df.iterrows()):
                                row = row.apply(lambda x: '' if str(x).lower() == 'nan' else x)
                                columns = ', '.join(column_mapping[col] for col in row.index if col in column_mapping)
                                values = ', '.join(['%s'] * len([col for col in row.index if col in column_mapping]))
                                query = f"INSERT INTO raw.{selected_table} ({columns}) VALUES ({values})"
                                cursor.execute(query, [row[col] for col in row.index if col in column_mapping])
                                progress_bar.progress((idx + 1) / total_rows)
                            connection.commit()
                            st.write("✅ Records inserted successfully.")
                            # Reset session state and reload page
                            st.session_state.clicked = False
                            st.rerun()
                        except Exception as e:
                            connection.rollback()
                            st.error(f"🥺Oops! Error inserting records: {e}")
                        finally:
                            cursor.close()
                            connection.close()
                            progress_bar.empty()  # Clear progress bar

    # Tab 3: Create New Table from Data
    with tabs[2]:
        st.subheader("Create a New Table from Data")
        st.text("Please upload a file to create a new table automatically.")
        
        uploaded_new_file = st.file_uploader("Choose a file", type=['csv', 'xlsx'], key="new_table_upload")
        
        if uploaded_new_file:
            st.write("You selected the file:", uploaded_new_file.name)
            
            # Read the new file into a DataFrame with progress bar
            progress_bar = st.progress(0)
            with st.spinner("⏳ Reading file..."):
                if uploaded_new_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    new_df = pd.read_excel(uploaded_new_file)
                else:
                    new_df = pd.read_csv(uploaded_new_file)
                progress_bar.progress(0.5)  # Update progress after reading
                
                # Convert all columns to string and handle NaN
                new_df = new_df.astype(str)
                new_df.fillna(' ', inplace=True)
                # Add created_date and created_by columns
                new_df['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_df['created_by'] = st.session_state['username']
                progress_bar.progress(1.0)  # Complete progress after processing
            
            st.subheader("Sample of the file:")
            st.write(new_df.head())
            
            # Input for new table name
            new_table_name = st.text_input("Enter the new table name (lowercase, no spaces):", key="new_table_name")
            
            if new_table_name:
                if new_table_name in table_names:
                    st.error(f"🚫 Table '{new_table_name}' already exists.")
                elif st.button("Create Table and Upload Data"):
                    with st.spinner("⏳ Creating table and inserting data..."):
                        progress_bar = st.progress(0)
                        try:
                            with engine.begin() as conn:
                                # Convert DataFrame columns to lowercase snake_case and create column definitions
                                column_defs = ", ".join([f"{to_snake_case(col)} TEXT" for col in new_df.columns if col not in ['created_date', 'created_by']])
                                # Add created_date and created_by columns explicitly in that order
                                column_defs = f"{column_defs}, created_date TEXT, created_by TEXT" if column_defs else "created_date TEXT, created_by TEXT"
                                create_table_sql = text(f"""
                                    CREATE TABLE raw.{new_table_name} (
                                        {column_defs}
                                    )
                                """)
                                conn.execute(create_table_sql)
                            progress_bar.progress(0.3)  # Update after table creation

                            connection = engine.raw_connection()
                            cursor = connection.cursor()
                            total_rows = len(new_df)
                            for idx, (_, row) in enumerate(new_df.iterrows()):
                                row = row.apply(lambda x: '' if str(x).lower() == 'nan' else x)
                                columns = ', '.join([to_snake_case(col) if col not in ['created_date', 'created_by'] else col for col in new_df.columns])
                                values = ', '.join(['%s'] * len(new_df.columns))
                                query = f"INSERT INTO raw.{new_table_name} ({columns}) VALUES ({values})"
                                cursor.execute(query, [row[col] for col in new_df.columns])
                                progress_bar.progress(0.3 + 0.7 * (idx + 1) / total_rows)  # Incremental progress
                            connection.commit()
                            st.success(f"✅ Table 'raw.{new_table_name}' created and data inserted successfully.")
                            # Reload page
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error occurred: {e}")
                        finally:
                            cursor.close()
                            connection.close()
                            progress_bar.empty()  # Clear progress bar