"""
Tool functions for AutoGen agents to interact with dive log data.
These functions are registered with agents for function calling.
"""
from typing import Annotated, List, Dict, Any, Optional
# Import config first to ensure .env file is loaded
import aidivelog.config  # noqa: F401
from aidivelog.sqlite_service import SQLiteService

# Initialize SQLite service (shared instance)
sqliteservice = SQLiteService()



def search_dive_logs(
    query: Annotated[str, "Comma-separated query of key terms for full-text search of dive logs (e.g., 'wreck, manta rays, whale sharks')"],
    location: Optional[Annotated[str, "Location mentioned by user - can be a dive site name, area, or country (e.g., 'Blue Corner', 'Malaysia', 'Red Sea', 'Cozumel'). When provided, this will be used to search across all location fields."]] = None,
    dive_type: Optional[Annotated[str, "Dive type (single type: wreck, cave, recreational, or decompression)"]] = None,
    max_depth: Optional[Annotated[int, "Maximum depth in meters"]] = None,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Search dive logs using semantic search. Finds relevant dive sites based on query.
    
    IMPORTANT: Always use the optional filter parameters (location, dive_type, max_depth) when the user
    mentions specific criteria. These filters significantly improve search accuracy and relevance.
    
    Args:
        query: Search query describing what kind of dive sites to find (e.g., "wreck dives with good visibility")
        location: ALWAYS use this when user mentions ANY location - whether it's a dive site name, area, or country.
                  Examples: "Blue Corner", "SS Thistlegorm", "Malaysia", "Red Sea", "Cozumel", "Shark Reef".
                  This single parameter will search across dive site names, areas, and countries.
        dive_type: ALWAYS use this when user mentions a specific dive type (e.g., "wreck", "cave", "recreational", "wall", "drift")
        max_depth: ALWAYS use this when user mentions depth constraints (e.g., "shallow dives", "under 30 meters", "deep dives")
        top_k: Number of results to return (default: 10). Increase for broader searches, decrease for more focused results.
        
    Returns:
        Dictionary with 'success' boolean and 'results' list of dive log dictionaries
    """
    try:
        # Use filter_by_metadata for all searches to handle dive_type filtering
        # When location is provided, pass it to all location-related parameters
        # to search across dive site names, areas, and countries
        results = sqliteservice.filter_by_metadata(
            query=query,
            location_site=location,  # Also search dive site names
            location_country=location,  # Also search countries
            location_area=location,  # Also search areas
            dive_type=dive_type,
            max_depth=max_depth,
            top_k=top_k
        )
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


def create_dive_log(
    date: Annotated[str, "Dive date in YYYY-MM-DD format (e.g., '2024-03-15')"],
    time: Annotated[str, "Dive time in HH:MM format using 24-hour clock (e.g., '09:30' or '14:15')"],
    max_depth: Annotated[int, "Maximum depth reached during the dive in meters"],
    dive_type: Annotated[str, "Type of dive (single type: 'recreational', 'wreck', 'cave', or 'decompression')"],
    location_site: Annotated[str, "Name of the dive site (e.g., 'Blue Corner', 'SS Thistlegorm')"],
    dive_length: Annotated[int, "Length of the dive in minutes"],
    location_area: Optional[Annotated[str, "Area or region where the dive site is located (e.g., 'Palau', 'Red Sea')"]] = None,
    location_country: Optional[Annotated[str, "Country where the dive site is located (e.g., 'Palau', 'Egypt')"]] = None,
    highlights: Optional[Annotated[str, "Highlights or notable features of the dive (e.g., 'barracuda schools, reef sharks, manta rays')"]] = None,
    equipment_used: Optional[Annotated[List[str], "List of equipment items used during the dive (e.g., ['BCD', 'regulator', 'wetsuit'])"]] = None,
    content: Optional[Annotated[str, "Narrative content of the dive experience."]] = None,
    depth_avg: Optional[Annotated[int, "Average depth during the dive in meters"]] = None
) -> Dict[str, Any]:
    """
    Create a new dive log entry in SQLite.
    
    Required fields:
    - date: Dive date in YYYY-MM-DD format
    - time: Dive time in HH:MM format (24-hour)
    - max_depth: Maximum depth in meters
    - dive_type: Type of dive
    - location_site: Name of the dive site
    - dive_length: Length of dive in minutes
    
    Optional fields:
    - location_area: Area or region
    - location_country: Country
    - highlights: Notable features or highlights
    - equipment_used: List of equipment items
    - content: Narrative content of the dive experience
    - depth_avg: Average depth in meters
    
    Returns:
        Dictionary with 'success' boolean, 'dive_id' (UUID string), and optional 'error' message
    """
    try:
        result = sqliteservice.create_dive_log(
            date=date,
            dive_time=time,
            max_depth=max_depth,
            dive_type=dive_type,
            location_site=location_site,
            dive_length=dive_length,
            location_area=location_area,
            location_country=location_country,
            highlights=highlights,
            equipment_used=equipment_used,
            content=content,
            depth_avg=depth_avg
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_all_dives() -> Dict[str, Any]:
    """
    Retrieve all dive logs from the database without any filters or search parameters.
    Returns all dives ordered by date (most recent first) and time.
    
    Returns:
        Dictionary with 'success' boolean and 'results' list of all dive log dictionaries
    """
    try:
        results = sqliteservice.get_all_dives()
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


def save_user_preference(
    key: Annotated[str, "Preference key (e.g., 'user_name', 'preferred_units')"],
    value: Annotated[str, "Preference value to store"]
) -> Dict[str, Any]:
    """
    Save a user preference to persistent storage.
    
    This tool saves user preferences directly to the database, making them available
    across all future conversations. Use this tool whenever the user states a preference
    such as their name or preferred units.
    
    Common preference keys:
    - 'user_name': The user's name (e.g., "Alex", "Sarah")
    - 'preferred_units': Unit system preference - must be either "metric" or "imperial"
    
    Args:
        key: Preference key identifier
        value: Preference value to store
        
    Returns:
        Dictionary with 'success' boolean and optional 'error' message
    """
    try:
        # Normalize preferred_units to "metric" or "imperial"
        if key == 'preferred_units':
            value_lower = value.lower()
            if 'metric' in value_lower:
                value = 'metric'
            elif 'imperial' in value_lower:
                value = 'imperial'
            else:
                # Default to metric if unclear
                value = 'metric'
        
        success = sqliteservice.save_user_preference(key, value)
        if success:
            return {
                "success": True,
                "message": f"Preference '{key}' saved successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to save preference"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
