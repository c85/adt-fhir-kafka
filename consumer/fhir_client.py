"""
FHIR R4 Client
Posts Patient and Encounter resources to the public HAPI FHIR server.
"""

import json
import requests
from typing import Optional

FHIR_BASE_URL = "https://hapi.fhir.org/baseR4"
HEADERS = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json",
}
TIMEOUT = 15


class FHIRClient:
    def __init__(self, base_url: str = FHIR_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update(HEADERS)

    def _post(self, resource_type: str, payload: dict) -> Optional[dict]:
        url = f"{self.base_url}/{resource_type}"
        try:
            resp = self.session.post(url, data=json.dumps(payload), timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[FHIR ERROR] POST {resource_type} failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"  Response: {e.response.text[:300]}")
            return None

    def create_patient(self, patient_resource: dict) -> Optional[str]:
        """POST Patient resource; returns FHIR logical ID on success."""
        result = self._post("Patient", patient_resource)
        if result:
            fhir_id = result.get("id")
            print(f"[FHIR] Patient created → id={fhir_id} "
                  f"name={patient_resource['name'][0]['family']}, "
                  f"{patient_resource['name'][0]['given'][0]}")
            return fhir_id
        return None

    def create_encounter(self, encounter_resource: dict, patient_fhir_id: str) -> Optional[str]:
        """POST Encounter resource linked to a Patient."""
        result = self._post("Encounter", encounter_resource)
        if result:
            fhir_id = result.get("id")
            print(f"[FHIR] Encounter created → id={fhir_id} "
                  f"patient=Patient/{patient_fhir_id}")
            return fhir_id
        return None
