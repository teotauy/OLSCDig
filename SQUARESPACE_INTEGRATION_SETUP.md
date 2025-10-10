# Squarespace to PassKit Integration Setup

## 🎯 Overview

This integration automatically creates PassKit members and sends welcome emails when someone submits your Squarespace membership form.

## 🔄 How It Works

1. **User fills out form** on your Squarespace website
2. **Squarespace sends webhook** to your server
3. **Your server creates PassKit member** automatically
4. **Welcome email sent** with pass download link
5. **User downloads pass** to their phone

## 📋 Prerequisites

### Required Accounts & Services
- ✅ **PassKit account** (you already have this)
- ✅ **Squarespace website** with membership form
- ✅ **Email service** (Gmail SMTP, SendGrid, etc.)
- ✅ **Server/computer** to run the webhook handler

### Required Information
- **Squarespace form fields** (name, email, phone, membership type)
- **Email templates** (welcome email content)
- **Server details** (where to host the webhook)

## 🚀 Setup Options

### Option 1: Real-Time Webhook (Recommended)
**Best for:** Immediate processing, automatic workflow

#### Setup Steps:
1. **Run webhook server** on your computer or server
2. **Configure Squarespace** to send webhooks to your endpoint
3. **Set up email service** for welcome emails
4. **Test the integration**

#### Advantages:
- ✅ **Instant processing** - Members created immediately
- ✅ **Fully automated** - No manual intervention needed
- ✅ **Real-time feedback** - Know immediately if something fails
- ✅ **Scalable** - Handles multiple submissions simultaneously

#### Requirements:
- Server with public IP or domain name
- SSL certificate (for security)
- Email service configured

### Option 2: CSV Batch Processing
**Best for:** Manual control, existing workflow

#### Setup Steps:
1. **Export CSV** from Squarespace (weekly/daily)
2. **Run batch processor** to create members
3. **Send welcome emails** in bulk

#### Advantages:
- ✅ **No server required** - Runs on your computer
- ✅ **Manual control** - Process when you want
- ✅ **Easy to test** - Simple CSV file processing
- ✅ **Cost effective** - No hosting costs

#### Disadvantages:
- ❌ **Not real-time** - Members wait for processing
- ❌ **Manual work** - You need to export and process
- ❌ **Delayed experience** - Users wait for their passes

### Option 3: Hybrid Approach
**Best for:** Flexibility, gradual implementation

#### Setup Steps:
1. **Start with CSV processing** for immediate results
2. **Set up webhook** for real-time processing later
3. **Use both methods** as needed

## 🛠️ Implementation Guide

### Step 1: Prepare Your Squarespace Form

#### Single Membership Form Fields:
- **First Name** (required)
- **Last Name** (required)
- **Email Address** (required)
- **Phone Number** (optional)
- **Membership Type** (dropdown: Standard, Premium, etc.)

#### Multiple Membership Form Fields:
For family/group memberships, your form should collect:
- **Primary Customer Email** (for transaction tracking)
- **Member 1**: First Name, Last Name, Email, Phone, Membership Type
- **Member 2**: First Name, Last Name, Email, Phone, Membership Type
- **Member 3**: First Name, Last Name, Email, Phone, Membership Type
- (Add more fields as needed)

**Important:** Each member must have their own unique email address.

### Step 2: Set Up Email Service

#### Using Gmail SMTP:
```bash
# Add to your .env file
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
FROM_EMAIL=noreply@liverpoololsc.com
FROM_NAME=Liverpool OLSC
```

#### Using SendGrid (Recommended):
```bash
# Add to your .env file
SENDGRID_API_KEY=your-sendgrid-api-key
FROM_EMAIL=noreply@liverpoololsc.com
FROM_NAME=Liverpool OLSC
```

### Step 3: Configure PassKit

Ensure your PassKit pass template has:
- **Dynamic "Next Match" field** (for new member updates)
- **Member information fields** (name, email, membership type)
- **Default values** set appropriately

