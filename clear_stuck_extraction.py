#!/usr/bin/env python3
"""Clear stuck extraction records from the database"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend" / "shared"))

from vora_shared.database import session_scope
from vora_shared.models import DocumentExtraction
from sqlalchemy import select

async def clear_stuck():
    """Clear all processing extractions"""
    async with session_scope() as session:
        # Find all processing extractions
        result = await session.execute(
            select(DocumentExtraction)
        )
        docs = result.scalars().all()
        
        stuck = [d for d in docs if isinstance(d.aiExtraction, dict) and d.aiExtraction.get("status") == "processing"]
        
        if not stuck:
            print("✅ No stuck extractions found")
            return
        
        print(f"Found {len(stuck)} stuck extractions:")
        for doc in stuck:
            print(f"  - {doc.id} | hash={doc.fileHash}")
            # Mark as failed
            doc.aiExtraction = {
                "status": "failed",
                "message": "Extraction was stuck, cleared by cleanup script",
                "timestamp": "2026-08-12T18:20:00Z"
            }
            session.add(doc)
        
        await session.commit()
        print(f"✅ Cleared {len(stuck)} stuck extractions")

if __name__ == "__main__":
    asyncio.run(clear_stuck())
