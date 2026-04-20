import os
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP, Context

# Load environment variables from .env file
load_dotenv()

# 1. Configuration (No more hardcoding!)
HEADER_NAME = os.getenv("API_KEY_HEADER", "X-API-Key")
SECRET_VALUE = os.getenv("API_KEY_VALUE")
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")

if not SECRET_VALUE:
    raise ValueError("CRITICAL: API_KEY_VALUE not found in environment. Check your .env file.")

mcp = FastMCP("Guardrail-FHIR-Link")

# Security Helper
def is_authorized(ctx: Context):
    headers = getattr(ctx, "headers", {})
    # Checks both lowercase and original for robustness
    return headers.get(HEADER_NAME.lower()) == SECRET_VALUE or headers.get(HEADER_NAME) == SECRET_VALUE

@mcp.tool()
async def get_patient_summary(patient_id: str, ctx: Context) -> str:
    """Fetch clinical conditions for a synthetic patient from FHIR."""
    if not is_authorized(ctx):
        return "Error: Unauthorized. Missing or invalid security header."

    url = f"{FHIR_BASE_URL}/Condition?patient={patient_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            entries = data.get('entry', [])
            conditions = [e['resource']['code']['text'] for e in entries if 'text' in e.get('resource', {}).get('code', {})]
            return f"Conditions for {patient_id}: {', '.join(set(conditions))}" if conditions else "No data."
        except Exception as e:
            return f"FHIR Error: {str(e)}"

@mcp.tool()
async def check_medications(patient_id: str, ctx: Context) -> str:
    """Check for active medications for a patient."""
    if not is_authorized(ctx):
        return "Error: Unauthorized."

    url = f"{FHIR_BASE_URL}/MedicationRequest?patient={patient_id}&status=active"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            entries = data.get('entry', [])
            meds = [e['resource'].get('medicationCodeableConcept', {}).get('text') for e in entries]
            meds = [m for m in meds if m]
            return f"Active Meds for {patient_id}: {', '.join(set(meds))}" if meds else "None found."
        except Exception as e:
            return f"Medication Fetch Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="sse", port=8000)