### Step 4: Test the Integration

#### Test CSV Processing:
```bash
# Create test CSV file
echo "Email Address,First Name,Last Name,Phone Number,Membership Type" > test_members.csv
echo "test@example.com,Test,Member,+1234567890,Standard" >> test_members.csv

# Process the CSV
python3 squarespace_to_passkit.py --csv test_members.csv
```

#### Test Webhook:
```bash
# Start webhook server
python3 squarespace_webhook.py

# Test webhook endpoint
curl -X POST http://localhost:5003/webhook/test
```

## 📧 Email Templates

### Welcome Email Content
The system sends a professional welcome email with:
- **Liverpool OLSC branding** (red and green colors)
- **Personalized greeting** with member's name
- **Download button** for the pass
- **Membership details** (type, join date, etc.)
- **Instructions** for using the pass
- **Contact information** for support

### Email Customization
You can customize the email template in `squarespace_to_passkit.py`:
- **Subject line** - Change the welcome email subject
- **Content** - Modify the HTML email template
- **Branding** - Update colors, logos, styling
- **Instructions** - Add specific instructions for your club

## 🔐 Security Considerations

### Webhook Security
- **Use HTTPS** - Always use SSL certificates
- **Webhook secrets** - Validate webhook authenticity
- **Rate limiting** - Prevent abuse
- **Input validation** - Sanitize form data

### Data Protection
- **No sensitive data** - Only collect necessary information
- **Secure storage** - Encrypt any stored data
- **Access control** - Limit who can access the system
- **Audit logs** - Track all member creation activities

## 🚀 Deployment Options

### Option 1: Local Computer
**Best for:** Testing, small scale

```bash
# Run on your computer
python3 squarespace_webhook.py
```

**Requirements:**
- Computer always on
- Internet connection
- Port forwarding (if needed)

### Option 2: Cloud Server
**Best for:** Production use, reliability

**Recommended platforms:**
- **Heroku** - Easy deployment, free tier available
- **DigitalOcean** - $5/month droplet
- **AWS EC2** - Scalable, professional
- **Railway** - Simple deployment

### Option 3: Serverless
**Best for:** Cost-effective, automatic scaling

**Platforms:**
- **Vercel** - Great for Python apps
- **Netlify Functions** - Simple deployment
- **AWS Lambda** - Pay per use

## 📊 Monitoring & Maintenance

### Health Checks
The webhook server includes health check endpoints:
- **`/health`** - Basic health status
- **`/webhook/test`** - Test webhook functionality

### Logging
All activities are logged:
- **Member creation** - Success/failure status
- **Email sending** - Delivery confirmation
- **Webhook requests** - Incoming form data
- **Errors** - Detailed error messages

### Monitoring
Set up monitoring for:
- **Server uptime** - Ensure webhook is always available
- **Email delivery** - Track welcome email success rates
- **Pass creation** - Monitor PassKit API success
- **Error rates** - Alert on failures

## 🔧 Edge Cases & Special Handling

### Multiple Memberships in One Transaction

**Scenario:** Customer buys 2+ memberships (e.g., family membership)

**How it works:**
1. **Squarespace form** collects multiple member details
2. **Webhook receives** transaction with multiple members
3. **System processes** each member individually
4. **Duplicate checking** prevents duplicate members
5. **Welcome emails** sent to each member's email

**Expected webhook payload:**
```json
{
  "formName": "Family Membership",
  "transactionId": "txn_123456",
  "customerEmail": "primary@example.com",
  "data": {
    "members": [
      {
        "firstName": "John",
        "lastName": "Smith",
        "email": "john@example.com",
        "phone": "+1234567890",
        "membershipType": "Standard"
      },
      {
        "firstName": "Jane",
        "lastName": "Smith", 
        "email": "jane@example.com",
        "phone": "+1234567891",
        "membershipType": "Standard"
      }
    ]
  }
}
```

### Duplicate Prevention

