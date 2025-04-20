# models.py
from mongoengine    import Document, StringField, IntField, EmailField, FloatField, ReferenceField, DateTimeField, BooleanField, ListField, DictField, ValidationError
import pytz
from datetime import datetime, timedelta

# Helper function to convert UTC time to IST
def convert_to_ist(utc_time):
    if utc_time is None:
        return None

    # Make sure the time is timezone-aware in UTC if not already
    if utc_time.tzinfo is None:
        utc_time = pytz.utc.localize(utc_time)

    # IST timezone
    ist_timezone = pytz.timezone('Asia/Kolkata')  # IST timezone
    ist_time = utc_time.astimezone(ist_timezone)  # Convert to IST
    return ist_time

class Business(Document):
    # Business Details fields
    business_name       =   StringField     (max_length=255, blank=True, null=True)
    business_address    =   StringField     (max_length=255, blank=True, null=True)
    business_type       =   StringField     (max_length=100, blank=True, null=True)

    meta = {
        'collection': 'business'  # The name of the collection in MongoDB
    }

    def __str__(self):
        return f"Business: {self.business_name}"

class User(Document):
    EXPORTER = 'exporter'
    IMPORTER = 'importer'
    PENDING = 'pending'
    VERIFIED = 'verified'

    USER_TYPE_CHOICES = [
        (EXPORTER, 'Indian Exporter'),
        (IMPORTER, 'Importer'),
    ]

    VERIFICATION_STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (VERIFIED, 'Verified'),
    ]

    # Basic User fields
    userid      =   IntField        (primary_key=True)
    name        =   StringField     (max_length=100)
    username    =   StringField     (max_length=50, unique=True)
    email       =   EmailField      (unique=True)
    phone       =   StringField     (max_length=20, blank=True, null=True)
    password    =   StringField     (max_length=255)
    user_type   =   StringField     (max_length=10, choices=USER_TYPE_CHOICES, default=EXPORTER)

    # Verification Status
    verification_status     =   StringField     (max_length=10, choices=VERIFICATION_STATUS_CHOICES, default=PENDING)

    # Business Details fields
    gst_number              =   StringField    (max_length=15, blank=True, null=True)
    pan_number              =   StringField    (max_length=10, blank=True, null=True)
    iec                     =   StringField    (max_length=10, blank=True, null=True)

    # Country (importers will have this field, exporters will have India as default)
    country                 =   StringField    (max_length=50, blank=True, null=True)

    # Reference to Business model
    business                =   ReferenceField  (Business, reverse_delete_rule=2)

    meta = {
        'collection': 'users'  # The name of the collection in MongoDB
    }
    def __str__(self):
        return self.username

