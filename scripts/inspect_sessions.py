"""
Script to inspect and read sessions.db database.

This script reads the sessions database and displays information about
stored sessions, including session metadata, conversation history, and events.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def get_db_path() -> Path:
    """Get the path to sessions.db."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "my_metric_agent" / "data" / "sessions.db"
    return db_path


def connect_to_db(db_path: Path) -> sqlite3.Connection:
    """Connect to the sessions database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def get_table_names(conn: sqlite3.Connection) -> List[str]:
    """Get all table names in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    return tables


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> List[tuple]:
    """Get the schema of a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    return cursor.fetchall()


def get_all_sessions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get all sessions from the database."""
    cursor = conn.cursor()
    
    # Try common table names for sessions
    possible_tables = ['sessions', 'session', 'adk_sessions', 'events']
    
    for table in possible_tables:
        try:
            cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC;")
            rows = cursor.fetchall()
            if rows:
                return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            continue
    
    return []


def format_timestamp(ts: Any) -> str:
    """Format a timestamp for display."""
    if ts is None:
        return "N/A"
    
    if isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(ts)
    
    return str(ts)


def format_json(data: Any, indent: int = 2) -> str:
    """Format JSON data for display."""
    if data is None:
        return "null"
    
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, indent=indent)
        except:
            return data
    
    return json.dumps(data, indent=indent)


def display_session_summary(sessions: List[Dict[str, Any]]) -> None:
    """Display a summary of all sessions."""
    print(f"\n{'='*80}")
    print(f"SESSIONS SUMMARY ({len(sessions)} sessions found)")
    print(f"{'='*80}\n")
    
    for i, session in enumerate(sessions, 1):
        print(f"Session {i}:")
        for key, value in session.items():
            if key.lower() in ['created_at', 'updated_at', 'timestamp']:
                value = format_timestamp(value)
            elif isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            
            print(f"  {key}: {value}")
        print()


def display_table_contents(conn: sqlite3.Connection, table_name: str, limit: int = 10) -> None:
    """Display contents of a specific table."""
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        
        print(f"\n{'='*80}")
        print(f"TABLE: {table_name} ({count} rows)")
        print(f"{'='*80}\n")
        
        if count == 0:
            print("  No data in this table.\n")
            return
        
        # Get schema
        schema = get_table_schema(conn, table_name)
        columns = [col[1] for col in schema]
        print(f"Columns: {', '.join(columns)}\n")
        
        # Get data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
        rows = cursor.fetchall()
        
        for i, row in enumerate(rows, 1):
            print(f"Row {i}:")
            row_dict = dict(row)
            for key, value in row_dict.items():
                if key.lower() in ['created_at', 'updated_at', 'timestamp']:
                    value = format_timestamp(value)
                elif isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                
                print(f"  {key}: {value}")
            print()
            
    except sqlite3.OperationalError as e:
        print(f"  Error reading table {table_name}: {e}\n")


def main():
    """Main function to inspect sessions database."""
    try:
        db_path = get_db_path()
        print(f"Database path: {db_path}")
        
        if not db_path.exists():
            print(f"\n❌ Database not found at: {db_path}")
            print("   Run 'adk web .' and have some conversations first to create the database.")
            return
        
        print(f"✅ Database found. Size: {db_path.stat().st_size} bytes\n")
        
        # Connect to database
        conn = connect_to_db(db_path)
        
        # Get all tables
        tables = get_table_names(conn)
        print(f"{'='*80}")
        print(f"DATABASE STRUCTURE")
        print(f"{'='*80}\n")
        print(f"Tables found: {', '.join(tables)}\n")
        
        # Display each table's contents
        for table in tables:
            display_table_contents(conn, table, limit=10)
        
        # Try to get sessions summary
        sessions = get_all_sessions(conn)
        if sessions:
            display_session_summary(sessions)
        else:
            print("\n⚠️  No sessions found in database.")
            print("   The database exists but may be empty or use a different schema.\n")
        
        conn.close()
        
        print(f"{'='*80}")
        print("Inspection complete!")
        print(f"{'='*80}\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
