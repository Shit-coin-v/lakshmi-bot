"""RFM segment labels — single source of truth.

Used by models (choices), services (SEGMENT_MAP), campaigns, and admin.
"""

# Segment label identifiers — use these instead of raw strings.
CHAMPIONS = "champions"
LOYAL = "loyal"
POTENTIAL_LOYALISTS = "potential_loyalists"
NEW_CUSTOMERS = "new_customers"
AT_RISK = "at_risk"
HIBERNATING = "hibernating"
LOST = "lost"

RFM_SEGMENT_CHOICES = [
    (CHAMPIONS, "Champions"),
    (LOYAL, "Loyal"),
    (POTENTIAL_LOYALISTS, "Potential Loyalists"),
    (NEW_CUSTOMERS, "New Customers"),
    (AT_RISK, "At Risk"),
    (HIBERNATING, "Hibernating"),
    (LOST, "Lost"),
]
