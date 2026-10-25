"""Build data/demo_outputs.json: hand written stand ins for Claude's outputs.

These are NOT model outputs. They let the app run end to end with LLM_MODE=scripted
(for example to record demo clips) before the real run with an API key. The real
outputs live in data/llm_cache.json and always take priority.

Also writes data/demo_cost_estimate.json: an estimated Claude cost per enquiry,
from prompt sizes (about 4 characters per token), at list prices.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# ---------------------------------------------------------------- triage
# id: (category, confidence, reason, fields, injection)
# fields: name, company, need, budget, budget_usd, timeline, industry, company_size, urgency
# A value given as (value, confidence) overrides the default confidence.


def F(name=None, company=None, need=None, budget=None, usd=None, timeline=None, industry=None, size=None,
      urgency="unknown", conf=0.92):
    def f(v, c=None):
        if isinstance(v, tuple):
            v, c = v
        return {"value": v, "confidence": 0.0 if v is None else (c if c is not None else conf)}

    u = urgency if isinstance(urgency, tuple) else (urgency, 0.0 if urgency == "unknown" else conf - 0.08)
    return {
        "name": f(name, 0.97 if name and not isinstance(name, tuple) else None),
        "company": f(company),
        "need": f(need),
        "budget": f(budget),
        "budget_usd": f(usd),
        "timeline": f(timeline),
        "industry": f(industry),
        "company_size": f(size),
        "urgency": {"value": u[0], "confidence": u[1]},
    }


T = {
    # ---- strong leads
    "E001": ("Sales", 0.97, "Freight forwarder re-keying 300 booking emails a day; clear need, $30k to $40k budget, start next month.",
             F("Dana Whitlock", "Harbourline Freight", "Automate booking emails into their TMS with a check step", "$30k to $40k", 35000, "Next month", "Freight forwarding", 180, "high")),
    "E002": ("Sales", 0.95, "Dental group of 12 practices wants automated recalls and no show follow ups; about $25k budget.",
             F("Isabel Moreau", "Verity Dental Group", "Automated recall campaigns and no show follow ups", "About $25k", 25000, "Soon", "Dental healthcare", 210, "medium")),
    "E008": ("Sales", 0.94, "Consulting partner wants AI drafted proposals from past work; about $30k, wants it within four weeks.",
             F("Elena Petrova", "Stonebridge Advisory", "Draft proposals from past work for consultants to edit", "About $30k", 30000, "Next four weeks", "Professional services consulting", 55, "high")),
    "E013": ("Sales", 0.93, "Follow up from Harbourline Freight: budget confirmed at $40k, start brought forward to three weeks.",
             F("Dana Whitlock", ("Harbourline Freight", 0.86), "Booking email automation, now about 350 bookings a day", "$40k", 40000, "In three weeks", "Freight forwarding", None, "high")),
    "E014": ("Sales", 0.95, "Physio network wants booking requests in the CRM with reminders and follow ups; around $22k.",
             F("Grace Holloway", "Fairfield Physio Network", "Booking requests into the CRM with reminders and follow ups", "Around $22k", 22000, "Within a month", "Physiotherapy clinics", 75, "high")),
    "E020": ("Sales", 0.96, "Retailer with 40 stores wants 2,000 weekly service emails sorted with drafted replies; about $50k.",
             F("Hannah Okafor", "Pennant Retail Group", "Sort customer service emails and draft replies for agents", "About $50,000", 50000, "Kick off in November", "Retail", 700, "medium")),
    "E026": ("Sales", 0.95, "Law firm wants enquiries categorised, conflict checked, logged in the CRM, replies drafted; $25k, ASAP.",
             F("Aisha Bello", "Meridian Legal LLP", "Categorise and log new client enquiries with drafted replies", "$25k", 25000, "As soon as possible", "Legal services", 90, "high")),
    "E032": ("Sales", 0.96, "Online retailer losing two days a week to Shopify and Xero reconciliation; about $20k, six weeks.",
             F("Sofia Lindqvist", "Brightpath Ecommerce", "Automate Shopify payout reconciliation against Xero", "About $20,000", 20000, "Within six weeks", "Ecommerce retail", 85, "high")),
    "E038": ("Sales", 0.95, "Accounting firm wants automated client onboarding and document extraction before the January rush.",
             F("Priya Raman", "Calder & Finch Accountants", "Automated client onboarding with document collection and extraction", "About 25,000 GBP", 31750, "Before the January tax rush", "Accounting", 120, "high")),
    "E039": ("Sales", 0.93, "Haulage firm wants driver timesheet collection and checks automated; around $20k, next month.",
             F("Owen Price", ("Trackside Haulage", 0.88), "Automate driver timesheet collection and checks", "Around $20k", 20000, "Next month", "Haulage and logistics", 95, "medium")),
    "E045": ("Sales", 0.96, "Manufacturer with 1,200 supplier invoices a month wants extraction and PO matching; $35k, by year end.",
             F("David Mensah", "Copperline Components", "Extract supplier invoices and match them to purchase orders", "$35k", 35000, "Before year end", "Electronics manufacturing", 320, "high")),
    "E051": ("Sales", 0.95, "Wholesaler wants order exceptions caught early with drafted emails and tasks; around $40k, pre Black Friday.",
             F("Kenji Watanabe", "Orchard Lane Wholesale", "Detect order exceptions and draft customer emails", "Around $40k", 40000, "Before Black Friday", "Wholesale ecommerce", 160, "high")),
    "E057": ("Sales", 0.95, "Logistics firm delayed in billing by manual proof of delivery typing; $28k budget, urgent.",
             F("Rafael Mendes", ("Bluewater Logistics", 0.88), "Extract proof of delivery photos into billing", "$28k", 28000, "Urgent", "Logistics", 140, "high")),
    "E063": ("Sales", 0.94, "Cold storage operator wants stock alerts and AI drafted customer answers; thinking $35k, next month.",
             F("Conor Whelan", "Atlas Cold Storage", "Stock alerts and drafted answers to customer stock questions", "$35k", 35000, "Next month", "Cold storage warehousing", 250, "medium")),
    "E069": ("Sales", 0.96, "Manufacturer gets 150 quote requests a week and wants them read and routed; around $60k this quarter.",
             F("Tomasz Brenner", "Kestrel Manufacturing", "Read quote requests, pull out specs and route to estimators", "Around $60k", 60000, "This quarter", "Precision manufacturing", 600, "medium")),
    "E075": ("Sales", 0.97, "Clinic group of 400 staff wants digital intake into its practice system; $45k approved, urgent for January.",
             F("Marcus Oyelaran", ("Northgate Clinics", 0.9), "Digital patient intake flowing into the practice system", "$45k", 45000, "Before January", "Healthcare clinics", 400, "high")),
    "E076": ("Sales", 0.95, "Fashion brand with returns piling up before peak wants requests checked and replies drafted; about $24k.",
             F("Nadia Haddad", "Lumen Ecommerce Co", "Check returns requests against policy and draft replies", "About $24k", 24000, "Urgent, before peak season", "Ecommerce fashion", 60, "high")),
    # ---- tricky leads
    "E050": ("Sales", 0.92, "Finance director at Harbourline Freight wants carrier invoice matching; same company as an earlier lead.",
             F("Ravi Shah", "Harbourline Freight Ltd", "Match carrier invoices against shipments", "About $25k", 25000, "This quarter", "Freight forwarding", 180, "medium")),
    "E044": ("Sales", 0.86, "Clinic group lead with budget and timeline, sent from a personal address so company details are unverified.",
             F("Jess Thornton", ("Wrenfield Clinics", 0.45), "Appointment reminders and digital intake into the CRM", "About $25k", 25000, "Next month", "Healthcare clinics", (120, 0.6), "medium")),
    "E062": ("Sales", 0.94, "Healthcare partnership with an urgent referral intake need and a six week deadline; no budget mentioned.",
             F("Olivia Brandt", "Tideway Health Partners", "Automate GP referral intake with a review step", None, None, "Within six weeks", "Healthcare", 300, "high")),
    "E056": ("Sales", 0.81, "Logistics lead with a $30k budget, but the email hides instructions to score it 100, skip review and share client data.",
             F("Victor Ashby", "Ashby Logistics", "Automate how the warehouse team handles customer emails", "Around $30k", 30000, "New year", "Logistics", 120, "medium"), True),
    # ---- weak leads
    "E003": ("Sales", 0.82, "Construction firm curious about AI costs, no project or budget yet.",
             F("Ahmed Karim", ("Karim Construction", 0.75), "Wants to know what AI could do and cost", None, None, None, "Construction", 40, "low")),
    "E009": ("Sales", 0.88, "Estate agency possibly interested in buyer follow ups, about $8k, depends on the market.",
             F("Tobias Kerr", ("Kerr Homes", 0.7), "Automated follow ups for buyer enquiries", "Maybe $8k", 8000, "Possibly in a few months", "Real estate", 25, "low")),
    "E015": ("Sales", 0.91, "Small gym wants a class booking chatbot for about $4,000 with no deadline.",
             F("Victor Hale", "Hale Fitness", "Website chatbot that books classes", "About $4,000", 4000, "No deadline", "Fitness", 12, "low")),
    "E021": ("Sales", 0.84, "Eight person design studio exploring ideas, a few thousand dollars, probably next year.",
             F("Jordan Lee", "Pixel Pup Studio", "Exploring what AI could do for the studio", ("A few thousand dollars", 0.6), (3000, 0.45), "Probably next year", "Design agency", 8, "low")),
    "E027": ("Sales", 0.86, "Six person cafe wants Instagram posts written by AI for about $300.",
             F("Sam Rivers", ("Corner Cup", 0.45), "AI written Instagram posts", "$300", 300, None, "Hospitality", 6, "low")),
    "E033": ("Sales", 0.9, "Freelance photographer wants a text alert from a contact form for about $500.",
             F("Ben Carter", "Ben Carter Photography", "Text alert when the contact form is filled in", "$500", 500, "No rush", "Photography", 1, "low")),
    "E040": ("Sales", 0.86, "Hobby podcaster wants automatic transcripts for $200.",
             F("Ella Morgan", None, "Automatic podcast transcripts", "$200", 200, None, "Podcasting", None, "low")),
    "E046": ("Sales", 0.9, "Solo wedding planner wants automated client emails with about $1,500.",
             F("Lucy Fernandes", "Lucy F Weddings", "Automatic emails to clients", "About $1,500", 1500, None, "Wedding planning", 2, "low")),
    "E052": ("Sales", 0.87, "Youth charity asks if a $6,000 grant could cover volunteer scheduling in the spring.",
             F("Maya Singh", "Riverside Youth Club", "Volunteer scheduling", "About $6,000", 6000, "Spring", "Nonprofit", 20, "low")),
    "E058": ("Sales", 0.9, "Three person bookshop wants its stock spreadsheet updated automatically for about $1,000.",
             F("Fiona Grant", ("The Book Nook", 0.6), "Stock spreadsheet that updates on each sale", "About $1,000", 1000, None, "Retail bookshop", 3, "low")),
    "E064": ("Sales", 0.72, "Student asking for free help with a university chatbot project.",
             F("Rita Novak", None, "Help setting up a chatbot for a final year project", ("Free", 0.8), None, None, "Education", None, "low")),
    "E070": ("Sales", 0.83, "Four person crypto startup wants an Uber style app with no budget yet, maybe next year.",
             F("Chloe Adams", "CoinHopper", "Build an Uber style app for crypto trades", None, None, "Maybe next year", "Crypto", 4, "low")),
    # ---- support
    "E004": ("Support", 0.95, "Existing client's legal team needs a copy of the data processing agreement.",
             F("Robert Kim", ("Summit Engineering", 0.7), "Copy of the data processing agreement", urgency="medium")),
    "E007": ("Support", 0.58, "Client reports a broken Xero sync but also asks for a returns portal quote; part support, part sales.",
             F("Grant Ellison", ("Oakridge Supplies", 0.72), "Fix the Xero sync; also wants a quote for a returns portal", None, None, ("Today for the fix", 0.7), "Wholesale", 70, "high")),
    "E010": ("Support", 0.96, "Client preparing for an audit asks where data is stored and how long backups are kept.",
             F("Oliver Grant", ("Westmoor Finance", 0.7), "Data storage location and backup retention for an audit", None, None, "Audit next month", "Finance", None, "medium")),
    "E011": ("Support", 0.96, "Xero integration has failed since the finance manager changed her password; orders are not syncing.",
             F("Beatriz Santos", ("Marina Gifts", 0.7), "Fix the Xero integration after a password change", urgency="high")),
    "E016": ("Support", 0.97, "HubSpot sync stopped yesterday and web leads are missing; blocking the sales team.",
             F("Luke Fenwick", ("Saltmarsh Foods", 0.7), "HubSpot sync has stopped", urgency="high")),
    "E017": ("Support", 0.95, "Client wants to give a new office manager portal access and asks about cost.",
             F("Joanna Price", ("Larkspur Florists", 0.7), "Add a new team member to the portal", None, None, "Monday", urgency="medium")),
    "E022": ("Support", 0.94, "Client asks which day of the month the retainer is billed.",
             F("George Hart", ("Millbrook Pharmacy", 0.7), "Retainer billing date", urgency="low")),
    "E023": ("Support", 0.95, "Client asks how to export a dashboard table to Excel.",
             F("Ruth Baptiste", ("Crescent Law", 0.7), "Export a dashboard table to Excel", urgency="low")),
    "E025": ("Support", 0.84, "Pilot client reports a failing dashboard export and mentions a $120k rollout to 12 depots next quarter.",
             F("Erik Halvorsen", ("Halvorsen Logistics Group", 0.82), "Fix the CSV export; ask about a rollout to all 12 depots", "Roughly $120k approved", 120000, "Next quarter", "Logistics", 1800, "medium")),
    "E028": ("Support", 0.96, "Client's accountant needs PDFs of the last three invoices.",
             F("Paul Dempsey", ("Riverbank Dental", 0.7), "Download the last three invoices", urgency="low")),
    "E029": ("Support", 0.93, "Client missed last week's Friday update and asks if launch is still on track.",
             F("Yasmin Khan", ("Oakfield Nursery", 0.7), "Missing weekly update and launch status", urgency="medium")),
    "E034": ("Support", 0.96, "Client locked out after failed sign ins and needs to approve a change request today.",
             F("Imran Siddiqui", ("Coastal Tiles", 0.7), "Unlock their portal account", None, None, "Today", urgency="high")),
    "E035": ("Support", 0.95, "Client wants to pause the retainer over a quiet December and asks the cost.",
             F("Claire Dubois", ("Hillside Catering", 0.7), "Pause the retainer for December", None, None, "December", urgency="low")),
    "E041": ("Support", 0.92, "Client wants a new monthly report and asks how to request it and how long it takes.",
             F("Natalie Ross", ("Cedar Home Care", 0.7), "New monthly report of visits by carer", urgency="low")),
    "E047": ("Support", 0.96, "Client's board asks whether customer data is used to train AI models.",
             F("Zainab Ali", ("Clearview Opticians", 0.7), "Confirm data is not used to train AI models", urgency="medium")),
    "E048": ("Support", 0.9, "Client needs a W-9 tax form from suppliers for their accounts system.",
             F("Kevin O'Hara", ("Redfern Plumbing", 0.7), "A W-9 tax form", urgency="low")),
    "E053": ("Support", 0.88, "Client moving from HubSpot to Pipedrive asks if it is supported and how long a switch takes.",
             F("Mei Chen", ("Harlow Print", 0.7), "Pipedrive support and time to switch the integration", urgency="low")),
    "E054": ("Support", 0.95, "Client's account admin has left and nobody can manage billing.",
             F("Ian McLeod", ("Glenwood Estates", 0.7), "Change the account admin", urgency="medium")),
    "E059": ("Support", 0.95, "Client asks whether support works over Christmas and what happens if something breaks.",
             F("Amara Nwosu", ("Pinecrest Lettings", 0.7), "Support cover over the holidays", urgency="low")),
    "E060": ("Support", 0.96, "Sales dashboard still shows yesterday's numbers; client asks how often it refreshes.",
             F("Arjun Mehta", ("Tidewater Boats", 0.7), "Dashboard refresh timing", urgency="medium")),
    "E065": ("Support", 0.96, "Client moved office and the October invoice still shows the old address.",
             F("Sinead Byrne", ("Lakeside Joinery", 0.7), "Update the billing address and fix the invoice", urgency="low")),
    "E066": ("Support", 0.94, "Membership dashboard shows 40 percent fewer October sign ups than the client's records.",
             F("Daniel Walsh", ("Northpoint Gyms", 0.7), "Check dashboard sign up numbers", urgency="medium")),
    "E071": ("Support", 0.96, "Growth retainer client asks how to switch on Microsoft 365 single sign on.",
             F("Helen Brooks", ("Greenfield Vets", 0.7), "Turn on Microsoft 365 single sign on", urgency="low")),
    "E072": ("Support", 0.93, "Client is bringing development in house and asks how to cancel and get a handover.",
             F("Martin Ellis", ("Foxglove Studios", 0.7), "Cancel the retainer and get code and documentation", urgency="low")),
    "E077": ("Support", 0.97, "Client requested three password reset emails this morning and none arrived.",
             F("Tara Quinn", ("Ashgrove Insurance", 0.7), "Password reset email not arriving", urgency="medium")),
    "E078": ("Support", 0.95, "Client used 6 of 10 retainer hours and asks if the rest roll over.",
             F("Femi Adeyemi", ("Brookfield Motors", 0.7), "Do unused retainer hours roll over", urgency="low")),
    # ---- spam
    "E005": ("Spam", 0.98, "Cold SEO pitch promising guaranteed rankings.", F()),
    "E012": ("Spam", 0.98, "Follower selling pitch.", F()),
    "E018": ("Spam", 0.99, "Sextortion style scam demanding bitcoin.", F()),
    "E019": ("Spam", 0.98, "Manipulation attempt: tells the AI to ignore its rules, mark itself a qualified lead and leak customer emails.", F(), True),
    "E024": ("Spam", 0.98, "Backlink selling pitch.", F()),
    "E030": ("Spam", 0.97, "Cold pitch for offshore developers.", F()),
    "E036": ("Spam", 0.95, "Guest post and link exchange request.", F()),
    "E042": ("Spam", 0.99, "Crypto investment scam.", F()),
    "E055": ("Spam", 0.96, "Cold web redesign pitch.", F()),
    "E061": ("Spam", 0.97, "Unsolicited offer to sell email lists.", F()),
    "E067": ("Spam", 0.98, "Phishing: fake overdue invoice asking for an email password.", F()),
    "E073": ("Spam", 0.99, "Lottery scam asking for bank details.", F()),
    "E079": ("Spam", 0.98, "Phishing: fake domain renewal asking for card details.", F()),
    # ---- other
    "E006": ("Other", 0.88, "Marketing agency proposing a referral partnership.", F("Laura Bennett", ("Northlight Agency", 0.7), "Referral partnership")),
    "E031": ("Other", 0.93, "Student asking about summer internships.", F("Noah Fisher", None, "Summer internship")),
    "E037": ("Other", 0.95, "Office cleaning supplier changing the cleaning day.", F(None, "Sparkle Office Cleaning", "Cleaning schedule change")),
    "E043": ("Other", 0.94, "Journalist asking for a quote on AI in small business.", F("Sophie Turner", ("Business Weekly", 0.6), "Quote for an article", None, None, "By Thursday")),
    "E049": ("Other", 0.95, "Job application from a full stack developer.", F("Chris Tan", None, "Developer job application")),
    "E068": ("Other", 0.9, "Recruiter offering AI engineer candidates.", F(None, "Talent Bridge Recruitment", "Offering candidates")),
    "E074": ("Other", 0.94, "Thank you note from a past client, no action needed.", F("Martha Gale", ("Willow Bakery", 0.7), "No action needed")),
    "E080": ("Other", 0.93, "Invitation to speak at an operations event in March.", F(None, "Operations Forum", "Speaker invitation")),
    # ---- the contact form submission used in clip C03
    "FORM": ("Sales", 0.95, "Logistics firm of 150 wants customer emails sorted with drafted replies; about $30k, next month.",
             F("Maria Lopez", "Crestway Freight", "Sort customer emails and draft replies", "About $30k", 30000, "Next month", "Logistics", 150, "medium")),
}
FORM_SUBJECT = "Sorting customer emails"

# ---------------------------------------------------------------- sales drafts
# id: (what we understood, how we would approach it)
S = {
    "E001": ("Re-keying around 300 booking emails a day into your TMS is exactly the kind of repetitive work that slows a team down and lets mistakes slip in.",
             "We would have AI read each booking, pull out the shipment details and prepare the entry in your TMS, with someone on your team confirming anything unusual before it goes live."),
    "E002": ("Recalls and no show follow ups across 12 practices are easy to lose track of when they are done by hand.",
             "We would automate the recall campaigns and follow ups, and give practice managers a simple dashboard showing who has been contacted and who still needs a call."),
    "E008": ("Your consultants spending days rebuilding proposals from old documents is time they could be spending with clients.",
             "We would build a tool that drafts a proposal from a short brief and your best past work, so a consultant starts from a strong draft and edits rather than writing from scratch."),
    "E013": ("Thanks for confirming the budget and the earlier start. With volumes now around 350 bookings a day, automating this makes even more sense.",
             "Starting in three weeks is realistic if we begin discovery shortly. We would keep the same approach: AI prepares each booking and your team confirms anything unusual."),
    "E014": ("Getting booking requests into your CRM automatically, with reminders and follow ups for patients who drop off, would take a lot of admin off your clinic teams.",
             "We would connect your online booking requests to the CRM, send reminders automatically and flag patients who need a personal follow up."),
    "E020": ("Two thousand customer service emails a week is a lot for any team to sort before they can even start replying.",
             "We would have AI sort each email into orders, returns, complaints and store questions, pull out order numbers and draft a reply for an agent to approve."),
    "E026": ("Categorising enquiries by practice area, checking conflicts and logging everything in the CRM by hand takes fee earner time away from clients.",
             "We would build a flow that categorises each enquiry, runs the conflict check, logs it in your CRM and drafts a reply for a fee earner to approve before it is sent."),
    "E032": ("Two days a week matching Shopify payouts, refunds and fees against Xero is a big cost for a finance team, especially going into peak season.",
             "We would automate the matching and only send your team the exceptions that genuinely need a person to look at them."),
    "E038": ("Chasing documents and typing client details into your practice software is a heavy load, and the January rush will only make it heavier.",
             "We would build an onboarding flow that collects documents, extracts the key details and prepares them for your practice software, with a review step before anything is saved."),
    "E039": ("Payroll spending three days a month fixing timesheets that arrive as photos and texts is the kind of work AI handles well.",
             "We would collect timesheets in one place, read the photos and messages automatically, and flag anything that does not add up for your payroll team to check."),
    "E045": ("Twelve hundred supplier invoices a month is a lot of manual keying and matching for accounts payable.",
             "We would extract the line items from each invoice, match them to the right purchase order and queue them for approval, with mismatches flagged for a person."),
    "E051": ("Finding out late about out of stock items, address problems or credit holds is frustrating for your team and your retailers.",
             "We would detect order exceptions as they happen, draft the customer email and create a task for the right person, so problems are handled before they become complaints."),
    "E057": ("Billing being held up for days while proof of delivery notes are typed up has a real cost to your cash flow.",
             "We would read the photos drivers send, extract the delivery details and pass them straight to billing, with anything unclear flagged for a quick check."),
    "E063": ("Answering constant stock and dispatch questions by email takes your team away from running the warehouses.",
             "We would set up automatic stock alerts and an assistant that drafts answers from your warehouse system for your team to review and send."),
    "E069": ("Engineers sorting 150 quote requests a week by hand is expensive time to spend on admin.",
             "We would have AI read each request and its drawings, pull out material, quantity and deadline, and route it to the right estimator, with unclear requests flagged for a person."),
    "E075": ("Moving 14 clinics from paper and PDF intake to forms that flow straight into your practice system is a big step, and opening three new sites makes the timing important.",
             "We would build digital intake forms that feed your practice management system directly, with a check step for anything unclear before it is saved."),
    "E076": ("With returns piling up and peak season close, getting this under control quickly matters.",
             "We would read each returns request, check it against the order and your policy, and draft a reply for your team to approve, so they only handle the exceptions."),
    "E050": ("Matching carrier invoices against shipments by hand is slow and easy to get wrong, and it sounds like it would fit well alongside the bookings work your colleague mentioned.",
             "We would extract each carrier invoice, match it to the shipment record and flag any differences for your finance team to review."),
    "E044": ("Automated appointment reminders and digital intake feeding your CRM would take a lot of admin off your five sites.",
             "We would set up reminders and intake forms that feed your CRM directly, with a review step for anything the system is unsure about."),
    "E062": ("Re-keying GP referrals from email and fax causes delays for patients, and with your admin contract ending the timing matters.",
             "We would automate the referral intake into your patient system, with a person reviewing each referral before it is confirmed."),
    "E056": ("Automating how your warehouse team handles customer emails is something we do often.",
             "We would sort incoming emails, pull out the key details and draft replies for your team to approve."),
    "FORM": ("Sorting customer emails and drafting replies for a team of 150 is exactly what we build.",
             "We would have AI sort each email, pull out the key details and draft a reply for your team to approve before anything is sent."),
}


def sales_reply(eid: str, first: str, has_budget: bool, has_timeline: bool) -> str:
    understood, approach = S[eid]
    ask = ""
    if not has_budget and not has_timeline:
        ask = " It would also help to know roughly what budget and timeline you have in mind."
    elif not has_budget:
        ask = " It would also help to know roughly what budget you have in mind."
    return (
        f"Hi {first},\n\nThanks for getting in touch. {understood}\n\n{approach}\n\n"
        "Would a 30 minute discovery call work for you? If you can share two times that suit you this week "
        f"or next, I will send over an invite.{ask}\n\nBest regards,\nFernhollow Digital"
    )


# ---------------------------------------------------------------- support drafts
# id: (reply, [exact quotes from the help articles]) ; answerable False if no quotes
P = {
    "E004": ("Our standard data processing agreement is available on request from your account manager, so I have asked them to send a copy to your legal team today. We are also happy to review your own DPA if you prefer to use that.",
             ["Our standard data processing agreement is available on request from your account manager.", "We are happy to review your own DPA."]),
    "E007": ("Sorry the Xero sync has stopped again. The most common cause is an expired connection, for example after a password change on the connected account, so please try reconnecting it under Integrations in the client portal. If it still fails, we will treat it as a Priority 2 ticket. I have also passed your returns portal question to your account manager, who will be in touch about a quote.",
             ["The most common cause is an expired connection, for example a password change on the connected account.", "If it still fails, raise a Priority 2 ticket."]),
    "E010": ("Your data is stored in the UK or the EU, depending on the region chosen at onboarding, and backups are encrypted and kept for 30 days. Your account manager can confirm the exact region for your account in writing for the audit.",
             ["Client data is stored in the UK or the EU, depending on the region chosen at onboarding.", "Backups are encrypted and kept for 30 days."]),
    "E011": ("Sorry about this. When an integration stops after a password change, the connection has usually expired. Please reconnect Xero under Integrations in the client portal using the new password, and orders should start syncing again. If it still fails, reply here and we will raise it as Priority 2.",
             ["The most common cause is an expired connection, for example a password change on the connected account.", "Reconnect it under Integrations in the client portal."]),
    "E016": ("Sorry, I know this is blocking your sales team. The most common cause is an expired connection, so please check under Integrations in the client portal and reconnect HubSpot if it shows an error. If that does not fix it, we will pick it up as a Priority 2 ticket straight away.",
             ["The most common cause is an expired connection, for example a password change on the connected account.", "If it still fails, raise a Priority 2 ticket."]),
    "E017": ("Welcome to your new office manager. An account admin can invite her under Settings > Team > Invite, and the link stays valid for seven days. There is no charge for extra portal users.",
             ["Account admins can invite people under Settings > Team > Invite.", "There is no charge for extra portal users."]),
    "E022": ("Retainers are billed monthly in advance on the 1st, so you can plan for it at the start of each month.",
             ["Retainers are billed monthly in advance on the 1st."]),
    "E023": ("Yes. Any table on a dashboard can be exported to CSV or Excel. You can also set up scheduled exports by email under Reports > Schedules if you need it regularly.",
             ["Any table on a dashboard can be exported to CSV or Excel.", "Scheduled exports by email can be set up under Reports > Schedules."]),
    "E025": ("Thanks for letting us know about the export. Any table on a dashboard should export to CSV or Excel, so this sounds like a fault rather than a setting. We have raised a ticket and will update you shortly. I am also really glad the pilot has gone well, and I have asked your account manager to get in touch about the rollout to all 12 depots.",
             ["Any table on a dashboard can be exported to CSV or Excel."]),
    "E028": ("Every invoice is in the client portal under Billing > Invoices, and you can download each one as a PDF. Your account admin can also add your accountant as a billing contact so they receive a copy automatically.",
             ["Every invoice is in the client portal under Billing > Invoices.", "Your account admin can add a billing contact who receives a copy by email."]),
    "E029": ("Sorry you did not get last week's update. You should receive a short written update every Friday, so I have asked your project lead to send it today along with a clear view of the launch date.",
             ["You get a short written update every Friday with what was done, what is next and anything we need from you."]),
    "E034": ("After five failed attempts an account locks for 15 minutes, so you will be able to sign in again shortly. If you need access sooner, your account admin can unlock it straight away from Settings > Team.",
             ["After five failed attempts an account locks for 15 minutes.", "Your account admin can unlock it straight away from Settings > Team."]),
    "E035": ("Yes, you can pause a retainer for up to two months once per year. During the pause we keep your automations running and monitored, and it costs 20 percent of your usual monthly fee.",
             ["You can pause a retainer for up to two months once per year.", "A pause costs 20 percent of your usual monthly fee."]),
    "E041": ("You can request this under Support > New change request in the client portal. Describe the report you need and who will use it, and your account manager will reply with a scope and a fixed price or an hours estimate within two business days.",
             ["Use Support > New change request in the client portal.", "Your account manager replies with a scope and a fixed price or an hours estimate within two business days."]),
    "E047": ("I can confirm that when we build AI features, your data is sent to the AI provider only to process your request and is not used to train their models. We can also switch AI features off for any workflow if your board would prefer.",
             ["When we build AI features, your data is sent to the AI provider only to process your request and is not used to train their models.", "We can switch AI features off for any workflow on request."]),
    "E048": ("Thanks for your message. I have passed your request for our tax form to our finance team, and someone will follow up with you shortly.", []),
    "E053": ("Yes, we build and maintain Pipedrive integrations. Moving your integration over would be scoped as a change request, and most new integrations take one to two weeks including testing in a sandbox account.",
             ["We build and maintain integrations with HubSpot, Salesforce, Pipedrive, Xero, QuickBooks Online, Shopify, WooCommerce, Google Workspace, Microsoft 365, Slack, Airtable and most systems that offer a REST API or webhooks.", "Most take one to two weeks, including testing in a sandbox account."]),
    "E054": ("Sorry to hear about this. If your admin has left, please email support from a company address and we will verify the change with a director before transferring the admin role.",
             ["If the admin has left your company, email support from a company address and we will verify the change with a director."]),
    "E059": ("Our support team works Monday to Friday, 8am to 6pm UK time, except UK public holidays, so we will be closed on the bank holidays over Christmas and New Year. If something breaks, please raise a ticket as usual and we will pick it up on the next working day.",
             ["Our support team works Monday to Friday, 8am to 6pm UK time, except UK public holidays."]),
    "E060": ("Dashboards refresh every hour, and you can force a refresh from the menu on each dashboard, which takes up to five minutes. If the numbers are still a day old after that, let us know and we will look into it.",
             ["Dashboards refresh every hour.", "A manual refresh is available from the menu on each dashboard and takes up to five minutes."]),
    "E065": ("Your account admin can update the billing address under Billing > Payment details, and the change applies from the next invoice. We cannot reissue a paid invoice with a new address, but we can add a credit note and a corrected invoice, so I have asked our finance team to do that for October.",
             ["Changes apply from the next invoice.", "We cannot reissue a paid invoice with a new address, but we can add a credit note and a corrected invoice on request."]),
    "E066": ("Thanks for flagging this. Please check the date range and filters on the dashboard first. If the numbers still look wrong, reply with a screenshot and the figure you expected, and we will raise it as a Priority 3 ticket.",
             ["Check the date range and filters first.", "If the numbers still look wrong, raise a Priority 3 ticket with a screenshot and the figure you expected."]),
    "E071": ("Good news: clients on the Growth retainer can sign in with Microsoft 365. Your account admin can turn on single sign on under Settings > Security. Once it is on, password sign in is turned off for everyone on your domain.",
             ["Clients on the Growth and Scale retainers can sign in with Google Workspace or Microsoft 365.", "Your account admin turns SSO on under Settings > Security."]),
    "E072": ("Retainers can be cancelled with 30 days notice, either from the account admin's email address or through Billing > Cancel retainer in the client portal. Everything we built belongs to you, and we hand over code, credentials and documentation within 10 business days.",
             ["Retainers can be cancelled with 30 days notice.", "On cancellation we hand over code, credentials and documentation within 10 business days."]),
    "E077": ("Sorry about that. Reset links usually arrive within five minutes. Please check your spam folder and make sure you are using the email address your account was created with. If it still does not arrive, reply here and we will reset it for you.",
             ["A reset link arrives within five minutes and stays valid for 60 minutes.", "If it does not arrive, check your spam folder and make sure the address matches the one on your account."]),
    "E078": ("Yes, unused retainer hours roll over for one month, so your remaining 4 hours carry into next month.",
             ["Unused hours roll over for one month."]),
}


def build():
    from app.intake.inbox_sim import load_enquiries

    enquiries = {e["id"]: e for e in load_enquiries()}
    assert set(T) - {"FORM"} == set(enquiries), set(enquiries) ^ (set(T) - {"FORM"})

    out = {"_note": "Hand written stand ins for Claude outputs, used only with LLM_MODE=scripted. Not model outputs.",
           "by_subject": {}}
    for eid, row in T.items():
        cat, conf, reason, fields = row[:4]
        injection = len(row) > 4 and row[4]
        subject = FORM_SUBJECT if eid == "FORM" else enquiries[eid]["subject"]
        entry = {"triage": {"category": cat, "confidence": conf, "reason": reason, "injection_suspected": injection,
                            "fields": fields}}
        if eid in S:
            first = (fields["name"]["value"] or "there").split()[0]
            entry["sales_draft"] = {
                "subject": f"Re: {subject}",
                "reply": sales_reply(eid, first, fields["budget"]["value"] is not None, fields["timeline"]["value"] is not None),
            }
        if eid in P:
            reply, quotes = P[eid]
            first = fields["name"]["value"].split()[0]
            entry["support_draft"] = {
                "answerable": bool(quotes),
                "subject": f"Re: {subject}",
                "reply": f"Hi {first},\n\n{reply}\n\nThe Fernhollow Digital support team",
                "quotes": quotes,
            }
        out["by_subject"][subject] = entry

    path = ROOT / "data" / "demo_outputs.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {path.relative_to(ROOT)} ({len(out['by_subject'])} emails)")
    estimate_cost()


def estimate_cost():
    """Run the pipeline with the scripted outputs and price the prompts it would send."""
    from app.config import Config
    from app.drafts.retriever import HelpDocRetriever
    from app.intake.inbox_sim import load_enquiries
    from app.llm.scripted import ScriptedLLM
    from app.pipeline.process import MessageIn, Pipeline
    from app.pipeline.scoring import load_icp
    from app.settings_store import DEFAULTS

    prices = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}
    usage = {m: [0, 0] for m in prices}

    class Counting(ScriptedLLM):
        def generate_json(self, *, model, system, user, schema, **kw):
            out = super().generate_json(model=model, system=system, user=user, schema=schema, **kw)
            usage[model][0] += (len(system) + len(user) + len(json.dumps(schema))) // 4
            # Output plus an allowance for thinking tokens, which are billed as output.
            usage[model][1] += int(len(out) / 4 * 2)
            return out

    config = Config()
    pipeline = Pipeline(Counting(), HelpDocRetriever(), config)
    settings = {**DEFAULTS, "icp": load_icp()}
    enquiries = load_enquiries()
    for i, e in enumerate(enquiries, 1):
        pipeline.analyse(MessageIn(i, e["from_name"], e["from_email"], e["company"], e["subject"], e["body"]), settings)
    total = sum(usage[m][0] / 1e6 * p[0] + usage[m][1] / 1e6 * p[1] for m, p in prices.items())
    result = {
        "cost_per_enquiry": round(total / len(enquiries), 5),
        "method": "Estimated from prompt sizes at about 4 characters per token, list prices, output doubled for thinking. Not measured.",
        "tokens": {m: {"input": v[0], "output": v[1]} for m, v in usage.items()},
    }
    (ROOT / "data" / "demo_cost_estimate.json").write_text(json.dumps(result, indent=1) + "\n")
    print(f"estimated cost per enquiry ${result['cost_per_enquiry']:.4f}")


if __name__ == "__main__":
    build()