class Auction(Document):
    # Product details
    product_name    =   StringField     (max_length=255, required=True)
    category        =   StringField     (required=True)
    subcategory     =   StringField     (required=True)
    hs_code         =   StringField     ()
    description     =   StringField     (required=True)

    # Auction Details
    initial_price   =   FloatField      (required=True)
    current_price   =   FloatField      (required=True)
    unit            =   StringField     (required=True)
    quantity        =   StringField     (required=True)
    round           =   IntField        (required=True)
    total_rounds    =   IntField        (default=1, required=True, const=True)
    time_left       =   StringField     (max_length=50)
    bids            =   ListField       (ReferenceField('Bids'))  # Reference to Bids model (list of bid IDs)
    winner          =   ReferenceField  ('Bids', null=True)

    # Additional details
    created_at      =   DateTimeField   (default=datetime.utcnow, required=True)

    # Reference to User (User who created the auction)
    user            =   ReferenceField  (User, required=True)

    # To store registered users' usernames
    registered_users = ListField        (ReferenceField(User, reverse_delete_rule=2), default=[])

    meta = {
        'collection': 'auctions'  # The name of the collection in MongoDB
    }

    def get_reverse_auction_winner(self):
        """
        Returns the bid with the lowest price in a reverse auction.
        """
        if not self.bids:
            return None

        print(f"Bids available: {self.bids}")

        # Fetch the actual Bids from the database using auction ID
        bids = Bids.objects(auctionID=self)  # Query all bids associated with this auction

        # Check if there are any bids available
        if not bids:
            print("No bids found for this auction.")
            return None

        # Print the bids and their prices to help with debugging
        for bid in bids:
            print(f"Bid ID: {bid.id}, Price per Quantity: {bid.pricePerQuantity}")

        # Now sort the bids by pricePerQuantity in ascending order (lowest first)
        try:
            winner_bid = min(bids, key=lambda bid: bid.pricePerQuantity)
        except Exception as e:
            print(f"Error in selecting winner bid: {str(e)}")
            return None

        # Return the winner bid object
        return winner_bid

    def get_time_left(self):
        # Convert UTC to IST
        ist_time = convert_to_ist(self.created_at)

        # Get current time in IST
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))

        print(f"IST Time: {ist_time}, Current Time in IST: {current_time}")

        # Add 24 hours to the auction's created time
        end_time = ist_time + timedelta(hours=24)

        # Calculate time remaining
        time_difference = end_time - current_time

        # If time remaining is greater than zero, calculate hours and minutes
        if time_difference.total_seconds() > 0:
            hours, remainder = divmod(time_difference.total_seconds(), 3600)
            minutes, remainder = divmod(remainder, 60)
            seconds = int(remainder)  # Get remaining seconds
            return f"{int(hours)}:{int(minutes):02d}:{seconds:02d}"  # Format as Hours:Minutes:Seconds

        return "Auction ended"

    def __str__(self):
        return self.product_name

    def clean(self):
        super().clean()
        category_map = {
            "Textiles & Apparels": [
                "Cotton & Synthetic Fabrics",
                "Readymade Garments",
                "Home Textiles",
                "Woolen & Silk Products",
                "Denim & Industrial Textiles",
            ],
            "Handicrafts & Home Decor": [
                "Wooden Handicrafts",
                "Metal Artware",
                "Marble & Stone Handicrafts",
                "Jute Products",
                "Pottery & Ceramic Decor",
                "Carpets & Rugs",
            ],
            "Engineering Goods & Machinery": [
                "Industrial Machinery",
                "Pumps & Valves",
                "Auto Components",
                "Electrical Equipment",
                "Diesel Engines & Generators",
                "Agricultural Implements",
            ],
            "Plastics & Polymers": [
                "Plastic Packaging Materials",
                "Household Plastic Items",
                "PVC, HDPE, LDPE Products",
                "Recycled Plastic Granules",
            ],
            "Leather & Footwear": [
                "Finished Leather",
                "Leather Footwear",
                "Leather Bags & Accessories",
                "Industrial Leather Gloves",
            ],
            "Building & Construction Materials": [
                "Ceramic Tiles & Sanitaryware",
                "Granite, Marble & Natural Stones",
                "Cement & Clinker",
                "Paints & Coatings",
                "Steel & Iron Products",
            ],
            "Automobiles & Spare Parts": [
                "Two-Wheelers",
                "Three-Wheelers",
                "Auto Spare Parts",
                "Tires & Tubes",
            ],
            "Furniture & Wood Products": [
                "Solid Wood Furniture",
                "MDF & Particle Board",
                "Office & School Furniture",
                "Plywood & Veneers",
            ],
            "Eco & Biodegradable Products": [
                "Areca Leaf Plates",
                "Bamboo Products",
                "Jute Bags",
                "Paper Products",
            ],
            "Stationery & Printing": [
                "Notebooks & Diaries",
                "Printing Paper",
                "Packaging Boxes",
                "Office & Educational Supplies",
            ],
            "IT & Electronics": [
                "Computer Accessories",
                "Mobile Accessories",
                "Consumer Electronics",
                "LED Lights",
            ]
        }

        # Validate subcategory belongs to category
        if self.category not in category_map:
            raise ValidationError(f"Invalid category selected: {self.category}")
        
        if self.subcategory not in category_map[self.category]:
            raise ValidationError(f"Subcategory '{self.subcategory}' does not belong to category '{self.category}'.")

        # Custom unit validation
        if self.unit == 'other' and not getattr(self, 'custom_unit', None):
            raise ValidationError("Custom unit must be provided when 'other' is selected.")

    def register_user(self, user):
        if any(u.userid == user.userid for u in self.registered_users):
            return False  # User is already registered
        else:
            self.registered_users.append(user)
            self.save()  # Save the auction object with the updated registered_users list
            return True

class Bids(Document):
    exporterId          =   ReferenceField  ('User', required=True)  # Reference to the exporter (User)
    auctionID           =   ReferenceField  ('Auction', required=True)  # Reference to the Auction

    # Bid-specific fields
    pricePerQuantity    =   FloatField      (required=True, min_value=0)
    bidsMade            =   ListField       (StringField())  # History of bids made (list of bid amounts/timestamps)
    isEnded             =   BooleanField    (default=False)

    # Timestamps
    createdAt           =   DateTimeField   (default=datetime.utcnow, required=True)
    endedAt             =   DateTimeField   ()

    # Create a descending index on createdAt to get the most recent bids first
    meta = {
        'collection': 'bids'  # Name of the collection in MongoDB
    }

    def __str__(self):
        return f"Bid by {self.exporterId.username} for Auction: {self.auctionID.product_name}"

    def add_bid_history(self, bid_value: float):
        """ Adds a bid to the bid history """
        self.bidsMade.append(f"{bid_value} at {convert_to_ist(datetime.utcnow()).isoformat()}")
        self.save()

    def end_bid(self):
        """ Marks the bid as ended """
        self.isEnded = True
        self.endedAt = convert_to_ist(datetime.utcnow())
        self.save()

    def get_created_at_ist(self):
        """ Directly converts the UTC createdAt time to IST when accessed """
        return convert_to_ist(self.createdAt)

    def get_ended_at_ist(self):
        """ Converts the UTC endedAt time to IST when accessed """
        return convert_to_ist(self.endedAt) if self.endedAt else None

class Message(Document):
    # Message fields
    auction             =   ReferenceField  (Auction, required=True)

    sender_username     =   StringField     (max_length=255, required=True)
    receiver_username   =   StringField     (max_length=255, required=True)
    message             =   StringField     (required=True)
    timestamp           =   DateTimeField   (default=lambda: datetime.utcnow())
    read                =   BooleanField    (default=False)

    def __str__(self):
        return f"Message from {self.sender_username} to {self.receiver_username} on {self.timestamp}"

    meta = {
        'collection': 'messages',  # The name of the collection in MongoDB
        'ordering': ['timestamp']
    }

    def get_timestamp_ist(self):
        """ Converts the UTC timestamp to IST when accessed """
        return convert_to_ist(self.timestamp)
