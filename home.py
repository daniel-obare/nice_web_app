import streamlit as st
from login import login_page
from users import authenticate_user
from upload import data_page

# Set page configuration
st.set_page_config(
    page_title=' MagicSync',  page_icon='images/nice_favicon.ico'
)


def main():
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    
    if not st.session_state['logged_in']:
        login_page(authenticate_user)
    else:
        data_page()

if __name__ == "__main__":
    main()