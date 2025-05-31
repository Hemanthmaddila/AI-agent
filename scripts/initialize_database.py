#!/usr/bin/env python3
"""
Database initialization script for the AI Job Application Agent.
This script creates the SQLite database and sets up all necessary tables.
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add the project root to Python path so we can import our modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config.settings import DATABASE_URL, PROJECT_ROOT
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

def create_database_schema():
    """Create all necessary tables for the AI job application agent."""
    
    # Extract the database path from DATABASE_URL
    # DATABASE_URL format: sqlite:///path/to/database.db
    db_path = DATABASE_URL.replace('sqlite:///', '')
    
    print(f"🗄️  Initializing database at: {db_path}")
    print("=" * 60)
    
    # Ensure the data directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"✅ Created database directory: {db_dir}")
    
    try:
        # Connect to SQLite database (creates file if it doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 Creating database tables...")
        
        # 1. User Profiles Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                location TEXT,
                job_title TEXT,
                experience_years INTEGER,
                skills TEXT,  -- JSON string of skills array
                education TEXT,  -- JSON string of education details
                resume_path TEXT,  -- Path to the resume file
                cover_letter_template TEXT,
                linkedin_url TEXT,
                portfolio_url TEXT,
                preferences TEXT,  -- JSON string of job preferences
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created user_profiles table")
        
        # 2. Job Postings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_postings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,  -- External job ID from job board
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                job_type TEXT,  -- full-time, part-time, contract, etc.
                remote_option TEXT,  -- remote, hybrid, on-site
                salary_min INTEGER,
                salary_max INTEGER,
                currency TEXT DEFAULT 'USD',
                description TEXT,
                requirements TEXT,
                benefits TEXT,
                application_url TEXT,
                company_website TEXT,
                source TEXT,  -- indeed, linkedin, company website, etc.
                source_url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score REAL,  -- AI-calculated relevance score
                relevance_reasons TEXT,  -- JSON string of relevance analysis
                status TEXT DEFAULT 'discovered',  -- discovered, analyzed, applied, rejected
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created job_postings table")
        
        # 3. Applications Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_profile_id INTEGER NOT NULL,
                job_posting_id INTEGER NOT NULL,
                application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',  -- pending, submitted, interview, rejected, offer
                application_method TEXT,  -- automated, manual, email
                resume_version TEXT,  -- Path to the specific resume used
                cover_letter TEXT,  -- Cover letter content
                application_url TEXT,  -- URL where application was submitted
                confirmation_number TEXT,
                follow_up_date DATE,
                interview_date TIMESTAMP,
                notes TEXT,
                response_received TEXT,  -- JSON string of responses
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_profile_id) REFERENCES user_profiles (id),
                FOREIGN KEY (job_posting_id) REFERENCES job_postings (id)
            )
        """)
        print("✅ Created applications table")
        
        # 4. AI Interactions Table (for tracking Gemini API usage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_type TEXT NOT NULL,  -- resume_analysis, job_analysis, cover_letter_generation, etc.
                user_profile_id INTEGER,
                job_posting_id INTEGER,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model_used TEXT,
                tokens_used INTEGER,
                processing_time REAL,  -- Time in seconds
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_profile_id) REFERENCES user_profiles (id),
                FOREIGN KEY (job_posting_id) REFERENCES job_postings (id)
            )
        """)
        print("✅ Created ai_interactions table")
        
        # 5. Search Queries Table (for tracking job searches)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_profile_id INTEGER NOT NULL,
                query_terms TEXT NOT NULL,
                location TEXT,
                job_type TEXT,
                remote_option TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                source TEXT NOT NULL,  -- indeed, linkedin, etc.
                results_count INTEGER DEFAULT 0,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_profile_id) REFERENCES user_profiles (id)
            )
        """)
        print("✅ Created search_queries table")
        
        # 6. Application Log Table (for detailed tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                action TEXT NOT NULL,  -- form_filled, submitted, error, response_received
                details TEXT,  -- JSON string of action details
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications (id)
            )
        """)
        print("✅ Created application_logs table")
        
        # Create indexes for better performance
        print("\n🚀 Creating database indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_job_postings_status ON job_postings(status)",
            "CREATE INDEX IF NOT EXISTS idx_job_postings_source ON job_postings(source)",
            "CREATE INDEX IF NOT EXISTS idx_job_postings_relevance ON job_postings(relevance_score)",
            "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)",
            "CREATE INDEX IF NOT EXISTS idx_applications_date ON applications(application_date)",
            "CREATE INDEX IF NOT EXISTS idx_ai_interactions_type ON ai_interactions(interaction_type)",
            "CREATE INDEX IF NOT EXISTS idx_search_queries_date ON search_queries(executed_at)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("✅ Created database indexes")
        
        # Insert a sample user profile for testing
        print("\n👤 Creating sample user profile...")
        
        sample_profile = """
            INSERT OR IGNORE INTO user_profiles 
            (profile_name, full_name, email, phone, location, job_title, experience_years, skills, preferences)
            VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(sample_profile, (
            'default',
            'AI Job Seeker',
            'user@example.com',
            '555-0123',
            'Remote',
            'Software Developer',
            3,
            '["Python", "Django", "REST APIs", "Machine Learning", "SQL"]',
            '{"job_type": "full-time", "remote_preference": "remote", "salary_min": 70000}'
        ))
        
        print("✅ Created sample user profile")
        
        # Commit changes
        conn.commit()
        print("\n✅ Database initialization completed successfully!")
        
        # Show table statistics
        print("\n📈 Database Statistics:")
        tables = ['user_profiles', 'job_postings', 'applications', 'ai_interactions', 'search_queries', 'application_logs']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} records")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_database():
    """Verify that the database was created correctly."""
    
    print("\n🔍 Verifying database structure...")
    print("=" * 60)
    
    db_path = DATABASE_URL.replace('sqlite:///', '')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        expected_tables = {'user_profiles', 'job_postings', 'applications', 'ai_interactions', 'search_queries', 'application_logs'}
        actual_tables = {table[0] for table in tables}
        
        print(f"📊 Found {len(actual_tables)} tables: {', '.join(sorted(actual_tables))}")
        
        missing_tables = expected_tables - actual_tables
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        
        extra_tables = actual_tables - expected_tables
        if extra_tables:
            print(f"ℹ️  Extra tables: {', '.join(extra_tables)}")
        
        # Test a simple query
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        user_count = cursor.fetchone()[0]
        print(f"✅ Database query test successful: {user_count} user profile(s)")
        
        print("✅ Database verification completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting Database Initialization")
    print("=" * 60)
    
    # Create database schema
    schema_success = create_database_schema()
    
    if schema_success:
        # Verify database was created correctly
        verification_success = verify_database()
        
        if verification_success:
            print("\n🎉 Database setup completed successfully!")
            print("💡 Your AI Job Application Agent database is ready for use.")
            print(f"📍 Database location: {DATABASE_URL.replace('sqlite:///', '')}")
        else:
            print("\n❌ Database verification failed.")
            sys.exit(1)
    else:
        print("\n❌ Database creation failed.")
        sys.exit(1)
    
    print("\n" + "=" * 60) 