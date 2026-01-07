# Ecommerce Product Analysis Prompt

Use this prompt with Claude or ChatGPT after running product discovery. Paste your top products along with their sentiment data for analysis.

---

## THE PROMPT

```
You are an expert ecommerce product analyst specializing in dropshipping and direct-to-consumer products sold via paid social ads (Facebook/TikTok).

I will provide you with product data including Reddit sentiment and Amazon review sentiment. Your job is to:

1. SYNTHESIZE the sentiment data - what are real users actually saying?
2. IDENTIFY the core problem this product solves (based on user comments, not guessing)
3. ASSESS market opportunity and profit potential
4. SUGGEST target markets/angles I might not have considered

## FOR EACH PRODUCT, ANALYZE:

### SENTIMENT SYNTHESIS
- What specific problems/pain points do users mention?
- What do they love about products like this?
- What complaints or issues come up repeatedly?
- Is the overall sentiment genuinely positive or mixed?

### MARKET OPPORTUNITY (Score 0-50)
- Is there an untapped market/angle for this product?
- How saturated is the competition?
- Can I target a different demographic than existing sellers?
- Are competitors running ads long-term (validated) or short-term (unproven)?

Score Guide:
- 40-50: No/low competition OR clear untapped market angle
- 30-39: Some competition but room to differentiate
- 20-29: Competitive but validated market
- 0-19: Saturated, no clear angle

### PROFIT MARGIN POTENTIAL (Score 0-50)
- Can it realistically sell for 3x+ the COGS?
- Is the perceived value high enough for $30+ pricing?
- Is it lightweight (shipping won't kill margins)?
- Are there upsell/bundle opportunities?

Score Guide:
- 40-50: High perceived value, lightweight, easy 3x+ markup
- 30-39: Good margins possible with right positioning
- 20-29: Tight margins, may work with volume
- 0-19: Can't justify price needed for profit

## OUTPUT FORMAT

For each product:

**[PRODUCT NAME]**

**What Users Are Actually Saying:**
- Pain points mentioned: [from Reddit/Amazon comments]
- What they love: [from Reddit/Amazon comments]
- Common complaints: [from Reddit/Amazon comments]

**Market Analysis:**
- Target Market: [Specific demographic - age, gender, interest, lifestyle]
- Competition Status: [New/Growing/Saturated]
- Suggested Angle: [How to differentiate from existing sellers]

**Financials:**
- Estimated COGS: $XX (including shipping)
- Suggested Retail: $XX
- Margin: XX%
- Upsell Ideas: [bundles, accessories, etc.]

**SCORES:**
| Criteria | Score |
|----------|-------|
| Market Opportunity | /50 |
| Profit Margin | /50 |
| **TOTAL** | **/100** |

**VERDICT**: [STRONG BUY / TEST WORTHY / PASS / HARD PASS]

**WHY/WHY NOT** (2-3 sentences):
[Clear reasoning based on the data, not speculation]
```

---

## HOW TO USE

### Step 1: Run Discovery
```bash
python main.py --discover --max-products 30 --min-price 30
```

### Step 2: Quick Visual Review (10 mins)
- Open CSV report
- Check top products on Amazon for wow factor
- Pick 10-15 that look visually interesting

### Step 3: Get Sentiment Data
The bot already collected:
- Reddit sentiment score + post count
- (Optional) Amazon review sentiment

For TikTok data, check Kalodata for the products you're interested in.

### Step 4: Paste into Claude/ChatGPT
Include for each product:
- Product name and price
- Reddit sentiment data from the report
- Any TikTok/Kalodata insights you found
- Amazon review highlights if relevant

### Step 5: Make Decision
AI gives you market analysis, you decide based on:
- AI analysis (market + margins)
- Your wow factor assessment (visuals)
- Your ad creative availability (TikTok UGC)

---

## PRODUCTS TO AVOID

- Can't sell for $30+ (margins too thin)
- Heavy products (shipping kills margins)
- Extreme health claims (ads get banned)
- Adult/inappropriate items (ads get flagged)
- No clear problem solved (impulse buy won't happen)
- Completely saturated with no new angle

---

## THE 5 STAGES OF AWARENESS

Reference for targeting:

| Stage | Customer Mindset | Your Approach |
|-------|------------------|---------------|
| **Unaware** | Doesn't know they have a problem | Educate about problem first |
| **Problem Aware** | Knows problem, not solution | Speak SPECIFICALLY to their pain |
| **Solution Aware** | Knows solutions exist | Position as superior choice |
| **Product Aware** | Comparing products | Build trust, social proof |
| **Most Aware** | Ready to buy | Urgency, discounts, CTA |

---

## DATA SOURCES

| Source | What It Tells You | How to Get It |
|--------|-------------------|---------------|
| Reddit | Honest opinions, complaints, recommendations | Bot collects automatically |
| Amazon Reviews | Buyer experience, quality issues, satisfaction | Bot can collect (slower) |
| TikTok/Kalodata | Trend validation, ad performance, UGC availability | Check Kalodata manually |
| Facebook Ad Library | Competitor ad duration, creative styles | Search manually |
