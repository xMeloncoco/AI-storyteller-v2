# 🤖 AI Setup Guide - Free AI Providers

This guide will help you set up FREE AI providers for Dreamwalkers. No credit card required!

## 🎯 Why Two Different AI Models?

Dreamwalkers uses a **two-tier AI system** for optimal performance and cost:

- **Small Model** (3B parameters): Fast, lightweight AI for quick checks
  - Character decision validation
  - Scene change detection
  - Flag/event checking
  - Simple analysis tasks

- **Large Model** (8B parameters): Powerful AI for story generation
  - Main story narration
  - Character dialogue
  - Complex scene descriptions
  - Creative responses

Using small models for simple tasks makes the app faster and reduces API costs!

---

## 🆓 Option 1: OpenRouter (Recommended)

OpenRouter provides access to multiple AI models, including **100% free options**.

### Step 1: Create Account

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Click "Sign In" → "Sign up with Google" (or email)
3. **No credit card required!**

### Step 2: Get API Key

1. Once logged in, click your profile → "Keys"
2. Click "Create Key"
3. Name it "Dreamwalkers" and click "Create"
4. **Copy the key** (starts with `sk-or-...`)
5. Keep it safe - you'll need it in Step 3

### Step 3: Configure Dreamwalkers

Create or edit `backend/.env`:

```bash
# AI Provider
AI_PROVIDER=openrouter

# Your OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# FREE Models (add :free suffix!)
SMALL_MODEL=meta-llama/llama-3.2-3b-instruct:free
LARGE_MODEL=meta-llama/llama-3.1-8b-instruct:free

# Optional: Adjust token limits
MAX_TOKENS_SMALL=500
MAX_TOKENS_LARGE=2000
```

### ⚠️ Important: The `:free` Suffix

The `:free` suffix is **critical**! Without it, you'll be charged.

✅ **Correct**: `meta-llama/llama-3.1-8b-instruct:free`
❌ **Wrong**: `meta-llama/llama-3.1-8b-instruct` (costs money!)

### Free Model Options

OpenRouter free tier includes:

**Small Models (for quick checks):**
- `meta-llama/llama-3.2-3b-instruct:free` (Recommended)
- `meta-llama/llama-3.2-1b-instruct:free` (Even faster)
- `google/gemma-2-9b-it:free`

**Large Models (for story generation):**
- `meta-llama/llama-3.1-8b-instruct:free` (Recommended)
- `microsoft/phi-3-medium-128k-instruct:free`
- `google/gemma-2-9b-it:free`

### Free Tier Limits

- **No cost** - completely free!
- Rate limits: ~10 requests/minute
- Perfect for personal use and development
- Requests go through OpenRouter's queue (may be slightly slower than paid)

---

## 🌟 Option 2: Nebius AI Studio

Nebius offers free credits for AI API access.

### Step 1: Create Account

