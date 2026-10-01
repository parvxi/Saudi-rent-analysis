"""Source schema and validation domains for the Aqar listings CSV."""

DETAILS_COLUMN = "details"

SOURCE_COLUMNS = (
    "city",
    "district",
    "front",
    "size",
    "property_age",
    "bedrooms",
    "bathrooms",
    "livingrooms",
    "kitchen",
    "garage",
    "driver_room",
    "maid_room",
    "furnished",
    "ac",
    "roof",
    "pool",
    "frontyard",
    "basement",
    "duplex",
    "stairs",
    "elevator",
    "fireplace",
    "price",
    DETAILS_COLUMN,
)

RETAINED_COLUMNS = tuple(
    column for column in SOURCE_COLUMNS if column != DETAILS_COLUMN
)
NUMERIC_COLUMNS = (
    "size",
    "property_age",
    "bedrooms",
    "bathrooms",
    "livingrooms",
    "price",
)
BINARY_COLUMNS = (
    "kitchen",
    "garage",
    "driver_room",
    "maid_room",
    "furnished",
    "ac",
    "roof",
    "pool",
    "frontyard",
    "basement",
    "duplex",
    "stairs",
    "elevator",
    "fireplace",
)
KNOWN_CITIES = frozenset({"الخبر", "الدمام", "الرياض", "جدة"})
KNOWN_FRONTS = frozenset(
    {
        "جنوب",
        "جنوب شرقي",
        "جنوب غربي",
        "شرق",
        "شمال",
        "شمال شرقي",
        "شمال غربي",
        "غرب",
        "3 شوارع",
        "4 شوارع",
    }
)
