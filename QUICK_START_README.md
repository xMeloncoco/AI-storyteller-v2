# 🚀 Dreamwalkers - Quick Start Guide

## What You Have

You now have three comprehensive documents to guide your development:

1. **Dreamwalkers_MVP_Complete_Development_Guide.md** - The main roadmap
2. **Phase_by_Phase_Implementation_Guide.md** - Detailed code for each phase  
3. **This file** - Quick reference and tips

Plus your original design document from Google Docs with all the specifications.

---

## 📋 Before You Start

### Hardware Check
- ✅ Windows PC
- ✅ NVIDIA GTX 960 (2GB VRAM) or better
- ✅ 16GB RAM
- ✅ ~20GB free disk space

### Skills Check
- ✅ Basic understanding of Python
- ✅ Basic understanding of JavaScript  
- ✅ Comfortable with command line
- ✅ Can follow instructions step-by-step

**You don't need to be an expert programmer - the documents provide all the code!**

---

## 🎯 Your Development Journey

### Week 1: Setup (Phase 0)
**Time:** 4-6 hours  
**Goal:** Get everything installed and working

**What you'll do:**
- Install Python, Node.js, Ollama
- Download AI models
- Create project structure
- Test that everything connects

**When done:** You'll have a working test app that connects frontend to backend

### Weeks 2-4: Core Features (Phase 1)
**Time:** 20-30 hours  
**Goal:** Build the basic chat system

**What you'll do:**
- Create database
- Implement logging system
- Connect to AI models
- Build chat interface
- Add memory system

**When done:** You can chat with AI characters that remember context

### Weeks 5-7: Intelligence (Phase 2)
**Time:** 20-25 hours  
**Goal:** Make characters smart and consistent

**What you'll do:**
- Add character decision system
- Implement story arcs
- Add story progression tracking

**When done:** Characters act realistically and story stays on track

### Weeks 8-10: Polish (Phase 3)
**Time:** 15-20 hours  
**Goal:** Add relationship dynamics and final features

**What you'll do:**
- Dynamic relationship updates
- "Generate More" feature
- Session resume with history
- Final testing and bug fixes

**When done:** ✨ Full MVP complete!

---

## 📚 How to Use the Documents

### Starting Out
1. Open **Dreamwalkers_MVP_Complete_Development_Guide.md**
2. Read the Phase 0 section completely
3. Follow each step in order
4. Test at each checkpoint

### During Development
1. Keep Phase_by_Phase_Implementation_Guide.md open
2. Copy code examples directly
3. Read the comments in the code
4. Use logs extensively to understand what's happening

### When Stuck
1. Check the "Common Issues" sections
2. Look at your logs
3. Verify each step was completed
4. Ask Claude Code for help with specific errors

---

## 🛠️ Essential Commands

### Starting Development Environment

**Terminal 1 - Ollama (always run first):**
```bash
ollama serve
```

