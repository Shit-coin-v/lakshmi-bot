"""RFM segment labels — single source of truth.

Used by models (choices), services (SEGMENT_MAP), and campaigns.
"""

RFM_SEGMENT_CHOICES = [
    ("champions", "Champions"),
    ("loyal", "Loyal"),
    ("potential_loyalists", "Potential Loyalists"),
    ("new_customers", "New Customers"),
    ("at_risk", "At Risk"),
    ("hibernating", "Hibernating"),
    ("lost", "Lost"),
]
