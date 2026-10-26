"""
Goldmine AI — Prisma Client Setup

Singleton Prisma client for direct database interactions.
"""

from prisma import Prisma

# Global Prisma client instance
prisma = Prisma()

async def connect_prisma():
    """Connect to the database via Prisma."""
    await prisma.connect()

async def disconnect_prisma():
    """Disconnect from the database."""
    if prisma.is_connected():
        await prisma.disconnect()
