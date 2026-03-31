import snowflake.connector


# ---------------- CONNECTION ---------------- #
def create_snowflake_connection(account, user, password, mfa_passcode):
    return snowflake.connector.connect(
        account=account,
        user=user,
        password=password,
        passcode=mfa_passcode
    )


# ---------------- FIND TABLE ---------------- #
def find_object(cursor, db, name):
    query = f"""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM {db}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME ILIKE '%{name}%'
    """
    cursor.execute(query)
    res = cursor.fetchall()
    return res[0] if res else None


# ---------------- COLUMNS ---------------- #
def get_columns(cursor, db, schema, table):
    cursor.execute(f"""
        SELECT COLUMN_NAME
        FROM {db}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA='{schema}'
        AND TABLE_NAME='{table}'
    """)
    return [r[0] for r in cursor.fetchall()]


# ---------------- PIPES ---------------- #
def get_pipes(cursor, db, schema, table):
    pipes_list = []
    try:
        cursor.execute(f"SHOW PIPES IN SCHEMA {db}.{schema}")
        for pipe in cursor.fetchall():
            if table.upper() in str(pipe[6]).upper():
                pipes_list.append({"pipe_name": pipe[1]})
    except Exception as e:
        print("Pipe error:", e)
    return pipes_list


# ---------------- TASKS ---------------- #
def get_tasks(cursor, db, schema, table):
    task_list = []
    try:
        cursor.execute(f"SHOW TASKS IN SCHEMA {db}.{schema}")
        for task in cursor.fetchall():
            if table.upper() in str(task[9]).upper():
                task_list.append({"task_name": task[1]})
    except Exception as e:
        print("Task error:", e)
    return task_list


# ---------------- PROCEDURES ---------------- #
def get_procedures(cursor, db, schema):
    proc_list = []
    try:
        cursor.execute(f"SHOW PROCEDURES IN SCHEMA {db}.{schema}")
        for proc in cursor.fetchall():
            proc_list.append({"procedure_name": proc[1]})
    except Exception as e:
        print("Proc error:", e)
    return proc_list


# ---------------- BUILD LAYER ---------------- #
def build_layer(cursor, db, table):
    obj = find_object(cursor, db, table)
    if not obj:
        return None

    schema, table = obj

    return {
        "database": db,
        "schema": schema,
        "table": table,
        "columns": get_columns(cursor, db, schema, table),
        "pipes": get_pipes(cursor, db, schema, table),
        "tasks": get_tasks(cursor, db, schema, table),
        "procedures": get_procedures(cursor, db, schema)
    }


# ---------------- METADATA ---------------- #
def extract_metadata(conn, table, layer_map):
    cursor = conn.cursor()

    result = {"table_name": table}

    for layer, db in layer_map.items():
        result[layer] = build_layer(cursor, db, table)

    cursor.close()
    return result
