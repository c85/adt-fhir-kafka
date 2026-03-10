"""
HL7 ADT → FHIR R4 Mapper
Converts structured ADT A01 payload to FHIR Patient + Encounter resources.
"""

from datetime import datetime, timezone


GENDER_MAP = {"M": "male", "F": "female", "U": "unknown"}


def _fhir_datetime(hl7_dt: str) -> str:
    """Convert HL7 datetime (YYYYMMDDHHMMSS) to ISO 8601."""
    try:
        dt = datetime.strptime(hl7_dt, "%Y%m%d%H%M%S")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _fhir_date(hl7_date: str) -> str:
    """Convert HL7 date (YYYYMMDD) to YYYY-MM-DD."""
    try:
        return datetime.strptime(hl7_date, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return hl7_date


def build_fhir_patient(adt: dict) -> dict:
    """
    Map ADT patient segment → FHIR R4 Patient resource.
    https://www.hl7.org/fhir/patient.html
    """
    p = adt["patient"]
    facility = adt["encounter"]["facility"]

    return {
        "resourceType": "Patient",
        "identifier": [
            {
                "use": "usual",
                "type": {
                    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]
                },
                "system": f"urn:oid:facility:{facility.replace(' ', '_')}",
                "value": p["id"],
            }
        ],
        "name": [
            {
                "use": "official",
                "family": p["last_name"],
                "given": [p["first_name"]],
            }
        ],
        "gender": GENDER_MAP.get(p["gender"], "unknown"),
        "birthDate": _fhir_date(p["dob"]),
    }


def build_fhir_encounter(adt: dict, patient_fhir_id: str) -> dict:
    """
    Map ADT encounter segment → FHIR R4 Encounter resource.
    https://www.hl7.org/fhir/encounter.html
    """
    enc = adt["encounter"]
    physician = enc["physician"]

    return {
        "resourceType": "Encounter",
        "status": "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
            "display": "inpatient encounter",
        },
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "305351004",
                        "display": "Admission to hospital",
                    }
                ]
            }
        ],
        "subject": {"reference": f"Patient/{patient_fhir_id}"},
        "participant": [
            {
                "type": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                                "code": "ATND",
                                "display": "attender",
                            }
                        ]
                    }
                ],
                "individual": {
                    "identifier": {
                        "system": "http://hl7.org/fhir/sid/us-npi",
                        "value": physician["npi"],
                    },
                    "display": physician["name"],
                },
            }
        ],
        "period": {"start": _fhir_datetime(enc["admit_dt"])},
        "location": [
            {
                "location": {"display": f"{enc['facility']} — {enc['ward']}"},
                "status": "active",
            }
        ],
        "serviceProvider": {"display": enc["facility"]},
    }
