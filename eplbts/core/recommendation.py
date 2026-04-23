import math
from .models import Hospital, HospitalStatus

def haversine_distance(lat1, lon1, lat2, lon2):

    R = 6371  # Earth's radius in km

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def estimate_eta(distance_km):

    if distance_km <= 0:
        return 1
    avg_speed = 30  # km/h for city traffic
    eta_minutes = (distance_km / avg_speed) * 60
    return round(eta_minutes)


def get_hospital_recommendations(patient_event):

    hospitals = Hospital.objects.filter(is_active=True)

    recommendations = []

    for hospital in hospitals:
        status = HospitalStatus.objects.filter(hospital=hospital).first()

        if not status:
            continue

        if not status.is_accepting:
            continue

        # Step 3: Required facilities check
        if patient_event.needs_icu and status.icu_available <= 0:
            continue
        if patient_event.needs_ventilator and not status.has_ventilator:
            continue
        if patient_event.needs_blood_bank and not status.has_blood_bank:
            continue
        if patient_event.needs_cath_lab and not status.has_cath_lab:
            continue

        distance = 0
        eta = 0

        if patient_event.latitude and patient_event.longitude:
            distance = haversine_distance(
                patient_event.latitude,
                patient_event.longitude,
                hospital.latitude,
                hospital.longitude
            )
            eta = estimate_eta(distance)
        else:
            distance = 999
            eta = 99

        icu_load = status.icu_load_percent
        bed_load = status.bed_load_percent

        # Combined score = (distance weight * distance) + (load weight * load)
        score = (0.4 * distance) + (0.3 * icu_load) + (0.3 * bed_load)

        recommendations.append({
            'hospital': hospital,
            'status': status,
            'distance_km': round(distance, 2),
            'eta_minutes': eta,
            'icu_load': icu_load,
            'bed_load': bed_load,
            'score': round(score, 2),
        })

    recommendations.sort(key=lambda x: x['score'])

    return recommendations[:3]