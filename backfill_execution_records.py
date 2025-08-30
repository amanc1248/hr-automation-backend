#!/usr/bin/env python3
"""
Backfill script to populate new fields in existing candidate_workflow_executions records.
This script fetches data from workflow_step_detail and workflow_step tables to populate
the new fields we added.
"""

import asyncio
import asyncpg
import os
from datetime import datetime

async def backfill_execution_records():
    """Backfill new fields in existing execution records"""
    
    # Database connection details
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database successfully")
        
        # Get all execution records that need backfilling
        print("🔍 Finding execution records to backfill...")
        records_result = await conn.fetch("""
            SELECT id, workflow_step_detail_id 
            FROM candidate_workflow_executions 
            WHERE order_number = 0 OR step_name = 'Unknown Step'
        """)
        
        if not records_result:
            print("✅ No records need backfilling - all fields are already populated!")
            return
        
        print(f"📋 Found {len(records_result)} records to backfill")
        
        # Process each record
        updated_count = 0
        for record in records_result:
            execution_id = record['id']
            step_detail_id = record['workflow_step_detail_id']
            
            try:
                # Get step detail and workflow step info
                step_detail_result = await conn.fetchrow("""
                    SELECT 
                        wsd.order_number,
                        wsd.auto_start,
                        wsd.required_human_approval,
                        wsd.number_of_approvals_needed,
                        wsd.approvers,
                        wsd.delay_in_seconds,
                        ws.name,
                        ws.step_type,
                        ws.description
                    FROM workflow_step_detail wsd
                    JOIN workflow_step ws ON wsd.workflow_step_id = ws.id
                    WHERE wsd.id = $1
                """, step_detail_id)
                
                if step_detail_result:
                    # Update the execution record with new field values
                    await conn.execute("""
                        UPDATE candidate_workflow_executions 
                        SET 
                            order_number = $1,
                            auto_start = $2,
                            required_human_approval = $3,
                            number_of_approvals_needed = $4,
                            approvers = $5,
                            delay_in_seconds = $6,
                            step_name = $7,
                            step_type = $8,
                            step_description = $9,
                            updated_at = NOW()
                        WHERE id = $10
                    """, 
                        step_detail_result['order_number'],
                        step_detail_result['auto_start'],
                        step_detail_result['required_human_approval'],
                        step_detail_result['number_of_approvals_needed'],
                        step_detail_result['approvers'] or [],
                        step_detail_result['delay_in_seconds'],
                        step_detail_result['name'],
                        step_detail_result['step_type'],
                        step_detail_result['description'],
                        execution_id
                    )
                    
                    updated_count += 1
                    print(f"✅ Updated execution record {execution_id} with step '{step_detail_result['name']}'")
                else:
                    print(f"⚠️ No step detail found for execution {execution_id}, step_detail_id: {step_detail_id}")
                    
            except Exception as e:
                print(f"❌ Failed to update execution {execution_id}: {e}")
        
        print(f"🎉 Backfill completed! Updated {updated_count} out of {len(records_result)} records")
        
        # Verify the backfill
        print("🔍 Verifying backfill results...")
        verification_result = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN order_number > 0 THEN 1 END) as with_order_number,
                COUNT(CASE WHEN step_name != 'Unknown Step' THEN 1 END) as with_step_name,
                COUNT(CASE WHEN step_type != 'unknown' THEN 1 END) as with_step_type
            FROM candidate_workflow_executions
        """)
        
        print(f"📊 Verification Results:")
        print(f"   Total records: {verification_result['total_records']}")
        print(f"   With order_number: {verification_result['with_order_number']}")
        print(f"   With step_name: {verification_result['with_step_name']}")
        print(f"   With step_type: {verification_result['with_step_type']}")
        
    except Exception as e:
        print(f"❌ Backfill failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'conn' in locals():
            await conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🚀 Starting execution records backfill...")
    print("=" * 50)
    asyncio.run(backfill_execution_records())
    print("=" * 50)
    print("🏁 Backfill script completed")