**Terminal 2 - Backend:**
```bash
cd C:\Projects\dreamwalkers\backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

**Terminal 3 - Frontend:**
```bash
cd C:\Projects\dreamwalkers\frontend
npm start
```

### Importing Test Data
```bash
cd backend
python test_data/import_test_data.py --story both --reset --create-playthroughs
```

### Checking Everything Works
- Backend health: http://localhost:8000/health
- Frontend: Opens automatically
- Check logs in the app

---

## 💡 Development Tips

### Working with Claude Code

**DO:**
- ✅ Work on one file at a time
- ✅ Test after every major change
- ✅ Use the logging system extensively
- ✅ Commit working versions to git
- ✅ Ask specific questions with error messages

**DON'T:**
- ❌ Try to implement multiple features at once
- ❌ Skip testing checkpoints
- ❌ Ignore error messages in logs
- ❌ Move to next phase before current one works

### Debugging Strategy

1. **Check logs first** - They show everything that's happening
2. **Verify database** - Use DB Browser for SQLite to inspect data
3. **Test endpoints** - Use the /health endpoint to verify backend
4. **One thing at a time** - Fix one issue before moving to next

### Performance Tips

**If responses are slow:**
- Reduce max_tokens in LLM calls
- Limit context size (fewer history messages)
- Use smaller model for more tasks
- Check Ollama is using GPU: `ollama ps`

**If memory issues:**
- Restart Ollama occasionally
- Clear old ChromaDB collections
- Limit conversation history shown

---

## 📊 Success Checkpoints

After each phase, verify:

### Phase 0 ✅
- [ ] All software installed
- [ ] Backend starts and shows "healthy"
- [ ] Frontend opens and connects to backend
- [ ] Ollama shows both models loaded

### Phase 1 ✅
- [ ] Database tables created
- [ ] Test data imported successfully
- [ ] Can send messages and get AI responses
- [ ] Logs show complete pipeline
- [ ] Memory is stored and retrieved

### Phase 2 ✅
- [ ] Characters can refuse user actions
- [ ] Character decisions appear in logs
- [ ] Story arcs activate and progress
- [ ] Narrative stays on track

### Phase 3 ✅
- [ ] Relationships update after interactions
- [ ] "Generate More" works
- [ ] Can resume sessions with history
- [ ] Both test stories work correctly
- [ ] Performance is acceptable (<15s per response)

---

## 🎮 Testing Your App

### Basic Test Flow

1. Start the app
2. Select Sterling Hearts story
3. Send: "I open the door and greet him coldly"
4. Verify: Alex responds according to his character
5. Check logs: See character decision analysis
6. Send: "I invite him in despite my feelings"
7. Verify: Response acknowledges relationship tension
8. Check logs: See relationship values updated

### Advanced Testing

1. Play through 20+ interactions
2. Try actions characters should refuse
3. Test with both stories (verify isolation)
4. Resume a session (verify history loads)
5. Use "Generate More" (verify continuation)
6. Check database (verify data structure)

---

## 🚨 Common Issues & Solutions

### "Cannot connect to Ollama"
**Solution:** 
```bash
ollama serve
ollama list  # Verify models are downloaded
```

### "Database locked" error
**Solution:** Close all connections, restart backend

### "Model not found"
**Solution:** 
```bash
ollama pull phi3:mini
ollama pull llama3.1:8b-instruct-q4_0
```

### AI responses are gibberish
**Solution:** Check that you're using the correct model name in .env

### Frontend can't connect to backend
**Solution:** Verify backend is running on port 8000, check CORS settings

### ChromaDB errors
**Solution:** Delete data/chroma folder and let it recreate

---

## 🎯 Your Next Steps

1. **Read Phase 0** in the main guide
2. **Install all software** following the instructions
3. **Create project structure** exactly as shown
4. **Test the setup** - make sure backend and frontend connect
5. **Start Phase 1** once everything works

---

## 💬 Getting Help

### From Claude Code

When asking for help, provide:
- Which phase/version you're on
- The specific file you're working on
- The complete error message
- What you've already tried
- Relevant logs from the app

**Example good question:**
"I'm on Phase 1.2, working on backend/app/routers/chat.py. When I send a message, I get this error: [paste error]. The logs show [paste relevant logs]. I've verified Ollama is running. What should I check?"

### Self-Debugging

1. Check logs in the app
2. Look at console output in frontend dev tools
3. Check backend terminal for Python errors
4. Verify database contents
5. Test endpoints individually

---

## 🎉 Final Thoughts

**This is a substantial project** - don't expect to finish in a few days. Take your time, test thoroughly, and celebrate each checkpoint.

**You have everything you need:**
- Complete specifications (your original doc)
- Development roadmap (main guide)
- All the code (phase guide)
- Testing procedures (in both guides)

**The documents are designed to be followed step-by-step.** Trust the process, and you'll have a working AI storytelling app!

---

**Ready to begin?**  
Open `Dreamwalkers_MVP_Complete_Development_Guide.md` and start with Phase 0.

**Good luck! 🚀**

