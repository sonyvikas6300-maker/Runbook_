import streamlit as st
from sf_conn import create_snowflake_connection, extract_metadata
from code_generator import *
from docx import Document
import tempfile
import os

st.title("Runbook Generator")

# ---------------- LOGIN ---------------- #
account = st.text_input("Account")
user = st.text_input("User")
password = st.text_input("Password", type="password")
mfa = st.text_input("MFA")

if st.button("Connect"):
    conn = create_snowflake_connection(account, user, password, mfa)
    st.session_state.conn = conn
    st.success("Connected to Snowflake")

# ---------------- MAIN ---------------- #
if "conn" in st.session_state:
    conn = st.session_state.conn
    cursor = conn.cursor()

    cursor.execute("SHOW DATABASES")
    dbs = [d[1] for d in cursor.fetchall()]
    db = st.selectbox("Database", dbs)

    cursor.execute(f"SHOW SCHEMAS IN {db}")
    schemas = [s[1] for s in cursor.fetchall()]
    schema = st.selectbox("Schema", schemas)

    cursor.execute(f"SHOW TABLES IN {db}.{schema}")
    tables = [t[1] for t in cursor.fetchall()]
    table = st.selectbox("Table", tables)

    # -------- LAYER MAP -------- #
    st.subheader("Layer DB Mapping")

    layer_map = {
        "bronze": st.text_input("Bronze DB", value=db),
        "silver": st.text_input("Silver DB", value=db),
        "gold": st.text_input("Gold DB", value=db)
    }

    # -------- METADATA -------- #
    if st.button("Get Metadata"):
        metadata = extract_metadata(conn, table, layer_map)
        st.session_state.metadata = metadata

        st.subheader("Bronze")
        st.json(metadata["bronze"])

        st.subheader("Silver")
        st.json(metadata["silver"])

        st.subheader("Gold")
        st.json(metadata["gold"])

# ---------------- FILE ---------------- #
uploaded = st.file_uploader("Upload DOCX")

if uploaded and "metadata" in st.session_state:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    if st.button("Generate Runbook"):
        metadata = st.session_state.metadata

        # READ
        b, s, g = read_docx_sections(path)

        # CLEAN
        b = clean_sql(b)
        s = clean_sql(s)
        g = clean_sql(g)

        # MINIMIZE METADATA
        b_meta = minimize_metadata(metadata["bronze"])
        s_meta = minimize_metadata(metadata["silver"])
        g_meta = minimize_metadata(metadata["gold"])

        st.write("Generating SQL Layer-wise...")

        # CHUNK PROCESS
        b_new = update_single_layer_sql(b, b_meta)
        s_new = update_single_layer_sql(s, s_meta)
        g_new = update_single_layer_sql(g, g_meta)

        # UPDATE DOC
        doc = Document(path)
        doc = replace_content(doc, b_new, s_new, g_new)

        output = f"{metadata['table_name']}_updated.docx"
        doc.save(output)

        with open(output, "rb") as f:
            st.download_button("Download Runbook", f, output)

        os.remove(path)
