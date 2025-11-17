import json
from dotenv import load_dotenv
from aidivelog.sqlite_service import SQLiteService

# Load environment variables from .env file
load_dotenv()

# Initialize SQLite service
print("Initializing SQLite database...")
sqlite_service = SQLiteService()
print("SQLite database initialized!")

# Step 1: Prepare dive log dataset
print("\n" + "="*60)
print("Step 1: Preparing dive log data")
print("="*60)

# Load dive logs from JSON file
with open("sample_dives.json", "r") as f:
    dive_logs = json.load(f)

# Step 2: Insert dive log data
print("\n" + "="*60)
print("Step 2: Inserting dive log data")
print("="*60)

print(f"Inserting {len(dive_logs)} dive log records...")
success_count = 0
error_count = 0

for i, dive_log in enumerate(dive_logs, 1):
    result = sqlite_service.create_dive_log(
        date=dive_log["date"],
        dive_time=dive_log["time"],
        max_depth=dive_log["max_depth"],
        dive_type=dive_log["dive_type"],
        location_site=dive_log["location_site"],
        dive_length=dive_log["dive_length"],
        location_area=dive_log.get("location_area"),
        location_country=dive_log.get("location_country"),
        highlights=dive_log.get("highlights"),
        content=dive_log.get("content"),
        depth_avg=dive_log.get("depth_avg")
    )
    
    if result.get("success"):
        success_count += 1
        if i % 5 == 0:
            print(f"  Inserted {i}/{len(dive_logs)} dive logs...")
    else:
        error_count += 1
        print(f"  Error inserting dive log {i}: {result.get('error')}")

print("\nDive log data insertion completed!")
print(f"  Success: {success_count}")
print(f"  Errors: {error_count}")

# Step 3: Test search functionality
print("\n" + "="*60)
print("Step 3: Testing Search Functionality")
print("="*60)

query = "Wreck dives with good visibility and marine life"
print(f"Query: '{query}'")
print("\nSearching for top 10 results...")

results = sqlite_service.search_dives(query, top_k=10)

print("\nSearch Results:")
print("-" * 80)
for i, dive in enumerate(results, 1):
    print(f"{i}. ID: {dive['id']:<36} | Score: {round(dive.get('score', 0), 3):<6} | Site: {dive.get('location_site', 'N/A'):<20} | Type: {dive.get('dive_type', 'N/A'):<20}")
    print(f"   Location: {dive.get('location_area', 'N/A')}, {dive.get('location_country', 'N/A')} | Depth: {dive.get('depth_max', 'N/A')}m | Date: {dive.get('date', 'N/A')}")
    content = dive.get('content', '')
    if content:
        print(f"   {content[:100]}...")
    print()

print("\n" + "="*60)
print("Dive log population and test completed successfully!")
print("="*60)
