"""The 50 US states, shared by search contracts and source coverage."""

STATES = dict(
    item.split(":", 1)
    for item in [
        "AL:Alabama",
        "AK:Alaska",
        "AZ:Arizona",
        "AR:Arkansas",
        "CA:California",
        "CO:Colorado",
        "CT:Connecticut",
        "DE:Delaware",
        "FL:Florida",
        "GA:Georgia",
        "HI:Hawaii",
        "ID:Idaho",
        "IL:Illinois",
        "IN:Indiana",
        "IA:Iowa",
        "KS:Kansas",
        "KY:Kentucky",
        "LA:Louisiana",
        "ME:Maine",
        "MD:Maryland",
        "MA:Massachusetts",
        "MI:Michigan",
        "MN:Minnesota",
        "MS:Mississippi",
        "MO:Missouri",
        "MT:Montana",
        "NE:Nebraska",
        "NV:Nevada",
        "NH:New Hampshire",
        "NJ:New Jersey",
        "NM:New Mexico",
        "NY:New York",
        "NC:North Carolina",
        "ND:North Dakota",
        "OH:Ohio",
        "OK:Oklahoma",
        "OR:Oregon",
        "PA:Pennsylvania",
        "RI:Rhode Island",
        "SC:South Carolina",
        "SD:South Dakota",
        "TN:Tennessee",
        "TX:Texas",
        "UT:Utah",
        "VT:Vermont",
        "VA:Virginia",
        "WA:Washington",
        "WV:West Virginia",
        "WI:Wisconsin",
        "WY:Wyoming",
    ]
)


def state_code(value: str, *, nationwide: bool = False) -> str:
    code = value.upper()
    if code not in STATES and not (nationwide and code == "US"):
        raise ValueError(
            "Select a valid US state" + (" or US for all states" if nationwide else "")
        )
    return code
