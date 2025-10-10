# Backfill Missing Members Guide

## 🎯 Overview

This guide helps you find and create PassKit members for all Squarespace membership purchases that haven't been processed yet.

## 🔍 What This Does

1. **Fetches all Squarespace orders** (or processes CSV export)
2. **Filters for membership products only** (ignores scarves, merchandise)
3. **Checks each email** against existing PassKit members
4. **Creates missing members** in PassKit
5. **Triggers PassKit welcome emails** automatically

## 🛠️ Two Methods Available

### Method 1: API-Based Backfill (Recommended)
Uses Squarespace API to fetch all orders automatically.

### Method 2: CSV-Based Backfill
Processes CSV export from Squarespace manually.

## 🚀 Method 1: API-Based Backfill

### Prerequisites
- Squarespace API access
- API credentials configured

### Setup
1. **Get Squarespace API credentials:**
   - Go to Squarespace Settings > Advanced > API Keys
   - Create new API key with Commerce permissions
   - Note your Site ID

2. **Add to .env file:**
   ```bash
   SQUARESPACE_API_KEY=your_api_key_here
   SQUARESPACE_SITE_ID=your_site_id_here
   ```

3. **Run backfill:**
   ```bash
   python3 backfill_missing_members.py
   ```

### What It Does
- ✅ **Fetches ALL orders** from Squarespace automatically
- ✅ **Filters membership products** (ignores scarves, etc.)
- ✅ **Checks existing members** by email address
- ✅ **Creates missing members** with PassKit welcome emails
- ✅ **Generates detailed report** of what was processed

## 📄 Method 2: CSV-Based Backfill

### Prerequisites
- CSV export from Squarespace
- No API access needed

### Setup
1. **Export orders from Squarespace:**
   - Go to Commerce > Orders
   - Export all orders as CSV
   - Save as `squarespace_orders_export.csv`

2. **Run CSV backfill:**
   ```bash
   python3 backfill_from_csv.py squarespace_orders_export.csv
   ```

### CSV Requirements
Your CSV should include these columns:
- **Customer Email** - Email address of the customer
- **Customer First Name** - First name
- **Customer Last Name** - Last name  
- **Customer Phone** - Phone number (optional)
- **Product Name** - Name of the product purchased
- **Order Number** - Unique order identifier
- **Order Date** - Date of purchase

## 🎯 Product Filtering

### ✅ Membership Products (Will Process)
- "membership"
- "olsc membership"
- "liverpool olsc membership"
- "supporters club membership"
- "annual membership"
- "yearly membership"

### ❌ Excluded Products (Will Ignore)
- "scarf"
- "merchandise"
- "shirt"
- "jersey"
- "hat"
- "mug"
- "pin"
- "badge"

### Customizing Product Filters
Edit the product lists in the script:
```python
MEMBERSHIP_PRODUCTS = [
    "membership",
    "olsc membership",
    # Add your specific product names
]

EXCLUDED_PRODUCTS = [
    "scarf",
    "merchandise", 
    # Add products to exclude
]
```

## 📊 What You'll See

### During Processing
```
🔄 Liverpool OLSC - Backfill Missing Members
==================================================
📥 Fetching Squarespace orders...
✅ Fetched 1,234 total orders from Squarespace
🎯 Filtering for membership orders...
🎯 Found 89 orders containing membership products
🔍 Checking existing PassKit members...

👤 Checking: john@example.com
  ✅ Already exists in PassKit

👤 Checking: jane@example.com  
  ❌ Missing from PassKit

📝 Creating 15 missing members...

👤 Creating member: jane@example.com
  ✅ Created successfully - Member ID: abc123
  📧 PassKit welcome email triggered
```

### Final Summary
```
📊 Backfill Summary:
  📥 Total Squarespace orders: 1,234
  🎯 Membership orders found: 89
  ✅ Already in PassKit: 74
  🆕 New members created: 15
  ❌ Failed creations: 0

🆕 New Members Created:
  • jane@example.com (Order: #12345)
  • bob@example.com (Order: #12346)
  • alice@example.com (Order: #12347)
  ...

💾 Results saved to backfill_results_20250109_143022.json
```

