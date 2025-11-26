from ..schemas import ActivityCo2Result, ActivityInput


def estimate_transport_co2(activity: ActivityInput) -> float:
    """Estimate CO2 for transport activities based on distance."""
    t = activity.type.lower()
    distance = activity.value

    if any(k in t for k in ["bts", "mrt", "train"]):
        factor = 0.08
    elif "bus" in t:
        factor = 0.15
    elif any(k in t for k in ["taxi", "car", "motorbike", "bike"]):
        factor = 0.20
    elif any(k in t for k in ["walk", "เดิน"]):
        factor = 0.0
    else:
        factor = 0.12

    return max(distance * factor, 0.0)


def estimate_food_co2(activity: ActivityInput) -> float:
    """Estimate CO2 for food activities based on portion."""
    t = activity.type.lower()
    portion = activity.value

    if any(k in t for k in ["beef", "เนื้อวัว"]):
        base = 5.0
    elif any(k in t for k in ["pork", "หมู"]):
        base = 2.5
    elif any(k in t for k in ["chicken", "ไก่"]):
        base = 1.5
    elif any(k in t for k in ["fish", "ปลา"]):
        base = 1.0
    elif any(k in t for k in ["vegan", "ผัก", "vegetable"]):
        base = 0.5
    else:
        base = 1.0

    return max(base * portion, 0.0)


def estimate_other_activity_co2(activity: ActivityInput) -> float:
    """Estimate CO2 impact for other activities using duration."""
    t = activity.type.lower()
    duration = activity.value

    if any(k in t for k in ["run", "running", "cycle", "cycling", "gym", "yoga", "swim", "walking"]):
        per_10 = -0.05
    elif any(k in t for k in ["clean", "housework", "ล้าง", "กวาด", "ถู"]):
        per_10 = -0.02
    else:
        per_10 = 0.0

    factor = duration / 10.0
    return per_10 * factor


def estimate_activity_co2(activity: ActivityInput) -> ActivityCo2Result:
    if activity.category == "TRANSPORT":
        co2 = estimate_transport_co2(activity)
    elif activity.category == "FOOD":
        co2 = estimate_food_co2(activity)
    else:
        co2 = estimate_other_activity_co2(activity)

    return ActivityCo2Result(
        id=activity.id,
        category=activity.category,
        type=activity.type,
        value=activity.value,
        co2=round(co2, 3),
    )
