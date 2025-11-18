import sqlite3
import uuid
from typing import Optional, Dict, List, Any, Tuple
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
        
        # Create user preferences table for memory persistence
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _build_filter_clauses(
        self,
        location_country: Optional[str] = None,
        location_area: Optional[str] = None,
        location_site: Optional[str] = None,
        dive_type: Optional[str] = None,
        max_depth: Optional[int] = None,
        min_depth: Optional[int] = None
    ) -> tuple[List[str], List[Any]]:
        """
        Build WHERE clause conditions and parameters for filtering dive logs.
        
        Args:
            location_country: Filter by country (exact match)
            location_area: Filter by area/region (exact match)
            location_site: Filter by dive site name (exact match)
            location: Filter by location matching either country or area
            dive_type: Filter by dive type (single type, e.g., "wreck" or "recreational")
            max_depth: Maximum depth filter (inclusive)
            min_depth: Minimum depth filter (inclusive)
            
        Returns:
            Tuple of (where_clauses list, params list)
        """
        where_clauses = []
        params = []
    

        if location_country:
            where_clauses.append("dl.location_country = ?")
            params.append(location_country)
        
        if location_area:
            where_clauses.append("dl.location_area = ?")
            params.append(location_area)
        
        # Handle dive site filtering
        if location_site:
            where_clauses.append("dl.location_site = ?")
            params.append(location_site)
        
        if max_depth is not None:
            where_clauses.append("dl.depth_max <= ?")
            params.append(max_depth)
        
        if min_depth is not None:
            where_clauses.append("dl.depth_max >= ?")
            params.append(min_depth)
        
        # Handle dive_type filtering (single string value)
        if dive_type:
            # Use simple equality check for exact match (case-insensitive)
            where_clauses.append("LOWER(dl.dive_type) = LOWER(?)")
            params.append(dive_type.strip())
        
        return where_clauses, params
    
    def _format_dive_result(self, row: sqlite3.Row, score: float = 0.0) -> Dict[str, Any]:
        """
        Format a database row into a standardized dive log dictionary.
        
        Args:
            row: Database row from SQLite query
            score: Relevance score for the dive (default: 0.0)
            
        Returns:
            Formatted dive log dictionary
        """
        return {
            "id": row["id"],
            "score": score,
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
    
    def _get_select_columns(self, use_fts: bool = False) -> str:
        """
        Get the standard SELECT column list for dive log queries.
        
        Args:
            use_fts: If True, include BM25 score calculation for FTS queries
            
        Returns:
            SELECT column list as a string
        """
        if use_fts:
            return """
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
                    """
        else:
            return """
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
                        0.0 as score
                    """
    
    def _build_fts_query(self, query: str) -> Tuple[str, List[str]]:
        """
        Build FTS query with OR operators for comma-separated terms.
        
        Args:
            query: Search query text (may contain commas)
            
        Returns:
            Tuple of (fts_query_string, fts_params_list)
        """
        # Clean and split query on commas
        fts_query_text = query.replace('"', ' ').strip()
        
        # Split on commas and filter out empty strings
        query_parts = [part.strip() for part in fts_query_text.split(',') if part.strip()]
        
        if not query_parts:
            # No meaningful query parts, match all
            return "dive_logs_fts MATCH '*'", []
        
        # Build single MATCH query with OR operators inside the query string
        # Join query parts with OR for FTS5 syntax: 'term1 OR term2 OR term3'
        fts_query_string = " OR ".join(query_parts)
        fts_query = "dive_logs_fts MATCH ?"
        fts_params = [fts_query_string]
        
        return fts_query, fts_params
    
    def search_dives(
        self,
        query: str,
        top_k: int = 10,
        location_country: Optional[str] = None,
        location_area: Optional[str] = None,
        location_site: Optional[str] = None,
        location: Optional[str] = None,
        dive_type: Optional[str] = None,
        max_depth: Optional[int] = None,
        min_depth: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search dive logs using full-text search with optional filtering.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            location_country: Filter by country (exact match)
            location_area: Filter by area/region (exact match)
            location_site: Filter by dive site name (exact match)
            location: Filter by location matching either country or area
            dive_type: Filter by dive type (single type, e.g., "wreck" or "recreational")
            max_depth: Maximum depth filter (inclusive)
            min_depth: Minimum depth filter (inclusive)
            
        Returns:
            List of dive log dictionaries with fields and metadata
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build filter clauses using helper method
            where_clauses, params = self._build_filter_clauses(
                location_country=location_country,
                location_area=location_area,
                location_site=location_site,
                dive_type=dive_type,
                max_depth=max_depth,
                min_depth=min_depth
            )
            
            # Determine if we should use FTS5 or query main table directly
            has_filters = bool(where_clauses)
            has_meaningful_query = query and query.strip() and query.strip() != "*"
            
            # If we have both filters and a meaningful query, run both searches separately
            # and combine results (OR logic - return results from EITHER method)
            if has_filters and has_meaningful_query:
                # Run filter-only search
                where_sql = " WHERE " + " OR ".join(where_clauses) if where_clauses else ""
                filter_sql = f"""
                    SELECT {self._get_select_columns(use_fts=False)}
                    FROM dive_logs dl
                    {where_sql}
                    ORDER BY dl.date DESC, dl.time DESC
                    LIMIT ?
                """
                filter_params = params + [top_k]
                
                # Run FTS search with filters
                fts_query, fts_query_params = self._build_fts_query(query)
                
                # Build WHERE clause for FTS query using same filters
                fts_where_parts = [fts_query]
                fts_filter_clauses, fts_filter_params = self._build_filter_clauses(
                    location_country=location_country,
                    location_area=location_area,
                    location_site=location_site,
                    dive_type=dive_type,
                    max_depth=max_depth,
                    min_depth=min_depth
                )
                fts_where_parts.extend(fts_filter_clauses)
                fts_where_sql = " OR ".join(fts_where_parts)
                
                fts_sql = f"""
                    SELECT {self._get_select_columns(use_fts=True)}
                    FROM dive_logs_fts
                    JOIN dive_logs dl ON dive_logs_fts.rowid = dl.rowid
                    WHERE {fts_where_sql}
                    ORDER BY score
                    LIMIT ?
                """
                fts_params = fts_query_params + fts_filter_params + [top_k]
                
                # Execute both queries
                cursor.execute(filter_sql, filter_params)
                filter_rows = cursor.fetchall()
                
                cursor.execute(fts_sql, fts_params)
                fts_rows = cursor.fetchall()
                
                # Combine results and deduplicate by ID
                seen_ids = set()
                formatted_results = []
                
                # Add filter results first
                for row in filter_rows:
                    dive_id = row["id"]
                    if dive_id not in seen_ids:
                        seen_ids.add(dive_id)
                        formatted_results.append(self._format_dive_result(row, score=0.0))
                
                # Add FTS results (skip duplicates)
                for row in fts_rows:
                    dive_id = row["id"]
                    if dive_id not in seen_ids:
                        seen_ids.add(dive_id)
                        # Negate BM25 score (lower is better in BM25, but we want higher)
                        score = -row["score"] if row["score"] else 0.0
                        formatted_results.append(self._format_dive_result(row, score=score))
                
                # Limit to top_k results
                formatted_results = formatted_results[:top_k]
                
            elif has_filters and not has_meaningful_query:
                # Query main table directly when we have filters but no text query
                where_sql = " WHERE " + " OR ".join(where_clauses) if where_clauses else ""
                
                sql = f"""
                    SELECT {self._get_select_columns(use_fts=False)}
                    FROM dive_logs dl
                    {where_sql}
                    ORDER BY dl.date DESC, dl.time DESC
                    LIMIT ?
                """
                all_params = params + [top_k]

                cursor.execute(sql, all_params)
                rows = cursor.fetchall()
                
                # Format results
                formatted_results = [self._format_dive_result(row, score=0.0) for row in rows]
                
            else:
                # Use FTS5 for text-based search only
                # Build FTS query (handles empty queries by matching all)
                fts_query, fts_query_params = self._build_fts_query(query if has_meaningful_query else "")
                
                # Build WHERE clause for FTS query if we have filters
                fts_where_parts = [fts_query]
                fts_filter_clauses, fts_filter_params = self._build_filter_clauses(
                    location_country=location_country,
                    location_area=location_area,
                    location_site=location_site,
                    dive_type=dive_type,
                    max_depth=max_depth,
                    min_depth=min_depth
                )
                fts_where_parts.extend(fts_filter_clauses)
                fts_where_sql = " OR ".join(fts_where_parts)
                
                sql = f"""
                    SELECT {self._get_select_columns(use_fts=True)}
                    FROM dive_logs_fts
                    JOIN dive_logs dl ON dive_logs_fts.rowid = dl.rowid
                    WHERE {fts_where_sql}
                    ORDER BY score
                    LIMIT ?
                """
                all_params = fts_query_params + fts_filter_params + [top_k]
            
                cursor.execute(sql, all_params)
                rows = cursor.fetchall()
                
                # Format results
                formatted_results = []
                for row in rows:
                    # Negate BM25 score (lower is better in BM25, but we want higher)
                    score = -row["score"] if row["score"] else 0.0
                    formatted_results.append(self._format_dive_result(row, score=score))
            
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
        location_site: Optional[str] = None,
        location: Optional[str] = None,
        dive_type: Optional[str] = None,
        max_depth: Optional[int] = None,
        min_depth: Optional[int] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search dives with metadata filtering.
        
        Args:
            query: Optional search query text
            location_country: Filter by country (exact match)
            location_area: Filter by area/region (exact match)
            location_site: Filter by dive site name (exact match)
            location: Filter by location matching either country or area
            dive_type: Filter by dive type (e.g., "wreck", "cave", "recreational")
            max_depth: Maximum depth filter
            min_depth: Minimum depth filter
            top_k: Number of results to return
            
        Returns:
            List of filtered dive log dictionaries
        """
        # Perform search with filters (including dive_type which is now handled in SQL)
        search_query = query if query else "*"
        results = self.search_dives(
            query=search_query,
            top_k=top_k,
            location_country=location_country,
            location_area=location_area,
            location_site=location_site,
            location=location,
            dive_type=dive_type,
            max_depth=max_depth,
            min_depth=min_depth
        )
        
        return results
    
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
            dive_type: Type of dive (single type: "wreck", "recreational", "cave", or "decompression")
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
    
    def save_user_preference(self, key: str, value: str) -> bool:
        """
        Save a user preference to the database.
        
        Args:
            key: Preference key (e.g., 'user_name', 'preferred_units')
            value: Preference value
            
        Returns:
            True if successful, False otherwise
        """
        print(f"Saving user preference: {key} = {value}")
        try:
            from datetime import datetime
            conn = self._get_connection()
            cursor = conn.cursor()
            
            updated_at = datetime.now().isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, updated_at))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving user preference: {e}")
            return False
    
    def get_all_user_preferences(self) -> Dict[str, str]:
        """
        Get all user preferences from the database.
        
        Returns:
            Dictionary mapping preference keys to values
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT key, value FROM user_preferences
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            return {row['key']: row['value'] for row in rows}
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return {}

