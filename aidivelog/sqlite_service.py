import sqlite3
import uuid
from typing import Optional, Dict, List, Any
from pathlib import Path


class SQLiteService:
    """Service for searching dive logs stored in SQLite."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the SQLiteService service.
        
        Args:
            db_path: Path to SQLite database file (default: aidivelog.db in project root)
        """
        if db_path is None:
            # Default to project root
            project_root = Path(__file__).parent.parent
            db_path = project_root / "aidivelog.db"
        
        self.db_path = str(db_path)
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def _init_database(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create main dive logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dive_logs (
                id TEXT PRIMARY KEY,
                content TEXT,
                location_site TEXT NOT NULL,
                location_area TEXT,
                location_country TEXT,
                depth_max INTEGER,
                depth_avg INTEGER,
                length_minutes INTEGER NOT NULL,
                dive_type TEXT,
                highlights TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                equipment_used TEXT
            )
        """)
        
        # Create FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS dive_logs_fts USING fts5(
                id UNINDEXED,
                content,
                location_site,
                location_area,
                location_country,
                highlights,
                content='dive_logs',
                content_rowid='rowid'
            )
        """)
        
        # Create triggers to keep FTS5 in sync with main table
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS dive_logs_ai AFTER INSERT ON dive_logs BEGIN
                INSERT INTO dive_logs_fts(rowid, id, content, location_site, location_area, location_country, highlights)
                VALUES (new.rowid, new.id, new.content, new.location_site, new.location_area, new.location_country, new.highlights);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS dive_logs_ad AFTER DELETE ON dive_logs BEGIN
                INSERT INTO dive_logs_fts(dive_logs_fts, rowid, id, content, location_site, location_area, location_country, highlights)
                VALUES('delete', old.rowid, old.id, old.content, old.location_site, old.location_area, old.location_country, old.highlights);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS dive_logs_au AFTER UPDATE ON dive_logs BEGIN
                INSERT INTO dive_logs_fts(dive_logs_fts, rowid, id, content, location_site, location_area, location_country, highlights)
                VALUES('delete', old.rowid, old.id, old.content, old.location_site, old.location_area, old.location_country, old.highlights);
                INSERT INTO dive_logs_fts(rowid, id, content, location_site, location_area, location_country, highlights)
                VALUES (new.rowid, new.id, new.content, new.location_site, new.location_area, new.location_country, new.highlights);
            END
        """)
        
        # Populate FTS5 with existing data if any
        cursor.execute("""
            INSERT OR IGNORE INTO dive_logs_fts(rowid, id, content, location_site, location_area, location_country, highlights)
            SELECT rowid, id, content, location_site, location_area, location_country, highlights
            FROM dive_logs
        """)
        
        conn.commit()
        conn.close()
    
    def search_dives(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        use_reranking: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search dive logs using full-text search with optional filtering.
        
        Args:
            query: Search query text
            filters: Optional metadata filters (e.g., {"location_country": "Egypt"})
            top_k: Number of results to return
            use_reranking: Ignored (kept for compatibility, SQLite FTS5 handles ranking)
            
        Returns:
            List of dive log dictionaries with fields and metadata
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build the FTS5 search query
            if not query or query.strip() == "*":
                # Search all if query is empty or "*"
                fts_query = "dive_logs_fts MATCH ?"
                fts_params = ["*"]
            else:
                # FTS5 uses a simple syntax: words are ANDed by default
                # Escape special FTS5 characters and build query
                # Replace spaces with AND for better matching
                fts_query_text = query.replace('"', ' ').strip()
                fts_query = "dive_logs_fts MATCH ?"
                fts_params = [fts_query_text]
            
            # Build WHERE clause for filters
            where_clauses = []
            params = []
            
            if filters:
                # Handle Pinecone-style filters
                if "$and" in filters:
                    # Multiple conditions
                    and_conditions = filters["$and"]
                    if isinstance(and_conditions, list):
                        for condition in and_conditions:
                            for key, value in condition.items():
                                if isinstance(value, dict):
                                    if "$eq" in value:
                                        where_clauses.append(f"{key} = ?")
                                        params.append(value["$eq"])
                                    elif "$lte" in value:
                                        where_clauses.append(f"{key} <= ?")
                                        params.append(value["$lte"])
                                    elif "$gte" in value:
                                        where_clauses.append(f"{key} >= ?")
                                        params.append(value["$gte"])
                elif "$or" in filters:
                    # OR conditions
                    or_conditions = filters["$or"]
                    if isinstance(or_conditions, list):
                        or_clauses = []
                        for condition in or_conditions:
                            for key, value in condition.items():
                                if isinstance(value, dict) and "$eq" in value:
                                    or_clauses.append(f"{key} = ?")
                                    params.append(value["$eq"])
                        if or_clauses:
                            where_clauses.append(f"({' OR '.join(or_clauses)})")
                else:
                    # Direct filter conditions
                    for key, value in filters.items():
                        if isinstance(value, dict):
                            if "$eq" in value:
                                where_clauses.append(f"{key} = ?")
                                params.append(value["$eq"])
                            elif "$lte" in value:
                                where_clauses.append(f"{key} <= ?")
                                params.append(value["$lte"])
                            elif "$gte" in value:
                                where_clauses.append(f"{key} >= ?")
                                params.append(value["$gte"])
            
            # Build the SQL query
            if where_clauses:
                where_sql = " AND " + " AND ".join(where_clauses)
            else:
                where_sql = ""
            
            sql = f"""
                SELECT 
                    dl.id,
                    dl.content,
                    dl.location_site,
                    dl.location_area,
                    dl.location_country,
                    dl.depth_max,
                    dl.depth_avg,
                    dl.length_minutes,
                    dl.dive_type,
                    dl.highlights,
                    dl.date,
                    dl.time,
                    bm25(dive_logs_fts) as score
                FROM dive_logs_fts
                JOIN dive_logs dl ON dive_logs_fts.rowid = dl.rowid
                WHERE {fts_query}{where_sql}
                ORDER BY score
                LIMIT ?
            """
            
            # Combine FTS params with filter params and limit
            all_params = fts_params + params + [top_k]
            
            cursor.execute(sql, all_params)
            rows = cursor.fetchall()
            
            # Format results
            formatted_results = []
            for row in rows:
                dive_data = {
                    "id": row["id"],
                    "score": -row["score"] if row["score"] else 0.0,  # Negate BM25 score (lower is better in BM25, but we want higher)
                    "content": row["content"] or "",
                    "location_site": row["location_site"] or "",
                    "location_area": row["location_area"] or "",
                    "location_country": row["location_country"] or "",
                    "depth_max": row["depth_max"],
                    "depth_avg": row["depth_avg"],
                    "length_minutes": row["length_minutes"],
                    "dive_type": row["dive_type"] or "",
                    "highlights": row["highlights"] or "",
                    "date": row["date"] or "",
                    "time": row["time"] or ""
                }
                formatted_results.append(dive_data)
            
            conn.close()
            return formatted_results
            
        except Exception as e:
            print(f"Error in search_dives: {e}")
            raise
    
    def get_dive_by_id(self, dive_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific dive log by ID.
        
        Args:
            dive_id: The dive log ID
            
        Returns:
            Dive log dictionary or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM dive_logs WHERE id = ?
            """, (dive_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "content": row["content"] or "",
                "location_site": row["location_site"] or "",
                "location_area": row["location_area"] or "",
                "location_country": row["location_country"] or "",
                "depth_max": row["depth_max"],
                "depth_avg": row["depth_avg"],
                "length_minutes": row["length_minutes"],
                "dive_type": row["dive_type"] or "",
                "highlights": row["highlights"] or "",
                "date": row["date"] or "",
                "time": row["time"] or ""
            }
        except Exception as e:
            print(f"Error in get_dive_by_id: {e}")
            raise
    
    def get_all_dives(self) -> List[Dict[str, Any]]:
        """
        Retrieve all dive logs from the database.
        
        Returns:
            List of all dive log dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM dive_logs
                ORDER BY date DESC, time DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            formatted_results = []
            for row in rows:
                dive_data = {
                    "id": row["id"],
                    "content": row["content"] or "",
                    "location_site": row["location_site"] or "",
                    "location_area": row["location_area"] or "",
                    "location_country": row["location_country"] or "",
                    "depth_max": row["depth_max"],
                    "depth_avg": row["depth_avg"],
                    "length_minutes": row["length_minutes"],
                    "dive_type": row["dive_type"] or "",
                    "highlights": row["highlights"] or "",
                    "date": row["date"] or "",
                    "time": row["time"] or ""
                }
                formatted_results.append(dive_data)
            
            return formatted_results
        except Exception as e:
            print(f"Error in get_all_dives: {e}")
            raise
    
    def filter_by_metadata(
        self,
        query: str = "",
        location_country: Optional[str] = None,
        location_area: Optional[str] = None,
        dive_type: Optional[str] = None,
        max_depth: Optional[int] = None,
        min_depth: Optional[int] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search dives with metadata filtering.
        
        Args:
            query: Optional search query text
            location_country: Filter by country
            location_area: Filter by area/region
            dive_type: Filter by dive type (e.g., "wreck", "cave", "recreational")
            max_depth: Maximum depth filter
            min_depth: Minimum depth filter
            top_k: Number of results to return
            
        Returns:
            List of filtered dive log dictionaries
        """
        # Build filters dictionary
        filters = {}
        
        if location_country:
            filters["location_country"] = {"$eq": location_country}
        
        if location_area:
            filters["location_area"] = {"$eq": location_area}
        
        # Handle depth filters - need to be careful not to overwrite
        if max_depth is not None and min_depth is not None:
            # Both min and max depth - we'll filter client-side after search
            # since SQLite WHERE clause can't easily combine $lte and $gte on same field
            filters["depth_max"] = {"$lte": max_depth}  # Use max_depth for initial filter
        elif max_depth is not None:
            filters["depth_max"] = {"$lte": max_depth}
        elif min_depth is not None:
            filters["depth_max"] = {"$gte": min_depth}
        
        # Perform search with filters
        search_query = query if query else "*"
        results = self.search_dives(search_query, filters=filters if filters else None, top_k=top_k * 2)
        
        # Client-side filtering for dive_type (since it's comma-separated)
        if dive_type:
            types_to_match = [t.strip().lower() for t in dive_type.split(",")] if "," in dive_type else [dive_type.strip().lower()]
            filtered_results = []
            for result in results:
                result_dive_type = result.get("dive_type", "").lower()
                if any(dt in result_dive_type for dt in types_to_match):
                    filtered_results.append(result)
            results = filtered_results
        
        # Handle depth range filtering (client-side for min/max combination)
        if min_depth is not None or max_depth is not None:
            filtered_results = []
            for result in results:
                depth = result.get("depth_max")
                if depth is not None:
                    if min_depth is not None and max_depth is not None:
                        # Both min and max
                        if min_depth <= depth <= max_depth:
                            filtered_results.append(result)
                    elif min_depth is not None:
                        # Only min
                        if depth >= min_depth:
                            filtered_results.append(result)
                    elif max_depth is not None:
                        # Only max (should already be filtered by SQL, but double-check)
                        if depth <= max_depth:
                            filtered_results.append(result)
                else:
                    # No depth info - exclude if we have depth filters
                    pass
            results = filtered_results[:top_k]
        
        return results[:top_k]
    
    def create_dive_log(
        self,
        date: str,
        dive_time: str,
        max_depth: int,
        dive_type: str,
        location_site: str,
        dive_length: int,
        location_area: Optional[str] = None,
        location_country: Optional[str] = None,
        highlights: Optional[str] = None,
        equipment_used: Optional[List[str]] = None,
        content: Optional[str] = None,
        depth_avg: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new dive log in SQLite.
        
        Args:
            date: Dive date in YYYY-MM-DD format
            dive_time: Dive time in HH:MM format (24-hour)
            max_depth: Maximum depth in meters
            dive_type: Type of dive (e.g., "wreck", "recreational", "cave,recreational")
            location_site: Name of the dive site (required)
            dive_length: Dive length in minutes
            location_area: Optional area/region
            location_country: Optional country
            highlights: Optional highlights description
            equipment_used: Optional list of equipment items
            content: Optional narrative content for the dive log
            depth_avg: Optional average depth in meters
            
        Returns:
            Dictionary with 'success' boolean, 'dive_id' (UUID), and optional 'error' message
        """
        try:
            # Generate UUID for dive log ID
            dive_id = str(uuid.uuid4())
            
            # Convert equipment_used list to comma-separated string if provided
            equipment_str = None
            if equipment_used:
                equipment_str = ",".join(equipment_used)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO dive_logs (
                    id, content, location_site, location_area, location_country,
                    depth_max, depth_avg, length_minutes, dive_type, highlights,
                    date, time, equipment_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dive_id,
                content,
                location_site,
                location_area,
                location_country,
                max_depth,
                depth_avg,
                dive_length,
                dive_type,
                highlights,
                date,
                dive_time,
                equipment_str
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "dive_id": dive_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

