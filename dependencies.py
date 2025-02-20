import subprocess
import sqlite3
import re

def get_current_service():
    """Extract the service name from settings.gradle."""
    try:
        with open("settings.gradle", "r") as f:
            for line in f:
                line = line.strip()
                # Match a line like: rootProject.name = 'service-c'
                match = re.search(r"rootProject\.name\s*=\s*'([^']+)'", line)
                if match:
                    return match.group(1)
    except Exception as e:
        print("Error reading settings.gradle:", e)
    return None

def get_dependencies():
    """
    Run the Gradle command to list dependencies and parse out those from 'com.example'.
    Returns a list of tuples: (dependency, version)
    """
    cmd = "gradle dependencies --configuration compileClasspath"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error running gradle dependencies:", result.stderr)
        return []
    
    dependencies = []
    for line in result.stdout.splitlines():
        # Look for lines that contain "com.example:"; e.g., "+--- com.example:service-a:1.0.0"
        if "com.example:" in line:
            match = re.search(r"com\.example:([^:]+):([^:\s]+)", line)
            if match:
                dep_name = match.group(1)
                version = match.group(2)
                dependencies.append((dep_name, version))
    return dependencies

def save_dependencies_to_db(service_name, dependencies, db_filename="dependencies.db"):
    """
    Saves the service name and its dependencies to an SQLite table.
    Uses a UNIQUE constraint to avoid duplicate entries.
    """
    try:
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        
        # Create the table with a unique constraint on (servicename, dependency, version)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servicename TEXT,
                dependency TEXT,
                version TEXT,
                UNIQUE(servicename, dependency, version)
            )
        """)
        
        # Insert each dependency using INSERT OR IGNORE
        for dep, version in dependencies:
            cursor.execute("""
                INSERT OR IGNORE INTO service_dependencies (servicename, dependency, version)
                VALUES (?, ?, ?)
            """, (service_name, dep, version))
        
        conn.commit()
        conn.close()
        print(f"Dependencies for {service_name} saved successfully to the database.")
    except Exception as e:
        print("Error saving to DB:", e)

def print_db_contents(db_filename="dependencies.db"):
    """Reads and prints all rows from the service_dependencies table."""
    try:
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        
        cursor.execute("SELECT servicename, dependency, version FROM service_dependencies")
        rows = cursor.fetchall()
        
        print("servicename, dependency, version")
        print("---------------------------------")
        for row in rows:
            print(f"{row[0]}, {row[1]}, {row[2]}")
        conn.close()
    except Exception as e:
        print("Error reading from DB:", e)

def main():
    service_name = get_current_service()
    if not service_name:
        print("Could not determine the current service name from settings.gradle.")
        return
    print("Service Name:", service_name)
    
    dependencies = get_dependencies()
    if dependencies:
        print("Found dependencies:")
        for dep, ver in dependencies:
            print(f"  {dep} - {ver}")
        save_dependencies_to_db(service_name, dependencies)
        print("\nSaved records in SQLite (servicename, dependency, version):")
        print_db_contents()
    else:
        print("No dependencies found.")

if __name__ == "__main__":
    main()
