import argparse
import sqlite3

def load_db(db_filename="dependencies.db"):
    """Load all dependency rows from the SQLite database."""
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute("SELECT servicename, dependency, version FROM service_dependencies")
    rows = cursor.fetchall()
    conn.close()
    return rows

def build_reverse_graph(rows):
    """
    Build a reverse dependency graph from the rows.
    Maps: dependency -> list of (dependent, version)
    """
    rev_graph = {}
    for svc, dep, ver in rows:
        rev_graph.setdefault(dep, []).append((svc, ver))
    return rev_graph

def build_direct_map(rows):
    """
    Build a mapping from each service to the set of services it directly depends on.
    """
    direct = {}
    for svc, dep, _ in rows:
        direct.setdefault(svc, set()).add(dep)
    return direct

def compute_immediate_upstream(service, rev_graph, direct_map):
    """
    For a given service, return only those services that depend on it immediately.
    A dependent D is considered immediate if none of the other dependents appear in D's direct dependencies.
    """
    candidates = rev_graph.get(service, [])
    candidate_names = {dep for dep, _ in candidates}
    immediate = []
    for dep, ver in candidates:
        # If D directly depends on any other candidate, skip it.
        if direct_map.get(dep, set()) & candidate_names:
            continue
        immediate.append((dep, ver))
    return immediate

def main():
    parser = argparse.ArgumentParser(
        description="Display upstream dependencies from the dependency DB."
    )
    parser.add_argument("--service", type=str,
                        help="Specify the service to compute upstream dependencies.")
    parser.add_argument("--reduce", action="store_true",
                        help="Only show immediate (direct) upstream dependencies.")
    parser.add_argument("--machine", action="store_true",
                        help="Output machine-readable format (no headers, one dependency per line, comma-separated).")
    args = parser.parse_args()
    
    rows = load_db()
    if not rows:
        print("No dependency data found in the DB.")
        return

    if args.service:
        input_service = args.service
        rev_graph = build_reverse_graph(rows)
        direct_map = build_direct_map(rows)
        # Get all upstream dependents (reverse lookup: who depends on the input service)
        upstream = rev_graph.get(input_service, [])
        if args.reduce:
            results = compute_immediate_upstream(input_service, rev_graph, direct_map)
        else:
            results = upstream
        
        if args.machine:
            # Machine output: one dependency per line, format: dependency,version
            for dep, ver in results:
                print(f"{dep},{ver}")
        else:
            # Human-readable output with header
            print("servicename, dependency, version")
            for dep, ver in results:
                print(f"{input_service}, {dep}, {ver}")
    else:
        # No service provided: simply list all rows.
        if args.machine:
            for svc, dep, ver in rows:
                print(f"{svc},{dep},{ver}")
        else:
            print("servicename, dependency, version")
            for svc, dep, ver in rows:
                print(f"{svc}, {dep}, {ver}")

if __name__ == "__main__":
    main()
