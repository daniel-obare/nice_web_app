import streamlit as st

def login_page(authenticate_user):
    # Embed image directly in HTML so CSS applies
    st.markdown(
        """
        <style>
            .image-container {
                text-align: center;
                margin-bottom: 20px;
            }
            .image-container img {
                border-radius: 50%;
                width: 300px;
                height: 300px;
                object-fit: cover;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
        </style>
        <div class="image-container">
            <img src="images/invent.jpg" alt="Rounded Image">
        </div>
        """,
        unsafe_allow_html=True
    )

    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.success(f"Welcome {username}!")
            st.experimental_rerun()
        else:
            st.error("Incorrect username or password")
