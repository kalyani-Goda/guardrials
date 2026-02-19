# **Quick Start - 5 Minutes to Running**

## **TL;DR (Too Long; Didn't Read)**

Your project now uses:
- **LLM**: Google Gemini (FREE, cloud)
- **Database**: SQLite (FREE, local)
- **Cache**: Redis (FREE, local)
- **Everything else**: Local

**Cost**: $0/month

---

## **Setup (Copy-Paste Commands)**

### **1. Get Google API Key**
```bash
# Open in browser:
# https://aistudio.google.com/app/apikeys
# Click "Create API Key"
# Copy the key
```

### **2. Setup Files**
```bash
cd /Users/kalyani/Desktop/Projects/guardrials

cp .env.example .env

# Edit .env and add your key (replace YOUR_KEY)
# GOOGLE_API_KEY=YOUR_KEY
```

### **3. Install Redis**
```bash
brew install redis
redis-server  # Keep this running!
```

### **4. Install Python Packages**
```bash
source .venv/bin/activate

pip install -r requirements.txt

python -m spacy download en_core_web_sm
```

### **5. Run It!**
```bash
python examples.py
```

---

## **What You're Running**

```
Patient Input
    ↓
[Remove PII] ← Local (Presidio)
    ↓
[Check if Emergency] ← Local (Regex)
    ↓
[Get Medical Advice] ← Cloud (Google Gemini)
    ↓
[Save to Database] ← Local (SQLite)
    ↓
[Nurse Approves] ← Local (SQLite)
    ↓
Patient Response
```

---

## **Files You Need to Know**

| File | Purpose | Location |
|------|---------|----------|
| **.env** | Your secrets | Local (don't share!) |
| **app/google_llm_integration.py** | Google API wrapper | Local (you created) |
| **app/local_database.py** | SQLite management | Local (you created) |
| **medi_triage.db** | Database file | Created automatically |

---

## **Troubleshooting (Copy-Paste)**

### **"GOOGLE_API_KEY not set"**
```bash
cat .env | grep GOOGLE_API_KEY
# Should show a key, not empty
```

### **"Cannot connect to Redis"**
```bash
redis-cli ping
# Should print: PONG
# If not, run: redis-server
```

### **"ModuleNotFoundError"**
```bash
pip install -r requirements.txt
```

### **"database is locked"**
```bash
# Just restart the script
# SQLite will handle it automatically
```

---

## **Verify It Works**

```bash
# Test 1: Google API
python -c "from app.google_llm_integration import get_google_llm; llm = get_google_llm(); print('✓ Google API working')"

# Test 2: Database
python -c "from app.local_database import get_local_database; db = get_local_database(); print('✓ Database working')"

# Test 3: Redis
redis-cli ping
# Should print: PONG

# Test 4: Full system
python examples.py
```

---

## **Next: Advanced**

```bash
# Run all tests
pytest tests/ -v

# Check database contents
sqlite3 medi_triage.db "SELECT * FROM triage_sessions;"

# Check Redis cache
redis-cli KEYS "*"

# View logs
tail -f medi_triage.log
```

---

## **Architecture Summary**

```
┌─────────────────────────────────────────────────┐
│         YOUR LOCAL MACHINE                      │
├─────────────────────────────────────────────────┤
│  • SQLite Database (medi_triage.db)            │
│  • Redis Cache (localhost:6379)                │
│  • Presidio (PII removal)                      │
│  • ChromaDB (Clinical protocols)               │
│                                                 │
│  ┌──────────────────────────────────────────┐ │
│  │  Google Gemini API (ONLY LLM CALLS)      │ │
│  │  Free tier: 60 requests/minute           │ │
│  └──────────────────────────────────────────┘ │
│         (Connected to internet)                │
└─────────────────────────────────────────────────┘
```

---

## **Questions?**

1. **Configuration**: See `.env.example`
2. **How it works**: Read `UNDERSTANDING_CHANGES.md`
3. **Detailed setup**: Read `EXECUTION_GUIDE.md`
4. **Issues**: Check `config/logging_config.py` for error logs

---

**Ready?** Run `python examples.py` now! 🚀
