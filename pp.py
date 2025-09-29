import json
from pathlib import Path
from collections import defaultdict, Counter

# Load the Pyright output
with open("pyright_output.json", "r") as f:
    data = json.load(f)

# Group errors by folder and file
errors_by_folder = defaultdict(lambda: defaultdict(list))
file_error_counts = Counter()

# Extract diagnostics
for diag in data.get("generalDiagnostics", []):
    file_path = Path(diag["file"])
    folder = str(file_path.parent)
    filename = file_path.name

    message = diag["message"]
    range_info = diag.get("range", {})
    line = range_info.get("start", {}).get("line", '?')
    character = range_info.get("start", {}).get("character", '?')

    error_message = f"{filename}:{line}:{character} - {message}"
    errors_by_folder[folder][filename].append(error_message)
    file_error_counts[str(file_path)] += 1  # Full path as key

# Track total errors
total_errors = sum(file_error_counts.values())

# Print errors grouped by folder and file
for folder in sorted(errors_by_folder):
    print(f"\n📂 {folder}")
    files = errors_by_folder[folder]
    # Sort files by number of errors descending
    sorted_files = sorted(files.items(), key=lambda item: len(item[1]), reverse=True)

    for filename, errors in sorted_files:
        count = len(errors)
        print(f"  📄 {filename} ({count} error{'s' if count != 1 else ''})")
        for error in errors:
            print(f"    🔸 {error}")

# Summary
print(f"\n✅ Summary: {total_errors} total typing error{'s' if total_errors != 1 else ''} found.")

# Top 10 files by error count
print("\n📊 Top 20 Files with Most Errors:")
for i, (file_path, count) in enumerate(file_error_counts.most_common(20), start=1):
    print(f"  {i:>2}. {file_path} - {count} error{'s' if count != 1 else ''}")
