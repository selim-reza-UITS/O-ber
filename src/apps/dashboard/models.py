from django.db import models
from django_prose_editor.fields import ProseEditorField
from django.conf import settings

class TermsAndConditionsModel(models.Model):
    content = ProseEditorField(
        extensions={
            # Core text formatting
            "Bold": True,
            "Italic": True,
            "Strike": True,
            "Underline": True,
            "HardBreak": True,

            # Structure
            "Heading": {
                "levels": [1, 2, 3,4,5,6]
            },
            "BulletList": True,
            "OrderedList": True,
            "ListItem": True,
            "Blockquote": True,

            # Advanced extensions
            "Link": {
                "enableTarget": True,
                "protocols": ["http", "https", "mailto"],
            },
            "Table": True,
            "TableRow": True,
            "TableHeader": True,
            "TableCell": True,

            # Editor capabilities
            "History": True,
            "HTML": True, 
            "Typographic": True,
        },
        sanitize=True 
    )
    
class PrivacyAndPolicyModel(models.Model):
    content = ProseEditorField(
        extensions={
            # Core text formatting
            "Bold": True,
            "Italic": True,
            "Strike": True,
            "Underline": True,
            "HardBreak": True,

            # Structure
            "Heading": {
                "levels": [1, 2, 3,4,5,6]
            },
            "BulletList": True,
            "OrderedList": True,
            "ListItem": True,
            "Blockquote": True,

            # Advanced extensions
            "Link": {
                "enableTarget": True,
                "protocols": ["http", "https", "mailto"],
            },
            "Table": True,
            "TableRow": True,
            "TableHeader": True,
            "TableCell": True,

            # Editor capabilities
            "History": True,
            "HTML": True, 
            "Typographic": True,
        },
        sanitize=True 
    )
    
    
class AboutUs(models.Model):
    content = ProseEditorField(
        extensions={
            "Bold": True,
            "Italic": True,
            "Strike": True,
            "Underline": True,
            "HardBreak": True,

            "Heading": {
                "levels": [1, 2, 3,4,5,6]
            },
            "BulletList": True,
            "OrderedList": True,
            "ListItem": True,
            "Blockquote": True,

            "Link": {
                "enableTarget": True,
                "protocols": ["http", "https", "mailto"],
            },
            "Table": True,
            "TableRow": True,
            "TableHeader": True,
            "TableCell": True,

            "History": True,
            "HTML": True, 
            "Typographic": True,
        },
        sanitize=True 
    )

    class Meta:
        verbose_name_plural = 'About Us'

    def __str__(self):
        return "About Us"
    
class HelpSupport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Support from {self.user.full_name} at {self.created_at}"
    

class PriceConfig(models.Model):
    vehicle_type = models.CharField(max_length=20, unique=True)
    base_fare = models.DecimalField(max_digits=6, decimal_places=2, default=5.00)
    price_per_km = models.DecimalField(max_digits=6, decimal_places=2, default=2.50)
    price_per_minute = models.DecimalField(max_digits=6, decimal_places=2, default=0.50)
    aruba_tax_percentage = models.DecimalField(max_digits=4, decimal_places=2, default=7.00)

    def __str__(self):
        return f"Pricing for {self.vehicle_type}"

class Notification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: Link to a specific user if it's personal, or null for system-wide
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title