from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title="Origination Platform API", version="0.1.0")

# Restrict CORS to known dev origins and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
        "https://demoema.vercel.app", # Potential production URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_TARGETS = [
    {
        "id": "co-1",
        "name": "TechFlow Industrials",
        "sector": "Industrial Tech",
        "priorityScore": 89,
        "signals": ["CFO Replacement", "Spin-off Rumors", "Historical Hold ~5Y"],
        "dealType": "Carve-out / Buyout",
        "timeframe": "3-6 Months",
        "accessibility": "High (Warm Intro via John Doe)",
        "scores": { "transmission": 85, "transaction": 92, "preparation": 88, "relationship": 90, "timing": 89 },
    },
    {
        "id": "co-2",
        "name": "Aetherial SA",
        "sector": "Renewable Energy",
        "priorityScore": 76,
        "signals": ["Succession Signal (Founder > 65)", "Secondary Buyout"],
        "dealType": "Sponsor-to-Sponsor",
        "timeframe": "9-12 Months",
        "accessibility": "Medium (Cold via LinkedIn)",
        "scores": { "transmission": 70, "transaction": 82, "preparation": 74, "relationship": 60, "timing": 95 },
    },
    {
        "id": "co-3",
        "name": "NexSphere Healthcare",
        "sector": "MedTech",
        "priorityScore": 68,
        "signals": ["Holding Vehicle Creation", "Private Equity Backed"],
        "dealType": "Build-up / Platform",
        "timeframe": "12-18 Months",
        "accessibility": "Low",
        "scores": { "transmission": 65, "transaction": 70, "preparation": 75, "relationship": 45, "timing": 85 },
    },
    {
        "id": "co-4",
        "name": "Blue Harbor Log",
        "sector": "Logistics",
        "priorityScore": 94,
        "signals": ["Asset Disposal", "Owner Debt Issues"],
        "dealType": "Distressed / special",
        "timeframe": "0-3 Months",
        "accessibility": "High",
        "scores": { "transmission": 90, "transaction": 98, "preparation": 85, "relationship": 70, "timing": 98 },
    },
    {
        "id": "co-5",
        "name": "Horizon Solar",
        "sector": "Renewable Energy",
        "priorityScore": 82,
        "signals": ["Series C extension", "New Market Entry"],
        "dealType": "Growth Equity",
        "timeframe": "6-12 Months",
        "accessibility": "Medium",
        "scores": { "transmission": 60, "transaction": 75, "preparation": 90, "relationship": 80, "timing": 70 },
    },
    {
        "id": "co-6",
        "name": "CyberGrid Solutions",
        "sector": "SaaS",
        "priorityScore": 71,
        "signals": ["Board Member Departure", "Audit Change"],
        "dealType": "Take-Private",
        "timeframe": "12-24 Months",
        "accessibility": "Low",
        "scores": { "transmission": 50, "transaction": 60, "preparation": 80, "relationship": 40, "timing": 85 },
    }
]

@app.get("/api/targets")
def get_targets(
    q: str = Query(None, description="Search query for target name or sector"),
    sector: str = Query(None, description="Filter by sector")
):
    results = MOCK_TARGETS
    
    if q:
        q_lower = q.lower()
        results = [
            t for t in results 
            if q_lower in t["name"].lower() or q_lower in t["sector"].lower()
        ]
    
    if sector:
        results = [t for t in results if t["sector"].lower() == sector.lower()]
        
    return {"data": results}

@app.get("/api/targets/{target_id}")
def get_target(target_id: str):
    target = next((t for t in MOCK_TARGETS if t["id"] == target_id), None)
    if target:
        return {"data": target}
    raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found")

@app.get("/api/copilot/query")
def copilot_query(q: str = Query(..., min_length=1, description="Natural language query")):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    time.sleep(1)  # Simulate LLM latency

    # Mock hardcoded natural language responses based on keywords
    q_lower = q.lower()
    if "france" in q_lower:
        return {"response": "I found 14 founder-led industrial companies in France exhibiting succession signals (founders older than 62, holding companies restructured recently). The top match is 'Industrie Lumiere SA' with a Transmission Score of 88."}
    if "industrial" in q_lower:
        return {"response": "There is a strong cluster of transaction preparation events in Industrial Software over the last 90 days. 7 companies have recently restructured their holding vehicles."}
    if "succession" in q_lower:
        return {"response": "I identified 23 succession signals across Europe this quarter — primarily in family-owned industrials. Aetherial SA ranks highest, with the founder aged 67 and no named successor."}
    if "pipeline" in q_lower or "priorit" in q_lower:
        return {"response": "Your top 3 priorities by combined score are: TechFlow Industrials (89), Aetherial SA (76), and NexSphere Healthcare (68). TechFlow has the shortest estimated transaction window at 3-6 months."}
    return {"response": "Based on our data signals, there's a strong cluster of transaction preparation events in Industrial Software over the last 90 days. Would you like me to narrow this down by geography or deal type?"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

