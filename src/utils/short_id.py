"""
Short ID generation utilities for the HR automation system.
"""
import random
import string
from typing import Set, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def generate_short_id(length: int = 6, prefix: str = "") -> str:
    """
    Generate a random short ID using uppercase letters and numbers.
    
    Args:
        length: Length of the random part (default: 6)
        prefix: Optional prefix to add (default: empty)
        
    Returns:
        Short ID string like "ABC123" or "JOB-ABC123" if prefix provided
    """
    # Use uppercase letters and numbers for readability
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    
    if prefix:
        return f"{prefix}-{random_part}"
    return random_part


async def generate_unique_job_short_id(db: AsyncSession, max_attempts: int = 10) -> str:
    """
    Generate a unique short ID for a job posting.
    
    Args:
        db: Database session
        max_attempts: Maximum attempts to generate unique ID
        
    Returns:
        Unique short ID for job
        
    Raises:
        RuntimeError: If unable to generate unique ID after max_attempts
    """
    from models.job import Job
    
    for attempt in range(max_attempts):
        # Generate format: JOB123 (6 chars total)
        short_id = generate_short_id(length=3, prefix="JOB")
        
        # Check if this ID already exists
        result = await db.execute(
            select(Job.id).where(Job.short_id == short_id)
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            return short_id
    
    # If we get here, we couldn't generate a unique ID
    raise RuntimeError(f"Failed to generate unique job short ID after {max_attempts} attempts")


def format_email_subject(base_subject: str, job_short_id: str) -> str:
    """
    Format an email subject with job short ID prefix.
    
    Args:
        base_subject: The original subject line
        job_short_id: The job's short ID (e.g., "JOB123")
        
    Returns:
        Formatted subject like "[JOB-ABC123] Technical Assessment - Full Stack Developer"
    """
    return f"[{job_short_id}] {base_subject}"


# Example usage:
"""
# Generate a short ID
short_id = generate_short_id()  # -> "ABC123"
short_id = generate_short_id(prefix="JOB")  # -> "JOB-ABC123"

# Generate unique job short ID
job_short_id = await generate_unique_job_short_id(db)  # -> "JOB123"

# Format email subject
subject = format_email_subject("Technical Assessment - Full Stack Developer", "JOB123")
# -> "[JOB123] Technical Assessment - Full Stack Developer"
"""
