# 📧 Email Configuration Guide for Numeria Institute

This guide will help you set up email functionality for the contact form and transactional emails.

## Quick Setup

### Option 1: Gmail (Recommended for Testing/Small Volume)

1. **Create a Gmail App Password:**
   - Go to https://myaccount.google.com/security
   - Enable "2-Step Verification" if not already enabled
   - Go to "App passwords" section
   - Select "Mail" and "Windows Computer" (or your platform)
   - Generate a 16-character password
   - Copy this password

2. **Update your `.env` file:**
   ```env
   EMAIL_SERVICE=gmail
   GMAIL_EMAIL=your-email@gmail.com
   GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # The 16-character password from Step 1
   DEFAULT_FROM_EMAIL=Numeria Institute <your-email@gmail.com>
   CONTACT_EMAIL=contact@numeriainstitute.com
   ```

3. **Test the configuration:**
   ```bash
   python manage.py test_email
   # or with a custom recipient:
   python manage.py test_email --to test@example.com
   ```

### Option 2: Mailgun (Recommended for Production)

Mailgun is perfect for transactional emails at scale.

1. **Sign up for Mailgun:**
   - Go to https://mailgun.com
   - Create a free account
   - Create a domain (e.g., `mg.numeriainstitute.com`)
   - Get your SMTP credentials

2. **Update your `.env` file:**
   ```env
   EMAIL_SERVICE=mailgun
   MAILGUN_SMTP_USER=postmaster@mg.numeriainstitute.com
   MAILGUN_SMTP_PASSWORD=your-mailgun-password
   DEFAULT_FROM_EMAIL=Numeria Institute <noreply@numeriainstitute.com>
   CONTACT_EMAIL=contact@numeriainstitute.com
   ```

3. **Test the configuration:**
   ```bash
   python manage.py test_email
   ```

### Option 3: SendGrid

SendGrid is another reliable option for production emails.

1. **Sign up for SendGrid:**
   - Go to https://sendgrid.com
   - Create an account
   - Generate an API key

2. **Update your `.env` file:**
   ```env
   EMAIL_SERVICE=smtp
   EMAIL_HOST=smtp.sendgrid.net
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=apikey
   EMAIL_HOST_PASSWORD=SG.your-sendgrid-api-key
   DEFAULT_FROM_EMAIL=Numeria Institute <noreply@numeriainstitute.com>
   CONTACT_EMAIL=contact@numeriainstitute.com
   ```

3. **Test the configuration:**
   ```bash
   python manage.py test_email
   ```

### Option 4: Custom SMTP Server

For any other SMTP provider:

```env
EMAIL_SERVICE=smtp
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587  # or 465 for SSL
EMAIL_USE_TLS=True  # or False if using SSL
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=Numeria Institute <noreply@yourprovider.com>
CONTACT_EMAIL=contact@numeriainstitute.com
```

## Railway Deployment

For deployment on Railway:

1. **Set Environment Variables:**
   - Go to your Railway project
   - Go to "Variables"
   - Add all email configuration variables from `.env.example`
   - Make sure to use your production email service credentials

2. **Recommended Services for Railway:**
   - **Mailgun**: Great integration, SMTP is simple
   - **SendGrid**: Popular choice with good documentation
   - **AWS SES**: If you're already in AWS ecosystem

## Testing Email Locally

```bash
# Using console backend (prints to console during development)
python manage.py runserver

# Test with actual email service
python manage.py test_email

# Test with custom recipient
python manage.py test_email --to your@email.com
```

## Troubleshooting

### "Connection refused" or "Connection timeout"
- Check that EMAIL_HOST and EMAIL_PORT are correct
- Verify firewall isn't blocking the port
- For Gmail: Check that "Less secure app access" is enabled OR use App Password

### "Authentication failed"
- Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are correct
- For Gmail: Use the 16-character App Password, not your regular password
- For Mailgun/SendGrid: Double-check API credentials

### Emails not showing in inbox
- Check spam/junk folder
- Verify sender email is authenticated with your mail provider
- For Mailgun: Check your domain is verified
- Check email provider's delivery logs

### "SMTP Connection Error" in production
- Verify all variables are set in Railway dashboard
- Check DATABASE_URL and other dependencies are also working
- Look at Railway logs: `railway logs`

## Email Features

### Contact Form Features
- ✅ Sends notification to admin
- ✅ Sends confirmation to user
- ✅ Automatic error handling
- ✅ Supports multiple email services

### Future Enhancements
- [ ] Email templates with HTML
- [ ] Async email sending (Celery)
- [ ] Email scheduling
- [ ] Newsletter functionality
- [ ] Course completion certificates via email

## Production Recommendations

1. **Use a dedicated email service** (Mailgun, SendGrid, AWS SES)
2. **Set up SPF/DKIM records** for your domain
3. **Monitor email delivery** with service provider dashboard
4. **Set up error logging** for failed email attempts
5. **Use async tasks** for non-blocking email sends (Celery)
6. **Test before going live** with `python manage.py test_email`

## Quick Reference: Environment Variables

```env
# Email Service Selection
EMAIL_SERVICE=smtp|gmail|mailgun|brevo|console

# SMTP Configuration (for 'smtp', 'brevo' or 'console' services)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password

# Brevo SMTP example
EMAIL_SERVICE=brevo
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-brevo-smtp-password

# Gmail Configuration (for 'gmail' service)
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Mailgun Configuration (for 'mailgun' service)
MAILGUN_SMTP_USER=postmaster@mg.domain.com
MAILGUN_SMTP_PASSWORD=your-mailgun-password

# Email Addresses
DEFAULT_FROM_EMAIL=Numeria Institute <contact@numeriainstitute.com>
CONTACT_EMAIL=contact@numeriainstitute.com
ADMIN_EMAIL=admin@numeriainstitute.com
```

## Support

For issues with email configuration:
1. Run `python manage.py test_email` to diagnose
2. Check your email provider's documentation
3. Review Django email documentation: https://docs.djangoproject.com/en/6.0/topics/email/
4. Check service provider's SMTP documentation

---

**Last Updated:** April 14, 2026  
**Django Version:** 6.0+  
**Numeria Institute**