1. Go to [Nebius AI Studio](https://studio.nebius.ai/)
2. Sign up with email or Google
3. **New users get free credits!**

### Step 2: Get API Key

1. Go to your dashboard
2. Navigate to "API Keys"
3. Click "Create New Key"
4. Copy the key

### Step 3: Configure Dreamwalkers

Create or edit `backend/.env`:

```bash
# AI Provider
AI_PROVIDER=nebius

# Your Nebius API Key
NEBIUS_API_KEY=your-nebius-key-here

# Models (check Nebius documentation for available models)
SMALL_MODEL=meta-llama/Llama-3.2-3B-Instruct
LARGE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct

# Token limits
MAX_TOKENS_SMALL=500
MAX_TOKENS_LARGE=2000
```

### Free Credits

- New accounts get free credits
- Check your Nebius dashboard for current balance
- Credits renew monthly

---

## 🧪 Option 3: Demo Mode (No AI Required)

Perfect for testing the app without setting up AI.

### Configure Demo Mode

Edit `backend/.env`:

```bash
# Use demo mode (no API key needed)
AI_PROVIDER=demo
```

### What Demo Mode Does

- Returns **mock/fake responses** instead of real AI
- Good for testing the UI and database
- **Not suitable for actual storytelling**
- Use this to verify the app works before setting up AI

---

## 🔧 Verifying Your Setup

### 1. Check Configuration

Start the backend:
```bash
cd backend
source venv/bin/activate
python -m app.main
```

Look for this in the startup logs:
```
AI Provider: openrouter (or nebius/demo)
Small Model: meta-llama/llama-3.2-3b-instruct:free
Large Model: meta-llama/llama-3.1-8b-instruct:free
```

### 2. Test in the App

1. Open the app
2. Go to **Settings** → **System Info**
3. Check:
   - **AI Provider**: Should show "openrouter" or "nebius"
   - **AI Configured**: Should show "Yes"

### 3. Try a Story

1. Load test data (Settings → Load All Test Data)
2. Select "Starling Contract" story
3. Create a playthrough
4. Send a message
5. If you get a response, AI is working! 🎉

---

## 🐛 Troubleshooting

### "AI not configured" error

**Check:**
1. `.env` file exists in `backend/` directory
2. API key is correctly copied (no extra spaces)
3. `AI_PROVIDER` matches your chosen provider
4. For OpenRouter: models have `:free` suffix

**Fix:**
```bash
cd backend
cat .env  # Check if file exists and looks correct
```

### "Invalid API key" error

**OpenRouter:**
- Make sure key starts with `sk-or-v1-`
- Key must be from openrouter.ai (not OpenAI!)
- Create a new key if needed

**Nebius:**
- Verify key in Nebius dashboard
- Check if free credits remain

### Slow responses

**This is normal for free tiers!**
- Free models use shared infrastructure
- Responses may take 10-30 seconds
- Faster than local AI, slower than paid tiers
- Be patient - it's free! 😊

### Rate limit errors

Free tiers have request limits:
- **OpenRouter**: ~10 requests/minute
- **Nebius**: Check your dashboard

**Solutions:**
- Wait a minute between requests
- Reduce `MAX_TOKENS` in `.env` to speed up responses
- Upgrade to paid tier if needed (optional)

---

## 💡 Tips for Best Results

### 1. Start with OpenRouter
- Easiest to set up
- Most reliable free tier
- Good model selection

### 2. Use Appropriate Token Limits
```bash
# Faster responses (recommended for testing)
MAX_TOKENS_SMALL=300
MAX_TOKENS_LARGE=1500

# More detailed responses (use if speed is ok)
MAX_TOKENS_SMALL=500
MAX_TOKENS_LARGE=2500
```

### 3. Monitor Your Usage
- OpenRouter: Check dashboard → Usage
- Nebius: Check credits in dashboard
- Both show how much you're using

### 4. Model Selection
- Larger models = better quality, slower
- Smaller models = faster, less creative
- Balance based on your needs!

---

## 🚀 Advanced: Local AI (Future)

Want to run AI completely offline? Future versions will support:
- **Ollama** - Run models on your PC
- **LM Studio** - Local model management
- No internet required!

*Stay tuned for updates!*

---

## 📞 Need Help?

1. **Check Settings → System Info** in the app
2. **View Logs** for error messages
3. **Try Demo Mode** to verify app works
4. **Re-read this guide** - most issues are simple config errors!

---

## ✅ Checklist

Before you start:
- [ ] Created OpenRouter or Nebius account
- [ ] Got API key
- [ ] Created `backend/.env` file
- [ ] Added `AI_PROVIDER` and API key
- [ ] Added `:free` suffix to OpenRouter models
- [ ] Started backend - no errors
- [ ] Settings → System Info shows "AI Configured: Yes"
- [ ] Tested with a story - got AI response

**All checked? You're ready to create stories! 🎉**

---

*Last updated: 2024-11-18*
