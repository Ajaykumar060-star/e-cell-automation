import os
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv


def main() -> None:
    # Load env from inner project folder and repo root
    load_dotenv(Path(__file__).resolve().parent / '.env')
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')

    project_root = Path(__file__).resolve().parent.parent
    schema_path = project_root / 'database_schema.sql'

    if not schema_path.exists():
        raise FileNotFoundError(f'Schema file not found: {schema_path}')

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    connection = mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
    )
    try:
        cursor = connection.cursor()
        # Fallback for environments where cursor.execute does not support multi=True
        # Execute statements one by one, ignoring empty fragments
        statements = [s.strip() for s in schema_sql.split(';')]
        for statement in statements:
            if not statement:
                continue
            cursor.execute(statement)
        connection.commit()
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        connection.close()

    print('Database initialized successfully.')


if __name__ == '__main__':
    main()