**How duplicates are prevented:**
1. **Email check** - Searches existing members by email
2. **External ID check** - Uses transaction-based external IDs
3. **No duplicate creation** - Returns existing member if found
4. **No duplicate emails** - Skips sending welcome emails for existing members

**External ID format:**
- Single membership: `sq_email@example.com_timestamp`
- Multiple memberships: `sq_txn_123456_1_email@example.com`

### PassKit Welcome Email vs Custom Email

**Two options available:**

#### Option 1: PassKit Built-in Email (Recommended)
- **Advantages:** Uses PassKit's professional templates, automatic delivery
- **Setup:** Add `"sendWelcomeEmail": true` to member creation
- **Result:** PassKit sends welcome email with pass download link

#### Option 2: Custom Email
- **Advantages:** Full control over content, Liverpool OLSC branding
- **Setup:** Set `use_passkit_email=False` in processing
- **Result:** Custom Liverpool OLSC branded email sent

## 🔧 Troubleshooting

### Common Issues

#### 1. Webhook Not Receiving Data
**Symptoms:** No webhook requests received
**Solutions:**
- Check Squarespace webhook configuration
- Verify webhook URL is accessible
- Check firewall/network settings
- Test with curl or Postman

#### 2. Multiple Memberships Not Processing
**Symptoms:** Only first member processed, others ignored
**Solutions:**
- Verify webhook payload includes `members` array
- Check that each member has unique email
- Ensure transaction ID is provided
- Test with `test_multiple_memberships.py`

#### 2. PassKit Member Creation Fails
**Symptoms:** 400/401 errors from PassKit API
**Solutions:**
- Verify API keys and configuration
- Check member data format
- Ensure PassKit pass template is correct
- Check for duplicate external IDs

#### 3. Welcome Emails Not Sending
**Symptoms:** Members created but no emails received
**Solutions:**
- Verify email service configuration
- Check SMTP credentials
- Test email sending manually
- Check spam folders

#### 4. Pass URLs Not Working
**Symptoms:** Users can't download passes
**Solutions:**
- Verify PassKit pass template is published
- Check member creation was successful
- Test pass URL format
- Ensure pass is not expired

## 📈 Scaling Considerations

### High Volume
For many memberships per day:
- **Queue system** - Use Celery or similar for background processing
- **Database** - Store member data for tracking
- **Load balancing** - Multiple webhook servers
- **Caching** - Cache PassKit API responses

### Multiple Forms
For different membership types:
- **Form routing** - Different webhooks for different forms
- **Template selection** - Different PassKit templates per form
- **Email customization** - Different welcome emails per type

### International
For global supporters:
- **Timezone handling** - Proper timezone conversion
- **Localization** - Multiple language support
- **Currency** - Different pricing per region
- **Compliance** - GDPR, data protection laws

## 💰 Cost Analysis

### Development Costs
- **Setup time** - 4-8 hours initial setup
- **Testing** - 2-4 hours testing and refinement
- **Documentation** - 2 hours creating guides

### Ongoing Costs
- **Server hosting** - $5-20/month (if using cloud)
- **Email service** - $0-50/month (depending on volume)
- **PassKit** - Your existing $40/month
- **Maintenance** - 1-2 hours/month

### ROI Benefits
- **Time savings** - 30+ minutes per new member
- **Error reduction** - No manual data entry mistakes
- **Better experience** - Instant pass delivery
- **Scalability** - Handle unlimited memberships

## 🎯 Success Metrics

### Technical Metrics
- **Webhook success rate** - >99% successful processing
- **Email delivery rate** - >95% emails delivered
- **Pass creation rate** - >99% successful pass creation
- **Response time** - <5 seconds end-to-end

### Business Metrics
- **Member satisfaction** - Faster onboarding experience
- **Admin efficiency** - Reduced manual work
- **Error reduction** - Fewer data entry mistakes
- **Growth support** - Handle increased membership volume

---

**Ready to automate your Liverpool OLSC membership process? 🚀⚽**

This integration will save you hours of manual work and provide a much better experience for new members!
