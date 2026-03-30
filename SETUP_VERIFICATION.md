# Quick Setup & Verification Checklist

## ✓ What Was Fixed

The simulator page was showing "Something went wrong. Try again." error because:
1. It was making TWO sequential API calls without proper error handling
2. If either call failed, the entire operation failed
3. Error messages were generic instead of specific

**Solution:** 
- Make predictions first (required)
- Store results immediately (no waiting)
- Fetch contributions in background (non-blocking)
- Much better error handling with detailed logging

---

## ✓ Quick Setup (5 minutes)

### Terminal 1: Start Backend
```bash
cd /Users/anubrataghosh/Projects/Equidata/backend
PYTHONPATH=/Users/anubrataghosh/Projects/Equidata/backend \
  python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**You should see:**
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Terminal 2: Start Frontend
```bash
cd /Users/anubrataghosh/Projects/Equidata/frontend
npm run dev
```

**You should see:**
```
▲ Next.js 16.2.1 (Turbopack)
- Local:   http://localhost:3000
✓ Ready in XXms
```

---

## ✓ Manual Testing

### Step 1: Open Simulator
1. Go to http://localhost:3000/simulate
2. You should see the simulator form with fields like:
   - Experience (default: 4)
   - Education Level (default: bachelors)
   - Skills Score (default: 72)
   - etc.

### Step 2: Click "Get Decision"
1. Form should look valid (all required fields filled)
2. Click the "Get Decision" button
3. You should see:
   - Button changes to "Processing..."
   - After 1-2 seconds, results appear showing:
     - Biased Model: [Approved/Rejected] with confidence
     - Fair Model: [Approved/Rejected] with confidence
     - Bias Gap percentage

### Step 3: Check Browser Console (F12)
1. Open DevTools (F12)
2. Go to Console tab
3. You should see logs like:
   ```
   [Simulator] Starting prediction with payload: {...}
   [Simulator] Got prediction response: {...}
   [Simulator] Stored prediction snapshot (requestId: req_XXXXX)
   [Simulator] Fetching feature contributions... (optional, runs in background)
   ```

### Step 4: Test Audit Page
1. Click "Go to Audit" or navigate to http://localhost:3000/audit
2. You should see the exact same results
3. Feature contributions should display at the bottom
4. Refresh the audit page - same results should display

---

## ✓ If You Get an Error

### "Something went wrong" still appears?

**Check 1: Backend is running**
```bash
curl http://127.0.0.1:8000/
# Should return: {"status":"ok","message":"Equidata backend is running..."}
```

**Check 2: API endpoint works**
```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "hiring",
    "features": {
      "experience": 4,
      "education_level": "bachelors",
      "college_tier": "other",
      "skills_score": 72,
      "expected_salary": 90000,
      "gender": "female",
      "caste": "general",
      "religion": "hindu"
    }
  }'
# Should return: {"biased_prediction":"Approved",...}
```

**Check 3: Browser Console**
- Open DevTools (F12)
- Go to Console tab
- Click "Get Decision" again
- Look for `[Simulator]` logs or red error messages
- Take a screenshot of any errors

**Check 4: Network Tab**
- Open DevTools Network tab
- Click "Get Decision"
- Check if requests are being made
- Look for red/failed requests

---

## ✓ What to Expect

### Success Indicators:
✓ "Get Decision" button returns results in 1-2 seconds
✓ Results show Approved/Rejected and confidence percentage
✓ Audit page shows same results
✓ Audit page loads instantly (not showing loading spinner)
✓ Browser console shows `[Simulator]` logs (no red errors)

### What's Changed:
- First time: Might see "Fetching feature contributions..." in console (background task)
- Contributions might take an extra second to populate on audit page
- All very normal! Don't worry about it.

---

## ✓ If Everything Works

**Congratulations!** The fix is complete. The issue is resolved because:

1. ✓ Predictions are stored immediately after /predict call succeeds
2. ✓ Error handling is robust and specific (not "something went wrong")
3. ✓ Contributions fetch in background (non-blocking)
4. ✓ Audit page shows stored predictions (no recomputation)
5. ✓ Backend logs show what's happening for debugging

---

## ✓ Files Modified

```
frontend/app/simulate/page.tsx    ← Fixed error handling, added logging
frontend/app/audit/page.tsx       ← Made resilient to missing contributions
backend/app/main.py               ← Added debug logging (no functional changes)
```

---

## ✓ Common Questions

**Q: Why is predictions showing empty contributions initially?**
A: By design! Contributions fetch in background after prediction is stored. They'll populate within 1-2 seconds.

**Q: Can I still click "Get Decision" multiple times?**
A: Yes, each click creates a new request ID and stores new results.

**Q: What if audit page shows old results?**
A: That's the stored results from your last prediction. Click "Get Decision" again to refresh.

**Q: Is the 10-second timeout enough?**
A: Yes, predictions typically return in 1-2 seconds. 10 seconds is plenty of buffer.

---

## ✓ Next Steps

1. Run the setup commands above
2. Go to http://localhost:3000/simulate
3. Click "Get Decision"
4. Check browser console for logs
5. Open audit page
6. Verify results match

That's it! The fix should now be working.