## 🔐 Security & Safety

### What's Safe
- ✅ **Read-only Squarespace access** - Only fetches order data
- ✅ **Duplicate prevention** - Won't create duplicate members
- ✅ **Product filtering** - Only processes membership purchases
- ✅ **Email validation** - Skips orders without email addresses

### What Happens
- ✅ **Creates missing members** in PassKit
- ✅ **Triggers welcome emails** via PassKit's built-in system
- ✅ **Sets default values** ("Some inferior side" for next match)
- ✅ **Tracks backfill source** in member metadata

### What Doesn't Happen
- ❌ **No duplicate members** - Checks existing emails first
- ❌ **No spam emails** - Only sends to genuinely missing members
- ❌ **No data modification** - Doesn't change existing members
- ❌ **No product changes** - Only processes memberships

## 📧 Welcome Email Behavior

### For New Members Created
- ✅ **PassKit welcome email sent** automatically
- ✅ **Pass download link included**
- ✅ **Professional PassKit branding**
- ✅ **Ready to add to phone wallet**

### For Existing Members
- ✅ **No duplicate created**
- ✅ **No email sent** (prevents spam)
- ✅ **Existing member data preserved**

## 🧪 Testing First

### Dry Run Option
Before running the full backfill, you can test with a small subset:

1. **Create test CSV** with a few recent orders
2. **Run CSV backfill** on test file
3. **Verify results** before full backfill
4. **Proceed with confidence**

### Test Command
```bash
# Test with small CSV first
python3 backfill_from_csv.py test_orders.csv
```

## 📋 Pre-Backfill Checklist

### Before Running
- [ ] **PassKit API configured** (API keys in .env)
- [ ] **Squarespace access** (API keys or CSV export)
- [ ] **Backup existing data** (optional but recommended)
- [ ] **Test with small dataset** (recommended)
- [ ] **Verify product filters** (membership vs merchandise)

### After Running
- [ ] **Check welcome emails** (verify they're being sent)
- [ ] **Review results file** (JSON report generated)
- [ ] **Test pass downloads** (try a few new passes)
- [ ] **Update new member script** (for future automation)

## 🔧 Troubleshooting

### Common Issues

#### 1. "No Squarespace API credentials"
**Solution:** Add `SQUARESPACE_API_KEY` and `SQUARESPACE_SITE_ID` to .env file

#### 2. "No membership orders found"
**Solution:** Check product names in your Squarespace store, update product filters

#### 3. "API rate limit exceeded"
**Solution:** Wait a few minutes and try again, or use CSV method instead

#### 4. "PassKit member creation failed"
**Solution:** Check PassKit API keys and configuration

### Getting Help
- **Check logs** - Detailed error messages in console output
- **Review results file** - JSON file with complete results
- **Test API connection** - Run `python3 test_connection.py` first
- **Verify credentials** - Ensure all API keys are correct

## 📈 Expected Results

### Typical Outcomes
- **70-90% already exist** - Most recent purchases already processed
- **10-30% missing** - Older purchases or manual entries
- **0-5% failures** - Usually due to invalid email addresses

### Time Estimates
- **Small store (< 100 orders):** 2-5 minutes
- **Medium store (100-1000 orders):** 5-15 minutes  
- **Large store (1000+ orders):** 15-30 minutes

### Success Metrics
- ✅ **All membership purchases processed**
- ✅ **No duplicate members created**
- ✅ **Welcome emails sent successfully**
- ✅ **Detailed report generated**

## 🎯 Next Steps After Backfill

### Immediate Actions
1. **Check welcome emails** - Verify new members receive passes
2. **Test pass downloads** - Try downloading a few new passes
3. **Review results** - Check the generated JSON report
4. **Update processes** - Set up automation for future purchases

### Long-term Improvements
1. **Set up webhook automation** - Prevent future backfills
2. **Regular monitoring** - Check for missing members monthly
3. **Product optimization** - Ensure clear membership product names
4. **Process documentation** - Document your specific workflow

---

**Ready to find and create all your missing Liverpool OLSC members? 🚀⚽**

This backfill process will ensure every membership purchase gets their digital pass!
