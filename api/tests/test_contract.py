from app.main import app


def test_expected_contract_operations_are_registered() -> None:
    operations = {
        operation["operationId"]
        for path in app.openapi()["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    assert {
        "getHealth",
        "createSession",
        "listListings",
        "createListing",
        "getListingAvailability",
        "suggestListingPrice",
        "presignMediaUpload",
        "createBooking",
        "handoverBooking",
        "returnBooking",
        "reportBookingDamage",
        "createReview",
        "getBookingLedger",
        "getDashboard",
        "getCurrentUser",
        "listMyListings",
        "listMrtStations",
        "getListing",
        "updateListing",
        "setListingAvailability",
        "attachListingMedia",
        "listBookings",
        "getBooking",
        "cancelBooking",
        "settleBooking",
        "getBookingChecklists",
        "listReviews",
        "createMeetup",
        "listMeetups",
        "getMeetup",
        "counterMeetup",
        "acceptMeetup",
        "declineMeetup",
        "cancelMeetup",
    } <= operations
