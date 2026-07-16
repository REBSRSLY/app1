"""Small UI utilities shared across the app's sections."""

import streamlit as st


def section_header(title, purpose):
    st.title(title)
    st.caption(purpose)
    st.write("---")
