# Database Service - Data persistence and retrieval
import sqlite3
from typing import List, Optional, Dict, Any
from app.models.job_posting_models import JobPosting # Our Pydantic model
from app.models.application_log_models import ApplicationLog # For application logging
from config import settings # To get DATABASE_URL
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# DB_PATH is derived from settings.DATABASE_URL
DB_PATH = settings.DATABASE_URL.split("sqlite:///")[-1] if settings.DATABASE_URL.startswith("sqlite:///") else settings.DATABASE_URL

def get_db_connection() -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Access columns by name
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database at {DB_PATH}: {e}", exc_info=True)
        raise # Reraise the exception to be handled by the caller

def save_job_posting(job: JobPosting) -> Optional[int]:
    """
    Saves a job posting to the job_postings table.
    Returns the database ID of the inserted or existing job, or None if an error occurs.
    """
    if not isinstance(job, JobPosting):
        logger.error(f"Invalid type passed to save_job_posting. Expected JobPosting, got {type(job)}")
        return None

    # Map JobPosting model fields to database columns
    sql_insert = """
        INSERT INTO job_postings 
        (job_id, title, company, location, job_type, remote_option, salary_min, salary_max, 
         description, requirements, application_url, source, source_url, scraped_at, 
         relevance_score, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    sql_check_existing = "SELECT id FROM job_postings WHERE source_url = ?"

    conn = get_db_connection()
    try:
        with conn: # Using 'with conn' handles commit/rollback automatically
            cursor = conn.cursor()
            
            # Check if job URL already exists (using source_url as the unique identifier)
            cursor.execute(sql_check_existing, (str(job.job_url),))
            existing_job_row = cursor.fetchone()
            
            if existing_job_row:
                existing_job_id = existing_job_row["id"]
                logger.info(f"Job with URL '{job.job_url}' already exists in job_postings with ID {existing_job_id}. Skipping insert.")
                return existing_job_id

            # Prepare data for insertion
            cursor.execute(sql_insert, (
                job.id_on_platform,  # job_id
                job.title,            # title
                job.company_name,     # company
                job.location_text,    # location
                "full-time",          # job_type (default, could be extracted from description later)
                "remote" if job.location_text and "remote" in job.location_text.lower() else "on-site",  # remote_option
                job.salary_min,       # salary_min
                job.salary_max,       # salary_max
                job.full_description_text,  # description
                job.full_description_text,  # requirements (using same as description for now)
                str(job.job_url),     # application_url
                job.source_platform,  # source
                str(job.job_url),     # source_url
                job.scraped_timestamp.isoformat() if job.scraped_timestamp else datetime.utcnow().isoformat(),  # scraped_at
                job.relevance_score,  # relevance_score
                job.processing_status.lower() if job.processing_status else "discovered",  # status
                None                  # notes
            ))
            job_db_id = cursor.lastrowid
            logger.info(f"Saved job posting '{job.title}' from '{job.company_name}' with DB ID {job_db_id} to job_postings.")
            return job_db_id
    except sqlite3.IntegrityError as ie:
        logger.error(f"Database integrity error while saving job posting: {job.job_url}. Error: {ie}", exc_info=True)
        # Attempt to fetch the ID again if it was a UNIQUE constraint
        cursor = conn.cursor()
        cursor.execute(sql_check_existing, (str(job.job_url),))
        existing_job_row = cursor.fetchone()
        if existing_job_row:
            return existing_job_row["id"]
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error while saving job posting: {job.job_url}. Error: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def get_pending_jobs(limit: int = 10) -> List[JobPosting]:
    """
    Retrieves job postings from job_postings that are pending processing (status = 'pending').
    Maps them back to JobPosting Pydantic models.
    """
    sql_select = "SELECT * FROM job_postings WHERE status = 'pending' ORDER BY scraped_at ASC LIMIT ?"
    jobs: List[JobPosting] = []
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_select, (limit,))
        rows = cursor.fetchall()
        
        for row in rows:
            # Map row back to JobPosting model
            jobs.append(JobPosting(
                internal_db_id=row["id"],  # Store the database ID
                source_platform=row["source"] if row["source"] else "unknown",
                id_on_platform=row["job_id"],
                job_url=row["source_url"] if row["source_url"] else row["application_url"],
                title=row["title"],
                company_name=row["company"],
                location_text=row["location"],
                salary_min=row["salary_min"],
                salary_max=row["salary_max"],
                salary_range_text=f"${row['salary_min']}-${row['salary_max']}" if row["salary_min"] and row["salary_max"] else None,
                full_description_raw=row["description"],
                full_description_text=row["description"],
                scraped_timestamp=datetime.fromisoformat(row["scraped_at"]) if row["scraped_at"] else None,
                processing_status=row["status"],
                relevance_score=row["relevance_score"]
                # Other JobPosting fields will have their defaults or be None
            ))
        logger.info(f"Retrieved {len(jobs)} pending jobs from database.")
        return jobs
    except sqlite3.Error as e:
        logger.error(f"Database error while fetching pending jobs: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

def update_job_processing_status(job_db_id: int, new_status: str, relevance_score: Optional[float] = None, relevance_reasons: Optional[str] = None) -> bool:
    """
    Updates the processing status of a job in the job_postings table.
    Optionally updates relevance_score and relevance_reasons if provided.
    """
    # Build dynamic SQL based on what parameters are provided
    update_fields = ["status = ?", "updated_at = ?"]
    update_values = [new_status, datetime.utcnow().isoformat()]
    
    if relevance_score is not None:
        update_fields.append("relevance_score = ?")
        update_values.append(relevance_score)
        
    if relevance_reasons is not None:
        update_fields.append("relevance_reasons = ?")
        update_values.append(relevance_reasons)
    
    # Add job_db_id at the end for WHERE clause
    update_values.append(job_db_id)
    
    sql_update = f"UPDATE job_postings SET {', '.join(update_fields)} WHERE id = ?"

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql_update, update_values)
            if cursor.rowcount > 0:
                logger.info(f"Updated job ID {job_db_id}: status='{new_status}', relevance_score={relevance_score}")
                return True
            else:
                logger.warning(f"No job found with ID {job_db_id} to update.")
                return False
    except sqlite3.Error as e:
        logger.error(f"Database error updating job ID {job_db_id}: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

def get_all_jobs(limit: int = 50, status_filter: Optional[str] = None) -> List[JobPosting]:
    """
    Retrieves job postings from the database with optional status filtering.
    """
    if status_filter:
        sql_select = "SELECT * FROM job_postings WHERE status = ? ORDER BY scraped_at DESC LIMIT ?"
        params = (status_filter, limit)
    else:
        sql_select = "SELECT * FROM job_postings ORDER BY scraped_at DESC LIMIT ?"
        params = (limit,)
    
    jobs: List[JobPosting] = []
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_select, params)
        rows = cursor.fetchall()
        
        for row in rows:
            jobs.append(JobPosting(
                internal_db_id=row["id"],
                source_platform=row["source"] if row["source"] else "unknown",
                id_on_platform=row["job_id"],
                job_url=row["source_url"] if row["source_url"] else row["application_url"],
                title=row["title"],
                company_name=row["company"],
                location_text=row["location"],
                salary_min=row["salary_min"],
                salary_max=row["salary_max"],
                salary_range_text=f"${row['salary_min']}-${row['salary_max']}" if row["salary_min"] and row["salary_max"] else None,
                full_description_raw=row["description"],
                full_description_text=row["description"],
                scraped_timestamp=datetime.fromisoformat(row["scraped_at"]) if row["scraped_at"] else None,
                processing_status=row["status"],
                relevance_score=row["relevance_score"]
            ))
        logger.info(f"Retrieved {len(jobs)} jobs from database (status_filter: {status_filter}).")
        return jobs
    except sqlite3.Error as e:
        logger.error(f"Database error while fetching jobs: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

def save_search_query(user_profile_id: int, query_terms: str, location: Optional[str], source: str, results_count: int = 0) -> Optional[int]:
    """
    Logs a search query to the search_queries table for tracking purposes.
    """
    sql_insert = """
        INSERT INTO search_queries 
        (user_profile_id, query_terms, location, source, results_count, executed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql_insert, (
                user_profile_id,
                query_terms,
                location,
                source,
                results_count,
                datetime.utcnow().isoformat()
            ))
            search_id = cursor.lastrowid
            logger.info(f"Logged search query: '{query_terms}' for user {user_profile_id}, got {results_count} results.")
            return search_id
    except sqlite3.Error as e:
        logger.error(f"Database error while saving search query: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

# TODO MVP: Add functions for ApplicationLog CRUD operations
def log_application(job_posting_id: int, user_profile_id: int, application_data: Dict[str, Any]) -> Optional[int]:
    """
    Logs a job application to the applications table.
    """
    sql_insert = """
        INSERT INTO applications 
        (user_profile_id, job_posting_id, application_date, status, application_method, 
         resume_version, application_url, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql_insert, (
                user_profile_id,
                job_posting_id,
                datetime.utcnow().isoformat(),
                application_data.get("status", "applied"),
                application_data.get("method", "manual"),
                application_data.get("resume_path", ""),
                application_data.get("job_url", ""),
                application_data.get("notes", "")
            ))
            application_id = cursor.lastrowid
            logger.info(f"Logged application for job {job_posting_id} by user {user_profile_id}.")
            return application_id
    except sqlite3.Error as e:
        logger.error(f"Database error while logging application: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def save_application_log(application_log: ApplicationLog) -> Optional[int]:
    """
    Saves an ApplicationLog to the applications table.
    Returns the database ID of the inserted application or None if an error occurs.
    """
    if not isinstance(application_log, ApplicationLog):
        logger.error(f"Invalid type passed to save_application_log. Expected ApplicationLog, got {type(application_log)}")
        return None

    # Try to find the job posting ID if the job exists in our database
    found_job = find_job_by_url(str(application_log.job_url))
    job_posting_id = found_job.internal_db_id if found_job else None
    
    # If we don't have the job in our database, we still want to log the application
    # but we'll use a placeholder job_posting_id or modify the table
    if job_posting_id is None:
        logger.info(f"Job not found in database for URL: {application_log.job_url}. Creating application log anyway.")
        # For MVP, we'll use job_posting_id = 0 to indicate external job
        job_posting_id = 0

    sql_insert = """
        INSERT INTO applications 
        (user_profile_id, job_posting_id, application_date, status, application_method, 
         resume_version, application_url, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql_insert, (
                1,  # Default user_profile_id for MVP
                job_posting_id,  # Will be 0 if job not in our database
                application_log.application_date.isoformat() if application_log.application_date else datetime.utcnow().isoformat(),
                application_log.status,
                "manual",  # application_method - since logged via CLI
                application_log.resume_version_used_path,
                str(application_log.job_url),
                application_log.notes or ""
            ))
            application_id = cursor.lastrowid
            logger.info(f"Saved application log: '{application_log.job_title}' at '{application_log.company_name}' with DB ID {application_id}")
            return application_id
    except sqlite3.Error as e:
        logger.error(f"Database error while saving application log: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def find_job_by_url(job_url: str) -> Optional[JobPosting]:
    """
    Finds a job posting by URL to help populate application logs.
    Returns the JobPosting object or None if not found.
    """
    sql_select = "SELECT * FROM job_postings WHERE source_url = ? OR application_url = ?"
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_select, (job_url, job_url))
        row = cursor.fetchone()
        
        if row:
            job = JobPosting(
                internal_db_id=row["id"],
                source_platform=row["source"] if row["source"] else "unknown",
                id_on_platform=row["job_id"],
                job_url=row["source_url"] if row["source_url"] else row["application_url"],
                title=row["title"],
                company_name=row["company"],
                location_text=row["location"],
                salary_min=row["salary_min"],
                salary_max=row["salary_max"],
                salary_range_text=f"${row['salary_min']}-${row['salary_max']}" if row["salary_min"] and row["salary_max"] else None,
                full_description_raw=row["description"],
                full_description_text=row["description"],
                scraped_timestamp=datetime.fromisoformat(row["scraped_at"]) if row["scraped_at"] else None,
                processing_status=row["status"],
                relevance_score=row["relevance_score"]
            )
            logger.info(f"Found job by URL: '{job.title}' at '{job.company_name}' (ID: {job.internal_db_id})")
            return job
        else:
            logger.info(f"No job found with URL: {job_url}")
            return None
    except sqlite3.Error as e:
        logger.error(f"Database error while finding job by URL: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def get_application_logs(user_profile_id: int = 1, limit: int = 50) -> List[ApplicationLog]:
    """
    Retrieves application logs from the applications table.
    Returns a list of ApplicationLog objects.
    """
    sql_select = """
        SELECT 
            a.*,
            COALESCE(jp.title, 'External Job') as job_title,
            COALESCE(jp.company, 'External Company') as company_name
        FROM applications a
        LEFT JOIN job_postings jp ON a.job_posting_id = jp.id
        WHERE a.user_profile_id = ? 
        ORDER BY a.application_date DESC 
        LIMIT ?
    """
    applications: List[ApplicationLog] = []
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_select, (user_profile_id, limit))
        rows = cursor.fetchall()
        
        for row in rows:
            app_log = ApplicationLog(
                internal_db_id=row["id"],
                job_url=row["application_url"],
                job_title=row["job_title"],
                company_name=row["company_name"],
                application_date=datetime.fromisoformat(row["application_date"]) if row["application_date"] else None,
                status=row["status"],
                resume_version_used_path=row["resume_version"],
                notes=row["notes"]
            )
            applications.append(app_log)
        
        logger.info(f"Retrieved {len(applications)} application logs for user {user_profile_id}")
        return applications
    except sqlite3.Error as e:
        logger.error(f"Database error while fetching application logs: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

def add_embedding_columns_if_not_exist():
    """Adds embedding related columns to job_postings if they don't exist."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Check existing columns
        cursor.execute("PRAGMA table_info(job_postings)")
        columns = [col[1] for col in cursor.fetchall()]  # col[1] is the column name
        
        # Add new columns if they don't exist
        if 'description_embedding' not in columns:
            cursor.execute("ALTER TABLE job_postings ADD COLUMN description_embedding TEXT")
            logger.info("Added 'description_embedding' column to 'job_postings'.")
        
        if 'title_embedding' not in columns:
            cursor.execute("ALTER TABLE job_postings ADD COLUMN title_embedding TEXT")
            logger.info("Added 'title_embedding' column to 'job_postings'.")
            
        if 'embedding_model' not in columns:
            cursor.execute("ALTER TABLE job_postings ADD COLUMN embedding_model TEXT")
            logger.info("Added 'embedding_model' column to 'job_postings'.")
            
        if 'embedding_generated_at' not in columns:
            cursor.execute("ALTER TABLE job_postings ADD COLUMN embedding_generated_at TEXT")
            logger.info("Added 'embedding_generated_at' column to 'job_postings'.")
            
        if 'semantic_similarity_score' not in columns:
            cursor.execute("ALTER TABLE job_postings ADD COLUMN semantic_similarity_score REAL")
            logger.info("Added 'semantic_similarity_score' column to 'job_postings'.")
            
        if 'combined_match_score' not in columns:
            cursor.execute("ALTER TABLE job_postings ADD COLUMN combined_match_score REAL")
            logger.info("Added 'combined_match_score' column to 'job_postings'.")

        conn.commit()
        logger.info("Database schema update completed successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error updating database schema for embeddings: {e}", exc_info=True)
        conn.rollback()
    finally:
        if conn:
            conn.close()

def save_job_embeddings(job_db_id: int, title_embedding: list = None, description_embedding: list = None, 
                       model_name: str = None) -> bool:
    """Saves embeddings for a job posting."""
    if not title_embedding and not description_embedding:
        logger.warning(f"No embeddings provided for job ID {job_db_id}")
        return False
        
    updates = []
    params = []
    
    if title_embedding:
        updates.append("title_embedding = ?")
        params.append(json.dumps(title_embedding))
        
    if description_embedding:
        updates.append("description_embedding = ?")
        params.append(json.dumps(description_embedding))
        
    if model_name:
        updates.append("embedding_model = ?")
        params.append(model_name)
        
    updates.append("embedding_generated_at = ?")
    params.append(datetime.utcnow().isoformat())
    
    updates.append("status = ?")
    params.append("embedded")
    
    sql_update = f"UPDATE job_postings SET {', '.join(updates)} WHERE id = ?"
    params.append(job_db_id)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_update, params)
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Saved embeddings for job ID {job_db_id} using model '{model_name}'")
            return True
        else:
            logger.warning(f"No job found with ID {job_db_id} to update embeddings")
            return False
    except sqlite3.Error as e:
        logger.error(f"Database error saving embeddings for job ID {job_db_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def update_semantic_scores(job_db_id: int, semantic_similarity_score: float = None, 
                          combined_match_score: float = None) -> bool:
    """Updates semantic analysis scores for a job."""
    updates = []
    params = []
    
    if semantic_similarity_score is not None:
        updates.append("semantic_similarity_score = ?")
        params.append(semantic_similarity_score)
        
    if combined_match_score is not None:
        updates.append("combined_match_score = ?")
        params.append(combined_match_score)
        
    if not updates:
        return False
        
    sql_update = f"UPDATE job_postings SET {', '.join(updates)} WHERE id = ?"
    params.append(job_db_id)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_update, params)
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Updated semantic scores for job ID {job_db_id}")
            return True
        else:
            logger.warning(f"No job found with ID {job_db_id} to update semantic scores")
            return False
    except sqlite3.Error as e:
        logger.error(f"Database error updating semantic scores for job ID {job_db_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_jobs_needing_embeddings(limit: int = 50) -> List[JobPosting]:
    """Gets jobs that need embeddings generated."""
    sql_select = """
        SELECT * FROM job_postings 
        WHERE description_embedding IS NULL 
        AND (title IS NOT NULL OR description IS NOT NULL)
        ORDER BY scraped_at DESC LIMIT ?
    """
    
    jobs = []
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_select, (limit,))
        rows = cursor.fetchall()
        
        for row in rows:
            job = JobPosting(
                internal_db_id=row["id"],
                id_on_platform=row["job_id"],
                source_platform=row["source"],
                job_url=row["source_url"] or row["application_url"],
                title=row["title"] or "No Title",
                company_name=row["company"] or "No Company",
                full_description_text=row["description"] or "",
                processing_status=row["status"] or "discovered",
                scraped_timestamp=datetime.fromisoformat(row["scraped_at"]) if row["scraped_at"] else datetime.utcnow()
            )
            jobs.append(job)
            
        logger.info(f"Retrieved {len(jobs)} jobs needing embeddings")
        return jobs
    except sqlite3.Error as e:
        logger.error(f"Database error getting jobs needing embeddings: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

def get_jobs_with_embeddings(limit: int = 100) -> List[JobPosting]:
    """Gets jobs that have embeddings for semantic search."""
    sql_select = """
        SELECT * FROM job_postings 
        WHERE description_embedding IS NOT NULL
        ORDER BY scraped_at DESC LIMIT ?
    """
    
    jobs = []
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_select, (limit,))
        rows = cursor.fetchall()
        
        for row in rows:
            # Parse embeddings from JSON
            title_embedding = None
            description_embedding = None
            
            if row["title_embedding"]:
                try:
                    title_embedding = json.loads(row["title_embedding"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse title embedding for job ID {row['id']}")
                    
            if row["description_embedding"]:
                try:
                    description_embedding = json.loads(row["description_embedding"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse description embedding for job ID {row['id']}")
            
            job = JobPosting(
                internal_db_id=row["id"],
                id_on_platform=row["job_id"],
                source_platform=row["source"],
                job_url=row["source_url"] or row["application_url"],
                title=row["title"] or "No Title",
                company_name=row["company"] or "No Company",
                full_description_text=row["description"] or "",
                title_embedding=json.dumps(title_embedding) if title_embedding else None,
                description_embedding=json.dumps(description_embedding) if description_embedding else None,
                embedding_model=row["embedding_model"],
                embedding_generated_at=datetime.fromisoformat(row["embedding_generated_at"]) if row["embedding_generated_at"] else None,
                semantic_similarity_score=row["semantic_similarity_score"],
                combined_match_score=row["combined_match_score"],
                relevance_score=row["relevance_score"],
                processing_status=row["status"] or "discovered",
                scraped_timestamp=datetime.fromisoformat(row["scraped_at"]) if row["scraped_at"] else datetime.utcnow()
            )
            jobs.append(job)
            
        logger.info(f"Retrieved {len(jobs)} jobs with embeddings")
        return jobs
    except sqlite3.Error as e:
        logger.error(f"Database error getting jobs with embeddings: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # This section is for direct testing of the database_service.py
    # Ensure your database is initialized by running scripts/initialize_database.py first.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Testing database_service.py directly...")

    # 1. Test saving a new job posting
    test_job_data = {
        "source_platform": "TestPlatform_DBService",
        "job_url": f"http://testjobs.com/job/{datetime.now().timestamp()}", # Unique URL
        "title": "Senior Test Engineer",
        "company_name": "DB Test Corp",
        "location_text": "Remote",
        "full_description_raw": "This is a test job description for database saving.",
        "full_description_text": "This is a test job description for database saving.",
        "processing_status": "Pending" # Default from model
    }
    test_job = JobPosting(**test_job_data)
    
    logger.debug(f"Attempting to save test job: {test_job.title}")
    saved_job_id = save_job_posting(test_job)

    if saved_job_id:
        logger.info(f"Test job saved successfully with ID: {saved_job_id}")

        # 2. Test retrieving pending jobs
        logger.debug("Attempting to retrieve pending jobs...")
        pending_jobs = get_pending_jobs(limit=5)
        if pending_jobs:
            logger.info(f"Retrieved {len(pending_jobs)} pending jobs. First one: {pending_jobs[0].title if pending_jobs else 'None'}")
            for pj in pending_jobs:
                if pj.internal_db_id == saved_job_id:
                    logger.info(f"Successfully retrieved the saved test job (ID: {saved_job_id}) in pending list.")
                    break
            else: # If loop completes without break
                logger.warning(f"Saved test job (ID: {saved_job_id}) not found in the first {len(pending_jobs)} pending jobs.")

        else:
            logger.warning("No pending jobs retrieved or an error occurred.")

        # 3. Test updating processing status
        if pending_jobs and any(pj.internal_db_id == saved_job_id for pj in pending_jobs):
            logger.debug(f"Attempting to update status for job ID: {saved_job_id}")
            update_success = update_job_processing_status(saved_job_id, "analyzed", relevance_score=0.85, relevance_reasons="High relevance test")
            if update_success:
                logger.info(f"Successfully updated status for job ID: {saved_job_id}.")
                # Verify it's no longer 'discovered'
                updated_pending_jobs = get_pending_jobs(limit=5)
                if not any(pj.internal_db_id == saved_job_id for pj in updated_pending_jobs):
                    logger.info(f"Job ID {saved_job_id} is no longer in pending list after status update, as expected.")
                else:
                     logger.warning(f"Job ID {saved_job_id} STILL found in pending list after status update.")
            else:
                logger.error(f"Failed to update status for job ID: {saved_job_id}.")
        else:
            logger.warning(f"Skipping status update test as saved job ID {saved_job_id} was not found in pending list.")
            
        # 4. Test saving a duplicate job URL
        logger.debug(f"Attempting to save the same test job again (URL: {test_job.job_url}) to test duplicate handling.")
        duplicate_job_id = save_job_posting(test_job)
        if duplicate_job_id == saved_job_id:
            logger.info(f"Duplicate job saving handled correctly. Returned existing ID: {duplicate_job_id}")
        elif duplicate_job_id is not None:
            logger.error(f"Duplicate job saving resulted in a new ID: {duplicate_job_id} instead of existing ID: {saved_job_id}")
        else:
            logger.error(f"Duplicate job saving failed or returned None unexpectedly.")

        # 5. Test search query logging
        logger.debug("Testing search query logging...")
        search_id = save_search_query(1, "Senior Test Engineer", "Remote", "TestPlatform_DBService", 1)
        if search_id:
            logger.info(f"Successfully logged search query with ID: {search_id}")
        else:
            logger.error("Failed to log search query.")
            
    else:
        logger.error("Failed to save initial test job. Further tests cannot proceed accurately.")
    
    logger.info("Finished testing database_service.py.") 