import sqlite3
import random

def split_database(original_db_path, new_db_path, train_ratio=0.8):
    # Connect to the original database
    conn_orig = sqlite3.connect(original_db_path)
    cursor_orig = conn_orig.cursor()
    
    # Fetch all records from the original 'posts' table
    cursor_orig.execute("SELECT title, comment, sentiment FROM posts")
    all_records = cursor_orig.fetchall()
    
    # Shuffle the records to ensure random distribution
    random.shuffle(all_records)
    
    # Calculate split index
    total_records = len(all_records)
    train_count = int(total_records * train_ratio)
    
    # Split the data
    train_records = all_records[:train_count]
    test_records = all_records[train_count:]
    
    # Connect to the new database
    conn_new = sqlite3.connect(new_db_path)
    cursor_new = conn_new.cursor()
    
    # Create 'training' and 'testing' tables
    create_table_query = """
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            comment TEXT,
            sentiment TEXT
        )
    """
    cursor_new.execute(create_table_query.format(table_name="training"))
    cursor_new.execute(create_table_query.format(table_name="testing"))
    conn_new.commit()
    
    # Insert training records
    cursor_new.executemany(
        "INSERT INTO training (title, comment, sentiment) VALUES (?, ?, ?)",
        train_records
    )
    conn_new.commit()
    
    # Insert testing records
    cursor_new.executemany(
        "INSERT INTO testing (title, comment, sentiment) VALUES (?, ?, ?)",
        test_records
    )
    conn_new.commit()
    
    # Close all connections
    conn_orig.close()
    conn_new.close()
    
    print(f"Database split completed successfully!")
    print(f"Training records: {len(train_records)}")
    print(f"Testing records: {len(test_records)}")

if __name__ == "__main__":
    original_db = "reddit_posts.db"       # Path to your original database
    new_db = "reddit_posts_split.db"      # Path for the new split database
    split_database(original_db, new_db, train_ratio=0.8)
