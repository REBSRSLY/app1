"""Piccole utility di UI condivise tra le sezioni dell'app."""

import streamlit as st


def section_header(title, purpose):
    st.title(title)
    st.caption(purpose)
    st.write("---")
