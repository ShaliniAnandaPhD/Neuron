#!/usr/bin/env python3
"""
Database Initialization Script for LLaMA3 Neuron Framework
Creates required database tables and initial data
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from config import POSTGRES_URL, get_logger

logger = get_logger(__name__)

# SQL statements for table creation
CREATE_TABLES_SQL = """
-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(255) PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(50) DEFAULT 'medium',
    pattern VARCHAR(50),
    payload JSONB NOT NULL,
    result JSONB,
    error TEXT,
    assigned_agent VARCHAR(255),
    parent_task_id UUID,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    timeout_seconds INT DEFAULT 300,
    execution_time FLOAT,
    token_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    FOREIGN KEY (assigned_agent) REFERENCES agents(agent_id) ON DELETE SET NULL,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

-- Results table
CREATE TABLE IF NOT EXISTS results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    request_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    result JSONB,
    pattern_used VARCHAR(50),
    agents_involved TEXT[],
    total_tokens INT DEFAULT 0,
    processing_time_ms FLOAT,
    error TEXT,
    warnings TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

-- Metrics table
CREATE TABLE IF NOT EXISTS metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    unit VARCHAR(50),
    labels JSONB DEFAULT '{}'::jsonb,
    aggregation_type VARCHAR(50) DEFAULT 'gauge',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orchestration events table
CREATE TABLE IF NOT EXISTS orchestration_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(255) NOT NULL,
    target VARCHAR(255),
    pattern VARCHAR(50),
    task_id UUID,
    message_id UUID,
    latency_ms FLOAT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metrics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent ON tasks(assigned_agent);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_results_task_id ON results(task_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(metric_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_task_id ON orchestration_events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON orchestration_events(created_at);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

# Initial data
INSERT_INITIAL_DATA_SQL = """
-- Insert default agent configurations
INSERT INTO agents (agent_id, agent_type, status, metadata) VALUES
    ('intake_01', 'intake', 'offline', '{"max_concurrent_tasks": 10, "timeout_seconds": 30}'),
    ('analysis_01', 'analysis', 'offline', '{"max_concurrent_tasks": 5, "timeout_seconds": 120}'),
    ('synthesis_01', 'synthesis', 'offline', '{"max_concurrent_tasks": 3, "timeout_seconds": 180}'),
    ('output_01', 'output', 'offline', '{"max_concurrent_tasks": 8, "timeout_seconds": 60}'),
    ('qc_01', 'quality_control', 'offline', '{"max_concurrent_tasks": 5, "timeout_seconds": 45}'),
    ('crosscheck_01', 'cross_check', 'offline', '{"max_concurrent_tasks": 5, "timeout_seconds": 45}')
ON CONFLICT (agent_id) DO NOTHING;
"""

async def create_database():
    """Create database if it doesn't exist"""
    # Parse connection URL
    import urllib.parse
    parsed = urllib.parse.urlparse(POSTGRES_URL)
    
    # Connect to default postgres database
    default_dsn = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"
    
    try:
        conn = await asyncpg.connect(default_dsn)
        
        # Check if database exists
        db_name = parsed.path.lstrip('/')
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)",
            db_name
        )
        
        if not exists:
            # Create database
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Created database: {db_name}")
        else:
            logger.info(f"Database already exists: {db_name}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise

async def init_tables():
    """Initialize database tables"""
    try:
        # Connect to the application database
        conn = await asyncpg.connect(POSTGRES_URL)
        
        # Create tables
        logger.info("Creating tables...")
        await conn.execute(CREATE_TABLES_SQL)
        
        # Insert initial data
        logger.info("Inserting initial data...")
        await conn.execute(INSERT_INITIAL_DATA_SQL)
        
        # Verify tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        
        logger.info(f"Created tables: {[t['tablename'] for t in tables]}")
        
        await conn.close()
        logger.info("Database initialization complete")
        
    except Exception as e:
        logger.error(f"Error initializing tables: {e}")
        raise

async def main():
    """Main initialization function"""
    logger.info("Starting database initialization...")
    
    try:
        # Create database if needed
        await create_database()
        
        # Initialize tables
        await init_tables()
        
        logger.info("Database initialization successful!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())